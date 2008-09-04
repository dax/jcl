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
import threading
import time

from sqlobject import *

from jcl.jabber.component import JCLComponent
from jcl.jabber.feeder import FeederComponent, Feeder, Sender, MessageSender, \
    HeadlineSender, FeederHandler
from jcl.model.account import Account, LegacyJID, User
import jcl.model as model

from jcl.model.tests.account import ExampleAccount, Example2Account
from jcl.jabber.tests.component import JCLComponent_TestCase, MockStream

from jcl.tests import JCLTestCase

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
        JCLTestCase.setUp(self, tables=[Account, LegacyJID, ExampleAccount,
                                        Example2Account, User])
        self.comp = FeederComponent("jcl.test.com",
                                    "password",
                                    "localhost",
                                    "5347",
                                    None,
                                    None)
        self.comp.time_unit = 0

    def test_run(self):
        def end_run():
            self.comp.running = False
            return
        self.comp.handle_tick = end_run
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.disable_signals()
        run_thread = threading.Thread(target=self.comp.run,
                                      name="run_thread")
        run_thread.start()
        self.comp.wait_event.wait(JCLComponent.timeout)
        run_thread.join(JCLComponent.timeout)
        self.assertTrue(self.comp.stream.connection_started)
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
                         "user_jid: " + _account.user.jid),
                        ("Simple Message for account " + _account.name,
                         "jid: " + _account.jid)]

        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user=User(jid="user2@test.com"),
                           name="account2",
                           jid="account2@jcl.test.com")
        self.comp.handler.feeder = AccountFeeder(self.comp)
        self.comp.handler.sender = MessageSender(self.comp)
        self.comp.handle_tick()

        messages_sent = self.comp.stream.sent
        self.assertEquals(len(messages_sent), 6)
        self.assertEquals(messages_sent[0].get_from(), "account11@jcl.test.com")
        self.assertEquals(messages_sent[0].get_to(), "user1@test.com")
        self.assertEquals(messages_sent[0].get_subject(),
                          "Simple Message for account account11")
        self.assertEquals(messages_sent[0].get_body(),
                          "user_jid: user1@test.com")
        self.assertEquals(messages_sent[1].get_from(), "account11@jcl.test.com")
        self.assertEquals(messages_sent[1].get_to(), "user1@test.com")
        self.assertEquals(messages_sent[1].get_subject(),
                          "Simple Message for account account11")
        self.assertEquals(messages_sent[1].get_body(),
                          "jid: account11@jcl.test.com")

        self.assertEquals(messages_sent[2].get_from(), "account12@jcl.test.com")
        self.assertEquals(messages_sent[2].get_to(), "user1@test.com")
        self.assertEquals(messages_sent[2].get_subject(),
                          "Simple Message for account account12")
        self.assertEquals(messages_sent[2].get_body(),
                          "user_jid: user1@test.com")
        self.assertEquals(messages_sent[3].get_from(), "account12@jcl.test.com")
        self.assertEquals(messages_sent[3].get_to(), "user1@test.com")
        self.assertEquals(messages_sent[3].get_subject(),
                          "Simple Message for account account12")
        self.assertEquals(messages_sent[3].get_body(),
                          "jid: account12@jcl.test.com")

        self.assertEquals(messages_sent[4].get_from(), "account2@jcl.test.com")
        self.assertEquals(messages_sent[4].get_to(), "user2@test.com")
        self.assertEquals(messages_sent[4].get_subject(),
                          "Simple Message for account account2")
        self.assertEquals(messages_sent[4].get_body(),
                          "user_jid: user2@test.com")
        self.assertEquals(messages_sent[5].get_from(), "account2@jcl.test.com")
        self.assertEquals(messages_sent[5].get_to(), "user2@test.com")
        self.assertEquals(messages_sent[5].get_subject(),
                          "Simple Message for account account2")
        self.assertEquals(messages_sent[5].get_body(),
                          "jid: account2@jcl.test.com")

class Feeder_TestCase(unittest.TestCase):
    def test_feed_exist(self):
        feeder = Feeder()
        self.assertRaises(NotImplementedError, feeder.feed, None)

class Sender_TestCase(unittest.TestCase):
    def test_send_exist(self):
        sender = Sender()
        self.assertRaises(NotImplementedError, sender.send, None, None, None)

class MessageSender_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[Account, User])
        self.comp = FeederComponent("jcl.test.com",
                                    "password",
                                    "localhost",
                                    "5347",
                                    None,
                                    None)
        self.sender = MessageSender(self.comp)
        self.message_type = None

    def test_send(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user=User(jid="user1@test.com"),
                            name="account11",
                            jid="account11@jcl.test.com")
        self.sender.send(account11, ("subject", "Body message"))
        self.assertEquals(len(self.comp.stream.sent), 1)
        message = self.comp.stream.sent[0]
        self.assertEquals(message.get_from(), account11.jid)
        self.assertEquals(message.get_to(), account11.user.jid)
        self.assertEquals(message.get_subject(), "subject")
        self.assertEquals(message.get_body(), "Body message")
        self.assertEquals(message.get_type(), self.message_type)
        model.db_disconnect()

    def test_send_closed_connection(self):
        self.comp.stream = None
        model.db_connect()
        account11 = Account(user=User(jid="user1@test.com"),
                            name="account11",
                            jid="account11@jcl.test.com")
        self.sender.send(account11, ("subject", "Body message"))

class HeadlineSender_TestCase(MessageSender_TestCase):
    def setUp(self):
        MessageSender_TestCase.setUp(self)
        self.sender = HeadlineSender(self.comp)
        self.message_type = "headline"

class FeederHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[Account, ExampleAccount, User])
        self.handler = FeederHandler(FeederMock(), SenderMock())

    def test_filter(self):
        model.db_connect()
        account12 = ExampleAccount(user=User(jid="user2@test.com"),
                                   name="account12",
                                   jid="account12@jcl.test.com")
        account11 = ExampleAccount(user=User(jid="user1@test.com"),
                                   name="account11",
                                   jid="account11@jcl.test.com")
        accounts = self.handler.filter(None, None)
        i = 0
        for _account in accounts:
            i += 1
            if i == 1:
                self.assertEquals(_account.name, "account12")
            else:
                self.assertEquals(_account.name, "account11")
        self.assertEquals(i, 2)
        model.db_disconnect()

    def test_handle(self):
        model.db_connect()
        account11 = ExampleAccount(user=User(jid="user1@test.com"),
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = ExampleAccount(user=User(jid="user2@test.com"),
                                   name="account12",
                                   jid="account12@jcl.test.com")
        accounts = self.handler.handle(None, None, [account11, account12])
        sent = self.handler.sender.sent
        self.assertEquals(len(sent), 2)
        self.assertEquals(sent[0], (account11, ("subject", "body")))
        self.assertEquals(sent[1], (account12, ("subject", "body")))
        model.db_disconnect()

    def test_handle_disabled_account(self):
        model.db_connect()
        account11 = ExampleAccount(user=User(jid="user1@test.com"),
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.enabled = False
        account12 = ExampleAccount(user=User(jid="user2@test.com"),
                                   name="account12",
                                   jid="account12@jcl.test.com")
        accounts = self.handler.handle(None, None, [account11, account12])
        sent = self.handler.sender.sent
        self.assertEquals(len(sent), 1)
        self.assertEquals(sent[0], (account12, ("subject", "body")))
        model.db_disconnect()

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(FeederComponent_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(Feeder_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(Sender_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(MessageSender_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(HeadlineSender_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(FeederHandler_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
