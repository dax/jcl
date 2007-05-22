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

"""JCL base component
"""

__revision__ = "$Id: component.py,v 1.3 2005/09/18 20:24:07 dax Exp $"

import sys

import threading
import time
import logging
import signal
import re
import traceback

from Queue import Queue

from sqlobject.inheritance import InheritableSQLObject
from sqlobject.sqlbuilder import AND
from sqlobject.dbconnection import connectionForURI

import pyxmpp.error as error
from pyxmpp.jid import JID
from pyxmpp.jabberd.component import Component
from pyxmpp.jabber.disco import DiscoInfo, DiscoItems, DiscoItem, DiscoIdentity
from pyxmpp.message import Message
from pyxmpp.presence import Presence
from pyxmpp.jabber.dataforms import Form, Field, Option

import jcl
from jcl.jabber.error import FieldError
from jcl.model import account
from jcl.model.account import Account
from jcl.lang import Lang

VERSION = "0.1"

###############################################################################
# JCL implementation
###############################################################################
class JCLComponent(Component, object):
    """Implement default JCL component behavior:
    - Jabber register process (add, delete, update accounts)
    - Jabber presence handling
    - passwork request at login
    """

    timeout = 1

    def __init__(self,
                 jid,
                 secret,
                 server,
                 port,
                 db_connection_str,
                 disco_category = "gateway",
                 disco_type = "headline",
                 lang = Lang()):
        Component.__init__(self, \
                           JID(jid), \
                           secret, \
                           server, \
                           port, \
                           disco_category, \
                           disco_type)
        # default values
        self.name = lang.get_default_lang_class().component_name
        self.spool_dir = "."
        self.db_connection_str = db_connection_str
        self.version = VERSION
        self.time_unit = 60
        self.queue = Queue(100)
        self.account_manager = AccountManager(self)
        self.msg_handlers = []

        self.__logger = logging.getLogger("jcl.jabber.JCLComponent")
        self.lang = lang
        self.running = False
        self.wait_event = threading.Event()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def run(self):
        """Main loop
        Connect to Jabber server
        Start timer thread
        Call Component main loop
        Clean up when shutting down JCLcomponent
        """
        self.spool_dir += "/" + unicode(self.jid)
        self.running = True
        self.connect()
        timer_thread = threading.Thread(target = self.time_handler, \
                                        name = "TimerThread")
        timer_thread.start()
        try:
            while (self.running and self.stream \
                   and not self.stream.eof \
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

    #################
    # SQlite connections are not multi-threaded
    # Utils workaround methods
    #################
    def db_connect(self):
        """Create a new connection to the DataBase (SQLObject use connection
        pool) associated to the current thread"""
        account.hub.threadConnection = \
                     connectionForURI(self.db_connection_str)
#        account.hub.threadConnection.debug = True

    def db_disconnect(self):
        """Delete connection associated to the current thread"""
        del account.hub.threadConnection


    ###########################################################################
    # Handlers
    ###########################################################################
    def time_handler(self):
        """Timer thread handler
        """
        self.__logger.info("Timer thread started...")
        try:
            while (self.running and self.stream \
                   and not self.stream.eof \
                   and self.stream.socket is not None):
                self.handle_tick()
                self.__logger.debug("Resetting alarm signal")
                ##time.sleep(self.time_unit)
                self.wait_event.wait(self.time_unit)
        except Exception, exception:
            self.queue.put(exception)
        self.__logger.info("Timer thread terminated...")

    def authenticated(self):
        """Override authenticated Component event handler
        Register event handlers
        Probe for every accounts registered
        """
        self.__logger.debug("AUTHENTICATED")
        Component.authenticated(self)
        self.stream.set_iq_get_handler("query", "jabber:iq:version", \
                                       self.handle_get_version)
        self.stream.set_iq_get_handler("query", "jabber:iq:register", \
                                       self.handle_get_register)
        self.stream.set_iq_set_handler("query", "jabber:iq:register", \
                                       self.handle_set_register)

        self.stream.set_presence_handler("available", \
                                         self.handle_presence_available)

        self.stream.set_presence_handler("probe", \
                                         self.handle_presence_available)

        self.stream.set_presence_handler("unavailable", \
                                         self.handle_presence_unavailable)

        self.stream.set_presence_handler("unsubscribe", \
                                         self.handle_presence_unsubscribe)
        self.stream.set_presence_handler("unsubscribed", \
                                         self.handle_presence_unsubscribed)
        self.stream.set_presence_handler("subscribe", \
                                         self.handle_presence_subscribe)
        self.stream.set_presence_handler("subscribed", \
                                         self.handle_presence_subscribed)

        self.stream.set_message_handler("normal", \
                                        self.handle_message)
        self.send_stanzas(self.account_manager.probe_all_accounts_presence())

        self.msg_handlers += [PasswordMessageHandler()]

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

    def apply_behavior(self, info_query, \
                       account_handler, \
                       account_type_handler, \
                       root_handler, \
                       send_result = False):
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
            result = account_handler(name, from_jid, account_type or "", lang_class)
        elif account_type is None: # root
            self.__logger.debug("Applying behavior on root node")
            result = root_handler(name, from_jid, "", lang_class) # TODO : account_type not needed
        else: # account type
            self.__logger.debug("Applying behavior on account type " + account_type)
            result = account_type_handler(name, from_jid, account_type, lang_class)
        if send_result:
            self.send_stanzas(result)
        return result
        
    def disco_get_info(self, node, info_query):
        """Discovery get info handler
        """
        return self.apply_behavior(info_query, \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_disco_get_info(), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_type_disco_get_info(), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.root_disco_get_info(self.name, \
                                                                            self.disco_identity.category, \
                                                                            self.disco_identity.type))

    def disco_get_items(self, node, info_query):
        """Discovery get nested nodes handler
        """
        return self.apply_behavior(info_query, \
                                   lambda name, from_jid, account_type, lang_class: \
                                   DiscoItems(), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_type_disco_get_items(from_jid, account_type), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.root_disco_get_items(from_jid, lang_class))

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
        self.apply_behavior(info_query, \
                            lambda name, from_jid, account_type, lang_class: \
                            self.account_manager.account_get_register(info_query, \
                                                                      name, \
                                                                      from_jid, \
                                                                      account_type, \
                                                                      lang_class), \
                            lambda name, from_jid, account_type, lang_class: \
                            self.account_manager.account_type_get_register(info_query, \
                                                                           account_type, \
                                                                           lang_class), \
                            lambda name, from_jid, account_type, lang_class: \
                            self.account_manager.root_get_register(info_query, \
                                                                   lang_class), \
                            send_result = True)

    def handle_set_register(self, info_query):
        """Handle user registration response
        """
        self.__logger.debug("SET_REGISTER")
        lang_class = \
                   self.lang.get_lang_class_from_node(info_query.get_node())
        from_jid = info_query.get_from()
        base_from_jid = unicode(from_jid.bare())
        remove = info_query.xpath_eval("r:query/r:remove", \
                                        {"r" : "jabber:iq:register"})
        if remove:
            result = self.account_manager.remove_all_accounts(from_jid.bare())
            self.send_stanzas(result)
            return 1

        x_node = info_query.xpath_eval("jir:query/jxd:x", \
                                       {"jir" : "jabber:iq:register", \
                                        "jxd" : "jabber:x:data"})[0]

        x_data = Form(x_node)
        if not "name" in x_data or x_data["name"].value == "":
            iq_error = info_query.make_error_response("not-acceptable")
            text = iq_error.get_error().xmlnode.newTextChild(None, \
                "text", \
                lang_class.mandatory_field % ("name"))
            text.setNs(text.newNs(error.STANZA_ERROR_NS, None))
            self.stream.send(iq_error)
            return
        account_name = x_data["name"].value
        return self.apply_behavior(info_query, \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_set_register(name, \
                                                                             from_jid, \
                                                                             lang_class, \
                                                                             x_data, \
                                                                             info_query), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_type_set_register(account_name, \
                                                                                  from_jid, \
                                                                                  account_type, \
                                                                                  lang_class, \
                                                                                  x_data, \
                                                                                  info_query), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.root_set_register(account_name, \
                                                                          from_jid, \
                                                                          lang_class, \
                                                                          x_data, \
                                                                          info_query), \
                                   send_result = True)

    def handle_presence_available(self, stanza):
        """Handle presence availability
        if presence sent to the component ('if not name'), presence is sent to
        all accounts for current user. Otherwise, send presence from current account.

        """
        return self.apply_behavior(stanza, \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_handle_presence_available(name, \
                                                                                          from_jid, \
                                                                                          lang_class, \
                                                                                          stanza.get_show()), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   [], \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.root_handle_presence_available(from_jid, \
                                                                                       lang_class, \
                                                                                       stanza.get_show()), \
                                   send_result = True)
                                   

    def handle_presence_unavailable(self, stanza):
        """Handle presence unavailability
        """
        self.__logger.debug("PRESENCE_UNAVAILABLE")
        return self.apply_behavior(stanza, \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_handle_presence_unavailable(name, \
                                                                                            from_jid), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   [], \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.root_handle_presence_unavailable(from_jid), \
                                   send_result = True)

    def handle_presence_subscribe(self, stanza):
        """Handle subscribe presence from user
        """
        self.__logger.debug("PRESENCE_SUBSCRIBE")
        return self.apply_behavior(stanza, \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_handle_presence_subscribe(name, \
                                                                                          from_jid, \
                                                                                          stanza), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   [], \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.root_handle_presence_subscribe(from_jid, \
                                                                                       stanza), \
                                   send_result = True)

    def handle_presence_subscribed(self, stanza):
        """Handle subscribed presence from user
        """
        self.__logger.debug("PRESENCE_SUBSCRIBED")
        return 1

    def handle_presence_unsubscribe(self, stanza):
        """Handle unsubscribe presence from user
        """
        self.__logger.debug("PRESENCE_UNSUBSCRIBE")
        return self.apply_behavior(stanza, \
                                   lambda name, from_jid, account_type, lang_class: \
                                   self.account_manager.account_handle_presence_unsubscribe(name, \
                                                                                            from_jid), \
                                   lambda name, from_jid, account_type, lang_class: \
                                   [], \
                                   lambda name, from_jid, account_type, lang_class: \
                                   [], \
                                   send_result = True)

    def handle_presence_unsubscribed(self, stanza):
        """Handle unsubscribed presence from user
        """
        self.__logger.debug("PRESENCE_UNSUBSCRIBED")
        presence = Presence(from_jid = stanza.get_to(), \
                            to_jid = stanza.get_from(), \
                            stanza_type = "unavailable")
        self.stream.send(presence)
        return 1

    def handle_message(self, message):
        """Handle new message
        Handle password response message
        """
        self.__logger.debug("MESSAGE: " + message.get_body())
        result = []
        self.db_connect()
        for msg_handler in self.msg_handlers:
            accounts = msg_handler.filter(message)
            if accounts is not None:
                result += msg_handler.handle(message, self.lang, accounts)
        self.db_disconnect()
        self.send_stanzas(result)
        return 1

    ###########################################################################
    # Utils
    ###########################################################################
    def send_error(self, _account, exception):
        """ """
        self.send_stanzas(self.account_manager.send_error(_account, exception))
        type, value, stack = sys.exc_info()
        # TODO : not checking email here
        self.__logger.debug("Error: %s\n%s" \
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
        self.account_classes = (Account,)
        self.component = component

    def _get_account_classes(self):
        """account_classes getter"""
        return self._account_classes

    def _set_account_classes(self, account_classes):
        """account_classes setter"""
        self._account_classes = account_classes
        self.has_multiple_account_type = (len(self._account_classes) > 1)
        
    account_classes = property(_get_account_classes, _set_account_classes)
    
    ###### disco_get_info handlers ######
    def account_disco_get_info(self):
        """Implement discovery get_info on an account node"""
        self.__logger.debug("account_disco_get_info")
        disco_info = DiscoInfo()
        disco_info.add_feature("jabber:iq:register")
        return disco_info

    def account_type_disco_get_info(self):
        """Implement discovery get_info on an account type node"""
        self.__logger.debug("account_type_disco_get_info")
        return self.account_disco_get_info()

    def root_disco_get_info(self, name, category, type):
        """Implement discovery get_info on main component JID"""
        self.__logger.debug("root_disco_get_info")
        disco_info = DiscoInfo()
        disco_info.add_feature("jabber:iq:version")
        if not self.has_multiple_account_type:
            disco_info.add_feature("jabber:iq:register")
        # TODO: name is always None
        DiscoIdentity(disco_info, name, \
                      category, \
                      type)
        return disco_info

    ###### disco_get_items handlers ######
    def account_type_disco_get_items(self, from_jid, account_type):
        """Discovery get_items on an account type node"""
        self.__logger.debug("Listing account for " + account_type)
        disco_items = DiscoItems()
        account_class = self._get_account_class(account_type + "Account")
        if account_class is not None:
            self._list_accounts(disco_items, \
                                account_class, \
                                from_jid.bare(), \
                                account_type = account_type)
        else:
            self.__logger.error("Error: " + account_class.__name__ \
                                + " class not in account_classes")
        return disco_items
        
    def root_disco_get_items(self, from_jid, lang_class):
        """Discovery get_items on root node"""
        disco_items = DiscoItems()
        regexp_type = re.compile("(.*)Account$")
        if self.has_multiple_account_type: # list accounts with only one type declared
            def _list_account_types(disco_items, account_class, bare_from_jid, account_type):
                type_label_attr = "type_" + account_type.lower() + "_name"
                if hasattr(lang_class, type_label_attr):
                    type_label = getattr(lang_class, type_label_attr)
                else:
                    type_label = account_type
                return DiscoItem(disco_items, \
                                  JID(unicode(self.component.jid) + "/" + account_type), \
                                  account_type, \
                                  type_label)
            list_func = _list_account_types
                        
        else:
            list_func = self._list_accounts

        for account_class in self.account_classes:
            match = regexp_type.search(account_class.__name__)
            if match is not None:
                account_type = match.group(1)
                list_func(disco_items, account_class, \
                          from_jid.bare(), account_type)
            else:
                self.__logger.error(account_class.__name__ + \
                                    " name not well formed")
        return disco_items

    ###### get_register handlers ######
    def account_get_register(self, info_query, \
                             name, \
                             from_jid, \
                             account_type, \
                             lang_class):
        """Handle get_register on an account.
        Return a preinitialized form"""
        info_query = info_query.make_result_response()
        account_class = self._get_account_class(account_type + "Account")
        self.db_connect()
        accounts = account_class.select(\
                AND(account_class.q.name == name, \
                    account_class.q.user_jid == unicode(from_jid.bare())))
        if accounts is not None:
            query = info_query.new_query("jabber:iq:register")
            self.get_reg_form_init(lang_class, \
                                   accounts[0]).as_xml(query)
        self.db_disconnect()
        return [info_query]

    def _account_type_get_register(self, info_query, account_class, lang_class):
        """Handle get_register for given account_class"""
        info_query = info_query.make_result_response()
        query = info_query.new_query("jabber:iq:register")
        self.get_reg_form(lang_class, \
                          account_class).as_xml(query)
        return [info_query]

    def account_type_get_register(self, info_query, account_type, lang_class):
        """Handle get_register on an account_type node"""
        return self._account_type_get_register(info_query, \
                                               self._get_account_class(account_type + "Account"), \
                                               lang_class)
                                           
    def root_get_register(self, info_query, lang_class):
        """Handle get_register on root node"""
        if not self.has_multiple_account_type:
            return self._account_type_get_register(info_query, \
                                                   self.account_classes[0], \
                                                   lang_class)

    ###### set_register handlers ######
    def remove_all_accounts(self, user_jid):
        """Unsubscribe all accounts associated to 'user_jid' then delete
        those accounts from the DataBase"""
        self.db_connect()
        result = []
        for _account in Account.select(Account.q.user_jid == unicode(user_jid)):
            self.__logger.debug("Deleting " + _account.name \
                                + " for " + unicode(user_jid))
            # get_jid
            result.append(Presence(from_jid = _account.jid, \
                                   to_jid = user_jid, \
                                   stanza_type = "unsubscribe"))
            result.append(Presence(from_jid = _account.jid, \
                                   to_jid = user_jid, \
                                   stanza_type = "unsubscribed"))
            _account.destroySelf()
        result.append(Presence(from_jid = self.component.jid, to_jid = user_jid, \
                               stanza_type = "unsubscribe"))
        result.append(Presence(from_jid = self.component.jid, to_jid = user_jid, \
                               stanza_type = "unsubscribed"))
        self.db_disconnect()
        return result

    def _populate_account(self, _account, lang_class, x_data, \
                          info_query, new_account, first_account):
        """Populate given account"""
        field = None
        result = []
        self.db_connect()
        try:
            for (field, field_type, field_options, field_post_func, \
                 field_default_func) in _account.get_register_fields():
                if field is not None:
                    if field in x_data:
                        value = x_data[field].value
                    else:
                        value = None
                    setattr(_account, field, \
                            field_post_func(value, field_default_func))
        except FieldError, exception:
            _account.destroySelf()
            type, value, stack = sys.exc_info()
            self.__logger.error("Error while populating account: %s\n%s" % \
                                (exception, "".join(traceback.format_exception
                                                    (type, value, stack, 5))))
            iq_error = info_query.make_error_response("not-acceptable")
            text = iq_error.get_error().xmlnode.newTextChild(None, \
                                "text", \
                                lang_class.mandatory_field % (field))
            text.setNs(text.newNs(error.STANZA_ERROR_NS, None))
            result.append(iq_error)
            self.db_disconnect()
            return result
        result.append(info_query.make_result_response())

        # TODO : _account.user_jid or from_jid
        if first_account:
            result.append(Presence(from_jid = self.component.jid, \
                                   to_jid = _account.user_jid, \
                                   stanza_type = "subscribe"))
        if new_account:
            result.append(Message(\
                from_jid = self.component.jid, to_jid = _account.user_jid, \
                stanza_type = "normal", \
                subject = _account.get_new_message_subject(lang_class), \
                body = _account.get_new_message_body(lang_class)))
            result.append(Presence(from_jid = _account.jid, \
                                   to_jid = _account.user_jid, \
                                   stanza_type = "subscribe"))
        else:
            result.append(Message(\
                from_jid = self.component.jid, to_jid = _account.user_jid, \
                stanza_type = "normal", \
                subject = _account.get_update_message_subject(lang_class), \
                body = _account.get_update_message_body(lang_class)))
        self.db_disconnect()
        return result

    def account_set_register(self, name, from_jid, lang_class, \
                             x_data, info_query):
        """Update account"""
        self.__logger.debug("Updating account " + name)
        bare_from_jid = from_jid.bare()
        self.db_connect()
        accounts = Account.select(\
            AND(Account.q.name == name, \
                Account.q.user_jid == unicode(bare_from_jid)))
        accounts_count = accounts.count()
        _account = list(accounts)[0]
        self.db_disconnect()
        if accounts_count > 1:
            # Just print a warning, only the first account will be use
            self.__logger.error("There might not exist 2 accounts for " + \
                  bare_from_jid + " and named " + name)
        if accounts_count >= 1:
            return self._populate_account(_account, lang_class,
                                          x_data, info_query, False, False)
        else:
            self.__logger.error("Account " + name + \
                                " was not found, cannot update it")
            return []

    def _account_type_set_register(self, name, \
                                   from_jid, \
                                   account_class, \
                                   lang_class, \
                                   x_data, \
                                   info_query):
        """Create new account from account_class"""
        self.db_connect()
        bare_from_jid = from_jid.bare()
        _account = account_class(user_jid = unicode(bare_from_jid), \
                                 name = name, \
                                 jid = self.get_account_jid(name))
        all_accounts = Account.select(\
            Account.q.user_jid == unicode(bare_from_jid))
        first_account = (all_accounts.count() > 0)
        self.db_disconnect()
        return self._populate_account(_account, lang_class, x_data, \
                                      info_query, True, first_account)
        
    def account_type_set_register(self, name, \
                                  from_jid, \
                                  account_type, \
                                  lang_class, \
                                  x_data, \
                                  info_query):
        """Create new typed account"""
        return self._account_type_set_register(name, from_jid, \
            self._get_account_class(account_type + "Account"), lang_class, \
                                               x_data, info_query)

    def root_set_register(self, name, from_jid, lang_class, \
                          x_data, info_query):
        """Create new account when managing only one account type"""
        if not self.has_multiple_account_type:
            return self._account_type_set_register(name, from_jid, \
                                                   self.account_classes[0], \
                                                   lang_class, x_data, \
                                                   info_query)
        else:
            return []


    ###### presence generic handlers ######
    def account_handle_presence(self, name, from_jid, presence_func):
        """Handle presence sent to an account JID"""
        result = []
        self.db_connect()
        accounts = Account.select(\
                 AND(Account.q.name == name, \
                     Account.q.user_jid == unicode(from_jid.bare())))
        if accounts.count() > 0:
            result.extend(presence_func(accounts[0]))
        self.db_disconnect()
        return result

    def root_handle_presence(self, from_jid, presence_func, root_presence_func):
        """handle presence sent to component JID"""
        result = []
        self.db_connect()
        accounts = Account.select(\
                Account.q.user_jid == unicode(from_jid.bare()))
        accounts_length = 0
        for _account in accounts:
            accounts_length += 1
            result.extend(presence_func(_account))
        self.db_disconnect()
        if (accounts_length > 0):
            result.extend(root_presence_func(accounts_length))
        return result

    def send_presence_all(self, presence):
        """Send presence to all account. Optimized to use only one sql
        request"""
        current_user_jid = None
        result = []
        self.db_connect()
        # Explicit reference to account table (clauseTables) to use
        # "user_jid" column with Account subclasses
        for _account in \
                Account.select(clauseTables = ["account"], \
                               orderBy = "user_jid"):
            if current_user_jid != _account.user_jid:
                current_user_jid = _account.user_jid
                result.extend(getattr(self, "_send_presence_" + \
                                      presence + "_root")(_account.user_jid))
            result.extend(getattr(self, "_send_presence_" + \
                                  presence)(_account))
        self.db_disconnect()
        return result

    
    ###### presence_available handlers ######
    def account_handle_presence_available(self, name, from_jid, lang_class, show):
        """Handle presence \"available\" sent to an account JID"""
        return self.account_handle_presence(name, from_jid, \
                                            lambda _account:\
                                            self._send_presence_available(_account, \
                                                                          show, \
                                                                          lang_class))
    
    def root_handle_presence_available(self, from_jid, lang_class, show):
        """Handle presence \"available\" sent to component JID"""
        return self.root_handle_presence(from_jid, \
                                         lambda _account:\
                                         self._send_presence_available(_account, \
                                                                       show, \
                                                                       lang_class), \
                                         lambda nb_accounts : \
                                         self._send_presence_available_root(from_jid, \
                                                                            show, \
                                                                            str(nb_accounts) \
                                                                            + lang_class.message_status))

    ###### presence_unavailable handlers ######
    def account_handle_presence_unavailable(self, name, from_jid):
        """Handle presence \"unavailable\" sent to an account JID"""
        return self.account_handle_presence(name, from_jid, \
                                            lambda _account:\
                                            self._send_presence_unavailable(_account))
    
    def root_handle_presence_unavailable(self, from_jid):
        """Handle presence \"unavailable\" sent to component JID"""
        return self.root_handle_presence(from_jid, \
                                         lambda _account:\
                                         self._send_presence_unavailable(_account), \
                                         lambda nb_accounts: \
                                         self._send_presence_unavailable_root(from_jid))

    ###### presence_subscribe handlers ######
    def account_handle_presence_subscribe(self, name, from_jid, stanza):
        """Handle \"subscribe\" iq sent to an account JID"""
        if self._has_account(from_jid, name):
            return [stanza.make_accept_response()]
        else:
            self.__logger.debug("Account '" + str(name) + "' for user '" + \
                                unicode(from_jid.bare()) + "' was not found. " + \
                                "Refusing subscription")
            return []

    def root_handle_presence_subscribe(self, from_jid, stanza):
        """Handle \"subscribe\" iq sent to component JID"""
        if self._has_account(from_jid):
            return [stanza.make_accept_response()]
        else:
            self.__logger.debug("User '" + \
                                unicode(from_jid.bare()) + "' doesn't have any account. " + \
                                "Refusing subscription")
            return []

    ###### presence_unsubscribe handler (only apply to account) ######
    def account_handle_presence_unsubscribe(self, name, from_jid):
        """Handle \"unsubscribe\" iq sent to account JID"""
        result = []
        self.db_connect()
        accounts = Account.select(\
                AND(Account.q.name == name, \
                    Account.q.user_jid == unicode(from_jid.bare())))
        for _account in accounts:
            result.append(Presence(from_jid = _account.jid, \
                                   to_jid = from_jid, \
                                   stanza_type = "unsubscribe"))
            result.append(Presence(from_jid = _account.jid, \
                                   to_jid = from_jid, \
                                   stanza_type = "unsubscribed"))
            _account.destroySelf()
        self.db_disconnect()
        return result

    def probe_all_accounts_presence(self):
        """Send presence probe to all registered accounts"""
        return self.send_presence_all("probe")

    ###### Utils methods ######
    def _has_account(self, from_jid, name = None):
        """Check if user with \"from_jid\" JID has an account.
        Check if an account named \"name\" exist if \"name\" given."""
        self.db_connect()
        if name is None:
            accounts = Account.select(\
                Account.q.user_jid == unicode(from_jid.bare()))
        else:
            accounts = Account.select(\
                 AND(Account.q.name == name, \
                     Account.q.user_jid == unicode(from_jid.bare())))
        result = (accounts is not None \
                  and accounts.count() > 0)
        self.db_disconnect()
        return result

        
    def _list_accounts(self, disco_items, _account_class, bare_from_jid, account_type = ""):
        """List accounts in disco_items for given _account_class and user jid"""
        if account_type is not None and account_type != "":
            resource = "/" + account_type
            account_type = account_type + "/"
        else:
            resource = ""
        self.db_connect()
        for _account in _account_class.select(_account_class.q.user_jid == \
                                              unicode(bare_from_jid)):
            self.__logger.debug(str(_account))
            DiscoItem(disco_items, \
                      JID(unicode(_account.jid) + resource), \
                      account_type + _account.name, \
                      _account.long_name)
        self.db_disconnect()

    def _get_account_class(self, account_class_name):
        """Return account class definition from declared classes in
        account_classes from its class name"""
        self.__logger.debug("Looking for " + account_class_name)
        for _account_class in self.account_classes:
            if _account_class.__name__.lower() == account_class_name.lower():
                self.__logger.debug(account_class_name + " found")
                return _account_class
        self.__logger.debug(account_class_name + " not found")
        return None

    def db_connect(self):
        """Create a new connection to the DataBase (SQLObject use connection
        pool) associated to the current thread"""
        account.hub.threadConnection = \
                     connectionForURI(self.component.db_connection_str) # TODO : move db_connection_str to AccountManager
#        account.hub.threadConnection.debug = True

    def db_disconnect(self):
        """Delete connection associated to the current thread"""
        del account.hub.threadConnection

    def get_reg_form(self, lang_class, _account_class):
        """Return register form based on language and account class
        """
        reg_form = Form(title = lang_class.register_title, \
                        instructions = lang_class.register_instructions)
        # "name" field is mandatory
        reg_form.add_field(field_type = "text-single", \
                           label = lang_class.account_name, \
                           name = "name", \
                           required = True)

        for (field_name, \
             field_type, \
             field_options, \
             post_func, \
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
                field = reg_form.add_field(field_type = field_type, \
                                           label = label, \
                                           name = field_name, \
                                           value = default_func())
                if field_options is not None:
                    for option_value in field_options:
                        lang_label_attr = "field_" + field_name + "_" + option_value
                        if hasattr(lang_class, lang_label_attr):
                            label = getattr(lang_class, lang_label_attr)
                        else:
                            label = option_value
                        field.add_option(label = label, \
                                         values = [option_value])
                try:
                    post_func(None, default_func)
                except:
                    self.__logger.debug("Setting field " + field_name + " required")
                    field.required = True
            ## TODO : get default value if any
        return reg_form

    def get_reg_form_init(self, lang_class, _account):
        """Return register form for an existing account (update)
        """
        reg_form = self.get_reg_form(lang_class, _account.__class__)
        reg_form["name"].value = _account.name
        reg_form["name"].type = "hidden"
        for field in reg_form.fields: # TODO
            if hasattr(_account, field.name):
                field.value = getattr(_account, field.name)
        return reg_form

    def get_account_jid(self, name):
        """Compose account jid from account name"""
        return name + u"@" + unicode(self.component.jid)

    def _send_presence_probe_root(self, to_jid):
        """Send presence probe to account's user from root JID"""
        return [Presence(from_jid = self.component.jid, \
                         to_jid = to_jid, \
                         stanza_type = "probe")]
        
    def _send_presence_probe(self, _account):
        """Send presence probe to account's user"""
        return [Presence(from_jid = _account.jid, \
                         to_jid = _account.user_jid, \
                         stanza_type = "probe")]

    def _send_presence_unavailable_root(self, to_jid):
        """Send unavailable presence to account's user from root JID"""
        return [Presence(from_jid = self.component.jid, \
                         to_jid = to_jid, \
                         stanza_type = "unavailable")]
        
    def _send_presence_unavailable(self, _account):
        """Send unavailable presence to account's user"""
        _account.status = account.OFFLINE
        return [Presence(from_jid = _account.jid, \
                         to_jid = _account.user_jid, \
                         stanza_type = "unavailable")]

    def _send_presence_available_root(self, to_jid, show, status_msg):
        """Send available presence to account's user from root JID"""
        return [Presence(from_jid = self.component.jid, \
                         to_jid = to_jid, \
                         status = status_msg, \
                         show = show, \
                         stanza_type = "available")]
        
    def _send_presence_available(self, _account, show, lang_class):
        """Send available presence to account's user and ask for password
        if necessary"""
        result = []
        _account.default_lang_class = lang_class
        old_status = _account.status
        if show is None:
            _account.status = account.ONLINE
        else:
            _account.status = show
        result.append(Presence(from_jid = _account.jid, \
                               to_jid = _account.user_jid, \
                               status = _account.status_msg, \
                               show = show, \
                               stanza_type = "available"))
        if hasattr(_account, 'store_password') \
               and hasattr(_account, 'password') \
               and _account.store_password == False \
               and old_status == account.OFFLINE \
               and _account.password == None :
            result.extend(self.ask_password(_account, lang_class))
        return result
    
    def ask_password(self, _account, lang_class):
        """Send a Jabber message to ask for account password
        """
        result = []
        if hasattr(_account, 'waiting_password_reply') \
               and not _account.waiting_password_reply \
               and _account.status != account.OFFLINE:
            _account.waiting_password_reply = True
            result.append(Message(from_jid = _account.jid, \
                                  to_jid = _account.user_jid, \
                                  stanza_type = "normal", \
                                  subject = u"[PASSWORD] " + \
                                  lang_class.ask_password_subject, \
                                  body = lang_class.ask_password_body % \
                                  (_account.name)))
        return result

    def send_error(self, _account, exception):
        """Send an error message only one time until _account.in_error
        has been reset to False"""
        result = []
        if _account.in_error == False:
            _account.in_error = True
            result.append(Message(from_jid = _account.jid, \
                                  to_jid = _account.user_jid, \
                                  stanza_type = "error", \
                                  subject = _account.default_lang_class.check_error_subject, \
                                  body = _account.default_lang_class.check_error_body \
                                  % (exception)))
        return result

class MessageHandler(object):
    """Message handling class"""

    def filter(self, message):
        """Filter account to be processed by the handler
        return all accounts. DB connection might already be opened."""
        accounts = Account.select()
        return accounts

    def handle(self, message, lang, accounts):
        """Apply actions to do on given accounts
        Do nothing by default"""
        return []

class PasswordMessageHandler(MessageHandler):
    """Handle password message"""

    def __init__(self):
        """Ḧandler constructor"""
        self.password_regexp = re.compile("\[PASSWORD\]")

    def filter(self, message):
        """Return the uniq account associated with a name and user JID.
        DB connection might already be opened."""
        name = message.get_to().node
        bare_from_jid = unicode(message.get_from().bare())
        accounts = Account.select(\
            AND(Account.q.name == name, \
                    Account.q.user_jid == bare_from_jid))
        if accounts.count() != 1:
            print >>sys.stderr, "Account " + name + " for user " + bare_from_jid + " must be uniq"
        _account = accounts[0]
        if hasattr(_account, 'password') \
                and hasattr(_account, 'waiting_password_reply') \
                and (getattr(_account, 'waiting_password_reply') == True) \
                and self.password_regexp.search(message.get_subject()) \
                is not None:
            return accounts
        else:
            return None
        
    def handle(self, message, lang, accounts):
        """Receive password for given account"""
        _account = accounts[0]
        lang_class = lang.get_lang_class_from_node(message.get_node())
        _account.password = message.get_body()
        _account.waiting_password_reply = False
        return [Message(from_jid = _account.jid, \
                            to_jid = message.get_from(), \
                            stanza_type = "normal", \
                            subject = lang_class.password_saved_for_session, \
                            body = lang_class.password_saved_for_session)]
        
