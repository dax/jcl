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

import logging
import signal

from pyxmpp.jid import JID
from pyxmpp.jabberd.component import Component
from pyxmpp.presence import Presence

from jcl.model.account import Account

VERSION = "0.1"

###############################################################################
# JCL implementation
###############################################################################
class JCLComponent(Component):
    def __init__(self,
                 jid,
                 secret,
                 server,
                 port,
                 name = "Jabber Component Library generic component",
                 disco_category = "gateway",
                 disco_type = "headline",
                 spool_dir = ".",
                 check_interval = 1,
                 account_class = Account):
        Component.__init__(self, \
                           JID(jid), \
                           secret, \
                           port, \
                           disco_category, \
                           disco_type)
        self.__logger = logging.getLogger("jcl.jabber.JCLComponent")
        # TODO : self.__lang = Lang(default_lang)
        self.__name = name
        self.__disco_category = disco_category
        self.__disco_type = disco_type
        self.__interval = check_interval
        self.running = False

        self.__shutdown = 0

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        spool_dir += "/" + jid
        self.__account_class = account_class
        self.__account_class.createTable(ifNotExists = True)
        self.version = VERSION
        
    def authenticated(self):
        Component.authenticated(self)
        self.__logger.debug("AUTHENTICATED")
        # Send probe for transport
        current_jid = None
        for account in self.__account_class.select(orderBy = "user_jid"):
            if account.user_jid != current_jid:
                p = Presence(from_jid = unicode(self.jid), \
                             to_jid = account.user_jid, \
                             stanza_type = "probe")
                self.stream.send(p)
                current_jid = account.user_jid
            p = Presence(from_jid = self.get_jid(account), \
                         to_jid = account.user_jid, \
                         stanza_type = "probe")
            self.stream.send(p)
            
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

    def run(self):
        self.connect()
        self.running = True
        thread.start_new_thread(self.time_handler, ())
        try:
            while (not self.__shutdown and self.stream
                   and not self.stream.eof and self.stream.socket is not None):
                try:
                    self.stream.loop_iter(timeout)
                except (KeyboardInterrupt, SystemExit, FatalStreamError, \
                        StreamError):
                    raise
                except:
                    self.__logger.exception("Exception cought:")
        finally:
            self.running = False
            if self.stream:
                # TODO : send unavailble from transport and all account to users
                pass
#                for jid in self.__storage.keys(()):
#                    p = Presence(from_jid = unicode(self.jid), to_jid = jid, \
#                                 stanza_type = "unavailable")
#                    self.stream.send(p)
#                for jid, name in self.__storage.keys():
#                    if self.__storage[(jid, name)].status != "offline":
#                        p = Presence(from_jid = name + "@" + unicode(self.jid), \
#                                     to_jid = jid, \
#                                     stanza_type = "unavailable")
#                        self.stream.send(p)
            threads = threading.enumerate()
            for th in threads:
                try:
                    th.join(10 * timeout)
                except:
                    pass
            for th in threads:
                try:
                    th.join(timeout)
                except:
                    pass
            self.disconnect()
            # TODO : terminate SQLObject
            self.__logger.debug("Exitting normally")

    def get_reg_form(self, lang_class, account_class):
        pass

    def get_reg_form_init(self, lang_class, account):
        pass

    def _ask_password(self, lang_class, account):
        if not account.waiting_password_reply \
               and account.status != "offline":
            account.waiting_password_reply = True
            msg = Message(from_jid = account.jid, \
                          to_jid = from_jid, \
                          stanza_type = "normal", \
                          subject = u"[PASSWORD] " + lang_class.ask_password_subject, \
                          body = lang_class.ask_password_body % \
                          (account.host, account.login))
            self.stream.send(msg)

    def get_jid(self, account):
        return account.name + u"@" + unicode(self.jid)
    
    ## Handlers

    """ Stop method handler """
    def signal_handler(self, signum, frame):
        self.__logger.debug("Signal %i received, shutting down..." % (signum,))
        self.__shutdown = 1


    def stream_state_changed(self,state,arg):
        self.__logger.debug("*** State changed: %s %r ***" % (state,arg))

    """ Discovery get info handler """
    def disco_get_info(self, node, iq):
        self.__logger.debug("DISCO_GET_INFO")
        di = DiscoInfo()
        if node is None:
            di.add_feature("jabber:iq:version")
            di.add_feature("jabber:iq:register")
            DiscoIdentity(di, self.__name, \
                          self.__disco_category, \
                          self.__disco_type)
        else:
            di.add_feature("jabber:iq:register")
        return di

    """ Discovery get nested nodes handler """
    def disco_get_items(self, node, iq):
        self.__logger.debug("DISCO_GET_ITEMS")
#        lang_class = self.__lang.get_lang_class_from_node(iq.get_node())
        base_from_jid = unicode(iq.get_from().bare())
        di = DiscoItems()
        if not node:
            # TODO : list accounts
            for account in self.__accounts:
                pass
