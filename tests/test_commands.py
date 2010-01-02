import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from test_config import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

class CommandTests(unittest.TestCase):
    "Unit tests for the loadconfig function"
    
    def test_ListCommands(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "commands.yaml"))
        
        ListCommands(commands)

    def test_GetCommands(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "commands.yaml"))
        
        steps = GetStepsForSelectedCommands(commands, "test")        
        self.assertEquals (len(steps), 1)

        steps = GetStepsForSelectedCommands(commands, "test,test2")
        self.assertEquals (len(steps), 2)

    
    def test_GetCommands_missing(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "commands.yaml"))
        
        self.assertRaises(
            ErrorCollection,
            GetStepsForSelectedCommands,
                commands, "test123")

    def test_GetCommands_ambiguous(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "commands.yaml"))
        
        self.assertRaises(
            ErrorCollection,
            GetStepsForSelectedCommands,
                commands, "tes")

    
    def test_parsestepdata_basic(self):
    
        step_data = {' run ui ': '\nrunning  \n'}
        action_type, qualifiers, step_info = ParseStepData(step_data)
        self.assertEquals(action_type, 'run')
        self.assertEquals(qualifiers, ['ui'])
        self.assertEquals(step_info, 'running')

    def test_parsestepdata_string(self):
    
        step_data = '\nrunning  \n'
        action_type, qualifiers, step_info = ParseStepData(step_data)
        self.assertEquals(action_type, 'run')
        self.assertEquals(qualifiers, [])
        self.assertEquals(step_info, 'running')

    def test_parsestepdata_basic_non_dict_error(self):
    
        step_data = []
        self.assertRaises(
            RuntimeError,
            ParseStepData,
                step_data)

    def test_parsestepdata_basic_wrong_dict_error(self):
    
        step_data = {}
        self.assertRaises(
            RuntimeError,
            ParseStepData,
                step_data)

        # dict len > 1
        step_data = {"run": 'test', "check": "test2"}
        self.assertRaises(
            RuntimeError,
            ParseStepData,
                step_data)


if __name__ == "__main__":
    unittest.main()
