# -*- coding: utf-8 -*-
##
## account.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Aug  9 21:04:42 2006 David Rousselie
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

"""Basic Account implementation
"""

__revision__ = "$Id: account.py,v 1.3 2005/09/18 20:24:07 dax Exp $"

import datetime

from sqlobject.inheritance import InheritableSQLObject
from sqlobject.col import StringCol, IntCol, BoolCol, ForeignKey, DateTimeCol
from sqlobject.joins import MultipleJoin
from sqlobject.sqlbuilder import AND

from jcl.lang import Lang
from jcl.error import FieldError
import jcl.model as model

OFFLINE = "offline"
ONLINE = "online"
DND = "dnd"
XA = "xa"

def default_post_func(field_value, default_func, bare_from_jid):
    """Default post process function: do nothing"""
    if field_value is None or str(field_value) == "":
        return default_func(bare_from_jid)
    return field_value

def int_post_func(field_value, default_func, bare_from_jid):
    """Return an integer from integer field value"""
    if field_value is None or str(field_value) == "":
        return int(default_func(bare_from_jid))
    return int(field_value)

def mandatory_field(field_name, field_value):
    """Used as default function for field that must be specified
    and cannot have an empty value"""
    if field_value is None or str(field_value) == "":
        raise FieldError(field_name, "Field required")
    return field_value

class User(InheritableSQLObject):
    _connection = model.hub

    jid = StringCol()
    has_received_motd = BoolCol(default=False)
    accounts = MultipleJoin("Account")

def get_user(bare_from_jid, user_class=User):
    result = None
    model.db_connect()
    users = user_class.select(User.q.jid == bare_from_jid)
    if users.count() > 0:
        result = users[0]
    return result

def get_all_users(user_class=User, limit=None, filter=None,
                  distinct=False):
    model.db_connect()
    users = user_class.select(clause=filter, limit=limit,
                              distinct=distinct)
    return users

class Account(InheritableSQLObject):
    """Base Account class"""
    _cacheValue = False
    _connection = model.hub

    name = StringCol()
    jid = StringCol()
    _status = StringCol(default=OFFLINE, dbName="status")
    error = StringCol(default=None)
    legacy_jids = MultipleJoin('LegacyJID')
    enabled = BoolCol(default=True)
    lastlogin = DateTimeCol(default=datetime.datetime.today())
    user = ForeignKey("User")

## Use these attributs to support volatile password
##    login = StringCol(default = "")
##    password = StringCol(default = None)
##    store_password = BoolCol(default = True)
##    waiting_password_reply = BoolCol(default = False)

    default_lang_class = Lang.en

    def get_long_name(self):
        """Return Human readable account name"""
        return self.name

    long_name = property(get_long_name)

    def get_status_msg(self, lang_class=Lang.en):
        """Return current status"""
        mapping = {"online": self.get_online_status_msg,
                   "chat": self.get_chat_status_msg,
                   "away": self.get_away_status_msg,
                   "xa": self.get_xa_status_msg,
                   "dnd": self.get_dnd_status_msg,
                   "offline": self.get_offline_status_msg}
        if mapping.has_key(self.status):
            return mapping[self.status](lang_class)
        return self.name

    status_msg = property(get_status_msg)

    def get_default_status_msg(self, lang_class):
        return self.name

    def get_disabled_status_msg(self, lang_class):
        return lang_class.account_disabled

    def get_error_status_msg(self, lang_class):
        return lang_class.account_error

    def get_online_status_msg(self, lang_class):
        return self.get_default_status_msg(lang_class)

    def get_chat_status_msg(self, lang_class):
        return self.get_default_status_msg(lang_class)

    def get_away_status_msg(self, lang_class):
        return self.get_default_status_msg(lang_class)

    def get_xa_status_msg(self, lang_class):
        return self.get_disabled_status_msg(lang_class)

    def get_dnd_status_msg(self, lang_class):
        return self.get_error_status_msg(lang_class)

    def get_offline_status_msg(self, lang_class):
        return self.get_default_status_msg(lang_class)

    def get_status(self):
        """Return current Jabber status"""
        return self._status

    def set_status(self, status):
        """Set current Jabber status"""
        if status == OFFLINE:
            if hasattr(self, 'waiting_password_reply') \
               and hasattr(self, 'store_password') \
               and hasattr(self, 'password'):
                setattr(self, 'waiting_password_reply', False)
                if not getattr(self, 'store_password'):
                    setattr(self, 'password', None)
        else:
            if self._status == OFFLINE:
                self.lastlogin = datetime.datetime.today()
        self._status = status

    status = property(get_status, set_status)

    def _get_register_fields(cls, real_class=None):
        """Return a list of tuples for X Data Form composition
        A tuple is composed of:
        - field_name: might be the name of one of the class attribut
        - field_type: 'text-single', 'hidden', 'text-private', 'boolean',
        'list-single', ...
        - field_options:
        - field_post_func: function called to process received field
        - field_default_func: function to return default value
        """
        return [] # "name" field is mandatory

    get_register_fields = classmethod(_get_register_fields)

    def get_new_message_subject(self, lang_class):
        """Get localized message subject for new account"""
        return lang_class.new_account_message_subject % (self.name)

    def get_new_message_body(self, lang_class):
        """Return localized message body for new account"""
        return lang_class.new_account_message_body

    def get_update_message_subject(self, lang_class):
        """Return localized message subject for existing account"""
        return lang_class.update_account_message_subject % (self.name)

    def get_update_message_body(self, lang_class):
        """Return localized message body for existing account"""
        return lang_class.update_account_message_body

