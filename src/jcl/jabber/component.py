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
from pyxmpp.streambase import StreamError, FatalStreamError

from jcl.jabber.x import X
from jcl.model import account
from jcl.model.account import Account

VERSION = "0.1"

###############################################################################
# JCL implementation
###############################################################################
class JCLComponent(Component):    
    """Implement default JCL component behavior:
    - regular interval behavior
    - Jabber register process (add, delete, update accounts)
    - Jabber presence handling
    - passwork request at login
    """

    timeout = 1

    def set_account_class(self, account_class):
        """account_class attribut setter
        create associated table via SQLObject"""
        self.__account_class = account_class
        self.db_connect()
        self.__account_class.createTable() # TODO: ifNotExists = True)
        self.db_disconnect()

    def get_account_class(self):
        """account_class attribut getter"""
        return self.__account_class

    account_class = property(get_account_class, set_account_class)

    
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
        self.set_account_class(Account)
        self.version = VERSION
        self.accounts = []
        self.time_unit = 60
        self.queue = Queue(100)
        
        self.disco_info.add_feature("jabber:iq:version")
        self.disco_info.add_feature("jabber:iq:register")
        self.__logger = logging.getLogger("jcl.jabber.JCLComponent")
        # TODO : self.__lang = Lang(default_lang)
        self.__lang = None
        self.running = False

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def run(self):
        """Main loop
        Connect to Jabber server
        Start timer thread
        Call Component main loop
        Clean up when shutting down JCLcomponent
        """
        self.spool_dir += "/" + str(self.jid)
        self.running = True
        self.connect()
        ## TODO : workaround to make test_run pass on FeederComponent
#        time.sleep(1)
        ##
        timer_thread = threading.Thread(target = self.time_handler, \
                                        name = "TimerThread")
        timer_thread.start()
        try:
            while (self.running and self.stream
                   and not self.stream.eof and self.stream.socket is not None):
                try:
                    self.stream.loop_iter(JCLComponent.timeout)
                    if self.queue.qsize():
                        raise self.queue.get(0)
            except Exception, e:
                self.__logger.exception("Exception cought:")
                # put Exception in queue to be use by unit tests
                self.queue.put(e)
                raise
        finally:
            if self.stream:
                # TODO : send unavailble from transport and all account to users
                pass
#                for jid in self.__storage.keys(()):
#                    p = Presence(from_jid = unicode(self.jid), to_jid = jid, \
#                                 stanza_type = "unavailable")
#                    self.stream.send(p)
#                for jid, name in self.__storage.keys():
#                    if self.__storage[(jid, name)].status != "offline":
#                      p = Presence(from_jid = name + "@" + unicode(self.jid),\
#                                     to_jid = jid, \
#                                     stanza_type = "unavailable")
#                        self.stream.send(p)
#            threads = threading.enumerate()
            timer_thread.join(JCLComponent.timeout)
#            for _thread in threads:
#                try:
#                    _thread.join(10 * JCLComponent.timeout)
#                except:
#                    pass
#            for _thread in threads:
#                try:
#                    _thread.join(JCLComponent.timeout)
#                except:
#                    pass
            self.disconnect()
            # TODO : terminate SQLObject
            self.__logger.debug("Exitting normally")
            # TODO : terminate SQLObject

    #################
    # SQlite connections are not multi-threaded
    # Utils workaround methods
    #################
    def db_connect(self):
        account.hub.threadConnection = \
                     connectionForURI(self.db_connection_str)

    def db_disconnect(self):
