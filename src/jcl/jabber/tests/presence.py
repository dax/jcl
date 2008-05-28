##
## presence.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Fri Jul  6 21:45:43 2007 David Rousselie
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
import tempfile
import os
from ConfigParser import ConfigParser
import time

from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.iq import Iq

from jcl.jabber.component import JCLComponent
from jcl.jabber.presence import DefaultSubscribeHandler, \
     DefaultUnsubscribeHandler, DefaultPresenceHandler, \
     RootPresenceAvailableHandler, AccountPresenceAvailableHandler, \
     AccountPresenceUnavailableHandler, DefaultIQLastHandler
from jcl.model.account import User, LegacyJID, Account
from jcl.lang import Lang

from jcl.tests import JCLTestCase

class DefaultIQLastHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, LegacyJID, Account])
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 None)
        self.handler = DefaultIQLastHandler(self.comp)

    def test_handle(self):
        info_query = Iq(from_jid="user1@test.com",
                        to_jid="jcl.test.com",
                        stanza_type="get")
        self.comp.last_activity = int(time.time())
        time.sleep(1)
        result = self.handler.handle(info_query, None, [])
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "jcl.test.com")
        self.assertEquals(result[0].get_type(), "result")
        self.assertNotEquals(result[0].xmlnode.children, None)
        self.assertEquals(result[0].xmlnode.children.name, "query")
        self.assertEquals(int(result[0].xmlnode.children.prop("seconds")), 1)

class DefaultSubscribeHandler_TestCase(unittest.TestCase):
    def setUp(self):
        self.handler = DefaultSubscribeHandler(None)

    def test_handle(self):
        presence = Presence(from_jid="user1@test.com",
                            to_jid="user1%test.com@jcl.test.com",
                            stanza_type="subscribe")
        result = self.handler.handle(presence, None, [])
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "user1%test.com@jcl.test.com")
        self.assertEquals(result[0].get_type(), "subscribe")
        self.assertEquals(result[1].get_to(), "user1@test.com")
        self.assertEquals(result[1].get_from(), "user1%test.com@jcl.test.com")
        self.assertEquals(result[1].get_type(), "subscribed")

class DefaultUnsubscribeHandler_TestCase(unittest.TestCase):
    def setUp(self):
        self.handler = DefaultUnsubscribeHandler(None)

    def test_handle(self):
        presence = Presence(from_jid="user1@test.com",
                            to_jid="user1%test.com@jcl.test.com",
                            stanza_type="unsubscribe")
        result = self.handler.handle(presence, None, [])
        self.assertEquals(len(result), 2)
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "user1%test.com@jcl.test.com")
        self.assertEquals(result[0].get_type(), "unsubscribe")
        self.assertEquals(result[1].get_to(), "user1@test.com")
        self.assertEquals(result[1].get_from(), "user1%test.com@jcl.test.com")
        self.assertEquals(result[1].get_type(), "unsubscribed")

class DefaultPresenceHandler_TestCase(unittest.TestCase):
    def setUp(self):
        self.handler = DefaultPresenceHandler(None)

    def test_handle_away(self):
        presence = Presence(from_jid="user1@test.com",
                            to_jid="user1%test.com@jcl.test.com",
                            stanza_type="available",
                            show="away")
        result = self.handler.handle(presence, None, [])
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "user1%test.com@jcl.test.com")
        self.assertEquals(result[0].get_type(), None)
        self.assertEquals(result[0].get_show(), "away")

    def test_handle_offline(self):
        presence = Presence(from_jid="user1@test.com",
                            to_jid="user1%test.com@jcl.test.com",
                            stanza_type="unavailable")
        result = self.handler.handle(presence, None, [])
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "user1%test.com@jcl.test.com")
        self.assertEquals(result[0].get_type(), "unavailable")

class RootPresenceAvailableHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, LegacyJID, Account])
        self.config = ConfigParser()
        self.config_file = tempfile.mktemp(".conf", "jcltest", "/tmp")
        self.config.read(self.config_file)
        self.config.add_section("component")
        self.config.set("component", "motd", "Message Of The Day")
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.config)
        self.handler = RootPresenceAvailableHandler(self.comp)

    def tearDown(self):
        JCLTestCase.tearDown(self)
        if os.path.exists(self.config_file):
            os.unlink(self.config_file)

    def test_get_root_presence(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="available",
                            from_jid="user1@test.com",
                            to_jid="jcl.test.com")
        self.assertFalse(user1.has_received_motd)
        result = self.handler.get_root_presence(presence, Lang.en, 2)
        self.assertTrue(user1.has_received_motd)
        self.assertEquals(len(result), 2)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "jcl.test.com")
        self.assertTrue(isinstance(result[1], Message))
        self.assertEquals(result[1].get_to(), "user1@test.com")
        self.assertEquals(result[1].get_from(), "jcl.test.com")
        self.assertEquals(result[1].get_body(), "Message Of The Day")

    def test_get_root_presence_with_resource(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="available",
                            from_jid="user1@test.com/resource",
                            to_jid="jcl.test.com")
        self.assertFalse(user1.has_received_motd)
        result = self.handler.get_root_presence(presence, Lang.en, 2)
        self.assertTrue(user1.has_received_motd)
        self.assertEquals(len(result), 2)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com/resource")
        self.assertEquals(result[0].get_from(), "jcl.test.com")
        self.assertTrue(isinstance(result[1], Message))
        self.assertEquals(result[1].get_to(), "user1@test.com/resource")
        self.assertEquals(result[1].get_from(), "jcl.test.com")
        self.assertEquals(result[1].get_body(), "Message Of The Day")

    def test_get_root_presence_already_received_motd(self):
        user1 = User(jid="user1@test.com")
        user1.has_received_motd = True
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="available",
                            from_jid="user1@test.com",
                            to_jid="jcl.test.com")
        self.assertTrue(user1.has_received_motd)
        result = self.handler.get_root_presence(presence, Lang.en, 2)
        self.assertTrue(user1.has_received_motd)
        self.assertEquals(len(result), 1)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "jcl.test.com")

    def test_get_root_presence_no_motd(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="available",
                            from_jid="user1@test.com",
                            to_jid="jcl.test.com")
        self.assertFalse(user1.has_received_motd)
        self.config.remove_option("component", "motd")
        result = self.handler.get_root_presence(presence, Lang.en, 2)
        self.assertTrue(user1.has_received_motd)
        self.assertEquals(len(result), 1)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "jcl.test.com")
        self.assertEquals(result[0].get_show(), "online")
        self.assertEquals(result[0].get_status(), "2" + Lang.en.message_status)

class AccountPresenceAvailableHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, LegacyJID, Account])
        self.config = ConfigParser()
        self.config_file = tempfile.mktemp(".conf", "jcltest", "/tmp")
        self.config.read(self.config_file)
        self.config.add_section("component")
        self.config.set("component", "motd", "Message Of The Day")
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.config)
        self.handler = AccountPresenceAvailableHandler(self.comp)

    def tearDown(self):
        JCLTestCase.tearDown(self)
        if os.path.exists(self.config_file):
            os.unlink(self.config_file)

    def test_get_account_presence(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="available",
                            from_jid="user1@test.com",
                            to_jid="account11@jcl.test.com")
        result = self.handler.get_account_presence(presence, Lang.en, account11)
        self.assertEquals(len(result), 1)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "account11@jcl.test.com")
        self.assertEquals(result[0].get_show(), "online")
        self.assertEquals(result[0].get_status(), "account11")

    def test_get_account_presence_with_resource(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="available",
                            from_jid="user1@test.com/resource",
                            to_jid="account11@jcl.test.com")
        result = self.handler.get_account_presence(presence, Lang.en, account11)
        self.assertEquals(len(result), 1)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com/resource")
        self.assertEquals(result[0].get_from(), "account11@jcl.test.com")
        self.assertEquals(result[0].get_show(), "online")
        self.assertEquals(result[0].get_status(), "account11")

    def test_get_disabled_account_presence(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account11.enabled = False
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="available",
                            from_jid="user1@test.com",
                            to_jid="account11@jcl.test.com")
        result = self.handler.get_account_presence(presence, Lang.en, account11)
        self.assertEquals(len(result), 1)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "account11@jcl.test.com")
        self.assertEquals(result[0].get_show(), "xa")
        self.assertEquals(result[0].get_status(), Lang.en.account_disabled)

    def test_get_inerror_account_presence(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account11.error = "Error"
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="available",
                            from_jid="user1@test.com",
                            to_jid="account11@jcl.test.com")
        result = self.handler.get_account_presence(presence, Lang.en, account11)
        self.assertEquals(len(result), 1)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "account11@jcl.test.com")
        self.assertEquals(result[0].get_show(), "dnd")
        self.assertEquals(result[0].get_status(), Lang.en.account_error)

class AccountPresenceUnavailableHandler_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[User, LegacyJID, Account])
        self.config = ConfigParser()
        self.config_file = tempfile.mktemp(".conf", "jcltest", "/tmp")
        self.config.read(self.config_file)
        self.config.add_section("component")
        self.config.set("component", "motd", "Message Of The Day")
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.config)
        self.handler = AccountPresenceUnavailableHandler(self.comp)

    def tearDown(self):
        JCLTestCase.tearDown(self)
        if os.path.exists(self.config_file):
            os.unlink(self.config_file)

    def test_get_account_presence(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="unavailable",
                            from_jid="user1@test.com",
                            to_jid="account11@jcl.test.com")
        result = self.handler.get_account_presence(presence, Lang.en, account11)
        self.assertEquals(len(result), 1)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com")
        self.assertEquals(result[0].get_from(), "account11@jcl.test.com")
        self.assertEquals(result[0].get_type(), "unavailable")

    def test_get_account_presence_with_resource(self):
        user1 = User(jid="user1@test.com")
        account11 = Account(user=user1,
                            name="account11",
                            jid="account11@jcl.test.com")
        account12 = Account(user=user1,
                            name="account12",
                            jid="account12@jcl.test.com")
        presence = Presence(stanza_type="unavailable",
                            from_jid="user1@test.com/resource",
                            to_jid="account11@jcl.test.com")
        result = self.handler.get_account_presence(presence, Lang.en, account11)
        self.assertEquals(len(result), 1)
        self.assertTrue(isinstance(result[0], Presence))
        self.assertEquals(result[0].get_to(), "user1@test.com/resource")
        self.assertEquals(result[0].get_from(), "account11@jcl.test.com")
        self.assertEquals(result[0].get_type(), "unavailable")

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(DefaultIQLastHandler_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(DefaultSubscribeHandler_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(DefaultUnsubscribeHandler_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(DefaultPresenceHandler_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(RootPresenceAvailableHandler_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(AccountPresenceAvailableHandler_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(AccountPresenceUnavailableHandler_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
