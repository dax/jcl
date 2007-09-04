# -*- coding: utf-8 -*-
##
## command.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jun 20 08:19:57 2007 David Rousselie
## $Id$
##
## Copyright (C) 2007 David Rousselie
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##

import re
import datetime
import logging

from sqlobject.sqlbuilder import AND

from pyxmpp.jid import JID
from pyxmpp.jabber.disco import DiscoInfo, DiscoItems, DiscoItem, DiscoIdentity
from pyxmpp.jabber.dataforms import Form, Field
from pyxmpp.message import Message

from jcl.jabber.disco import DiscoHandler, RootDiscoGetInfoHandler
from jcl.model import account
from jcl.model.account import Account, User

COMMAND_NS = "http://jabber.org/protocol/commands"

ACTION_COMPLETE = "complete"
ACTION_NEXT = "next"
ACTION_PREVIOUS = "prev"
ACTION_CANCEL = "cancel"

STATUS_COMPLETED = "completed"
STATUS_EXECUTING = "executing"
STATUS_CANCELED = "canceled"

class FieldNoType(Field):
    def complete_xml_element(self, xmlnode, doc):
        result = Field.complete_xml_element(self, xmlnode, doc)
        result.unsetProp("type")
        return result

class CommandManager(object):
    """Handle Ad-Hoc commands"""

    def __init__(self, component=None, account_manager=None):
        """CommandManager constructor"""
        self.__logger = logging.getLogger("jcl.jabber.command.CommandManager")
        self.component = component
        self.account_manager = account_manager
        self.commands = []
        self.command_re = re.compile("([^#]*#)?(.*)")
        self.sessions = {}

    def get_short_command_name(self, command_name):
        """
        Return short command name associated to given command name:
        'http://jabber.org/protocol/admin#add-user' -> 'add-user'
        """
        match = self.command_re.match(command_name)
        return match.group(2).replace('-', '_')

    def get_command_desc(self, command_name, lang_class):
        """Return localized command description"""
        short_command_name = self.get_short_command_name(command_name)
        command_desc_attribut = "command_" + short_command_name
        if hasattr(lang_class, command_desc_attribut):
            command_desc = getattr(lang_class, command_desc_attribut)
        else:
            command_desc = short_command_name
        return command_desc

    def list_commands(self, disco_items, lang_class):
        """Return DiscoItem for each supported commands"""
        for command_name in self.commands:
            command_desc = self.get_command_desc(command_name,
                                                 lang_class)
            DiscoItem(disco_items,
                      self.component.jid,
                      command_name,
                      command_desc)
        return disco_items

    def get_command_info(self, disco_info, command_name, lang_class):
        """Return command infos"""
        disco_info.add_feature(COMMAND_NS)
        DiscoIdentity(disco_info,
                      self.get_command_desc(command_name, lang_class),
                      "automation",
                      "command-node")
        return disco_info

    def apply_command_action(self, info_query, command_name, action):
        """Apply action on command"""
        short_command_name = self.get_short_command_name(command_name)
        action_command_method = "apply_" + action + "_command"
        if hasattr(self, action_command_method):
            return getattr(self, action_command_method)(info_query,
                                                        short_command_name)
        else:
            return [info_query.make_error_response(\
                "feature-not-implemented")]

    def apply_execute_command(self, info_query, short_command_name):
        return self.execute_multi_step_command(\
            info_query,
            short_command_name,
            lambda session_id: (self.sessions[session_id][0] + 1,
                                self.sessions[session_id][1]))

    def apply_prev_command(self, info_query, short_command_name):
        return self.execute_multi_step_command(\
            info_query,
            short_command_name,
            lambda session_id: (self.sessions[session_id][0] - 1,
                                self.sessions[session_id][1]))

    def apply_cancel_command(self, info_query, short_command_name):
        xml_command = info_query.xpath_eval("c:command",
                                            {"c": "http://jabber.org/protocol/commands"})[0]
        if xml_command.hasProp("sessionid"):
            session_id = xml_command.prop("sessionid")
            response = info_query.make_result_response()
            command_node = response.set_new_content(COMMAND_NS, "command")
            command_node.setProp("node", xml_command.prop("node"))
            command_node.setProp("status", STATUS_CANCELED)
            command_node.setProp("sessionid",
                                 session_id)
            del self.sessions[session_id]
            return [response]

    def generate_session_id(self, node):
        return self.get_short_command_name(node) + ":" + \
               datetime.datetime.now().isoformat()

    def _create_response(self, info_query, completed=True):
        xml_command = info_query.xpath_eval(\
            "c:command",
            {"c": "http://jabber.org/protocol/commands"})[0]
        node = xml_command.prop("node")
        if xml_command.hasProp("sessionid"):
            session_id = xml_command.prop("sessionid")
        else:
            session_id = self.generate_session_id(node)
        self.__logger.debug("Creating command execution with session ID "
                            + str(session_id))
        response = info_query.make_result_response()
        command_node = response.set_new_content(COMMAND_NS, "command")
        command_node.setProp("node", node)
        if completed:
            command_node.setProp("status", STATUS_COMPLETED)
        else:
            command_node.setProp("status", STATUS_EXECUTING)
        command_node.setProp("sessionid",
                             session_id)
        return (response, command_node, session_id)

    def parse_form(self, info_query, session_id):
        fields = info_query.xpath_eval(\
            "c:command/data:x/data:field",
            {"c": "http://jabber.org/protocol/commands",
             "data": "jabber:x:data"})
        for field in fields:
            field_name = field.prop("var")
            values = info_query.xpath_eval(\
                        "c:command/data:x/data:field[@var='"
                        + field_name + "']/data:value",
                        {"c": "http://jabber.org/protocol/commands",
                         "data": "jabber:x:data"})
            if len(values) > 0:
                values = map(lambda value: value.content, values)
                self.__logger.debug("Adding to session '" + session_id
                                    + "': " + field_name + "="
                                    + str(values))
                self.sessions[session_id][1][field_name] = values

    def execute_multi_step_command(self, info_query, short_node,
                                   update_step_func):
        (response,
         command_node,
         session_id) = self._create_response(info_query,
                                             False)
        lang_class = self.component.lang.get_lang_class_from_node(\
            info_query.get_node())
        if not self.sessions.has_key(session_id):
            self.sessions[session_id] = (1, {})
        else:
            self.sessions[session_id] = update_step_func(session_id)
        step = self.sessions[session_id][0]
        step_method = "execute_" + short_node + "_" + str(step)
        self.parse_form(info_query, session_id)
        if hasattr(self, step_method):
            (form, result) = getattr(self, step_method)(\
                info_query,
                self.sessions[session_id][1],
                command_node,
                lang_class)
            return [response] + result
        else:
            return [info_query.make_error_response(\
                "feature-not-implemented")]

    def add_actions(self, command_node, actions, default_action_idx=0):
        actions_node = command_node.newTextChild(None, "actions", None)
        actions_node.setProp("execute", actions[default_action_idx])
        for action in actions:
            actions_node.newTextChild(None, action, None)
        return actions_node

