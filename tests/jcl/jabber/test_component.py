# -*- coding: utf-8 -*-
##
## test_component.py
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

import thread
import threading
import time
import sys
import os

from sqlobject import *
from sqlobject.dbconnection import TheURIOpener

from pyxmpp.iq import Iq
from pyxmpp.stanza import Stanza
from pyxmpp.presence import Presence
from pyxmpp.message import Message

from jcl.jabber.component import JCLComponent
from jcl.model import account
from jcl.model.account import Account
from jcl.lang import Lang

DB_PATH = "/tmp/test.db"
DB_URL = DB_PATH# + "?debug=1&debugThreading=1"

class MockStream(object):
    def __init__(self, \
                 jid = "",
                 secret = "",
                 server = "",
                 port = "",
                 keepalive = True):
        self.sent = []
        self.connection_started = False
        self.connection_stopped = False
        self.eof = False
        self.socket = []

    def send(self, iq):
        self.sent.append(iq)

    def set_iq_set_handler(self, iq_type, ns, handler):
        if not iq_type in ["query"]:
            raise Exception("IQ type unknown: " + iq_type)
        if not ns in ["jabber:iq:version", \
                      "jabber:iq:register", \
                      "http://jabber.org/protocol/disco#items", \
                      "http://jabber.org/protocol/disco#info"]:
            raise Exception("Unknown namespace: " + ns)
        if handler is None:
            raise Exception("Handler must not be None")

    set_iq_get_handler = set_iq_set_handler

    def set_presence_handler(self, status, handler):
        if not status in ["available", \
                          "unavailable", \
                          "probe", \
                          "subscribe", \
                          "subscribed", \
                          "unsubscribe", \
                          "unsubscribed"]:
            raise Exception("Status unknown: " + status)
        if handler is None:
            raise Exception("Handler must not be None")

    def set_message_handler(self, msg_type, handler):
        if not msg_type in ["normal"]:
            raise Exception("Message type unknown: " + msg_type)
        if handler is None:
            raise Exception("Handler must not be None")

    def connect(self):
        self.connection_started = True

    def disconnect(self):
        self.connection_stopped = True

    def loop_iter(self, timeout):
        time.sleep(timeout)

    def close(self):
        pass

class MockStreamNoConnect(MockStream):
    def connect(self):
        self.connection_started = True
        self.eof = True

