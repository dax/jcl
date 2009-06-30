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

import sys
sys.path.append("src")
reload(sys)
sys.setdefaultencoding('utf8')
del sys.setdefaultencoding

import jcl.tests
import jcl.jabber.tests

def suite():
    return jcl.tests.suite()

if __name__ == '__main__':
    class MyTestProgram(unittest.TestProgram):
        def runTests(self):
            """run tests but do not exit after"""
	    self.testRunner = unittest.TextTestRunner(verbosity=self.verbosity)
            self.testRunner.run(self.test)

    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.CRITICAL)
    try:
        print "Trying to launch test with testoob"
        import testoob
        testoob.main(defaultTest='suite')
    except ImportError:
        print "Falling back to standard unittest"
        MyTestProgram(defaultTest='suite')

coverage.report(["src/jcl/__init__.py",
                 "src/jcl/lang.py",
                 "src/jcl/runner.py",
                 "src/jcl/error.py",
                 "src/jcl/jabber/__init__.py",
                 "src/jcl/jabber/component.py",
                 "src/jcl/jabber/command.py",
                 "src/jcl/jabber/feeder.py",
                 "src/jcl/jabber/message.py",
                 "src/jcl/jabber/presence.py",
                 "src/jcl/jabber/disco.py",
                 "src/jcl/jabber/register.py",
                 "src/jcl/model/__init__.py",
                 "src/jcl/model/account.py"])
