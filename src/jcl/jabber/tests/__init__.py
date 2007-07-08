"""JCL test module"""
__revision__ = ""

import unittest

from jcl.jabber.tests import component, feeder, command, message, presence

def suite():
    suite = unittest.TestSuite()
    suite.addTest(component.suite())
    suite.addTest(feeder.suite())
    suite.addTest(command.suite())
    suite.addTest(message.suite())
    suite.addTest(presence.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
