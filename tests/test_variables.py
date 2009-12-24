import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from test_config import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

# how to raise a yaml.parser.ParserError???

class VariableTests(unittest.TestCase):
    "Unit tests for the loadconfig function"
    
    def test_empty(self):
        """"""
        vars_and_commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "empty_variables.yaml"))
        self.assertEquals(vars_and_commands, ({}, {}))

    def test_broken(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ParseConfigFile,
            os.path.join(TEST_FILES_PATH, "broken_variables.yaml"))

    def test_simple(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))
        
        self.assertEquals(vars['simple'].resolve(vars), 'here')

    def test_replacement(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(vars['replace'].resolve(vars), 'This is here')

    def test_system(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(vars['system'].resolve(vars), 'This is a test')

    def test_replace_and_system(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(
            vars['system+replace'].resolve(vars), 
            'This is here that is there')

    def test_repr(self):
        """"""
        var = Variable('my_var', "German - Germany", "test_file")
        self.assertEquals(repr(var), "<var:'my_var'>")

    def test_system_variable_error(self):
        """"""
        var = Variable('my_var', "(system) failure", "no_file")
        self.assertRaises(RuntimeError, var.resolve, {})


if __name__ == "__main__":
    unittest.main()