#                DiscoItem(di, JID(name + "@" + unicode(self.jid)), \
#                          name, str_name)
        return di

    """ Get Version handler """
    def handle_get_version(self, iq):
        self.__logger.debug("GET_VERSION")
        iq = iq.make_result_response()
        q = iq.new_query("jabber:iq:version")
        q.newTextChild(q.ns(), "name", self.__name)
        q.newTextChild(q.ns(), "version", self.version)
        self.stream.send(iq)
        return 1

    """ Send back register form to user """
    def handle_get_register(self, iq):
        self.__logger.debug("GET_REGISTER")
#        lang_class = self.__lang.get_lang_class_from_node(iq.get_node())
        base_from_jid = unicode(iq.get_from().bare())
        to = iq.get_to()
        iq = iq.make_result_response()
        q = iq.new_query("jabber:iq:register")
        if to and to != self.jid:
            self.get_reg_form_init(lang_class, \
                                   self.__accounts.select() # TODO
                                   ).attach_xml(q)
        else:
            self.get_reg_form(lang_class).attach_xml(q)
        self.stream.send(iq)
        return 1

    """ Handle user registration response """
    def handle_set_register(self, iq):
        self.__logger.debug("SET_REGISTER")
        lang_class = self.__lang.get_lang_class_from_node(iq.get_node())
        to = iq.get_to()
        from_jid = iq.get_from()
        base_from_jid = unicode(from_jid.bare())
        remove = iq.xpath_eval("r:query/r:remove", \
                               {"r" : "jabber:iq:register"})
        if remove:
            for name in self.__storage.keys((base_from_jid,)):
                self.__logger.debug("Deleting " + name + " for " + base_from_jid)
                p = Presence(from_jid = name + "@" + unicode(self.jid), \
                             to_jid = from_jid, \
                             stanza_type = "unsubscribe")
                self.stream.send(p)
                p = Presence(from_jid = name + "@" + unicode(self.jid), \
                             to_jid = from_jid, \
                             stanza_type = "unsubscribed")
                self.stream.send(p)
                del self.__storage[(base_from_jid, name)]
            p = Presence(from_jid = self.jid, to_jid = from_jid, \
                         stanza_type = "unsubscribe")
            self.stream.send(p)
            p = Presence(from_jid = self.jid, to_jid = from_jid, \
                         stanza_type = "unsubscribed")
            self.stream.send(p)
            return 1

        query = iq.get_query()
        x = X()
        x.from_xml(query.children)
        # TODO : get info from Xdata
  

    """ Handle presence availability """
    def handle_presence_available(self, stanza):
        self.__logger.debug("PRESENCE_AVAILABLE")
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        name = stanza.get_to().node
        lang_class = self.__lang.get_lang_class_from_node(stanza.get_node())
        show = stanza.get_show()
        self.__logger.debug("SHOW : " + str(show))
        if name:
            self.__logger.debug("TO : " + name + " " + base_from_jid)
        # TODO : if to transport send back available to all user's account
        # else send available presence
        return 1

    """ handle presence unavailability """
    def handle_presence_unavailable(self, stanza):
        self.__logger.debug("PRESENCE_UNAVAILABLE")
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        # TODO : send unavailable to all user's account if target is transport
        # else send unavailable back
        return 1

    """ handle subscribe presence from user """
    def handle_presence_subscribe(self, stanza):
        self.__logger.debug("PRESENCE_SUBSCRIBE")
        p = stanza.make_accept_response()
        self.stream.send(p)
        return 1

    """ handle subscribed presence from user """
    def handle_presence_subscribed(self, stanza):
        self.__logger.debug("PRESENCE_SUBSCRIBED")
        name = stanza.get_to().node
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        # TODO : send presence available to subscribed user
        return 1

    """ handle unsubscribe presence from user """
    def handle_presence_unsubscribe(self, stanza):
        self.__logger.debug("PRESENCE_UNSUBSCRIBE")
        name = stanza.get_to().node
        from_jid = stanza.get_from()
        base_from_jid = unicode(from_jid.bare())
        # TODO : delete from account base
        p = Presence(from_jid = stanza.get_to(), to_jid = from_jid, \
                     stanza_type = "unsubscribe")
        self.stream.send(p)
        p = stanza.make_accept_response()
        self.stream.send(p)
        return 1

    """ handle unsubscribed presence from user """
    def handle_presence_unsubscribed(self, stanza):
        self.__logger.debug("PRESENCE_UNSUBSCRIBED")
        p = Presence(from_jid = stanza.get_to(), \
                     to_jid = stanza.get_from(), \
                     stanza_type = "unavailable")
        self.stream.send(p)
        return 1

    """ Handle new message """
    def handle_message(self, message):
        self.__logger.debug("MESSAGE: " + message.get_body())
        lang_class = self.__lang.get_lang_class_from_node(message.get_node())
        name = message.get_to().node
        base_from_jid = unicode(message.get_from().bare())
        if re.compile("\[PASSWORD\]").search(message.get_subject()) is not None:
# TODO               and self.__storage.has_key((base_from_jid, name)):
#            account = self.__storage[(base_from_jid, name)]
            account.password = message.get_body()
            account.waiting_password_reply = False
            msg = Message(from_jid = account.jid, \
                          to_jid = message.get_from(), \
                          stanza_type = "normal", \
                          subject = lang_class.password_saved_for_session, \
                          body = lang_class.password_saved_for_session)
            self.stream.send(msg)
        return 1

    def handle_tick(self):
        pass
