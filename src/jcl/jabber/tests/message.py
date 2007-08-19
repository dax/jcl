##
## message.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Fri Jul  6 21:40:55 2007 David Rousselie
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

import unittest

from pyxmpp.message import Message

from jcl.lang import Lang
from jcl.jabber.component import JCLComponent
from jcl.jabber.message import PasswordMessageHandler
import jcl.model.account as account
import jcl.model as model
from jcl.model.account import Account, User

from jcl.model.tests.account import ExampleAccount
from jcl.tests import JCLTestCase

class PasswordMessageHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, Account, ExampleAccount])
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.db_url)
        self.handler = PasswordMessageHandler(self.comp)

    def test_filter_waiting_password(self):
        model.db_connect()
        user1 = User(jid="user1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.waiting_password_reply = True
        account12 = ExampleAccount(user=user1,
                                   name="account12",
                                   jid="account12@jcl.test.com")
        message = Message(from_jid="user1@test.com",
                          to_jid="account11@jcl.test.com",
                          subject="[PASSWORD]",
                          body="secret")
        _account = self.handler.filter(message, None)
        self.assertEquals(_account.name, "account11")
        model.db_disconnect()

    def test_filter_not_waiting_password(self):
        model.db_connect()
        user1 = User(jid="user1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.waiting_password_reply = False
        account12 = ExampleAccount(user=user1,
                                   name="account12",
                                   jid="account12@jcl.test.com")
        message = Message(from_jid="user1@test.com",
                          to_jid="account11@jcl.test.com",
                          subject="[PASSWORD]",
                          body="secret")
        _account = self.handler.filter(message, None)
        self.assertEquals(_account, None)
        model.db_disconnect()

    def test_filter_not_good_message(self):
        model.db_connect()
        user1 = User(jid="user1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.waiting_password_reply = True
        account12 = ExampleAccount(user=user1,
                                   name="account12",
                                   jid="account12@jcl.test.com")
        message = Message(from_jid="user1@test.com",
                          to_jid="account11@jcl.test.com",
                          subject="[WRONG MESSAGE]",
                          body="secret")
        _account = self.handler.filter(message, None)
        self.assertEquals(_account, None)
        model.db_disconnect()

    def test_filter_not_password_account(self):
        model.db_connect()
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        message = Message(from_jid="user1@test.com",
                          to_jid="account11@jcl.test.com",
                          subject="[PASSWORD]",
                          body="secret")
        _account = self.handler.filter(message, None)
        self.assertEquals(_account, None)
        model.db_disconnect()

    def test_handle(self):
        model.db_connect()
        user1 = User(jid="user1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = ExampleAccount(user=user1,
                                   name="account12",
                                   jid="account12@jcl.test.com")
        message = Message(from_jid="user1@test.com",
                          to_jid="account11@jcl.test.com",
                          subject="[PASSWORD]",
                          body="secret")
        messages = self.handler.handle(message, Lang.en, account11)
        self.assertEquals(len(messages), 1)
        self.assertEquals(account11.password, "secret")
        model.db_disconnect()

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(PasswordMessageHandler_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
