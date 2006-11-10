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

from Queue import Queue

from sqlobject.dbconnection import connectionForURI

from pyxmpp.jid import JID
from pyxmpp.jabberd.component import Component
from pyxmpp.jabber.disco import DiscoInfo, DiscoItems, DiscoItem
from pyxmpp.message import Message
from pyxmpp.presence import Presence

import jcl
from jcl.jabber.x import DataForm
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
                 disco_type = "headline"):
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
        self.__account_class = None
        self.version = VERSION
        self.accounts = []
        self.time_unit = 60
        self.queue = Queue(100)

        self.disco_info.add_feature("jabber:iq:version")
        self.disco_info.add_feature("jabber:iq:register")
        self.__logger = logging.getLogger("jcl.jabber.JCLComponent")
        self.__lang = Lang() # TODO : Lang(default_lang = from_config)
        self.running = False

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def set_account_class(self, account_class):
        """account_class attribut setter
        create associated table via SQLObject"""
        self.__account_class = account_class
        self.db_connect()
        self.__account_class.createTable(ifNotExists = True)
        self.db_disconnect()

    def get_account_class(self):
        """account_class attribut getter"""
        if self.__account_class is None:
            self.set_account_class(Account)
        return self.__account_class

    account_class = property(get_account_class, set_account_class)

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
            try:
                while (self.running and self.stream \
                       and not self.stream.eof \
                       and self.stream.socket is not None):
                    self.stream.loop_iter(JCLComponent.timeout)
                    if self.queue.qsize():
                        raise self.queue.get(0)
            except Exception, exception:
                #self.__logger.exception("Exception cought:")
                # put Exception in queue to be use by unit tests
                self.queue.put(exception)
                raise
        finally:
            if self.stream and not self.stream.eof \
                   and self.stream.socket is not None:
                current_user_jid = None
                self.db_connect()
                for _account in \
                        self.account_class.select(orderBy = "user_jid"):
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
                time.sleep(self.time_unit)
        except Exception, exception:
            self.queue.put(exception)
            raise

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
        for _account in self.account_class.select(orderBy = "user_jid"):
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

    def disco_get_info(self, node, info_query):
        """Discovery get info handler
        """
        self.__logger.debug("DISCO_GET_INFO")
        if node is not None:
            disco_info = DiscoInfo()
            disco_info.add_feature("jabber:iq:register")
            return disco_info
        else:
            return self.disco_info

    def disco_get_items(self, node, info_query):
        """Discovery get nested nodes handler
        """
        self.__logger.debug("DISCO_GET_ITEMS")
        base_from_jid = unicode(info_query.get_from().bare())
        disco_items = DiscoItems()
        if not node:
            self.db_connect()
            for _account in self.account_class.select(Account.q.user_jid == \
                                                      base_from_jid):
                self.__logger.debug(str(_account))
                DiscoItem(disco_items, \
                          JID(_account.jid), \
                          _account.name, _account.long_name)
            self.db_disconnect()
        return disco_items

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
        """
        self.__logger.debug("GET_REGISTER")
        lang_class = self.__lang.get_lang_class_from_node(info_query.get_node())
        base_from_jid = unicode(info_query.get_from().bare())
        to_jid = info_query.get_to()
        name = to_jid.node
        info_query = info_query.make_result_response()
        query = info_query.new_query("jabber:iq:register")
        if to_jid and to_jid != self.jid:
            self.db_connect()
            for _account in self.account_class.select(\
                self.account_class.q.user_jid == base_from_jid \
                and self.account_class.q.name == name):
                self.get_reg_form_init(lang_class, \
                                       _account).attach_xml(query)
            self.db_disconnect()
        else:
            self.get_reg_form(lang_class).attach_xml(query)
        self.stream.send(info_query)
        return 1

    def remove_all_accounts(self, user_jid):
        """Unsubscribe all accounts associated to 'user_jid' then delete
        those accounts from the DataBase"""
        self.db_connect()
        for _account in self.account_class.select(\
            self.account_class.q.user_jid == user_jid):
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
                   self.__lang.get_lang_class_from_node(info_query.get_node())
        from_jid = info_query.get_from()
        base_from_jid = unicode(from_jid.bare())
        remove = info_query.xpath_eval("r:query/r:remove", \
                                        {"r" : "jabber:iq:register"})
        if remove:
            self.remove_all_accounts(base_from_jid)
            return 1

        query = info_query.get_query()
        x_data = DataForm()
        x_data.from_xml(query.children)
        name = x_data.get_field_value("name")
        if name is None:
            # TODO : find correct error for mandatory field
            info_query = info_query.make_error_response(\
                "resource-constraint")
            self.stream.send(info_query)
            return            
        self.db_connect()
        accounts = self.account_class.select(\
            self.account_class.q.user_jid == base_from_jid \
            and self.account_class.q.name == name)
        accounts_count = accounts.count()
        all_accounts = self.account_class.select(\
            self.account_class.q.user_jid == base_from_jid)
        all_accounts_count = all_accounts.count()
        if accounts_count > 1:
            # Just print a warning, only the first account will be use
            print >> sys.stderr, "There might not exist 2 accounts for " + \
                  base_from_jid + " and named " + name
        if accounts_count >= 1:
            _account = list(accounts)[0]
        else:
            _account = self.account_class(user_jid = base_from_jid, \
                                          name = name, \
                                          jid = name + u"@"+unicode(self.jid))
        try:
            for (field, field_type, field_post_func, field_default_func) in \
                    self.account_class.get_register_fields():
                setattr(_account, field, \
                        x_data.get_field_value(field, \
                                               field_post_func, \
                                               field_default_func))
        except FieldError, exception:
            _account.destroySelf()
            # TODO: get correct error from exception
            info_query = info_query.make_error_response("resource-constraint")
            self.stream.send(info_query)
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
        """
        self.__logger.debug("PRESENCE_AVAILABLE")
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        name = stanza.get_to().node
        lang_class = self.__lang.get_lang_class_from_node(stanza.get_node())
        show = stanza.get_show()
        self.__logger.debug("SHOW : " + str(show))
        if name:
            self.__logger.debug("TO : " + name + " " + base_from_jid)
        self.db_connect()
        if not name:
            accounts = self.account_class.select(\
                self.account_class.q.user_jid == base_from_jid)
            # TODO: Translate
            accounts_length = 0
            for _account in accounts:
                accounts_length += 1
                self._send_presence_available(_account, show, lang_class)
            presence = Presence(from_jid = self.jid, \
                                to_jid = from_jid, \
                                status = \
                                str(accounts_length) \
                                + " accounts registered.", \
                                show = show, \
                                stanza_type = "available")
            self.stream.send(presence)
        else:
            accounts = self.account_class.select(\
                self.account_class.q.user_jid == base_from_jid
                and self.account_class.q.name == name)
            if accounts.count() >= 1:
                self._send_presence_available(accounts[0], show, lang_class)
        self.db_disconnect()
        return 1

    def handle_presence_unavailable(self, stanza):
        """Handle presence unavailability
        """
        self.__logger.debug("PRESENCE_UNAVAILABLE")
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        if stanza.get_to() == unicode(self.jid):
            self.db_connect()
            for _account in self.account_class.select(\
                self.account_class.q.user_jid == base_from_jid):
                _account.status = jcl.model.account.OFFLINE
                presence = Presence(from_jid = _account.jid, \
                                    to_jid = from_jid, \
                                    stanza_type = "unavailable")
                self.stream.send(presence)
            self.db_disconnect()
        presence = Presence(from_jid = stanza.get_to(), \
                            to_jid = from_jid, \
                            stanza_type = "unavailable")
        self.stream.send(presence)
        return 1

    def handle_presence_subscribe(self, stanza):
        """Handle subscribe presence from user
        """
        self.__logger.debug("PRESENCE_SUBSCRIBE")
        presence = stanza.make_accept_response()
        self.stream.send(presence)
        return 1

    def handle_presence_subscribed(self, stanza):
        """Handle subscribed presence from user
        """
        self.__logger.debug("PRESENCE_SUBSCRIBED")
        name = stanza.get_to().node
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
#        accounts = self.account_class.select(\
#                self.account_class.q.user_jid == base_from_jid
#                and self.account_class.q.name == name)
#        if accounts.count() >= 1:
#            _account = list(accounts)[0]
#            self._send_presence_available(_account, "show", lang_class)
        # TODO : send presence available to subscribed user
        # is it necessary to send available presence ?
        return 1

    def handle_presence_unsubscribe(self, stanza):
        """Handle unsubscribe presence from user
        """
        self.__logger.debug("PRESENCE_UNSUBSCRIBE")
        name = stanza.get_to().node
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        presence = Presence(from_jid = stanza.get_to(), to_jid = from_jid, \
                            stanza_type = "unsubscribe")
        self.stream.send(presence)
        self.db_connect()
        for _account in self.account_class.select(\
            self.account_class.q.user_jid == base_from_jid \
            and self.account_class.q.name == name):
            _account.destroySelf()
        self.db_disconnect()
        presence = stanza.make_accept_response()
        self.stream.send(presence)
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
        lang_class = self.__lang.get_lang_class_from_node(message.get_node())
        name = message.get_to().node
        base_from_jid = unicode(message.get_from().bare())
        self.db_connect()
        accounts = self.account_class.select(\
            self.account_class.q.user_jid == base_from_jid \
            and self.account_class.q.name == name)
        if hasattr(self.account_class, 'password') \
               and hasattr(self.account_class, 'waiting_password_reply') \
               and re.compile("\[PASSWORD\]").search(message.get_subject()) \
               is not None \
               and accounts.count() == 1:
            _account = list(accounts)[0]
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
        if hasattr(self.account_class, 'store_password') \
               and hasattr(self.account_class, 'password') \
               and _account.store_password == False \
               and old_status == account.OFFLINE \
               and _account.password == None :
            self._ask_password(_account, lang_class)

    def _ask_password(self, _account, lang_class):
        """Send a Jabber message to ask for account password
        """
        if hasattr(self.account_class, 'waiting_password_reply') \
               and not _account.waiting_password_reply \
               and _account.status != account.OFFLINE:
            _account.waiting_password_reply = True
            msg = Message(from_jid = _account.jid, \
                          to_jid = _account.user_jid, \
                          stanza_type = "normal", \
                          subject = u"[PASSWORD] " + \
                          lang_class.ask_password_subject)#, \
