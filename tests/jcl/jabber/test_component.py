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

import pyxmpp.error as error
from pyxmpp.iq import Iq
from pyxmpp.stanza import Stanza
from pyxmpp.presence import Presence
from pyxmpp.message import Message

from jcl.jabber.component import JCLComponent
from jcl.model import account
from jcl.model.account import Account
from jcl.lang import Lang
from jcl.jabber.x import DataForm

from tests.jcl.model.account import AccountExample

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
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.createTable(ifNotExists = True)
        AccountExample.createTable(ifNotExists = True)
        del account.hub.threadConnection
        self.max_tick_count = 1
        self.saved_time_handler = None

    def tearDown(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        AccountExample.dropTable(ifExists = True)
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
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.time_unit = 1
        self.max_tick_count = 1
        self.comp.handle_tick = self.__handle_tick_test_time_handler
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "test1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "test1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "test2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        del account.hub.threadConnection
        self.comp.run()
        self.assertTrue(self.comp.stream.connection_started)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertTrue(self.comp.stream.connection_stopped)
        if self.comp.queue.qsize():
            raise self.comp.queue.get(0)
        self.assertEquals(len(self.comp.stream.sent), 5)
        presence = self.comp.stream.sent[0]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "jcl.test.com")
        self.assertEquals(presence.get_to(), "test1@test.com")
        self.assertEquals(presence.get_node().prop("type"), "unavailable")
        presence = self.comp.stream.sent[1]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "account11@jcl.test.com")
        self.assertEquals(presence.get_to(), "test1@test.com")
        self.assertEquals(presence.get_node().prop("type"), "unavailable")
        presence = self.comp.stream.sent[2]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "account12@jcl.test.com")
        self.assertEquals(presence.get_to(), "test1@test.com")
        self.assertEquals(presence.get_node().prop("type"), "unavailable")
        presence = self.comp.stream.sent[3]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "jcl.test.com")
        self.assertEquals(presence.get_to(), "test2@test.com")
        self.assertEquals(presence.get_node().prop("type"), "unavailable")
        presence = self.comp.stream.sent[4]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "account2@jcl.test.com")
        self.assertEquals(presence.get_to(), "test2@test.com")
        self.assertEquals(presence.get_node().prop("type"), "unavailable")
        
    def __handle_tick_test_time_handler(self):
        self.max_tick_count -= 1
        if self.max_tick_count == 0:
            self.comp.running = False

    def test_time_handler(self):
        self.comp.time_unit = 1
        self.max_tick_count = 1
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
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "test1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "test2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        del account.hub.threadConnection
        self.comp.stream = MockStream()
        self.comp.authenticated()
        self.assertEqual(len(self.comp.stream.sent), 5)
        presence = self.comp.stream.sent[0]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "jcl.test.com")
        self.assertEquals(presence.get_to(), "test1@test.com")
        self.assertEquals(presence.get_node().prop("type"), "probe")
        presence = self.comp.stream.sent[1]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "account11@jcl.test.com")
        self.assertEquals(presence.get_to(), "test1@test.com")
        self.assertEquals(presence.get_node().prop("type"), "probe")
        presence = self.comp.stream.sent[2]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "account12@jcl.test.com")
        self.assertEquals(presence.get_to(), "test1@test.com")
        self.assertEquals(presence.get_node().prop("type"), "probe")
        presence = self.comp.stream.sent[3]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "jcl.test.com")
        self.assertEquals(presence.get_to(), "test2@test.com")
        self.assertEquals(presence.get_node().prop("type"), "probe")
        presence = self.comp.stream.sent[4]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_from(), "account2@jcl.test.com")
        self.assertEquals(presence.get_to(), "test2@test.com")
        self.assertEquals(presence.get_node().prop("type"), "probe")

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
        self.assertEquals(fields[0].prop("type"), "text-single")
        self.assertEquals(fields[0].prop("var"), "name")
        self.assertEquals(fields[0].prop("label"), Lang.en.account_name)
        self.assertEquals(fields[0].children.name, "required")

    def test_handle_get_register_new_complex(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.default_account_class = AccountExample
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
        self.assertEquals(len(fields), 6)
        self.assertEquals(fields[0].prop("type"), "text-single")
        self.assertEquals(fields[0].prop("var"), "name")
        self.assertEquals(fields[0].prop("label"), Lang.en.account_name)
        self.assertEquals(fields[0].children.name, "required")

        self.assertEquals(fields[1].prop("type"), "text-single")
        self.assertEquals(fields[1].prop("var"), "login")
        self.assertEquals(fields[1].prop("label"), "login")
        self.assertEquals(fields[0].children.name, "required")

        self.assertEquals(fields[2].prop("type"), "text-private")
        self.assertEquals(fields[2].prop("var"), "password")
        self.assertEquals(fields[2].prop("label"), "password")

        self.assertEquals(fields[3].prop("type"), "boolean")
        self.assertEquals(fields[3].prop("var"), "store_password")
        self.assertEquals(fields[3].prop("label"), "store_password")

        self.assertEquals(fields[4].prop("type"), "list-single")
        self.assertEquals(fields[4].prop("var"), "test_enum")
        self.assertEquals(fields[4].prop("label"), "test_enum")
        # TODO : correct xpath expression (field[4])
        options = iq_sent.xpath_eval("jir:query/jxd:x/jxd:field/jxd:option", \
                                     {"jir" : "jabber:iq:register", \
                                      "jxd" : "jabber:x:data"})

        self.assertEquals(options[0].prop("label"), "choice1")
        self.assertEquals(options[0].children.content, "choice1")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[1].prop("label"), "choice2")
        self.assertEquals(options[1].children.content, "choice2")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[2].prop("label"), "choice3")
        self.assertEquals(options[2].children.content, "choice3")
        self.assertEquals(options[2].children.name, "value")

        self.assertEquals(fields[5].prop("type"), "text-single")
        self.assertEquals(fields[5].prop("var"), "test_int")
        self.assertEquals(fields[5].prop("label"), "test_int")

    def test_handle_get_register_exist(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "user1@test.com", \
                           name = "account11", \
                           jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                           name = "account12", \
                           jid = "account12@jcl.test.com")
        account21 = Account(user_jid = "user1@test.com", \
                           name = "account21", \
                           jid = "account21@jcl.test.com")
        del account.hub.threadConnection
        self.comp.handle_get_register(Iq(stanza_type = "get", \
                                         from_jid = "user1@test.com", \
                                         to_jid = "account11@jcl.test.com"))
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
        self.assertEquals(fields[0].prop("type"), "hidden")
        self.assertEquals(fields[0].prop("var"), "name")
        self.assertEquals(fields[0].prop("label"), Lang.en.account_name)
        self.assertEquals(fields[0].children.next.name, "required")
        value = iq_sent.xpath_eval("jir:query/jxd:x/jxd:field/jxd:value", \
                                   {"jir" : "jabber:iq:register", \
                                    "jxd" : "jabber:x:data"})
        self.assertEquals(len(value), 1)
        self.assertEquals(value[0].content, "account11")

    def test_handle_get_register_exist_complex(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account1 = AccountExample(user_jid = "user1@test.com", \
                                  name = "account1", \
                                  jid = "account1@jcl.test.com", \
                                  login = "mylogin", \
                                  password = "mypassword", \
                                  store_password = False, \
                                  test_enum = "choice3", \
                                  test_int = 21)
        account11 = AccountExample(user_jid = "user1@test.com", \
                                   name = "account11", \
                                   jid = "account11@jcl.test.com", \
                                   login = "mylogin", \
                                   password = "mypassword", \
                                   store_password = False, \
                                   test_enum = "choice3", \
                                   test_int = 21)
        account21 = AccountExample(user_jid = "user2@test.com", \
                                   name = "account21", \
                                   jid = "account21@jcl.test.com", \
                                   login = "mylogin", \
                                   password = "mypassword", \
                                   store_password = False, \
                                   test_enum = "choice3", \
                                   test_int = 21)
        del account.hub.threadConnection
        self.comp.handle_get_register(Iq(stanza_type = "get", \
                                         from_jid = "user1@test.com", \
                                         to_jid = "account1@jcl.test.com"))
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
        self.assertEquals(len(fields), 6)
        field = fields[0]
        self.assertEquals(field.prop("type"), "hidden")
        self.assertEquals(field.prop("var"), "name")
        self.assertEquals(field.prop("label"), Lang.en.account_name)
        self.assertEquals(field.children.name, "value")
        self.assertEquals(field.children.content, "account1")
        self.assertEquals(field.children.next.name, "required")
        field = fields[1]
        self.assertEquals(field.prop("type"), "text-single")
        self.assertEquals(field.prop("var"), "login")
        self.assertEquals(field.prop("label"), "login")
        self.assertEquals(field.children.name, "value")
        self.assertEquals(field.children.content, "mylogin")
        self.assertEquals(field.children.next.name, "required")
        field = fields[2]
        self.assertEquals(field.prop("type"), "text-private")
        self.assertEquals(field.prop("var"), "password")
        self.assertEquals(field.prop("label"), "password")
        self.assertEquals(field.children.name, "value")
        self.assertEquals(field.children.content, "mypassword")
        field = fields[3]
        self.assertEquals(field.prop("type"), "boolean")
        self.assertEquals(field.prop("var"), "store_password")
        self.assertEquals(field.prop("label"), "store_password")
        self.assertEquals(field.children.name, "value")
        self.assertEquals(field.children.content, "False")
        field = fields[4]
        self.assertEquals(field.prop("type"), "list-single")
        self.assertEquals(field.prop("var"), "test_enum")
        self.assertEquals(field.prop("label"), "test_enum")
        self.assertEquals(field.children.name, "value")
        self.assertEquals(field.children.content, "choice3")
        # TODO : correct xpath expression (field[4])
        options = iq_sent.xpath_eval("jir:query/jxd:x/jxd:field/jxd:option", \
                                     {"jir" : "jabber:iq:register", \
                                      "jxd" : "jabber:x:data"})

        self.assertEquals(options[0].prop("label"), "choice1")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[0].children.content, "choice1")
        self.assertEquals(options[1].prop("label"), "choice2")
        self.assertEquals(options[1].children.content, "choice2")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[2].prop("label"), "choice3")
        self.assertEquals(options[2].children.content, "choice3")
        self.assertEquals(options[2].children.name, "value")

        field = fields[5]
        self.assertEquals(field.prop("type"), "text-single")
        self.assertEquals(field.prop("var"), "test_int")
        self.assertEquals(field.prop("label"), "test_int")
        self.assertEquals(field.children.name, "value")
        self.assertEquals(field.children.content, "21")

    def test_handle_set_register_new(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        x_data = DataForm()
        x_data.xmlns = "jabber:x:data"
        x_data.type = "submit"
        x_data.add_field(field_type = "text-single", \
                         var = "name", \
                         value = "account1")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.attach_xml(query)
        self.comp.handle_set_register(iq_set)

        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        accounts = self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com" \
            and self.comp.default_account_class.q.name == "account1")
        self.assertEquals(accounts.count(), 1)
        _account = accounts[0]
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        del account.hub.threadConnection
        
        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 4)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com")
        self.assertEquals(iq_result.get_to(), "user1@test.com")

        presence_component = stanza_sent[1]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "jcl.test.com")
        self.assertEquals(presence_component.get_to(), "user1@test.com")
        self.assertEquals(presence_component.get_node().prop("type"), \
                          "subscribe")
        
        message = stanza_sent[2]
        self.assertTrue(isinstance(message, Message))
        self.assertEquals(message.get_from(), "jcl.test.com")
        self.assertEquals(message.get_to(), "user1@test.com")
        self.assertEquals(message.get_subject(), \
                          _account.get_new_message_subject(Lang.en))
        self.assertEquals(message.get_body(), \
                          _account.get_new_message_body(Lang.en))

        presence_account = stanza_sent[3]
        self.assertTrue(isinstance(presence_account, Presence))
        self.assertEquals(presence_account.get_from(), "account1@jcl.test.com")
        self.assertEquals(presence_account.get_to(), "user1@test.com")
        self.assertEquals(presence_account.get_node().prop("type"), \
                          "subscribe")

    def test_handle_set_register_new_complex(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_factory = (lambda user_jid, name, jid, x_data: \
                                     AccountExample(user_jid = user_jid, \
                                                    name = name, \
                                                    jid = jid))
        x_data = DataForm()
        x_data.xmlns = "jabber:x:data"
        x_data.type = "submit"
        x_data.add_field(field_type = "text-single", \
                         var = "name", \
                         value = "account1")
        x_data.add_field(field_type = "text-single", \
                         var = "login", \
                         value = "mylogin")
        x_data.add_field(field_type = "text-private", \
                         var = "password", \
                         value = "mypassword")
        x_data.add_field(field_type = "boolean", \
                         var = "store_password", \
                         value = "false")
        x_data.add_field(field_type = "list-single", \
                         var = "test_enum", \
                         value = "choice3")
        x_data.add_field(field_type = "text-single", \
                         var = "test_int", \
                         value = "43")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.attach_xml(query)
        self.comp.handle_set_register(iq_set)

        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        accounts = self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com" \
            and self.comp.default_account_class.q.name == "account1")
        self.assertEquals(accounts.count(), 1)
        _account = accounts[0]
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        self.assertEquals(_account.login, "mylogin")
        self.assertEquals(_account.password, "mypassword")
        self.assertFalse(_account.store_password)
        self.assertEquals(_account.test_enum, "choice3")
        self.assertEquals(_account.test_int, 43)
        del account.hub.threadConnection
        
        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 4)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com")
        self.assertEquals(iq_result.get_to(), "user1@test.com")

        presence_component = stanza_sent[1]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "jcl.test.com")
        self.assertEquals(presence_component.get_to(), "user1@test.com")
        self.assertEquals(presence_component.get_node().prop("type"), \
                          "subscribe")
        
        message = stanza_sent[2]
        self.assertTrue(isinstance(message, Message))
        self.assertEquals(message.get_from(), "jcl.test.com")
        self.assertEquals(message.get_to(), "user1@test.com")
        self.assertEquals(message.get_subject(), \
                          _account.get_new_message_subject(Lang.en))
        self.assertEquals(message.get_body(), \
                          _account.get_new_message_body(Lang.en))

        presence_account = stanza_sent[3]
        self.assertTrue(isinstance(presence_account, Presence))
        self.assertEquals(presence_account.get_from(), "account1@jcl.test.com")
        self.assertEquals(presence_account.get_to(), "user1@test.com")
        self.assertEquals(presence_account.get_node().prop("type"), \
                          "subscribe")        

    def test_handle_set_register_new_default_values(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_factory = (lambda user_jid, name, jid, x_data: \
                                     AccountExample(user_jid = user_jid, \
                                                    name = name, \
                                                    jid = jid))
        x_data = DataForm()
        x_data.xmlns = "jabber:x:data"
        x_data.type = "submit"
        x_data.add_field(field_type = "text-single", \
                         var = "name", \
                         value = "account1")
        x_data.add_field(field_type = "text-single", \
                         var = "login", \
                         value = "mylogin")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.attach_xml(query)
        self.comp.handle_set_register(iq_set)

        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        accounts = self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com" \
            and self.comp.default_account_class.q.name == "account1")
        self.assertEquals(accounts.count(), 1)
        _account = accounts[0]
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        self.assertEquals(_account.login, "mylogin")
        self.assertEquals(_account.password, None)
        self.assertTrue(_account.store_password)
        self.assertEquals(_account.test_enum, "choice2")
        self.assertEquals(_account.test_int, 44)
        del account.hub.threadConnection

    def test_handle_set_register_new_name_mandatory(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        x_data = DataForm()
        x_data.xmlns = "jabber:x:data"
        x_data.type = "submit"
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.attach_xml(query)
        self.comp.handle_set_register(iq_set)

        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        accounts = self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com" \
            and self.comp.default_account_class.q.name == "account1")
        self.assertEquals(accounts.count(), 0)
        del account.hub.threadConnection

        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 1)
        self.assertTrue(isinstance(stanza_sent[0], Iq))
        self.assertEquals(stanza_sent[0].get_node().prop("type"), "error")
        stanza_error = stanza_sent[0].get_error()
        self.assertEquals(stanza_error.get_condition().name, \
                          "not-acceptable")
        self.assertEquals(stanza_error.get_text(), \
                          Lang.en.mandatory_field % ("name"))

    def test_handle_set_register_new_field_mandatory(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_factory = (lambda user_jid, name, jid, x_data: \
                                     AccountExample(user_jid = user_jid, \
                                                    name = name, \
                                                    jid = jid))
        x_data = DataForm()
        x_data.xmlns = "jabber:x:data"
        x_data.type = "submit"
        x_data.add_field(field_type = "text-single", \
                         var = "name", \
                         value = "account1")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.attach_xml(query)
        self.comp.handle_set_register(iq_set)

        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        accounts = self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com" \
            and self.comp.default_account_class.q.name == "account1")
        self.assertEquals(accounts.count(), 0)
        del account.hub.threadConnection

        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 1)
        self.assertTrue(isinstance(stanza_sent[0], Iq))
        self.assertEquals(stanza_sent[0].get_node().prop("type"), "error")
        stanza_error = stanza_sent[0].get_error()
        self.assertEquals(stanza_error.get_condition().name, \
                          "not-acceptable")
        self.assertEquals(stanza_error.get_text(), \
                          Lang.en.mandatory_field % ("login"))

    def test_handle_set_register_update_complex(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        existing_account = AccountExample(user_jid = "user1@test.com", \
                                          name = "account1", \
                                          jid = "account1@jcl.test.com", \
                                          login = "mylogin", \
                                          password = "mypassword", \
                                          store_password = True, \
                                          test_enum = "choice1", \
                                          test_int = 21)
        another_account = AccountExample(user_jid = "user1@test.com", \
                                         name = "account2", \
                                         jid = "account2@jcl.test.com", \
                                         login = "mylogin", \
                                         password = "mypassword", \
                                         store_password = True, \
                                         test_enum = "choice1", \
                                         test_int = 21)
        del account.hub.threadConnection
        x_data = DataForm()
        x_data.xmlns = "jabber:x:data"
        x_data.type = "submit"
        x_data.add_field(field_type = "text-single", \
                         var = "name", \
                         value = "account1")
        x_data.add_field(field_type = "text-single", \
                         var = "login", \
                         value = "mylogin2")
        x_data.add_field(field_type = "text-private", \
                         var = "password", \
                         value = "mypassword2")
        x_data.add_field(field_type = "boolean", \
                         var = "store_password", \
                         value = "false")
        x_data.add_field(field_type = "list-single", \
                         var = "test_enum", \
                         value = "choice3")
        x_data.add_field(field_type = "text-single", \
                         var = "test_int", \
                         value = "43")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.attach_xml(query)
        self.comp.handle_set_register(iq_set)

        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        accounts = self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com" \
            and self.comp.default_account_class.q.name == "account1")
        self.assertEquals(accounts.count(), 1)
        _account = accounts[0]
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        self.assertEquals(_account.login, "mylogin2")
        self.assertEquals(_account.password, "mypassword2")
        self.assertFalse(_account.store_password)
        self.assertEquals(_account.test_enum, "choice3")
        self.assertEquals(_account.test_int, 43)
        del account.hub.threadConnection
        
        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 2)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com")
        self.assertEquals(iq_result.get_to(), "user1@test.com")

        message = stanza_sent[1]
        self.assertTrue(isinstance(message, Message))
        self.assertEquals(message.get_from(), "jcl.test.com")
        self.assertEquals(message.get_to(), "user1@test.com")
        self.assertEquals(message.get_subject(), \
                          _account.get_update_message_subject(Lang.en))
        self.assertEquals(message.get_body(), \
                          _account.get_update_message_body(Lang.en))

    def test_handle_set_register_remove(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account1", \
                            jid = "account1@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account2", \
                            jid = "account2@jcl.test.com")
        account21 = Account(user_jid = "user2@test.com", \
                            name = "account1", \
                            jid = "account1@jcl.test.com")
        del account.hub.threadConnection
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        query.newChild(None, "remove", None)
        self.comp.handle_set_register(iq_set)

        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        accounts = self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com")
        self.assertEquals(accounts.count(), 0)
        accounts = self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user2@test.com")
        self.assertEquals(accounts.count(), 1)
        _account = accounts[0]
        self.assertEquals(_account.user_jid, "user2@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        del account.hub.threadConnection
        
        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 6)
        presence = stanza_sent[0]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_node().prop("type"), "unsubscribe")
        self.assertEquals(presence.get_from(), "account1@jcl.test.com")
        self.assertEquals(presence.get_to(), "user1@test.com")
        presence = stanza_sent[1]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_node().prop("type"), "unsubscribed")
        self.assertEquals(presence.get_from(), "account1@jcl.test.com")
        self.assertEquals(presence.get_to(), "user1@test.com")
        presence = stanza_sent[2]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_node().prop("type"), "unsubscribe")
        self.assertEquals(presence.get_from(), "account2@jcl.test.com")
        self.assertEquals(presence.get_to(), "user1@test.com")
        presence = stanza_sent[3]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_node().prop("type"), "unsubscribed")
        self.assertEquals(presence.get_from(), "account2@jcl.test.com")
        self.assertEquals(presence.get_to(), "user1@test.com")
        presence = stanza_sent[4]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_node().prop("type"), "unsubscribe")
        self.assertEquals(presence.get_from(), "jcl.test.com")
        self.assertEquals(presence.get_to(), "user1@test.com")
        presence = stanza_sent[5]
        self.assertTrue(isinstance(presence, Presence))
        self.assertEquals(presence.get_node().prop("type"), "unsubscribed")
        self.assertEquals(presence.get_from(), "jcl.test.com")
        self.assertEquals(presence.get_to(), "user1@test.com")
    
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
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
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
                              and isinstance(presence, Presence)]), \
                          1)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == \
                              "account11@jcl.test.com" \
                              and isinstance(presence, Presence)]), \
                          1)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == \
                              "account12@jcl.test.com" \
                              and isinstance(presence, Presence)]), \
                          1)

    def test_handle_presence_available_to_component_unknown_user(self):
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
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "unknown@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

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
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "account11@jcl.test.com")
        self.assertTrue(isinstance(presence_sent[0], Presence))

    def test_handle_presence_available_to_account_unknown_user(self):
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
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "unknown@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_available_to_unknown_account(self):
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
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "user1@test.com",\
            to_jid = "unknown@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

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
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        messages_sent = self.comp.stream.sent
        self.assertEqual(len(messages_sent), 1)
        presence = messages_sent[0]
        self.assertTrue(presence is not None)
        self.assertTrue(isinstance(presence, Presence))
        self.assertEqual(presence.get_from_jid(), "account11@jcl.test.com")
        self.assertEqual(presence.get_to_jid(), "user1@test.com")
        
    def test_handle_presence_available_to_account_live_password_complex(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account11 = AccountExample(user_jid = "user1@test.com", \
                                   name = "account11", \
                                   jid = "account11@jcl.test.com")
        account11.store_password = False
        account12 = AccountExample(user_jid = "user1@test.com", \
                                   name = "account12", \
                                   jid = "account12@jcl.test.com")
        account2 = AccountExample(user_jid = "user2@test.com", \
                                  name = "account2", \
                                  jid = "account2@jcl.test.com")
        del account.hub.threadConnection
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        messages_sent = self.comp.stream.sent
        self.assertEqual(len(messages_sent), 2)
        password_message = None
        presence = None
        for message in messages_sent:
            if isinstance(message, Message):
                password_message = message
            elif isinstance(message, Presence):
                presence = message
        self.assertTrue(password_message is not None)
        self.assertTrue(presence is not None)
        self.assertTrue(isinstance(presence, Presence))
        self.assertEqual(presence.get_from_jid(), "account11@jcl.test.com")
        self.assertEqual(presence.get_to_jid(), "user1@test.com")
        
        self.assertEqual(unicode(password_message.get_from_jid()), \
                         "account11@jcl.test.com")
        self.assertEqual(unicode(password_message.get_to_jid()), \
                         "user1@test.com")
        self.assertEqual(password_message.get_subject(), \
                         "[PASSWORD] Password request")
        self.assertEqual(password_message.get_body(), \
                         Lang.en.ask_password_body % ("account11"))

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

    def test_handle_presence_unavailable_to_component_unknown_user(self):
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
            from_jid = "unknown@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

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

    def test_handle_presence_unavailable_to_account_unknown_user(self):
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
            from_jid = "unknown@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_unavailable_to_unknown_account(self):
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
            to_jid = "unknown@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_subscribe_to_component(self):
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

    def test_handle_presence_subscribe_to_component_unknown_user(self):
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
        self.comp.handle_presence_subscribe(Presence(\
            stanza_type = "subscribe", \
            from_jid = "unknown@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_subscribe_to_account(self):
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

    def test_handle_presence_subscribe_to_account_unknown_user(self):
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
        self.comp.handle_presence_subscribe(Presence(\
            stanza_type = "subscribe", \
            from_jid = "unknown@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_subscribe_to_unknown_account(self):
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
        self.comp.handle_presence_subscribe(Presence(\
            stanza_type = "subscribe", \
            from_jid = "user1@test.com",\
            to_jid = "unknown@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_subscribed(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.handle_presence_subscribed(None)
        self.assertEqual(len(self.comp.stream.sent), 0)
        
    def test_handle_presence_unsubscribe_to_account(self):
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
        presence = presence_sent[0]
        self.assertEqual(presence.get_from(), "account11@jcl.test.com")
        self.assertEqual(presence.get_to(), "user1@test.com")
        self.assertEqual(presence.xpath_eval("@type")[0].get_content(), \
                         "unsubscribe")
        presence = presence_sent[1]
        self.assertEqual(presence.get_from(), "account11@jcl.test.com")
        self.assertEqual(presence.get_to(), "user1@test.com")
        self.assertEqual(presence.xpath_eval("@type")[0].get_content(), \
                         "unsubscribed")
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.assertEquals(self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com" \
            and self.comp.default_account_class.q.name == "account11").count(), \
                          0)
        self.assertEquals(self.comp.default_account_class.select(\
            self.comp.default_account_class.q.user_jid == "user1@test.com").count(), \
                          1)
        self.assertEquals(self.comp.default_account_class.select().count(), \
                          2)
        del account.hub.threadConnection

    def test_handle_presence_unsubscribe_to_account_unknown_user(self):
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
            from_jid = "unknown@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.assertEquals(self.comp.default_account_class.select().count(), \
                          3)
        del account.hub.threadConnection


    def test_handle_presence_unsubscribe_to_unknown_account(self):
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
            to_jid = "unknown@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.assertEquals(self.comp.default_account_class.select().count(), \
                          3)
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

    def test_handle_message_password_complex(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account11 = AccountExample(user_jid = "user1@test.com", \
                                   name = "account11", \
                                   jid = "account11@jcl.test.com")
        account11.waiting_password_reply = True
        account12 = AccountExample(user_jid = "user1@test.com", \
                                   name = "account12", \
                                   jid = "account12@jcl.test.com")
        account2 = AccountExample(user_jid = "user2@test.com", \
                                  name = "account2", \
                                  jid = "account2@jcl.test.com")
        del account.hub.threadConnection
        self.comp.handle_message(Message(\
            from_jid = "user1@test.com", \
            to_jid = "account11@jcl.test.com", \
            subject = "[PASSWORD]", \
            body = "secret"))
        messages_sent = self.comp.stream.sent
        self.assertEqual(len(messages_sent), 1)
        self.assertEqual(messages_sent[0].get_to(), "user1@test.com")
        self.assertEqual(messages_sent[0].get_from(), "account11@jcl.test.com")
        self.assertEqual(account11.password, "secret")
        self.assertEqual(account11.waiting_password_reply, False)
        self.assertEqual(messages_sent[0].get_subject(), \
            "Password will be kept during your Jabber session")
        self.assertEqual(messages_sent[0].get_body(), \
            "Password will be kept during your Jabber session")
        
    def test_handle_tick(self):
        self.assertRaises(NotImplementedError, self.comp.handle_tick)
