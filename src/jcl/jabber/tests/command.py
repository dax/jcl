##
## command.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Jun 27 08:23:04 2007 David Rousselie
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
from pyxmpp.jabber.dataforms import Form
from pyxmpp.iq import Iq
from pyxmpp.message import Message

from jcl.lang import Lang
from jcl.jabber.component import JCLComponent
import jcl.jabber.command as command
from jcl.jabber.command import FieldNoType, JCLCommandManager
import jcl.model as model
import jcl.model.account as account
from jcl.model.account import Account, LegacyJID
from jcl.model.tests.account import ExampleAccount, Example2Account
from jcl.tests import JCLTestCase

class FieldNoType_TestCase(unittest.TestCase):
    def test_complete_xml_element(self):
        fake_iq = Iq(stanza_type="get",
                     from_jid="user1@test.com")
        field = FieldNoType(name="name",
                            label="Account name")
        field.complete_xml_element(fake_iq.xmlnode, None)
        self.assertFalse(fake_iq.xmlnode.hasProp("type"))

class CommandManager_TestCase(unittest.TestCase):
    def test_get_short_command_name_form_long_name(self):
        command_name = command.command_manager.get_short_command_name("http://jabber.org/protocol/admin#test-command")
        self.assertEquals(command_name, "test_command")

    def test_get_short_command_name(self):
        command_name = command.command_manager.get_short_command_name("test-command")
        self.assertEquals(command_name, "test_command")