def get_account_filter(filter, account_class=Account):
    result = None
    model.db_connect()
    accounts = account_class.select(filter)
    if accounts.count() > 0:
        result = accounts[0]
    model.db_disconnect()
    return result

def get_account(bare_user_jid, name, account_class=Account):
    real_filter = AND(AND(Account.q.name == name,
                          Account.q.userID == User.q.id),
                      User.q.jid == unicode(bare_user_jid))
    return get_account_filter(real_filter, account_class)

def get_accounts(bare_user_jid, account_class=Account, filter=None):
    if filter is not None:
        filter = AND(AND(Account.q.userID == User.q.id,
                         User.q.jid == unicode(bare_user_jid)),
                     filter)
    else:
        filter = AND(Account.q.userID == User.q.id,
                     User.q.jid == unicode(bare_user_jid))
    accounts = account_class.select(filter)
    return accounts

def get_all_accounts(account_class=Account, filter=None, limit=None):
    model.db_connect()
    accounts = account_class.select(clause=filter, limit=limit)
    return accounts

def get_accounts_count(bare_user_jid, account_class=Account):
    model.db_connect()
    accounts_count = account_class.select(\
        AND(Account.q.userID == User.q.id,
            User.q.jid == unicode(bare_user_jid))).count()
    return accounts_count

def get_all_accounts_count(account_class=Account, filter=None):
    model.db_connect()
    if filter is None:
        accounts_count = account_class.select().count()
    else:
        accounts_count = account_class.select(filter).count()
    return accounts_count
    
