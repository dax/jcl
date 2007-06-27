# -*- coding: utf-8 -*-
##
## component.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jun 27 21:42:47 2007 David Rousselie
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

from pyxmpp.presence import Presence

from jcl.jabber import Handler

class DefaultPresenceHandler(Handler):
    """Handle presence"""

    def handle(self, presence, lang_class, data):
        """Return same presence as receive one"""
        to_jid = presence.get_to()
        from_jid = presence.get_from()
        presence.set_to(from_jid)
        presence.set_from(to_jid)
        return [presence]

class DefaultSubscribeHandler(Handler):
    """Return default response to subscribe queries"""

    def handle(self, stanza, lang_class, data):
        """Create subscribe response"""
        result = []
        result.append(Presence(from_jid=stanza.get_to(),
                               to_jid=stanza.get_from(),
                               stanza_type="subscribe"))
        result.append(Presence(from_jid=stanza.get_to(),
                               to_jid=stanza.get_from(),
                               stanza_type="subscribed"))
        return result

class DefaultUnsubscribeHandler(Handler):
    """Return default response to subscribe queries"""

    def handle(self, stanza, lang_class, data):
        """Create subscribe response"""
        result = []
        result.append(Presence(from_jid=stanza.get_to(),
                               to_jid=stanza.get_from(),
                               stanza_type="unsubscribe"))
        result.append(Presence(from_jid=stanza.get_to(),
                               to_jid=stanza.get_from(),
                               stanza_type="unsubscribed"))
        return result

