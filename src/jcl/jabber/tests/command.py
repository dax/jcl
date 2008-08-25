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
import sys
import logging

from pyxmpp.jid import JID
from pyxmpp.jabber.dataforms import Form
from pyxmpp.iq import Iq
from pyxmpp.jabber.disco import DiscoItems
from pyxmpp.jabber.dataforms import Field

import jcl.tests
from jcl.lang import Lang
from jcl.jabber.component import JCLComponent
import jcl.jabber.command as command
from jcl.jabber.command import FieldNoType, CommandManager, JCLCommandManager, \
    CommandError
import jcl.model.account as account
from jcl.model.account import Account, PresenceAccount, LegacyJID, User
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

class MockComponent(JCLComponent):
    jid = JID("jcl.test.com")
    lang = Lang()

    def __init__(self):
        pass

    def get_admins(self):
        return ["admin@test.com"]

class MockCommandManager(CommandManager):
    """ """
    def __init__ (self):
        """ """
        CommandManager.__init__(self)
        self.commands["command1"] = (False,
                                     command.root_node_re)
        self.component = MockComponent()
        self.command1_step_1_called = False

    def execute_command1_1(self, info_query, session_context,
                           command_node, lang_class):
        """ """
        self.command1_step_1_called = True
        return (None, [])

def prepare_submit(node, session_id, from_jid, to_jid="jcl.test.com",
                   fields=[], action="next"):
    """
    Prepare IQ form to be submitted
    """
    info_query = Iq(stanza_type="set",
                    from_jid=from_jid,
                    to_jid=to_jid)
    command_node = info_query.set_new_content(command.COMMAND_NS,
                                              "command")
    command_node.setProp("node", node)
    command_node.setProp("sessionid", session_id)
    command_node.setProp("action", action)
    submit_form = Form(xmlnode_or_type="submit")
    submit_form.fields.extend(fields)
    submit_form.as_xml(command_node)
    return info_query

class CommandManager_TestCase(unittest.TestCase):
    def setUp(self):
        self.command_manager = CommandManager()
        self.command_manager.commands = {}

    def test_get_short_command_name_form_long_name(self):
        command_name = self.command_manager.get_short_command_name("http://jabber.org/protocol/admin#test-command")
        self.assertEquals(command_name, "test_command")

    def test_get_short_command_name(self):
        command_name = self.command_manager.get_short_command_name("test-command")
        self.assertEquals(command_name, "test_command")

    def test_list_root_commands(self):
        self.command_manager.commands["command1"] = (True,
                                                     command.root_node_re)
        self.command_manager.commands["command2"] = (False,
                                                     command.root_node_re)
        self.command_manager.commands["command11"] = (\
            True, command.account_type_node_re)
        self.command_manager.commands["command12"] = (\
            False, command.account_type_node_re)
        self.command_manager.commands["command21"] = (\
            True, command.account_node_re)
        self.command_manager.commands["command22"] = (\
            False, command.account_node_re)
        self.command_manager.component = MockComponent()
        disco_items = self.command_manager.list_commands(\
            jid=JID("user@test.com"),
            to_jid=JID("jcl.test.com"),
            disco_items=DiscoItems(),
            lang_class=Lang.en)
        self.assertEquals(disco_items.get_node(), None)
        items = disco_items.get_items()
        self.assertEquals(len(items), 1)
        self.assertEquals(items[0].get_node(), "command2")
        self.assertEquals(items[0].get_name(), "command2")
        self.assertEquals(items[0].get_jid(), "jcl.test.com")

    def test_list_accounttype_commands(self):
        self.command_manager.commands["command1"] = (True,
                                                     command.root_node_re)
        self.command_manager.commands["command2"] = (False,
                                                     command.root_node_re)
        self.command_manager.commands["command11"] = (\
            True, command.account_type_node_re)
        self.command_manager.commands["command12"] = (\
            False, command.account_type_node_re)
        self.command_manager.commands["command21"] = (\
            True, command.account_node_re)
        self.command_manager.commands["command22"] = (\
            False, command.account_node_re)
        self.command_manager.component = MockComponent()
        disco_items = self.command_manager.list_commands(\
            jid=JID("user@test.com"),
            to_jid=JID("jcl.test.com/Example"),
            disco_items=DiscoItems("Example"),
            lang_class=Lang.en)
        self.assertEquals(disco_items.get_node(), "Example")
        items = disco_items.get_items()
        self.assertEquals(len(items), 1)
        self.assertEquals(items[0].get_node(), "command12")
        self.assertEquals(items[0].get_name(), "command12")
        self.assertEquals(items[0].get_jid(), "jcl.test.com/Example")

    def test_list_account_commands(self):
        self.command_manager.commands["command1"] = (True,
                                                     command.root_node_re)
        self.command_manager.commands["command2"] = (False,
                                                     command.root_node_re)
        self.command_manager.commands["command11"] = (\
            True, command.account_type_node_re)
        self.command_manager.commands["command12"] = (\
            False, command.account_type_node_re)
        self.command_manager.commands["command21"] = (\
            True, command.account_node_re)
        self.command_manager.commands["command22"] = (\
            False, command.account_node_re)
        self.command_manager.component = MockComponent()
        disco_items = self.command_manager.list_commands(\
            jid=JID("user@test.com"),
            to_jid=JID("account@jcl.test.com/Example"),
            disco_items=DiscoItems("Example/account1"),
            lang_class=Lang.en)
        self.assertEquals(disco_items.get_node(), "Example/account1")
        items = disco_items.get_items()
        self.assertEquals(len(items), 1)
        self.assertEquals(items[0].get_node(), "command22")
        self.assertEquals(items[0].get_name(), "command22")
        self.assertEquals(items[0].get_jid(), "account@jcl.test.com/Example")

    def test_list_commands_as_admin(self):
        self.command_manager.commands["command1"] = (True,
                                                     command.root_node_re)
        self.command_manager.commands["command2"] = (False,
                                                     command.root_node_re)
        self.command_manager.component = MockComponent()
        disco_items = self.command_manager.list_commands(\
            jid=JID("admin@test.com"),
            to_jid=JID("jcl.test.com"),
            disco_items=DiscoItems(),
            lang_class=Lang.en)
        self.assertEquals(disco_items.get_node(), None)
        items = disco_items.get_items()
        self.assertEquals(len(items), 2)
        self.assertEquals(items[0].get_node(), "command1")
        self.assertEquals(items[0].get_name(), "command1")
        self.assertEquals(items[0].get_jid(), "jcl.test.com")
        self.assertEquals(items[1].get_node(), "command2")
        self.assertEquals(items[1].get_name(), "command2")
        self.assertEquals(items[1].get_jid(), "jcl.test.com")

    def test_list_commands_as_admin_fulljid(self):
        self.command_manager.commands["command1"] = (True,
                                                     command.root_node_re)
        self.command_manager.commands["command2"] = (False,
                                                     command.root_node_re)
        self.command_manager.component = MockComponent()
        disco_items = self.command_manager.list_commands(\
            jid=JID("admin@test.com/full"),
            to_jid=JID("jcl.test.com"),
            disco_items=DiscoItems(),
            lang_class=Lang.en)
        self.assertEquals(disco_items.get_node(), None)
        items = disco_items.get_items()
        self.assertEquals(len(items), 2)
        self.assertEquals(items[0].get_node(), "command1")
        self.assertEquals(items[0].get_name(), "command1")
        self.assertEquals(items[0].get_jid(), "jcl.test.com")
        self.assertEquals(items[1].get_node(), "command2")
        self.assertEquals(items[1].get_name(), "command2")
        self.assertEquals(items[1].get_jid(), "jcl.test.com")

    def test_apply_admin_command_action_as_admin(self):
        self.command_manager.commands["command1"] = (True,
                                                     command.root_node_re)
        self.command_manager.apply_execute_command = \
            lambda iq, command_name: []
        self.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        result = self.command_manager.apply_command_action(info_query,
                                                           "command1",
                                                           "execute")
        self.assertEquals(result, [])

    def test_apply_admin_command_action_as_admin_fulljid(self):
        self.command_manager.commands["command1"] = (True,
                                                     command.root_node_re)
        self.command_manager.apply_execute_command = \
            lambda iq, command_name: []
        self.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com/full",
                        to_jid="jcl.test.com")
        result = self.command_manager.apply_command_action(info_query,
                                                           "command1",
                                                           "execute")
        self.assertEquals(result, [])

    def test_apply_admin_command_action_as_user(self):
        self.command_manager.commands["command1"] = (True,
                                                     command.root_node_re)
        self.command_manager.apply_execute_command = \
            lambda iq, command_name: []
        self.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        result = self.command_manager.apply_command_action(info_query,
                                                           "command1",
                                                           "execute")
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_type(), "error")
        self.assertEquals(result[0].xmlnode.children.name, "error")
        self.assertEquals(result[0].xmlnode.children.prop("type"),
                          "auth")
        self.assertEquals(result[0].xmlnode.children.children.name,
                          "forbidden")

    def test_apply_non_admin_command_action_as_admin(self):
        self.command_manager.commands["command1"] = (False,
                                                     command.root_node_re)
        self.command_manager.apply_execute_command = \
            lambda iq, command_name: []
        self.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="admin@test.com",
                        to_jid="jcl.test.com")
        result = self.command_manager.apply_command_action(info_query,
                                                           "command1",
                                                           "execute")
        self.assertEquals(result, [])

    def test_apply_non_admin_command_action_as_user(self):
        self.command_manager.commands["command1"] = (False,
                                                     command.root_node_re)
        self.command_manager.apply_execute_command = \
            lambda iq, command_name: []
        self.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        result = self.command_manager.apply_command_action(info_query,
                                                           "command1",
                                                           "execute")
        self.assertEquals(result, [])

    def test_apply_command_action_to_wrong_jid(self):
        self.command_manager.commands["command1"] = (False,
                                                     command.account_node_re)
        self.command_manager.apply_execute_command = \
            lambda iq, command_name: []
        self.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        result = self.command_manager.apply_command_action(info_query,
                                                           "command1",
                                                           "execute")
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_type(), "error")
        self.assertEquals(result[0].xmlnode.children.name, "error")
        self.assertEquals(result[0].xmlnode.children.prop("type"),
                          "auth")
        self.assertEquals(result[0].xmlnode.children.children.name,
                          "forbidden")

    def test_apply_command_non_existing_action(self):
        self.command_manager.commands["command1"] = (False,
                                                     command.root_node_re)
        self.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        result = self.command_manager.apply_command_action(info_query,
                                                           "command1",
                                                           "noexecute")
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_type(), "error")
        self.assertEquals(result[0].xmlnode.children.name, "error")
        self.assertEquals(result[0].xmlnode.children.prop("type"),
                          "cancel")
        self.assertEquals(result[0].xmlnode.children.children.name,
                          "feature-not-implemented")

    def test_apply_command_unknown_command(self):
        self.command_manager.component = MockComponent()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        result = self.command_manager.apply_command_action(info_query,
                                                           "command1",
                                                           "noexecute")
        self.assertEquals(len(result), 1)
        self.assertEquals(result[0].get_type(), "error")
        self.assertEquals(result[0].xmlnode.children.name, "error")
        self.assertEquals(result[0].xmlnode.children.prop("type"),
                          "cancel")
        self.assertEquals(result[0].xmlnode.children.children.name,
                          "feature-not-implemented")

    def test_multi_step_command_unknown_step(self):
        self.command_manager = MockCommandManager()
        self.command_manager.sessions["session_id"] = (1, {})
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS,
                                                  "command")
        command_node.setProp("sessionid", "session_id")
        command_node.setProp("node", "command1")
        result = self.command_manager.execute_multi_step_command(\
            info_query, "command1", lambda session_id: (2, {}))
        self.assertEquals(result[0].get_type(), "error")
        child = result[0].xmlnode.children
        self.assertEquals(child.name, "command")
        self.assertEquals(child.prop("node"), "command1")
        child = result[0].xmlnode.children.next
        self.assertEquals(child.name, "error")
        self.assertEquals(child.prop("type"), "cancel")
        self.assertEquals(child.children.name,
                          "feature-not-implemented")

    def test_multi_step_command_first_step(self):
        self.command_manager = MockCommandManager()
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS,
                                                  "command")
        command_node.setProp("node", "command1")
        self.command_manager.execute_multi_step_command(\
            info_query, "command1", None)
        self.assertTrue(self.command_manager.command1_step_1_called)

    def test_multi_step_command_multi_step_method(self):
        """
        Test if the multi steps method is called if no specific method
        is implemented
        """
        self.command_manager = MockCommandManager()
        self.command_manager.sessions["session_id"] = (1, {})
        self.multi_step_command1_called = False
        def execute_command1(info_query, session_context,
                             command_node, lang_class):
            """ """
            self.multi_step_command1_called = True
            return (None, [])

        self.command_manager.__dict__["execute_command1"] = execute_command1
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS,
                                                  "command")
        command_node.setProp("sessionid", "session_id")
        command_node.setProp("node", "command1")
        self.command_manager.execute_multi_step_command(\
            info_query, "command1", lambda session_id: (2, {}))
        self.assertTrue(self.multi_step_command1_called)

    def test_multi_step_command_error_in_command(self):
        """
        Test if the multi steps method catch the CommandError exception
        and translate it into an IQ error
        """
        self.command_manager = MockCommandManager()
        def execute_command1(info_query, session_context,
                             command_node, lang_class):
            raise CommandError("feature-not-implemented")

        self.command_manager.__dict__["execute_command1_1"] = execute_command1
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS,
                                                  "command")
        command_node.setProp("node", "command1")
        result = self.command_manager.execute_multi_step_command(\
            info_query, "command1", None)
        result_iq = result[0].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='" + unicode(self.command_manager.component.jid)
                + "' to='user@test.com' type='error' "
                + "xmlns='http://pyxmpp.jabberstudio.org/xmlns/common'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "node='command1' />"
                + "<error type='cancel'><feature-not-implemented "
                + "xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
                + "</iq>",
                result_iq, True))

    def test_multi_step_command_unknown_error_in_command(self):
        """
        Test if the multi steps method catch the CommandError exception
        and translate it into an IQ error
        """
        self.command_manager = MockCommandManager()
        def execute_command1(info_query, session_context,
                             command_node, lang_class):
            raise Exception("error")

        self.command_manager.__dict__["execute_command1_1"] = execute_command1
        info_query = Iq(stanza_type="set",
                        from_jid="user@test.com",
                        to_jid="jcl.test.com")
        command_node = info_query.set_new_content(command.COMMAND_NS,
                                                  "command")
        command_node.setProp("node", "command1")
        result = self.command_manager.execute_multi_step_command(\
            info_query, "command1", None)
        result_iq = result[0].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='" + unicode(self.command_manager.component.jid)
                + "' to='user@test.com' type='error' "
                + "xmlns='http://pyxmpp.jabberstudio.org/xmlns/common'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "node='command1' />"
                + "<error type='cancel'><service-unavailable "
                + "xmlns='urn:ietf:params:xml:ns:xmpp-stanzas'/></error>"
                + "</iq>",
                result_iq, True))

    def test_parse_form(self):
        """
        Check if parse_form method correctly set the session variables
        from given Form.
        """
        session_id = "session_id"
        self.command_manager.sessions[session_id] = (1, {})
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="test1@test.com",
            fields=[Field(field_type="list-multi",
                          name="test",
                          values=["1", "2"])])
        self.command_manager.parse_form(info_query, session_id)
        self.assertEquals(\
            self.command_manager.sessions[session_id][1]["test"],
            ["1", "2"])

    def test_parse_form_multiple_calls(self):
        """
        Check if parse_form method correctly set the session variables
        from given Form. It should append data to an existing session
        variable.
        """
        session_id = "session_id"
        self.command_manager.sessions[session_id] = (1, {"test": ["1", "2"]})
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="test1@test.com",
            fields=[Field(field_type="list-multi",
                          name="test",
                          values=["3", "4"])])
        self.command_manager.parse_form(info_query, session_id)
        self.assertEquals(\
            self.command_manager.sessions[session_id][1]["test"],
            ["1", "2", "3", "4"])

