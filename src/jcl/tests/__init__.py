"""JCL test module"""
__revision__ = ""

import unittest
import os
import tempfile
import sys

from sqlobject.dbconnection import TheURIOpener
import jcl.model

if sys.platform == "win32":
    DB_DIR = "/c|/temp/"
else:
    DB_DIR = "/tmp/"

class JCLTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.tables = []

    def setUp(self, tables=[]):
        self.tables = tables
        self.db_path = tempfile.mktemp("db", "jcltest", DB_DIR)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        self.db_url = "sqlite://" + self.db_path
        jcl.model.db_connection_str = self.db_url
        jcl.model.db_connect()
        for table in tables:
            table.createTable(ifNotExists=True)
        jcl.model.db_disconnect()

    def tearDown(self):
        jcl.model.db_connect()
        for table in self.tables:
            table.dropTable(ifExists=True)
        del TheURIOpener.cachedURIs[self.db_url]
        jcl.model.hub.threadConnection.close()
        jcl.model.db_disconnect()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

def suite():
    from jcl.tests import lang, runner
    from jcl.jabber import tests as jabber
    from jcl.model import tests as model
    suite = unittest.TestSuite()
    suite.addTest(lang.suite())
    suite.addTest(runner.suite())
    suite.addTest(jabber.suite())
    suite.addTest(model.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
