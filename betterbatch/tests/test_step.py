import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from betterbatch import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

class StepTests(unittest.TestCase):
    "Unit tests for the loadconfig function"
    
    def test_StepFromString(self):
        """"""
        
        s = ParseStepData("echo this step")
        self.assertEquals(s, ('run', [], "echo this step"))

    def test_StepFromDict(self):
        """"""        
        s = ParseStepData({'run': "echo this step"})
        self.assertEquals(s, ('run', [], "echo this step"))

    def test_Step_from_list(self):
        """"""        
        s = ParseStepData({'run': ["echo", "run this"]})
        self.assertEquals(s, ('run', [], ["echo", "run this"]))

    def test_StepFromBadDict(self):
        """"""        
        self.assertRaises(
            RuntimeError,
            ParseStepData,
                {'run': "echo this step", "a": 123})

    def test_StepWithQualifiers(self):
        """"""
        Step("run", ['ui', 'nocheck'], 'dir')
        Step("run", ['nocheck'], 'dir')
        Step("count", [5], 'dir')

    #def test_StepInfoAsDict(self):
    #    """"""
    #    step_data = {'run': ['dir', 'c:\\', "/b"] }
    #    
    #    Step(step_data, {})

    def test_StepUnknownActionType(self):
        """"""
        
        self.assertRaises(
            RuntimeError,
            Step,
                "blah", [], ['dir', "c:\\", "/b"])

    def test_StepExecute_no_ret(self):
        """"""
        Step('run', [], "dir").Execute()
        
    def test_StepExecute_ret(self):
        """"""
        Step('run', ['nocheck'], "dirsad").Execute()


if __name__ == "__main__":
    unittest.main()