class JCLCommandManagerTestCase(JCLTestCase):
    def setUp(self, tables=[]):
        tables += [Account, PresenceAccount, ExampleAccount,
                   Example2Account, LegacyJID,
                   User]
        JCLTestCase.setUp(self, tables=tables)
        self.config_file = tempfile.mktemp(".conf", "jcltest", jcl.tests.DB_DIR)
        self.config = ConfigParser()
        self.config.read(self.config_file)
        self.comp = JCLComponent("jcl.test.com",
                                 "password",
                                 "localhost",
                                 "5347",
                                 self.config,
                                 self.config_file)
        self.comp.time_unit = 0
        self.comp.set_admins(["admin@test.com"])
        self.command_manager = JCLCommandManager(self.comp,
                                                 self.comp.account_manager)
        self.comp.account_manager.account_classes = (ExampleAccount,
                                                     Example2Account)
        self.user1 = User(jid="test1@test.com")
        self.account11 = ExampleAccount(user=self.user1,
                                        name="account11",
                                        jid="account11@jcl.test.com")
        self.account12 = Example2Account(user=self.user1,
                                         name="account12",
                                         jid="account12@jcl.test.com")
        self.user2 = User(jid="test2@test.com")
        self.account21 = ExampleAccount(user=self.user2,
                                        name="account21",
                                        jid="account21@jcl.test.com")
        self.account22 = ExampleAccount(user=self.user2,
                                        name="account11",
                                        jid="account11@jcl.test.com")
        self.user3 = User(jid="test3@test.com")
        self.account31 = ExampleAccount(user=self.user3,
                                        name="account31",
                                        jid="account31@jcl.test.com")
        self.account32 = Example2Account(user=self.user3,
                                         name="account32",
                                         jid="account32@jcl.test.com")
        self.info_query = Iq(stanza_type="set",
                             from_jid="admin@test.com",
                             to_jid=self.comp.jid)
        self.command_node = self.info_query.set_new_content(command.COMMAND_NS,
                                                            "command")

    def tearDown(self):
        JCLTestCase.tearDown(self)
        if os.path.exists(self.config_file):
            os.unlink(self.config_file)

    def _check_actions(self, info_query, expected_actions=None, action_index=0):
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

class JCLCommandManager_TestCase(JCLCommandManagerTestCase):
    def test_init(self):
        command_manager = JCLCommandManager(self.comp,
                                            self.comp.account_manager)
        self.assertEquals(len(command_manager.commands), 23)

class JCLCommandManagerAddFormSelectUserJID_TestCase(JCLCommandManagerTestCase):
    """
    Test add_form_select_user_jid* method of JCLCommandManager class
    """

    def test_add_form_select_users_jids(self):
        """
        test add_form_select_user_jid method which should add a field to
        select multiple JIDs
        """
        self.command_manager.add_form_select_users_jids(self.command_node,
                                                        "title", "description",
                                                        Lang.en.field_users_jids)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<command xmlns='http://jabber.org/protocol/commands'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>title</title>"
                + "<instructions>description</instructions>"
                + "<field var='user_jids' type='jid-multi' label='"
                + Lang.en.field_users_jids + "' />"
                + "</x></command>",
                self.command_node, True))

    def test_add_form_select_user_jid(self):
        """
        test add_form_select_users_jid method which should add a field to
        select a JID
        """
        self.command_manager.add_form_select_user_jid(self.command_node,
                                                      "title", "description",
                                                      Lang.en.field_user_jid)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<command xmlns='http://jabber.org/protocol/commands'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>title</title>"
                + "<instructions>description</instructions>"
                + "<field var='user_jid' type='jid-single' label='"
                + Lang.en.field_user_jid + "' />"
                + "</x></command>",
                self.command_node, True))

