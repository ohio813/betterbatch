import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from test_config import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

class StepTests(unittest.TestCase):
    "Unit tests for the loadconfig function"
    
    #def test_StepFromString(self):
    #    """"""
    #    
    #    s = Step("echo this step", {})

    #def test_StepFromDict(self):
    #    """"""        
    #    s = Step({'run': "echo this step"}, {})

    # needs to be re-written for the ParseStepData() function
    #def test_StepFromBadDict(self):
    #    """"""        
    #    self.assertRaises(
    #        RuntimeError,
    #        Step,
    #            {'run': "echo this step", "a": 123}, {})
    #    Step("run", [], 'echo this step')

    #def test_StepFromother(self):
    #    """"""
    #    
    #    self.assertRaises(
    #        RuntimeError,
    #        Step,
    #            None, {})

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
