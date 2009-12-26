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
    
    def test_exists_true(self):
        """"""
        
        self.assertEquals(
            FileExists(__file__)[0], 0)

    def test_exists_false(self):
        """"""
        
        self.assertRaises(
            RuntimeError,
            FileExists,
            "does not exist.blah")


    def test_count_passes(self):
        """"""
        
        VerifyFileCount("cmd_line.py", [1])
        VerifyFileCount("cmd_line.py", 1)
        VerifyFileCount("cmd_line.py", ">0")
        VerifyFileCount("cmd_line.py", "<2")
        VerifyFileCount("cmd_line.py", ">=1")
        VerifyFileCount("cmd_line.py", "<=1")
        VerifyFileCount("cmd_line.py", "=1")

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


    def test_output(self):
       Output("this is a testing message")


if __name__ == "__main__":
    unittest.main()
