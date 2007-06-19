# -*- coding: utf-8 -*-
##
## test_feeder.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Aug  9 21:34:26 2006 David Rousselie
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
import threading
import time
import sys

from sqlobject import *
from sqlobject.dbconnection import TheURIOpener

from pyxmpp.message import Message

from jcl.jabber.component import JCLComponent
from jcl.jabber.feeder import FeederComponent, Feeder, Sender, MessageSender, \
    HeadlineSender, FeederHandler
from jcl.model.account import Account, LegacyJID
from jcl.model import account

from jcl.model.tests.account import ExampleAccount, Example2Account
from jcl.jabber.tests.component import JCLComponent_TestCase, MockStream

if sys.platform == "win32":
   DB_PATH = "/c|/temp/jcl_test.db"
else:
   DB_PATH = "/tmp/jcl_test.db"
DB_URL = DB_PATH #+ "?debug=1&debugThreading=1"

class FeederMock(object):
    def feed(self, _account):
        return [("subject", "body")]

class SenderMock(object):
    def __init__(self):
        self.sent = []

    def send(self, _account, data):
        self.sent.append((_account, data))

class FeederComponent_TestCase(JCLComponent_TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        self.comp = FeederComponent("jcl.test.com",
                                    "password",
                                    "localhost",
                                    "5347",
                                    'sqlite://' + DB_URL)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.createTable(ifNotExists = True)
        LegacyJID.createTable(ifNotExists=True)
        ExampleAccount.createTable(ifNotExists = True)
        Example2Account.createTable(ifNotExists = True)
        del account.hub.threadConnection

    def tearDown(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.dropTable(ifExists = True)
        LegacyJID.dropTable(ifExists=True)
        ExampleAccount.dropTable(ifExists = True)
        Example2Account.dropTable(ifExists = True)
        del TheURIOpener.cachedURIs['sqlite://' + DB_URL]
        account.hub.threadConnection.close()
        del account.hub.threadConnection
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)

    def test_run(self):
        self.comp.time_unit = 1
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        run_thread = threading.Thread(target = self.comp.run, \
                                      name = "run_thread")
        run_thread.start()
        time.sleep(1)
        self.comp.running = False
        self.assertTrue(self.comp.stream.connection_started)
        time.sleep(JCLComponent.timeout + 1)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertTrue(self.comp.stream.connection_stopped)
        if self.comp.queue.qsize():
            raise self.comp.queue.get(0)

    def test_run_ni_handle_tick(self):
        # handle_tick is implemented in FeederComponent
        # so no need to check for NotImplemented raise assertion
        self.assertTrue(True)

    def test_handle_tick(self):
        class AccountFeeder(Feeder):
            def feed(self, _account):
                return [("Simple Message for account " + _account.name,
                            "user_jid: " + _account.user_jid), \
                            ("Simple Message for account " + _account.name, \
                            "jid: " + _account.jid)]

        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        self.comp.handler.feeder = AccountFeeder(self.comp)
        self.comp.handler.sender = MessageSender(self.comp)
        self.comp.handle_tick()

        messages_sent = self.comp.stream.sent
        self.assertEquals(len(messages_sent), 6)
        self.assertEqual(messages_sent[0].get_from(), "account11@jcl.test.com")
        self.assertEqual(messages_sent[0].get_to(), "user1@test.com")
        self.assertEqual(messages_sent[0].get_subject(), \
            "Simple Message for account account11")
        self.assertEqual(messages_sent[0].get_body(), \
            "user_jid: user1@test.com")
        self.assertEqual(messages_sent[1].get_from(), "account11@jcl.test.com")
        self.assertEqual(messages_sent[1].get_to(), "user1@test.com")
        self.assertEqual(messages_sent[1].get_subject(), \
            "Simple Message for account account11")
        self.assertEqual(messages_sent[1].get_body(), \
            "jid: account11@jcl.test.com")

        self.assertEqual(messages_sent[2].get_from(), "account12@jcl.test.com")
        self.assertEqual(messages_sent[2].get_to(), "user1@test.com")
        self.assertEqual(messages_sent[2].get_subject(), \
            "Simple Message for account account12")
        self.assertEqual(messages_sent[2].get_body(), \
            "user_jid: user1@test.com")
        self.assertEqual(messages_sent[3].get_from(), "account12@jcl.test.com")
        self.assertEqual(messages_sent[3].get_to(), "user1@test.com")
        self.assertEqual(messages_sent[3].get_subject(), \
            "Simple Message for account account12")
        self.assertEqual(messages_sent[3].get_body(), \
            "jid: account12@jcl.test.com")

        self.assertEqual(messages_sent[4].get_from(), "account2@jcl.test.com")
        self.assertEqual(messages_sent[4].get_to(), "user2@test.com")
        self.assertEqual(messages_sent[4].get_subject(), \
            "Simple Message for account account2")
        self.assertEqual(messages_sent[4].get_body(), \
            "user_jid: user2@test.com")
        self.assertEqual(messages_sent[5].get_from(), "account2@jcl.test.com")
        self.assertEqual(messages_sent[5].get_to(), "user2@test.com")
        self.assertEqual(messages_sent[5].get_subject(), \
            "Simple Message for account account2")
        self.assertEqual(messages_sent[5].get_body(), \
            "jid: account2@jcl.test.com")

class Feeder_TestCase(unittest.TestCase):
    def test_feed_exist(self):
        feeder = Feeder()
        self.assertRaises(NotImplementedError, feeder.feed, None)

class Sender_TestCase(unittest.TestCase):
    def test_send_exist(self):
        sender = Sender()
        self.assertRaises(NotImplementedError, sender.send, None, None, None)

class MessageSender_TestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        self.comp = FeederComponent("jcl.test.com",
                                    "password",
                                    "localhost",
                                    "5347",
                                    'sqlite://' + DB_URL)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.createTable(ifNotExists = True)
        del account.hub.threadConnection
        self.sender = MessageSender(self.comp)
        self.message_type = None

    def tearDown(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.dropTable(ifExists = True)
        del TheURIOpener.cachedURIs['sqlite://' + DB_URL]
        account.hub.threadConnection.close()
        del account.hub.threadConnection
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)

    def test_send(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        self.sender.send(account11, ("subject", "Body message"))
        self.assertEquals(len(self.comp.stream.sent), 1)
        message = self.comp.stream.sent[0]
        self.assertEquals(message.get_from(), account11.jid)
        self.assertEquals(message.get_to(), account11.user_jid)
        self.assertEquals(message.get_subject(), "subject")
        self.assertEquals(message.get_body(), "Body message")
        self.assertEquals(message.get_type(), self.message_type)
        del account.hub.threadConnection

class HeadlineSender_TestCase(MessageSender_TestCase):
    def setUp(self):
        MessageSender_TestCase.setUp(self)
        self.sender = HeadlineSender(self.comp)
        self.message_type = "headline"

class FeederHandler_TestCase(unittest.TestCase):
    def setUp(self):
        self.handler = FeederHandler(FeederMock(), SenderMock())
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.createTable(ifNotExists = True)
        ExampleAccount.createTable(ifNotExists = True)
        del account.hub.threadConnection

    def tearDown(self):
        self.handler = None
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        ExampleAccount.dropTable(ifExists = True)
        Account.dropTable(ifExists = True)
        del TheURIOpener.cachedURIs['sqlite://' + DB_URL]
        account.hub.threadConnection.close()
        del account.hub.threadConnection
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)

    def test_filter(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account12 = ExampleAccount(user_jid="user2@test.com",
                                   name="account12",
                                   jid="account12@jcl.test.com")
        account11 = ExampleAccount(user_jid="user1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        accounts = self.handler.filter(None, None)
        self.assertEquals(accounts.count(), 2)
        # accounts must be ordered by user_jid
        self.assertEquals(accounts[0].name, "account11")
        self.assertEquals(accounts[1].name, "account12")
        del account.hub.threadConnection

    def test_handle(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = ExampleAccount(user_jid="user1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = ExampleAccount(user_jid="user2@test.com",
                                   name="account12",
                                   jid="account12@jcl.test.com")
        accounts = self.handler.handle(None, None, [account11, account12])
        sent = self.handler.sender.sent
        self.assertEquals(len(sent), 2)
        self.assertEquals(sent[0], (account11, ("subject", "body")))
        self.assertEquals(sent[1], (account12, ("subject", "body")))
        del account.hub.threadConnection

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FeederComponent_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(Feeder_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(Sender_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(MessageSender_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(HeadlineSender_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(FeederHandler_TestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
