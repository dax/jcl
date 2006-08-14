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

from jcl.jabber.component import JCLComponent
from jcl.model.account import *

class FeederComponent(JCLComponent):
    def __init__(self,
                 jid,
                 secret,
                 server,
                 port,
                 name = "Generic Feeder Component",
                 disco_category = "gateway",
                 disco_type = "headline",
                 spool_dir = ".",
                 check_interval = 1):
        JCLComponent.__init__(self, \
                              jid, \
                              secret, \
                              server, \
                              port, \
                              name, \
                              disco_category, \
                              disco_type, \
                              spool_dir, \
                              check_interval)
        
    def handle_tick(self):
        for account in Account.select("*"):
            for message in self.__jabber_component.feeder.feed(account):
                self.__jabber_component.sender.send(account, message)



class Feeder(object):
    def __init__(self):
        pass

    def feed(self, account):
        pass


class Sender(object):
    def __init__(self):
        pass

    def send(self, to_account, message):
        pass

