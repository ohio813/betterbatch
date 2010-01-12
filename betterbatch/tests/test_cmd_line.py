import unittest
import os


TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

import sys
sys.path.append(os.path.dirname(TEST_PATH))

from cmd_line import *

class CommandLineTests(unittest.TestCase):
    "Unit tests for the loadconfig function"

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
            options.config_file,
            os.path.join(TEST_FILES_PATH, "commands.yaml"))

    def test_GetValidatedOptions(self):
        """"""
        sys.argv = ["prog.py", os.path.join(TEST_FILES_PATH, "commands.yaml")]
        options = GetValidatedOptions()

        self.assertEquals(
            options.config_file,
            os.path.join(TEST_FILES_PATH, "commands.yaml"))


if __name__ == "__main__":
    unittest.main()
