##
## x.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Fri Jan  7 11:06:42 2005 
## $Id: x.py,v 1.3 2005/09/18 20:24:07 dax Exp $
## 
## Copyright (C) 2005 
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

"""X -- X data handling
"""

__revision__ = "$Id: x.py,v 1.3 2005/09/18 20:24:07 dax Exp $"

from pyxmpp.stanza import common_doc

class Option(object):
    """Option value for list field
    """
    def __init__(self, label, value):
        self.__label = label
        self.__value = value
    
    def get_xml(self, parent):
        """Return XML Option representation from
        self.__label and self.__value and attach it to parent
        """
        if parent is None:
            option = common_doc.newChild(None, "option", None)
        else:
            option = parent.newChild(None, "option", None)
        option.setProp("label", self.__label)
        option.newChild(None, "value", self.__value)
        return option

class Field(object):
    """Jabber Xdata form Field
    """
    def __init__(self, field_type, label, var, value, required = False):
        self.type = field_type
        self.__label = label
        self.__var = var
        self.value = value
        self.__options = []
        self.required = required

    def add_option(self, label, value):
        """Add an Option to this field
        """
        option = Option(label, value)
        self.__options.append(option)
        return option

    def get_xml(self, parent):
        """Return XML Field representation
        and attach it to parent
        """
        if parent is None:
            raise Exception, "parent field should not be None"
        else:
            field = parent.newChild(None, "field", None)
        field.setProp("type", self.type)
        if not self.__label is None:
            field.setProp("label", self.__label)
        if not self.__var is None:
            field.setProp("var", self.__var)
        if self.value:
            field.newChild(None, "value", self.value)
        if self.required:
            field.newChild(None, "required", None)
        for option in self.__options:
            option.get_xml(field)
        return field

class X(object):
    """Jabber Xdata form
    """
    def __init__(self):
        self.fields = {}
        self.fields_tab = []
        self.title = None
        self.instructions = None
        self.x_type = None
        self.xmlns = None
        
    def add_field(self, \
                  field_type = "fixed", \
                  label = None, \
                  var = None, \
                  value = ""):
        """Add a Field to this Xdata form
        """
        field = Field(field_type, label, var, value)
        self.fields[var] = field
        # fields_tab exist to keep added fields order
        self.fields_tab.append(field)
        return field

    def get_field_value(self, field_name, \
                        post_func = (lambda value: value), \
                        default_func = (lambda field_name: None)):
        """Return field value processed by post_func
        or return default func processing if field does not exist"""
        if self.fields.has_key(field_name):
            return post_func(self.fields[field_name].value)
        return default_func(field_name)
        
    def attach_xml(self, info_query):
        """Attach this Xdata form to iq node
        """
        node = info_query.newChild(None, "x", None)
        _ns = node.newNs(self.xmlns, None)
        node.setNs(_ns)
        if not self.title is None:
            node.newTextChild(None, "title", self.title)
        if not self.instructions is None:
            node.newTextChild(None, "instructions", self.instructions)
        for field in self.fields_tab:
            field.get_xml(node)
        return node

    def from_xml(self, node):
        """Populate this X object from an XML representation
        """
## TODO : test node type and ns and clean that loop !!!!
        while node and node.type != "element":
            node = node.next
        child = node.children
        while child:
## TODO : test child type (element) and ns (jabber:x:data)
            if child.type == "element" and child.name == "field":
                if child.hasProp("type"): 
                    field_type = child.prop("type")
                else:
                    field_type = ""

                if child.hasProp("label"): 
                    label = child.prop("label")
                else:
                    label = ""

                if child.hasProp("var"): 
                    var = child.prop("var")
                else:
                    var = ""

                xval = child.children
                while xval and xval.name != "value":
                    xval = xval.next
                if xval:
                    value = xval.getContent()
                else:
                    value = ""
                field = Field(field_type, label, var, value)
                self.fields[var] = field
            child = child.next
