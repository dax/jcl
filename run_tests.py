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
import logging
import unittest

import sys
sys.path.append("src")
reload(sys)
sys.setdefaultencoding('utf8')
del sys.setdefaultencoding

import jcl.tests

def suite():
    return jcl.tests.suite()

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.CRITICAL)
    
    coverage.erase()
    coverage.start()

    unittest.main(defaultTest='suite')

    coverage.stop()
    coverage.analysis(jcl.jabber.component)
    coverage.analysis(jcl.jabber.feeder)
    coverage.analysis(jcl.lang)
    coverage.analysis(jcl.model.account)

    coverage.report([jcl.jabber.component,
                     jcl.jabber.feeder,
                     jcl.lang,
                     jcl.model.account])

