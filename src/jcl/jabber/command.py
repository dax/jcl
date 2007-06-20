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

from pyxmpp.jabber.disco import DiscoInfo, DiscoItems, DiscoItem, DiscoIdentity

import jcl
from jcl.jabber import DiscoHandler

class CommandManager(object):
    """Handle Ad-Hoc commands"""

    def __init__(self, component=None, account_manager=None):
        """CommandManager constructor"""
        self.component = component
        self.account_manager = account_manager
        self.commands = []

    def get_command_desc(self, command_name, lang_class):
        """Return localized command description"""
        command_desc_attribut = "command_" + command_name
        if hasattr(lang_class, command_desc_attribut):
            command_desc = getattr(lang_class, command_desc_attribut)
        else:
            command_desc = command_name
        return command_desc

    def list_commands(self, disco_items, lang_class):
        """Return DiscoItem for each supported commands"""
        for command_name in self.commands:
            DiscoItem(disco_items,
                      self.component.jid,
                      command_name,
                      self.get_command_desc(command_name,
                                            lang_class))
        return disco_items

    def get_command_info(self, disco_info, command, lang_class):
        """Return command infos"""
        get_command_info_method_name = "get_" + command + "_info"
        if hasattr(self, get_command_info_method_name):
            return getattr(self, get_command_info_method_name)(disco_info,
                                                               lang_class)
        else:
            return disco_info

command_manager = CommandManager()

class JCLCommandManager(CommandManager):
    """Implement default set of Ad-Hoc commands"""

    def __init__(self, component=None, account_manager=None):
        """JCLCommandManager constructor"""
        CommandManager.__init__(self, component, account_manager)
        self.commands.extend(["list"])

    def get_list_info(self, disco_info, lang_class):
        """Return infos for 'list' command"""
        disco_info.add_feature("http://jabber.org/protocol/commands")
        DiscoIdentity(disco_info,
                      self.get_command_desc("list", lang_class),
                      "automation",
                      "command-node")
        return disco_info

class CommandDiscoGetInfoHandler(DiscoHandler):
    """Handle Ad-Hoc command disco get info requests"""

    def filter(self, node, info_query):
        """
        Filter requests to be handled. Only known commands
        """
        return (node in command_manager.commands)

    def handle(self, disco_info, node, info_query, data, lang_class):
        """
        Return infos for given command
        """
        if not disco_info:
            disco_info = DiscoInfo()
        return command_manager.get_command_info(disco_info, node, lang_class)

class CommandDiscoGetItemsHandler(DiscoHandler):
    """Handle Ad-Hoc command disco get items requests"""

    def filter(self, node, info_query):
        """
        Filter requests to be handled.
        """
        return (node == 'http://jabber.org/protocol/commands')

    def handle(self, disco_items, node, info_query, data, lang_class):
        """
        """
        if not disco_items:
            disco_items = DiscoItems()
        return command_manager.list_commands(disco_items, lang_class)

