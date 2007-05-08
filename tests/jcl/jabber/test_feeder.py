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

from tests.jcl.jabber.test_component import JCLComponent_TestCase, MockStream

from jcl.jabber.component import JCLComponent
from jcl.jabber.feeder import FeederComponent, Feeder, Sender
from jcl.model.account import Account
from jcl.model import account

from tests.jcl.model.account import ExampleAccount, Example2Account

if sys.platform == "win32":
   DB_PATH = "/c|/temp/test.db"
else:
   DB_PATH = "/tmp/test.db"
DB_URL = DB_PATH #+ "?debug=1&debugThreading=1"

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
        ExampleAccount.createTable(ifNotExists = True)
        Example2Account.createTable(ifNotExists = True)
        del account.hub.threadConnection
        
    def tearDown(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.dropTable(ifExists = True)
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
                return ["user_jid: " + _account.user_jid, \
                        "jid: " + _account.jid]

        class MessageAccountSender(Sender):
            def send(self, _account, data):
                self.component.stream.send(Message(\
                    from_jid = _account.jid, \
                    to_jid = _account.user_jid, \
                    subject = "Simple Message for account " + _account.name, \
                    body = data))
                
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
        self.comp.feeder = AccountFeeder(self.comp)
        self.comp.sender = MessageAccountSender(self.comp)
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
        self.assertRaises(NotImplementedError, sender.send, None, None)
