# -*- coding: utf-8 -*-
##
## vcard.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jun 20 08:19:57 2007 David Rousselie
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

from pyxmpp.jabber.vcard import VCard, VCardName, VCardString

from jcl.jabber import Handler

class DefaultVCardHandler(Handler):
    """Default VCard Handler. Return a VCard for all requests"""

    def filter(self, stanza, lang_class):
        """
        Do not filter any stanza
        """
        return True

    def handle(self, stanza, lang_class, data):
        """
        Return default VCard
        """
        print "Handling VCard"
        vcard_response = stanza.make_result_response()
        vcard_rfc_tab = [u"BEGIN:VCARD",
                         VCardName("N", self.component.name).rfc2426()]
        if self.component.config.has_section("vcard"):
            config = self.component.config
            vcard_rfc_tab += [VCardString(field.upper(),
                                          unicode(config.get("vcard",
                                                             field))).rfc2426()
                              for field in config.options("vcard")]
        vcard_rfc_tab += ["END:VCARD"]
        vcard = VCard("\n".join(vcard_rfc_tab))
        ## Correct PyXMPP bug
        vcard.xml_element_name = "vCard"
        vcard.as_xml(vcard_response.xmlnode)
        return [vcard_response]
