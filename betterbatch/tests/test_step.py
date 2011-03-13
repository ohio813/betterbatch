from __future__ import absolute_import

import unittest
import os
import sys

# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(package_root)

from betterbatch.parsescript import *
from betterbatch import built_in_commands

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


    #def test_ParseStep_DOS_replacement_cmd(self):

    #    step_data = "cd test"
    #    data = ParseStep(step_data)
    #    self.assertEquals(data, ('cd', [], 'test'))

    #    step_data = {"run": "cd test"}
    #    data = ParseStep(step_data)
    #    self.assertEquals(data, ('cd', [], 'test'))

    #    step_data = {"run": ["cd", "test"]}
    #    data = ParseStep(step_data)
    #    self.assertEquals(data, ('cd', [], ['test']))


class StepTests(unittest.TestCase):
    "Unit tests for the loadconfig function"

    def test_StepFromString(self):
        """"""

        s = ParseStep("dir this step")
        self.assertEquals(isinstance(s, CommandStep), True)
        self.assertEquals(s.qualifiers, [])
        self.assertEquals(s.raw_step, "dir this step")
        self.assertEquals(s.step_data, "dir this step")

    #def test_StepFromDict(self):
    #    """"""
    #    s = ParseStep({'run': "echo this step"})
    #    self.assertEquals(s, ('run', [], "echo this step"))

    #def test_Step_from_list(self):
    #    """"""
    #    s = ParseStep({'run': ["echo", "run this"]})
    #    self.assertEquals(s, ('run', [], ["echo", "run this"]))

    def test_StepFromBadDict(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ParseStep,
                {'run': "echo this step", "a": 123})

    #def test_Step_DosCommand(self):
        """"""
        s = CommandStep('cd "some directory"')
        
        #self.assertEquals(
        #    s.params, '"some directory"')

        #self.assertEquals(s.argcount, 1)
        #self.assertEquals(s.command, "cd")

        #self.assertEquals(
        #    s.action, built_in_commands.NAME_ACTION_MAPPING['cd'])

    #def test_Step_DosCommand_not_run(self):
        """"""
        #s = Step('cd', [], '"some directory"')
        
        #self.assertEquals(
        #    s.params, '"some directory"')
            
        #self.assertEquals(s.argcount, 1)

    def test_Step_DosCommand(self):
        """"""
        #s = Step('run', [], ['cd', 'some directory'])
        
        #self.assertEquals(
        #    s.params, ['some directory'])

        #self.assertEquals(s.argcount, 1)
        #self.assertEquals(s.command, "cd")

        #self.assertEquals(
        #    s.action, built_in_commands.NAME_ACTION_MAPPING['cd'])


    #def test_StepWithDict_params(self):
    #    """"""
    #    s = ParseStep({'run': {'test': "echo this step"}})


    def test_StepWithQualifiers(self):
        """"""
        s = CommandStep('dir {*ui*} {*nocheck*}')
        self.assertEquals(s.qualifiers, ['ui', 'nocheck'])
        
        #Step('dir {*nocheck*}')
        #Step("count", [5], 'dir')

    #def test_StepUnknownActionType(self):
    #    """"""

  # #     self.assertRaises(
    #        RuntimeError,
    #        Step,
    #            "blah", [], ['dir', "c:\\", "/b"])

    def test_Stepexecute_no_ret(self):
        """"""
        CommandStep("dir").execute({}, 'run')

    def test_Step_output(self):
        """"""
        CommandStep('echo my message').execute({}, 'run')

    def test_Stepexecute_ret(self):
        """Test that 'nocheck' doesn't raise on error"""
        CommandStep("dirsad {*nocheck*}").execute({}, 'run')

    def test_Stepexecute_with_echo(self):
        """"""
        CommandStep("echo Hi Tester").execute({}, 'run')

    def test_Stepexecute_with_echo(self):
        """"""
        CommandStep("echo Hi Tester {*echo*}").execute({}, 'run')

    def test_Stepexecute_(self):
        """"""
        CommandStep("echo Hi Tester").execute({}, 'run')

    def test_Step_repr(self):
        """"""
        rep = repr(Step("echo Hi Tester"))
        
        self.assertEquals(rep, "<Step echo Hi Tester>")

    #def test_Step_command_with_list(self):
    #    """"""
    #    step = Step(["echo", "Hi", "Tester"])
    #    
    #    self.assertEquals(step.command, 'echo')

  # # def test_Step_argcount_with_list(self):
    #    """"""
    #    step = Step(["echo", "Hi", "Tester"])
    #    
    #    self.assertEquals(step.argcount, 2)

  # # def test_Step_argcount_with_invalid_shlex_str(self):
    #    """"""
    #    step = Step('echo Hi " Tester')
    #    self.assertEquals(step.argcount, 3)


#
if __name__ == "__main__":
    unittest.main()
