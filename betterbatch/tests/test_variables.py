import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from betterbatch import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


class CalculateExternalVariableTests(unittest.TestCase):
    "Unit tests for the loadconfig function"

    def test_with_any_case(self):
        """"""
        self.assertEquals(
            CalculateExternalVariable("(RuN) echo This value"),
            "This value")
            
    def test_not_a_command(self):
        """"""
        var = "(not_a_command) echo This value"
        self.assertEquals(
            CalculateExternalVariable(var),
            var)


if __name__ == "__main__":
    unittest.main()
