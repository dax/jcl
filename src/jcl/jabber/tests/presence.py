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

from pyxmpp.presence import Presence

from jcl.jabber.presence import DefaultSubscribeHandler, \
     DefaultUnsubscribeHandler, DefaultPresenceHandler

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

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DefaultSubscribeHandler_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(DefaultUnsubscribeHandler_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(DefaultPresenceHandler_TestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
