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

from sqlobject.sqlbuilder import AND
from pyxmpp.message import Message

from jcl.jabber import Handler
import jcl.model.account as account
from jcl.model.account import Account

class PasswordMessageHandler(Handler):
    """Handle password message"""

    def __init__(self, component):
        """handler constructor"""
        Handler.__init__(self, component)
        self.password_regexp = re.compile("\[PASSWORD\]")

    def filter(self, stanza, lang_class):
        """
        Return the uniq account associated with a name and user JID.
        DB connection might already be opened.
        """
        _account = account.get_account(stanza.get_to().node,
                                       stanza.get_from().bare())
        if hasattr(_account, 'password') \
               and hasattr(_account, 'waiting_password_reply') \
               and (getattr(_account, 'waiting_password_reply') == True) \
               and self.password_regexp.search(stanza.get_subject()) \
               is not None:
            return _account
        else:
            return None

    def handle(self, stanza, lang_class, data):
        """
        Receive password in stanza (must be a Message) for given account.
        """
        return self.component.account_manager.set_password(data, stanza.get_from(),
                                                           stanza.get_body(),
                                                           lang_class)
