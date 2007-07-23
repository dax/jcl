##
## disco.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jun 27 22:27:25 2007 David Rousselie
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

import logging

from pyxmpp.jid import JID
from pyxmpp.jabber.disco import DiscoInfo, DiscoItems, DiscoItem, DiscoIdentity

import jcl.jabber as jabber

class DiscoHandler(object):
    """Handle disco get items requests"""

    def __init__(self, component):
        self.component = component

    def filter(self, stanza, lang_class, node):
        """Filter requests to be handled"""
        return False

    def handle(self, stanza, lang_class, node, disco_obj, data):
        """Handle disco get items request"""
        return None

class RootDiscoGetInfoHandler(DiscoHandler):

    filter = jabber.root_filter

    def __init__(self, component):
        DiscoHandler.__init__(self, component)
        self.__logger = logging.getLogger("jcl.jabber.RootDiscoGetInfoHandler")

    def handle(self, stanza, lang_class, node, disco_obj, data):
        """Implement discovery get_info on main component JID"""
        self.__logger.debug("root_disco_get_info")
        disco_info = DiscoInfo()
        disco_info.add_feature("jabber:iq:version")
        disco_info.add_feature("http://jabber.org/protocol/disco#info")
        disco_info.add_feature("http://jabber.org/protocol/disco#items")
        if not self.component.account_manager.has_multiple_account_type:
            disco_info.add_feature("jabber:iq:register")
        DiscoIdentity(disco_info, self.component.name,
                      self.component.disco_identity.category,
                      self.component.disco_identity.type)
        return [disco_info]

class AccountDiscoGetInfoHandler(DiscoHandler):

    filter = jabber.account_filter

    def __init__(self, component):
        DiscoHandler.__init__(self, component)
        self.__logger = logging.getLogger("jcl.jabber.AccountDiscoGetInfoHandler")

    def handle(self, stanza, lang_class, node, disco_obj, data):
        """Implement discovery get_info on an account node"""
        self.__logger.debug("account_disco_get_info")
        disco_info = DiscoInfo()
        disco_info.add_feature("jabber:iq:register")
        return [disco_info]

class AccountTypeDiscoGetInfoHandler(AccountDiscoGetInfoHandler):

    filter = jabber.account_type_filter

    def __init__(self, component):
        AccountDiscoGetInfoHandler.__init__(self, component)
        self.__logger = logging.getLogger("jcl.jabber.AccountTypeDiscoGetInfoHandler")

class RootDiscoGetItemsHandler(DiscoHandler):

    filter = jabber.root_filter

    def __init__(self, component):
        DiscoHandler.__init__(self, component)
        self.__logger = logging.getLogger("jcl.jabber.RootDiscoGetItemsHandler")
        
    def handle(self, stanza, lang_class, node, disco_obj, data):
        """Discovery get_items on root node"""
        from_jid = stanza.get_from()
        if node is not None:
            return None
        disco_items = None
        if self.component.account_manager.has_multiple_account_type: # list accounts with only one type declared
            disco_items = DiscoItems()
            for (account_type, type_label) in \
                    self.component.account_manager.list_account_types(lang_class):
                DiscoItem(disco_items,
                          JID(unicode(self.component.jid) + "/" +
                              account_type),
                          account_type,
                          type_label)

        else:
            disco_items = DiscoItems()
            for (_account, resource, account_type) in \
                    self.component.account_manager.list_accounts(from_jid.bare()):
                DiscoItem(disco_items,
                          JID(unicode(_account.jid) + resource),
                          account_type + _account.name,
                          _account.long_name)
        return [disco_items]

class AccountTypeDiscoGetItemsHandler(DiscoHandler):

    filter = jabber.account_type_filter

    def __init__(self, component):
        DiscoHandler.__init__(self, component)
        self.__logger = logging.getLogger("jcl.jabber.AccountTypeDiscoGetItemsHandler")
        
    def handle(self, stanza, lang_class, node, disco_obj, data):
        """Discovery get_items on an account type node"""
        account_type = data
        from_jid = stanza.get_from()
        self.__logger.debug("Listing account for " + account_type)
        account_class = self.component.account_manager.get_account_class(account_type)
        if account_class is not None:
            disco_items = DiscoItems()
            for (_account, resource, account_type) in \
                    self.component.account_manager.list_accounts(from_jid.bare(),
                                                                 account_class,
                                                                 account_type=account_type):
                DiscoItem(disco_items,
                          JID(unicode(_account.jid) + resource),
                          account_type + _account.name,
                          _account.long_name)
            return [disco_items]
        else:
            self.__logger.error("Error: " + str(account_class)
                                + " class not in account_classes")
            return []
