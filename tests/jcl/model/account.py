##
## account.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Sat Oct 28 17:03:30 2006 David Rousselie
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

from sqlobject.main import SQLObject
from sqlobject.col import StringCol, BoolCol, EnumCol, IntCol

from jcl.lang import Lang

from jcl.model import account
from jcl.model.account import Account, PresenceAccount

class AccountExample(Account):
    login = StringCol(default = "")
    password = StringCol(default = None)
    store_password = BoolCol(default = True)
    waiting_password_reply = BoolCol(default = False)

    test_enum = EnumCol(default = "choice1", enumValues = ["choice1", "choice2", "choice3"])
    test_int = IntCol(default = 42)
    
    def _get_register_fields(cls):
        def password_post_func(password):
            if password is None or password == "":
                return None
            return password
        
        return Account.get_register_fields() + \
               [("login", "text-single", account.string_not_null_post_func, \
                 account.mandatory_field), \
                ("password", "text-private", password_post_func, \
                 (lambda field_name: None)), \
                ("store_password", "boolean", account.boolean_post_func, \
                 lambda field_name: True), \
                ("test_enum", "list-single",account.string_not_null_post_func,\
                 lambda field_name: "choice2"), \
                ("test_int", "text-single", account.int_post_func, \
                 lambda field_name: 44)]
    
    get_register_fields = classmethod(_get_register_fields)


class PresenceAccountExample(PresenceAccount):
    DO_SOMETHING_ELSE = 2
    possibles_actions = [DO_SOMETHING_ELSE]
    
    def _get_presence_actions_fields(cls):
        """See PresenceAccount._get_presence_actions_fields
        """
        return {'chat_action': (cls.possibles_actions, \
                                PresenceAccountExample.DO_SOMETHING_ELSE), \
                'online_action': (cls.possibles_actions, \
                                  PresenceAccountExample.DO_SOMETHING_ELSE), \
                'away_action': (cls.possibles_actions, \
                                PresenceAccountExample.DO_SOMETHING_ELSE), \
                'xa_action': (cls.possibles_actions, \
                              PresenceAccountExample.DO_SOMETHING_ELSE), \
                'dnd_action': (cls.possibles_actions, \
                               PresenceAccountExample.DO_SOMETHING_ELSE), \
                'offline_action': (cls.possibles_actions, \
                                   PresenceAccountExample.DO_SOMETHING_ELSE)}
    
    get_presence_actions_fields = classmethod(_get_presence_actions_fields)

