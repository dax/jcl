##
## test_account.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Nov 22 19:32:53 2006 David Rousselie
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

import unittest

import os

from sqlobject import *
from sqlobject.dbconnection import TheURIOpener

from jcl.jabber.error import FieldError
from jcl.model import account
from jcl.model.account import Account, PresenceAccount

from tests.jcl.model.account import ExampleAccount, PresenceAccountExample

DB_PATH = "/tmp/test.db"
DB_URL = DB_PATH# + "?debug=1&debugThreading=1"

class AccountModule_TestCase(unittest.TestCase):
    def test_default_post_func(self):
        result = account.default_post_func("test")
        self.assertEquals(result, "test")

    def test_boolean_post_func_1(self):
        result = account.boolean_post_func("1")
        self.assertTrue(result)

    def test_boolean_post_func_0(self):
        result = account.boolean_post_func("0")
        self.assertFalse(result)

    def test_boolean_post_func_True(self):
        result = account.boolean_post_func("True")
        self.assertTrue(result)
        
    def test_boolean_post_func_true(self):
        result = account.boolean_post_func("true")
        self.assertTrue(result)

    def test_boolean_post_func_False(self):
        result = account.boolean_post_func("False")
        self.assertFalse(result)

    def test_boolean_post_func_false(self):
        result = account.boolean_post_func("false")
        self.assertFalse(result)

    def test_int_post_func(self):
        result = account.int_post_func("42")
        self.assertEquals(result, 42)

    def test_string_not_null_post_func_not_null(self):
        result = account.string_not_null_post_func("ok")
        self.assertEquals(result, "ok")

    def test_string_not_null_post_func_none(self):
        self.assertRaises(FieldError, \
                          account.string_not_null_post_func, \
                          None)

    def test_string_not_null_post_func_empty(self):
        self.assertRaises(FieldError, \
                          account.string_not_null_post_func, \
                          "")

    def test_mandatory_field(self):
        self.assertRaises(FieldError, \
                          account.mandatory_field, \
                          "")
        
class Account_TestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.createTable(ifNotExists = True)
        ExampleAccount.createTable(ifNotExists = True)
        del account.hub.threadConnection

    def tearDown(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        ExampleAccount.dropTable(ifExists = True)
        Account.dropTable(ifExists = True)
        del TheURIOpener.cachedURIs['sqlite://' + DB_URL]
        account.hub.threadConnection.close()
        del account.hub.threadConnection
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        
    def test_set_status(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "test1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account11.status = account.OFFLINE
        self.assertEquals(account11.status, account.OFFLINE)
        # TODO : test first_check attribute
        del account.hub.threadConnection

    def test_set_status_live_password(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = ExampleAccount(user_jid = "test1@test.com", \
                                   name = "account11", \
                                   jid = "account11@jcl.test.com", \
                                   login = "mylogin", \
                                   password = "mypassword", \
                                   store_password = False, \
                                   test_enum = "choice3", \
                                   test_int = 21)
        account11.waiting_password_reply = True
        account11.status = account.OFFLINE
        self.assertEquals(account11.status, account.OFFLINE)
        self.assertEquals(account11.waiting_password_reply, False)
        self.assertEquals(account11.password, None)
        del account.hub.threadConnection

class PresenceAccount_TestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.createTable(ifNotExists = True)
        PresenceAccount.createTable(ifNotExists = True)
        PresenceAccountExample.createTable(ifNotExists = True)
        del account.hub.threadConnection

    def tearDown(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        PresenceAccountExample.dropTable(ifExists = True)
        PresenceAccount.dropTable(ifExists = True)
        Account.dropTable(ifExists = True)
        del TheURIOpener.cachedURIs['sqlite://' + DB_URL]
        account.hub.threadConnection.close()
        del account.hub.threadConnection
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        
    def test_get_presence_actions_fields(self):
        fields = PresenceAccount.get_presence_actions_fields()
        (possibles_actions, chat_default_action) = fields["chat_action"]
        self.assertEquals(chat_default_action, PresenceAccount.DO_SOMETHING)
        self.assertEquals(possibles_actions, PresenceAccount.possibles_actions)
        (possibles_actions, online_default_action) = fields["online_action"]
        self.assertEquals(online_default_action, PresenceAccount.DO_SOMETHING)
        self.assertEquals(possibles_actions, PresenceAccount.possibles_actions)

    def test_possibles_actions(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = PresenceAccountExample(\
            user_jid = "test1@test.com", \
            name = "account11", \
            jid = "account11@jcl.test.com")
        self.assertEquals(account11.possibles_actions, PresenceAccountExample.possibles_actions)
        (possibles_actions, chat_default_action) = account11.get_presence_actions_fields()["chat_action"]
        self.assertEquals(chat_default_action, PresenceAccountExample.DO_SOMETHING_ELSE)
        self.assertEquals(possibles_actions, PresenceAccountExample.possibles_actions)
        del account.hub.threadConnection
    
