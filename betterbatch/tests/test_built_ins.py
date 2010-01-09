import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from built_in_commands import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


class BuiltInCommandsTests(unittest.TestCase):
    "Unit tests for the loadconfig function"

    def test_PathExists_true(self):
        """"""

        self.assertEquals(
            PathExists(__file__)[0], 0)

    def test_PathExists_false(self):
        """"""

        self.assertRaises(
            RuntimeError,
            PathExists,
            "does not exist.blah")

    def test_PathNotExists_true(self):
        """"""

        self.assertEquals(
            PathNotExists("does not exist.blah")[0], 0)

    def test_PathNotExists_false(self):
        """"""

        self.assertRaises(
            RuntimeError,
            PathNotExists,
            __file__)


    def test_count_passes(self):
        """"""
        test_file = os.path.join(TEST_PATH, "run_tests.py")
        VerifyFileCount(test_file, [1])
        VerifyFileCount(test_file, 1)
        VerifyFileCount(test_file, ">0")
        VerifyFileCount(test_file, "<2")
        VerifyFileCount(test_file, ">=1")
        VerifyFileCount(test_file, "<=1")
        VerifyFileCount(test_file, "=1")

    def test_count_fail(self):
        """"""
        self.assertRaises(
            RuntimeError,
            VerifyFileCount,
            "cmd_line.py",
            12)

    def test_missing_count(self):
        self.assertRaises(
            RuntimeError,
            VerifyFileCount,
            "cmd_line.py")

    def test_SystemCommand_ui(self):
        SystemCommand("echo here", ['ui'])

    def test_SystemCommand_no_ui(self):
        SystemCommand("echo here", [])

if __name__ == "__main__":
    unittest.main()
