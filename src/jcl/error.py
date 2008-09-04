##
## error.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Sun Nov  5 20:13:48 2006 David Rousselie
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

"""Jabber exception classes"""

__revision__ = "$Id: error.py,v 1.1 2006/11/05 20:13:48 dax Exp $"

from jcl.lang import Lang

class FieldError(Exception):
    """Error raised when error exists on Jabber Data Form fields"""

    def __init__(self, field,
                 message_property=None, lang_class=Lang.en,
                 detailed_message=None):
        Exception.__init__(self)
        self.field = field
        self.lang_class = lang_class
        self.message_property = message_property
        self.detailed_message = detailed_message

    def __str__(self):
        full_message = ""
        if self.detailed_message is not None:
            full_message = self.detailed_message
        elif self.message_property is not None \
                and hasattr(self.lang_class, self.message_property):
            full_message = str(getattr(self.lang_class, self.message_property))
        return self.lang_class.field_error % (str(self.field), full_message)

class MandatoryFieldError(FieldError):
    """Error raised when a mandatory field in a Form is not supplied"""

    def __init__ (self, field):
        FieldError.__init__(self, field, message_property="mandatory_field")

class NotWellFormedFieldError(FieldError):
    """Error raised when a supplied field in a Form is not well formed"""

    def __init__ (self, field, detailed_message=None):
        FieldError.__init__(self, field,
                            message_property="not_well_formed_field",
                            detailed_message=detailed_message)
