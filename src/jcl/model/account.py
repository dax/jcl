# -*- coding: UTF-8 -*-
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

from sqlobject.main import SQLObject
from sqlobject.col import StringCol
from sqlobject.dbconnection import ConnectionHub

from jcl.lang import Lang
from jcl.jabber.error import FieldError

OFFLINE = "offline"
ONLINE = "online"


def default_post_func(field_value):
    """Default post process function: do nothing"""
    return field_value

def boolean_post_func(field_value):
    """Return a boolean from boolean field value"""
    return (field_value == "1" or field_value.lower() == "true")

def int_post_func(field_value):
    """Return an integer from integer field value"""
    return int(field_value)

def string_not_null_post_func(field_value):
    """Post process function for not null/empty string"""
    if field_value is None or field_value == "":
        raise FieldError # TODO : add translated message
    return field_value

def mandatory_field(field_name):
    """Used as default function for field that must be specified
    and cannot have default value"""
    raise FieldError # TODO : add translated message

# create a hub to attach a per thread connection
hub = ConnectionHub()

class Account(SQLObject):
    """Base Account class"""
    _cacheValue = False
    _connection = hub
    user_jid = StringCol()
    name = StringCol()
    jid = StringCol()
## Not yet used    first_check = BoolCol(default = True)
    __status = StringCol(default = OFFLINE, dbName = "status")

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
    
    def get_status_msg(self):
        """Return current status"""
        return self.name

    status_msg = property(get_status_msg)

    def get_status(self):
        """Return current Jabber status"""
        return self.__status

    def set_status(self, status):
        """Set current Jabber status"""
        if status == OFFLINE:
            if hasattr(self.__class__, 'waiting_password_reply') \
               and hasattr(self.__class__, 'store_password') \
               and hasattr(self.__class__, 'password'):
                setattr(self.__class__, 'waiting_password_reply', False)
                if not getattr(self.__class__, 'store_password'):
                    setattr(self.__class__, 'password', None)
        else:
            # TODO seems to be a bug : first_check = True only
            # if previous status was OFFLINE
            self.first_check = True
        self.__status = status
        
    status = property(get_status, set_status)


    def _get_register_fields(cls):
        """Return a list of tuples for X Data Form composition
        A tuple is composed of:
        - field_name: might be the name of one of the class attribut
        - field_type: 'text-single', 'hidden', 'text-private', 'boolean',
        'list-single', ...
        - field_post_func: function called to process received field
        - field_default_func: function to return default value (or error if
        field is mandatory)
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
        return lang_class.new_account_message_subject % (self.name)

    def get_update_message_body(self, lang_class):
        """Return localized message body for existing account"""
        return lang_class.new_account_message_body