#        account.hub.threadConnection.close()
        del account.hub.threadConnection


    ###########################################################################
    # Handlers
    ###########################################################################
    def time_handler(self):
        """Timer thread handler
        """
        self.__logger.info("Timer thread started...")
        try:
            while self.running:
                self.handle_tick()
                self.__logger.debug("Resetting alarm signal")
                time.sleep(self.time_unit)
        except Exception, e:
            self.queue.put(e)
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
        for account in self.account_class.select(orderBy = "user_jid"):
            if account.user_jid != current_jid:
                presence = Presence(from_jid = unicode(self.jid), \
                                    to_jid = account.user_jid, \
                                    stanza_type = "probe")
                self.stream.send(presence)
                current_jid = account.user_jid
            presence = Presence(from_jid = self.get_jid(account), \
                                to_jid = account.user_jid, \
                                stanza_type = "probe")
            self.stream.send(presence)
        self.db_disconnect()

    def signal_handler(self, signum, frame):
        """Stop method handler
        """
        self.__logger.debug("Signal %i received, shutting down..." % (signum,))
        self.running = False

    def disco_get_info(self, node, input_query):
        """Discovery get info handler
        """
        self.__logger.debug("DISCO_GET_INFO")
        if node is not None:
            disco_info = DiscoInfo()
            disco_info.add_feature("jabber:iq:register")
            return disco_info
        else:
            return self.disco_info

    def disco_get_items(self, node, input_query):
        """Discovery get nested nodes handler
        """
        self.__logger.debug("DISCO_GET_ITEMS")
## TODO Lang
##  lang_class = self.__lang.get_lang_class_from_node(info_query.get_node())
        base_from_jid = unicode(info_query.get_from().bare())
        disco_items = DiscoItems()
        if not node:
## TODO : list accounts
            self.db_connect()
            for account in self.account_class.select(Account.q.user_jid == \
                                                     base_from_jid):
                self.__logger.debug(str(account))
                DiscoItem(disco_items, \
                          JID(account.jid), \
                          account.name, account.long_name)
            self.db_disconnect()
        return disco_items

    def handle_get_version(self, input_query):
        """Get Version handler
        """
        self.__logger.debug("GET_VERSION")
        input_query = input_query.make_result_response()
        query = input_query.new_query("jabber:iq:version")
        query.newTextChild(query.ns(), "name", self.name)
        query.newTextChild(query.ns(), "version", self.version)
        self.stream.send(input_query)
        return 1

    def handle_get_register(self, input_query):
        """Send back register form to user
        """
        self.__logger.debug("GET_REGISTER")
## TODO Lang
##  lang_class = self.__lang.get_lang_class_from_node(input_query.get_node())
        lang_class = None
##        base_from_jid = unicode(input_query.get_from().bare())
        to_jid = input_query.get_to()
        input_query = input_query.make_result_response()
        query = input_query.new_query("jabber:iq:register")
        if to_jid and to_jid != self.jid:
            self.db_connect()
            self.get_reg_form_init(lang_class, \
                                   self.account_class.select() # TODO
                                   ).attach_xml(query)
            self.db_disconnect()
        else:
            self.get_reg_form(lang_class).attach_xml(query)
        self.stream.send(input_query)
        return 1

    def handle_set_register(self, input_query):
        """Handle user registration response
        """
        self.__logger.debug("SET_REGISTER")
##        lang_class = \
##                 self.__lang.get_lang_class_from_node(input_query.get_node())
        from_jid = input_query.get_from()
##        base_from_jid = unicode(from_jid.bare())
        remove = input_query.xpath_eval("r:query/r:remove", \
                                        {"r" : "jabber:iq:register"})
        if remove:
