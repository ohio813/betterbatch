from __future__ import absolute_import

import unittest
import os
import sys

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

# ensure that the package root is on the path
PACKAGE_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.append(PACKAGE_ROOT)

from betterbatch import cmd_line
from betterbatch.cmd_line import *


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

    def test_defultcolor_options(self):
        """"""
        sys.argv = ["prog.py", os.path.join(TEST_FILES_PATH, "commands.yaml")]
        options = GetValidatedOptions()

        self.assertEquals(options.colored_output, USE_COLORED_OUTPUT)
        self.assertEquals(options.no_color, False)

    def test_force_no_color(self):
        """"""
        sys.argv = [
            "prog.py",
            os.path.join(TEST_FILES_PATH, "commands.yaml"),
            "--no-color"]
        options = GetValidatedOptions()

        self.assertEquals(options.colored_output, False)
        self.assertEquals(options.no_color, True)


    def test_different_platforms(self):
        """"""
        old_plat = sys.platform
        sys.platform = "win32"
        cmd_win32 = reload(cmd_line)
        if hasattr(cmd_line, 'colorama'):
            self.assertEquals(cmd_win32.USE_COLORED_OUTPUT, True)
        else:
            self.assertEquals(cmd_win32.USE_COLORED_OUTPUT, False)
        sys.platform = "unix"
        cmd_unix = reload(cmd_line)
        self.assertEquals(cmd_unix.USE_COLORED_OUTPUT, True)
        sys.platform = old_plat



if __name__ == "__main__":
    unittest.main()
