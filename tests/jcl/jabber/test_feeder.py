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

from sqlobject import *
from sqlobject.dbconnection import TheURIOpener

from tests.jcl.jabber.test_component import JCLComponent_TestCase, MockStream

from jcl.jabber.component import JCLComponent
from jcl.jabber.feeder import FeederComponent, Feeder, Sender
from jcl.model.account import Account
from jcl.model import account

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
        
    def tearDown(self):
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.dropTable(ifExists = True)
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

    # handle_tick is implemented in FeederComponent
    def test_run_ni_handle_tick(self):
        pass
    
    def test_handle_tick(self):
        # TODO
        self.comp.handle_tick()
        self.assertTrue(True)
        
class Feeder_TestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.createTable()

    def tearDown(self):
        Account.dropTable(ifExists = True)
        del account.hub.threadConnection
#        os.unlink(DB_PATH)
        
    def test_feed_exist(self):
        feeder = Feeder()
        feeder.feed(Account(user_jid = "test@test.com", \
                            name = "test", \
                            jid = "test@jcl.test.com"))
        self.assertTrue(True)

class Sender_TestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        account.hub.threadConnection = connectionForURI('sqlite://' + DB_URL)
        Account.createTable()

    def tearDown(self):
        Account.dropTable(ifExists = True)
        del account.hub.threadConnection
#        os.unlink(DB_PATH)
        
    def test_send_exist(self):
        sender = Sender()
        account = Account(user_jid = "test@test.com", \
                          name = "test", \
                          jid = "test@jcl.test.com")
        sender.send(to_account = account, \
                    data = "Hello World")
        self.assertTrue(True)