command_manager = CommandManager()

class JCLCommandManager(CommandManager):
    """Implement default set of Ad-Hoc commands"""

    def __init__(self, component=None, account_manager=None):
        """
        JCLCommandManager constructor
        Not implemented commands:
        'http://jabber.org/protocol/admin#user-stats',
        'http://jabber.org/protocol/admin#edit-blacklist',
        'http://jabber.org/protocol/admin#add-to-blacklist-in',
        'http://jabber.org/protocol/admin#add-to-blacklist-out',
        'http://jabber.org/protocol/admin#edit-whitelist',
        'http://jabber.org/protocol/admin#add-to-whitelist-in',
        'http://jabber.org/protocol/admin#add-to-whitelist-out',
        'http://jabber.org/protocol/admin#get-active-users-num',
        'http://jabber.org/protocol/admin#get-idle-users-num',
        'http://jabber.org/protocol/admin#get-active-users',
        'http://jabber.org/protocol/admin#get-idle-users',
        """
        CommandManager.__init__(self, component, account_manager)
        self.__logger = logging.getLogger("jcl.jabber.command.JCLCommandManager")
        self.commands.extend(["list",
                              "http://jabber.org/protocol/admin#add-user",
                              "http://jabber.org/protocol/admin#delete-user",
                              "http://jabber.org/protocol/admin#disable-user",
                              "http://jabber.org/protocol/admin#reenable-user",
                              "http://jabber.org/protocol/admin#end-user-session",
                              "http://jabber.org/protocol/admin#get-user-password",
                              "http://jabber.org/protocol/admin#change-user-password",
                              "http://jabber.org/protocol/admin#get-user-roster",
                              "http://jabber.org/protocol/admin#get-user-lastlogin",
                              "http://jabber.org/protocol/admin#get-registered-users-num",
                              "http://jabber.org/protocol/admin#get-disabled-users-num",
                              "http://jabber.org/protocol/admin#get-online-users-num",
                              "http://jabber.org/protocol/admin#get-registered-users-list",
                              "http://jabber.org/protocol/admin#get-disabled-users-list",
                              "http://jabber.org/protocol/admin#get-online-users-lists",
                              "http://jabber.org/protocol/admin#announce",
                              "http://jabber.org/protocol/admin#set-motd",
                              "http://jabber.org/protocol/admin#edit-motd",
                              "http://jabber.org/protocol/admin#delete-motd",
                              "http://jabber.org/protocol/admin#set-welcome",
                              "http://jabber.org/protocol/admin#delete-welcome",
                              "http://jabber.org/protocol/admin#edit-admin",
                              "http://jabber.org/protocol/admin#restart",
                              "http://jabber.org/protocol/admin#shutdown"])

    def get_name_and_jid(self, mixed_name_and_jid):
        return mixed_name_and_jid.split("/", 1)[:2]

    ## Reusable steps
    def add_form_select_user_jids(self, command_node, lang_class):
        result_form = Form(xmlnode_or_type="result",
                           title="TODO")
        result_form.add_field(name="user_jids",
                              field_type="jid-multi",
                              label=lang_class.field_user_jid)
        result_form.as_xml(command_node)
        return result_form

    def add_form_select_user_jid(self, command_node, lang_class):
        result_form = Form(xmlnode_or_type="result",
                           title="TODO")
        result_form.add_field(name="user_jid",
                              field_type="jid-single",
                              label=lang_class.field_user_jid)
        result_form.as_xml(command_node)
        return result_form

    def __add_accounts_to_field(self, user_jids, field, lang_class, filter=None):
        for (account_type, type_label) in \
                self.account_manager.list_account_types(lang_class):
            account_class = self.account_manager.get_account_class(\
                account_type=account_type)
            for user_jid in user_jids:
                self.__logger.debug("Listing " + str(user_jid) + "'s accounts")
                for _account in account.get_accounts(user_jid, account_class,
                                                     filter):
                    self.__logger.debug(" - " + _account.name)
                    field.add_option(label=_account.name + " (" + account_type
                                     + ") (" + user_jid + ")",
                                     values=[_account.name + "/" + user_jid])

    def add_form_select_accounts(self, session_context,
                                 command_node, lang_class,
                                 filter=None, format_as_xml=True):
        """
        Add a form to select accounts for user JIDs contained in
        session_context[\"user_jids\"]
        """
        result_form = Form(xmlnode_or_type="result",
                           title="TODO")
        field = result_form.add_field(name="account_names",
                                      field_type="list-multi",
                                      label="Account") # TODO
        self.__add_accounts_to_field(session_context["user_jids"],
                                     field, lang_class, filter)
        if format_as_xml:
            result_form.as_xml(command_node)
        return result_form

    def add_form_select_account(self, session_context,
                                command_node, lang_class,
                                format_as_xml=True):
        """
        Add a form to select account for user JIDs contained in
        session_context[\"user_jids\"]
        """
        result_form = Form(xmlnode_or_type="result",
                           title="TODO")
        field = result_form.add_field(name="account_name",
                                      field_type="list-single",
                                      label="Account") # TODO
        self.__add_accounts_to_field(session_context["user_jid"],
                                     field, lang_class)
        if format_as_xml:
            result_form.as_xml(command_node)
        return result_form

    def add_form_select_max(self, command_node, lang_class):
        self.add_actions(command_node, [ACTION_NEXT])
        result_form = Form(xmlnode_or_type="result")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        max_items_field = result_form.add_field(name="max_items",
                                                field_type="list-single",
                                                label="TODO")
        for value in ["25", "50", "75", "100", "150", "200"]:
            max_items_field.add_option(label=value,
                                       values=[value])
        result_form.as_xml(command_node)
        return (result_form, [])

    def add_form_list_accounts(self, command_node, lang_class,
                               var_name, var_label,
                               filter=None, limit=None):
        result_form = Form(xmlnode_or_type="result")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        accounts = account.get_all_accounts(filter=filter, limit=limit)
        accounts_labels = []
        for _account in accounts:
            accounts_labels += [_account.user.jid + " (" + _account.name
                                + " " + str(_account.__class__.__name__) + ")"]
        result_form.fields.append(FieldNoType(name=var_name,
                                              label=var_label,
                                              values=accounts_labels))
        result_form.as_xml(command_node)
        command_node.setProp("status", STATUS_COMPLETED)
        return (result_form, [])

    def select_user_jids_step_1(self, info_query, session_context,
                                command_node, lang_class):
        self.__logger.debug("Executing select_user_jids step 1")
        self.add_actions(command_node, [ACTION_NEXT])
        return (self.add_form_select_user_jids(command_node, lang_class), [])

    def select_user_jid_step_1(self, info_query, session_context,
                               command_node, lang_class,
                               actions=[ACTION_NEXT],
                               default_action=0):
        self.__logger.debug("Executing select_user_jid step 1")
        self.add_actions(command_node, actions, default_action)
        return (self.add_form_select_user_jid(command_node, lang_class), [])

    def select_accounts_step_2(self, info_query, session_context,
                               command_node, lang_class, format_as_xml=True):
        self.__logger.debug("Executing select_accounts step 2")
        self.add_actions(command_node, [ACTION_PREVIOUS, ACTION_COMPLETE], 1)
        return (self.add_form_select_accounts(session_context, command_node,
                                              lang_class, format_as_xml),
                [])

    def select_account_step_2(self, info_query, session_context,
                              command_node, lang_class, format_as_xml=True):
        self.__logger.debug("Executing select_account step 2")
        self.add_actions(command_node, [ACTION_PREVIOUS, ACTION_COMPLETE], 1)
        return (self.add_form_select_account(session_context, command_node,
                                             lang_class, format_as_xml),
                [])

    def execute_list_1(self, info_query, session_context,
                       command_node, lang_class):
        """Execute command 'list'. List accounts"""
        self.__logger.debug("Executing 'list' command")
        result_form = Form(xmlnode_or_type="result",
                           title="Registered account") # TODO : add to Lang
        result_form.reported_fields.append(FieldNoType(name="name",
                                                       label="Account name")) # TODO: add to Lang
        bare_from_jid = unicode(info_query.get_from().bare())
        for _account in account.get_accounts(bare_from_jid):
            fields = [FieldNoType(name="name",
                                  value=_account.name)]
            result_form.add_item(fields)
        result_form.as_xml(command_node)
        command_node.setProp("status", STATUS_COMPLETED)
        return (result_form, [])

    def execute_add_user_1(self, info_query, session_context,
                           command_node, lang_class):
        self.__logger.debug("Executing command 'add-user' step 1")
        self.add_actions(command_node, [ACTION_NEXT])
        result_form = Form(xmlnode_or_type="result",
                           title=lang_class.select_account_type)
        field = result_form.add_field(name="account_type",
                                      field_type="list-single",
                                      label="Account type")
        for (account_type, type_label) in \
                self.component.account_manager.list_account_types(lang_class):
            field.add_option(label=type_label,
                             values=[account_type])
        result_form.add_field(name="user_jid",
                              field_type="jid-single",
                              label=lang_class.field_user_jid)
        result_form.as_xml(command_node)
        return (result_form, [])

    def execute_add_user_2(self, info_query, session_context,
                           command_node, lang_class):
        self.__logger.debug("Executing command 'add-user' step 2")
        self.add_actions(command_node, [ACTION_PREVIOUS, ACTION_COMPLETE], 1)
        user_jid = session_context["user_jid"][0]
        account_type = session_context["account_type"][0]
        account_class = self.account_manager.get_account_class(account_type)
        result_form = self.account_manager.generate_registration_form(lang_class,
                                                                      account_class,
                                                                      user_jid)
        result_form.as_xml(command_node)
        return (result_form, [])

    def execute_add_user_3(self, info_query, session_context,
                           command_node, lang_class):
        self.__logger.debug("Executing command 'add-user' step 3")
        x_node = info_query.xpath_eval("c:command/jxd:x",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "jxd" : "jabber:x:data"})[0]
        x_data = Form(x_node)
        to_send = self.component.account_manager.create_account_from_type(\
            account_name=session_context["name"][0],
            from_jid=JID(session_context["user_jid"][0]),
            account_type=session_context["account_type"][0],
            lang_class=lang_class,
            x_data=x_data)
        command_node.setProp("status", STATUS_COMPLETED)
        return (None, to_send)

    execute_delete_user_1 = select_user_jids_step_1
    execute_delete_user_2 = select_accounts_step_2

    def execute_delete_user_3(self, info_query, session_context,
                              command_node, lang_class):
        self.__logger.debug("Executing command 'delete-user' step 3")
        result = []
        for account_name in session_context["account_names"]:
            name, user_jid = self.get_name_and_jid(account_name)
            result += self.account_manager.remove_account_from_name(user_jid,
                                                                    name)
        command_node.setProp("status", STATUS_COMPLETED)
        return (None, result)

    execute_disable_user_1 = select_user_jids_step_1

    def execute_disable_user_2(self, info_query, session_context,
                               command_node, lang_class):
        self.__logger.debug("Executing 'disable-user' step 2")
        self.add_actions(command_node, [ACTION_PREVIOUS, ACTION_COMPLETE], 1)
        return (self.add_form_select_accounts(session_context, command_node,
                                              lang_class,
                                              Account.q.enabled==True),
                [])

    def execute_disable_user_3(self, info_query, session_context,
                               command_node, lang_class):
        self.__logger.debug("Executing command 'disable-user' step 3")
        result = []
        for account_name in session_context["account_names"]:
            name, user_jid = self.get_name_and_jid(account_name)
            _account = account.get_account(user_jid, name)
            _account.enabled = False
        command_node.setProp("status", STATUS_COMPLETED)
        return (None, result)

    execute_reenable_user_1 = select_user_jids_step_1

    def execute_reenable_user_2(self, info_query, session_context,
                                command_node, lang_class):
        self.__logger.debug("Executing 'reenable-user' step 2")
        self.add_actions(command_node, [ACTION_PREVIOUS, ACTION_COMPLETE], 1)
        return (self.add_form_select_accounts(session_context, command_node,
                                              lang_class,
                                              Account.q.enabled==False),
                [])

    def execute_reenable_user_3(self, info_query, session_context,
                                command_node, lang_class):
        self.__logger.debug("Executing command 'reenable-user' step 3")
        result = []
        for account_name in session_context["account_names"]:
            name, user_jid = self.get_name_and_jid(account_name)
            _account = account.get_account(user_jid, name)
            _account.enabled = True
        command_node.setProp("status", STATUS_COMPLETED)
        return (None, result)

    execute_end_user_session_1 = select_user_jids_step_1

    def execute_end_user_session_2(self, info_query, session_context,
                                   command_node, lang_class):
        self.__logger.debug("Executing 'end-user-session' step 2")
        self.add_actions(command_node, [ACTION_PREVIOUS, ACTION_COMPLETE], 1)
        return (self.add_form_select_accounts(session_context, command_node,
                                              lang_class,
                                              Account.q._status != account.OFFLINE),
                [])

    def execute_end_user_session_3(self, info_query, session_context,
                                   command_node, lang_class):
        self.__logger.debug("Executing command 'end-user-session' step 3")
        result = []
        for account_name in session_context["account_names"]:
            name, user_jid = self.get_name_and_jid(account_name)
            _account = account.get_account(user_jid, name)
            result += self.component.account_manager.send_presence_unavailable(
                _account)
        command_node.setProp("status", STATUS_COMPLETED)
        return (None, result)

    execute_get_user_password_1 = select_user_jid_step_1
    execute_get_user_password_2 = select_account_step_2

    def execute_get_user_password_3(self, info_query, session_context,
                                    command_node, lang_class):
        self.__logger.debug("Executing command 'get-user-password' step 3")
        result_form = Form(xmlnode_or_type="result")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        name, user_jid = self.get_name_and_jid(session_context["account_name"][0])
        _account = account.get_account(user_jid, name)
        result_form.fields.append(FieldNoType(name="accountjids",
                                              value=user_jid))
        result_form.fields.append(FieldNoType(name="password",
                                              value=_account.password))
        result_form.as_xml(command_node)
        command_node.setProp("status", STATUS_COMPLETED)
        return (result_form, [])

    execute_change_user_password_1 = select_user_jid_step_1

    def execute_change_user_password_2(self, info_query, session_context,
                                       command_node, lang_class):
        self.__logger.debug("Executing command 'change-user-password' step 2")
        (result_form, result) = self.select_account_step_2(info_query,
                                                           session_context,
                                                           command_node,
                                                           lang_class,
                                                           False)
        result_form.add_field(field_type="text-private",
                              name="password",
                              label=lang_class.field_password)
        result_form.as_xml(command_node)
        return (result_form, result)

    def execute_change_user_password_3(self, info_query, session_context,
                                       command_node, lang_class):
        self.__logger.debug("Executing command 'change-user-password' step 2")
        name, user_jid = self.get_name_and_jid(session_context["account_name"][0])
        _account = account.get_account(user_jid, name)
        _account.password = session_context["password"][0]
        command_node.setProp("status", STATUS_COMPLETED)
        return (None, [])

    def execute_get_user_roster_1(self, info_query, session_context,
                                  command_node, lang_class):
        (result_form, result) = self.select_user_jid_step_1(info_query,
                                                            session_context,
                                                            command_node,
                                                            lang_class,
                                                            actions=[ACTION_COMPLETE])
        return (result_form, result)

    def execute_get_user_roster_2(self, info_query, session_context,
                                  command_node, lang_class):
        self.__logger.debug("Executing command 'get-user-roster' step 2")
        result_form = Form(xmlnode_or_type="result")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        user_jid = session_context["user_jid"][0]
        result_form.fields.append(FieldNoType(name="user_jid",
                                              value=user_jid))
        result_form.as_xml(command_node)
        x_form = command_node.children
        query = x_form.newChild(None, "query", None)
        roster_ns = query.newNs("jabber:iq:roster", None)
        query.setNs(roster_ns)
        for legacy_jid in account.get_legacy_jids(user_jid):
            item = query.newChild(None, "item", None)
            item.setProp("jid", legacy_jid.jid)
            item.setProp("name", legacy_jid.legacy_address)
        command_node.setProp("status", STATUS_COMPLETED)
        return (result_form, [])

    execute_get_user_lastlogin_1 = select_user_jid_step_1
    execute_get_user_lastlogin_2 = select_account_step_2

    def execute_get_user_lastlogin_3(self, info_query, session_context,
                                     command_node, lang_class):
        self.__logger.debug("Executing command 'get-user-roster' step 2")
        result_form = Form(xmlnode_or_type="result")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        name, user_jid = self.get_name_and_jid(session_context["account_name"][0])
        _account = account.get_account(user_jid, name)
        result_form.fields.append(FieldNoType(name="user_jid",
                                              value=user_jid))
        result_form.fields.append(FieldNoType(name="lastlogin",
                                              value=_account.lastlogin))
        result_form.as_xml(command_node)
        command_node.setProp("status", STATUS_COMPLETED)
        return (result_form, [])

    def execute_get_registered_users_num_1(self, info_query, session_context,
                                           command_node, lang_class):
        result_form = Form(xmlnode_or_type="result")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        num_accounts = account.get_all_accounts_count()
        result_form.fields.append(FieldNoType(name="registeredusersnum",
                                              label="TODO",
                                              value=num_accounts))
        result_form.as_xml(command_node)
        command_node.setProp("status", STATUS_COMPLETED)
        return (result_form, [])

    def execute_get_disabled_users_num_1(self, info_query, session_context,
                                         command_node, lang_class):
        result_form = Form(xmlnode_or_type="result")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        num_accounts = account.get_all_accounts_count(\
            filter=(Account.q.enabled == False))
        result_form.fields.append(FieldNoType(name="disabledusersnum",
                                              label="TODO",
                                              value=num_accounts))
        result_form.as_xml(command_node)
        command_node.setProp("status", STATUS_COMPLETED)
        return (result_form, [])

    def execute_get_online_users_num_1(self, info_query, session_context,
                                       command_node, lang_class):
        result_form = Form(xmlnode_or_type="result")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        num_accounts = account.get_all_accounts_count(\
            filter=(Account.q._status != account.OFFLINE))
        result_form.fields.append(FieldNoType(name="onlineusersnum",
                                              label="TODO",
                                              value=num_accounts))
        result_form.as_xml(command_node)
        command_node.setProp("status", STATUS_COMPLETED)
        return (result_form, [])

    def execute_get_registered_users_list_1(self, info_query, session_context,
                                            command_node, lang_class):
        num_accounts = account.get_all_accounts_count()
        if num_accounts < 25:
            return self.add_form_list_accounts(command_node, lang_class,
                                               "registeredusers", "TODO")
        else:
            return self.add_form_select_max(command_node, lang_class)

    def execute_get_registered_users_list_2(self, info_query, session_context,
                                            command_node, lang_class):
        limit = int(session_context["max_items"][0])
        return self.add_form_list_accounts(command_node, lang_class,
                                           "registeredusers", "TODO",
                                           limit=limit)

    def execute_get_disabled_users_list_1(self, info_query, session_context,
                                          command_node, lang_class):
        num_accounts = account.get_all_accounts_count()
        if num_accounts < 25:
            return self.add_form_list_accounts(command_node, lang_class,
                                               "disabledusers", "TODO",
                                               filter=(Account.q.enabled == False))
        else:
            return self.add_form_select_max(command_node, lang_class)

    def execute_get_disabled_users_list_2(self, info_query, session_context,
                                          command_node, lang_class):
        limit = int(session_context["max_items"][0])
        return self.add_form_list_accounts(command_node, lang_class,
                                           "disabledusers", "TODO",
                                           limit=limit,
                                           filter=(Account.q.enabled == False))

    def execute_get_online_users_list_1(self, info_query, session_context,
                                        command_node, lang_class):
        num_accounts = account.get_all_accounts_count()
        if num_accounts < 25:
            return self.add_form_list_accounts(\
                command_node, lang_class,
                "onlineusers", "TODO",
                filter=(Account.q._status != account.OFFLINE))
        else:
            return self.add_form_select_max(command_node, lang_class)

    def execute_get_online_users_list_2(self, info_query, session_context,
                                        command_node, lang_class):
        limit = int(session_context["max_items"][0])
        return self.add_form_list_accounts(\
            command_node, lang_class,
            "onlineusers", "TODO",
            limit=limit,
            filter=(Account.q._status != account.OFFLINE))

    def execute_announce_1(self, info_query, session_context,
                           command_node, lang_class):
        self.add_actions(command_node, [ACTION_NEXT])
        result_form = Form(xmlnode_or_type="result",
                           title="TODO",
                           instructions="TODO")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        result_form.add_field(name="announcement",
                              field_type="text-multi",
                              label="TODO",
                              required=True)
        result_form.as_xml(command_node)
        return (result_form, [])

    def execute_announce_2(self, info_query, session_context,
                           command_node, lang_class):
        self.__logger.debug("Executing command 'announce' step 2")
        announcement = session_context["announcement"][0]
        users = account.get_all_users(\
            filter=AND(Account.q.userID == User.q.id,
                       Account.q._status != account.OFFLINE),
            distinct=True)
        result = []
        for user in users:
            result.append(Message(from_jid=self.component.jid,
                                  to_jid=user.jid,
                                  body=announcement))
            command_node.setProp("status", STATUS_COMPLETED)
        return (None, result)

    def execute_set_motd_1(self, info_query, session_context,
                           command_node, lang_class, motd=""):
        self.add_actions(command_node, [ACTION_NEXT])
        result_form = Form(xmlnode_or_type="result",
                           title="TODO",
                           instructions="TODO")
        result_form.add_field(field_type="hidden",
                              name="FORM_TYPE",
                              value="http://jabber.org/protocol/admin")
        result_form.add_field(name="motd",
                              field_type="text-multi",
                              label="TODO",
                              value=[motd],
                              required=True)
        result_form.as_xml(command_node)
        return (result_form, [])

    def execute_set_motd_2(self, info_query, session_context,
                           command_node, lang_class):
        self.__logger.debug("Executing command 'set motd' step 2")
        motd = session_context["motd"][0]
        self.component.set_motd(motd)
        users = account.get_all_users(\
            filter=AND(Account.q.userID == User.q.id,
                       Account.q._status != account.OFFLINE),
            distinct=True)
        result = []
        motd = self.component.get_motd()
        if motd is not None:
            for user in users:
                for _account in user.accounts:
                    if _account.status == account.OFFLINE:
                        user.has_received_motd = False
                    else:
                        user.has_received_motd = True
                if user.has_received_motd:
                    result.append(Message(from_jid=self.component.jid,
                                          to_jid=user.jid,
                                          body=motd))
        command_node.setProp("status", STATUS_COMPLETED)
        return (None, result)

    def execute_edit_motd_1(self, info_query, session_context,
                            command_node, lang_class):
        return self.execute_set_motd_1(info_query, session_context,
                                       command_node, lang_class,
                                       self.component.get_motd())

    execute_edit_motd_2 = execute_set_motd_2

    def execute_delete_motd_1(self, info_query, session_context,
                              command_node, lang_class):
        return []

    def execute_set_welcome(self, info_query):
        return []

    def execute_delete_welcome(self, info_query):
        return []

    def execute_edit_admin(self, info_query):
        return []

    def execute_restart(self, info_query):
        return []

    def execute_shutdown(self, info_query):
        return []

