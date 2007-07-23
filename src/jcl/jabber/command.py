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

from pyxmpp.jid import JID
from pyxmpp.jabber.disco import DiscoInfo, DiscoItems, DiscoItem, DiscoIdentity
from pyxmpp.jabber.dataforms import Form, Field

from jcl.jabber.disco import DiscoHandler, RootDiscoGetInfoHandler
from jcl.model import account

COMMAND_NS = "http://jabber.org/protocol/commands"

ACTION_COMPLETE = "complete"
ACTION_NEXT = "next"
ACTION_PREVIOUS = "prev"
ACTION_CANCEL = "cancel"

STATUS_COMPLETED = "completed"
STATUS_EXECUTING = "executing"
STATUS_CANCELLED = "cancel"

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
        action_command_method = action + "_" + short_command_name
        if hasattr(self, action_command_method):
            return getattr(self, action_command_method)(info_query)
        else:
            return [info_query.make_error_response("feature-not-implemented")]

    def generate_session_id(self, node):
        return self.get_short_command_name(node) + ":" + \
               datetime.datetime.now().isoformat()

    def _create_response(self, info_query, completed=True):
        xml_command = info_query.xpath_eval("c:command",
                                            {"c": "http://jabber.org/protocol/commands"})[0]
        node = xml_command.prop("node")
        if xml_command.hasProp("sessionid"):
            session_id = xml_command.prop("sessionid")
        else:
            session_id = self.generate_session_id(node)
        self.__logger.debug("Creating command execution with session ID " + str(session_id))
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
            value = info_query.xpath_eval(\
                        "c:command/data:x/data:field[@var='"
                        + field_name + "']/data:value",
                        {"c": "http://jabber.org/protocol/commands",
                         "data": "jabber:x:data"})
            if len(value) > 0:
                self.__logger.debug("Adding to session '" + session_id
                                    + "': " + field_name + "="
                                    + value[0].content)
                self.sessions[session_id][1][field_name] = value[0].content

    def execute_multi_step_command(self, info_query, short_node, update_step_func):
        (response,
         command_node,
         session_id) = self._create_response(info_query,
                                             False)
        lang_class = self.component.lang.get_lang_class_from_node(info_query.get_node())
        if not self.sessions.has_key(session_id):
            self.sessions[session_id] = (1, {})
        else:
            self.sessions[session_id] = update_step_func(session_id)
        step = self.sessions[session_id][0]
        step_method = "execute_" + short_node + "_" + str(step)
        self.parse_form(info_query, session_id)
        return [response] + getattr(self, step_method)(info_query,
                                                       self.sessions[session_id][1],
                                                       command_node,
                                                       lang_class)

    def add_actions(self, command_node, actions, default_action_idx=0):
        actions_node = command_node.newTextChild(None, "actions", None)
        actions_node.setProp("execute", actions[default_action_idx])
        for action in actions:
            actions_node.newTextChild(None, action, None)
        return actions_node

    def cancel_command(self, info_query):
        xml_command = info_query.xpath_eval("c:command",
                                            {"c": "http://jabber.org/protocol/commands"})[0]
        if xml_command.hasProp("sessionid"):
            session_id = xml_command.prop("sessionid")
            response = info_query.make_result_response()
            command_node = response.set_new_content(COMMAND_NS, "command")
            command_node.setProp("node", xml_command.prop("node"))
            command_node.setProp("status", STATUS_CANCELLED)
            command_node.setProp("sessionid",
                                 session_id)
            del self.sessions[session_id]

command_manager = CommandManager()

