import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from betterbatch import *
from betterbatch import built_in_commands

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


def DebugAction(to_exec, dummy = None):
    exec to_exec
    return 0, "no message"


built_in_commands.NAME_ACTION_MAPPING['debug'] = DebugAction


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

    def test_StepUnknownActionType(self):
        """"""

        self.assertRaises(
            RuntimeError,
            Step,
                "blah", [], ['dir', "c:\\", "/b"])

    def test_StepExecute_no_ret(self):
        """"""
        Step('run', [], "dir").Execute()

    def test_Step_output(self):
        """"""
        Step('output', [], "my message").Execute()

    def test_Step_interupted_continue(self):
        """"""
        old_stdin = sys.stdin
        sys.stdin = open(os.path.join(TEST_FILES_PATH, "no.txt"), "r")
        Step('debug', [], "raise KeyboardInterrupt()").Execute()
        sys.stdin.close()
        sys.stdin = old_stdin

    def test_Step_interupted_stop(self):
        """"""
        old_stdin = sys.stdin
        sys.stdin = open(os.path.join(TEST_FILES_PATH, "yes.txt"), "r")
        s = Step('debug', [], "raise KeyboardInterrupt")
        
        self.assertRaises(RuntimeError, s.Execute)
        self.assertRaises(RuntimeError, s.Execute)
        
        sys.stdin.close()
        sys.stdin = old_stdin

    def test_StepExecute_ret(self):
        """"""
        Step('run', ['nocheck'], "dirsad").Execute()

    def test_StepExecute_with_echo(self):
        """"""
        Step('run', ['echo'], "echo Hi Tester").Execute()

    def test_StepExecute_with_echo(self):
        """"""
        Step('run', ['echo'], "echo Hi Tester").Execute()


    def test_StepExecute_(self):
        """"""
        Step('run', ['echo'], "echo Hi Tester").Execute()

    def test_Step_repr(self):
        """"""
        rep = repr(Step('run', ['echo'], "echo Hi Tester"))
        
        self.assertEquals(rep, "<Step: %s %s>"% ('run', 'echo'))



if __name__ == "__main__":
    unittest.main()
