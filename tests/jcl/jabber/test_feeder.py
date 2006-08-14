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
from sqlobject import *

from tests.jcl.jabber.test_component import JCLComponent_TestCase

from jcl.jabber.feeder import Feeder, Sender
from jcl.model.account import Account

class FeederComponent_TestCase(JCLComponent_TestCase):
    pass
    
class Feeder_TestCase(unittest.TestCase):
    def setUp(self):
        connection = sqlhub.processConnection = connectionForURI('sqlite:/:memory:')
        Account.createTable()

    def tearDown(self):
        Account.dropTable(ifExists = True)
        
    def test_feed_exist(self):
        feeder = Feeder()
        feeder.feed(Account(user_jid = "test@test.com", \
                            name = "test"))
        self.assertTrue(True)

class Sender_TestCase(unittest.TestCase):
    def setUp(self):
        connection = sqlhub.processConnection = connectionForURI('sqlite:/:memory:')
        Account.createTable()

    def tearDown(self):
        Account.dropTable(ifExists = True)

    def test_send_exist(self):
        sender = Sender()
        account = Account(user_jid = "test@test.com", \
                          name = "test")
        sender.send(to_account = account, \
                    message = "Hello World")
        self.assertTrue(True)
