"""JCL test module"""
__revision__ = ""

import unittest
import os
import tempfile
import sys
import types
import libxml2

from sqlobject.dbconnection import TheURIOpener
import jcl.model

if sys.platform == "win32":
    DB_DIR = "/c|/temp/"
else:
    DB_DIR = "/tmp/"

def is_xml_equal(xml_ref, xml_test, strict=False, test_sibling=True):
    """
    Test for xml structures equality.
    By default (`strict`=False), it only test if `xml_ref` structure is included
    in `xml_test` (ie. if all elements of `xml_ref` exists in `xml_test`).
    if `strict`=True, it also checks if all elements of `xml_test` are in `xml_ref`.
    siblings are tested only if `test_sibling` is True.
    `xml_ref`.
    `xml_ref`: xml node
    `xml_test`: xml node
    `strict`: boolean
    `test_sibling`: boolean
    """
    if (xml_ref is None) ^ (xml_test is None):
        if strict or xml_test is None:
            return False
        else:
            return True
    if (xml_ref is None) and (xml_test is None):
        return True
    if isinstance(xml_ref, types.StringType):
        xml_ref = libxml2.parseDoc(xml_ref)
    if isinstance(xml_test, types.StringType):
        xml_test = libxml2.parseDoc(xml_test)

    def check_equality(test_func, ref, test, strict):
        """
        Check equality with testing function `test_func`. If `strict` is
        False, test xml node equality (without its siblings)
        """
        if not test_func(ref, test):
            if strict:
                return False
            else:
                if test.next is not None:
                    return is_xml_equal(ref, test.next, strict, False)
                else:
                    return False
        else:
            return True

    if not check_equality(lambda ref, test: ref.type == test.type,
                          xml_ref, xml_test, strict):
        return False

    if not check_equality(lambda ref, test: ref.name == test.name,
                          xml_ref, xml_test, strict):
        return False

    if not check_equality(lambda ref, test: ref.ns() == test.ns(),
                          xml_ref, xml_test, strict):
        return False

    def check_attribut_equality(ref, test):
        """
        Check if `ref` xml node attributs are in `test` xml node.
        if `strict` is True, check if `test` attributs are in `ref` xml node.
        """
        if ref.properties is not None:
            if test.properties is None:
                return False
            for attr in ref.properties:
                if ref.prop(attr.name) != test.prop(attr.name):
                    return False
            if strict:
                for attr in test.properties:
                    if ref.prop(attr.name) != test.prop(attr.name):
                        return False
        elif strict and test.properties is not None:
            return False
        return True

    if not check_equality(check_attribut_equality,
                          xml_ref, xml_test, strict):
        return False

    if not check_equality(lambda ref, test: \
                              is_xml_equal(ref.children, test.children, strict),
                          xml_ref, xml_test, strict):
        return False

    if test_sibling:
        if strict:
            new_xml_test = xml_test.next
        else:
            new_xml_test = xml_test
        if not check_equality(lambda ref, test: \
                                  is_xml_equal(ref, test, strict),
                              xml_ref.next, new_xml_test, strict):
            return False
    return True

