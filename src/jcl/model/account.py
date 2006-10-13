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
from sqlobject.col import StringCol, BoolCol
from sqlobject.dbconnection import ConnectionHub

from jcl.lang import Lang

OFFLINE = 0
ONLINE = 1

# create a hub to attach a per thread connection
hub = ConnectionHub()

class Account(SQLObject):
    """Base Account class"""
    _cacheValue = False
    _connection = hub
    user_jid = StringCol()
    name = StringCol()
    jid = StringCol()
    login = StringCol(default = "")
    __password = StringCol(default = "")
    __store_password = BoolCol(default = True)

    default_lang_class = Lang.en
    first_check = True
    __status = OFFLINE
    waiting_password_reply = False
    __volatile_password = ""
    
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
            self.waiting_password_reply = False
            if not self.store_password:
                self.password = None
        else:
            self.first_check = True
        self.__status = status
        
    status = property(get_status, set_status)

    def set_password(self, password):
        """Set password associated to account"""
        self.__password = password

    def get_password(self):
        """Return password associated to account"""
        return self.__password

    password = property(get_password, set_password)

    def set_store_password(self, store_password):
        """Set store_password attribut
        determine if password is persitent or not"""
        if store_password:
            self.password = property(get_password, set_password)
        else:
            self.password = property(get_volatile_password, \
                                     set_volatile_password)
        self.__store_password = store_password

    def get_store_password(self):
        """Return store_password boolean"""
        return self.__store_password
    
    store_password = property(get_store_password, set_store_password)
