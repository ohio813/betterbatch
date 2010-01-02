import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from test_config import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")
COMMANDS_YAML = os.path.join(TEST_FILES_PATH, "commands.yaml")

class MainTests(unittest.TestCase):
    "Unit tests for the loadconfig function"
    
    def test_Main_none(self):
        """"""
        Main()
        

    def test_Main_list(self):
        """"""
        
        sys.argv = ['main.py', "--list", COMMANDS_YAML]
        Main()

    
    def test_Main_execute(self):
        """"""
        sys.argv = ['main.py', COMMANDS_YAML, "--execute", "test" ]
        Main()


    def test_Main_execute_fail(self):
        """"""
        
        sys.argv = ['main.py', COMMANDS_YAML, "--execute", "test_broken" ]
        self.assertRaises(
            ErrorCollection,
            Main)

    def test_Main_execute_fail2(self):
        """"""
        
        sys.argv = ['main.py', COMMANDS_YAML, "--execute", "test_broken2" ]
        
        self.assertRaises(
            ErrorCollection,
            Main)

    def test_Main_LogFile(self):
        """"""
        
        sys.argv = ['main.py', os.path.join(TEST_FILES_PATH, "logfile.yaml")]
        Main()


if __name__ == "__main__":
    unittest.main()
