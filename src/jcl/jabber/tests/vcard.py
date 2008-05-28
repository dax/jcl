# -*- coding: utf-8 -*-
##
## vcard.py
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
import logging
import sys
from ConfigParser import ConfigParser

from pyxmpp.iq import Iq

import jcl.tests
from jcl.lang import Lang
from jcl.jabber.component import JCLComponent
from jcl.model.account import Account, User
from jcl.jabber.vcard import DefaultVCardHandler

from jcl.model.tests.account import ExampleAccount
from jcl.tests import JCLTestCase

class DefaultVCardHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, Account, ExampleAccount])
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.db_url)
        self.handler = DefaultVCardHandler(self.comp)
        self.comp.config = ConfigParser()
        self.comp.config.read("src/jcl/tests/jcl.conf")

    def test_filter(self):
        """Test DefaultVCardHandler filter. Accept any stanza"""
        self.assertEquals(self.handler.filter(None, None), True)

    def test_handle(self):
        """Test default VCard returned"""
        result = self.handler.handle(Iq(from_jid="jcl.test.com",
                                        to_jid="user@test.com",
                                        stanza_type="get"),
                                     Lang.en, True)
        self.assertEquals(len(result), 1)
        result[0].xmlnode.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='user@test.com' to='jcl.test.com' type='result'>"
                + "<vCard xmlns='vcard-temp'>"
                + "<URL>" + self.comp.config.get("vcard", "url") + "</URL>"
                + "<N><FAMILY>" + self.comp.name + "</FAMILY>"
                + "<GIVEN></GIVEN>"
                + "<MIDDLE></MIDDLE>"
                + "<PREFIX></PREFIX>"
                + "<SUFFIX></SUFFIX></N>"
                + "<FN>" + self.comp.name + "</FN>"
                + "</vCard></iq>",
                result[0].xmlnode, True))

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(DefaultVCardHandler_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    if '-v' in sys.argv:
        logger.setLevel(logging.INFO)
    unittest.main(defaultTest='suite')
