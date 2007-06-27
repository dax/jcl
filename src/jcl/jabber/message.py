##
## message.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jun 27 21:43:57 2007 David Rousselie
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

from pyxmpp.message import Message

from jcl.jabber import Handler
from jcl.model.account import Account

class PasswordMessageHandler(Handler):
    """Handle password message"""

    def __init__(self):
        """handler constructor"""
        self.password_regexp = re.compile("\[PASSWORD\]")

    def filter(self, stanza, lang_class):
        """
        Return the uniq account associated with a name and user JID.
        DB connection might already be opened.
        """
        name = stanza.get_to().node
        bare_from_jid = unicode(stanza.get_from().bare())
        accounts = Account.select(\
            AND(Account.q.name == name,
                Account.q.user_jid == bare_from_jid))
        if accounts.count() > 1:
            print >>sys.stderr, "Account " + name + " for user " + \
                bare_from_jid + " must be uniq"
        elif accounts.count() == 0:
            return None
        _account = accounts[0]
        if hasattr(_account, 'password') \
                and hasattr(_account, 'waiting_password_reply') \
                and (getattr(_account, 'waiting_password_reply') == True) \
                and self.password_regexp.search(stanza.get_subject()) \
                is not None:
            return accounts
        else:
            return None

    def handle(self, stanza, lang_class, data):
        """
        Receive password in stanza (must be a Message) for given account.
        """
        _account = data[0]
        _account.password = stanza.get_body()
        _account.waiting_password_reply = False
        return [Message(from_jid=_account.jid,
                        to_jid=stanza.get_from(),
                        subject=lang_class.password_saved_for_session,
                        body=lang_class.password_saved_for_session)]