class CommandRootDiscoGetInfoHandler(RootDiscoGetInfoHandler):

    def handle(self, info_query, lang_class, node, disco_obj, data):
        """Add command feature to DiscoInfo"""
        disco_infos = RootDiscoGetInfoHandler.handle(self, info_query,
                                                    lang_class, node,
                                                    disco_obj, data)
        disco_infos[0].add_feature(COMMAND_NS)
        return disco_infos

class CommandDiscoGetInfoHandler(DiscoHandler):
    """Handle Ad-Hoc command disco get info requests"""

    def filter(self, info_query, lang_class, node):
        """
        Filter requests to be handled. Only known commands
        """
        return (node in command_manager.commands)

    def handle(self, info_query, lang_class, node, disco_obj, data):
        """
        Return infos for given command
        """
        if not disco_obj:
            disco_obj = DiscoInfo()
        return [command_manager.get_command_info(disco_info=disco_obj,
                                                 command_name=node,
                                                 lang_class=lang_class)]

class CommandDiscoGetItemsHandler(DiscoHandler):
    """Handle Ad-Hoc command disco get items requests"""

    def filter(self, info_query, lang_class, node):
        """
        Filter requests to be handled.
        """
        return (node == 'http://jabber.org/protocol/commands')

    def handle(self, info_query, lang_class, node, disco_obj, data):
        """
        """
        if not disco_obj:
            disco_obj = DiscoItems()
        return [command_manager.list_commands(disco_items=disco_obj,
                                              lang_class=lang_class)]

