"""JCL test module"""
__revision__ = ""

import unittest

from jcl.model.tests import account

def suite():
    suite = unittest.TestSuite()
    suite.addTest(account.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
