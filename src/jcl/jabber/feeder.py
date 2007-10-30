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

"""FeederComponent with default Feeder and Sender
implementation"""

__revision__ = "$Id: feeder.py,v 1.3 2005/09/18 20:24:07 dax Exp $"

import logging

from jcl.jabber import Handler
from jcl.jabber.component import JCLComponent, AccountManager
from jcl.lang import Lang
import jcl.model as model
from jcl.model import account
from jcl.jabber.command import JCLCommandManager

from pyxmpp.message import Message

class FeederComponent(JCLComponent):
    """
    Implement a feeder sender behavior based on the
    regular interval behavior of JCLComponent
    feed data from given Feeder and send it to user
    through the given Sender.
    """

    def __init__(self,
                 jid,
                 secret,
                 server,
                 port,
                 config,
                 config_file,
                 lang=Lang(),
                 account_manager_class=AccountManager,
                 command_manager_class=JCLCommandManager):
        JCLComponent.__init__(self,
                              jid,
                              secret,
                              server,
                              port,
                              config,
                              config_file,
                              lang=lang,
                              account_manager_class=account_manager_class,
                              command_manager_class=command_manager_class)
        # Define default feeder and sender, can be override
        self.handler = FeederHandler(Feeder(self), Sender(self))
        self.check_interval = 1

        self.__logger = logging.getLogger("jcl.jabber.FeederComponent")
        
    def handle_tick(self):
        """Implement main feed/send behavior"""
        model.db_connect()
        self.handler.handle(\
            None, self.lang.get_default_lang_class(), 
            self.handler.filter(None, 
                                self.lang.get_default_lang_class()))
        model.db_disconnect()



class Feeder(object):
    """Abstract feeder class"""
    def __init__(self, component = None):
        self.component = component

    def feed(self, _account):
        """Feed data for given account"""
        raise NotImplementedError


class Sender(object):
    """Abstract sender class"""
    def __init__(self, component = None):
        self.component = component

    def send(self, to_account, subject, body):
        """Send data (subject and body) to given account"""
        raise NotImplementedError

class MessageSender(Sender):
    """Send data as Jabber Message"""

    def create_message(self, to_account, data):
        """Create message to send"""
        subject, body = data
        return Message(from_jid=to_account.jid,
                       to_jid=to_account.user.jid,
                       subject=subject,
                       body=body)

    def send(self, to_account, data):
        """Implement abstract method from Sender class and send
        data as Jabber message.
        """
        self.component.stream.send(self.create_message(to_account,
                                                       data))

class HeadlineSender(MessageSender):
    """Send data as Jabber Headline"""

    def create_message(self, to_account, data):
        """Create headline to send"""
        subject, body = data
        return Message(from_jid=to_account.jid,
                       to_jid=to_account.user.jid,
                       subject=subject,
                       stanza_type="headline",
                       body=body)

class FeederHandler(Handler):
    """
    Filter (nothing by default) and call sender for each message from
    Feeder.
    """

    def __init__(self, feeder, sender):
        """DefaultFeederHandler constructor"""
        self.feeder = feeder
        self.sender = sender

    def filter(self, stanza, lang_class):
        """
        Filter account to be processed by the handler
        return all accounts.
        """
        accounts = account.get_all_accounts()
        return accounts

    def handle(self, stanza, lang_class, data):
        """
        Apply actions to do on given accounts
        Do nothing by default.
        """
        for _account in data:
            if _account.enabled:
                for data in self.feeder.feed(_account):
                    self.sender.send(_account, data)
        return []

