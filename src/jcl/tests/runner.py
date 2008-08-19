##
## runner.py
## Login : David Rousselie <dax@happycoders.org>
## Started on  Fri May 18 13:43:37 2007 David Rousselie
## $Id$
##
## Copyright (C) 2007 David Rousselie
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

import unittest
import sys
import os
import tempfile
import logging

from sqlobject import *

import jcl
from jcl.runner import JCLRunner
import jcl.model as model
from jcl.model.account import Account, PresenceAccount, User, LegacyJID
from jcl.jabber.component import JCLComponent

if sys.platform == "win32":
    DB_DIR = "/c|/temp/"
else:
    DB_DIR = "/tmp/"

class JCLRunner_TestCase(unittest.TestCase):
    def setUp(self):
        self.runner = JCLRunner("JCL", jcl.version)

    def tearDown(self):
        self.runner = None
        sys.argv = [""]

    def test_configure_default(self):
        self.runner.configure()
        self.assertEquals(self.runner.config_file, "jcl.conf")
        self.assertEquals(self.runner.server, "localhost")
        self.assertEquals(self.runner.port, 5347)
        self.assertEquals(self.runner.secret, "secret")
        self.assertEquals(self.runner.service_jid, "jcl.localhost")
        self.assertEquals(self.runner.language, "en")
        self.assertEquals(self.runner.db_url, "sqlite:///var/spool/jabber/jcl.db")
        self.assertEquals(self.runner.pid_file, "/var/run/jabber/jcl.pid")
        self.assertFalse(self.runner.debug)
        self.assertEquals(self.runner.logger.getEffectiveLevel(),
                          logging.CRITICAL)

    def test_configure_configfile(self):
        self.runner.config_file = "src/jcl/tests/jcl.conf"
        self.runner.configure()
        self.assertEquals(self.runner.server, "test_localhost")
        self.assertEquals(self.runner.port, 42)
        self.assertEquals(self.runner.secret, "test_secret")
        self.assertEquals(self.runner.service_jid, "test_jcl.localhost")
        self.assertEquals(self.runner.language, "test_en")
        self.assertEquals(self.runner.db_url, "test_sqlite://root@localhost/var/spool/jabber/test_jcl.db")
        self.assertEquals(self.runner.pid_file, "/var/run/jabber/test_jcl.pid")
        self.assertFalse(self.runner.debug)
        self.assertEquals(self.runner.logger.getEffectiveLevel(),
                          logging.CRITICAL)

    def test_configure_uncomplete_configfile(self):
        self.runner.config_file = "src/jcl/tests/uncomplete_jcl.conf"
        self.runner.configure()
        self.assertEquals(self.runner.server, "test_localhost")
        self.assertEquals(self.runner.port, 42)
        self.assertEquals(self.runner.secret, "test_secret")
        self.assertEquals(self.runner.service_jid, "test_jcl.localhost")
        self.assertEquals(self.runner.language, "test_en")
        self.assertEquals(self.runner.db_url, "test_sqlite://root@localhost/var/spool/jabber/test_jcl.db")
        # pid_file is not in uncmplete_jcl.conf, must be default value
        self.assertEquals(self.runner.pid_file, "/var/run/jabber/jcl.pid")
        self.assertFalse(self.runner.debug)
        self.assertEquals(self.runner.logger.getEffectiveLevel(),
                          logging.CRITICAL)

    def test_configure_commandline_shortopt(self):
        sys.argv = ["", "-c", "src/jcl/test/jcl.conf",
                    "-S", "test2_localhost",
                    "-P", "43",
                    "-s", "test2_secret",
                    "-j", "test2_jcl.localhost",
                    "-l", "test2_en",
                    "-u", "sqlite:///tmp/test_jcl.db",
                    "-p", "/tmp/test_jcl.pid"]
        self.runner.configure()
        self.assertEquals(self.runner.server, "test2_localhost")
        self.assertEquals(self.runner.port, 43)
        self.assertEquals(self.runner.secret, "test2_secret")
        self.assertEquals(self.runner.service_jid, "test2_jcl.localhost")
        self.assertEquals(self.runner.language, "test2_en")
        self.assertEquals(self.runner.db_url, "sqlite:///tmp/test_jcl.db")
        self.assertEquals(self.runner.pid_file, "/tmp/test_jcl.pid")
        self.assertFalse(self.runner.debug)
        self.assertEquals(self.runner.logger.getEffectiveLevel(),
                          logging.CRITICAL)

    def test_configure_commandline_longopt(self):
        sys.argv = ["", "--config-file", "src/jcl/tests/jcl.conf",
                    "--server", "test2_localhost",
                    "--port", "43",
                    "--secret", "test2_secret",
                    "--service-jid", "test2_jcl.localhost",
                    "--language", "test2_en",
                    "--db-url", "sqlite:///tmp/test_jcl.db",
                    "--pid-file", "/tmp/test_jcl.pid"]
        self.runner.configure()
        self.assertEquals(self.runner.server, "test2_localhost")
        self.assertEquals(self.runner.port, 43)
        self.assertEquals(self.runner.secret, "test2_secret")
        self.assertEquals(self.runner.service_jid, "test2_jcl.localhost")
        self.assertEquals(self.runner.language, "test2_en")
        self.assertEquals(self.runner.db_url, "sqlite:///tmp/test_jcl.db")
        self.assertEquals(self.runner.pid_file, "/tmp/test_jcl.pid")
        self.assertFalse(self.runner.debug)
        self.assertEquals(self.runner.logger.getEffectiveLevel(),
                          logging.CRITICAL)

    def test_configure_commandline_shortopts_configfile(self):
        sys.argv = ["", "-c", "src/jcl/tests/jcl.conf"]
        self.runner.configure()
        self.assertEquals(self.runner.server, "test_localhost")
        self.assertEquals(self.runner.port, 42)
        self.assertEquals(self.runner.secret, "test_secret")
        self.assertEquals(self.runner.service_jid, "test_jcl.localhost")
        self.assertEquals(self.runner.language, "test_en")
        self.assertEquals(self.runner.db_url, "test_sqlite://root@localhost/var/spool/jabber/test_jcl.db")
        self.assertEquals(self.runner.pid_file, "/var/run/jabber/test_jcl.pid")
        self.assertFalse(self.runner.debug)
        self.assertEquals(self.runner.logger.getEffectiveLevel(),
                          logging.CRITICAL)

    def test_configure_commandline_longopts_configfile(self):
        sys.argv = ["", "--config-file", "src/jcl/tests/jcl.conf"]
        self.runner.configure()
        self.assertEquals(self.runner.server, "test_localhost")
        self.assertEquals(self.runner.port, 42)
        self.assertEquals(self.runner.secret, "test_secret")
        self.assertEquals(self.runner.service_jid, "test_jcl.localhost")
        self.assertEquals(self.runner.language, "test_en")
        self.assertEquals(self.runner.db_url, "test_sqlite://root@localhost/var/spool/jabber/test_jcl.db")
        self.assertEquals(self.runner.pid_file, "/var/run/jabber/test_jcl.pid")
        self.assertFalse(self.runner.debug)
        self.assertEquals(self.runner.logger.getEffectiveLevel(),
                          logging.CRITICAL)

    def test_configure_commandline_short_debug(self):
        sys.argv = ["", "-d"]
        old_debug_func = self.runner.logger.debug
        old_info_func = self.runner.logger.debug
        try:
            self.runner.logger.debug = lambda msg: None
            self.runner.logger.info = lambda msg: None
            self.runner.configure()
            self.assertTrue(self.runner.debug)
            self.assertEquals(self.runner.logger.getEffectiveLevel(),
                              logging.DEBUG)
        finally:
            self.runner.logger.debug = old_debug_func
            self.runner.logger.info = old_info_func

    def test_configure_commandline_long_debug(self):
        sys.argv = ["", "--debug"]
        old_debug_func = self.runner.logger.debug
        old_info_func = self.runner.logger.debug
        try:
            self.runner.logger.debug = lambda msg: None
            self.runner.logger.info = lambda msg: None
            self.runner.configure()
            self.assertTrue(self.runner.debug)
            self.assertEquals(self.runner.logger.getEffectiveLevel(),
                              logging.DEBUG)
        finally:
            self.runner.logger.debug = old_debug_func
            self.runner.logger.info = old_info_func

    def test_setup_pidfile(self):
        try:
            self.runner.pid_file = "/tmp/jcl.pid"
            self.runner.setup_pidfile()
            pidfile = open("/tmp/jcl.pid", "r")
            pid = int(pidfile.read())
            pidfile.close()
            self.assertEquals(pid, os.getpid())
        finally:
            os.remove("/tmp/jcl.pid")

    def test_run(self):
        """Test if run method of JCLComponent is executed"""
        self.has_run_func = False
        def run_func(component_self):
            self.has_run_func = True
            return (False, 0)

        self.runner.pid_file = "/tmp/jcl.pid"
        db_path = tempfile.mktemp("db", "jcltest", DB_DIR)
        db_url = "sqlite://" + db_path
        self.runner.db_url = db_url
        self.runner.config = None
        old_run_func = JCLComponent.run
        JCLComponent.run = run_func
        try:
            self.runner.run()
        finally:
            JCLComponent.run = old_run_func
        self.assertTrue(self.has_run_func)
        Account.dropTable()
        PresenceAccount.dropTable()
        User.dropTable()
        LegacyJID.dropTable()
        model.db_disconnect()
        os.unlink(db_path)
        self.assertFalse(os.access("/tmp/jcl.pid", os.F_OK))

    def test__run(self):
        self.runner.pid_file = "/tmp/jcl.pid"
        db_path = tempfile.mktemp("db", "jcltest", DB_DIR)
        db_url = "sqlite://" + db_path
        self.runner.db_url = db_url
        def do_nothing():
            return (False, 0)
        self.runner._run(do_nothing)
        model.db_connect()
        # dropTable should succeed because tables should exist
        Account.dropTable()
        PresenceAccount.dropTable()
        User.dropTable()
        LegacyJID.dropTable()
        model.db_disconnect()
        os.unlink(db_path)
        self.assertFalse(os.access("/tmp/jcl.pid", os.F_OK))

    def test__run_restart(self):
        self.runner.pid_file = "/tmp/jcl.pid"
        db_path = tempfile.mktemp("db", "jcltest", DB_DIR)
        db_url = "sqlite://" + db_path
        self.runner.db_url = db_url
        self.i = 0
        def restart(self):
            self.i += 1
            yield (True, 0)
            self.i += 1
            yield (False, 0)
            self.i += 1
        restart_generator = restart(self)
        self.runner._run(lambda : restart_generator.next())
        model.db_connect()
        # dropTable should succeed because tables should exist
        Account.dropTable()
        PresenceAccount.dropTable()
        User.dropTable()
        LegacyJID.dropTable()
        model.db_disconnect()
        os.unlink(db_path)
        self.assertFalse(os.access("/tmp/jcl.pid", os.F_OK))
        self.assertEquals(self.i, 2)

    def test__get_help(self):
        self.assertNotEquals(self.runner._get_help(), None)

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(JCLRunner_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
