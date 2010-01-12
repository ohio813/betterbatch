import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from built_in_commands import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


class BuiltInCommandsTests(unittest.TestCase):
    "Unit tests for the built in commands"

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

    def test_dirname(self):
        self.assertEquals(dirname(r"c:\tes\temp\here.txt"), (0, r"c:\tes\temp"))

    def test_basename(self):
        self.assertEquals(basename(r"c:\tes\temp\here.txt"), (0, r"here.txt"))



if __name__ == "__main__":
    unittest.main()
