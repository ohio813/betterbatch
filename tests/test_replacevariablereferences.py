import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from test_config import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

class VarReplacementTests(unittest.TestCase):
    "Perform some simple tests"
    
    def setUp(self):
        self.vars = {}
        self.vars['var'] = Variable('var', "value", 'testing')
        self.vars['var2'] = Variable('var2', "value<here>", 'testing')

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

    def test_None(self):
        replaced = ReplaceVariableReferences(None, {})
        self.assertEquals(replaced, None)

    def test_empty_string(self):
        replaced = ReplaceVariableReferences('', {})
        self.assertEquals(replaced, '')

    def test_numeric_string(self):
        self.assertRaises(
            NumericVarNotAllowedError, 
            ReplaceVariableReferences,
            1000**1000, {})
        self.assertRaises(
            NumericVarNotAllowedError, 
            ReplaceVariableReferences,
            1, {})
        self.assertRaises(
            NumericVarNotAllowedError, 
            ReplaceVariableReferences,
            1.5, {})

    def test_non_string(self):
        replaced = ReplaceVariableReferences([1,2,3], {})
        self.assertEquals(replaced, [1,2,3])

    def test_error_in_replaced_var(self):
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,"<var2>", self.vars)
        




    # check parsing a value with 1 var
    # check parsing a value which is only a variable reference
    # check that > and < work OK (begining, middle and end of the string)
