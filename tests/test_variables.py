import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from test_config import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

class VariableTests(unittest.TestCase):
    "Unit tests for the loadconfig function"
    
    def test_empty(self):
        """"""
        vars_and_commands = LoadConfigFile(
            os.path.join(TEST_FILES_PATH, "empty_variables.yaml"))
        self.assertEquals(vars_and_commands, ({}, {}))

    def test_broken(self):
        """"""
        self.assertRaises(
            RuntimeError,
            LoadConfigFile,
            os.path.join(TEST_FILES_PATH, "broken_variables.yaml"))

    def test_simple(self):
        """"""
        vars, commands = LoadConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))
        
        self.assertEquals(vars['simple'].resolve(vars), 'here')

    def test_replacement(self):
        """"""
        vars, commands = LoadConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(vars['replace'].resolve(vars), 'This is here')

    def test_system(self):
        """"""
        vars, commands = LoadConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(vars['system'].resolve(vars), 'This is a test')

    def test_replace_and_system(self):
        """"""
        vars, commands = LoadConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(
            vars['system+replace'].resolve(vars), 
            'This is here that is there')


if __name__ == "__main__":
    unittest.main()
