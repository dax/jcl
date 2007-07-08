"""JCL test module"""
__revision__ = ""

import unittest
import threading
import os
import sys

from sqlobject import SQLObject
from sqlobject.col import StringCol
from sqlobject.dbconnection import TheURIOpener

import jcl.model as model

if sys.platform == "win32":
   DB_PATH = "/c|/temp/jcl_test.db"
else:
   DB_PATH = "/tmp/jcl_test.db"
DB_URL = DB_PATH# + "?debug=1&debugThreading=1"

class MockSQLObject(SQLObject):
    _connection = model.hub
    string_attr = StringCol()

class ModelModule_TestCase(unittest.TestCase):
    def setUp(self):
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        model.db_connection_str = 'sqlite://' + DB_URL
        model.db_connect()
        MockSQLObject.createTable(ifNotExists=True)
        model.db_disconnect()

    def tearDown(self):
        model.db_connect()
        MockSQLObject.dropTable(ifExists=True)
        del TheURIOpener.cachedURIs['sqlite://' + DB_URL]
        model.hub.threadConnection.close()
        model.db_disconnect()
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)

    def test_multiple_db_connection(self):
        def create_account_thread():
            model.db_connect()
            obj21 = MockSQLObject(string_attr="obj21")
            obj22 = MockSQLObject(string_attr="obj22")
            model.db_disconnect()

        model.db_connect()
        timer_thread = threading.Thread(target=create_account_thread,
                                        name="CreateAccountThread")
        timer_thread.start()
        obj11 = MockSQLObject(string_attr="obj11")
        obj12 = MockSQLObject(string_attr="obj12")
        timer_thread.join(2)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        objs = MockSQLObject.select()
        self.assertEquals(objs.count(), 4)
        model.db_disconnect()

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ModelModule_TestCase, 'test'))
    from jcl.model.tests import account
    suite.addTest(account.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
