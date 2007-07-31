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

import threading
import time
import re
import tempfile

from sqlobject.dbconnection import TheURIOpener

from pyxmpp.jid import JID
from pyxmpp.iq import Iq
from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.jabber.dataforms import Form

from jcl.jabber import Handler
from jcl.jabber.component import JCLComponent
from jcl.jabber.presence import DefaultSubscribeHandler, \
    DefaultUnsubscribeHandler, DefaultPresenceHandler
import jcl.model as model
import jcl.model.account as account
from jcl.model.account import Account, LegacyJID
from jcl.lang import Lang

from jcl.model.tests.account import ExampleAccount, Example2Account
from jcl.tests import JCLTestCase

class MockStream(object):
    def __init__(self,
                 jid="",
                 secret="",
                 server="",
                 port="",
                 keepalive=True):
        self.sent = []
        self.connection_started = False
        self.connection_stopped = False
        self.eof = False
        self.socket = []

    def send(self, iq):
        self.sent.append(iq)

    def set_iq_set_handler(self, iq_type, ns, handler):
        if not iq_type in ["query", "command"]:
            raise Exception("IQ type unknown: " + iq_type)
        if not ns in ["jabber:iq:version",
                      "jabber:iq:register",
                      "jabber:iq:gateway",
                      "http://jabber.org/protocol/disco#items",
                      "http://jabber.org/protocol/disco#info",
                      "http://jabber.org/protocol/commands"]:
            raise Exception("Unknown namespace: " + ns)
        if handler is None:
            raise Exception("Handler must not be None")

    set_iq_get_handler = set_iq_set_handler

    def set_presence_handler(self, status, handler):
        if not status in ["available",
                          "unavailable",
                          "probe",
                          "subscribe",
                          "subscribed",
                          "unsubscribe",
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

class MockStreamRaiseException(MockStream):
    def loop_iter(self, timeout):
        raise Exception("in loop error")

class LangExample(Lang):
    class en(Lang.en):
        type_example_name = "Type Example"

class TestSubscribeHandler(DefaultSubscribeHandler):
    def filter(self, message, lang_class):
        if re.compile(".*%.*").match(message.get_to().node):
            # return no account because self.handle does not need an account
            return []
        else:
            return None

class ErrorHandler(Handler):
    def filter(self, stanza, lang_class):
        raise Exception("test error")

class TestUnsubscribeHandler(DefaultUnsubscribeHandler):
    def filter(self, message, lang_class):
        if re.compile(".*%.*").match(message.get_to().node):
            # return no account because self.handle does not need an account
            return []
        else:
            return None

class HandlerMock(object):
    def __init__(self):
        self.handled = []

    def filter(self, stanza, lang_class):
        return True

    def handle(self, stanza, lang_class, data):
        self.handled.append((stanza, lang_class, data))
        return [(stanza, lang_class, data)]

class JCLComponent_TestCase(JCLTestCase):
    ###########################################################################
    # Utility methods
    ###########################################################################
    def setUp(self):
        JCLTestCase.setUp(self, tables=[Account, LegacyJID, ExampleAccount,
                                        Example2Account])
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347")
        self.max_tick_count = 1
        self.saved_time_handler = None

    ###########################################################################
    # Constructor tests
    ###########################################################################
    def test_constructor(self):
        model.db_connect()
        self.assertTrue(Account._connection.tableExists("account"))
        model.db_disconnect()

    ###########################################################################
    # apply_registered_behavior tests
    ###########################################################################
    def test_apply_registered_behavior(self):
        self.comp.stream = MockStreamNoConnect()
        self.comp.stream_class = MockStreamNoConnect
        message = Message(from_jid="user1@test.com",
                          to_jid="account11@jcl.test.com")
        result = self.comp.apply_registered_behavior([[ErrorHandler(None)]], message)
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_type(), "error")
        self.assertEquals(len(self.comp.stream.sent), 1)
        self.assertEquals(result[0], self.comp.stream.sent[0])

    def test_apply_all_registered_behavior(self):
        self.comp.stream = MockStreamNoConnect()
        self.comp.stream_class = MockStreamNoConnect
        message = Message(from_jid="user1@test.com",
                          to_jid="account11@jcl.test.com")
        handler1 = HandlerMock()
        handler2 = HandlerMock()
        result = self.comp.apply_registered_behavior([[handler1], [handler2]],
                                                     message)
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0][0], message)
        self.assertEquals(result[1][0], message)

    def test_apply_one_registered_behavior(self):
        self.comp.stream = MockStreamNoConnect()
        self.comp.stream_class = MockStreamNoConnect
        message = Message(from_jid="user1@test.com",
                          to_jid="account11@jcl.test.com")
        handler1 = HandlerMock()
        handler2 = HandlerMock()
        result = self.comp.apply_registered_behavior([[handler1, handler2]],
                                                     message)
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0][0], message)
        self.assertEquals(len(handler1.handled), 1)
        self.assertEquals(len(handler2.handled), 0)

    ###########################################################################
    # 'run' tests
    ###########################################################################
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
        """Test basic main loop execution"""
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

    def test_run_unhandled_error(self):
        """Test main loop unhandled error from a component handler"""
        def do_nothing():
            return
        self.comp.time_unit = 1
        self.comp.stream = MockStreamRaiseException()
        self.comp.stream_class = MockStreamRaiseException
        self.comp.handle_tick = do_nothing

        try:
            self.comp.run()
        except Exception, e:
            threads = threading.enumerate()
            self.assertEquals(len(threads), 1)
            self.assertTrue(self.comp.stream.connection_stopped)
            return
        self.fail("No exception caught")

    def test_run_ni_handle_tick(self):
        """Test JCLComponent 'NotImplemented' error from handle_tick method"""
        self.comp.time_unit = 1
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        try:
            self.comp.run()
        except NotImplementedError, e:
            threads = threading.enumerate()
            self.assertEquals(len(threads), 1)
            self.assertTrue(self.comp.stream.connection_stopped)
            return
        self.fail("No exception caught")

    def test_run_go_offline(self):
        """Test main loop send offline presence when exiting"""
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.time_unit = 1
        self.max_tick_count = 1
        self.comp.handle_tick = self.__handle_tick_test_time_handler
        model.db_connect()
        account11 = Account(user_jid="test1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="test1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="test2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.run()
        self.assertTrue(self.comp.stream.connection_started)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertTrue(self.comp.stream.connection_stopped)
        if self.comp.queue.qsize():
            raise self.comp.queue.get(0)
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 5)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "test1@test.com"]), \
                          3)
        self.assertEqual(\
            len([presence \
                 for presence in presence_sent \
                 if presence.get_from_jid() == \
                 "jcl.test.com" \
                 and presence.xpath_eval("@type")[0].get_content() \
                 == "unavailable"]), \
            2)
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
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "test2@test.com"]), \
                          2)
        self.assertEqual(\
            len([presence \
                 for presence in presence_sent \
                 if presence.get_from_jid() == \
                 "account2@jcl.test.com" \
                 and presence.xpath_eval("@type")[0].get_content() \
                 == "unavailable"]), \
            1)

    ###########################################################################
    # 'time_handler' tests
    ###########################################################################
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

    ###########################################################################
    # 'authenticated handler' tests
    ###########################################################################
    def test_authenticated_handler(self):
        self.comp.stream = MockStream()
        self.comp.authenticated()
        self.assertTrue(True)

    def test_authenticated_send_probe(self):
        model.db_connect()
        account11 = Account(user_jid = "test1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "test1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "test2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
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

    ###########################################################################
    # 'signal_handler' tests
    ###########################################################################
    def test_signal_handler(self):
        self.comp.running = True
        self.comp.signal_handler(42, None)
        self.assertFalse(self.comp.running)

    ###########################################################################
    # 'handle_get_gateway' tests
    ###########################################################################
    def test_handle_get_gateway(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        info_query = Iq(stanza_type = "get",
                        from_jid = "user1@test.com")
        info_query.new_query("jabber:iq:gateway")
        self.comp.handle_get_gateway(info_query)
        self.assertEquals(len(self.comp.stream.sent), 1)
        iq_sent = self.comp.stream.sent[0]
        self.assertEquals(iq_sent.get_to(), "user1@test.com")
        self.assertEquals(len(iq_sent.xpath_eval("*/*")), 2)
        desc_nodes = iq_sent.xpath_eval("jig:query/jig:desc",
                                        {"jig" : "jabber:iq:gateway"})
        self.assertEquals(len(desc_nodes), 1)
        self.assertEquals(desc_nodes[0].content, Lang.en.get_gateway_desc)
        prompt_nodes = iq_sent.xpath_eval("jig:query/jig:prompt",
                                          {"jig" : "jabber:iq:gateway"})
        self.assertEquals(len(prompt_nodes), 1)
        self.assertEquals(prompt_nodes[0].content, Lang.en.get_gateway_prompt)

    ###########################################################################
    # 'handle_set_gateway' tests
    ###########################################################################
    def test_handle_set_gateway(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        info_query = Iq(stanza_type = "get",
                        from_jid = "user1@test.com")
        query = info_query.new_query("jabber:iq:gateway")
        prompt = query.newChild(None, "prompt", None)
        prompt.addContent("user@test.com")
        self.comp.handle_set_gateway(info_query)
        self.assertEquals(len(self.comp.stream.sent), 1)
        iq_sent = self.comp.stream.sent[0]
        self.assertEquals(iq_sent.get_to(), "user1@test.com")
        self.assertEquals(len(iq_sent.xpath_eval("*/*")), 2)
        jid_nodes = iq_sent.xpath_eval("jig:query/jig:jid",
                                       {"jig" : "jabber:iq:gateway"})
        self.assertEquals(len(jid_nodes), 1)
        self.assertEquals(jid_nodes[0].content, "user%test.com@jcl.test.com")

    ###########################################################################
    # 'disco_get_info' tests
    ###########################################################################
    def test_disco_get_info(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        disco_info = self.comp.disco_get_info(None, info_query)
        self.assertEquals(len(self.comp.stream.sent), 0)
        self.assertEquals(disco_info.get_identities()[0].get_name(), self.comp.name)
        self.assertTrue(disco_info.has_feature("jabber:iq:version"))
        self.assertTrue(disco_info.has_feature("jabber:iq:register"))

    def test_disco_get_info_multiple_account_type(self):
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        disco_info = self.comp.disco_get_info(None, info_query)
        self.assertEquals(len(self.comp.stream.sent), 0)
        self.assertEquals(disco_info.get_identities()[0].get_name(),
                          self.comp.name)
        self.assertTrue(disco_info.has_feature("jabber:iq:version"))
        self.assertFalse(disco_info.has_feature("jabber:iq:register"))

    def test_disco_get_info_node(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="node_test@jcl.test.com")
        disco_info = self.comp.disco_get_info("node_test", info_query)
        self.assertEquals(len(self.comp.stream.sent), 0)
        self.assertTrue(disco_info.has_feature("jabber:iq:register"))

    def test_disco_get_info_long_node(self):
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="node_test@jcl.test.com/node_type")
        disco_info = self.comp.disco_get_info("node_type/node_test",
                                              info_query)
        self.assertEquals(len(self.comp.stream.sent), 0)
        self.assertTrue(disco_info.has_feature("jabber:iq:register"))

    def test_disco_get_info_root_unknown_node(self):
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        disco_info = self.comp.disco_get_info("unknown", info_query)
        self.assertEquals(disco_info, None)

    def test_disco_get_info_command_list(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        disco_info = self.comp.disco_get_info("list", info_query)
        self.assertEquals(len(self.comp.stream.sent), 0)
        self.assertTrue(disco_info.has_feature("http://jabber.org/protocol/commands"))
        self.assertEquals(len(disco_info.get_identities()), 1)
        self.assertEquals(disco_info.get_identities()[0].get_category(),
                          "automation")
        self.assertEquals(disco_info.get_identities()[0].get_type(),
                          "command-node")
        self.assertEquals(disco_info.get_identities()[0].get_name(),
                          Lang.en.command_list)

    ###########################################################################
    # 'disco_get_items' tests
    ###########################################################################
    def test_disco_get_items_1type_no_node(self):
        """get_items on main entity. Must list accounts"""
        model.db_connect()
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account1 = Account(user_jid = "user1@test.com", \
                           name = "account1", \
                           jid = "account1@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type = "get", \
                        from_jid = "user1@test.com", \
                        to_jid = "jcl.test.com")
        disco_items = self.comp.disco_get_items(None, info_query)
        self.assertEquals(len(disco_items.get_items()), 1)
        disco_item = disco_items.get_items()[0]
        self.assertEquals(disco_item.get_jid(), account1.jid)
        self.assertEquals(disco_item.get_node(), account1.name)
        self.assertEquals(disco_item.get_name(), account1.long_name)

    def test_disco_get_items_unknown_node(self):
        self.comp.account_manager.account_classes = (ExampleAccount, )
        model.db_connect()
        account11 = ExampleAccount(user_jid="user1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        disco_items = self.comp.disco_get_items("unknown", info_query)
        self.assertEquals(disco_items, None)

    def test_disco_get_items_unknown_node_multiple_account_types(self):
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="user1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account21 = Example2Account(user_jid="user1@test.com",
                                    name="account21",
                                    jid="account21@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        self.comp.account_manager.has_multiple_account_type = True
        disco_items = self.comp.disco_get_items("unknown", info_query)
        self.assertEquals(disco_items, None)

    def test_disco_get_items_1type_with_node(self):
        """get_items on an account. Must return nothing"""
        model.db_connect()
        account1 = Account(user_jid="user1@test.com",
                           name="account1",
                           jid="account1@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="account1@jcl.test.com")
        disco_items = self.comp.disco_get_items("account1", info_query)
        self.assertEquals(disco_items, None)

    def test_disco_get_items_2types_no_node(self):
        """get_items on main entity. Must account types"""
        self.comp.lang = LangExample()
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = ExampleAccount(user_jid="user1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account21 = Example2Account(user_jid="user1@test.com",
                                    name="account21",
                                    jid="account21@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        disco_items = self.comp.disco_get_items(None, info_query)
        self.assertEquals(len(disco_items.get_items()), 2)
        disco_item = disco_items.get_items()[0]
        self.assertEquals(unicode(disco_item.get_jid()),
                          unicode(self.comp.jid) + "/Example")
        self.assertEquals(disco_item.get_node(), "Example")
        self.assertEquals(disco_item.get_name(),
                          LangExample.en.type_example_name)
        disco_item = disco_items.get_items()[1]
        self.assertEquals(unicode(disco_item.get_jid()),
                          unicode(self.comp.jid) + "/Example2")
        self.assertEquals(disco_item.get_node(), "Example2")
        # no name in language class for type Example2, so fallback on type name
        self.assertEquals(disco_item.get_name(), "Example2")

    # Be careful, account_classes cannot contains parent classes
    #
    def test_disco_get_items_2types_with_node(self):
        """get_items on the first account type node. Must return account list of
        that type for the current user"""
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = ExampleAccount(user_jid="user1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = ExampleAccount(user_jid="user2@test.com",
                                   name="account12",
                                   jid="account12@jcl.test.com")
        account21 = Example2Account(user_jid="user1@test.com",
                                    name="account21",
                                    jid="account21@jcl.test.com")
        account22 = Example2Account(user_jid="user2@test.com",
                                    name="account22",
                                    jid="account22@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com/Example")
        disco_items = self.comp.disco_get_items("Example", info_query)
        self.assertEquals(len(disco_items.get_items()), 1)
        disco_item = disco_items.get_items()[0]
        self.assertEquals(unicode(disco_item.get_jid()), unicode(account11.jid) + "/Example")
        self.assertEquals(disco_item.get_node(), "Example/" + account11.name)
        self.assertEquals(disco_item.get_name(), account11.long_name)

    def test_disco_get_items_2types_with_node2(self):
        """get_items on the second account type node. Must return account list of
        that type for the current user"""
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = ExampleAccount(user_jid="user1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = ExampleAccount(user_jid="user2@test.com",
                                   name="account12",
                                   jid="account12@jcl.test.com")
        account21 = Example2Account(user_jid="user1@test.com",
                                    name="account21",
                                    jid="account21@jcl.test.com")
        account22 = Example2Account(user_jid="user2@test.com",
                                    name="account22",
                                    jid="account22@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="get",
                        from_jid="user2@test.com",
                        to_jid="jcl.test.com/Example2")
        disco_items = self.comp.disco_get_items("Example2", info_query)
        self.assertEquals(len(disco_items.get_items()), 1)
        disco_item = disco_items.get_items()[0]
        self.assertEquals(unicode(disco_item.get_jid()), unicode(account22.jid) + "/Example2")
        self.assertEquals(disco_item.get_node(), "Example2/" + account22.name)
        self.assertEquals(disco_item.get_name(), account22.long_name)

    def test_disco_get_items_2types_with_long_node(self):
        """get_items on a first type account. Must return nothing"""
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        model.db_connect()
        account1 = ExampleAccount(user_jid="user1@test.com",
                                  name="account1",
                                  jid="account1@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="account1@jcl.test.com/Example")
        disco_items = self.comp.disco_get_items("Example/account1", info_query)
        self.assertEquals(disco_items, None)

    def test_disco_get_items_2types_with_long_node2(self):
        """get_items on a second type account. Must return nothing"""
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        model.db_connect()
        account1 = Example2Account(user_jid="user1@test.com",
                                   name="account1",
                                   jid="account1@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="account1@jcl.test.com/Example2")
        disco_items = self.comp.disco_get_items("Example2/account1", info_query)
        self.assertEquals(disco_items, None)

    def test_disco_get_items_list_commands(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        info_query = Iq(stanza_type="get",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        disco_items = self.comp.disco_get_items("http://jabber.org/protocol/commands",
                                                info_query)
        self.assertEquals(len(disco_items.get_items()), 36)
        item = disco_items.get_items()[0]
        self.assertEquals(item.get_node(), "list")
        self.assertEquals(item.get_name(), Lang.en.command_list)

    ###########################################################################
    # 'handle_get_version' tests
    ###########################################################################
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

    ###########################################################################
    # 'handle_get_register' tests
    ###########################################################################
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

    def __check_get_register_new_type(self):
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
        self.assertEquals(fields[2].prop("label"), Lang.en.field_password)

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

    def test_handle_get_register_new_complex(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_manager.account_classes = (ExampleAccount,)
        self.comp.handle_get_register(Iq(stanza_type = "get", \
                                         from_jid = "user1@test.com", \
                                         to_jid = "jcl.test.com"))
        self.__check_get_register_new_type()

    def test_handle_get_register_exist(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                           name="account11",
                           jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                           name="account12",
                           jid="account12@jcl.test.com")
        account21 = Account(user_jid="user1@test.com",
                           name="account21",
                           jid="account21@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_get_register(Iq(stanza_type="get",
                                         from_jid="user1@test.com",
                                         to_jid="account11@jcl.test.com"))
        self.assertEquals(len(self.comp.stream.sent), 1)
        iq_sent = self.comp.stream.sent[0]
        self.assertEquals(iq_sent.get_to(), "user1@test.com")
        titles = iq_sent.xpath_eval("jir:query/jxd:x/jxd:title",
                                    {"jir" : "jabber:iq:register",
                                     "jxd" : "jabber:x:data"})
        self.assertEquals(len(titles), 1)
        self.assertEquals(titles[0].content,
                          Lang.en.register_title)
        instructions = iq_sent.xpath_eval("jir:query/jxd:x/jxd:instructions",
                                          {"jir" : "jabber:iq:register",
                                           "jxd" : "jabber:x:data"})
        self.assertEquals(len(instructions), 1)
        self.assertEquals(instructions[0].content,
                          Lang.en.register_instructions)
        fields = iq_sent.xpath_eval("jir:query/jxd:x/jxd:field",
                                    {"jir" : "jabber:iq:register",
                                     "jxd" : "jabber:x:data"})
        self.assertEquals(len(fields), 1)
        self.assertEquals(fields[0].prop("type"), "hidden")
        self.assertEquals(fields[0].prop("var"), "name")
        self.assertEquals(fields[0].prop("label"), Lang.en.account_name)
        self.assertEquals(fields[0].children.next.name, "required")
        value = iq_sent.xpath_eval("jir:query/jxd:x/jxd:field/jxd:value",
                                   {"jir" : "jabber:iq:register",
                                    "jxd" : "jabber:x:data"})
        self.assertEquals(len(value), 1)
        self.assertEquals(value[0].content, "account11")

    def test_handle_get_register_exist_complex(self):
        model.db_connect()
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account1 = ExampleAccount(user_jid = "user1@test.com", \
                                  name = "account1", \
                                  jid = "account1@jcl.test.com", \
                                  login = "mylogin", \
                                  password = "mypassword", \
                                  store_password = False, \
                                  test_enum = "choice3", \
                                  test_int = 1)
        account11 = ExampleAccount(user_jid = "user1@test.com", \
                                   name = "account11", \
                                   jid = "account11@jcl.test.com", \
                                   login = "mylogin11", \
                                   password = "mypassword11", \
                                   store_password = False, \
                                   test_enum = "choice2", \
                                   test_int = 11)
        account21 = ExampleAccount(user_jid = "user2@test.com", \
                                   name = "account21", \
                                   jid = "account21@jcl.test.com", \
                                   login = "mylogin21", \
                                   password = "mypassword21", \
                                   store_password = False, \
                                   test_enum = "choice1", \
                                   test_int = 21)
        model.db_disconnect()
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
        self.assertEquals(field.prop("label"), Lang.en.field_password)
        self.assertEquals(field.children.name, "value")
        self.assertEquals(field.children.content, "mypassword")
        field = fields[3]
        self.assertEquals(field.prop("type"), "boolean")
        self.assertEquals(field.prop("var"), "store_password")
        self.assertEquals(field.prop("label"), "store_password")
        self.assertEquals(field.children.name, "value")
        self.assertEquals(field.children.content, "0")
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
        self.assertEquals(field.children.content, "1")

    def test_handle_get_register_new_type1(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        self.comp.handle_get_register(Iq(stanza_type = "get", \
                                         from_jid = "user1@test.com", \
                                         to_jid = "jcl.test.com/example"))
        self.__check_get_register_new_type()

    def test_handle_get_register_new_type2(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        self.comp.handle_get_register(Iq(stanza_type = "get", \
                                         from_jid = JID("user1@test.com"), \
                                         to_jid = JID("jcl.test.com/example2")))
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
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[0].prop("type"), "text-single")
        self.assertEquals(fields[0].prop("var"), "name")
        self.assertEquals(fields[0].prop("label"), Lang.en.account_name)
        self.assertEquals(fields[0].children.name, "required")

        self.assertEquals(fields[1].prop("type"), "text-single")
        self.assertEquals(fields[1].prop("var"), "test_new_int")
        self.assertEquals(fields[1].prop("label"), "test_new_int")

    ###########################################################################
    # 'handle_set_register' tests
    ###########################################################################
    def test_handle_set_register_new(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        x_data = Form("submit")
        x_data.add_field(name="name",
                         value="account1",
                         field_type="text-single")
        iq_set = Iq(stanza_type="set",
                    from_jid="user1@test.com",
                    to_jid="jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.as_xml(query, None)
        self.comp.handle_set_register(iq_set)

        model.db_connect()
        _account = account.get_account("user1@test.com", "account1")
        self.assertNotEquals(_account, None)
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        model.db_disconnect()

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
        self.assertEquals(presence_component.get_node().prop("type"),
                          "subscribe")

        message = stanza_sent[2]
        self.assertTrue(isinstance(message, Message))
        self.assertEquals(message.get_from(), "jcl.test.com")
        self.assertEquals(message.get_to(), "user1@test.com")
        self.assertEquals(message.get_subject(),
                          _account.get_new_message_subject(Lang.en))
        self.assertEquals(message.get_body(),
                          _account.get_new_message_body(Lang.en))

        presence_account = stanza_sent[3]
        self.assertTrue(isinstance(presence_account, Presence))
        self.assertEquals(presence_account.get_from(), "account1@jcl.test.com")
        self.assertEquals(presence_account.get_to(), "user1@test.com")
        self.assertEquals(presence_account.get_node().prop("type"),
                          "subscribe")

    def test_handle_set_register_new_multiple_types(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_manager.account_classes = (ExampleAccount, Example2Account)
        x_data = Form("submit")
        x_data.add_field(name="name",
                         value="account1",
                         field_type="text-single")
        iq_set = Iq(stanza_type="set",
                    from_jid="user1@test.com",
                    to_jid="jcl.test.com/Example2")
        query = iq_set.new_query("jabber:iq:register")
        x_data.as_xml(query, None)
        self.comp.handle_set_register(iq_set)

        model.db_connect()
        _account = account.get_account("user1@test.com", "account1")
        self.assertNotEquals(_account, None)
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        model.db_disconnect()

        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 4)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com/Example2")
        self.assertEquals(iq_result.get_to(), "user1@test.com")

        presence_component = stanza_sent[1]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "jcl.test.com")
        self.assertEquals(presence_component.get_to(), "user1@test.com")
        self.assertEquals(presence_component.get_node().prop("type"),
                          "subscribe")

        message = stanza_sent[2]
        self.assertTrue(isinstance(message, Message))
        self.assertEquals(message.get_from(), "jcl.test.com")
        self.assertEquals(message.get_to(), "user1@test.com")
        self.assertEquals(message.get_subject(),
                          _account.get_new_message_subject(Lang.en))
        self.assertEquals(message.get_body(),
                          _account.get_new_message_body(Lang.en))

        presence_account = stanza_sent[3]
        self.assertTrue(isinstance(presence_account, Presence))
        self.assertEquals(presence_account.get_from(), "account1@jcl.test.com")
        self.assertEquals(presence_account.get_to(), "user1@test.com")
        self.assertEquals(presence_account.get_node().prop("type"),
                          "subscribe")

    def test_handle_set_register_new_complex(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_manager.account_classes = (ExampleAccount,)
        x_data = Form("submit")
        x_data.add_field(name = "name", \
                         value = "account1", \
                         field_type = "text-single")
        x_data.add_field(name = "login", \
                         value = "mylogin", \
                         field_type = "text-single")
        x_data.add_field(name = "password", \
                         value = "mypassword", \
                         field_type = "text-private")
        x_data.add_field(name = "store_password", \
                         value = False, \
                         field_type = "boolean")
        x_data.add_field(name = "test_enum", \
                         value = "choice3", \
                         field_type = "list-single")
        x_data.add_field(name = "test_int", \
                         value = 43, \
                         field_type = "text-single")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.as_xml(query, None)
        self.comp.handle_set_register(iq_set)

        model.db_connect()
        _account = account.get_account("user1@test.com", "account1")
        self.assertNotEquals(_account, None)
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        self.assertEquals(_account.login, "mylogin")
        self.assertEquals(_account.password, "mypassword")
        self.assertFalse(_account.store_password)
        self.assertEquals(_account.test_enum, "choice3")
        self.assertEquals(_account.test_int, 43)
        model.db_disconnect()

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
        self.comp.account_manager.account_classes = (ExampleAccount,)
        x_data = Form("submit")
        x_data.add_field(name = "name", \
                         value = "account1", \
                         field_type = "text-single")
        x_data.add_field(name = "login", \
                         value = "mylogin", \
                         field_type = "text-single")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.as_xml(query)
        self.comp.handle_set_register(iq_set)

        model.db_connect()
        _account = account.get_account("user1@test.com", "account1")
        self.assertNotEquals(_account, None)
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        self.assertEquals(_account.login, "mylogin")
        self.assertEquals(_account.password, None)
        self.assertTrue(_account.store_password)
        self.assertEquals(_account.test_enum, "choice2")
        self.assertEquals(_account.test_int, 44)
        model.db_disconnect()

    def test_handle_set_register_new_name_mandatory(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        x_data = Form("submit")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.as_xml(query)
        self.comp.handle_set_register(iq_set)

        model.db_connect()
        _account = account.get_account("user1@test.com", "account1")
        self.assertEquals(_account, None)
        model.db_disconnect()

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
        self.comp.account_manager.account_classes = (ExampleAccount,)
        x_data = Form("submit")
        x_data.add_field(name="name",
                         value="account1",
                         field_type="text-single")
        iq_set = Iq(stanza_type="set",
                    from_jid="user1@test.com",
                    to_jid="jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.as_xml(query)
        self.comp.handle_set_register(iq_set)

        model.db_connect()
        _account = account.get_account("user1@test.com", "account1")
        self.assertEquals(_account, None)
        model.db_disconnect()

        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 1)
        self.assertTrue(isinstance(stanza_sent[0], Iq))
        self.assertEquals(stanza_sent[0].get_node().prop("type"), "error")
        stanza_error = stanza_sent[0].get_error()
        self.assertEquals(stanza_error.get_condition().name,
                          "not-acceptable")
        self.assertEquals(stanza_error.get_text(),
                          Lang.en.mandatory_field % ("login"))

    def test_handle_set_register_update_complex(self):
        model.db_connect()
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.account_manager.account_classes = (Example2Account, ExampleAccount)
        existing_account = ExampleAccount(user_jid = "user1@test.com", \
                                          name = "account1", \
                                          jid = "account1@jcl.test.com", \
                                          login = "mylogin", \
                                          password = "mypassword", \
                                          store_password = True, \
                                          test_enum = "choice1", \
                                          test_int = 21)
        another_account = ExampleAccount(user_jid = "user1@test.com", \
                                         name = "account2", \
                                         jid = "account2@jcl.test.com", \
                                         login = "mylogin", \
                                         password = "mypassword", \
                                         store_password = True, \
                                         test_enum = "choice1", \
                                         test_int = 21)
        model.db_disconnect()
        x_data = Form("submit")
        x_data.add_field(name = "name", \
                         value = "account1", \
                         field_type = "text-single")
        x_data.add_field(name = "login", \
                         value = "mylogin2", \
                         field_type = "text-single")
        x_data.add_field(name = "password", \
                         value = "mypassword2", \
                         field_type = "text-private")
        x_data.add_field(name = "store_password", \
                         value = False, \
                         field_type = "boolean")
        x_data.add_field(name = "test_enum", \
                         value = "choice3", \
                         field_type = "list-single")
        x_data.add_field(name = "test_int", \
                         value = 43, \
                         field_type = "text-single")
        iq_set = Iq(stanza_type = "set", \
                    from_jid = "user1@test.com", \
                    to_jid = "account1@jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        x_data.as_xml(query)
        self.comp.handle_set_register(iq_set)

        model.db_connect()
        _account = account.get_account("user1@test.com", "account1")
        self.assertNotEquals(_account, None)
        self.assertEquals(_account.__class__.__name__, "ExampleAccount")
        self.assertEquals(_account.user_jid, "user1@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        self.assertEquals(_account.login, "mylogin2")
        self.assertEquals(_account.password, "mypassword2")
        self.assertFalse(_account.store_password)
        self.assertEquals(_account.test_enum, "choice3")
        self.assertEquals(_account.test_int, 43)
        model.db_disconnect()

        stanza_sent = self.comp.stream.sent
        self.assertEquals(len(stanza_sent), 2)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "account1@jcl.test.com")
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
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account1",
                            jid="account1@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account2",
                            jid="account2@jcl.test.com")
        account21 = Account(user_jid="user2@test.com",
                            name="account1",
                            jid="account1@jcl.test.com")
        model.db_disconnect()
        iq_set = Iq(stanza_type="set",
                    from_jid="user1@test.com",
                    to_jid="jcl.test.com")
        query = iq_set.new_query("jabber:iq:register")
        query.newChild(None, "remove", None)
        self.comp.handle_set_register(iq_set)

        model.db_connect()
        self.assertEquals(account.get_accounts_count("user1@test.com"),
                          0)
        accounts = account.get_accounts("user2@test.com")
        i = 0
        for _account in accounts:
            i = i + 1
        self.assertEquals(i, 1)
        self.assertEquals(_account.user_jid, "user2@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        model.db_disconnect()

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
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "user1@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 3)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "user1@test.com" \
                              and presence.get_type() is None]), \
                          3)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == \
                              "jcl.test.com" \
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]), \
                          1)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == \
                              "account11@jcl.test.com" \
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]), \
                          1)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_from_jid() == \
                              "account12@jcl.test.com" \
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]), \
                          1)

    def test_handle_presence_available_to_component_legacy_users(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        legacy_jid111 = LegacyJID(legacy_address="u111@test.com",
                                  jid="u111%test.com@jcl.test.com",
                                  account=account11)
        legacy_jid112 = LegacyJID(legacy_address="u112@test.com",
                                  jid="u112%test.com@jcl.test.com",
                                  account=account11)
        legacy_jid121 = LegacyJID(legacy_address="u121@test.com",
                                  jid="u121%test.com@jcl.test.com",
                                  account=account12)
        legacy_jid122 = LegacyJID(legacy_address="u122@test.com",
                                  jid="u122%test.com@jcl.test.com",
                                  account=account12)
        legacy_jid21 = LegacyJID(legacy_address="u21@test.com",
                                 jid="u21%test.com@jcl.test.com",
                                 account=account2)
        model.db_disconnect()
        self.comp.handle_presence_available(Presence(\
            stanza_type="available",
            from_jid="user1@test.com",
            to_jid="jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 7)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_to_jid() == "user1@test.com" \
                              and presence.get_type() is None]),
                         7)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "account11@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "account12@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "u111%test.com@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "u112%test.com@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "u121%test.com@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "u122%test.com@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() is None]),
                         1)

    def test_handle_presence_available_to_component_unknown_user(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "unknown@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_available_to_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "user1@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "account11@jcl.test.com")
        self.assertTrue(isinstance(presence_sent[0], Presence))
        self.assertEqual(presence_sent[0].get_type(), None)

    def test_handle_presence_available_to_registered_handlers(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.presence_available_handlers += [(DefaultPresenceHandler(self.comp),)]
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_available(Presence(\
            stanza_type="available",
            from_jid="user1@test.com",
            to_jid="user1%test.com@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(),
                         "user1%test.com@jcl.test.com")
        self.assertTrue(isinstance(presence_sent[0], Presence))
        self.assertEqual(presence_sent[0].get_type(), None)

    def test_handle_presence_available_to_account_unknown_user(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "unknown@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_available_to_unknown_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_available(Presence(\
            stanza_type = "available", \
            from_jid = "user1@test.com",\
            to_jid = "unknown@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_available_to_account_live_password(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
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
        model.db_disconnect()
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
        self.assertEqual(presence.get_type(), None)

    def test_handle_presence_available_to_account_live_password_complex(self):
        model.db_connect()
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        account11 = ExampleAccount(user_jid = "user1@test.com", \
                                   name = "account11", \
                                   jid = "account11@jcl.test.com")
        account11.store_password = False
        account12 = ExampleAccount(user_jid = "user1@test.com", \
                                   name = "account12", \
                                   jid = "account12@jcl.test.com")
        account2 = ExampleAccount(user_jid = "user2@test.com", \
                                  name = "account2", \
                                  jid = "account2@jcl.test.com")
        model.db_disconnect()
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
        self.assertEqual(presence.get_type(), None)

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
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type = "unavailable", \
            from_jid = "user1@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 3)
        self.assertEqual(len([presence \
                              for presence in presence_sent \
                              if presence.get_to_jid() == "user1@test.com" \
                              and presence.get_type() == "unavailable"]), \
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

    def test_handle_presence_unavailable_to_component_legacy_users(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        legacy_jid111 = LegacyJID(legacy_address="u111@test.com",
                                  jid="u111%test.com@jcl.test.com",
                                  account=account11)
        legacy_jid112 = LegacyJID(legacy_address="u112@test.com",
                                  jid="u112%test.com@jcl.test.com",
                                  account=account11)
        legacy_jid121 = LegacyJID(legacy_address="u121@test.com",
                                  jid="u121%test.com@jcl.test.com",
                                  account=account12)
        legacy_jid122 = LegacyJID(legacy_address="u122@test.com",
                                  jid="u122%test.com@jcl.test.com",
                                  account=account12)
        legacy_jid21 = LegacyJID(legacy_address="u21@test.com",
                                 jid="u21%test.com@jcl.test.com",
                                 account=account2)
        model.db_disconnect()
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type="unavailable",
            from_jid="user1@test.com",
            to_jid="jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 7)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_to_jid() == "user1@test.com" \
                              and presence.get_type() == "unavailable"]),
                         7)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() == "unavailable"]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "account11@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() == "unavailable"]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "account12@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() == "unavailable"]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "u111%test.com@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() == "unavailable"]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "u112%test.com@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() == "unavailable"]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "u121%test.com@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() == "unavailable"]),
                         1)
        self.assertEqual(len([presence
                              for presence in presence_sent
                              if presence.get_from_jid() == \
                              "u122%test.com@jcl.test.com"
                              and isinstance(presence, Presence) \
                              and presence.get_type() == "unavailable"]),
                         1)

    def test_handle_presence_unavailable_to_component_unknown_user(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type = "unavailable", \
            from_jid = "unknown@test.com",\
            to_jid = "jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_unavailable_to_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type="unavailable",
            from_jid="user1@test.com",
            to_jid="account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "account11@jcl.test.com")
        self.assertEqual(\
            presence_sent[0].xpath_eval("@type")[0].get_content(),
            "unavailable")

    def test_handle_presence_unavailable_to_registered_handlers(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.presence_unavailable_handlers += [(DefaultPresenceHandler(self.comp),)]
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type = "unavailable", \
            from_jid = "user1@test.com",\
            to_jid = "user1%test.com@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "user1%test.com@jcl.test.com")
        self.assertEqual(\
            presence_sent[0].xpath_eval("@type")[0].get_content(), \
            "unavailable")

    def test_handle_presence_unavailable_to_account_unknown_user(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type = "unavailable", \
            from_jid = "unknown@test.com",\
            to_jid = "account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_unavailable_to_unknown_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unavailable(Presence(\
            stanza_type = "unavailable", \
            from_jid = "user1@test.com",\
            to_jid = "unknown@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_subscribe_to_component(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
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
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_subscribe(Presence(\
            stanza_type="subscribe",
            from_jid="unknown@test.com",
            to_jid="jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_subscribe_to_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
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
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_subscribe(Presence(\
            stanza_type="subscribe",
            from_jid="unknown@test.com",
            to_jid="account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_subscribe_to_unknown_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_subscribe(Presence(\
            stanza_type = "subscribe", \
            from_jid = "user1@test.com",\
            to_jid = "unknown@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)

    def test_handle_presence_subscribe_to_registered_handlers(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.presence_subscribe_handlers += [(DefaultSubscribeHandler(self.comp),)]
        model.db_connect()
        account11 = Account(user_jid = "user1@test.com", \
                            name = "account11", \
                            jid = "account11@jcl.test.com")
        account12 = Account(user_jid = "user1@test.com", \
                            name = "account12", \
                            jid = "account12@jcl.test.com")
        account2 = Account(user_jid = "user2@test.com", \
                           name = "account2", \
                           jid = "account2@jcl.test.com")
        model.db_disconnect()
        result = self.comp.handle_presence_subscribe(Presence(\
            stanza_type = "subscribe", \
            from_jid = "user1@test.com",\
            to_jid = "user1%test.com@jcl.test.com"))
        sent = self.comp.stream.sent
        self.assertEqual(len(sent), 2)
        self.assertTrue(type(sent[0]), Presence)
        self.assertEquals(sent[0].get_type(), "subscribe")
        self.assertTrue(type(sent[1]), Presence)
        self.assertEquals(sent[1].get_type(), "subscribed")

    def test_handle_presence_subscribed(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.handle_presence_subscribed(None)
        self.assertEqual(len(self.comp.stream.sent), 0)

    def test_handle_presence_unsubscribe_to_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unsubscribe(Presence(\
            stanza_type="unsubscribe",
            from_jid="user1@test.com",
            to_jid="account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 2)
        presence = presence_sent[0]
        self.assertEqual(presence.get_from(), "account11@jcl.test.com")
        self.assertEqual(presence.get_to(), "user1@test.com")
        self.assertEqual(presence.xpath_eval("@type")[0].get_content(),
                         "unsubscribe")
        presence = presence_sent[1]
        self.assertEqual(presence.get_from(), "account11@jcl.test.com")
        self.assertEqual(presence.get_to(), "user1@test.com")
        self.assertEqual(presence.xpath_eval("@type")[0].get_content(),
                         "unsubscribed")
        model.db_connect()
        self.assertEquals(account.get_account("user1@test.com", "account11"),
                          None)
        self.assertEquals(account.get_accounts_count("user1@test.com"),
                          1)
        self.assertEquals(account.get_all_accounts_count(),
                          2)
        model.db_disconnect()

    def test_handle_presence_unsubscribe_to_registered_handlers(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.presence_unsubscribe_handlers += [(DefaultUnsubscribeHandler(self.comp),)]
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unsubscribe(Presence(\
            stanza_type="unsubscribe",
            from_jid="user1@test.com",
            to_jid="user1%test.com@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 2)
        presence = presence_sent[0]
        self.assertEqual(presence.get_from(), "user1%test.com@jcl.test.com")
        self.assertEqual(presence.get_to(), "user1@test.com")
        self.assertEqual(presence.xpath_eval("@type")[0].get_content(),
                         "unsubscribe")
        presence = presence_sent[1]
        self.assertEqual(presence.get_from(), "user1%test.com@jcl.test.com")
        self.assertEqual(presence.get_to(), "user1@test.com")
        self.assertEqual(presence.xpath_eval("@type")[0].get_content(),
                         "unsubscribed")

    def test_handle_presence_unsubscribe_to_account_unknown_user(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unsubscribe(Presence(\
            stanza_type="unsubscribe",
            from_jid="unknown@test.com",
            to_jid="account11@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)
        model.db_connect()
        self.assertEquals(account.get_all_accounts_count(),
                          3)
        model.db_disconnect()

    def test_handle_presence_unsubscribe_to_unknown_account(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        account2 = Account(user_jid ="user2@test.com",
                           name="account2",
                           jid="account2@jcl.test.com")
        model.db_disconnect()
        self.comp.handle_presence_unsubscribe(Presence(\
            stanza_type="unsubscribe",
            from_jid="user1@test.com",
            to_jid="unknown@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 0)
        model.db_connect()
        self.assertEquals(account.get_all_accounts_count(),
                          3)
        model.db_disconnect()

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

    def test_handle_presence_unsubscribed_to_registered_handler(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.handle_presence_unsubscribed(Presence(\
            stanza_type = "unsubscribed", \
            from_jid = "user1@test.com",\
            to_jid = "user1%test.com@jcl.test.com"))
        presence_sent = self.comp.stream.sent
        self.assertEqual(len(presence_sent), 1)
        self.assertEqual(presence_sent[0].get_to(), "user1@test.com")
        self.assertEqual(presence_sent[0].get_from(), "user1%test.com@jcl.test.com")
        self.assertEqual(\
            presence_sent[0].xpath_eval("@type")[0].get_content(), \
            "unavailable")

    def test_handle_message_password(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.authenticated()
        model.db_connect()
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
        model.db_disconnect()
        self.comp.handle_message(Message(\
            from_jid = "user1@test.com", \
            to_jid = "account11@jcl.test.com", \
            subject = "[PASSWORD]", \
            body = "secret"))
        messages_sent = self.comp.stream.sent
        self.assertEqual(len(messages_sent), 0)

    def test_handle_message_password_complex(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.authenticated()
        model.db_connect()
        account11 = ExampleAccount(user_jid = "user1@test.com", \
                                   name = "account11", \
                                   jid = "account11@jcl.test.com")
        account11.waiting_password_reply = True
        account12 = ExampleAccount(user_jid = "user1@test.com", \
                                   name = "account12", \
                                   jid = "account12@jcl.test.com")
        account2 = ExampleAccount(user_jid = "user2@test.com", \
                                  name = "account2", \
                                  jid = "account2@jcl.test.com")
        model.db_disconnect()
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

    def test_send_error_first(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        _account = Account(user_jid = "user1@test.com", \
                           name = "account11", \
                           jid = "account11@jcl.test.com")
        exception = Exception("test exception")
        self.comp.send_error(_account, exception)
        self.assertEqual(len(self.comp.stream.sent), 1)
        error_sent = self.comp.stream.sent[0]
        self.assertEqual(error_sent.get_to(), _account.user_jid)
        self.assertEqual(error_sent.get_from(), _account.jid)
        self.assertEqual(error_sent.get_type(), "error")
        self.assertEqual(error_sent.get_subject(), _account.default_lang_class.error_subject)
        self.assertEqual(error_sent.get_body(), _account.default_lang_class.error_body \
                         % (exception))
        model.db_disconnect()

    def test_send_error_second(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        _account = Account(user_jid = "user1@test.com", \
                           name = "account11", \
                           jid = "account11@jcl.test.com")
        _account.in_error = True
        exception = Exception("test exception")
        self.comp.send_error(_account, exception)
        self.assertEqual(len(self.comp.stream.sent), 0)

    def test_send_stanzas(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        msg1 = Message()
        msg2 = Message()
        self.comp.send_stanzas([msg1, msg2])
        self.assertEquals(len(self.comp.stream.sent), 2)
        self.assertEquals(self.comp.stream.sent[0], msg1)
        self.assertEquals(self.comp.stream.sent[1], msg2)

    def test_send_stanzas_none(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        self.comp.send_stanzas(None)
        self.assertEquals(len(self.comp.stream.sent), 0)


    ###########################################################################
    # 'handle_command' tests
    ###########################################################################
    def test_handle_command_execute_list(self):
        self.comp.stream = MockStream()
        self.comp.stream_class = MockStream
        model.db_connect()
        account11 = ExampleAccount(user_jid="user1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user_jid="user1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account2 = ExampleAccount(user_jid="user2@test.com",
                                  name="account2",
                                  jid="account2@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content("http://jabber.org/protocol/commands",
                                                  "command")
        command_node.setProp("node", "list")
        command_node.setProp("action", "execute")
        self.comp.handle_command(info_query)
        result = self.comp.stream.sent
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        command_result = result[0].xpath_eval("c:command",
                                              {"c": "http://jabber.org/protocol/commands"})
        self.assertEquals(len(command_result), 1)
        self.assertEquals(command_result[0].prop("status"), "completed")
        items = result[0].xpath_eval("c:command/data:x/data:item",
                                     {"c": "http://jabber.org/protocol/commands",
                                      "data": "jabber:x:data"})
        self.assertEquals(len(items), 2)

class Handler_TestCase(JCLTestCase):
    def setUp(self):
        self.handler = Handler(None)
        JCLTestCase.setUp(self, tables=[Account])

    def test_filter(self):
        model.db_connect()
        account11 = Account(user_jid="user1@test.com",
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user_jid="user1@test.com",
                            name="account12",
                            jid="account12@jcl.test.com")
        accounts = self.handler.filter(None, None)
        accounts_count = 0
        for account in accounts:
            accounts_count += 1
        self.assertEquals(accounts_count, 2)
        model.db_disconnect()

    def test_handle(self):
        self.assertEquals(self.handler.handle(None, None, None), [])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(JCLComponent_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(Handler_TestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
