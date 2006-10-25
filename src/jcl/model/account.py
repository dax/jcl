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

OFFLINE = "offline"
ONLINE = "online"

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
                self.waiting_password_reply = False
                if not self.store_password:
                    self.password = None
        else:
            # TODO seems a bug : first_check = True only if previous status
            # was OFFLINE
            self.first_check = True
        self.__status = status
        
    status = property(get_status, set_status)


    def get_register_fields(cls):
        return [('name', "text-single")]
    
    get_register_fields = classmethod(get_register_fields)