#            for name in self.__storage.keys((base_from_jid,)):
#                self.__logger.debug("Deleting " + name \
#                                    + " for " + base_from_jid)
#              presence = Presence(from_jid = name + "@" + unicode(self.jid), \
#                                    to_jid = from_jid, \
#                                    stanza_type = "unsubscribe")
#                self.stream.send(presence)
#              presence = Presence(from_jid = name + "@" + unicode(self.jid), \
#                                    to_jid = from_jid, \
#                                    stanza_type = "unsubscribed")
#                self.stream.send(presence)
#                del self.__storage[(base_from_jid, name)]
            presence = Presence(from_jid = self.jid, to_jid = from_jid, \
                                stanza_type = "unsubscribe")
            self.stream.send(presence)
            presence = Presence(from_jid = self.jid, to_jid = from_jid, \
                                stanza_type = "unsubscribed")
            self.stream.send(presence)
            return 1

        query = input_query.get_query()
        x_data = X()
        x_data.from_xml(query.children)
        # TODO : get info from Xdata
  

    def handle_presence_available(self, stanza):
        """Handle presence availability
        """
        self.__logger.debug("PRESENCE_AVAILABLE")
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        name = stanza.get_to().node
##        lang_class = self.__lang.get_lang_class_from_node(stanza.get_node())
        show = stanza.get_show()
        self.__logger.debug("SHOW : " + str(show))
        if name:
            self.__logger.debug("TO : " + name + " " + base_from_jid)
        # TODO : if to transport send back available to all user's account
        # else send available presence
        return 1

    def handle_presence_unavailable(self, stanza):
        """Handle presence unavailability
        """
        self.__logger.debug("PRESENCE_UNAVAILABLE")
##        from_jid = stanza.get_from()
##        base_from_jid = unicode(from_jid.bare())
        # TODO : send unavailable to all user's account if target is transport
        # else send unavailable back
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
##        from_jid = stanza.get_from()
##        base_from_jid = unicode(from_jid.bare())
        # TODO : send presence available to subscribed user
        return 1

    def handle_presence_unsubscribe(self, stanza):
        """Handle unsubscribe presence from user
        """
        self.__logger.debug("PRESENCE_UNSUBSCRIBE")
        name = stanza.get_to().node
        from_jid = stanza.get_from()
##        base_from_jid = unicode(from_jid.bare())
        # TODO : delete from account base
        presence = Presence(from_jid = stanza.get_to(), to_jid = from_jid, \
                            stanza_type = "unsubscribe")
        self.stream.send(presence)
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
        """
        self.__logger.debug("MESSAGE: " + message.get_body())
        lang_class = self.__lang.get_lang_class_from_node(message.get_node())
##        name = message.get_to().node
##        base_from_jid = unicode(message.get_from().bare())
        if re.compile("\[PASSWORD\]").search(message.get_subject()) \
               is not None:
## TODO               and self.__storage.has_key((base_from_jid, name)):
##            account = self.__storage[(base_from_jid, name)]
            account = Account()
            account.password = message.get_body()
            account.waiting_password_reply = False
            msg = Message(from_jid = account.jid, \
                          to_jid = message.get_from(), \
                          stanza_type = "normal", \
                          subject = lang_class.password_saved_for_session, \
                          body = lang_class.password_saved_for_session)
            self.stream.send(msg)
        return 1

    ###########################################################################
    # Utils
    ###########################################################################
    def _ask_password(self, from_jid, lang_class, account):
        """Send a Jabber message to ask for account password
        """
        #TODO be JMC independant
        if not account.waiting_password_reply \
               and account.status != "offline":
            account.waiting_password_reply = True
            msg = Message(from_jid = account.jid, \
                          to_jid = from_jid, \
                          stanza_type = "normal", \
                          subject = u"[PASSWORD] " + \
                          lang_class.ask_password_subject, \
                          body = lang_class.ask_password_body % \
                          (account.host, account.login))
            self.stream.send(msg)

    def get_jid(self, account):
        """Return account jid based on account instance and component jid
        """
        return account.name + u"@" + unicode(self.jid)
    
    ###########################################################################
    # Virtual methods
    ###########################################################################
    def handle_tick(self):
        """Virtual method
        Called regularly
        """
        pass

    def get_reg_form(self, lang_class, account_class):
        """Virtual method
        Return register form based on language and account class
        """
        pass

    def get_reg_form_init(self, lang_class, account):
        """Virtual method
        Return register form for an existing account (update)
        """
        pass
