# -*- coding: UTF-8 -*-
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
    - regular interval behavior
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
        self.name = "Jabber Component Library generic component"
        self.spool_dir = "."
        self.db_connection_str = db_connection_str
        self.version = VERSION
        self.time_unit = 60
        self.queue = Queue(100)
        self.account_manager = AccountManager(self)
        
        self.__logger = logging.getLogger("jcl.jabber.JCLComponent")
        self.lang = lang
        self.running = False
        self.wait_event = threading.Event()

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        # TODO : delete
        self.account_classes = (Account,)

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
                current_user_jid = None
                self.db_connect()
                # Explicit reference to account table (clauseTables) to use
                # "user_jid" column with Account subclasses
                for _account in \
                    self.account_classes[0].select(clauseTables = ["account"], \
                                                      orderBy = "user_jid"):
                    if current_user_jid != _account.user_jid:
                        current_user_jid = _account.user_jid
                        self.stream.send(Presence(\
                            from_jid = unicode(self.jid), \
                            to_jid = _account.user_jid, \
                            stanza_type = "unavailable"))
                    self.stream.send(Presence(\
                        from_jid = self.get_jid(_account), \
                        to_jid = _account.user_jid, \
                        stanza_type = "unavailable"))
                self.db_disconnect()
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
        current_jid = None
        self.db_connect()
        for _account in self.account_classes[0].select(clauseTables = ["account"], \
                                                          orderBy = "user_jid"):
            if _account.user_jid != current_jid:
                presence = Presence(from_jid = unicode(self.jid), \
                                    to_jid = _account.user_jid, \
                                    stanza_type = "probe")
                self.stream.send(presence)
                current_jid = _account.user_jid
            presence = Presence(from_jid = _account.jid, \
                                to_jid = _account.user_jid, \
                                stanza_type = "probe")
            self.stream.send(presence)
        self.db_disconnect()

    def signal_handler(self, signum, frame):
        """Stop method handler
        """
        self.__logger.debug("Signal %i received, shutting down..." % (signum,))
        self.running = False

    def apply_behavior(self, info_query, \
                       account_handler, \
                       account_type_handler, \
                       root_handler, \
                       send_result = False):
        bare_from_jid = unicode(info_query.get_from().bare())
        to_jid = info_query.get_to()
        name = to_jid.node
        account_type = to_jid.resource
        lang_class = self.lang.get_lang_class_from_node(info_query.get_node())
        if name is not None: # account
            self.__logger.debug("Applying behavior on account " + name)
            result = account_handler(name, bare_from_jid, account_type or "", lang_class)
        elif account_type is None: # root
            self.__logger.debug("Applying behavior on root node")
            result = root_handler(name, bare_from_jid, "", lang_class) # TODO : account_type not needed
        else: # account type
            self.__logger.debug("Applying behavior on account type " + account_type)
            result = account_type_handler(name, bare_from_jid, account_type, lang_class)
        if send_result:
            self.__logger.debug("Sending responses")
            for stanza in result:
                self.stream.send(stanza)
        return result
        
    def disco_get_info(self, node, info_query):
        """Discovery get info handler
        """
        return self.apply_behavior(info_query, \
                                   lambda name, bare_from_jid, account_type, lang_class: \
                                   self.account_manager.account_disco_get_info(), \
                                   lambda name, bare_from_jid, account_type, lang_class: \
                                   self.account_manager.account_type_disco_get_info(), \
                                   lambda name, bare_from_jid, account_type, lang_class: \
                                   self.account_manager.root_disco_get_info(self.name, \
                                                                            self.disco_identity.category, \
                                                                            self.disco_identity.type))

    def disco_get_items(self, node, info_query):
        """Discovery get nested nodes handler
        """
        return self.apply_behavior(info_query, \
                                   lambda name, bare_from_jid, account_type, lang_class: \
                                   DiscoItems(), \
                                   lambda name, bare_from_jid, account_type, lang_class: \
                                   self.account_manager.account_type_disco_get_items(bare_from_jid, account_type), \
                                   lambda name, bare_from_jid, account_type, lang_class: \
                                   self.account_manager.root_disco_get_items(bare_from_jid))

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
                            lambda name, bare_from_jid, account_type, lang_class: \
                            self.account_manager.account_get_register(info_query, \
                                                                      name, \
                                                                      bare_from_jid, \
                                                                      account_type, \
                                                                      lang_class), \
                            lambda name, bare_from_jid, account_type, lang_class: \
                            self.account_manager.account_type_get_register(info_query, \
                                                                           account_type, \
                                                                           lang_class), \
                            lambda name, bare_from_jid, account_type, lang_class: \
                            self.account_manager.root_get_register(info_query, \
                                                                   lang_class), \
                            send_result = True)

    def remove_all_accounts(self, user_jid):
        """Unsubscribe all accounts associated to 'user_jid' then delete
        those accounts from the DataBase"""
        self.db_connect()
        for _account in self.account_classes[0].select(\
            self.account_classes[0].q.user_jid == user_jid):
            self.__logger.debug("Deleting " + _account.name \
                                + " for " + user_jid)
            presence = Presence(from_jid = self.get_jid(_account), \
                                to_jid = user_jid, \
                                stanza_type = "unsubscribe")
            self.stream.send(presence)
            presence = Presence(from_jid = self.get_jid(_account), \
                                to_jid = user_jid, \
                                stanza_type = "unsubscribed")
            self.stream.send(presence)
            _account.destroySelf()
        presence = Presence(from_jid = self.jid, to_jid = user_jid, \
                            stanza_type = "unsubscribe")
        self.stream.send(presence)
        presence = Presence(from_jid = self.jid, to_jid = user_jid, \
                            stanza_type = "unsubscribed")
        self.stream.send(presence)
        self.db_disconnect()

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
            self.remove_all_accounts(base_from_jid)
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
        name = x_data["name"].value
        self.__logger.debug("Account name received = " + str(name))
        self.db_connect()
        accounts = Account.select(\
            AND(Account.q.name == name, \
                Account.q.user_jid == base_from_jid))
        accounts_count = accounts.count()
        all_accounts = Account.select(\
            Account.q.user_jid == base_from_jid)
        all_accounts_count = all_accounts.count()
        if accounts_count > 1:
            # Just print a warning, only the first account will be use
            self.__logger.error("There might not exist 2 accounts for " + \
                  base_from_jid + " and named " + name)
        if accounts_count >= 1:
            _account = list(accounts)[0]
        else:
            if info_query.get_to().resource is None:
                if len(self.account_classes) > 1:
                    self.__logger.error("There might be only one account class declared")
                new_account_class = self.account_classes[0]
            else:
                new_account_class = self._get_account_class(info_query.get_to().resource + "Account")
            _account = new_account_class(user_jid = unicode(base_from_jid), \
                                         name = name, \
                                         jid = name + u"@" + unicode(self.jid))
        self.__logger.debug("Account '" + str(name) + "' created: " + str(_account))
        field = None
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
            self.stream.send(iq_error)
            self.db_disconnect()
            return
        info_query = info_query.make_result_response()
        self.stream.send(info_query)

        if all_accounts_count == 0:
            self.stream.send(Presence(from_jid = self.jid, \
                                      to_jid = base_from_jid, \
                                      stanza_type = "subscribe"))
        if accounts_count == 0:
            self.stream.send(Message(\
                from_jid = self.jid, to_jid = from_jid, \
                stanza_type = "normal", \
                subject = _account.get_new_message_subject(lang_class), \
                body = _account.get_new_message_body(lang_class)))
            self.stream.send(Presence(from_jid = self.get_jid(_account), \
                                      to_jid = base_from_jid, \
                                      stanza_type = "subscribe"))
        else:
            self.stream.send(Message(\
                from_jid = self.jid, to_jid = from_jid, \
                stanza_type = "normal", \
                subject = _account.get_update_message_subject(lang_class), \
                body = _account.get_update_message_body(lang_class)))
        self.db_disconnect()

    def handle_presence_available(self, stanza):
        """Handle presence availability
        if presence sent to the component ('if not name'), presence is sent to
        all accounts for current user. Otherwise, send presence from current account.

        """
        self.__logger.debug("PRESENCE_AVAILABLE")
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        name = stanza.get_to().node
        lang_class = self.lang.get_lang_class_from_node(stanza.get_node())
        show = stanza.get_show()
        self.__logger.debug("SHOW : " + str(show))
        if name:
            self.__logger.debug("TO : " + name + " " + base_from_jid)
        self.db_connect()
        if not name:
            accounts = self.account_classes[0].select(\
                self.account_classes[0].q.user_jid == base_from_jid)
            accounts_length = 0
            for _account in accounts:
                accounts_length += 1
                self._send_presence_available(_account, show, lang_class)
            if (accounts_length > 0):
                presence = Presence(from_jid = self.jid, \
                                    to_jid = from_jid, \
                                    status = \
                                    str(accounts_length) \
                                    + lang_class.message_status, \
                                    show = show, \
                                    stanza_type = "available")
                self.stream.send(presence)
        else:
            accounts = self.account_classes[0].select(\
                 AND(self.account_classes[0].q.name == name, \
                     self.account_classes[0].q.user_jid == base_from_jid))
            if accounts.count() > 0:
                self._send_presence_available(accounts[0], show, lang_class)
        self.db_disconnect()
        return 1

    def handle_presence_unavailable(self, stanza):
        """Handle presence unavailability
        """
        self.__logger.debug("PRESENCE_UNAVAILABLE")
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        name = stanza.get_to().node
        self.db_connect()
        if not name:
            accounts = self.account_classes[0].select(\
                self.account_classes[0].q.user_jid == base_from_jid)
            for _account in accounts:
                _account.status = jcl.model.account.OFFLINE
                presence = Presence(from_jid = _account.jid, \
                                    to_jid = from_jid, \
                                    stanza_type = "unavailable")
                self.stream.send(presence)
            if accounts.count() > 0:
                presence = Presence(from_jid = stanza.get_to(), \
                                    to_jid = from_jid, \
                                    stanza_type = "unavailable")
                self.stream.send(presence)
        else:
            accounts = self.account_classes[0].select(\
                 AND(self.account_classes[0].q.name == name, \
                     self.account_classes[0].q.user_jid == base_from_jid))
            if accounts.count() > 0:
                presence = Presence(from_jid = stanza.get_to(), \
                                    to_jid = from_jid, \
                                    stanza_type = "unavailable")
                self.stream.send(presence)
        self.db_disconnect()
        return 1

    def handle_presence_subscribe(self, stanza):
        """Handle subscribe presence from user
        """
        self.__logger.debug("PRESENCE_SUBSCRIBE")
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        name = stanza.get_to().node
        accounts = None
        self.db_connect()
        if not name:
            self.__logger.debug("subscribe request on main jid")
            accounts = self.account_classes[0].select(\
                self.account_classes[0].q.user_jid == base_from_jid)
        else:
            self.__logger.debug("subscribe request on '" + name + "' account")
            accounts = self.account_classes[0].select(\
                 AND(self.account_classes[0].q.name == name, \
                     self.account_classes[0].q.user_jid == base_from_jid))
        if (accounts is not None \
            and accounts.count() > 0):
            presence = stanza.make_accept_response()
            self.stream.send(presence)
        else:
            self.__logger.debug("Account '" + str(name) + "' for user '" + \
                                str(base_from_jid) + "' was not found. " + \
                                "Refusing subscription")
        self.db_disconnect()
        return 1

    def handle_presence_subscribed(self, stanza):
        """Handle subscribed presence from user
        """
        self.__logger.debug("PRESENCE_SUBSCRIBED")
        return 1

    def handle_presence_unsubscribe(self, stanza):
        """Handle unsubscribe presence from user
        """
        self.__logger.debug("PRESENCE_UNSUBSCRIBE")
        name = stanza.get_to().node
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        self.db_connect()
        accounts = self.account_classes[0].select(\
                AND(self.account_classes[0].q.name == name, \
                    self.account_classes[0].q.user_jid == base_from_jid))
        for _account in accounts:
            presence = Presence(from_jid = _account.jid, \
                                to_jid = from_jid, \
                                stanza_type = "unsubscribe")
            self.stream.send(presence)
            _account.destroySelf()
            presence = Presence(from_jid = _account.jid, \
                                to_jid = from_jid, \
                                stanza_type = "unsubscribed")
            self.stream.send(presence)
        self.db_disconnect()
        return 1

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
        lang_class = self.lang.get_lang_class_from_node(message.get_node())
        name = message.get_to().node
        base_from_jid = unicode(message.get_from().bare())
        self.db_connect()
        accounts = self.account_classes[0].select(\
            AND(self.account_classes[0].q.name == name, \
                self.account_classes[0].q.user_jid == base_from_jid))
        if accounts.count() == 1:
            _account = list(accounts)[0]
            if hasattr(_account, 'password') \
                   and hasattr(_account, 'waiting_password_reply') \
                   and re.compile("\[PASSWORD\]").search(message.get_subject()) \
                   is not None:
                _account.password = message.get_body()
                _account.waiting_password_reply = False
                msg = Message(from_jid = _account.jid, \
                              to_jid = message.get_from(), \
                              stanza_type = "normal", \
                              subject = lang_class.password_saved_for_session, \
                              body = lang_class.password_saved_for_session)
                self.stream.send(msg)
        self.db_disconnect()
        return 1

    ###########################################################################
    # Utils
    ###########################################################################
    # TODO : delete
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

    def _send_presence_available(self, _account, show, lang_class):
        """Send available presence to account's user and ask for password
        if necessary"""
        _account.default_lang_class = lang_class
        old_status = _account.status
        if show is None:
            _account.status = account.ONLINE
        else:
            _account.status = show
        self.stream.send(Presence(from_jid = _account.jid, \
                     to_jid = _account.user_jid, \
                     status = _account.status_msg, \
                     show = show, \
                     stanza_type = "available"))
        if hasattr(_account, 'store_password') \
               and hasattr(_account, 'password') \
               and _account.store_password == False \
               and old_status == account.OFFLINE \
               and _account.password == None :
            self.ask_password(_account, lang_class)

    def ask_password(self, _account, lang_class):
        """Send a Jabber message to ask for account password
        """
        if hasattr(_account, 'waiting_password_reply') \
               and not _account.waiting_password_reply \
               and _account.status != account.OFFLINE:
            _account.waiting_password_reply = True
            msg = Message(from_jid = _account.jid, \
                          to_jid = _account.user_jid, \
                          stanza_type = "normal", \
                          subject = u"[PASSWORD] " + \
                          lang_class.ask_password_subject, \
                          body = lang_class.ask_password_body % \
                          (_account.name))
            self.stream.send(msg)

    def send_error(self, _account, exception):
        """Send an error message only one time until _account.in_error
        has been reset to False"""
        if _account.in_error == False:
            _account.in_error = True
            msg = Message(from_jid = _account.jid, \
                          to_jid = _account.user_jid, \
                          stanza_type = "error", \
                          subject = _account.default_lang_class.check_error_subject, \
                          body = _account.default_lang_class.check_error_body \
                          % (exception))
            self.stream.send(msg)
        type, value, stack = sys.exc_info()
        # TODO : not checking email here
        self.__logger.debug("Error while first checking mail : %s\n%s" \
                            % (exception, "".join(traceback.format_exception
                                                  (type, value, stack, 5))))
        
    def get_jid(self, _account):
        """Return account jid based on account instance and component jid
        """
        return _account.name + u"@" + unicode(self.jid)

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
        DiscoIdentity(disco_info, name, \
                      category, \
                      type)
        return disco_info

    ###### disco_get_items handlers ######
    def account_type_disco_get_items(self, bare_from_jid, account_type):
        """Discovery get_items on an account type node"""
        self.__logger.debug("Listing account for " + account_type)
        disco_items = DiscoItems()
        account_class = self._get_account_class(account_type + "Account")
        if account_class is not None:
            self._list_accounts(disco_items, \
                                account_class, \
                                bare_from_jid, \
                                account_type = account_type)
        else:
            self.__logger.error("Error: " + account_class.__name__ \
                                + " class not in account_classes")
        return disco_items
        
    def root_disco_get_items(self, bare_from_jid):
        """Discovery get_items on root node"""
        disco_items = DiscoItems()
        regexp_type = re.compile("(.*)Account$")
        if self.has_multiple_account_type: # list accounts with only one type declared
            list_func = lambda disco_items, account_class, bare_from_jid, account_type: \
                        DiscoItem(disco_items, \
                                  JID(unicode(self.component.jid) + "/" + account_type), \
                                  account_type, \
                                  account_type)
        else:
            list_func = self._list_accounts

        for account_class in self.account_classes:
            match = regexp_type.search(account_class.__name__)
            if match is not None:
                account_type = match.group(1)
                list_func(disco_items, account_class, \
                          bare_from_jid, account_type)
            else:
                self.__logger.error(account_class.__name__ + \
                                    " name not well formed")
        return disco_items

    ###### get_register handlers ######
    def account_get_register(self, info_query, \
                             name, \
                             bare_from_jid, \
                             account_type, \
                             lang_class):
        """Handle get_register on an account.
        Return a preinitialized form"""
        info_query = info_query.make_result_response()
        account_class = self._get_account_class(account_type + "Account")
        self.db_connect()
        # TODO : do it only one time
        accounts = account_class.select(\
                AND(account_class.q.name == name, \
                    account_class.q.user_jid == bare_from_jid))
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
        
    ###### Utils methods ######
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
