import unittest
import os

import sys
# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(package_root)

from parsescript import LoadAndCheckFile
from parsescript import ErrorCollection
from parsescript import PopulateVariables

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


class LoadConfigTests(unittest.TestCase):
    "Unit tests for the loadconfig function"

    def test_emtpy_file(self):
        """"""
        path = os.path.join(TEST_FILES_PATH, "empty.yaml")
        vars = PopulateVariables(path)
        steps = LoadAndCheckFile(path, vars)
        self.assertEquals(steps, [])

    def test_can_load_relative_include(self):
        """Should be able to load an include relative to the current config

        The original code was only looking relative to the users current
        directory - so if running from another directory - config files were
        not found.
        """
        path = os.path.join(TEST_FILES_PATH, "test_rel_include.yaml")
        vars = PopulateVariables(path)
        commands = LoadAndCheckFile(path, vars)
        self.assertEquals(commands[0].value, "Hello World")

    def test_missing_file(self):
        """"""
        
        path = os.path.join(TEST_FILES_PATH, "missing.yaml")
        vars = PopulateVariables(path)

        self.assertRaises(
            RuntimeError,
            LoadAndCheckFile,
            path, vars)

    def test_missing_include(self):
        """"""

        path = os.path.join(TEST_FILES_PATH, "missing_include.yaml")
        vars = PopulateVariables(path)
        self.assertRaises(
            RuntimeError,
            LoadAndCheckFile,
            path, vars)

    def test_variables_as_list(self):
        """"""

        path = os.path.join(TEST_FILES_PATH, "variables_as_list.yaml")
        vars = PopulateVariables(path)
        commands = LoadAndCheckFile(path, vars)
        commands[0].execute(vars)
        
        self.assertEquals(vars['test'].value, "Hello World")

    def test_numeric_variable(self):
        """"""

        try:
            path = os.path.join(TEST_FILES_PATH, "number_variables.yaml")
            vars = PopulateVariables(path)
            LoadAndCheckFile(path, vars)
        except ErrorCollection, e:
            self.assertEquals(len(e.errors), 2)

    def test_empty_include_section(self):
        """"""
        path = os.path.join(TEST_FILES_PATH, "empty_includes.yaml")
        vars = PopulateVariables(path)
        self.assertRaises(
            RuntimeError,
            LoadAndCheckFile, path, vars)
        path = os.path.join(TEST_FILES_PATH, "empty_includes2.yaml")
        self.assertRaises(
            RuntimeError,
            LoadAndCheckFile,
                path, vars)

    def test_broken_variable_block(self):
        """"""

        path = os.path.join(TEST_FILES_PATH, "variable_block_broken.yaml")
        vars = PopulateVariables(path)
        self.assertRaises(
            RuntimeError,
            LoadAndCheckFile,
                path, vars)



if __name__ == "__main__":
    unittest.main()
