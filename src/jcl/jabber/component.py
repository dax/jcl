# -*- coding: utf-8 -*-
##
## component.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Aug  9 21:04:42 2006 David Rousselie
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

"""
JCL base component
"""

__revision__ = "$Id: component.py,v 1.3 2005/09/18 20:24:07 dax Exp $"

import sys

import threading
import logging
import signal
import re
import traceback

from Queue import Queue

import pyxmpp.error as error
from pyxmpp.jid import JID
from pyxmpp.jabberd.component import Component
from pyxmpp.message import Message
from pyxmpp.presence import Presence
from pyxmpp.jabber.dataforms import Form

from jcl.error import FieldError
from jcl.jabber.disco import AccountDiscoGetInfoHandler, \
     AccountTypeDiscoGetInfoHandler, RootDiscoGetItemsHandler, \
     AccountTypeDiscoGetItemsHandler
from jcl.jabber.message import PasswordMessageHandler
import jcl.jabber.command as command
from jcl.jabber.command import CommandDiscoGetItemsHandler, \
     CommandDiscoGetInfoHandler, JCLCommandManager, \
     CommandRootDiscoGetInfoHandler
from jcl.jabber.presence import AccountPresenceAvailableHandler, \
     RootPresenceAvailableHandler, AccountPresenceUnavailableHandler, \
     RootPresenceUnavailableHandler, AccountPresenceSubscribeHandler, \
     RootPresenceSubscribeHandler, AccountPresenceUnsubscribeHandler
from jcl.jabber.register import RootSetRegisterHandler, \
     AccountSetRegisterHandler, AccountTypeSetRegisterHandler
import jcl.model as model
from jcl.model import account
from jcl.model.account import Account
from jcl.lang import Lang

VERSION = "0.1"

