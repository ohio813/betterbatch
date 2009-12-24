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
    
    def test_structure(self):
        """"""
        vars_and_commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "empty_variables.yaml"))
        self.assertEquals(vars_and_commands, ({}, {}))



if __name__ == "__main__":
    unittest.main()
