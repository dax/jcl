##
## test_lang.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Nov 22 19:19:25 2006 David Rousselie
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
from jcl.lang import Lang

from pyxmpp.iq import Iq

class Lang_TestCase(unittest.TestCase):
    def setUp(self):
        self.lang = Lang()

    def tearDown(self):
        self.lang = None
        
    def test_get_lang_class_exist(self):
        lang_class = self.lang.get_lang_class("fr")
        self.assertEquals(lang_class, Lang.fr)

    def test_get_lang_class_not_exist(self):
        lang_class = self.lang.get_lang_class("not_exist")
        self.assertEquals(lang_class, Lang.en)
        
    def test_get_lang_class_long_code(self):
        lang_class = self.lang.get_lang_class("fr_FR")
        self.assertEquals(lang_class, Lang.fr)
        
    def test_get_lang_from_node(self):
        iq = Iq(from_jid = "test@test.com", \
                to_jid = "test2@test.com", \
                stanza_type = "get")
        iq_node = iq.get_node()
        iq_node.setLang("fr")
        lang = self.lang.get_lang_from_node(iq_node)
        self.assertEquals(lang, "fr")

    def test_get_lang_class_from_node(self):
        iq = Iq(from_jid = "test@test.com", \
                to_jid = "test2@test.com", \
                stanza_type = "get")
        iq_node = iq.get_node()
        iq_node.setLang("fr")
        lang = self.lang.get_lang_class_from_node(iq_node)
        self.assertEquals(lang, Lang.fr)

    def test_get_default_lang_class(self):
        self.assertEquals(self.lang.get_default_lang_class(), Lang.en)

    def test_get_default_lang_class_other(self):
        self.lang = Lang("fr")
        self.assertEquals(self.lang.get_default_lang_class(), Lang.fr)

class Language_TestCase(unittest.TestCase):
    """Test language classes"""

    def setUp(self):
        """must define self.lang_class. Lang.en is default"""
        self.lang_class = Lang.en

    def test_strings(self):
        self.assertNotEquals(self.lang_class.component_name, None)
        self.assertNotEquals(self.lang_class.register_title, None)
        self.assertNotEquals(self.lang_class.register_instructions, None)
        self.assertNotEquals(self.lang_class.message_status, None)
        self.assertNotEquals(self.lang_class.account_name, None)

        self.assertNotEquals(self.lang_class.password_saved_for_session, None)
        self.assertNotEquals(self.lang_class.ask_password_subject, None)
        self.assertNotEquals(self.lang_class.ask_password_body % (""), None)
        self.assertNotEquals(self.lang_class.new_account_message_subject % (""), None)
        self.assertNotEquals(self.lang_class.new_account_message_body, None)
        self.assertNotEquals(self.lang_class.update_account_message_subject % (""), None)
        self.assertNotEquals(self.lang_class.update_account_message_body, None)

        self.assertNotEquals(self.lang_class.mandatory_field % (""), None)

        self.assertNotEquals(self.lang_class.field_chat_action, None)
        self.assertNotEquals(self.lang_class.field_online_action, None)
        self.assertNotEquals(self.lang_class.field_away_action, None)
        self.assertNotEquals(self.lang_class.field_xa_action, None)
        self.assertNotEquals(self.lang_class.field_dnd_action, None)
        self.assertNotEquals(self.lang_class.field_offline_action, None)

        self.assertNotEquals(self.lang_class.field_action_0, None)
        self.assertNotEquals(self.lang_class.field_chat_action_0, None)
        self.assertNotEquals(self.lang_class.field_online_action_0, None)
        self.assertNotEquals(self.lang_class.field_away_action_0, None)
        self.assertNotEquals(self.lang_class.field_xa_action_0, None)
        self.assertNotEquals(self.lang_class.field_dnd_action_0, None)
        self.assertNotEquals(self.lang_class.field_offline_action_0, None)

        self.assertNotEquals(self.lang_class.check_error_subject, None)
        self.assertNotEquals(self.lang_class.check_error_body % (""), None)


class Language_fr_TestCase(Language_TestCase):
    def setUp(self):
        self.lang_class = Lang.fr

class Language_nl_TestCase(Language_TestCase):
    def setUp(self):
        self.lang_class = Lang.nl

class Language_es_TestCase(Language_TestCase):
    def setUp(self):
        self.lang_class = Lang.es

class Language_pl_TestCase(Language_TestCase):
    def setUp(self):
        self.lang_class = Lang.pl

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Lang_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(Language_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(Language_fr_TestCase, 'test'))
#    suite.addTest(unittest.makeSuite(Language_nl_TestCase, 'test'))
#    suite.addTest(unittest.makeSuite(Language_es_TestCase, 'test'))
#    suite.addTest(unittest.makeSuite(Language_pl_TestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')