class PresenceAccount(Account):
    DO_NOTHING = 0
    DO_SOMETHING = 1

    # Should use EnumCol but attribute redefinition is not supported
    chat_action = IntCol(default = DO_NOTHING)
    online_action = IntCol(default = DO_NOTHING)
    away_action = IntCol(default = DO_NOTHING)
    xa_action = IntCol(default = DO_NOTHING)
    dnd_action = IntCol(default = DO_NOTHING)
    offline_action = IntCol(default = DO_NOTHING)

    possibles_actions = [DO_NOTHING, DO_SOMETHING]

    def _get_presence_actions_fields(cls):
        """Return a list of tuples for X Data Form composition
        for actions asociated to a presence state.
        A tuple is composed of:
        - presence_state (related to an Account attribut): 'chat_action',
        'online_action', 'away_action', 'xa_action', 'dnd_action',
        'offline_action'
        - possible_actions: list of possibles actions
        - default_action: one of the possibles actions, 'None' for no default
        if nothing is selected by the user, Account.DO_NOTHING will be used.
        """
        return {'chat_action': (cls.possibles_actions, \
                 PresenceAccount.DO_SOMETHING), \
                'online_action': (cls.possibles_actions, \
                 PresenceAccount.DO_SOMETHING), \
                'away_action': (cls.possibles_actions, \
                 PresenceAccount.DO_NOTHING), \
                'xa_action': (cls.possibles_actions, \
                 PresenceAccount.DO_NOTHING), \
                'dnd_action': (cls.possibles_actions, \
                 PresenceAccount.DO_NOTHING), \
                'offline_action': (cls.possibles_actions, \
                 PresenceAccount.DO_NOTHING)}

    get_presence_actions_fields = classmethod(_get_presence_actions_fields)

    def _get_register_fields(cls, real_class = None):
        """ See Account._get_register_fields """
        def get_possibles_actions(presence_action_field):
            return real_class.get_presence_actions_fields()[presence_action_field][0]

        def is_action_possible(presence_action_field, action, default_func,
                               bare_from_jid):
            if int(action) in get_possibles_actions(presence_action_field):
                return int(action)
            raise default_func(bare_from_jid)

        def get_default_presence_action(presence_action_field):
            return real_class.get_presence_actions_fields()[presence_action_field][1]

        if real_class is None:
            real_class = cls
        return Account.get_register_fields(real_class) + \
            [(None, None, None, None, None),
             ("chat_action", "list-single",
              [str(action) for action in get_possibles_actions("chat_action")],
              lambda action, default_func, bare_from_jid: \
                     is_action_possible("chat_action",
                                        action,
                                        default_func,
                                        bare_from_jid),
              lambda bare_from_jid: get_default_presence_action("chat_action")),
             ("online_action", "list-single",
              [str(action) for action in get_possibles_actions("online_action")],
              lambda action, default_func, bare_from_jid: \
                  is_action_possible("online_action",
                                     action,
                                     default_func,
                                     bare_from_jid),
              lambda bare_from_jid: \
                  get_default_presence_action("online_action")),
             ("away_action", "list-single",
              [str(action) for action in get_possibles_actions("away_action")],
              lambda action, default_func, bare_from_jid: \
                  is_action_possible("away_action",
                                     action,
                                     default_func,
                                     bare_from_jid),
              lambda bare_from_jid: get_default_presence_action("away_action")),
             ("xa_action", "list-single",
              [str(action) for action in get_possibles_actions("xa_action")],
              lambda action, default_func, bare_from_jid: \
                  is_action_possible("xa_action",
                                     action,
                                     default_func,
                                     bare_from_jid),
              lambda bare_from_jid: get_default_presence_action("xa_action")),
             ("dnd_action", "list-single",
              [str(action) for action in get_possibles_actions("dnd_action")],
              lambda action, default_func, bare_from_jid: \
                  is_action_possible("dnd_action",
                                     action,
                                     default_func,
                                     bare_from_jid),
              lambda bare_from_jid: get_default_presence_action("dnd_action")),
             ("offline_action", "list-single",
              [str(action) for action in get_possibles_actions("offline_action")],
              lambda action, default_func, bare_from_jid: \
                  is_action_possible("offline_action",
                                     action,
                                     default_func,
                                     bare_from_jid),
              lambda bare_from_jid: \
                  get_default_presence_action("offline_action"))]

    get_register_fields = classmethod(_get_register_fields)

    def get_action(self):
        """Get apropriate action depending on current status"""
        mapping = {"online": self.online_action,
                   "chat": self.chat_action,
                   "away": self.away_action,
                   "xa": self.xa_action,
                   "dnd": self.dnd_action,
                   "offline": self.offline_action}
        if mapping.has_key(self.status):
            return mapping[self.status]
        return PresenceAccount.DO_NOTHING

    action = property(get_action)

def get_legacy_jids(bare_to_jid):
    model.db_connect()
    legacy_jids = LegacyJID.select(\
            AND(AND(LegacyJID.q.accountID == Account.q.id,
                    Account.q.userID == User.q.id),
                User.q.jid == bare_to_jid))
    return legacy_jids

class LegacyJID(InheritableSQLObject):
    _connection = model.hub

    legacy_address = StringCol()
    jid = StringCol()
    account = ForeignKey('Account')

