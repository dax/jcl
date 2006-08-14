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
from sqlobject import *

from jcl.jabber.component import JCLComponent
from jcl.model.account import Account
from jcl.lang import Lang

class MockStream(object):
    def __init__(self):
        self.sended = []
        
    def send(self, iq):
        self.sended.append(iq)

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
        
class JCLComponent_TestCase(unittest.TestCase):
    def setUp(self):
        connection = sqlhub.processConnection = connectionForURI('sqlite:/:memory:')
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347")
        
    def tearDown(self):
        Account.dropTable(ifExists = True)

    def test_constructor(self):
        self.assertTrue(Account._connection.tableExists("account"))

    def test_authenticated_handler(self):
        self.comp.stream = MockStream()
        self.comp.authenticated()
        self.assertTrue(True)

    def test_authenticated_send_probe(self):
        account11 = Account(user_jid = "test1@test.com", \
                            name = "test11")
        account12 = Account(user_jid = "test1@test.com", \
                            name = "test12")
        account2 = Account(user_jid = "test2@test.com", \
                           name = "test2")
        self.comp.stream = stream = MockStream()
        self.comp.authenticated()

        presence_sended = stream.sended
        self.assertEqual(len(presence_sended), 5)
        self.assertEqual(len([presence \
                              for presence in presence_sended \
                              if presence.get_from_jid() == "jcl.test.com"]), \
                         2)
        self.assertEqual(len([presence \
                              for presence in presence_sended \
                              if presence.get_to_jid() == "test1@test.com"]), \
                         3)
        self.assertEqual(len([presence \
                              for presence in presence_sended \
                              if presence.get_to_jid() == "test2@test.com"]), \
                         2)
        
    def test_get_reg_form(self):
        self.comp.get_reg_form(Lang.en, Account)
        self.assertTrue(True)

    def test_get_reg_form_init(self):
        account = Account(user_jid = "", name = "")
        self.comp.get_reg_form_init(Lang.en, account)
        self.assertTrue(True)

    def test_disco_get_info(self):
        pass

    def test_disco_get_items(self):
        pass

    def test_handle_get_version(self):
        pass

    def test_handle_get_register(self):
        pass

    def test_handle_set_register(self):
        pass

    def test_handle_presence_available(self):
        pass

    def test_handle_presence_unavailable(self):
        pass
    
    def test_handle_presence_subscribe(self):
        pass

    def test_handle_presence_subscribed(self):
        pass

    def test_handle_presence_unsubscribe(self):
        pass

    def test_handle_presence_unsubscribed(self):
        pass

    def test_handle_message(self):
        pass

    def test_handle_tick(self):
        self.comp.handle_tick()
        self.assertTrue(True)

