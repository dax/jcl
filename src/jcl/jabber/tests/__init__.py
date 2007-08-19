"""JCL test module"""
__revision__ = ""

import unittest

from jcl.jabber.tests import component, feeder, command, message, presence

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(component.suite())
    test_suite.addTest(feeder.suite())
    test_suite.addTest(command.suite())
    test_suite.addTest(message.suite())
    test_suite.addTest(presence.suite())
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