###############################################################################
# JCL implementation
###############################################################################
class JCLComponent(Component, object):
    """
    Implement default JCL component behavior:
    - Jabber register process (add, delete, update accounts)
    - Jabber presence handling
    - passwork request at login
    - Service Administration (XEP-0133)
    """

    timeout = 1

    def __init__(self,
                 jid,
                 secret,
                 server,
                 port,
                 disco_category="headline",
                 disco_type="x-unknown",
                 lang=Lang()):
        Component.__init__(self,
                           JID(jid),
                           secret,
                           server,
                           port,
                           disco_category=disco_category,
                           disco_type=disco_type)
        # default values
        self.name = lang.get_default_lang_class().component_name
        self.spool_dir = "."
        self.version = VERSION
        self.time_unit = 60
        self.queue = Queue(100)
        self.account_manager = AccountManager(self)
        self.msg_handlers = []
        self.presence_subscribe_handlers = [[AccountPresenceSubscribeHandler(self),
                                             RootPresenceSubscribeHandler(self)]]
        self.presence_unsubscribe_handlers = [[AccountPresenceUnsubscribeHandler(self)]]
        self.presence_available_handlers = [[AccountPresenceAvailableHandler(self),
                                             RootPresenceAvailableHandler(self)]]
        self.presence_unavailable_handlers = [[AccountPresenceUnavailableHandler(self),
                                               RootPresenceUnavailableHandler(self)]]
        command.command_manager = JCLCommandManager()
        command.command_manager.component = self
        command.command_manager.account_manager = self.account_manager
        self.disco_get_items_handlers = [[RootDiscoGetItemsHandler(self),
                                          AccountTypeDiscoGetItemsHandler(self)],
                                         [CommandDiscoGetItemsHandler(self)]]
        self.disco_get_info_handlers = [[CommandRootDiscoGetInfoHandler(self),
                                         AccountDiscoGetInfoHandler(self),
                                         AccountTypeDiscoGetInfoHandler(self)],
                                        [CommandDiscoGetInfoHandler(self)]]
        self.set_register_handlers = [[RootSetRegisterHandler(self),
                                       AccountSetRegisterHandler(self),
                                       AccountTypeSetRegisterHandler(self)]]

        self.__logger = logging.getLogger("jcl.jabber.JCLComponent")
        self.lang = lang
        self.running = False
        self.wait_event = threading.Event()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def run(self):
        """
        Main loop
        Connect to Jabber server
        Start timer thread
        Call Component main loop
        Clean up when shutting down JCLcomponent
        """
        self.spool_dir += "/" + unicode(self.jid)
        self.running = True
        self.connect()
        timer_thread = threading.Thread(target=self.time_handler,
                                        name="TimerThread")
        timer_thread.start()
        try:
            while (self.running and self.stream
                   and not self.stream.eof
                   and self.stream.socket is not None):
                self.stream.loop_iter(JCLComponent.timeout)
                if self.queue.qsize():
                    raise self.queue.get(0)
        finally:
            self.running = False
            if self.stream and not self.stream.eof \
                   and self.stream.socket is not None:
                presences = self.account_manager.send_presence_all("unavailable")
                self.send_stanzas(presences)
            self.wait_event.set()
            timer_thread.join(JCLComponent.timeout)
            self.disconnect()
            self.__logger.debug("Exitting normally")

    ###########################################################################
    # Handlers
    ###########################################################################
    def time_handler(self):
        """
        Timer thread handler
        """
        self.__logger.info("Timer thread started...")
        try:
            while (self.running and self.stream
                   and not self.stream.eof
                   and self.stream.socket is not None):
                self.wait_event.wait(self.time_unit)
                self.handle_tick()
                self.__logger.debug("Resetting alarm signal")
        except Exception, exception:
            type, value, stack = sys.exc_info()
            self.__logger.error("Error in timer thread\n%s\n%s"
                                % (exception, "".join(traceback.format_exception
                                                      (type, value, stack, 5))))
            self.queue.put(exception)
        self.__logger.info("Timer thread terminated...")

    def authenticated(self):
        """
        Override authenticated Component event handler
        Register event handlers
        Probe for every accounts registered
        """
        self.__logger.debug("AUTHENTICATED")
        Component.authenticated(self)
        self.stream.set_iq_get_handler("query", "jabber:iq:version",
                                       self.handle_get_version)
        self.stream.set_iq_get_handler("query", "jabber:iq:register",
                                       self.handle_get_register)
        self.stream.set_iq_set_handler("query", "jabber:iq:register",
                                       self.handle_set_register)
        self.stream.set_iq_get_handler("query", "jabber:iq:gateway",
                                       self.handle_get_gateway)
        self.stream.set_iq_set_handler("query", "jabber:iq:gateway",
                                       self.handle_set_gateway)

        self.stream.set_iq_set_handler("command", command.COMMAND_NS,
                                       self.handle_command)

        self.stream.set_presence_handler("available",
                                         self.handle_presence_available)

        self.stream.set_presence_handler("probe",
                                         self.handle_presence_available)

        self.stream.set_presence_handler("unavailable",
                                         self.handle_presence_unavailable)

        self.stream.set_presence_handler("unsubscribe",
                                         self.handle_presence_unsubscribe)
        self.stream.set_presence_handler("unsubscribed",
                                         self.handle_presence_unsubscribed)
        self.stream.set_presence_handler("subscribe",
                                         self.handle_presence_subscribe)
        self.stream.set_presence_handler("subscribed",
                                         self.handle_presence_subscribed)

        self.stream.set_message_handler("normal",
                                        self.handle_message)
        self.send_stanzas(self.account_manager.probe_all_accounts_presence())

        self.msg_handlers += [[PasswordMessageHandler(self)]]

    def signal_handler(self, signum, frame):
        """Stop method handler
        """
        self.__logger.debug("Signal %i received, shutting down..." % (signum,))
        self.running = False

    def send_stanzas(self, stanzas):
        """Send given stanza list"""
        self.__logger.debug("Sending responses")
        if stanzas is not None:
            for stanza in stanzas:
                self.stream.send(stanza)

    def apply_behavior(self, info_query,
                       account_handler,
                       account_type_handler,
                       root_handler,
                       send_result=False):
        """Apply given handler depending on info_query receiver"""
        from_jid = info_query.get_from()
        to_jid = info_query.get_to()
        name = to_jid.node
        account_type = to_jid.resource
        lang_class = self.lang.get_lang_class_from_node(info_query.get_node())
        # * root
        # |-* account_type1
        # | |-* account1
        # | |-* account2
        # |-* account_type2
        #   |-* account3
        #   |-* account4
        if name is not None: # account
            self.__logger.debug("Applying behavior on account " + name)
            result = account_handler(name, from_jid, account_type or "",
                                     lang_class)
        elif account_type is None: # root
            self.__logger.debug("Applying behavior on root node")
            result = root_handler(name, from_jid, "",
                                  lang_class) # TODO : account_type not needed
        else: # account type
            self.__logger.debug("Applying behavior on account type " +
                                account_type)
            result = account_type_handler(name, from_jid, account_type,
                                          lang_class)
        if send_result:
            self.send_stanzas(result)
        return result

    def apply_registered_behavior(self, handlers, stanza,
                                  apply_filter_func=None,
                                  apply_handle_func=None,
                                  send_result=True):
        """Execute handler if their filter method does not return None"""
        result = []
        lang_class = self.lang.get_lang_class_from_node(stanza.get_node())
        for handler_group in handlers:
            for handler in handler_group:
                try:
                    self.__logger.debug("Applying filter " + repr(handler))
                    if apply_filter_func is not None:
                        data = apply_filter_func(handler.filter, stanza, lang_class)
                    else:
                        data = handler.filter(stanza, lang_class)
                    if data is not None and data != False:
                        self.__logger.debug("Applying handler " + repr(handler))
                        if apply_handle_func is not None:
                            handler_result = apply_handle_func(handler.handle,
                                                               stanza,
                                                               lang_class,
                                                               data,
                                                               result)
                        else:
                            handler_result = handler.handle(stanza, lang_class,
                                                            data)
                        if handler_result is not None:
                            result += handler_result
                            break
                except Exception, e:
                    error_type, value, stack = sys.exc_info()
                    self.__logger.error("Error with handler " + str(handler) +
                                        " with " + str(stanza) + "\n%s\n%s"
                                        % (e, "".join(traceback.format_exception
                                                      (error_type, value, stack, 5))))
                    result += [Message(from_jid=stanza.get_to(),
                                       to_jid=stanza.get_from(),
                                       stanza_type="error",
                                       subject=lang_class.error_subject,
                                       body=lang_class.error_body % (e))]
        if send_result:
            self.send_stanzas(result)
        return result

    def handle_get_gateway(self, info_query):
        """Handle IQ-get "jabber:iq:gateway" requests.
        Return prompt and description.
        """
        self.__logger.debug("GET_GATEWAY")
        info_query = info_query.make_result_response()
        lang_class = self.lang.get_lang_class_from_node(info_query.get_node())
        query = info_query.new_query("jabber:iq:gateway")
        query.newTextChild(query.ns(), "desc", lang_class.get_gateway_desc)
        query.newTextChild(query.ns(), "prompt", lang_class.get_gateway_prompt)
        self.stream.send(info_query)
        return 1

    def handle_set_gateway(self, info_query):
        """Handle IQ-set "jabber:iq:gateway" requests.
        Return well formed JID from legacy ID.
        """
        self.__logger.debug("SET_GATEWAY")
        prompt_nodes = info_query.xpath_eval("jig:query/jig:prompt",
                                             {"jig" : "jabber:iq:gateway"})
        # TODO : Add malformed content error handling
        jid = prompt_nodes[0].content.replace("@", "%") + "@" + unicode(self.jid)
        info_query = info_query.make_result_response()
        query = info_query.new_query("jabber:iq:gateway")
        query.newTextChild(query.ns(), "jid", jid)
        # XEP-0100 - section 6: should be <jid> but PSI only work with <prompt>
        query.newTextChild(query.ns(), "prompt", jid)
        self.stream.send(info_query)
        return 1

    def disco_get_info(self, node, info_query):
        """
        Discovery get info handler
        """
        result = self.apply_registered_behavior(\
            self.disco_get_info_handlers,
            info_query,
            lambda filter_func, stanza, lang_class: \
                filter_func(stanza, lang_class, node),
            lambda handle_func, stanza, lang_class, data, result: \
                handle_func(stanza, lang_class, node, result, data),
            send_result=False)
        if len(result) > 0:
            return result[0]
        else:
            return None

    def disco_get_items(self, node, info_query):
        """
        Discovery get nested nodes handler
        """
        result = self.apply_registered_behavior(\
            self.disco_get_items_handlers,
            info_query,
            lambda filter_func, stanza, lang_class: \
                filter_func(stanza, lang_class, node),
            lambda handle_func, stanza, lang_class, data, result: \
                handle_func(stanza, lang_class, node, result, data),
            send_result=False)
        if len(result) > 0:
            return result[0]
        else:
            return None

    def handle_get_version(self, info_query):
        """Get Version handler
        """
        self.__logger.debug("GET_VERSION")
        info_query = info_query.make_result_response()
        query = info_query.new_query("jabber:iq:version")
        query.newTextChild(query.ns(), "name", self.name)
        query.newTextChild(query.ns(), "version", self.version)
        self.stream.send(info_query)
        return 1

    def handle_get_register(self, info_query):
        """Send back register form to user
        see node structure in disco_get_items()
        """
        self.__logger.debug("GET_REGISTER")
        self.apply_behavior(\
            info_query,
            lambda name, from_jid, account_type, lang_class: \
                self.account_manager.account_get_register(info_query,
                                                          name,
                                                          from_jid,
                                                          account_type,
                                                          lang_class),
            lambda name, from_jid, account_type, lang_class: \
                self.account_manager.account_type_get_register(info_query,
                                                               account_type,
                                                               lang_class),
            lambda name, from_jid, account_type, lang_class: \
                self.account_manager.root_get_register(info_query,
                                                       lang_class),
            send_result=True)

    def handle_set_register(self, info_query):
        """Handle user registration response
        """
        self.__logger.debug("SET_REGISTER")
        lang_class = \
            self.lang.get_lang_class_from_node(info_query.get_node())
        from_jid = info_query.get_from()
        remove = info_query.xpath_eval("r:query/r:remove",
                                       {"r" : "jabber:iq:register"})
        if remove:
            result = self.account_manager.remove_all_accounts(from_jid.bare())
            self.send_stanzas(result)
            return 1

        x_node = info_query.xpath_eval("jir:query/jxd:x",
                                       {"jir" : "jabber:iq:register",
                                        "jxd" : "jabber:x:data"})[0]
        x_data = Form(x_node)
        if not "name" in x_data or x_data["name"].value == "":
            iq_error = info_query.make_error_response("not-acceptable")
            text = iq_error.get_error().xmlnode.newTextChild(\
                None,
                "text",
                lang_class.mandatory_field % ("name"))
            text.setNs(text.newNs(error.STANZA_ERROR_NS, None))
            self.stream.send(iq_error)
            return
        return self.apply_registered_behavior(\
            self.set_register_handlers,
            info_query,
            apply_handle_func=lambda handle_func, stanza, lang_class, data, result: \
                handle_func(stanza, lang_class, data, x_data))

    def handle_presence_available(self, stanza):
        """Handle presence availability
        if presence sent to the component ('if not name'), presence is sent to
        all accounts for current user. Otherwise, send presence from current account.
        """
        result = self.apply_registered_behavior(self.presence_available_handlers,
                                                stanza)
        return result


    def handle_presence_unavailable(self, stanza):
        """Handle presence unavailability
        """
        self.__logger.debug("PRESENCE_UNAVAILABLE")
        result = self.apply_registered_behavior(self.presence_unavailable_handlers,
                                                stanza)
        return result

    def handle_presence_subscribe(self, stanza):
        """Handle subscribe presence from user
        """
        self.__logger.debug("PRESENCE_SUBSCRIBE")
        result = self.apply_registered_behavior(self.presence_subscribe_handlers,
                                                stanza)
        return result

    def handle_presence_subscribed(self, stanza):
        """Handle subscribed presence from user
        """
        self.__logger.debug("PRESENCE_SUBSCRIBED")
        return 1

    def handle_presence_unsubscribe(self, stanza):
        """Handle unsubscribe presence from user
        """
        self.__logger.debug("PRESENCE_UNSUBSCRIBE")
        result = self.apply_registered_behavior(self.presence_unsubscribe_handlers,
                                                stanza)
        return result

    def handle_presence_unsubscribed(self, stanza):
        """Handle unsubscribed presence from user
        """
        self.__logger.debug("PRESENCE_UNSUBSCRIBED")
        presence = Presence(from_jid=stanza.get_to(),
                            to_jid=stanza.get_from(),
                            stanza_type="unavailable")
        self.stream.send(presence)
        return 1

    def handle_message(self, message):
        """Handle new message
        Handle password response message
        """
        self.__logger.debug("MESSAGE: " + message.get_body())
        self.apply_registered_behavior(self.msg_handlers, message)
        return 1

    def handle_command(self, info_query):
        """
        Handle command IQ
        """
        self.__logger.debug("COMMAND")

        _command = info_query.xpath_eval("c:command",
                                         {"c": command.COMMAND_NS})[0]
        command_node = _command.prop("node")
        action = _command.prop("action")
        if action is None:
            action = "execute"
        try:
            result = command.command_manager.apply_command_action(info_query,
                                                                  command_node,
                                                                  action)
            self.send_stanzas(result)
        except:
            type, value, stack = sys.exc_info()
            self.__logger.error("Error in command " + str(command_node) +
                                " with " + str(info_query) + "\n%s"
                                % ("".join(traceback.format_exception
                                           (type, value, stack, 5))))
            print("Error in command " + str(command_node) +
                                " with " + str(info_query) + "\n%s"
                                % ("".join(traceback.format_exception
                                           (type, value, stack, 5))))
        return 1
        
    ###########################################################################
    # Utils
    ###########################################################################
    def send_error(self, _account, exception):
        """ """
        self.send_stanzas(self.account_manager.send_error_from_account(_account, exception))
        type, value, stack = sys.exc_info()
        self.__logger.debug("Error: %s\n%s"
                            % (exception, "".join(traceback.format_exception
                                                  (type, value, stack, 5))))

    ###########################################################################
    # Virtual methods
    ###########################################################################
    def handle_tick(self):
        """Virtual method
        Called regularly
        """
        raise NotImplementedError