class JCLCommandManagerAddFormSelectAccount_TestCase(JCLCommandManagerTestCase):
    """
    Test add_form_select_account* method of JCLCommandManager class
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.session_context = {}
        self.session_context["user_jids"] = ["test1@test.com", "test2@test.com"]

    def test_add_form_select_accounts(self):
        """
        test add_form_select_accounts method which should add a field to
        select accounts for given JIDs
        """
        self.command_manager.add_form_select_accounts(self.session_context,
                                                      self.command_node,
                                                      Lang.en,
                                                      "title", "description")
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<command xmlns='http://jabber.org/protocol/commands'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>title</title>"
                + "<instructions>description</instructions>"
                + "<field var='account_names' type='list-multi' label='"
                + Lang.en.field_accounts + "'>"
                + "<option label='account11 (Example) (test1@test.com)'>"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label='account21 (Example) (test2@test.com)'>"
                + "<value>account21/test2@test.com</value></option>"
                + "<option label='account11 (Example) (test2@test.com)'>"
                + "<value>account11/test2@test.com</value></option>"
                + "<option label='account12 (Example2) (test1@test.com)'>"
                + "<value>account12/test1@test.com</value></option>"
                + "</field></x></command>",
                self.command_node, True))

    def test_add_form_select_accounts_without_user_jid(self):
        """
        test add_form_select_accounts method which should add a field to
        select accounts for given JIDs but don't show JID in labels
        """
        self.command_manager.add_form_select_accounts(self.session_context,
                                                      self.command_node,
                                                      Lang.en,
                                                      "title", "description",
                                                      show_user_jid=False)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<command xmlns='http://jabber.org/protocol/commands'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>title</title>"
                + "<instructions>description</instructions>"
                + "<field var='account_names' type='list-multi' label='"
                + Lang.en.field_accounts + "'>"
                + "<option label='account11 (Example)'>"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label='account21 (Example)'>"
                + "<value>account21/test2@test.com</value></option>"
                + "<option label='account11 (Example)'>"
                + "<value>account11/test2@test.com</value></option>"
                + "<option label='account12 (Example2)'>"
                + "<value>account12/test1@test.com</value></option>"
                + "</field></x></command>",
                self.command_node, True))

    def test_add_form_select_accounts_filtered(self):
        """
        test add_form_select_accounts method which should add a field to
        select accounts for given JIDs with a filter
        """
        self.account21.enabled = False
        self.command_manager.add_form_select_accounts(self.session_context,
                                                      self.command_node,
                                                      Lang.en,
                                                      "title", "description",
                                                      Account.q.enabled==True)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<command xmlns='http://jabber.org/protocol/commands'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>title</title>"
                + "<instructions>description</instructions>"
                + "<field var='account_names' type='list-multi' label='"
                + Lang.en.field_accounts + "'>"
                + "<option label='account11 (Example) (test1@test.com)'>"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label='account11 (Example) (test2@test.com)'>"
                + "<value>account11/test2@test.com</value></option>"
                + "<option label='account12 (Example2) (test1@test.com)'>"
                + "<value>account12/test1@test.com</value></option>"
                + "</field></x></command>",
                self.command_node, True))

    def test_add_form_select_account(self):
        """
        test add_form_select_account method which should add a field to
        select one accounts for a given JID
        """
        self.session_context["user_jid"] = ["test1@test.com"]
        self.command_manager.add_form_select_account(self.session_context,
                                                     self.command_node,
                                                     Lang.en,
                                                     "title", "description")
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<command xmlns='http://jabber.org/protocol/commands'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>title</title>"
                + "<instructions>description</instructions>"
                + "<field var='account_name' type='list-single' label='"
                + Lang.en.field_account + "'>"
                + "<option label='account11 (Example) (test1@test.com)'>"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label='account12 (Example2) (test1@test.com)'>"
                + "<value>account12/test1@test.com</value></option>"
                + "</field></x></command>",
                self.command_node, True))

class JCLCommandManagerAddUserCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'add-user' ad-hoc command method.
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#add-user")

    def check_step_1(self, result, to_jid, is_admin=False):
        """
        Check result of step 1 of 'add-user' ad-hoc command
        """
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        xml_ref = u"<iq from='jcl.test.com' to='" + to_jid + "' type='result'>" \
            + "<command xmlns='http://jabber.org/protocol/commands'" \
            + "status='executing'>" \
            + "<actions execute='next'><next/></actions>" \
            + "<x xmlns='jabber:x:data' type='form'>" \
            + "<title>" + Lang.en.command_add_user + "</title>" \
            + "<instructions>" + Lang.en.command_add_user_1_description \
            + "</instructions>" \
            + "<field var='account_type' type='list-single' label='" \
            + Lang.en.field_account_type + "'>" \
            + "<option label='Example'>" \
            + "<value>Example</value></option>" \
            + "<option label='Example2'>" \
            + "<value>Example2</value></option>"
        if is_admin:
            xml_ref += u"</field><field var='user_jid' type='jid-single' label='" \
                + Lang.en.field_user_jid + "'>"
        xml_ref += "</field></x></command></iq>"
        self.assertTrue(jcl.tests.is_xml_equal(\
                xml_ref,
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)
        return session_id

    def check_step_2(self, result, session_id, to_jid, new_jid):
        """
        Check result of step 2 of 'add-user' ad-hoc command.
        """
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='" + to_jid + "' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing' sessionid='" + session_id + "'>"
                + "<actions execute='complete'><prev/><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.register_title + "</title>"
                + "<instructions>" + Lang.en.register_instructions
                + "</instructions>"
                + "<field var='name' type='text-single' label='"
                + Lang.en.account_name + "'><required/>"
                + "</field><field var='login' type='text-single' label='"
                + "login'><value> </value><required/>"
                + "</field><field var='password' type='text-private' label='"
                + Lang.en.field_password + "'><value> </value>"
                + "</field><field var='store_password' type='boolean' label='"
                + "store_password'><value>1</value>"
                + "</field><field var='test_enum' type='list-single' label='"
                + "test_enum'><value>choice2</value>"
                + "<option label='choice1'>"
                + "<value>choice1</value></option>"
                + "<option label='choice2'>"
                + "<value>choice2</value></option>"
                + "<option label='choice3'>"
                + "<value>choice3</value></option>"
                + "</field><field var='test_int' type='text-single' label='"
                + "test_int'><value>44</value>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["account_type"], ["Example"])
        self.assertEquals(context_session["user_jid"], [new_jid])

    def check_step_3(self, result, session_id, to_jid, new_jid):
        """
        """
        _account = account.get_account(new_jid,
                                       "account1")
        self.assertNotEquals(_account, None)
        self.assertEquals(_account.user.jid, new_jid)
        self.assertEquals(_account.name, "account1")
        self.assertEquals(_account.jid, "account1@" + unicode(self.comp.jid))
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='" + to_jid + "' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        result_iq = result[1].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<presence from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='" + new_jid + "' "
                + "type='subscribe' />",
                result_iq, True, test_sibling=False))
        result_iq = result[2].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='" + new_jid + "'>"
                + "<subject>" + _account.get_new_message_subject(Lang.en)
                + "</subject>"
                + "<body>" + _account.get_new_message_body(Lang.en)
                + "</body></message>",
                result_iq, True, test_sibling=False))
        result_iq = result[3].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<presence from='account1@" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='" + new_jid + "' type='subscribe' />",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["name"], ["account1"])
        self.assertEquals(context_session["login"], ["login1"])
        self.assertEquals(context_session["password"], ["pass1"])
        self.assertEquals(context_session["store_password"], ["1"])
        self.assertEquals(context_session["test_enum"], ["choice2"])
        self.assertEquals(context_session["test_int"], ["42"])

    def test_execute_add_user(self):
        """
        test 'add-user' ad-hoc command with an admin user.
        """
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#add-user",
            "execute")
        session_id = self.check_step_1(result, "admin@test.com", is_admin=True)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-single",
                          name="account_type",
                          value="Example"),
                    Field(field_type="jid-single",
                          name="user_jid",
                          value="user2@test.com")])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#add-user",
            "next")
        self.check_step_2(result, session_id,
                          "admin@test.com", "user2@test.com")

        # Third step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="text-single",
                          name="name",
                          value="account1"),
                    Field(field_type="text-single",
                          name="login",
                          value="login1"),
                    Field(field_type="text-private",
                          name="password",
                          value="pass1"),
                    Field(field_type="boolean",
                          name="store_password",
                          value="1"),
                    Field(field_type="list-single",
                          name="test_enum",
                          value="choice2"),
                    Field(field_type="text-single",
                          name="test_int",
                          value="42")],
            action="complete")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#add-user",
            "execute")
        self.check_step_3(result, session_id,
                          "admin@test.com", "user2@test.com")

    def test_execute_add_user_not_admin(self):
        """
        test 'add-user' ad-hoc command without an admin user.
        """
        self.info_query.set_from("test4@test.com")
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#add-user",
            "execute")
        session_id = self.check_step_1(result, "test4@test.com")

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="test4@test.com",
            fields=[Field(field_type="list-single",
                          name="account_type",
                          value="Example")])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#add-user",
            "next")
        context_session = self.check_step_2(result, session_id,
                                            "test4@test.com", "test4@test.com")

        # Third step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="test4@test.com",
            fields=[Field(field_type="text-single",
                          name="name",
                          value="account1"),
                    Field(field_type="text-single",
                          name="login",
                          value="login1"),
                    Field(field_type="text-private",
                          name="password",
                          value="pass1"),
                    Field(field_type="boolean",
                          name="store_password",
                          value="1"),
                    Field(field_type="list-single",
                          name="test_enum",
                          value="choice2"),
                    Field(field_type="text-single",
                          name="test_int",
                          value="42")],
            action="complete")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#add-user",
            "execute")
        self.check_step_3(result, session_id,
                          "test4@test.com", "test4@test.com")

    def test_execute_add_user_prev(self):
        """
        test 'add-user' ad-hoc command with an admin user. Test 'prev' action.
        """
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#add-user",
            "execute")
        session_id = self.check_step_1(result, "admin@test.com", is_admin=True)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-single",
                          name="account_type",
                          value="Example"),
                    Field(field_type="jid-single",
                          name="user_jid",
                          value="user2@test.com")])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#add-user",
            "next")
        self.check_step_2(result, session_id,
                          "admin@test.com", "user2@test.com")

        # First step again
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="text-single",
                          name="name",
                          value="account1"),
                    Field(field_type="text-single",
                          name="login",
                          value="login1"),
                    Field(field_type="text-private",
                          name="password",
                          value="pass1"),
                    Field(field_type="boolean",
                          name="store_password",
                          value="1"),
                    Field(field_type="list-single",
                          name="test_enum",
                          value="choice2"),
                    Field(field_type="text-single",
                          name="test_int",
                          value="42")],
            action="prev")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#add-user",
            "prev")
        other_session_id = self.check_step_1(result, "admin@test.com",
                                             is_admin=True)
        self.assertEquals(other_session_id, session_id)

    def test_execute_add_user_cancel(self):
        """
        Test cancel 'add-user' ad-hoc command .
        """
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#add-user",
            "execute")
        session_id = self.check_step_1(result, "admin@test.com", is_admin=True)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#add-user",
            session_id=session_id,
            from_jid="admin@test.com",
            action="cancel")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#add-user",
            "cancel")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='canceled' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True))

class JCLCommandManagerDeleteUserCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'delete-user' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#delete-user")

    def test_execute_delete_user(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#delete-user",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='next'><next/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_delete_user + "</title>"
                + "<instructions>" + Lang.en.command_delete_user_1_description
                + "</instructions>"
                + "<field var='user_jids' type='jid-multi' label='"
                + Lang.en.field_users_jids + "'>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#delete-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="jid-multi",
                          name="user_jids",
                          values=["test1@test.com", "test2@test.com"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#delete-user",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><prev/><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_delete_user + "</title>"
                + "<instructions>" + Lang.en.command_delete_user_2_description
                + "</instructions>"
                + "<field var='account_names' type='list-multi' label='"
                + Lang.en.field_accounts + "'>"
                + "<option label=\"account11 (Example) (test1@test.com)\">"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label=\"account21 (Example) (test2@test.com)\">"
                + "<value>account21/test2@test.com</value></option>"
                + "<option label=\"account11 (Example) (test2@test.com)\">"
                + "<value>account11/test2@test.com</value></option>"
                + "<option label=\"account12 (Example2) (test1@test.com)\">"
                + "<value>account12/test1@test.com</value></option>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jids"],
                          ["test1@test.com", "test2@test.com"])

        # Third step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#delete-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-multi",
                          name="account_names",
                          values=["account11/test1@test.com",
                                  "account11/test2@test.com"])],
            action="complete")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#delete-user",
            "execute")
        self.assertEquals(context_session["account_names"],
                          ["account11/test1@test.com",
                           "account11/test2@test.com"])
        test1_accounts = account.get_accounts("test1@test.com")
        self.assertEquals(test1_accounts.count(), 1)
        self.assertEquals(test1_accounts[0].name, "account12")
        test2_accounts = account.get_accounts("test2@test.com")
        self.assertEquals(test2_accounts.count(), 1)
        self.assertEquals(test2_accounts[0].name, "account21")
        test3_accounts = account.get_accounts("test3@test.com")
        self.assertEquals(test3_accounts.count(), 2)

        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        result_iq = result[1].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<presence from='account11@" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test1@test.com' "
                + "type='unsubscribe' />",
                result_iq, True, test_sibling=False))
        result_iq = result[2].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<presence from='account11@" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test1@test.com' "
                + "type='unsubscribed' />",
                result_iq, True, test_sibling=False))
        result_iq = result[3].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<presence from='account11@" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test2@test.com' "
                + "type='unsubscribe' />",
                result_iq, True, test_sibling=False))
        result_iq = result[4].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<presence from='account11@" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test2@test.com' "
                + "type='unsubscribed' />",
                result_iq, True, test_sibling=False))

class JCLCommandManagerDisableUserCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'disable-user' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.account11.enabled = True
        self.account12.enabled = False
        self.account21.enabled = False
        self.account22.enabled = True
        self.account31.enabled = False
        self.account32.enabled = False
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#disable-user")

    def test_execute_disable_user(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#disable-user",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='next'><next/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_disable_user + "</title>"
                + "<instructions>" + Lang.en.command_disable_user_1_description
                + "</instructions>"
                + "<field var='user_jids' type='jid-multi' label='"
                + Lang.en.field_users_jids + "'>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#disable-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="jid-multi",
                          name="user_jids",
                          values=["test1@test.com", "test2@test.com"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#disable-user",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><prev/><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_disable_user + "</title>"
                + "<instructions>" + Lang.en.command_disable_user_2_description
                + "</instructions>"
                + "<field var='account_names' type='list-multi' label='"
                + Lang.en.field_accounts + "'>"
                + "<option label=\"account11 (Example) (test1@test.com)\">"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label=\"account11 (Example) (test2@test.com)\">"
                + "<value>account11/test2@test.com</value></option>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jids"],
                          ["test1@test.com", "test2@test.com"])

        # Third step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#disable-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-multi",
                          name="account_names",
                          values=["account11/test1@test.com",
                                  "account11/test2@test.com"])],
            action="complete")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#disable-user",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        self.assertEquals(context_session["account_names"],
                          ["account11/test1@test.com",
                           "account11/test2@test.com"])
        for _account in account.get_all_accounts():
            self.assertFalse(_account.enabled)

class JCLCommandManagerReenableUserCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'reenable-user' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.account11.enabled = False
        self.account12.enabled = True
        self.account21.enabled = True
        self.account22.enabled = False
        self.account31.enabled = True
        self.account32.enabled = True
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#reenable-user")

    def test_execute_reenable_user(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#reenable-user",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='next'><next/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_reenable_user + "</title>"
                + "<instructions>" + Lang.en.command_reenable_user_1_description
                + "</instructions>"
                + "<field var='user_jids' type='jid-multi' label='"
                + Lang.en.field_users_jids + "'>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#reenable-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="jid-multi",
                          name="user_jids",
                          values=["test1@test.com", "test2@test.com"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#reenable-user",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><prev/><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_reenable_user + "</title>"
                + "<instructions>" + Lang.en.command_reenable_user_2_description
                + "</instructions>"
                + "<field var='account_names' type='list-multi' label='"
                + Lang.en.field_accounts + "'>"
                + "<option label=\"account11 (Example) (test1@test.com)\">"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label=\"account11 (Example) (test2@test.com)\">"
                + "<value>account11/test2@test.com</value></option>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jids"],
                          ["test1@test.com", "test2@test.com"])

        # Third step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#reenable-user",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-multi",
                          name="account_names",
                          values=["account11/test1@test.com",
                                  "account11/test2@test.com"])],
            action="complete")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#reenable-user",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        self.assertEquals(context_session["account_names"],
                          ["account11/test1@test.com",
                           "account11/test2@test.com"])
        for _account in account.get_all_accounts():
            self.assertTrue(_account.enabled)

class JCLCommandManagerEndUserSessionCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'end-user-session' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.account11.status = account.ONLINE
        self.account22.status = account.ONLINE
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#end-user-session")

    def test_execute_end_user_session(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#end-user-session",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='next'><next/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_end_user_session + "</title>"
                + "<instructions>" + Lang.en.command_end_user_session_1_description
                + "</instructions>"
                + "<field var='user_jids' type='jid-multi' label='"
                + Lang.en.field_users_jids + "'>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#end-user-session",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="jid-multi",
                          name="user_jids",
                          values=["test1@test.com", "test2@test.com"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#end-user-session",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><prev/><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_end_user_session + "</title>"
                + "<instructions>" + Lang.en.command_end_user_session_2_description
                + "</instructions>"
                + "<field var='account_names' type='list-multi' label='"
                + Lang.en.field_accounts + "'>"
                + "<option label=\"account11 (Example) (test1@test.com)\">"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label=\"account11 (Example) (test2@test.com)\">"
                + "<value>account11/test2@test.com</value></option>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jids"],
                          ["test1@test.com", "test2@test.com"])

        # Third step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#end-user-session",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-multi",
                          name="account_names",
                          values=["account11/test1@test.com",
                                  "account11/test2@test.com"])],
            action="complete")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#end-user-session",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        self.assertEquals(context_session["account_names"],
                          ["account11/test1@test.com",
                           "account11/test2@test.com"])
        result_iq = result[1].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<presence from='account11@" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test1@test.com' "
                + "type='unavailable' />",
                result_iq, True, test_sibling=False))
        result_iq = result[2].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<presence from='account11@" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test2@test.com' "
                + "type='unavailable' />",
                result_iq, True, test_sibling=False))

# disabled command
#     def test_execute_get_user_password(self):
#         self.comp.account_manager.account_classes = (ExampleAccount,
#                                                      Example2Account)
#         model.db_connect()
#         user1 = User(jid="test1@test.com")
#         user2 = User(jid="test2@test.com")
#         account11 = ExampleAccount(user=user1,
#                                    name="account11",
#                                    jid="account11@" + unicode(self.comp.jid))
#         account11.password = "pass1"
#         account12 = Example2Account(user=user1,
#                                     name="account12",
#                                     jid="account12@" + unicode(self.comp.jid))
#         account21 = ExampleAccount(user=user2,
#                                    name="account21",
#                                    jid="account21@" + unicode(self.comp.jid))
#         account22 = ExampleAccount(user=user2,
#                                    name="account11",
#                                    jid="account11@" + unicode(self.comp.jid))
#         model.db_disconnect()
#         info_query = Iq(stanza_type="set",
#                         from_jid="admin@test.com",
#                         to_jid=self.comp.jid)
#         command_node = info_query.set_new_content(command.COMMAND_NS, "command")
#         command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-password")
#         result = self.command_manager.apply_command_action(info_query,
#                                                            "http://jabber.org/protocol/admin#get-user-password",
#                                                            "execute")
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)
#         xml_command = result[0].xpath_eval("c:command",
#                                            {"c": "http://jabber.org/protocol/commands"})[0]
#         self.assertEquals(xml_command.prop("status"), "executing")
#         self.assertNotEquals(xml_command.prop("sessionid"), None)
#         self._check_actions(result[0], ["next"])

#         # Second step
#         info_query = Iq(stanza_type="set",
#                         from_jid="admin@test.com",
#                         to_jid=self.comp.jid)
#         command_node = info_query.set_new_content(command.COMMAND_NS, "command")
#         command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-password")
#         session_id = xml_command.prop("sessionid")
#         command_node.setProp("sessionid", session_id)
#         command_node.setProp("action", "next")
#         submit_form = Form(xmlnode_or_type="submit")
#         submit_form.add_field(field_type="jid-single",
#                               name="user_jid",
#                               value="test1@test.com")
#         submit_form.as_xml(command_node)
#         result = self.command_manager.apply_command_action(info_query,
#                                                            "http://jabber.org/protocol/admin#get-user-password",
#                                                            "execute")
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)
#         xml_command = result[0].xpath_eval("c:command",
#                                            {"c": "http://jabber.org/protocol/commands"})[0]
#         self.assertEquals(xml_command.prop("status"), "executing")
#         self.assertEquals(xml_command.prop("sessionid"), session_id)
#         self._check_actions(result[0], ["prev", "complete"], 1)
#         context_session = self.command_manager.sessions[session_id][1]
#         self.assertEquals(context_session["user_jid"],
#                           ["test1@test.com"])

#         # Third step
#         info_query = Iq(stanza_type="set",
#                         from_jid="admin@test.com",
#                         to_jid=self.comp.jid)
#         command_node = info_query.set_new_content(command.COMMAND_NS, "command")
#         command_node.setProp("node", "http://jabber.org/protocol/admin#get-user-password")
#         command_node.setProp("sessionid", session_id)
#         command_node.setProp("action", "complete")
#         submit_form = Form(xmlnode_or_type="submit")
#         submit_form.add_field(field_type="list-single",
#                               name="account_name",
#                               value="account11/test1@test.com")
#         submit_form.as_xml(command_node)
#         result = self.command_manager.apply_command_action(info_query,
#                                                            "http://jabber.org/protocol/admin#get-user-password",
#                                                            "execute")
#         xml_command = result[0].xpath_eval("c:command",
#                                            {"c": "http://jabber.org/protocol/commands"})[0]
#         self.assertEquals(xml_command.prop("status"), "completed")
#         self.assertEquals(xml_command.prop("sessionid"), session_id)
#         self._check_actions(result[0])
#         self.assertEquals(context_session["account_name"],
#                           ["account11/test1@test.com"])
#         stanza_sent = result
#         self.assertEquals(len(stanza_sent), 1)
#         iq_result = stanza_sent[0]
#         self.assertTrue(isinstance(iq_result, Iq))
#         self.assertEquals(iq_result.get_node().prop("type"), "result")
#         self.assertEquals(iq_result.get_from(), self.comp.jid)
#         self.assertEquals(iq_result.get_to(), "admin@test.com")
#         fields = iq_result.xpath_eval("c:command/data:x/data:field",
#                                       {"c": "http://jabber.org/protocol/commands",
#                                        "data": "jabber:x:data"})
#         self.assertEquals(len(fields), 3)
#         self.assertEquals(fields[0].prop("var"), "FORM_TYPE")
#         self.assertEquals(fields[0].prop("type"), "hidden")
#         self.assertEquals(fields[0].children.name, "value")
#         self.assertEquals(fields[0].children.content,
#                           "http://jabber.org/protocol/admin")
#         self.assertEquals(fields[1].prop("var"), "accountjids")
#         self.assertEquals(fields[1].children.name, "value")
#         self.assertEquals(fields[1].children.content,
#                           "test1@test.com")
#         self.assertEquals(fields[2].prop("var"), "password")
#         self.assertEquals(fields[2].children.name, "value")
#         self.assertEquals(fields[2].children.content,
#                           "pass1")

# disabled command
#     def test_execute_change_user_password(self):
#         self.comp.account_manager.account_classes = (ExampleAccount,
#                                                      Example2Account)
#         model.db_connect()
#         user1 = User(jid="test1@test.com")
#         account11 = ExampleAccount(user=user1,
#                                    name="account11",
#                                    jid="account11@" + unicode(self.comp.jid))
#         account11.password = "pass1"
#         account12 = Example2Account(user=user1,
#                                     name="account12",
#                                     jid="account12@" + unicode(self.comp.jid))
#         user2 = User(jid="test2@test.com")
#         account21 = ExampleAccount(user=user2,
#                                    name="account21",
#                                    jid="account21@" + unicode(self.comp.jid))
#         account22 = ExampleAccount(user=user2,
#                                    name="account11",
#                                    jid="account11@" + unicode(self.comp.jid))
#         model.db_disconnect()
#         info_query = Iq(stanza_type="set",
#                         from_jid="admin@test.com",
#                         to_jid=self.comp.jid)
#         command_node = info_query.set_new_content(command.COMMAND_NS, "command")
#         command_node.setProp("node", "http://jabber.org/protocol/admin#change-user-password")
#         result = self.command_manager.apply_command_action(info_query,
#                                                            "http://jabber.org/protocol/admin#change-user-password",
#                                                            "execute")
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)
#         xml_command = result[0].xpath_eval("c:command",
#                                            {"c": "http://jabber.org/protocol/commands"})[0]
#         self.assertEquals(xml_command.prop("status"), "executing")
#         self.assertNotEquals(xml_command.prop("sessionid"), None)
#         self._check_actions(result[0], ["next"])

#         # Second step
#         info_query = Iq(stanza_type="set",
#                         from_jid="admin@test.com",
#                         to_jid=self.comp.jid)
#         command_node = info_query.set_new_content(command.COMMAND_NS, "command")
#         command_node.setProp("node", "http://jabber.org/protocol/admin#change-user-password")
#         session_id = xml_command.prop("sessionid")
#         command_node.setProp("sessionid", session_id)
#         command_node.setProp("action", "next")
#         submit_form = Form(xmlnode_or_type="submit")
#         submit_form.add_field(field_type="jid-single",
#                               name="user_jid",
#                               value="test1@test.com")
#         submit_form.as_xml(command_node)
#         result = self.command_manager.apply_command_action(info_query,
#                                                            "http://jabber.org/protocol/admin#change-user-password",
#                                                            "execute")
#         self.assertNotEquals(result, None)
#         self.assertEquals(len(result), 1)
#         xml_command = result[0].xpath_eval("c:command",
#                                            {"c": "http://jabber.org/protocol/commands"})[0]
#         self.assertEquals(xml_command.prop("status"), "executing")
#         self.assertEquals(xml_command.prop("sessionid"), session_id)
#         self._check_actions(result[0], ["prev", "complete"], 1)
#         context_session = self.command_manager.sessions[session_id][1]
#         self.assertEquals(context_session["user_jid"],
#                           ["test1@test.com"])
#         fields = result[0].xpath_eval("c:command/data:x/data:field",
#                                       {"c": "http://jabber.org/protocol/commands",
#                                        "data": "jabber:x:data"})
#         self.assertEquals(len(fields), 2)

#         # Third step
#         info_query = Iq(stanza_type="set",
#                         from_jid="admin@test.com",
#                         to_jid=self.comp.jid)
#         command_node = info_query.set_new_content(command.COMMAND_NS, "command")
#         command_node.setProp("node", "http://jabber.org/protocol/admin#change-user-password")
#         command_node.setProp("sessionid", session_id)
#         command_node.setProp("action", "complete")
#         submit_form = Form(xmlnode_or_type="submit")
#         submit_form.add_field(field_type="list-single",
#                               name="account_name",
#                               value="account11/test1@test.com")
#         submit_form.add_field(field_type="text-private",
#                               name="password",
#                               value="pass2")
#         submit_form.as_xml(command_node)
#         result = self.command_manager.apply_command_action(info_query,
#                                                            "http://jabber.org/protocol/admin#change-user-password",
#                                                            "execute")
#         xml_command = result[0].xpath_eval("c:command",
#                                            {"c": "http://jabber.org/protocol/commands"})[0]
#         self.assertEquals(xml_command.prop("status"), "completed")
#         self.assertEquals(xml_command.prop("sessionid"), session_id)
#         self._check_actions(result[0])
#         self.assertEquals(context_session["account_name"],
#                           ["account11/test1@test.com"])
#         self.assertEquals(context_session["password"],
#                           ["pass2"])
#         self.assertEquals(account11.password, "pass2")

class JCLCommandManagerGetUserRosterCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-user-roster' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#get-user-roster")
        ljid111 = LegacyJID(legacy_address="test111@test.com",
                            jid="test111%test.com@" + unicode(self.comp.jid),
                            account=self.account11)
        ljid112 = LegacyJID(legacy_address="test112@test.com",
                            jid="test112%test.com@" + unicode(self.comp.jid),
                            account=self.account11)
        ljid121 = LegacyJID(legacy_address="test121@test.com",
                            jid="test121%test.com@" + unicode(self.comp.jid),
                            account=self.account12)
        ljid211 = LegacyJID(legacy_address="test211@test.com",
                            jid="test211%test.com@" + unicode(self.comp.jid),
                            account=self.account21)
        ljid212 = LegacyJID(legacy_address="test212@test.com",
                            jid="test212%test.com@" + unicode(self.comp.jid),
                            account=self.account21)
        ljid221 = LegacyJID(legacy_address="test221@test.com",
                            jid="test221%test.com@" + unicode(self.comp.jid),
                            account=self.account22)

    def test_execute_get_user_roster(self):
        result = self.command_manager.apply_command_action(
            self.info_query,
            "http://jabber.org/protocol/admin#get-user-roster",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_get_user_roster + "</title>"
                + "<instructions>" + Lang.en.command_get_user_roster_1_description
                + "</instructions>"
                + "<field var='user_jid' type='jid-single' label='"
                + Lang.en.field_user_jid + "'>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#get-user-roster",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="jid-single",
                          name="user_jid",
                          value="test1@test.com")],
            action="complete")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-user-roster",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='result'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='user_jid' label='" + Lang.en.field_user_jid
                + "'><value>test1@test.com</value></field>"
                + "<query xmlns='jabber:iq:roster'>"
                + "<item jid=\"account11@jcl.test.com\" name=\"account11\"/>"
                + "<item jid=\"account12@jcl.test.com\" name=\"account12\"/>"
                + "<item jid=\"test111%test.com@jcl.test.com\" "
                + "name=\"test111@test.com\"/>"
                + "<item jid=\"test112%test.com@jcl.test.com\" "
                + "name=\"test112@test.com\"/>"
                + "<item jid=\"test121%test.com@jcl.test.com\" "
                + "name=\"test121@test.com\"/></query>"
                + "</x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jid"],
                          ["test1@test.com"])

class JCLCommandManagerGetUserLastLoginCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-user-lastlogin' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#get-user-lastlogin")

    def test_execute_get_user_lastlogin(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-user-lastlogin",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='next'><next/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_get_user_lastlogin + "</title>"
                + "<instructions>" + Lang.en.command_get_user_lastlogin_1_description
                + "</instructions>"
                + "<field var='user_jid' type='jid-single' label='"
                + Lang.en.field_user_jid + "'>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#get-user-lastlogin",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="jid-single",
                          name="user_jid",
                          value="test1@test.com")])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-user-lastlogin",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><prev/><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_get_user_lastlogin + "</title>"
                + "<instructions>" + Lang.en.command_get_user_lastlogin_2_description
                + "</instructions>"
                + "<field var='account_name' type='list-single' label='"
                + Lang.en.field_account + "'>"
                + "<option label=\"account11 (Example) (test1@test.com)\">"
                + "<value>account11/test1@test.com</value></option>"
                + "<option label=\"account12 (Example2) (test1@test.com)\">"
                + "<value>account12/test1@test.com</value></option>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["user_jid"],
                          ["test1@test.com"])

        # Third step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#get-user-lastlogin",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-single",
                          name="account_name",
                          value="account11/test1@test.com")],
            action="complete")
        result = self.command_manager.apply_command_action(info_query,
                                                           "http://jabber.org/protocol/admin#get-user-lastlogin",
                                                           "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='result'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='user_jid' label='" + Lang.en.field_user_jid
                + "'><value>test1@test.com</value></field>"
                + "<field var='lastlogin'><value>"
                + self.account11.lastlogin.isoformat(" ")
                + "</value></field></x></command></iq>",
                result_iq, True))

class JCLCommandManagerGetRegisteredUsersNumCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-registered-users-num' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#get-registered-users-num")

    def test_execute_get_registered_users_num(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-registered-users-num",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='result'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='registeredusersnum' label='"
                + Lang.en.field_registered_users_num + "'><value>6</value>"
                + "</field></x></command></iq>",
                result_iq, True))

class JCLCommandManagerGetDisabledUsersNumCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-disabled-users-num' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.account11.enabled = False
        self.account22.enabled = False
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#get-disabled-users-num")

    def test_execute_get_disabled_users_num(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-disabled-users-num",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='result'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='disabledusersnum' label='"
                + Lang.en.field_disabled_users_num + "'><value>2</value>"
                + "</field></x></command></iq>",
                result_iq, True))

class JCLCommandManagerGetOnlineUsersNumCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-online-users-num' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account22.status = "chat"
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#get-online-users-num")

    def test_execute_get_online_users_num(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-online-users-num",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='result'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='onlineusersnum' label='"
                + Lang.en.field_online_users_num + "'><value>3</value>"
                + "</field></x></command></iq>",
                result_iq, True))

class JCLCommandManagerGetRegisteredUsersListCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-registered-users-list' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#get-registered-users-list")

    def test_execute_get_registered_users_list(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-registered-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='registeredusers' label='"
                + Lang.en.field_registered_users_list + "'>"
                + "<value>test1@test.com (account11 ExampleAccount)</value>"
                + "<value>test1@test.com (account12 Example2Account)</value>"
                + "<value>test2@test.com (account21 ExampleAccount)</value>"
                + "<value>test2@test.com (account11 ExampleAccount)</value>"
                + "<value>test3@test.com (account31 ExampleAccount)</value>"
                + "<value>test3@test.com (account32 Example2Account)</value>"
                + "</field></x></command></iq>",
                result_iq, True))

    def test_execute_get_registered_users_list_max(self):
        user10 = User(jid="test10@test.com")
        user20 = User(jid="test20@test.com")
        for i in xrange(10):
            ExampleAccount(user=user10,
                           name="account101" + str(i),
                           jid="account101" + str(i) + "@" + unicode(self.comp.jid))
            Example2Account(user=user10,
                            name="account102" + str(i),
                            jid="account102" + str(i) + "@" + unicode(self.comp.jid))
            ExampleAccount(user=user20,
                           name="account20" + str(i),
                           jid="account20" + str(i) + "@" + unicode(self.comp.jid))
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-registered-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='max_items' type='list-single' label='"
                + Lang.en.field_max_items + "'>"
                + "<option label='25'><value>25</value></option>"
                + "<option label='50'><value>50</value></option>"
                + "<option label='75'><value>75</value></option>"
                + "<option label='100'><value>100</value></option>"
                + "<option label='150'><value>150</value></option>"
                + "<option label='200'><value>200</value></option>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#get-registered-users-list",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-single",
                          name="max_items",
                          value="25")])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-registered-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='registeredusers' label='"
                + Lang.en.field_registered_users_list + "'>"
                + "<value>test1@test.com (account11 ExampleAccount)</value>"
                + "<value>test1@test.com (account12 Example2Account)</value>"
                + "<value>test2@test.com (account21 ExampleAccount)</value>"
                + "<value>test2@test.com (account11 ExampleAccount)</value>"
                + "<value>test3@test.com (account31 ExampleAccount)</value>"
                + "<value>test3@test.com (account32 Example2Account)</value>"
                + "<value>test10@test.com (account1010 ExampleAccount)</value>"
                + "<value>test10@test.com (account1020 Example2Account)</value>"
                + "<value>test20@test.com (account200 ExampleAccount)</value>"
                + "<value>test10@test.com (account1011 ExampleAccount)</value>"
                + "<value>test10@test.com (account1021 Example2Account)</value>"
                + "<value>test20@test.com (account201 ExampleAccount)</value>"
                + "<value>test10@test.com (account1012 ExampleAccount)</value>"
                + "<value>test10@test.com (account1022 Example2Account)</value>"
                + "<value>test20@test.com (account202 ExampleAccount)</value>"
                + "<value>test10@test.com (account1013 ExampleAccount)</value>"
                + "<value>test10@test.com (account1023 Example2Account)</value>"
                + "<value>test20@test.com (account203 ExampleAccount)</value>"
                + "<value>test10@test.com (account1014 ExampleAccount)</value>"
                + "<value>test10@test.com (account1024 Example2Account)</value>"
                + "<value>test20@test.com (account204 ExampleAccount)</value>"
                + "<value>test10@test.com (account1015 ExampleAccount)</value>"
                + "<value>test10@test.com (account1025 Example2Account)</value>"
                + "<value>test20@test.com (account205 ExampleAccount)</value>"
                + "<value>test10@test.com (account1016 ExampleAccount)</value>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["max_items"],
                          ["25"])

class JCLCommandManagerGetDisabledUsersListCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-disabled-users-list' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#get-disabled-users-list")

    def test_execute_get_disabled_users_list(self):
        self.account11.enabled = False
        self.account12.enabled = False
        self.account22.enabled = False
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-disabled-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='disabledusers' label='"
                + Lang.en.field_disabled_users_list + "'>"
                + "<value>test1@test.com (account11 ExampleAccount)</value>"
                + "<value>test1@test.com (account12 Example2Account)</value>"
                + "<value>test2@test.com (account11 ExampleAccount)</value>"
                + "</field></x></command></iq>",
                result_iq, True))

    def test_execute_get_disabled_users_list_max(self):
        user10 = User(jid="test10@test.com")
        user20 = User(jid="test20@test.com")
        for i in xrange(20):
            _account = ExampleAccount(user=user10,
                                      name="account101" + str(i),
                                      jid="account101" + str(i)
                                      + "@" + unicode(self.comp.jid))
            _account.enabled = False
            Example2Account(user=user10,
                            name="account102" + str(i),
                            jid="account102" + str(i) + "@" + unicode(self.comp.jid))
            _account = ExampleAccount(user=user20,
                                      name="account20" + str(i),
                                      jid="account20" + str(i)
                                      + "@" + unicode(self.comp.jid))
            _account.enabled = False
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-disabled-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='max_items' type='list-single' label='"
                + Lang.en.field_max_items + "'>"
                + "<option label='25'><value>25</value></option>"
                + "<option label='50'><value>50</value></option>"
                + "<option label='75'><value>75</value></option>"
                + "<option label='100'><value>100</value></option>"
                + "<option label='150'><value>150</value></option>"
                + "<option label='200'><value>200</value></option>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#get-disabled-users-list",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-single",
                          name="max_items",
                          value="25")])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-disabled-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='disabledusers' label='"
                + Lang.en.field_disabled_users_list + "'>"
                + "<value>test10@test.com (account1010 ExampleAccount)</value>"
                + "<value>test20@test.com (account200 ExampleAccount)</value>"
                + "<value>test10@test.com (account1011 ExampleAccount)</value>"
                + "<value>test20@test.com (account201 ExampleAccount)</value>"
                + "<value>test10@test.com (account1012 ExampleAccount)</value>"
                + "<value>test20@test.com (account202 ExampleAccount)</value>"
                + "<value>test10@test.com (account1013 ExampleAccount)</value>"
                + "<value>test20@test.com (account203 ExampleAccount)</value>"
                + "<value>test10@test.com (account1014 ExampleAccount)</value>"
                + "<value>test20@test.com (account204 ExampleAccount)</value>"
                + "<value>test10@test.com (account1015 ExampleAccount)</value>"
                + "<value>test20@test.com (account205 ExampleAccount)</value>"
                + "<value>test10@test.com (account1016 ExampleAccount)</value>"
                + "<value>test20@test.com (account206 ExampleAccount)</value>"
                + "<value>test10@test.com (account1017 ExampleAccount)</value>"
                + "<value>test20@test.com (account207 ExampleAccount)</value>"
                + "<value>test10@test.com (account1018 ExampleAccount)</value>"
                + "<value>test20@test.com (account208 ExampleAccount)</value>"
                + "<value>test10@test.com (account1019 ExampleAccount)</value>"
                + "<value>test20@test.com (account209 ExampleAccount)</value>"
                + "<value>test10@test.com (account10110 ExampleAccount)</value>"
                + "<value>test20@test.com (account2010 ExampleAccount)</value>"
                + "<value>test10@test.com (account10111 ExampleAccount)</value>"
                + "<value>test20@test.com (account2011 ExampleAccount)</value>"
                + "<value>test10@test.com (account10112 ExampleAccount)</value>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["max_items"],
                          ["25"])

class JCLCommandManagerGetOnlineUsersListCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-online-users-list' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#get-online-users-list")

    def test_execute_get_online_users_list(self):
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account22.status = "xa"
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-online-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='onlineusers' label='"
                + Lang.en.field_online_users_list + "'>"
                + "<value>test1@test.com (account11 ExampleAccount)</value>"
                + "<value>test1@test.com (account12 Example2Account)</value>"
                + "<value>test2@test.com (account11 ExampleAccount)</value>"
                + "</field></x></command></iq>",
                result_iq, True))

    def test_execute_get_online_users_list_max(self):
        user10 = User(jid="test10@test.com")
        user20 = User(jid="test20@test.com")
        for i in xrange(20):
            _account = ExampleAccount(user=user10,
                                      name="account101" + str(i),
                                      jid="account101" + str(i)
                                      + "@" + unicode(self.comp.jid))
            _account.status = account.ONLINE
            Example2Account(user=user10,
                            name="account102" + str(i),
                            jid="account102" + str(i) + "@" + unicode(self.comp.jid))
            _account = ExampleAccount(user=user20,
                                      name="account20" + str(i),
                                      jid="account20" + str(i)
                                      + "@" + unicode(self.comp.jid))
            _account.status = "away"
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#get-online-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='max_items' type='list-single' label='"
                + Lang.en.field_max_items + "'>"
                + "<option label='25'><value>25</value></option>"
                + "<option label='50'><value>50</value></option>"
                + "<option label='75'><value>75</value></option>"
                + "<option label='100'><value>100</value></option>"
                + "<option label='150'><value>150</value></option>"
                + "<option label='200'><value>200</value></option>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#get-online-users-list",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-single",
                          name="max_items",
                          value="25")])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#get-online-users-list",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='onlineusers' label='"
                + Lang.en.field_online_users_list + "'>"
                + "<value>test10@test.com (account1010 ExampleAccount)</value>"
                + "<value>test20@test.com (account200 ExampleAccount)</value>"
                + "<value>test10@test.com (account1011 ExampleAccount)</value>"
                + "<value>test20@test.com (account201 ExampleAccount)</value>"
                + "<value>test10@test.com (account1012 ExampleAccount)</value>"
                + "<value>test20@test.com (account202 ExampleAccount)</value>"
                + "<value>test10@test.com (account1013 ExampleAccount)</value>"
                + "<value>test20@test.com (account203 ExampleAccount)</value>"
                + "<value>test10@test.com (account1014 ExampleAccount)</value>"
                + "<value>test20@test.com (account204 ExampleAccount)</value>"
                + "<value>test10@test.com (account1015 ExampleAccount)</value>"
                + "<value>test20@test.com (account205 ExampleAccount)</value>"
                + "<value>test10@test.com (account1016 ExampleAccount)</value>"
                + "<value>test20@test.com (account206 ExampleAccount)</value>"
                + "<value>test10@test.com (account1017 ExampleAccount)</value>"
                + "<value>test20@test.com (account207 ExampleAccount)</value>"
                + "<value>test10@test.com (account1018 ExampleAccount)</value>"
                + "<value>test20@test.com (account208 ExampleAccount)</value>"
                + "<value>test10@test.com (account1019 ExampleAccount)</value>"
                + "<value>test20@test.com (account209 ExampleAccount)</value>"
                + "<value>test10@test.com (account10110 ExampleAccount)</value>"
                + "<value>test20@test.com (account2010 ExampleAccount)</value>"
                + "<value>test10@test.com (account10111 ExampleAccount)</value>"
                + "<value>test20@test.com (account2011 ExampleAccount)</value>"
                + "<value>test10@test.com (account10112 ExampleAccount)</value>"
                + "</field></x></command></iq>",
                result_iq, True))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["max_items"],
                          ["25"])

class JCLCommandManagerAnnounceCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'announce' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account22.status = "xa"
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#announce")

    def _common_execute_announce(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#announce",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_announce + "</title>"
                + "<instructions>" + Lang.en.command_announce_1_description
                + "</instructions>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='announcement' type='text-multi' label='"
                + Lang.en.field_announcement + "'>"
                + "<required /></field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)
        return session_id

    def test_execute_announce(self):
        session_id = self._common_execute_announce()
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#announce",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="text-multi",
                          name="announcement",
                          value=["test announce"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#announce",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        result_iq = result[1].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test1@test.com'>"
                + "<body>test announce</body></message>",
                result_iq, True, test_sibling=False))
        result_iq = result[2].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test2@test.com'>"
                + "<body>test announce</body></message>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["announcement"],
                          ["test announce"])

    def test_execute_announce_no_announcement(self):
        session_id = self._common_execute_announce()
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#announce",
            session_id=session_id,
            from_jid="admin@test.com")
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#announce",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertFalse(context_session.has_key("announcement"))

class JCLCommandManagerSetMOTDCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'set-motd' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account21.status = account.OFFLINE
        self.account22.status = account.OFFLINE
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#set-motd")

    def test_execute_set_motd(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#set-motd",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_set_motd + "</title>"
                + "<instructions>" + Lang.en.command_set_motd_1_description
                + "</instructions>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='motd' type='text-multi' label='"
                + Lang.en.field_motd + "'><value> </value>"
                + "<required /></field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#edit-motd",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="text-multi",
                          name="motd",
                          value=["Message Of The Day"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#set-motd",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        result_iq = result[1].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test1@test.com'>"
                + "<body>Message Of The Day</body></message>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["motd"],
                          ["Message Of The Day"])
        self.assertTrue(self.account11.user.has_received_motd)
        self.assertFalse(self.account21.user.has_received_motd)

class JCLCommandManagerEditMOTDCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'edit-motd' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.comp.set_motd("test motd")
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.user2.has_received_motd = True
        self.account21.status = account.OFFLINE
        self.account22.status = account.OFFLINE
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#edit-motd")

    def test_execute_edit_motd(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#edit-motd",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_set_motd + "</title>"
                + "<instructions>" + Lang.en.command_set_motd_1_description
                + "</instructions>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='motd' type='text-multi' label='"
                + Lang.en.field_motd + "'><value>test motd</value>"
                + "<required /></field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#edit-motd",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="text-multi",
                          name="motd",
                          value=["Message Of The Day"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#edit-motd",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        result_iq = result[1].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test1@test.com'>"
                + "<body>Message Of The Day</body></message>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["motd"],
                          ["Message Of The Day"])
        self.assertTrue(self.account11.user.has_received_motd)
        self.assertFalse(self.account21.user.has_received_motd)
        self.comp.config.read(self.comp.config_file)
        self.assertTrue(self.comp.config.has_option("component", "motd"))
        self.assertEquals(self.comp.config.get("component", "motd"),
                          "Message Of The Day")

class JCLCommandManagerDeleteMOTDCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'delete-motd' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.comp.set_motd("test motd")
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account21.status = account.OFFLINE
        self.account22.status = account.OFFLINE
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#delete-motd")

    def test_execute_delete_motd(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#delete-motd",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        self.comp.config.read(self.comp.config_file)
        self.assertFalse(self.comp.config.has_option("component", "motd"))

class JCLCommandManagerSetWelcomeCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'set-welcome' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.comp.set_welcome_message("Welcome Message")
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account21.status = account.OFFLINE
        self.account22.status = account.OFFLINE
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#set-welcome")

    def test_execute_set_welcome(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#set-welcome",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_set_welcome + "</title>"
                + "<instructions>" + Lang.en.command_set_welcome_1_description
                + "</instructions>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='welcome' type='text-multi' label='"
                + Lang.en.field_welcome + "'><value>Welcome Message</value>"
                + "<required /></field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#set-welcome",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="text-multi",
                          name="welcome",
                          value=["New Welcome Message"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#set-welcome",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["welcome"],
                          ["New Welcome Message"])
        self.comp.config.read(self.comp.config_file)
        self.assertTrue(self.comp.config.has_option("component",
                                                    "welcome_message"))
        self.assertEquals(self.comp.config.get("component",
                                               "welcome_message"),
                          "New Welcome Message")

class JCLCommandManagerDeleteWelcomeCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'delete-welcome' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.comp.set_motd("test motd")
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account21.status = account.OFFLINE
        self.account22.status = account.OFFLINE
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#delete-welcome")

    def test_execute_delete_welcome(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#delete-welcome",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        self.comp.config.read(self.comp.config_file)
        self.assertFalse(self.comp.config.has_option("component",
                                                     "welcome_message"))

class JCLCommandManagerEditAdminCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'edit-admin' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.comp.set_admins(["admin1@test.com", "admin2@test.com"])
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account21.status = account.OFFLINE
        self.account22.status = account.OFFLINE
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#edit-admin")

    def test_execute_edit_admin(self):
        self.info_query.set_from("admin1@test.com")
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#edit-admin",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin1@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_edit_admin + "</title>"
                + "<instructions>" + Lang.en.command_edit_admin_1_description
                + "</instructions>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='adminjids' type='jid-multi' label='"
                + Lang.en.field_admin_jids + "'><value>admin1@test.com</value>"
                + "<value>admin2@test.com</value><required/>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)

        # Second step
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#edit-admin",
            session_id=session_id,
            from_jid="admin1@test.com",
            fields=[Field(field_type="jid-multi",
                          name="adminjids",
                          value=["admin3@test.com", "admin4@test.com"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#edit-admin",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin1@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["adminjids"],
                          ["admin3@test.com", "admin4@test.com"])
        self.comp.config.read(self.comp.config_file)
        self.assertTrue(self.comp.config.has_option("component", "admins"))
        self.assertEquals(self.comp.config.get("component", "admins"),
                          "admin3@test.com,admin4@test.com")

class JCLCommandManagerRestartCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'restart' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.comp.running = True
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account22.status = "xa"
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#restart")
        self.wait_event = threading.Event()
        self.command_manager.sleep = lambda delay: self.wait_event.wait(2)

    def _common_execute_restart(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#restart",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_restart + "</title>"
                + "<instructions>" + Lang.en.command_restart_1_description
                + "</instructions>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='delay' type='list-single' label='"
                + Lang.en.field_restart_delay + "'>"
                + "<option label='" + Lang.en.field_30_sec + "'>"
                + "<value>30</value></option>"
                + "<option label='" + Lang.en.field_60_sec + "'>"
                + "<value>60</value></option>"
                + "<option label='" + Lang.en.field_90_sec + "'>"
                + "<value>90</value></option>"
                + "<option label='" + Lang.en.field_120_sec + "'>"
                + "<value>120</value></option>"
                + "<option label='" + Lang.en.field_180_sec + "'>"
                + "<value>180</value></option>"
                + "<option label='" + Lang.en.field_240_sec + "'>"
                + "<value>240</value></option>"
                + "<option label='" + Lang.en.field_300_sec + "'>"
                + "<value>300</value></option><required/></field>"
                + "<field label='" + Lang.en.field_announcement + "' "
                + "type='text-multi' var='announcement'>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)
        return session_id

    def test_execute_restart(self):
        session_id = self._common_execute_restart()
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#restart",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-multi",
                          name="delay",
                          value=[1]),
                    Field(field_type="text-multi",
                          name="announcement",
                          value=["service will be restarted in 1 second"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#restart",
            "execute")
        self.assertFalse(self.comp.restart)
        self.assertTrue(self.comp.running)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 2)
        self.wait_event.set()
        self.command_manager.restart_thread.join(1)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertTrue(self.comp.restart)
        self.assertFalse(self.comp.running)

        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        result_iq = result[1].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test1@test.com'>"
                + "<body>service will be restarted in 1 second</body></message>",
                result_iq, True, test_sibling=False))
        result_iq = result[2].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test2@test.com'>"
                + "<body>service will be restarted in 1 second</body></message>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["announcement"],
                          ["service will be restarted in 1 second"])
        self.assertEquals(context_session["delay"],
                          ["1"])

    def test_execute_restart_no_announcement(self):
        session_id = self._common_execute_restart()
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#restart",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-multi",
                          name="delay",
                          value=[1])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#restart",
            "execute")
        self.assertFalse(self.comp.restart)
        self.assertTrue(self.comp.running)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 2)
        self.wait_event.set()
        self.command_manager.restart_thread.join(1)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertTrue(self.comp.restart)
        self.assertFalse(self.comp.running)

        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertFalse(context_session.has_key("announcement"))
        self.assertEquals(context_session["delay"],
                          ["1"])

class JCLCommandManagerShutdownCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'shutdown' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.comp.running = True
        self.account11.status = account.ONLINE
        self.account12.status = "away"
        self.account22.status = "xa"
        self.command_node.setProp("node",
                                  "http://jabber.org/protocol/admin#shutdown")
        self.wait_event = threading.Event()
        self.command_manager.sleep = lambda delay: self.wait_event.wait(2)

    def _common_execute_shutdown(self):
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "http://jabber.org/protocol/admin#shutdown",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='executing'>"
                + "<actions execute='complete'><complete/></actions>"
                + "<x xmlns='jabber:x:data' type='form'>"
                + "<title>" + Lang.en.command_shutdown + "</title>"
                + "<instructions>" + Lang.en.command_shutdown_1_description
                + "</instructions>"
                + "<field var='FORM_TYPE' type='hidden'><value>"
                + "http://jabber.org/protocol/admin</value></field>"
                + "<field var='delay' type='list-single' label='"
                + Lang.en.field_shutdown_delay + "'>"
                + "<option label='" + Lang.en.field_30_sec + "'>"
                + "<value>30</value></option>"
                + "<option label='" + Lang.en.field_60_sec + "'>"
                + "<value>60</value></option>"
                + "<option label='" + Lang.en.field_90_sec + "'>"
                + "<value>90</value></option>"
                + "<option label='" + Lang.en.field_120_sec + "'>"
                + "<value>120</value></option>"
                + "<option label='" + Lang.en.field_180_sec + "'>"
                + "<value>180</value></option>"
                + "<option label='" + Lang.en.field_240_sec + "'>"
                + "<value>240</value></option>"
                + "<option label='" + Lang.en.field_300_sec + "'>"
                + "<value>300</value></option><required/></field>"
                + "<field label='" + Lang.en.field_announcement + "' "
                + "type='text-multi' var='announcement'>"
                + "</field></x></command></iq>",
                result_iq, True))
        session_id = result_iq.children.prop("sessionid")
        self.assertNotEquals(session_id, None)
        return session_id

    def test_execute_shutdown(self):
        session_id = self._common_execute_shutdown()
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#shutdown",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-multi",
                          name="delay",
                          value=[1]),
                    Field(field_type="text-multi",
                          name="announcement",
                          value=["service will be shutdown in 1 second"])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#shutdown",
            "execute")
        self.assertFalse(self.comp.restart)
        self.assertTrue(self.comp.running)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 2)
        self.wait_event.set()
        self.command_manager.shutdown_thread.join(1)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertFalse(self.comp.restart)
        self.assertFalse(self.comp.running)

        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        result_iq = result[1].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test1@test.com'>"
                + "<body>service will be shutdown in 1 second</body></message>",
                result_iq, True, test_sibling=False))
        result_iq = result[2].xmlnode
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<message from='" + unicode(self.comp.jid) + "' "
                + "xmlns=\"http://pyxmpp.jabberstudio.org/xmlns/common\" "
                + "to='test2@test.com'>"
                + "<body>service will be shutdown in 1 second</body></message>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertEquals(context_session["announcement"],
                          ["service will be shutdown in 1 second"])
        self.assertEquals(context_session["delay"],
                          ["1"])

    def test_execute_shutdown_no_announcement(self):
        session_id = self._common_execute_shutdown()
        info_query = prepare_submit(\
            node="http://jabber.org/protocol/admin#shutdown",
            session_id=session_id,
            from_jid="admin@test.com",
            fields=[Field(field_type="list-multi",
                          name="delay",
                          value=[1])])
        result = self.command_manager.apply_command_action(\
            info_query,
            "http://jabber.org/protocol/admin#shutdown",
            "execute")
        self.assertFalse(self.comp.restart)
        self.assertTrue(self.comp.running)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 2)
        self.wait_event.set()
        self.command_manager.shutdown_thread.join(1)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        self.assertFalse(self.comp.restart)
        self.assertFalse(self.comp.running)

        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='jcl.test.com' to='admin@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands' "
                + "status='completed' sessionid='" + session_id + "'>"
                + "</command></iq>",
                result_iq, True, test_sibling=False))
        context_session = self.command_manager.sessions[session_id][1]
        self.assertFalse(context_session.has_key("announcement"))
        self.assertEquals(context_session["delay"],
                          ["1"])

class JCLCommandManagerGetLastErrorCommand_TestCase(JCLCommandManagerTestCase):
    """
    Test 'get-last-error' ad-hoc command
    """

    def setUp (self, tables=[]):
        """
        Prepare data
        """
        JCLCommandManagerTestCase.setUp(self, tables)
        self.command_node.setProp("node", "jcl#get-last-error")

    def test_execute_get_last_error_no_error(self):
        self.info_query.set_from("test1@test.com")
        self.info_query.set_to("account11@" + unicode(self.comp.jid))
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "jcl#get-last-error",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='account11@" + unicode(self.comp.jid)
                + "' to='test1@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='result'>"
                + "<field label='"
                + Lang.en.field_last_error + "'>"
                + "<value>" + Lang.en.account_no_error + "</value>"
                + "</field></x></command></iq>",
                result_iq, True))

    def test_execute_get_last_error(self):
        self.info_query.set_from("test1@test.com")
        self.info_query.set_to("account11@" + unicode(self.comp.jid))
        self.account11.error = "Current error"
        result = self.command_manager.apply_command_action(\
            self.info_query,
            "jcl#get-last-error",
            "execute")
        result_iq = result[0].xmlnode
        result_iq.setNs(None)
        self.assertTrue(jcl.tests.is_xml_equal(\
                u"<iq from='account11@" + unicode(self.comp.jid)
                + "' to='test1@test.com' type='result'>"
                + "<command xmlns='http://jabber.org/protocol/commands'"
                + "status='completed'>"
                + "<x xmlns='jabber:x:data' type='result'>"
                + "<field label='"
                + Lang.en.field_last_error + "'>"
                + "<value>Current error</value>"
                + "</field></x></command></iq>",
                result_iq, True))

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(CommandManager_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(FieldNoType_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManager_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerAddFormSelectUserJID_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerAddFormSelectAccount_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerAddUserCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerDeleteUserCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerDisableUserCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerReenableUserCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerEndUserSessionCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerGetUserRosterCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerGetUserLastLoginCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerGetRegisteredUsersNumCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerGetDisabledUsersNumCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerGetOnlineUsersNumCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerAnnounceCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerSetMOTDCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerEditMOTDCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerDeleteMOTDCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerSetWelcomeCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerDeleteWelcomeCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerEditAdminCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerRestartCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerShutdownCommand_TestCase, 'test'))
    test_suite.addTest(unittest.makeSuite(JCLCommandManagerGetLastErrorCommand_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    if '-v' in sys.argv:
        logger.setLevel(logging.INFO)
    unittest.main(defaultTest='suite')
