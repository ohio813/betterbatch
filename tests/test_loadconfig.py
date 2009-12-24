import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from test_config import ParseConfigFile
from test_config import ErrorCollection

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

class LoadConfigTests(unittest.TestCase):
    "Unit tests for the loadconfig function"
    
    def test_emtpy_file(self):
        """"""
        vars_and_commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "empty.yaml"))
        self.assertEquals(vars_and_commands, ({}, {}))

    def test_can_load_relative_include(self):
        """Should be able to load an include relative to the current config
        
        The original code was only looking relative to the users current 
        directory - so if running from another directory - config files were
        not found.
        """        
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "test_rel_include.yaml"))
        self.assertEquals(vars['test'].value, "Hello World")


    def test_missing_file(self):
        """"""
        
        self.assertRaises(
            ErrorCollection,
            ParseConfigFile,
            os.path.join(TEST_FILES_PATH, "missing.yaml"))

    def test_missing_include(self):
        """"""
        
        self.assertRaises(
            ErrorCollection,
            ParseConfigFile,
            os.path.join(TEST_FILES_PATH, "missing_include.yaml"))


    def test_variables_as_list(self):
        """"""
        
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "variables_as_list.yaml"))
        self.assertEquals(vars['test'].value, "Hello World")

        
    def test_numeric_variable(self):
        """"""
        
        try:
            ParseConfigFile(os.path.join(TEST_FILES_PATH, "number_variables.yaml"))
        except ErrorCollection, e:
            self.assertEquals(len(e.errors), 2)
            

    def test_empty_include_section(self):
        """"""        
        ParseConfigFile(os.path.join(TEST_FILES_PATH, "empty_includes.yaml"))
        ParseConfigFile(os.path.join(TEST_FILES_PATH, "empty_includes2.yaml"))

    def test_overlapping_variable(self):
        """"""
        
        self.assertRaises(
            RuntimeError,
            ParseConfigFile,
            os.path.join(TEST_FILES_PATH, "overlapping_variables.yaml"))




if __name__ == "__main__":
    unittest.main()
