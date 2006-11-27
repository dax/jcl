##
## test_x.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Nov 22 19:24:19 2006 David Rousselie
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

from jcl.jabber.x import *
from pyxmpp.stanza import common_doc
import libxml2

class DataForm_TestCase(unittest.TestCase):
    def setUp(self):
        self.data_form = DataForm()

    def tearDown(self):
        self.data_form = None
        
    def test_add_field(self):
        self.data_form = DataForm()
        field = self.data_form.add_field(field_type = "single-text", \
                                         label = "Name", \
                                         var = "name", \
                                         value = "jcl")
        self.assertEquals(self.data_form.fields["name"], field)
        self.assertTrue(field in self.data_form.fields_tab)
        self.assertEquals(field.type, "single-text")
        self.assertEquals(field.label, "Name")
        self.assertEquals(field.var, "name")
        self.assertEquals(field.value, "jcl")
        self.assertEquals(field.required, False)

    def test_add_required_field(self):
        self.data_form = DataForm()
        field = self.data_form.add_field(field_type = "single-text", \
                                         label = "Name", \
                                         var = "name", \
                                         value = "jcl", \
                                         required = True)
        self.assertEquals(self.data_form.fields["name"], field)
        self.assertTrue(field in self.data_form.fields_tab)
        self.assertEquals(field.type, "single-text")
        self.assertEquals(field.label, "Name")
        self.assertEquals(field.var, "name")
        self.assertEquals(field.value, "jcl")
        self.assertEquals(field.required, True)

    def test_get_field_value(self):
        self.data_form.add_field(field_type = "single-text", \
                                 var = "name", \
                                 value = "jcl")
        self.assertEquals(self.data_form.get_field_value("name"), \
                          "jcl")

    def test_get_field_value_not_exist(self):
        self.assertEquals(self.data_form.get_field_value("name"), \
                          None)

    def test_get_field_value_post_func(self):
        self.data_form.add_field(field_type = "single-text", \
                                 var = "name", \
                                 value = "jcl")
        self.assertEquals(self.data_form.get_field_value("name", \
                            post_func = (lambda value: "_" + value + "_")), \
                          "_jcl_")

    def test_get_field_value_post_func(self):
        self.assertEquals(self.data_form.get_field_value("name", \
            default_func = (lambda field_name: "no '" + field_name + "' field")), \
                          "no 'name' field")

    def test_attach_xml(self):
        parent_node = common_doc.newChild(None, "iq", None)
        self.data_form.title = "JCL Form"
        self.data_form.instructions = "Fill the form"
        self.data_form.add_field(label = "label1", \
                                 var = "var1")
        self.data_form.add_field(label = "label2", \
                                 var = "var2")
        self.data_form.xmlns = "jabber:x:data"
        data_form_node = self.data_form.attach_xml(parent_node)
        context = common_doc.xpathNewContext()
        context.setContextNode(parent_node)
        context.xpathRegisterNs("jxd", "jabber:x:data")
        self.assertEquals(context.xpathEval("jxd:x/jxd:title")[0].content, "JCL Form")
        self.assertEquals(context.xpathEval("jxd:x/jxd:instructions")[0].content, "Fill the form")
        self.assertEquals(len(context.xpathEval("jxd:x/jxd:field")), 2)
        self.assertEquals(context.xpathEval("jxd:x/jxd:field")[0].prop("type"), "fixed")
        self.assertEquals(context.xpathEval("jxd:x/jxd:field")[0].prop("label"), "label1")
        self.assertEquals(context.xpathEval("jxd:x/jxd:field")[0].prop("var"), "var1")
        self.assertEquals(context.xpathEval("jxd:x/jxd:field")[1].prop("type"), "fixed")
        self.assertEquals(context.xpathEval("jxd:x/jxd:field")[1].prop("label"), "label2")
        self.assertEquals(context.xpathEval("jxd:x/jxd:field")[1].prop("var"), "var2")
        context.xpathFreeContext()

    def test_from_xml(self):
        xml_buffer = "<x xmlns='jabber:x:data'>" \
        "<field type='text-single' var='var1'><value>value1</value></field>" \
        "<field type='text-single' var='var2'><value>value2</value></field>" \
        "</x>"
        xml_node = libxml2.parseMemory(xml_buffer, len(xml_buffer))
        self.data_form.from_xml(xml_node.children)
        self.assertEquals(len(self.data_form.fields_tab), 2)
        field1 = self.data_form.fields["var1"]
        self.assertEquals(field1.type, "text-single")
        self.assertEquals(field1.var, "var1")
        self.assertEquals(field1.value, "value1")
        field2 = self.data_form.fields["var2"]
        self.assertEquals(field2.type, "text-single")
        self.assertEquals(field2.var, "var2")
        self.assertEquals(field2.value, "value2")
        
class Field_TestCase(unittest.TestCase):
    def test_get_xml_no_option_required(self):
        field = Field(field_type = "text-single", \
                      label = "Name", \
                      var = "name", \
                      value = "myaccount", \
                      required = True)
        parent_node = common_doc.newChild(None, "x", None)
        xml_field = field.get_xml(parent_node)
        self.assertEquals(xml_field.prop("type"), "text-single")
        self.assertEquals(xml_field.prop("label"), "Name")
        self.assertEquals(xml_field.prop("var"), "name")
        self.assertEquals(xml_field.xpathEval("value")[0].content, "myaccount")
        self.assertEquals(len(xml_field.xpathEval("required")), 1)

    def test_get_xml_with_option(self):
        field = Field(field_type = "text-single", \
                      label = "Name", \
                      var = "name", \
                      value = "myaccount")
        field.add_option("test_option", "option_value")
        parent_node = common_doc.newChild(None, "x", None)
        xml_field = field.get_xml(parent_node)
        self.assertEquals(xml_field.prop("type"), "text-single")
        self.assertEquals(xml_field.prop("label"), "Name")
        self.assertEquals(xml_field.prop("var"), "name")
        self.assertEquals(xml_field.xpathEval("value")[0].content, "myaccount")
        self.assertEquals(\
            xml_field.xpathEval("option['label=test_option']/value")[0].content, \
            "option_value")

    def test_get_xml_no_parent(self):
        field = Field(field_type = "text-single", \
                      label = "Name", \
                      var = "name", \
                      value = "myaccount")
        self.assertRaises(Exception, field.get_xml, None)

class Option_TestCase(unittest.TestCase):
    def test_get_xml(self):
        option = Option("test_option", "option_value")
        xml_option = option.get_xml(None)
        self.assertEquals(xml_option.prop("label"), "test_option")
        self.assertEquals(xml_option.xpathEval("value")[0].content, \
                          "option_value")

