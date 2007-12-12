"""JCL test module"""
__revision__ = ""

import unittest

import jcl.jabber as jabber

from jcl.jabber.tests import component, feeder, command, message, presence

class HandlerType1:
    pass

class HandlerType2:
    pass

class HandlerType3:
    pass

class JabberModule_TestCase(unittest.TestCase):
    def test_replace_handlers(self):
        handlers = [[HandlerType1(), HandlerType2(), HandlerType1()],
                    [HandlerType2(), HandlerType1(), HandlerType2()]]
        jabber.replace_handlers(handlers, HandlerType2, HandlerType3())
        self.assertEquals(handlers[0][0].__class__.__name__, "HandlerType1")
        self.assertEquals(handlers[0][1].__class__.__name__, "HandlerType3")
        self.assertEquals(handlers[0][2].__class__.__name__, "HandlerType1")
        self.assertEquals(handlers[1][0].__class__.__name__, "HandlerType3")
        self.assertEquals(handlers[1][1].__class__.__name__, "HandlerType1")
        self.assertEquals(handlers[1][2].__class__.__name__, "HandlerType3")

def suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(JabberModule_TestCase, 'test'))
    test_suite.addTest(component.suite())
    test_suite.addTest(feeder.suite())
    test_suite.addTest(command.suite())
    test_suite.addTest(message.suite())
    test_suite.addTest(presence.suite())
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
