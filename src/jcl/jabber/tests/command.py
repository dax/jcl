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
import os
import tempfile
from ConfigParser import ConfigParser
import threading

from pyxmpp.jid import JID
from pyxmpp.presence import Presence
from pyxmpp.jabber.dataforms import Form
from pyxmpp.iq import Iq
from pyxmpp.message import Message
from pyxmpp.jabber.disco import DiscoItems

import jcl.tests
from jcl.lang import Lang
from jcl.jabber.component import JCLComponent
import jcl.jabber.command as command
from jcl.jabber.command import FieldNoType, JCLCommandManager
import jcl.model as model
import jcl.model.account as account
from jcl.model.account import Account, LegacyJID, User
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

class MockComponent(object):
    jid = JID("jcl.test.com")

    def get_admins(self):
        return ["admin@test.com"]

class CommandManager_TestCase(unittest.TestCase):
    def test_get_short_command_name_form_long_name(self):
        command_name = command.command_manager.get_short_command_name("http://jabber.org/protocol/admin#test-command")
        self.assertEquals(command_name, "test_command")

    def test_get_short_command_name(self):
        command_name = command.command_manager.get_short_command_name("test-command")
        self.assertEquals(command_name, "test_command")

    def test_list_commands(self):
        command.command_manager.commands["command1"] = True
        command.command_manager.commands["command2"] = False
        command.command_manager.component = MockComponent()
        disco_items = command.command_manager.list_commands(jid="user@test.com",
                                                            disco_items=DiscoItems(),
                                                            lang_class=Lang.en)
        items = disco_items.get_items()
        self.assertEquals(len(items), 1)
        self.assertEquals(items[0].get_node(), "command2")
        self.assertEquals(items[0].get_name(), "command2")

    def test_list_commands_as_admin(self):
        command.command_manager.commands = {}
        command.command_manager.commands["command1"] = True
        command.command_manager.commands["command2"] = False
        command.command_manager.component = MockComponent()
        disco_items = command.command_manager.list_commands(jid="admin@test.com",
                                                            disco_items=DiscoItems(),
                                                            lang_class=Lang.en)
        items = disco_items.get_items()
        self.assertEquals(len(items), 2)
        self.assertEquals(items[0].get_node(), "command1")
        self.assertEquals(items[0].get_name(), "command1")
        self.assertEquals(items[1].get_node(), "command2")
        self.assertEquals(items[1].get_name(), "command2")

    def test_apply_admin_command_action_as_admin(self):
        command.command_manager.commands["command1"] = True
        command.command_manager.apply_execute_command = \
            lambda iq, command_name: [] 
        command.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        result = command.command_manager.apply_command_action(info_query,
                                                              "command1",
                                                              "execute")
        self.assertEquals(result, [])

    def test_apply_admin_command_action_as_user(self):
        command.command_manager.commands["command1"] = True
        command.command_manager.apply_execute_command = \
            lambda iq, command_name: [] 
        command.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        result = command.command_manager.apply_command_action(info_query,
                                                              "command1",
                                                              "execute")
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_type(), "error")
        self.assertEquals(result[0].xmlnode.children.name, "error")
        self.assertEquals(result[0].xmlnode.children.prop("type"), "auth")
        self.assertEquals(result[0].xmlnode.children.children.name, "forbidden")

    def test_apply_non_admin_command_action_as_admin(self):
        command.command_manager.commands["command1"] = False
        command.command_manager.apply_execute_command = \
            lambda iq, command_name: [] 
        command.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        result = command.command_manager.apply_command_action(info_query,
                                                              "command1",
                                                              "execute")
        self.assertEquals(result, [])

    def test_apply_non_admin_command_action_as_user(self):
        command.command_manager.commands["command1"] = False
        command.command_manager.apply_execute_command = \
            lambda iq, command_name: [] 
        command.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        result = command.command_manager.apply_command_action(info_query,
                                                              "command1",
                                                              "execute")
        self.assertEquals(result, [])

    def test_apply_command_non_existing_action(self):
        command.command_manager.commands["command1"] = False
        command.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        result = command.command_manager.apply_command_action(info_query,
                                                              "command1",
                                                              "noexecute")
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_type(), "error")
        self.assertEquals(result[0].xmlnode.children.name, "error")
        self.assertEquals(result[0].xmlnode.children.prop("type"), "cancel")
        self.assertEquals(result[0].xmlnode.children.children.name,
                          "feature-not-implemented")

