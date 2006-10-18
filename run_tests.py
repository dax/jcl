# -*- coding: utf-8 -*-
##
## run_tests.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Wed Aug  9 21:37:35 2006 David Rousselie
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

import coverage
coverage.erase()
coverage.start()
import logging
import unittest
from test import test_support

import sys
sys.path.append("src")
reload(sys)
sys.setdefaultencoding('utf8')
del sys.setdefaultencoding

import tests
from tests.jcl.jabber.test_component import *
from tests.jcl.jabber.test_feeder import *

import jcl

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    
    component_suite = unittest.makeSuite(JCLComponent_TestCase, "test")
    feeder_component_suite = unittest.makeSuite(FeederComponent_TestCase, "test")
    feeder_suite = unittest.makeSuite(Feeder_TestCase, "test")
    sender_suite = unittest.makeSuite(Sender_TestCase, "test")
    jcl_suite = unittest.TestSuite()
#    jcl_suite.addTest(FeederComponent_TestCase('test_handle_get_version'))
#    jcl_suite.addTest(FeederComponent_TestCase('test_handle_presence_available_to_account_live_password'))
#    jcl_suite = unittest.TestSuite((feeder_component_suite))
#    jcl_suite = unittest.TestSuite((component_suite))
    jcl_suite = unittest.TestSuite((component_suite,
                                    feeder_component_suite,
                                    feeder_suite,
                                    sender_suite))
    test_support.run_suite(jcl_suite)


coverage.stop()
coverage.analysis(jcl.jabber.component)
coverage.analysis(jcl.jabber.feeder)
coverage.report([jcl.jabber.component, jcl.jabber.feeder])