class JCLCommandManager(CommandManager):
    """Implement default set of Ad-Hoc commands"""

    def __init__(self, component=None, account_manager=None):
        """JCLCommandManager constructor"""
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
                              "http://jabber.org/protocol/admin#user-stats",
                              "http://jabber.org/protocol/admin#edit-blacklist",
                              "http://jabber.org/protocol/admin#add-to-blacklist-in",
                              "http://jabber.org/protocol/admin#add-to-blacklist-out",
                              "http://jabber.org/protocol/admin#edit-whitelist",
                              "http://jabber.org/protocol/admin#add-to-whitelist-in",
                              "http://jabber.org/protocol/admin#add-to-whitelist-out",
                              "http://jabber.org/protocol/admin#get-registered-users-num",
                              "http://jabber.org/protocol/admin#get-disabled-users-num",
                              "http://jabber.org/protocol/admin#get-online-users-num",
                              "http://jabber.org/protocol/admin#get-active-users-num",
                              "http://jabber.org/protocol/admin#get-idle-users-num",
                              "http://jabber.org/protocol/admin#get-registered-users-list",
                              "http://jabber.org/protocol/admin#get-disabled-users-list",
                              "http://jabber.org/protocol/admin#get-online-users",
                              "http://jabber.org/protocol/admin#get-active-users",
                              "http://jabber.org/protocol/admin#get-idle-users",
                              "http://jabber.org/protocol/admin#announce",
                              "http://jabber.org/protocol/admin#set-motd",
                              "http://jabber.org/protocol/admin#edit-motd",
                              "http://jabber.org/protocol/admin#delete-motd",
                              "http://jabber.org/protocol/admin#set-welcome",
                              "http://jabber.org/protocol/admin#delete-welcome",
                              "http://jabber.org/protocol/admin#edit-admin",
                              "http://jabber.org/protocol/admin#restart",
                              "http://jabber.org/protocol/admin#shutdown"])

    def execute_list(self, info_query):
        """Execute command 'list'. List accounts"""
        self.__logger.debug("Executing 'list' command")
        (response, command_node, session_id) = self._create_response(info_query,
                                                                     "list")
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
        return [response]

    def execute_add_user(self, info_query):
        """Execute command 'add-user'. Create new account"""
        self.__logger.debug("Executing 'add-user' command")
        return self.execute_multi_step_command(\
            info_query,
            "add_user",
            lambda session_id: (self.sessions[session_id][0] + 1,
                                self.sessions[session_id][1]))

    def prev_add_user(self, info_query):
        """Execute previous step of command 'add-user'."""
        self.__logger.debug("Executing 'add-user' command previous step")
        return self.execute_multi_step_command(\
            info_query,
            "add_user",
            lambda session_id: (self.sessions[session_id][0] - 1,
                                self.sessions[session_id][1]))

    def cancel_add_user(self, info_query):
        """Cancel current 'add-user' session"""
        self.__logger.debug("Cancelling 'add-user' command")
        return self.cancel_command(info_query)

    def execute_add_user_1(self, info_query, session_context, command_node, lang_class):
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
                              field_type="text-single",
                              label=lang_class.field_user_jid)
        result_form.as_xml(command_node)
        return []

    def execute_add_user_2(self, info_query, session_context, command_node, lang_class):
        self.__logger.debug("Executing command 'add-user' step 2")
        self.add_actions(command_node, [ACTION_PREVIOUS, ACTION_COMPLETE], 1)
        user_jid = session_context["user_jid"]
        account_type = session_context["account_type"]
        account_class = self.account_manager.get_account_class(account_type)
        result_form = self.account_manager.generate_registration_form(lang_class,
                                                                      account_class,
                                                                      user_jid)
        result_form.as_xml(command_node)
        return []

    def execute_add_user_3(self, info_query, session_context,
                           command_node, lang_class):
        self.__logger.debug("Executing command 'add-user' step 3")
        x_node = info_query.xpath_eval("c:command/jxd:x",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "jxd" : "jabber:x:data"})[0]
        x_data = Form(x_node)
        to_send = self.component.account_manager.create_account_from_type(\
            account_name=session_context["name"],
            from_jid=JID(session_context["user_jid"]),
            account_type=session_context["account_type"],
            lang_class=lang_class,
            x_data=x_data)
        command_node.setProp("status", STATUS_COMPLETED)
        return to_send

    def execute_delete_user(self, info_query):
        return []

    def execute_disable_user(self, info_query):
        return []

    def execute_reenable_user(self, info_query):
        return []

    def execute_end_user_session(self, info_query):
        return []

    def execute_get_user_password(self, info_query):
        return []

    def execute_change_user_password(self, info_query):
        return []

    def execute_get_user_roster(self, info_query):
        return []

    def execute_get_user_lastlogin(self, info_query):
        return []

    def execute_user_stats(self, info_query):
        return []

    def execute_edit_blacklist(self, info_query):
        return []

    def execute_add_to_blacklist_in(self, info_query):
        return []

    def execute_add_to_blacklist_out(self, info_query):
        return []

    def execute_edit_whitelist(self, info_query):
        return []

    def execute_add_to_whitelist_in(self, info_query):
        return []

    def execute_add_to_whitelist_out(self, info_query):
        return []

    def execute_get_registered_users_num(self, info_query):
        return []

    def execute_get_disabled_users_num(self, info_query):
        return []

    def execute_get_online_users_num(self, info_query):
        return []

    def execute_get_active_users_num(self, info_query):
        return []

    def execute_get_idle_users_num(self, info_query):
        return []

    def execute_get_registered_users_list(self, info_query):
        return []

    def execute_get_disabled_users_list(self, info_query):
        return []

    def execute_get_online_users(self, info_query):
        return []

    def execute_get_active_users(self, info_query):
        return []

    def execute_get_idle_users(self, info_query):
        return []

    def execute_announce(self, info_query):
        return []

    def execute_set_motd(self, info_query):
        return []

    def execute_edit_motd(self, info_query):
        return []

    def execute_delete_motd(self, info_query):
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

