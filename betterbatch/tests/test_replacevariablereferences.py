from __future__ import absolute_import

import unittest
import os
import sys

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

# ensure that the package root is on the path
PACKAGE_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.append(PACKAGE_ROOT)

from betterbatch.parsescript import *


class VarReplacementTests(unittest.TestCase):
    "Perform some simple tests"

    def setUp(self):
        self.vars = {}
        self.vars['var'] = "value"
        self.vars['var2'] = "value<here>"

    def test_no_var(self):
        replaced = ReplaceVariableReferences("test string", {})
        self.assertEquals(replaced, "test string")

    def test_escaped_gt(self):
        replaced = ReplaceVariableReferences(">>test string>>", {})
        self.assertEquals(replaced, ">test string>")

    def test_escaped_lt(self):
        replaced = ReplaceVariableReferences("<<test string<<", {})
        self.assertEquals(replaced, "<test string<")

    def test_escaped_both(self):
        replaced = ReplaceVariableReferences("<<test string>>", {})
        self.assertEquals(replaced, "<test string>")

    def test_escaped_lt_next_to_var(self):
        replaced = ReplaceVariableReferences("<<<var>", self.vars)
        self.assertEquals(replaced, "<value")

    def test_escaped_gt_next_to_var(self):
        replaced = ReplaceVariableReferences("<var>>>", self.vars)
        self.assertEquals(replaced, "value>")

    def test_escaped_both_var(self):
        replaced = ReplaceVariableReferences("<<<var>>>", self.vars)
        self.assertEquals(replaced, "<value>")

    def test_escaped_both_non_var(self):
        replaced = ReplaceVariableReferences("<<var>>", self.vars)
        self.assertEquals(replaced, "<var>")

    #def test_None(self):
    #    replaced = ReplaceVariableReferences(None, {})
    #    self.assertEquals(replaced, None)

    def test_empty_string(self):
        replaced = ReplaceVariableReferences('', {})
        self.assertEquals(replaced, '')

    #def test_numeric_string(self):
    #    self.assertRaises(
    #        NumericVarNotAllowedError,
    #        ReplaceVariableReferences,
    #        1000**1000, {})
    #    self.assertRaises(
    #        NumericVarNotAllowedError,
    #        ReplaceVariableReferences,
    #        1, {})
    #    self.assertRaises(
    #        NumericVarNotAllowedError,
    #        ReplaceVariableReferences,
    #        1.5, {})

    #def test_non_string(self):
    #    replaced = ReplaceVariableReferences([1,2,3], {})
    #    self.assertEquals(replaced, [1,2,3])

    def test_error_in_replaced_var(self):
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,"<var2>", self.vars)





    # check parsing a value with 1 var
    # check parsing a value which is only a variable reference
    # check that > and < work OK (begining, middle and end of the string)

if __name__ == "__main__":
    unittest.main()
