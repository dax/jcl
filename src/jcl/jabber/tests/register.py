# -*- coding: utf-8 -*-
##
## register.py
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

from pyxmpp.iq import Iq
from pyxmpp.jabber.dataforms import Form

from jcl.tests import JCLTestCase
from jcl.model.tests.account import ExampleAccount

from jcl.lang import Lang
from jcl.model.account import User, Account
from jcl.jabber.component import JCLComponent
from jcl.jabber.register import SetRegisterHandler

class SetRegisterHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, Account, ExampleAccount])
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.db_url)
        self.handler = SetRegisterHandler(self.comp)

    def test_handle_valid_name(self):
        """Test with invalid supplied name"""
        iq_set = Iq(stanza_type="set",
                    from_jid="user1@test.com/res",
                    to_jid="jcl.test.com")
        x_data = Form("submit")
        x_data.add_field(name="name",
                         value="good_name",
                         field_type="text-single")
        result = self.handler.handle(iq_set, Lang.en, None, x_data)
        self.assertEquals(result, None)

    def test_handle_invalid_name_with_invalid_char(self):
        """Test with invalid supplied name"""
        iq_set = Iq(stanza_type="set",
                    from_jid="user1@test.com/res",
                    to_jid="jcl.test.com")
        x_data = Form("submit")
        x_data.add_field(name="name",
                         value="wrong@name",
                         field_type="text-single")
        result = self.handler.handle(iq_set, Lang.en, None, x_data)
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].xmlnode.prop("type"), "error")
        error = result[0].get_error()
        self.assertEquals(error.get_condition().name, "not-acceptable")
        self.assertEquals(error.get_text(), Lang.en.field_error \
                              % ("name", Lang.en.arobase_in_name_forbidden))

    def test_handle_invalid_name_with_whitespace(self):
        """Test with invalid supplied name"""
        iq_set = Iq(stanza_type="set",
                    from_jid="user1@test.com/res",
                    to_jid="jcl.test.com")
        x_data = Form("submit")
        x_data.add_field(name="name",
                         value="wrong name",
                         field_type="text-single")
        result = self.handler.handle(iq_set, Lang.en, None, x_data)
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].xmlnode.prop("type"), "error")
        error = result[0].get_error()
        self.assertEquals(error.get_condition().name, "not-acceptable")
        self.assertEquals(error.get_text(), Lang.en.field_error \
                              % ("name", Lang.en.arobase_in_name_forbidden))

    def test_handle_invalid_empty_name(self):
        """Test with empty supplied name"""
        iq_set = Iq(stanza_type="set",
                    from_jid="user1@test.com/res",
                    to_jid="jcl.test.com")
        x_data = Form("submit")
        x_data.add_field(name="name",
                         value="",
                         field_type="text-single")
        result = self.handler.handle(iq_set, Lang.en, None, x_data)
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].xmlnode.prop("type"), "error")
        error = result[0].get_error()
        self.assertEquals(error.get_condition().name, "not-acceptable")
        self.assertEquals(error.get_text(), Lang.en.field_error \
                              % ("name", Lang.en.mandatory_field))

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(SetRegisterHandler_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
