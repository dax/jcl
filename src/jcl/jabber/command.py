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

from pyxmpp.jabber.disco import DiscoInfo, DiscoItems, DiscoItem, DiscoIdentity
from pyxmpp.jabber.dataforms import Form, Field

import jcl
from jcl.lang import Lang
from jcl.jabber.disco import DiscoHandler, RootDiscoGetInfoHandler
from jcl.model import account
from jcl.model.account import Account

COMMAND_NS = "http://jabber.org/protocol/commands"

class FieldNoType(Field):
    def complete_xml_element(self, xmlnode, doc):
        result = Field.complete_xml_element(self, xmlnode, doc)
        result.unsetProp("type")
        return result

class CommandManager(object):
    """Handle Ad-Hoc commands"""

    def __init__(self, component=None, account_manager=None):
        """CommandManager constructor"""
        self.component = component
        self.account_manager = account_manager
        self.commands = []
        self.command_re = re.compile("([^#]*#)?(.*)")

    def get_short_command_name(self, command_name):
        """
        Return short command name associated to given command name:
        'http://jabber.org/protocol/admin#add-user' -> 'add-user'
        """
        match = self.command_re.match(command_name)
        return match.group(2)

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

command_manager = CommandManager()

class JCLCommandManager(CommandManager):
    """Implement default set of Ad-Hoc commands"""

    def __init__(self, component=None, account_manager=None):
        """JCLCommandManager constructor"""
        CommandManager.__init__(self, component, account_manager)
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
        response = info_query.make_result_response()
        command_node = response.set_new_content(COMMAND_NS, "command")
        command_node.setProp("node", "list")
        command_node.setProp("status", "completed")
        #command_node.setProp("sessionid", "????") # TODO
        result_form = Form(xmlnode_or_type="result",
                           title="Registered account") # TODO : add to Lang
        result_form.reported_fields.append(FieldNoType(name="name",
                                                       label="Account name")) # TODO: add to Lang
        bare_from_jid = unicode(info_query.get_from().bare())
        for _account in account.get_accounts(bare_from_jid):
            print "Adding account : " + str(_account)
            fields = [FieldNoType(name="name",
                                  value=_account.name)]
            result_form.add_item(fields)
        result_form.as_xml(command_node)
        return [response]

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

