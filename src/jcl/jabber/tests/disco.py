# -*- coding: utf-8 -*-
##
## disco.py
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

from jcl.tests import JCLTestCase
from jcl.model.tests.account import ExampleAccount

from jcl.model.account import User, Account
from jcl.jabber.component import JCLComponent
from jcl.jabber.disco import DiscoHandler, AccountTypeDiscoGetItemsHandler

class DiscoHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, Account, ExampleAccount])
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.db_url)
        self.handler = DiscoHandler(self.comp)

    def test_default_filter(self):
        """Test default filter behavior"""
        self.assertFalse(self.handler.filter(None, None, None))

    def test_default_handler(self):
        """Test default handler: do nothing"""
        self.assertEquals(self.handler.handle(None, None, None, None, None),
                          None)

class AccountTypeDiscoGetItemsHandler_TestCase (JCLTestCase):
    """Test AccountTypeDiscoGetItemsHandler class"""
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, Account, ExampleAccount])
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.db_url)
        self.comp.account_manager.account_classes = (ExampleAccount,)
        self.handler = AccountTypeDiscoGetItemsHandler(self.comp)

    def test_handler_unknown_account_type(self):
        """Test handler with an unknown account type"""
        self.assertEquals(self.handler.handle(Message(from_jid="from@test.com"),
                                              None, None, None,
                                              "Unknown"), [])

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(DiscoHandler_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(AccountTypeDiscoGetItemsHandler_TestCase,
                                          'test'))
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
