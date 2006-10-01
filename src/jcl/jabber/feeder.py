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

"""FeederComponent with default Feeder and Sender
implementation
"""

__revision__ = "$Id: feeder.py dax $"

import logging

from jcl.jabber.component import JCLComponent
from jcl.model.account import Account

class FeederComponent(JCLComponent):
    """Implement a feeder sender behavior based on the
    regular interval behavior of JCLComponent
    feed data from given Feeder and send it to user
    through the given Sender.
    """
    def __init__(self,
                 jid,
                 secret,
                 server,
                 port):
        JCLComponent.__init__(self, \
                              jid, \
                              secret, \
                              server, \
                              port)
        self.name = "Generic Feeder Component"
        # Define default feeder and sender, can be override
        self.feeder = Feeder()
        self.sender = Sender()
        self.check_interval = 1

        self.__logger = logging.getLogger("jcl.jabber.JCLComponent")
        
    def handle_tick(self):
        """Implement main feed/send behavior        
        """
        for account in Account.select("*"):
            for data in self.feeder.feed(account):
                self.sender.send(account, data)



class Feeder(object):
    """Abstract feeder class
    """
    def __init__(self):
        pass

    def feed(self, account):
        """Feed data for given account
        """
        pass


class Sender(object):
    """Abstract sender class
    """
    def __init__(self):
        pass

    def send(self, to_account, data):
        """Send data to given account
        """
        pass