class JCLTest_TestCase(unittest.TestCase):
    ###########################################################################
    ## Test weak equality
    ###########################################################################
    def test_is_xml_equal_simple_str_node_weak_equal(self):
        """
        Test with only one node (as string) weak equality (inclusion) 2 equals
        structures.
        """
        self.assertTrue(is_xml_equal("<test />", "<test />"))

    def test_is_xml_equal_simple_str_node_weak_different(self):
        """
        Test with only one node (as string) weak equality (inclusion) 2
        differents structures (attribut added).
        """
        self.assertTrue(is_xml_equal("<test />", "<test attr='value' />"))

    def test_is_xml_equal_simple_str_node_weak_different_missing_attribut(self):
        """
        Test with only one node (as string) weak equality (inclusion) 2
        differents structures (attribut missing).
        """
        self.assertFalse(is_xml_equal("<test attr='value' />", "<test />"))

    def test_is_xml_equal_simple_str_node_weak_different_subnode(self):
        """
        Test with only one node (as string) weak equality (inclusion) 2
        differents structures (subnode added).
        """
        self.assertTrue(is_xml_equal("<test />", "<test><subnode /></test>"))

    def test_is_xml_equal_simple_str_node_weak_different_node(self):
        """
        Test with only one node (as string) weak equality (inclusion) 2
        differents nodes.
        """
        self.assertFalse(is_xml_equal("<test />", "<othertest />"))

    def test_is_xml_equal_simple_str_node_weak_different_attribut(self):
        """
        Test with only one node (as string) weak equality (inclusion) 2
        differents structures (different attributs).
        """
        self.assertFalse(is_xml_equal("<test attribut='value' />",
                                      "<test other_attribut='value'/>"))

    def test_is_xml_equal_simple_str_node_weak_different_attribut_value(self):
        """
        Test with only one node (as string) weak equality (inclusion) 2
        differents structures (different attributs values).
        """
        self.assertFalse(is_xml_equal("<test attribut='value' />",
                                      "<test attribut='other_value'/>"))

    def test_is_xml_equal_complex_str_node_weak_equal(self):
        """
        Test 2 complex equal xml structures (weak equality).
        """
        self.assertTrue(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                     """<test attr="value"><subnode subattr="subvalue" /></test>"""))

    def test_is_xml_equal_complex_str_node_weak_different_node_order(self):
        """
        Test 2 complex equal xml structures (weak equality) but with different
        node order.
        """
        self.assertTrue(is_xml_equal("""<test><subnode1 /><subnode2 /></test>""",
                                     """<test><subnode2 /><subnode1 /></test>"""))

    def test_is_xml_equal_complex_str_node_weak_different_attribut_order(self):
        """
        Test 2 complex equal xml structures (weak equality) but with different
        attribut order.
        """
        self.assertTrue(is_xml_equal("""<test attr1='value1' attr2='value2' />""",
                                     """<test attr2='value2' attr1='value1' />"""))

    def test_is_xml_equal_complex_str_node_weak_different(self):
        """
        Test 2 complex not strictly equal (attribut added) xml structures
        (weak equality).
        """
        self.assertTrue(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                     """<test attr="value"><subnode subattr="subvalue" other_subattribut="other_value" /></test>"""))

    def test_is_xml_equal_complex_str_node_weak_different_missing_attribut(self):
        """
        Test 2 complex not strictly equal (missing attribut) xml structures
        (weak equality).
        """
        self.assertFalse(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                     """<test attr="value"><subnode /></test>"""))

    def test_is_xml_equal_complex_str_node_weak_different_subnode(self):
        """
        Test 2 complex not strictly equal (subnode added) xml structures
        (weak equality).
        """
        self.assertTrue(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                     """<test attr="value"><subnode subattr="subvalue"><subsubnode /></subnode></test>"""))

    def test_is_xml_equal_complex_str_node_weak_different_siblingnode(self):
        """
        Test 2 complex not strictly equal (sibling node added) xml structures
        (weak equality).
        """
        self.assertTrue(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                     """<test attr="value"><othersubnode /><subnode subattr="subvalue" /></test>"""))

    ###########################################################################
    ## Test strict equality
    ###########################################################################
    def test_is_xml_equal_simple_str_node_strict_equal(self):
        """
        Test with only one node (as string) strict equality 2 equals
        structures.
        """
        self.assertTrue(is_xml_equal("<test />", "<test />", True))

    def test_is_xml_equal_simple_str_node_strict_different(self):
        """
        Test with only one node (as string) strict equality 2
        differents structures (attribut added).
        """
        self.assertFalse(is_xml_equal("<test />", "<test attr='value' />",
                                      True))

    def test_is_xml_equal_simple_str_node_strict_different(self):
        """
        Test with only one node (as string) strict equality 2
        differents structures (attribut missing).
        """
        self.assertFalse(is_xml_equal("<test attr='value' />", "<test />",
                                      True))

    def test_is_xml_equal_simple_str_node_strict_different_subnode(self):
        """
        Test with only one node (as string) strict equality 2
        differents structures (subnode added).
        """
        self.assertFalse(is_xml_equal("<test />", "<test><subnode /></test>",
                                      True))

    def test_is_xml_equal_simple_str_node_strict_different_node(self):
        """
        Test with only one node (as string) strict equality 2
        differents nodes.
        """
        self.assertFalse(is_xml_equal("<test />", "<othertest />", True))

    def test_is_xml_equal_simple_str_node_strict_different_attribut(self):
        """
        Test with only one node (as string) strict equality 2
        differents structures (different attributs).
        """
        self.assertFalse(is_xml_equal("<test attribut='value' />",
                                      "<test other_attribut='value'/>",
                                      True))

    def test_is_xml_equal_simple_str_node_strict_different_attribut_value(self):
        """
        Test with only one node (as string) strict equality 2
        differents structures (different attributs values).
        """
        self.assertFalse(is_xml_equal("<test attribut='value' />",
                                      "<test attribut='other_value'/>",
                                      True))

    def test_is_xml_equal_complex_str_node_strict_equal(self):
        """
        Test 2 complex equal xml structures (strict equality).
        """
        self.assertTrue(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                     """<test attr="value"><subnode subattr="subvalue" /></test>""",
                                     True))

    def test_is_xml_equal_complex_str_node_strict_different_node_order(self):
        """
        Test 2 complex equal xml structures but with different
        node order.
        """
        self.assertFalse(is_xml_equal("""<test><subnode1 /><subnode2 /></test>""",
                                      """<test><subnode2 /><subnode1 /></test>""",
                                      True))

    def test_is_xml_equal_complex_str_node_strict_different_attribut_order(self):
        """
        Test 2 complex equal xml structures but with different
        attribut order.
        """
        self.assertTrue(is_xml_equal("""<test attr1='value1' attr2='value2' />""",
                                     """<test attr2='value2' attr1='value1' />""",
                                     True))

    def test_is_xml_equal_complex_str_node_strict_different(self):
        """
        Test 2 complex not strictly equal (attribut added) xml structures
        (strict equality).
        """
        self.assertFalse(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                      """<test attr="value"><subnode subattr="subvalue" other_subattribut="other_value" /></test>""",
                                      True))

    def test_is_xml_equal_complex_str_node_strict_different_missing_attribut(self):
        """
        Test 2 complex not strictly equal (missing attribut) xml structures
        (strict equality).
        """
        self.assertFalse(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                      """<test attr="value"><subnode /></test>""",
                                      True))

    def test_is_xml_equal_complex_str_node_strict_different_subnode(self):
        """
        Test 2 complex not strictly equal (subnode added) xml structures
        (strict equality).
        """
        self.assertFalse(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                      """<test attr="value"><subnode subattr="subvalue"><subsubnode /></subnode></test>""",
                                      True))

    def test_is_xml_equal_complex_str_node_strict_different_siblingnode(self):
        """
        Test 2 complex not strictly equal (sibling node added) xml structures
        (strict equality).
        """
        self.assertFalse(is_xml_equal("""<test attr="value"><subnode subattr="subvalue" /></test>""",
                                      """<test attr="value"><othersubnode /><subnode subattr="subvalue" /></test>""",
                                      True))

class JCLTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.tables = []

    def setUp(self, tables=[]):
        self.tables = tables
        self.db_path = tempfile.mktemp(".db", "jcltest", DB_DIR)
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        self.db_url = "sqlite://" + self.db_path #+ "?debug=True"
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
    test_suite = unittest.TestSuite()
    test_suite.addTest(lang.suite())
    test_suite.addTest(runner.suite())
    test_suite.addTest(jabber.suite())
    test_suite.addTest(model.suite())
    test_suite.addTest(unittest.makeSuite(JCLTest_TestCase, 'test'))
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
