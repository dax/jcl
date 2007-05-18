"""JCL test module"""
__revision__ = ""

import unittest

from jcl.tests import lang, runner
from jcl.jabber import tests as jabber
from jcl.model import tests as model

def suite():
    suite = unittest.TestSuite()
    suite.addTest(lang.suite())
    suite.addTest(runner.suite())
    suite.addTest(jabber.suite())
    suite.addTest(model.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