class JCLCommandManager_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[Account, ExampleAccount,
                                        Example2Account, LegacyJID])
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347")
        self.command_manager = JCLCommandManager(self.comp,
                                                 self.comp.account_manager)

    def __check_actions(self, info_query, expected_actions=None, action_index=0):
        actions = info_query.xpath_eval("c:command/c:actions",
                                        {"c": "http://jabber.org/protocol/commands"})
        if expected_actions is None:
            self.assertEquals(len(actions), 0)
        else:
            self.assertEquals(len(actions), 1)
            self.assertEquals(actions[0].prop("execute"),
                              expected_actions[action_index])
            children = actions[0].children
            for action in expected_actions:
                self.assertNotEquals(children, None)
                self.assertEquals(children.name, action)
                children = children.next

    def test_add_form_select_user_jids(self):
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        self.command_manager.add_form_select_user_jids(command_node, Lang.en)
        user_jid_field = info_query.xpath_eval("c:command/data:x/data:field[1]",
                                               {"c": "http://jabber.org/protocol/commands",
                                                "data": "jabber:x:data"})
        self.assertNotEquals(user_jid_field, None)
        self.assertEquals(len(user_jid_field), 1)
        self.assertEquals(user_jid_field[0].prop("var"), "user_jids")
        self.assertEquals(user_jid_field[0].prop("type"), "jid-multi")
        self.assertEquals(user_jid_field[0].prop("label"), Lang.en.field_user_jid)

    def test_add_form_select_user_jid(self):
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        self.command_manager.add_form_select_user_jid(command_node, Lang.en)
        user_jid_field = info_query.xpath_eval("c:command/data:x/data:field[1]",
                                               {"c": "http://jabber.org/protocol/commands",
                                                "data": "jabber:x:data"})
        self.assertNotEquals(user_jid_field, None)
        self.assertEquals(len(user_jid_field), 1)
        self.assertEquals(user_jid_field[0].prop("var"), "user_jid")
        self.assertEquals(user_jid_field[0].prop("type"), "jid-single")
        self.assertEquals(user_jid_field[0].prop("label"), Lang.en.field_user_jid)

    def test_add_form_select_accounts(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account31 = ExampleAccount(user_jid="test3@test.com",
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user_jid="test3@test.com",
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        session_context = {}
        session_context["user_jids"] = ["test1@test.com", "test2@test.com"]
        self.command_manager.add_form_select_accounts(session_context,
                                                      command_node,
                                                      Lang.en)
        fields = info_query.xpath_eval("c:command/data:x/data:field",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(fields), 1)
        self.assertEquals(fields[0].prop("var"), "account_names")
        self.assertEquals(fields[0].prop("type"), "list-multi")
        self.assertEquals(fields[0].prop("label"), "Account")
        options = info_query.xpath_eval("c:command/data:x/data:field[1]/data:option",
                                        {"c": "http://jabber.org/protocol/commands",
                                         "data": "jabber:x:data"})
        self.assertEquals(len(options), 4)
        self.assertEquals(options[0].prop("label"),
                          "account11 (Example) (test1@test.com)")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[0].children.content,
                          "account11/test1@test.com")
        self.assertEquals(options[1].prop("label"),
                          "account21 (Example) (test2@test.com)")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[1].children.content,
                          "account21/test2@test.com")
        self.assertEquals(options[2].prop("label"),
                          "account11 (Example) (test2@test.com)")
        self.assertEquals(options[2].children.name, "value")
        self.assertEquals(options[2].children.content,
                          "account11/test2@test.com")
        self.assertEquals(options[3].prop("label"),
                          "account12 (Example2) (test1@test.com)")
        self.assertEquals(options[3].children.name, "value")
        self.assertEquals(options[3].children.content,
                          "account12/test1@test.com")

    def test_add_form_select_accounts_filtered(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.enabled = False
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account31 = ExampleAccount(user_jid="test3@test.com",
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user_jid="test3@test.com",
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        session_context = {}
        session_context["user_jids"] = ["test1@test.com", "test2@test.com"]
        self.command_manager.add_form_select_accounts(session_context,
                                                      command_node,
                                                      Lang.en,
                                                      Account.q.enabled==True)
        fields = info_query.xpath_eval("c:command/data:x/data:field",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(fields), 1)
        self.assertEquals(fields[0].prop("var"), "account_names")
        self.assertEquals(fields[0].prop("type"), "list-multi")
        self.assertEquals(fields[0].prop("label"), "Account")
        options = info_query.xpath_eval("c:command/data:x/data:field[1]/data:option",
                                        {"c": "http://jabber.org/protocol/commands",
                                         "data": "jabber:x:data"})
        self.assertEquals(len(options), 3)
        self.assertEquals(options[0].prop("label"),
                          "account11 (Example) (test1@test.com)")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[0].children.content,
                          "account11/test1@test.com")
        self.assertEquals(options[1].prop("label"),
                          "account11 (Example) (test2@test.com)")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[1].children.content,
                          "account11/test2@test.com")
        self.assertEquals(options[2].prop("label"),
                          "account12 (Example2) (test1@test.com)")
        self.assertEquals(options[2].children.name, "value")
        self.assertEquals(options[2].children.content,
                          "account12/test1@test.com")

    def test_add_form_select_account(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account31 = ExampleAccount(user_jid="test3@test.com",
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user_jid="test3@test.com",
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        session_context = {}
        session_context["user_jid"] = ["test1@test.com"]
        self.command_manager.add_form_select_account(session_context,
                                                     command_node,
                                                     Lang.en)
        fields = info_query.xpath_eval("c:command/data:x/data:field",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(fields), 1)
        self.assertEquals(fields[0].prop("var"), "account_name")
        self.assertEquals(fields[0].prop("type"), "list-single")
        self.assertEquals(fields[0].prop("label"), "Account")
        options = info_query.xpath_eval("c:command/data:x/data:field[1]/data:option",
                                        {"c": "http://jabber.org/protocol/commands",
                                         "data": "jabber:x:data"})
        self.assertEquals(len(options), 2)
        self.assertEquals(options[0].prop("label"),
                          "account11 (Example) (test1@test.com)")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[0].children.content,
                          "account11/test1@test.com")
        self.assertEquals(options[1].prop("label"),
                          "account12 (Example2) (test1@test.com)")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[1].children.content,
                          "account12/test1@test.com")

    def test_execute_add_user(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#add-user")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#add-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        options = result[0].xpath_eval("c:command/data:x/data:field[1]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 2)
        self.assertEquals(options[0].prop("label"), "Example")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[0].children.content, "Example")
        self.assertEquals(options[1].prop("label"), "Example2")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[1].children.content, "Example2")
        user_jid_field = result[0].xpath_eval("c:command/data:x/data:field[2]",
                                              {"c": "http://jabber.org/protocol/commands",
                                               "data": "jabber:x:data"})
        self.assertNotEquals(user_jid_field, None)
        self.assertEquals(len(user_jid_field), 1)
        self.assertEquals(user_jid_field[0].prop("var"), "user_jid")
        self.assertEquals(user_jid_field[0].prop("type"), "jid-single")
        self.assertEquals(user_jid_field[0].prop("label"), Lang.en.field_user_jid)

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#add-user")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-single",
                              name="account_type",
                              value="Example")
        submit_form.add_field(field_type="jid-single",
                              name="user_jid",
                              value="user2@test.com")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#add-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 6)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["account_type"], ["Example"])
        self.assertEquals(context_session["user_jid"], ["user2@test.com"])

        # Third step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#add-user")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="text-single",
                              name="name",
                              value="account1")
        submit_form.add_field(field_type="text-single",
                              name="login",
                              value="login1")
        submit_form.add_field(field_type="text-private",
                              name="password",
                              value="pass1")
        submit_form.add_field(field_type="boolean",
                              name="store_password",
                              value="1")
        submit_form.add_field(field_type="list-single",
                              name="test_enum",
                              value="choice2")
        submit_form.add_field(field_type="text-single",
                              name="test_int",
                              value="42")
        submit_form.as_xml(command_node)

        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#add-user",
                                                           "execute")
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])

        self.assertEquals(context_session["name"], ["account1"])
        self.assertEquals(context_session["login"], ["login1"])
        self.assertEquals(context_session["password"], ["pass1"])
        self.assertEquals(context_session["store_password"], ["1"])
        self.assertEquals(context_session["test_enum"], ["choice2"])
        self.assertEquals(context_session["test_int"], ["42"])

        model.db_connect()
        _account = account.get_account("user2@test.com",
                                       "account1")
        self.assertNotEquals(_account, None)
        self.assertEquals(_account.user_jid, "user2@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        model.db_disconnect()

        stanza_sent = result
        self.assertEquals(len(stanza_sent), 4)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com")
        self.assertEquals(iq_result.get_to(), "user1@test.com")

        presence_component = stanza_sent[1]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "jcl.test.com")
        self.assertEquals(presence_component.get_to(), "user2@test.com")
        self.assertEquals(presence_component.get_node().prop("type"),
                          "subscribe")

        message = stanza_sent[2]
        self.assertTrue(isinstance(message, Message))
        self.assertEquals(message.get_from(), "jcl.test.com")
        self.assertEquals(message.get_to(), "user2@test.com")
        self.assertEquals(message.get_subject(),
                          _account.get_new_message_subject(Lang.en))
        self.assertEquals(message.get_body(),
                          _account.get_new_message_body(Lang.en))

        presence_account = stanza_sent[3]
        self.assertTrue(isinstance(presence_account, Presence))
        self.assertEquals(presence_account.get_from(), "account1@jcl.test.com")
        self.assertEquals(presence_account.get_to(), "user2@test.com")
        self.assertEquals(presence_account.get_node().prop("type"),
                          "subscribe")

    def test_execute_add_user_prev(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#add-user")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#add-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        options = result[0].xpath_eval("c:command/data:x/data:field[1]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 2)
        self.assertEquals(options[0].prop("label"), "Example")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[0].children.content, "Example")
        self.assertEquals(options[1].prop("label"), "Example2")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[1].children.content, "Example2")
        user_jid_field = result[0].xpath_eval("c:command/data:x/data:field[2]",
                                              {"c": "http://jabber.org/protocol/commands",
                                               "data": "jabber:x:data"})
        self.assertNotEquals(user_jid_field, None)
        self.assertEquals(len(user_jid_field), 1)
        self.assertEquals(user_jid_field[0].prop("var"), "user_jid")
        self.assertEquals(user_jid_field[0].prop("type"), "jid-single")
        self.assertEquals(user_jid_field[0].prop("label"), Lang.en.field_user_jid)

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#add-user")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-single",
                              name="account_type",
                              value="Example")
        submit_form.add_field(field_type="jid-single",
                              name="user_jid",
                              value="user2@test.com")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#add-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 6)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["account_type"], ["Example"])
        self.assertEquals(context_session["user_jid"], ["user2@test.com"])

        # First step again
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#add-user")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "prev")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="text-single",
                              name="name",
                              value="account1")
        submit_form.add_field(field_type="text-single",
                              name="login",
                              value="login1")
        submit_form.add_field(field_type="text-private",
                              name="password",
                              value="pass1")
        submit_form.add_field(field_type="boolean",
                              name="store_password",
                              value="1")
        submit_form.add_field(field_type="list-single",
                              name="test_enum",
                              value="choice2")
        submit_form.add_field(field_type="text-single",
                              name="test_int",
                              value="42")
        submit_form.as_xml(command_node)

        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#add-user",
                                                           "prev")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["next"])
        options = result[0].xpath_eval("c:command/data:x/data:field[1]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 2)
        self.assertEquals(options[0].prop("label"), "Example")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[0].children.content, "Example")
        self.assertEquals(options[1].prop("label"), "Example2")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[1].children.content, "Example2")
        user_jid_field = result[0].xpath_eval("c:command/data:x/data:field[2]",
                                              {"c": "http://jabber.org/protocol/commands",
                                               "data": "jabber:x:data"})
        self.assertNotEquals(user_jid_field, None)
        self.assertEquals(len(user_jid_field), 1)
        self.assertEquals(user_jid_field[0].prop("var"), "user_jid")
        self.assertEquals(user_jid_field[0].prop("type"), "jid-single")
        self.assertEquals(user_jid_field[0].prop("label"), Lang.en.field_user_jid)

    def test_execute_add_user_cancel(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#add-user")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#add-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        options = result[0].xpath_eval("c:command/data:x/data:field[1]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 2)
        self.assertEquals(options[0].prop("label"), "Example")
        self.assertEquals(options[0].children.name, "value")
        self.assertEquals(options[0].children.content, "Example")
        self.assertEquals(options[1].prop("label"), "Example2")
        self.assertEquals(options[1].children.name, "value")
        self.assertEquals(options[1].children.content, "Example2")
        user_jid_field = result[0].xpath_eval("c:command/data:x/data:field[2]",
                                              {"c": "http://jabber.org/protocol/commands",
                                               "data": "jabber:x:data"})
        self.assertNotEquals(user_jid_field, None)
        self.assertEquals(len(user_jid_field), 1)
        self.assertEquals(user_jid_field[0].prop("var"), "user_jid")
        self.assertEquals(user_jid_field[0].prop("type"), "jid-single")
        self.assertEquals(user_jid_field[0].prop("label"), Lang.en.field_user_jid)

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#add-user")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "cancel")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#add-user",
                                                           "cancel")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "canceled")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.assertEquals(xml_command.children, None)


    def test_execute_delete_user(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account31 = ExampleAccount(user_jid="test3@test.com",
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user_jid="test3@test.com",
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#delete-user")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#delete-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#delete-user")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-multi",
                              name="user_jids",
                              values=["test1@test.com", "test2@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#delete-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jids"],
                          ["test1@test.com", "test2@test.com"])

        # Third step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#delete-user")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-multi",
                              name="account_names",
                              values=["account11/test1@test.com",
                                      "account11/test2@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#delete-user",
                                                           "execute")
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        self.assertEquals(context_session["account_names"],
                          ["account11/test1@test.com",
                           "account11/test2@test.com"])
        test1_accounts = account.get_accounts("test1@test.com")
        count = 0
        for test1_account in test1_accounts:
            count += 1
            self.assertEquals(test1_account.name, "account12")
        self.assertEquals(count, 1)
        test2_accounts = account.get_accounts("test2@test.com")
        count = 0
        for test2_account in test2_accounts:
            count += 1
            self.assertEquals(test2_account.name, "account21")
        self.assertEquals(count, 1)
        test3_accounts = account.get_accounts("test3@test.com")
        count = 0
        for test3_account in test3_accounts:
            count += 1
        self.assertEquals(count, 2)
        stanza_sent = result
        self.assertEquals(len(stanza_sent), 5)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com")
        self.assertEquals(iq_result.get_to(), "user1@test.com")
        presence_component = stanza_sent[1]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "account11@jcl.test.com")
        self.assertEquals(presence_component.get_to(), "test1@test.com")
        self.assertEquals(presence_component.get_node().prop("type"),
                          "unsubscribe")
        presence_component = stanza_sent[2]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "account11@jcl.test.com")
        self.assertEquals(presence_component.get_to(), "test1@test.com")
        self.assertEquals(presence_component.get_node().prop("type"),
                          "unsubscribed")
        presence_component = stanza_sent[3]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "account11@jcl.test.com")
        self.assertEquals(presence_component.get_to(), "test2@test.com")
        self.assertEquals(presence_component.get_node().prop("type"),
                          "unsubscribe")
        presence_component = stanza_sent[4]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "account11@jcl.test.com")
        self.assertEquals(presence_component.get_to(), "test2@test.com")
        self.assertEquals(presence_component.get_node().prop("type"),
                          "unsubscribed")

    def test_execute_disable_user(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.enabled = True
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.enabled = False
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.enabled = False
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.enabled = True
        account31 = ExampleAccount(user_jid="test3@test.com",
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account31.enabled = False
        account32 = Example2Account(user_jid="test3@test.com",
                                    name="account32",
                                    jid="account32@jcl.test.com")
        account32.enabled = False
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#disable-user")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#disable-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#disable-user")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-multi",
                              name="user_jids",
                              values=["test1@test.com", "test2@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#disable-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jids"],
                          ["test1@test.com", "test2@test.com"])
        options = result[0].xpath_eval("c:command/data:x/data:field[1]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 2)

        # Third step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#disable-user")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-multi",
                              name="account_names",
                              values=["account11/test1@test.com",
                                      "account11/test2@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#disable-user",
                                                           "execute")
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        self.assertEquals(context_session["account_names"],
                          ["account11/test1@test.com",
                           "account11/test2@test.com"])
        for _account in account.get_all_accounts():
            self.assertFalse(_account.enabled)

    def test_execute_reenable_user(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.enabled = False
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.enabled = True
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.enabled = True
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.enabled = False
        account31 = ExampleAccount(user_jid="test3@test.com",
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account31.enabled = True
        account32 = Example2Account(user_jid="test3@test.com",
                                    name="account32",
                                    jid="account32@jcl.test.com")
        account32.enabled = True
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#reenable-user")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#reenable-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#reenable-user")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-multi",
                              name="user_jids",
                              values=["test1@test.com", "test2@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#reenable-user",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jids"],
                          ["test1@test.com", "test2@test.com"])
        options = result[0].xpath_eval("c:command/data:x/data:field[1]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 2)

        # Third step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#reenable-user")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-multi",
                              name="account_names",
                              values=["account11/test1@test.com",
                                      "account11/test2@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#reenable-user",
                                                           "execute")
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        self.assertEquals(context_session["account_names"],
                          ["account11/test1@test.com",
                           "account11/test2@test.com"])
        for _account in account.get_all_accounts():
            self.assertTrue(_account.enabled)

    def test_execute_end_user_session(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = account.ONLINE
        account31 = ExampleAccount(user_jid="test3@test.com",
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user_jid="test3@test.com",
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#end-user-session")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#end-user-session",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#end-user-session")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-multi",
                              name="user_jids",
                              values=["test1@test.com", "test2@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#end-user-session",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jids"],
                          ["test1@test.com", "test2@test.com"])
        options = result[0].xpath_eval("c:command/data:x/data:field[1]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 2)

        # Third step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#end-user-session")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-multi",
                              name="account_names",
                              values=["account11/test1@test.com",
                                      "account11/test2@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#end-user-session",
                                                           "execute")
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        self.assertEquals(context_session["account_names"],
                          ["account11/test1@test.com",
                           "account11/test2@test.com"])
        stanza_sent = result
        self.assertEquals(len(stanza_sent), 3)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com")
        self.assertEquals(iq_result.get_to(), "user1@test.com")
        presence_component = stanza_sent[1]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "account11@jcl.test.com")
        self.assertEquals(presence_component.get_to(), "test1@test.com")
        self.assertEquals(presence_component.get_node().prop("type"),
                          "unavailable")
        presence_component = stanza_sent[2]
        self.assertTrue(isinstance(presence_component, Presence))
        self.assertEquals(presence_component.get_from(), "account11@jcl.test.com")
        self.assertEquals(presence_component.get_to(), "test2@test.com")
        self.assertEquals(presence_component.get_node().prop("type"),
                          "unavailable")

    def test_execute_get_user_password(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.password = "pass1"
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-password")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-password",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-password")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-single",
                              name="user_jid",
                              value="test1@test.com")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-password",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jid"],
                          ["test1@test.com"])

        # Third step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-password")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-single",
                              name="account_name",
                              value="account11/test1@test.com")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-password",
                                                           "execute")
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        self.assertEquals(context_session["account_name"],
                          ["account11/test1@test.com"])
        stanza_sent = result
        self.assertEquals(len(stanza_sent), 1)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com")
        self.assertEquals(iq_result.get_to(), "user1@test.com")
        fields = iq_result.xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 3)
        self.assertEquals(fields[0].prop("var"), "FORM_TYPE")
        self.assertEquals(fields[0].prop("type"), "hidden")
        self.assertEquals(fields[0].children.name, "value")
        self.assertEquals(fields[0].children.content,
                          "http://jabber.org/protocol/admin")
        self.assertEquals(fields[1].prop("var"), "accountjids")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content,
                          "test1@test.com")
        self.assertEquals(fields[2].prop("var"), "password")
        self.assertEquals(fields[2].children.name, "value")
        self.assertEquals(fields[2].children.content,
                          "pass1")

    def test_execute_change_user_password(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.password = "pass1"
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#change-user-password")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#change-user-password",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#change-user-password")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-single",
                              name="user_jid",
                              value="test1@test.com")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#change-user-password",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jid"],
                          ["test1@test.com"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)

        # Third step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#change-user-password")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-single",
                              name="account_name",
                              value="account11/test1@test.com")
        submit_form.add_field(field_type="text-private",
                              name="password",
                              value="pass2")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#change-user-password",
                                                           "execute")
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        self.assertEquals(context_session["account_name"],
                          ["account11/test1@test.com"])
        self.assertEquals(context_session["password"],
                          ["pass2"])
        self.assertEquals(account11.password, "pass2")

    def test_execute_get_user_roster(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        ljid111 = LegacyJID(legacy_address="test111@test.com",
                            jid="test111%test.com@test.com",
                            account=account11)
        ljid112 = LegacyJID(legacy_address="test112@test.com",
                            jid="test112%test.com@test.com",
                            account=account11)
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        ljid121 = LegacyJID(legacy_address="test121@test.com",
                            jid="test121%test.com@test.com",
                            account=account12)
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        ljid211 = LegacyJID(legacy_address="test211@test.com",
                            jid="test211%test.com@test.com",
                            account=account21)
        ljid212 = LegacyJID(legacy_address="test212@test.com",
                            jid="test212%test.com@test.com",
                            account=account21)
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        ljid221 = LegacyJID(legacy_address="test221@test.com",
                            jid="test221%test.com@test.com",
                            account=account22)
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-roster")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-roster",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["complete"])

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-roster")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-single",
                              name="user_jid",
                              value="test1@test.com")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-roster",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jid"],
                          ["test1@test.com"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[0].prop("var"), "FORM_TYPE")
        self.assertEquals(fields[0].prop("type"), "hidden")
        self.assertEquals(fields[0].children.name, "value")
        self.assertEquals(fields[0].children.content,
                          "http://jabber.org/protocol/admin")
        items = result[0].xpath_eval("c:command/data:x/roster:query/roster:item",
                                     {"c": "http://jabber.org/protocol/commands",
                                      "data": "jabber:x:data",
                                      "roster": "jabber:iq:roster"})
        self.assertEquals(len(items), 3)
        self.assertEquals(items[0].prop("jid"), "test111%test.com@test.com")
        self.assertEquals(items[0].prop("name"), "test111@test.com")
        self.assertEquals(items[1].prop("jid"), "test112%test.com@test.com")
        self.assertEquals(items[1].prop("name"), "test112@test.com")
        self.assertEquals(items[2].prop("jid"), "test121%test.com@test.com")
        self.assertEquals(items[2].prop("name"), "test121@test.com")

    def test_execute_get_user_lastlogin(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        account11 = ExampleAccount(user_jid="test1@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user_jid="test1@test.com",
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user_jid="test2@test.com",
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user_jid="test2@test.com",
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-lastlogin")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-lastlogin",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-lastlogin")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-single",
                              name="user_jid",
                              value="test1@test.com")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-lastlogin",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0], ["prev", "complete"], 1)
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jid"],
                          ["test1@test.com"])

        # Third step
        info_query = Iq(stanza_type="set",
                        from_jid="user1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-lastlogin")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "complete")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-single",
                              name="account_name",
                              value="account11/test1@test.com")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-lastlogin",
                                                           "execute")
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        self.assertEquals(context_session["account_name"],
                          ["account11/test1@test.com"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 3)
        self.assertEquals(fields[0].prop("var"), "FORM_TYPE")
        self.assertEquals(fields[0].prop("type"), "hidden")
        self.assertEquals(fields[0].children.name, "value")
        self.assertEquals(fields[0].children.content,
                          "http://jabber.org/protocol/admin")
        self.assertEquals(fields[1].prop("var"), "user_jid")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content, "test1@test.com")
        self.assertEquals(fields[2].prop("var"), "lastlogin")
        self.assertEquals(fields[2].children.name, "value")
        self.assertEquals(fields[2].children.content, account11.lastlogin.isoformat(" "))

#     def test_execute_user_stats(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_edit_blacklist(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_add_to_blacklist_in(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_add_to_blacklist_out(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_edit_whitelist(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_add_to_whitelist_in(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_add_to_whitelist_out(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_registered_users_num(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_disabled_users_num(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_online_users_num(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_active_users_num(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_idle_users_num(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_registered_users_list(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_disabled_users_list(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_online_users(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_active_users(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_get_idle_users(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_announce(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_set_motd(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_edit_motd(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_delete_motd(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_set_welcome(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_delete_welcome(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_edit_admin(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_restart(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

#     def test_execute_shutdown(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="user1@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CommandManager_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(FieldNoType_TestCase, 'test'))
    suite.addTest(unittest.makeSuite(JCLCommandManager_TestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