class JCLCommandManager_TestCase(JCLTestCase):
    def setUp(self):
        JCLTestCase.setUp(self, tables=[Account, ExampleAccount,
                                        Example2Account, LegacyJID,
                                        User])
        self.config_file = tempfile.mktemp(".conf", "jcltest", jcl.tests.DB_DIR)
        self.config = ConfigParser()
        self.config.read(self.config_file)
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.config,
                                 self.config_file)
        self.comp.set_admins(["admin@test.com"])
        self.command_manager = JCLCommandManager(self.comp,
                                                 self.comp.account_manager)

    def tearDown(self):
        JCLTestCase.tearDown(self)
        if os.path.exists(self.config_file):
            os.unlink(self.config_file)

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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        user3 = User(jid="test3@test.com")
        account31 = ExampleAccount(user=user3,
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user=user3,
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.enabled = False
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        user3 = User(jid="test3@test.com")
        account31 = ExampleAccount(user=user3,
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user=user3,
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        user3 = User(jid="test3@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account31 = ExampleAccount(user=user3,
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user=user3,
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        self.assertEquals(_account.user.jid, "user2@test.com")
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@jcl.test.com")
        model.db_disconnect()

        stanza_sent = result
        self.assertEquals(len(stanza_sent), 4)
        iq_result = stanza_sent[0]
        self.assertTrue(isinstance(iq_result, Iq))
        self.assertEquals(iq_result.get_node().prop("type"), "result")
        self.assertEquals(iq_result.get_from(), "jcl.test.com")
        self.assertEquals(iq_result.get_to(), "admin@test.com")
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        user3 = User(jid="test3@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account31 = ExampleAccount(user=user3,
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user=user3,
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        self.assertEquals(iq_result.get_to(), "admin@test.com")
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
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        user3 = User(jid="test3@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.enabled = True
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.enabled = False
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.enabled = False
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.enabled = True
        account31 = ExampleAccount(user=user3,
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account31.enabled = False
        account32 = Example2Account(user=user3,
                                    name="account32",
                                    jid="account32@jcl.test.com")
        account32.enabled = False
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        user3 = User(jid="test3@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.enabled = False
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.enabled = True
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.enabled = True
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.enabled = False
        account31 = ExampleAccount(user=user3,
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account31.enabled = True
        account32 = Example2Account(user=user3,
                                    name="account32",
                                    jid="account32@jcl.test.com")
        account32.enabled = True
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        user3 = User(jid="test3@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = account.ONLINE
        account31 = ExampleAccount(user=user3,
                                   name="account31",
                                   jid="account31@jcl.test.com")
        account32 = Example2Account(user=user3,
                                    name="account32",
                                    jid="account32@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        self.assertEquals(iq_result.get_to(), "admin@test.com")
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
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.password = "pass1"
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        self.assertEquals(iq_result.get_to(), "admin@test.com")
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
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.password = "pass1"
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        ljid111 = LegacyJID(legacy_address="test111@test.com",
                            jid="test111%test.com@test.com",
                            account=account11)
        ljid112 = LegacyJID(legacy_address="test112@test.com",
                            jid="test112%test.com@test.com",
                            account=account11)
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        ljid121 = LegacyJID(legacy_address="test121@test.com",
                            jid="test121%test.com@test.com",
                            account=account12)
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        ljid211 = LegacyJID(legacy_address="test211@test.com",
                            jid="test211%test.com@test.com",
                            account=account21)
        ljid212 = LegacyJID(legacy_address="test212@test.com",
                            jid="test212%test.com@test.com",
                            account=account21)
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        ljid221 = LegacyJID(legacy_address="test221@test.com",
                            jid="test221%test.com@test.com",
                            account=account22)
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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
                        from_jid="admin@test.com",
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

    def test_execute_get_registered_users_num(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-registered-users-num")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-registered-users-num",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "registeredusersnum")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content, "4")

    def test_execute_get_disabled_users_num(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.enabled = False
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.enabled = False
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-disabled-users-num")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-disabled-users-num",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "disabledusersnum")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content, "2")

    def test_execute_get_online_users_num(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = "chat"
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-online-users-num")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-online-users-num",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "onlineusersnum")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content, "3")

    def test_execute_get_registered_users_list(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-registered-users-list")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-registered-users-list",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "registeredusers")
        values = result[0].xpath_eval("c:command/data:x/data:field[2]/data:value",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(values), 4)
        self.assertEquals(values[0].content,
                          "test1@test.com (account11 ExampleAccount)")
        self.assertEquals(values[1].content,
                          "test1@test.com (account12 Example2Account)")
        self.assertEquals(values[2].content,
                          "test2@test.com (account21 ExampleAccount)")
        self.assertEquals(values[3].content,
                          "test2@test.com (account11 ExampleAccount)")

    def test_execute_get_registered_users_list_max(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        for i in xrange(10):
            ExampleAccount(user=user1,
                           name="account11" + str(i),
                           jid="account11" + str(i) + "@jcl.test.com")
            Example2Account(user=user1,
                            name="account12" + str(i),
                            jid="account12" + str(i) + "@jcl.test.com")
            ExampleAccount(user=user2,
                           name="account2" + str(i),
                           jid="account2" + str(i) + "@jcl.test.com")
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node", "http://jabber.org/protocol/admin#get-registered-users-list")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-registered-users-list",
                                                           "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "max_items")
        self.assertEquals(fields[1].prop("type"), "list-single")
        options = result[0].xpath_eval("c:command/data:x/data:field[2]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 6)
        self.assertEquals(options[0].prop("label"), "25")
        self.assertEquals(options[0].content, "25")
        self.assertEquals(options[1].prop("label"), "50")
        self.assertEquals(options[1].content, "50")
        self.assertEquals(options[2].prop("label"), "75")
        self.assertEquals(options[2].content, "75")
        self.assertEquals(options[3].prop("label"), "100")
        self.assertEquals(options[3].content, "100")
        self.assertEquals(options[4].prop("label"), "150")
        self.assertEquals(options[4].content, "150")
        self.assertEquals(options[5].prop("label"), "200")
        self.assertEquals(options[5].content, "200")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#get-registered-users-list")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-single",
                              name="max_items",
                              value="25")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-registered-users-list",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["max_items"],
                          ["25"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[0].prop("var"), "FORM_TYPE")
        self.assertEquals(fields[0].prop("type"), "hidden")
        self.assertEquals(fields[0].children.name, "value")
        self.assertEquals(fields[0].children.content,
                          "http://jabber.org/protocol/admin")
        self.assertEquals(fields[1].prop("var"), "registeredusers")
        values = result[0].xpath_eval("c:command/data:x/data:field[2]/data:value",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(values), 25)
        while i < 7:
            self.assertEquals(values[i * 3].content,
                              "test1@test.com (account11" + str(i)
                              + " ExampleAccount)")
            self.assertEquals(values[i * 3 + 1].content,
                              "test1@test.com (account12" + str(i)
                              + " Example2Account)")
            self.assertEquals(values[i * 3 + 2].content,
                              "test2@test.com (account2" + str(i)
                              + " ExampleAccount)")
        self.assertEquals(values[24].content,
                          "test1@test.com (account118 ExampleAccount)")

    def test_execute_get_disabled_users_list(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.enabled = False
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.enabled = False
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.enabled = False
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#get-disabled-users-list")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-disabled-users-list",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "disabledusers")
        values = result[0].xpath_eval("c:command/data:x/data:field[2]/data:value",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(values), 3)
        self.assertEquals(values[0].content,
                          "test1@test.com (account11 ExampleAccount)")
        self.assertEquals(values[1].content,
                          "test1@test.com (account12 Example2Account)")
        self.assertEquals(values[2].content,
                          "test2@test.com (account11 ExampleAccount)")

    def test_execute_get_disabled_users_list_max(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        for i in xrange(20):
            _account = ExampleAccount(user=user1,
                                      name="account11" + str(i),
                                      jid="account11" + str(i)
                                      + "@jcl.test.com")
            _account.enabled = False
            Example2Account(user=user1,
                            name="account12" + str(i),
                            jid="account12" + str(i) + "@jcl.test.com")
            _account = ExampleAccount(user=user2,
                                      name="account2" + str(i),
                                      jid="account2" + str(i)
                                      + "@jcl.test.com")
            _account.enabled = False
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#get-disabled-users-list")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-disabled-users-list",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "max_items")
        self.assertEquals(fields[1].prop("type"), "list-single")
        options = result[0].xpath_eval("c:command/data:x/data:field[2]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 6)
        self.assertEquals(options[0].prop("label"), "25")
        self.assertEquals(options[0].content, "25")
        self.assertEquals(options[1].prop("label"), "50")
        self.assertEquals(options[1].content, "50")
        self.assertEquals(options[2].prop("label"), "75")
        self.assertEquals(options[2].content, "75")
        self.assertEquals(options[3].prop("label"), "100")
        self.assertEquals(options[3].content, "100")
        self.assertEquals(options[4].prop("label"), "150")
        self.assertEquals(options[4].content, "150")
        self.assertEquals(options[5].prop("label"), "200")
        self.assertEquals(options[5].content, "200")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#get-disabled-users-list")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-single",
                              name="max_items",
                              value="25")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-disabled-users-list",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["max_items"],
                          ["25"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[0].prop("var"), "FORM_TYPE")
        self.assertEquals(fields[0].prop("type"), "hidden")
        self.assertEquals(fields[0].children.name, "value")
        self.assertEquals(fields[0].children.content,
                          "http://jabber.org/protocol/admin")
        self.assertEquals(fields[1].prop("var"), "disabledusers")
        values = result[0].xpath_eval("c:command/data:x/data:field[2]/data:value",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(values), 25)
        i = 0
        while i < 12:
            self.assertEquals(values[i * 2].content,
                              "test1@test.com (account11" + str(i)
                              + " ExampleAccount)")
            self.assertEquals(values[i * 2 + 1].content,
                              "test2@test.com (account2" + str(i)
                              + " ExampleAccount)")
            i += 1
        self.assertEquals(values[24].content,
                          "test1@test.com (account1112 ExampleAccount)")

    def test_execute_get_online_users_list(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = "xa"
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#get-online-users-list")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-online-users-list",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "onlineusers")
        values = result[0].xpath_eval("c:command/data:x/data:field[2]/data:value",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(values), 3)
        self.assertEquals(values[0].content,
                          "test1@test.com (account11 ExampleAccount)")
        self.assertEquals(values[1].content,
                          "test1@test.com (account12 Example2Account)")
        self.assertEquals(values[2].content,
                          "test2@test.com (account11 ExampleAccount)")

    def test_execute_get_online_users_list_max(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        user2 = User(jid="test2@test.com")
        for i in xrange(20):
            _account = ExampleAccount(user=user1,
                                      name="account11" + str(i),
                                      jid="account11" + str(i)
                                      + "@jcl.test.com")
            _account.status = account.ONLINE
            Example2Account(user=user1,
                            name="account12" + str(i),
                            jid="account12" + str(i) + "@jcl.test.com")
            _account = ExampleAccount(user=user2,
                                      name="account2" + str(i),
                                      jid="account2" + str(i)
                                      + "@jcl.test.com")
            _account.status = "away"
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#get-online-users-list")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-online-users-list",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "max_items")
        self.assertEquals(fields[1].prop("type"), "list-single")
        options = result[0].xpath_eval("c:command/data:x/data:field[2]/data:option",
                                       {"c": "http://jabber.org/protocol/commands",
                                        "data": "jabber:x:data"})
        self.assertEquals(len(options), 6)
        self.assertEquals(options[0].prop("label"), "25")
        self.assertEquals(options[0].content, "25")
        self.assertEquals(options[1].prop("label"), "50")
        self.assertEquals(options[1].content, "50")
        self.assertEquals(options[2].prop("label"), "75")
        self.assertEquals(options[2].content, "75")
        self.assertEquals(options[3].prop("label"), "100")
        self.assertEquals(options[3].content, "100")
        self.assertEquals(options[4].prop("label"), "150")
        self.assertEquals(options[4].content, "150")
        self.assertEquals(options[5].prop("label"), "200")
        self.assertEquals(options[5].content, "200")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#get-online-users-list")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-single",
                              name="max_items",
                              value="25")
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-online-users-list",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["max_items"],
                          ["25"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[0].prop("var"), "FORM_TYPE")
        self.assertEquals(fields[0].prop("type"), "hidden")
        self.assertEquals(fields[0].children.name, "value")
        self.assertEquals(fields[0].children.content,
                          "http://jabber.org/protocol/admin")
        self.assertEquals(fields[1].prop("var"), "onlineusers")
        values = result[0].xpath_eval("c:command/data:x/data:field[2]/data:value",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(values), 25)
        i = 0
        while i < 12:
            self.assertEquals(values[i * 2].content,
                              "test1@test.com (account11" + str(i)
                              + " ExampleAccount)")
            self.assertEquals(values[i * 2 + 1].content,
                              "test2@test.com (account2" + str(i)
                              + " ExampleAccount)")
            i += 1
        self.assertEquals(values[24].content,
                          "test1@test.com (account1112 ExampleAccount)")

    def test_execute_announce(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = "xa"
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#announce")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#announce",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "announcement")
        self.assertEquals(fields[1].prop("type"), "text-multi")
        self.assertEquals(fields[1].children.name, "required")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#announce")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="text-multi",
                              name="announcement",
                              value=["test announce"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#announce",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 3)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["announcement"],
                          ["test announce"])
        self.assertEquals(result[1].get_from(), "jcl.test.com")
        self.assertEquals(result[1].get_to(), "test1@test.com")
        self.assertEquals(result[1].get_body(), "test announce")
        self.assertEquals(result[2].get_from(), "jcl.test.com")
        self.assertEquals(result[2].get_to(), "test2@test.com")
        self.assertEquals(result[2].get_body(), "test announce")

    def test_execute_set_motd(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.status = account.OFFLINE
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = account.OFFLINE
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#set-motd")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#set-motd",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "motd")
        self.assertEquals(fields[1].prop("type"), "text-multi")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content, "")
        self.assertEquals(fields[1].children.next.name, "required")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#set-motd")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="text-multi",
                              name="motd",
                              value=["Message Of The Day"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#set-motd",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 2)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["motd"],
                          ["Message Of The Day"])
        self.assertTrue(account11.user.has_received_motd)
        self.assertEquals(result[1].get_from(), "jcl.test.com")
        self.assertEquals(result[1].get_to(), "test1@test.com")
        self.assertEquals(result[1].get_body(), "Message Of The Day")
        self.assertFalse(account21.user.has_received_motd)

    def test_execute_edit_motd(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        self.comp.set_motd("test motd")
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.status = account.OFFLINE
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = account.OFFLINE
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#edit-motd")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#edit-motd",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "motd")
        self.assertEquals(fields[1].prop("type"), "text-multi")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content, "test motd")
        self.assertEquals(fields[1].children.next.name, "required")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#edit-motd")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="text-multi",
                              name="motd",
                              value=["Message Of The Day"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#edit-motd",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 2)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["motd"],
                          ["Message Of The Day"])
        self.assertTrue(account11.user.has_received_motd)
        self.assertEquals(result[1].get_from(), "jcl.test.com")
        self.assertEquals(result[1].get_to(), "test1@test.com")
        self.assertEquals(result[1].get_body(), "Message Of The Day")
        self.assertFalse(account21.user.has_received_motd)
        self.comp.config.read(self.comp.config_file)
        self.assertTrue(self.comp.config.has_option("component", "motd"))
        self.assertEquals(self.comp.config.get("component", "motd"),
                          "Message Of The Day")

    def test_execute_delete_motd(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        self.comp.set_motd("test motd")
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.status = account.OFFLINE
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = account.OFFLINE
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#delete-motd")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#delete-motd",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0])
        self.comp.config.read(self.comp.config_file)
        self.assertFalse(self.comp.config.has_option("component", "motd"))

    def test_execute_set_welcome(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        self.comp.set_welcome_message("Welcome Message")
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.status = account.OFFLINE
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = account.OFFLINE
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#set-welcome")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#set-welcome",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "welcome")
        self.assertEquals(fields[1].prop("type"), "text-multi")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content, "Welcome Message")
        self.assertEquals(fields[1].children.next.name, "required")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#set-welcome")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="text-multi",
                              name="welcome",
                              value=["New Welcome Message"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#set-welcome",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["welcome"],
                          ["New Welcome Message"])
        self.comp.config.read(self.comp.config_file)
        self.assertTrue(self.comp.config.has_option("component", "welcome_message"))
        self.assertEquals(self.comp.config.get("component", "welcome_message"),
                          "New Welcome Message")

    def test_execute_delete_welcome(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        self.comp.set_motd("test motd")
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.status = account.OFFLINE
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = account.OFFLINE
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#delete-welcome")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#delete-welcome",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0])
        self.comp.config.read(self.comp.config_file)
        self.assertFalse(self.comp.config.has_option("component",
                                                     "welcome_message"))

    def test_execute_edit_admin(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        self.comp.set_admins(["admin1@test.com", "admin2@test.com"])
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account21.status = account.OFFLINE
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = account.OFFLINE
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#edit-admin")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#edit-admin",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 2)
        self.assertEquals(fields[1].prop("var"), "adminjids")
        self.assertEquals(fields[1].prop("type"), "jid-multi")
        self.assertEquals(fields[1].children.name, "value")
        self.assertEquals(fields[1].children.content, "admin1@test.com")
        self.assertEquals(fields[1].children.next.name, "value")
        self.assertEquals(fields[1].children.next.content, "admin2@test.com")
        self.assertEquals(fields[1].children.next.next.name, "required")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin1@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#edit-admin")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="jid-multi",
                              name="adminjids",
                              values=["admin3@test.com", "admin4@test.com"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#edit-admin",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["adminjids"],
                          ["admin3@test.com", "admin4@test.com"])
        self.comp.config.read(self.comp.config_file)
        self.assertTrue(self.comp.config.has_option("component", "admins"))
        self.assertEquals(self.comp.config.get("component", "admins"),
                          "admin3@test.com,admin4@test.com")

    def test_execute_restart(self):
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        self.comp.running = True
        model.db_connect()
        user1 = User(jid="test1@test.com")
        account11 = ExampleAccount(user=user1,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account11.status = account.ONLINE
        account12 = Example2Account(user=user1,
                                    name="account12",
                                    jid="account12@jcl.test.com")
        account12.status = "away"
        user2 = User(jid="test2@test.com")
        account21 = ExampleAccount(user=user2,
                                   name="account21",
                                   jid="account21@jcl.test.com")
        account22 = ExampleAccount(user=user2,
                                   name="account11",
                                   jid="account11@jcl.test.com")
        account22.status = "xa"
        model.db_disconnect()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#restart")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#restart",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 1)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "executing")
        self.assertNotEquals(xml_command.prop("sessionid"), None)
        self.__check_actions(result[0], ["next"])
        fields = result[0].xpath_eval("c:command/data:x/data:field",
                                      {"c": "http://jabber.org/protocol/commands",
                                       "data": "jabber:x:data"})
        self.assertEquals(len(fields), 3)
        self.assertEquals(fields[1].prop("var"), "delay")
        self.assertEquals(fields[1].prop("type"), "list-multi")
        self.assertEquals(fields[2].prop("var"), "announcement")
        self.assertEquals(fields[2].prop("type"), "text-multi")

        # Second step
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS, "command")
        command_node.setProp("node",
                             "http://jabber.org/protocol/admin#restart")
        session_id = xml_command.prop("sessionid")
        command_node.setProp("sessionid", session_id)
        command_node.setProp("action", "next")
        submit_form = Form(xmlnode_or_type="submit")
        submit_form.add_field(field_type="list-multi",
                              name="delay",
                              value=[0])
        submit_form.add_field(field_type="text-multi",
                              name="announcement",
                              value=["service will be restarted in 0 second"])
        submit_form.as_xml(command_node)
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#restart",
            "execute")
        self.assertNotEquals(result, None)
        self.assertEquals(len(result), 3)
        xml_command = result[0].xpath_eval("c:command",
                                           {"c": "http://jabber.org/protocol/commands"})[0]
        self.assertEquals(xml_command.prop("status"), "completed")
        self.assertEquals(xml_command.prop("sessionid"), session_id)
        self.__check_actions(result[0])
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["announcement"],
                          ["service will be restarted in 0 second"])
        self.assertEquals(context_session["delay"],
                          ["0"])
        self.assertEquals(result[1].get_from(), "jcl.test.com")
        self.assertEquals(result[1].get_to(), "test1@test.com")
        self.assertEquals(result[1].get_body(), "service will be restarted in 0 second")
        self.assertEquals(result[2].get_from(), "jcl.test.com")
        self.assertEquals(result[2].get_to(), "test2@test.com")
        self.assertEquals(result[2].get_body(), "service will be restarted in 0 second")
        self.assertFalse(self.comp.restart)
        self.assertTrue(self.comp.running)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 2)
        threading.Event().wait(1)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertTrue(self.comp.restart)
        self.assertFalse(self.comp.running)

#     def test_execute_shutdown(self):
#         #TODO : implement command
#         info_query = Iq(stanza_type="set",
#                         from_jid="admin@test.com",
#                         to_jid="jcl.test.com")
#         result = self.command_manager.execute_add_user(info_query)
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(CommandManager_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(FieldNoType_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManager_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
