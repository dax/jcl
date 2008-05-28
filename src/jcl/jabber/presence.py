# -*- coding: utf-8 -*-
##
## component.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jun 27 21:42:47 2007 David Rousselie
## $Id$
##
## Copyright (C) 2006 David Rousselie
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

from pyxmpp.presence import Presence
from pyxmpp.message import Message

from jcl.jabber import Handler
from jcl.model import account
import jcl.jabber as jabber

class DefaultPresenceHandler(Handler):
    """Handle presence"""

    def handle(self, stanza, lang_class, data):
        """Return same presence as receive one"""
        to_jid = stanza.get_to()
        from_jid = stanza.get_from()
        stanza.set_to(from_jid)
        stanza.set_from(to_jid)
        return [stanza]

class DefaultSubscribeHandler(Handler):
    """Return default response to subscribe queries"""

    def handle(self, stanza, lang_class, data):
        """Create subscribe response"""
        result = []
        result.append(Presence(from_jid=stanza.get_to(),
                               to_jid=stanza.get_from(),
                               stanza_type="subscribe"))
        result.append(Presence(from_jid=stanza.get_to(),
                               to_jid=stanza.get_from(),
                               stanza_type="subscribed"))
        return result

class DefaultUnsubscribeHandler(Handler):
    """Return default response to subscribe queries"""

    def handle(self, stanza, lang_class, data):
        """Create subscribe response"""
        result = []
        result.append(Presence(from_jid=stanza.get_to(),
                               to_jid=stanza.get_from(),
                               stanza_type="unsubscribe"))
        result.append(Presence(from_jid=stanza.get_to(),
                               to_jid=stanza.get_from(),
                               stanza_type="unsubscribed"))
        return result

class AccountPresenceHandler(Handler):
    filter = jabber.get_account_filter

    def get_account_presence(self, stanza, lang_class, _account):
        raise NotImplemented

    def handle(self, stanza, lang_class, data):
        """Handle presence sent to an account JID"""
        result = []
        _account = data
        result.extend(self.get_account_presence(stanza, lang_class, _account))
        return result

class AccountPresenceAvailableHandler(AccountPresenceHandler):
    def get_account_presence(self, stanza, lang_class, _account):
        _account.default_lang_class = lang_class
        return self.component.account_manager.get_account_presence_available(\
            stanza.get_from(), _account, lang_class)

class RootPresenceHandler(AccountPresenceHandler):
    filter = jabber.get_accounts_root_filter

    def get_root_presence(self, stanza, lang_class, nb_accounts):
        raise NotImplemented

    def handle(self, stanza, lang_class, data):
        """handle presence sent to component JID"""
        result = []
        accounts_length = 0
        accounts = data
        for _account in accounts:
            accounts_length += 1
            result.extend(self.get_account_presence(stanza, lang_class, _account))
        if accounts_length > 0:
            result.extend(self.get_root_presence(stanza, lang_class, accounts_length))
        return result

class RootPresenceAvailableHandler(RootPresenceHandler, AccountPresenceAvailableHandler):
    def get_root_presence(self, stanza, lang_class, nb_accounts):
        from_jid = stanza.get_from()
        result = self.component.account_manager.get_root_presence(\
            from_jid,
            "available",
            "online",
            str(nb_accounts) +
            lang_class.message_status)
        user = account.get_user(unicode(from_jid.bare()))
        if not user.has_received_motd:
            user.has_received_motd = True
            motd = self.component.get_motd()
            if motd is not None:
                result.append(Message(from_jid=self.component.jid,
                                      to_jid=from_jid,
                                      body=motd))
        return result

class AccountPresenceUnavailableHandler(AccountPresenceHandler):
    def get_account_presence(self, stanza, lang_class, _account):
        return self.component.account_manager.get_account_presence_unavailable(\
            stanza.get_from(), _account)

class RootPresenceUnavailableHandler(RootPresenceHandler, AccountPresenceUnavailableHandler):
    def get_root_presence(self, stanza, lang_class, nb_accounts):
        return self.component.account_manager.get_root_presence(\
            stanza.get_from(), "unavailable")

class AccountPresenceSubscribeHandler(Handler):
    """"""

    filter = jabber.get_account_filter

    def handle(self, stanza, lang_class, data):
        """Handle \"subscribe\" iq sent to an account JID"""
        return [stanza.make_accept_response()]

class RootPresenceSubscribeHandler(AccountPresenceSubscribeHandler):
    """"""

    filter = jabber.get_accounts_root_filter

    def handle(self, stanza, lang_class, data):
        """Handle \"subscribe\" iq sent to component JID"""
        if list(data) != []:
            return AccountPresenceSubscribeHandler.handle(self, stanza,
                                                          lang_class, None)
        else:
            return None

class AccountPresenceUnsubscribeHandler(Handler):
    """"""

    filter = jabber.get_account_filter

    def handle(self, stanza, lang_class, data):
        """Handle \"unsubscribe\" iq sent to account JID"""
        from_jid = stanza.get_from()
        _account = data
        return self.component.account_manager.remove_account(_account, from_jid)

class RootPresenceUnsubscribeHandler(Handler):
    """"""

    filter = jabber.get_accounts_root_filter

    def handle(self, stanza, lang_class, data):
        """Handle \"unsubscribe\" iq sent to account JID"""
        from_jid = stanza.get_from()
        _account = data
        return self.component.account_manager.remove_all_accounts(from_jid)