class JCLComponent_TestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 'sqlite://' + DB_URL)
        self.max_tick_count = 2
        self.saved_time_handler = None

    def tearDown(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.dropTable(ifExists = True)
        del TheURIOpener.cachedURIs['sqlite://' + DB_URL]
        account.hub.threadConnection.close()
        del account.hub.threadConnection
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)

    def test_constructor(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.assertTrue(Account._connection.tableExists("account"))
        del account.hub.threadConnection

    def __comp_run(self):
        try:
            self.comp.run()
        except:
            # Ignore exception, might be obtain from self.comp.queue
            pass

    def __comp_time_handler(self):
        try:
            self.saved_time_handler()
        except:
            # Ignore exception, might be obtain from self.comp.queue
            pass

    def test_run(self):
        self.comp.time_unit = 1
        # Do not loop, handle_tick is virtual
        # Tests in subclasses might be more precise
        self.comp.stream = MockStreamNoConnect()
        self.comp.stream_class = MockStreamNoConnect
        self.comp.run()
        self.assertTrue(self.comp.stream.connection_started)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertTrue(self.comp.stream.connection_stopped)
        if self.comp.queue.qsize():
            raise self.comp.queue.get(0)

    def test_run_ni_handle_tick(self):
        self.comp.time_unit = 1
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.saved_time_handler = self.comp.time_handler
        self.comp.time_handler = self.__comp_time_handler
        run_thread = threading.Thread(target = self.__comp_run, \
                                      name = "run_thread")
        run_thread.start()
        time.sleep(1)
        self.comp.running = False
        self.assertTrue(self.comp.stream.connection_started)
        time.sleep(1)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertTrue(self.comp.stream.connection_stopped)
        self.assertEquals(self.comp.queue.qsize(), 1)
        self.assertTrue(isinstance(self.comp.queue.get(0), \
                                   NotImplementedError))

    def test_run_go_offline(self):
        ## TODO : verify offline stanza are sent
        pass

    def __handle_tick_test_time_handler(self):
        self.max_tick_count -= 1
        if self.max_tick_count == 0:
            self.comp.running = False

    def test_time_handler(self):
        self.comp.time_unit = 1
        self.max_tick_count = 2
        self.comp.handle_tick = self.__handle_tick_test_time_handler
        self.comp.stream = MockStream()
        self.comp.running = True
        self.comp.time_handler()
        self.assertEquals(self.max_tick_count, 0)
        self.assertFalse(self.comp.running)

    def test_authenticated_handler(self):
        self.comp.stream = MockStream()
        self.comp.authenticated()
        self.assertTrue(True)

    def test_authenticated_send_probe(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "test1@test.com", \
                            name = "test11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "test1@test.com", \
                            name = "test12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "test2@test.com", \
                           name = "test2", \
                           jid = "account2@jcl.test.com")
        del account.hub.threadConnection
        self.comp.stream = stream = MockStream()
        self.comp.authenticated()

        presence_sent = stream.sent
        self.assertEqual(len(presence_sent), 5)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == "jcl.test.com"]), \
                         2)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "test1@test.com"]), \
                         3)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "test2@test.com"]), \
                         2)

    def test_signal_handler(self):
        self.comp.running = True
        self.comp.signal_handler(42, None)
        self.assertFalse(self.comp.running)

    def test_disco_get_info(self):
        disco_info = self.comp.disco_get_info(None, None)
        self.assertTrue(disco_info.has_feature("jabber:iq:version"))
        self.assertTrue(disco_info.has_feature("jabber:iq:register"))

    def test_disco_get_info_node(self):
        disco_info = self.comp.disco_get_info("node_test", None)
        self.assertFalse(disco_info.has_feature("jabber:iq:version"))
        self.assertTrue(disco_info.has_feature("jabber:iq:register"))

    def test_disco_get_items_no_node(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account1 = Account(user_jid = "user1@test.com", \
                           name = "account1", \
                           jid = "account1@jcl.test.com")
        del account.hub.threadConnection
        info_query = Iq(stanza_type = "get", \
                        from_jid = "user1@test.com")
        disco_items = self.comp.disco_get_items(None, info_query)
        self.assertEquals(len(disco_items.get_items()), 1)
        disco_item = disco_items.get_items()[0]
        self.assertEquals(disco_item.get_jid(), account1.jid)
        self.assertEquals(disco_item.get_node(), account1.name)
        self.assertEquals(disco_item.get_name(), account1.long_name)

    def test_disco_get_items_with_node(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account1 = Account(user_jid = "user1@test.com", \
                           name = "account1", \
                           jid = "account1@jcl.test.com")
        del account.hub.threadConnection
        info_query = Iq(stanza_type = "get", \
                        from_jid = "user1@test.com")
        disco_items = self.comp.disco_get_items("account1", info_query)
        self.assertEquals(disco_items.get_items(), [])

    def test_get_reg_form(self):
##        self.comp.get_reg_form(Lang.en, Account)
        # TODO
        self.assertTrue(True)

    def test_get_reg_form_init(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account1 = Account(user_jid = "", name = "", jid = "")
        del account.hub.threadConnection
##        self.comp.get_reg_form_init(Lang.en, account1)
        # TODO
        self.assertTrue(True)

    def test_handle_get_version(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.handle_get_version(Iq(stanza_type = "get", \
                                        from_jid = "user1@test.com"))
        self.assertEquals(len(self.comp.stream.sent), 1)
        iq_sent = self.comp.stream.sent[0]
        self.assertEquals(iq_sent.get_to(), "user1@test.com")
        self.assertEquals(len(iq_sent.xpath_eval("*/*")), 2)
        name_nodes = iq_sent.xpath_eval("jiv:query/jiv:name", \
                                        {"jiv" : "jabber:iq:version"})
        self.assertEquals(len(name_nodes), 1)
        self.assertEquals(name_nodes[0].content, self.comp.name)
        version_nodes = iq_sent.xpath_eval("jiv:query/jiv:version", \
                                           {"jiv" : "jabber:iq:version"})
        self.assertEquals(len(version_nodes), 1)
        self.assertEquals(version_nodes[0].content, self.comp.version)

    def test_handle_get_register_new(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.handle_get_register(Iq(stanza_type = "get", \
                                         from_jid = "user1@test.com", \
                                         to_jid = "jcl.test.com"))
        self.assertEquals(len(self.comp.stream.sent), 1)
        iq_sent = self.comp.stream.sent[0]
        self.assertEquals(iq_sent.get_to(), "user1@test.com")
        titles = iq_sent.xpath_eval("jir:query/jxd:x/jxd:title", \
                                    {"jir" : "jabber:iq:register", \
                                     "jxd" : "jabber:x:data"})
        self.assertEquals(len(titles), 1)
        self.assertEquals(titles[0].content, \
                          Lang.en.register_title)
        instructions = iq_sent.xpath_eval("jir:query/jxd:x/jxd:instructions", \
                                          {"jir" : "jabber:iq:register", \
                                           "jxd" : "jabber:x:data"})
        self.assertEquals(len(instructions), 1)
        self.assertEquals(instructions[0].content, \
                          Lang.en.register_instructions)
        fields = iq_sent.xpath_eval("jir:query/jxd:x/jxd:field", \
                                    {"jir" : "jabber:iq:register", \
                                     "jxd" : "jabber:x:data"})
        self.assertEquals(len(fields), 1)
        self.assertEquals(len([field
                               for field in fields \
                               if field.prop("type") == "text-single" \
                               and field.prop("var") == "name" \
                               and field.prop("label") == \
                               Lang.en.account_name]), \
                          1)


    def test_handle_get_register_exist(self):
        pass

    def test_handle_set_register(self):
        pass

    def test_handle_presence_available_to_component(self):
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
        del account.hub.threadConnection
## TODO: "online"  exist ?
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            show = "online", \
            from_jid = "user1@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 3)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "user1@test.com"]), \
                          3)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == \
                              "jcl.test.com" \
                              and presence.get_show() == "online"]), \
                          1)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == \
                              "account11@jcl.test.com" \
                              and presence.get_show() == "online"]), \
                          1)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == \
                              "account12@jcl.test.com" \
                              and presence.get_show() == "online"]), \
                          1)

    def test_handle_presence_available_to_account(self):
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
        del account.hub.threadConnection
## TODO: "online"  exist ?
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            show = "online", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "account11@jcl.test.com")
        self.assertEqual(presence_sent[0].get_show(), "online")

    def test_handle_presence_available_to_account_live_password(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account11.store_password = False
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        del account.hub.threadConnection
## TODO: "online"  exist ?
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            show = "online", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        messages_sent = self.comp.stream.sent
        self.assertEqual(len(messages_sent), 1)
        presence = messages_sent[0]
        self.assertTrue(presence is not None)
        self.assertEqual(presence.get_show(), "online")
        self.assertEqual(presence.get_from_jid(), "account11@jcl.test.com")
        self.assertEqual(presence.get_to_jid(), "user1@test.com")
        
# Use it in real live password implementation
#     def test_handle_presence_available_to_account_live_password(self):
#         self.comp.stream = MockStream()
#         self.comp.stream_class = MockStream
#         account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
#         account11 = Account(user_jid = "user1@test.com", \
#                             name = "account11", \
#                             jid = "account11@jcl.test.com")
#         account11.store_password = False
#         account12 = Account(user_jid = "user1@test.com", \
#                             name = "account12", \
#                             jid = "account12@jcl.test.com")
#         account2 = Account(user_jid = "user2@test.com", \
#                            name = "account2", \
#                            jid = "account2@jcl.test.com")
#         del account.hub.threadConnection
# ## TODO: "online"  exist ?
#         self.comp.handle_presence_available(Presence(\
#             stanza_type = "available", \
#             show = "online", \
#             from_jid = "user1@test.com",\
#             to_jid = "account11@jcl.test.com"))
#         messages_sent = self.comp.stream.sent
#         self.assertEqual(len(messages_sent), 2)
#         password_message = None
#         presence = None
#         for message in messages_sent:
#             if isinstance(message, Message):
#                 password_message = message
#             elif isinstance(message, Presence):
#                 presence = message
#         self.assertTrue(password_message is not None)
#         self.assertTrue(presence is not None)
#         self.assertEqual(presence.get_show(), "online")
#         self.assertEqual(presence.get_from_jid(), "account11@jcl.test.com")
#         self.assertEqual(presence.get_to_jid(), "user1@test.com")
        
#         self.assertEqual(unicode(password_message.get_from_jid()), \
#                          "account11@jcl.test.com")
#         self.assertEqual(unicode(password_message.get_to_jid()), \
#                          "user1@test.com")
#         self.assertEqual(password_message.get_subject(), \
#                          "[PASSWORD] Password request")
#         self.assertEqual(password_message.get_body(), None)

    def test_handle_presence_unavailable_to_component(self):
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
        del account.hub.threadConnection
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type = "unavailable", \
            from_jid = "user1@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 3)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "user1@test.com"]), \
                          3)
        self.assertEqual(\
            len([presence \
                 for presence in presence_sent \
                 if presence.get_from_jid() == \
                 "jcl.test.com" \
                 and presence.xpath_eval("@type")[0].get_content() \
                 == "unavailable"]), \
            1)
        self.assertEqual(\
            len([presence \
                 for presence in presence_sent \
                 if presence.get_from_jid() == \
                 "account11@jcl.test.com" \
                 and presence.xpath_eval("@type")[0].get_content() \
                 == "unavailable"]), \
            1)
        self.assertEqual(\
            len([presence \
                 for presence in presence_sent \
                 if presence.get_from_jid() == \
                 "account12@jcl.test.com" \
                 and presence.xpath_eval("@type")[0].get_content() \
                 == "unavailable"]), \
            1)


    def test_handle_presence_unavailable_to_account(self):
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
        del account.hub.threadConnection
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type = "unavailable", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "account11@jcl.test.com")
        self.assertEqual(\
            presence_sent[0].xpath_eval("@type")[0].get_content(), \
            "unavailable")

    def test_handle_presence_subscribe_to_component(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.handle_presence_subscribe(Presence(\
            stanza_type = "subscribe", \
            from_jid = "user1@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "jcl.test.com")
        self.assertEqual(\
            presence_sent[0].xpath_eval("@type")[0].get_content(), \
            "subscribed")

    def test_handle_presence_subscribe_to_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.handle_presence_subscribe(Presence(\
            stanza_type = "subscribe", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "account11@jcl.test.com")
        self.assertEqual(\
            presence_sent[0].xpath_eval("@type")[0].get_content(), \
            "subscribed")

    def test_handle_presence_subscribed(self):
        pass

    def test_handle_presence_unsubscribe(self):
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
        del account.hub.threadConnection
        self.comp.handle_presence_unsubscribe(Presence(\
            stanza_type = "unsubscribe", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 2)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "user1@test.com"]), \
                          2)
        self.assertEqual(\
            len([presence \
                 for presence in presence_sent \
                 if presence.get_from_jid() == \
                 "account11@jcl.test.com" \
                 and presence.xpath_eval("@type")[0].get_content() \
                 == "unsubscribe"]), \
            1)
        self.assertEqual(\
            len([presence \
                 for presence in presence_sent \
                 if presence.get_from_jid() == \
                 "account11@jcl.test.com" \
                 and presence.xpath_eval("@type")[0].get_content() \
                 == "unsubscribed"]), \
            1)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.assertEquals(self.comp.account_class.select(\
            self.comp.account_class.q.user_jid == "user1@test.com" \
            and self.comp.account_class.q.name == "account11").count(), \
                          0)
        del account.hub.threadConnection

    def test_handle_presence_unsubscribed(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.handle_presence_unsubscribed(Presence(\
            stanza_type = "unsubscribed", \
            from_jid = "user1@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "jcl.test.com")
        self.assertEqual(\
            presence_sent[0].xpath_eval("@type")[0].get_content(), \
            "unavailable")

    def test_handle_message_password(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account11.waiting_password_reply = True
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        del account.hub.threadConnection
        self.comp.handle_message(Message(\
            from_jid = "user1@test.com", \
            to_jid = "account11@jcl.test.com", \
            subject = "[PASSWORD]", \
            body = "secret"))
        messages_sent = self.comp.stream.sent
        self.assertEqual(len(messages_sent), 0)

# TODO Use it with real implementation live password
#     def test_handle_message_password(self):
#         self.comp.stream = MockStream()
#         self.comp.stream_class = MockStream
#         account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
#         account11 = Account(user_jid = "user1@test.com", \
#                             name = "account11", \
#                             jid = "account11@jcl.test.com")
#         account11.waiting_password_reply = True
#         account12 = Account(user_jid = "user1@test.com", \
#                             name = "account12", \
#                             jid = "account12@jcl.test.com")
#         account2 = Account(user_jid = "user2@test.com", \
#                            name = "account2", \
#                            jid = "account2@jcl.test.com")
#         del account.hub.threadConnection
#         self.comp.handle_message(Message(\
#             from_jid = "user1@test.com", \
#             to_jid = "account11@jcl.test.com", \
#             subject = "[PASSWORD]", \
#             body = "secret"))
#         messages_sent = self.comp.stream.sent
#         self.assertEqual(len(messages_sent), 1)
#         self.assertEqual(messages_sent[0].get_to(), "user1@test.com")
#         self.assertEqual(messages_sent[0].get_from(), "account11@jcl.test.com")
#         self.assertEqual(account11.password, "secret")
#         self.assertEqual(account11.waiting_password_reply, False)
#         self.assertEqual(messages_sent[0].get_subject(), \
#             "Password will be kept during your Jabber session")
#         self.assertEqual(messages_sent[0].get_body(), \
#             "Password will be kept during your Jabber session")
        
    def test_handle_tick(self):
        self.assertRaises(NotImplementedError, self.comp.handle_tick)


