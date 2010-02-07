import unittest
import os


import sys
# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(package_root)

from cmd_line import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


class CommandLineTests(unittest.TestCase):
    "Unit tests for the command line processing functionality"

    def test_SettingUpParser(self):
        """"""
        sys.argv = ["prog.py"]
        self.assertRaises(
            SystemExit,
            ParseArguments)

    def test_ParsingVariableOverrides_good(self):
        """"""
        overrides = ParseVariableOverrides(["a=123", "c=<here>"])
        self.assertEquals(overrides['a'], '123')
        self.assertEquals(overrides['c'], '<here>')

    def test_ParsingVariableOverrides_bad(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ParseVariableOverrides,
            ["a"])

    def test_ValidateOptions_missing_yaml(self):
        """"""
        sys.argv = ["prog.py", "blah_blah_not_existing.yaml"]
        options, args = ParseArguments()
        self.assertRaises(
            RuntimeError,
            ValidateOptions, 
                options, args)

    def test_ValidateOptions_too_many_yaml(self):
        """"""
        sys.argv = ["prog.py", "yaml1", "yaml2"]
        options, args = ParseArguments()
        self.assertRaises(
            RuntimeError,
            ValidateOptions,
            options,
            args)

    def test_ValidateOptions_yaml_file_missing(self):
        """"""
        sys.argv = ["prog.py", "yaml1"]
        options, args = ParseArguments()
        self.assertRaises(
            RuntimeError,
            ValidateOptions,
            options,
            args)

    def test_ValidateOptions_yaml_exists(self):
        """"""
        sys.argv = ["prog.py", os.path.join(TEST_FILES_PATH, "commands.yaml")]
        options, args = ParseArguments()
        options = ValidateOptions(options, args)

        self.assertEquals(
            options.script_file,
            os.path.join(TEST_FILES_PATH, "commands.yaml"))

    def test_GetValidatedOptions(self):
        """"""
        sys.argv = ["prog.py", os.path.join(TEST_FILES_PATH, "commands.yaml")]
        options = GetValidatedOptions()

        self.assertEquals(
            options.script_file,
            os.path.join(TEST_FILES_PATH, "commands.yaml"))


if __name__ == "__main__":
    unittest.main()