##                          body = lang_class.ask_password_body)# % \
##                          (account.host, account.login))
            self.stream.send(msg)

    def get_jid(self, _account):
        """Return account jid based on account instance and component jid
        """
        return _account.name + u"@" + unicode(self.jid)

    def get_reg_form(self, lang_class):
        """Return register form based on language and account class
        """
        reg_form = DataForm()
        reg_form.xmlns = "jabber:x:data"
        reg_form.title = lang_class.register_title
        reg_form.instructions = lang_class.register_instructions
        reg_form.type = "form"

        # "name" field is mandatory
        reg_form.add_field(field_type = "text-single", \
                           label = lang_class.account_name, \
                           var = "name")

        for (field, field_type, post_func, default_func) in \
                self.account_class.get_register_fields():
            lang_label_attr = self.account_class.__name__.lower() \
                              + "_" + field
            if hasattr(lang_class, lang_label_attr):
                label = getattr(lang_class, lang_label_attr)
            else:
                label = field
            reg_form.add_field(field_type = field_type, \
                               label = label, \
                               var = field)
            ## TODO : Add page when empty tuple given
            ## TODO : get default value if any
        return reg_form

    def get_reg_form_init(self, lang_class, _account):
        """Return register form for an existing account (update)
        """
        reg_form = self.get_reg_form(lang_class)
        reg_form.fields["name"].value = _account.name
        reg_form.fields["name"].type = "hidden"
        for (field_name, field) in reg_form.fields.items():
            if hasattr(self.account_class, field_name):
                field.value = str(getattr(_account, field_name))
        return reg_form

    ###########################################################################
    # Virtual methods
    ###########################################################################
    def handle_tick(self):
        """Virtual method
        Called regularly
        """
        raise NotImplementedError