class AccountManager(object):
    """Implement component account behavior"""

    def __init__(self, component):
        """AccountManager constructor"""
        self.__logger = logging.getLogger("jcl.jabber.JCLComponent")
        self.regexp_type = re.compile("(.*)Account$")
        self._account_classes = None
        self.account_classes = (Account,)
        self.component = component
        self.account_types = []

    def _get_account_classes(self):
        """account_classes getter"""
        return self._account_classes

    def _set_account_classes(self, account_classes):
        """account_classes setter"""
        self._account_classes = account_classes
        self.has_multiple_account_type = (len(self._account_classes) > 1)
        self.account_types = []
        for account_class in account_classes:
            match = self.regexp_type.search(account_class.__name__)
            if match is not None:
                account_type = match.group(1)
                self.account_types.append(account_type)
            else:
                self.__logger.error(account_class.__name__ +
                                    " name not well formed")
                self.account_types.append("")

    account_classes = property(_get_account_classes, _set_account_classes)

    ###### get_register handlers ######
    def account_get_register(self, info_query,
                             name,
                             from_jid,
                             account_type,
                             lang_class):
        """Handle get_register on an account.
        Return a preinitialized form"""
        info_query = info_query.make_result_response()
        account_class = self.get_account_class(account_type)
        model.db_connect()
        _account = account.get_account(from_jid.bare(), name, account_class)
        if _account is not None:
            query = info_query.new_query("jabber:iq:register")
            model.db_disconnect()
            self.generate_registration_form_init(lang_class,
                                                 _account).as_xml(query)
        else:
            model.db_disconnect()
        return [info_query]

    def _account_type_get_register(self, info_query, account_class, lang_class):
        """Handle get_register for given account_class"""
        info_query = info_query.make_result_response()
        query = info_query.new_query("jabber:iq:register")
        from_jid = info_query.get_from()
        bare_from_jid = unicode(from_jid.bare())
        self.generate_registration_form(lang_class,
                                        account_class,
                                        bare_from_jid).as_xml(query)
        return [info_query]

    def account_type_get_register(self, info_query, account_type, lang_class):
        """Handle get_register on an account_type node"""
        return self._account_type_get_register(\
            info_query,
            self.get_account_class(account_type),
            lang_class)

    def root_get_register(self, info_query, lang_class):
        """Handle get_register on root node"""
        if not self.has_multiple_account_type:
            return self._account_type_get_register(info_query,
                                                   self.account_classes[0],
                                                   lang_class)

    ###### set_register handlers ######
    def remove_all_accounts(self, user_jid):
        """Unsubscribe all accounts associated to 'user_jid' then delete
        those accounts from the DataBase"""
        model.db_connect()
        result = []
        for _account in account.get_accounts(user_jid):
            self.__logger.debug("Deleting " + _account.name
                                + " for " + unicode(user_jid))
            # get_jid
            result.append(Presence(from_jid=_account.jid,
                                   to_jid=user_jid,
                                   stanza_type="unsubscribe"))
            result.append(Presence(from_jid=_account.jid,
                                   to_jid=user_jid,
                                   stanza_type="unsubscribed"))
            _account.destroySelf()
        result.append(Presence(from_jid=self.component.jid,
                               to_jid=user_jid,
                               stanza_type="unsubscribe"))
        result.append(Presence(from_jid=self.component.jid,
                               to_jid=user_jid,
                               stanza_type="unsubscribed"))
        model.db_disconnect()
        return result

    def remove_account_from_name(self, user_jid, name):
        _account = account.get_account(user_jid, name)
        if _account is not None:
            return self.remove_account(_account, user_jid)
        else:
            return []

    def remove_account(self, _account, user_jid):
        self.__logger.debug("Deleting account: " + str(_account))
        result = []
        model.db_connect()
        result.append(Presence(from_jid=_account.jid,
                               to_jid=user_jid,
                               stanza_type="unsubscribe"))
        result.append(Presence(from_jid=_account.jid,
                               to_jid=user_jid,
                               stanza_type="unsubscribed"))
        _account.destroySelf()
        model.db_disconnect()
        return result

    def populate_account(self, _account, lang_class, x_data,
                         new_account, first_account, from_jid=None):
        """Populate given account"""
        if from_jid is None:
            from_jid = _account.user_jid
        field = None
        result = []
        model.db_connect()
        for (field, field_type, field_options, field_post_func,
             field_default_func) in _account.get_register_fields():
            if field is not None:
                if field in x_data:
                    value = x_data[field].value
                else:
                    value = None
                setattr(_account, field,
                        field_post_func(value, field_default_func,
                                        from_jid.bare()))

        if first_account:
            # component subscribe user presence when registering the first
            # account
            result.append(Presence(from_jid=self.component.jid,
                                   to_jid=from_jid,
                                   stanza_type="subscribe"))
        if new_account:
            # subscribe to user presence if this is a new account
            result.append(Message(\
                    from_jid=self.component.jid,
                    to_jid=from_jid,
                    subject=_account.get_new_message_subject(lang_class),
                    body=_account.get_new_message_body(lang_class)))
            result.append(Presence(from_jid=_account.jid,
                                   to_jid=from_jid,
                                   stanza_type="subscribe"))
        else:
            result.append(Message(\
                    from_jid=self.component.jid,
                    to_jid=from_jid,
                    subject=_account.get_update_message_subject(lang_class),
                    body=_account.get_update_message_body(lang_class)))
        model.db_disconnect()
        return result

    def update_account(self,
                       account_name,
                       from_jid,
                       lang_class,
                       x_data):
        """Update account"""
        self.__logger.debug("Updating account " + account_name)
        bare_from_jid = from_jid.bare()
        _account = account.get_account(bare_from_jid,
                                       account_name)
        if _account is not None:
            return self.populate_account(_account, lang_class,
                                         x_data,
                                         new_account=False,
                                         first_account=False,
                                         from_jid=from_jid)
        else:
            self.__logger.error("Account " + account_name +
                                " was not found, cannot update it")
            return []

    def create_account(self,
                       account_name,
                       from_jid,
                       account_class,
                       lang_class,
                       x_data):
        """Create new account from account_class"""
        bare_from_jid = from_jid.bare()
        first_account = (account.get_accounts_count(bare_from_jid) == 0)
        model.db_connect()
        _account = account_class(user_jid=unicode(bare_from_jid),
                                 name=account_name,
                                 jid=self.get_account_jid(account_name))
        model.db_disconnect()
        try:
            return self.populate_account(_account, lang_class, x_data,
                                         new_account=True,
                                         first_account=first_account,
                                         from_jid=from_jid)
        except FieldError, field_error:
            model.db_connect()
            _account.destroySelf()
            model.db_disconnect()
            raise field_error

    def create_account_from_type(self,
                                 account_name,
                                 from_jid,
                                 account_type,
                                 lang_class,
                                 x_data):
        """Create new account from its type name"""
        account_class = self.get_account_class(account_type)
        return self.create_account(account_name,
                                   from_jid,
                                   account_class,
                                   lang_class,
                                   x_data)

    def create_default_account(self,
                               account_name,
                               bare_from_jid,
                               lang_class,
                               x_data):
        """Create new account when managing only one account type"""
        if not self.has_multiple_account_type:
            return self.create_account(account_name, bare_from_jid,
                                       self.account_classes[0],
                                       lang_class, x_data)
        else:
            return []

    ###### presence generic handlers ######
    def send_presence_all(self, presence):
        """Send presence to all account. Optimized to use only one sql
        request"""
        current_user_jid = None
        result = []
        model.db_connect()
        # Explicit reference to account table (clauseTables) to use
        # "user_jid" column with Account subclasses
        for _account in \
                Account.select(clauseTables=["account"],
                               orderBy="user_jid"):
            if current_user_jid != _account.user_jid:
                current_user_jid = _account.user_jid
                result.extend(self.send_presence(self.component.jid,
                                                 _account.user_jid,
                                                 presence))
            result.extend(getattr(self, "send_presence_" +
                                  presence)(_account))
        model.db_disconnect()
        return result


    def probe_all_accounts_presence(self):
        """Send presence probe to all registered accounts"""
        return self.send_presence_all("probe")

    ###### Utils methods ######
    def list_accounts(self, bare_from_jid, account_class=None,
                      account_type=""):
        """List accounts in disco_items for given _account_class and user jid"""
        if account_class is None:
            account_class = self.account_classes[0]
        if account_type is not None and account_type != "":
            resource = "/" + account_type
            account_type = account_type + "/"
        else:
            resource = ""
        model.db_connect()
        accounts = account.get_accounts(bare_from_jid, account_class)
        if accounts:
            for _account in accounts:
                yield (_account, resource, account_type)
        model.db_disconnect()

    def list_account_types(self, lang_class):
        """List account supported types"""
        for account_type in self.account_types:
            type_label_attr = "type_" + account_type.lower() + "_name"
            if hasattr(lang_class, type_label_attr):
                type_label = getattr(lang_class, type_label_attr)
            else:
                type_label = account_type
            yield (account_type, type_label)
        
    def get_account_class(self, account_type=None,
                          account_class_name=None):
        """Return account class definition from declared classes in
        account_classes from its class name"""
        if account_type is not None:
            account_class_name = account_type + "Account"
        elif account_class_name is None:
            self.__logger.error("account_type and account_class_name are None")
            return None
        self.__logger.debug("Looking for " + account_class_name)
        for _account_class in self.account_classes:
            if _account_class.__name__.lower() == account_class_name.lower():
                self.__logger.debug(account_class_name + " found")
                return _account_class
        self.__logger.debug(account_class_name + " not found")
        return None

    def generate_registration_form(self, lang_class, _account_class, bare_from_jid):
        """
        Return register form based on language and account class
        """
        reg_form = Form(title=lang_class.register_title,
                        instructions=lang_class.register_instructions)
        # "name" field is mandatory
        reg_form.add_field(field_type="text-single",
                           label=lang_class.account_name,
                           name="name",
                           required=True)

        for (field_name,
             field_type,
             field_options,
             post_func,
             default_func) in \
                _account_class.get_register_fields():
            if field_name is None:
                # TODO : Add page when empty tuple given
                pass

            else:
                lang_label_attr = "field_" + field_name
                if hasattr(lang_class, lang_label_attr):
                    label = getattr(lang_class, lang_label_attr)
                else:
                    label = field_name
                self.__logger.debug("Adding field " + field_name + " to registration form")
                field = reg_form.add_field(field_type=field_type,
                                           label=label,
                                           name=field_name,
                                           value=default_func(bare_from_jid))
                if field_options is not None:
                    for option_value in field_options:
                        lang_label_attr = "field_" + field_name + "_" + option_value
                        if hasattr(lang_class, lang_label_attr):
                            label = getattr(lang_class, lang_label_attr)
                        else:
                            label = option_value
                        field.add_option(label=label,
                                         values=[option_value])
                try:
                    post_func(None, default_func, bare_from_jid)
                except:
                    self.__logger.debug("Setting field " + field_name + " required")
                    field.required = True
        return reg_form

    def generate_registration_form_init(self, lang_class, _account):
        """
        Return register form for an existing account (update)
        """
        reg_form = self.generate_registration_form(lang_class, _account.__class__,
                                                   _account.user_jid)
        reg_form["name"].value = _account.name
        reg_form["name"].type = "hidden"
        for field in reg_form.fields:
            if hasattr(_account, field.name):
                field.value = getattr(_account, field.name)
        return reg_form

    def get_account_jid(self, name):
        """Compose account jid from account name"""
        return name + u"@" + unicode(self.component.jid)

    def send_presence_probe(self, _account):
        """Send presence probe to account's user"""
        return [Presence(from_jid=_account.jid,
                         to_jid=_account.user_jid,
                         stanza_type="probe")]

    def send_presence_unavailable(self, _account):
        """Send unavailable presence to account's user"""
        model.db_connect()
        _account.status = account.OFFLINE
        result = [Presence(from_jid=_account.jid,
                           to_jid=_account.user_jid,
                           stanza_type="unavailable")]
        model.db_disconnect()
        return result

    def send_root_presence(self, to_jid, presence_type,
                            show=None, status=None):
        result = self.send_presence(self.component.jid, to_jid,
                                    presence_type, show=show,
                                    status=status)
        result.extend(self.send_root_presence_legacy(to_jid,
                                                     presence_type,
                                                     show=show,
                                                     status=status))
        return result

    def send_presence(self, from_jid, to_jid, presence_type, status=None, show=None):
        """Send presence stanza"""
        return [Presence(from_jid=from_jid,
                         to_jid=to_jid,
                         status=status,
                         show=show,
                         stanza_type=presence_type)]

    def send_presence_available(self, _account, show, lang_class):
        """Send available presence to account's user and ask for password
        if necessary"""
        result = []
        model.db_connect()
        _account.default_lang_class = lang_class
        old_status = _account.status
        if show is None:
            _account.status = account.ONLINE
        else:
            _account.status = show
        result.append(Presence(from_jid=_account.jid,
                               to_jid=_account.user_jid,
                               status=_account.status_msg,
                               show=show,
                               stanza_type="available"))
        if hasattr(_account, 'store_password') \
            and hasattr(_account, 'password') \
            and _account.store_password == False \
            and old_status == account.OFFLINE \
            and _account.password == None :
            result.extend(self.ask_password(_account, lang_class))
        model.db_disconnect()
        return result

    def send_root_presence_legacy(self, to_jid, presence_type,
                                   status=None, show=None):
        """Send presence from legacy JID"""
        result = []
        for legacy_jid in account.get_legacy_jids(unicode(to_jid.bare())):
            result.append(Presence(from_jid=legacy_jid.jid,
                                   to_jid=to_jid,
                                   show=show,
                                   status=status,
                                   stanza_type=presence_type))
        return result

    def ask_password(self, _account, lang_class):
        """Send a Jabber message to ask for account password
        """
        result = []
        if hasattr(_account, 'waiting_password_reply') \
            and not _account.waiting_password_reply \
            and _account.status != account.OFFLINE:
            _account.waiting_password_reply = True
            result.append(Message(from_jid=_account.jid,
                                  to_jid=_account.user_jid,
                                  subject=u"[PASSWORD] " + \
                                      lang_class.ask_password_subject,
                                  body=lang_class.ask_password_body % \
                                      (_account.name)))
        return result

    def set_password(self, _account, from_jid, password, lang_class):
        """
        Set password to given account
        """
        model.db_connect()
        _account.password = password
        _account.waiting_password_reply = False
        result = [Message(from_jid=_account.jid,
                          to_jid=from_jid,
                          subject=lang_class.password_saved_for_session,
                          body=lang_class.password_saved_for_session)]
        model.db_disconnect()
        return result

    def send_error_from_account(self, _account, exception):
        """Send an error message only one time until _account.in_error
        has been reset to False"""
        result = []
        if _account.in_error == False:
            _account.in_error = True
            result.append(Message(from_jid=_account.jid,
                                  to_jid=_account.user_jid,
                                  stanza_type="error",
                                  subject=_account.default_lang_class.error_subject,
                                  body=_account.default_lang_class.error_body \
                                      % (exception)))
        return result
