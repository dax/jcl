"""JCL test module"""
__revision__ = ""

import unittest
import threading
import os
import tempfile
import sys

from sqlobject import SQLObject
from sqlobject.col import StringCol
from sqlobject.dbconnection import TheURIOpener

import jcl.model as model

if sys.platform == "win32":
    DB_DIR = "/c|/temp/"
else:
    DB_DIR = "/tmp/"

class MyMockSQLObject(SQLObject):
    _connection = model.hub
    string_attr = StringCol()

class ModelModule_TestCase(unittest.TestCase):
    def setUp(self):
        self.db_path = tempfile.mktemp("db", "jcltest", DB_DIR)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        self.db_url = "sqlite://" + self.db_path
        model.db_connection_str = self.db_url
        model.db_connect()
        MyMockSQLObject.createTable(ifNotExists=True)
        model.db_disconnect()

    def tearDown(self):
        model.db_connect()
        MyMockSQLObject.dropTable(ifExists=True)
        del TheURIOpener.cachedURIs[self.db_url]
        model.hub.threadConnection.close()
        model.db_disconnect()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_multiple_db_connection(self):
        def create_account_thread():
            for i in xrange(100):
                string_attr = "obj2" + str(i)
                model.db_connect()
                obj = MyMockSQLObject(string_attr=string_attr)
                model.db_disconnect()
                model.db_connect()
                obj2 = MyMockSQLObject.select(MyMockSQLObject.q.string_attr == string_attr)
                model.db_disconnect()
                self.assertEquals(obj, obj2[0])
        timer_thread = threading.Thread(target=create_account_thread,
                                        name="CreateAccountThread")
        timer_thread.start()
        for i in xrange(100):
            string_attr = "obj1" + str(i)
            model.db_connect()
            obj = MyMockSQLObject(string_attr=string_attr)
            model.db_disconnect()
            model.db_connect()
            obj2 = MyMockSQLObject.select(MyMockSQLObject.q.string_attr == string_attr)
            model.db_disconnect()
            self.assertEquals(obj, obj2[0])
        timer_thread.join(2)
        threads = threading.enumerate()
        self.assertEquals(len(threads), 1)
        model.db_connect()
        objs = MyMockSQLObject.select()
        self.assertEquals(objs.count(), 200)
        model.db_disconnect()

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ModelModule_TestCase, 'test'))
    from jcl.model.tests import account
    suite.addTest(account.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
