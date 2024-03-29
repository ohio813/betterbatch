import unittest
import os
import sys
import glob

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

# ensure that the package root is on the path
PACKAGE_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.append(PACKAGE_ROOT)

from betterbatch import parsescript
from betterbatch.parsescript import *
parsescript.LOG = ConfigLogging()


#class CommandTests(unittest.TestCase):
#    "Unit tests for the commands"
#
#    #def test_ListCommands(self):
#    #    """"""
#    #    vars, commands = ParseScriptFile(
#    #        os.path.join(TEST_FILES_PATH, "commands.bb"))
#
#    #    ListCommands(commands)
#
#    #def test_GetCommands(self):
#    #    """"""
#    #    vars, commands = ParseScriptFile(
#    #        os.path.join(TEST_FILES_PATH, "commands.bb"))
#
#    #    steps = GetStepsForSelectedCommands(commands)#, "test")
#    #    self.assertEquals(len(steps), 1)
#
#    #    steps = GetStepsForSelectedCommands(commands)#, "test,test2")
#    #    self.assertEquals(len(steps), 2)
#
#    #def test_GetCommands_missing(self):
#    #    """"""
#    #    vars, commands = ParseScriptFile(
#    #        os.path.join(TEST_FILES_PATH, "commands.bb"))
#
#    #    self.assertRaises(
#    #        ErrorCollection,
#    #        GetStepsForSelectedCommands,
#    #            commands, "test123")
#
#    #def test_GetCommands_ambiguous(self):
#    #    """"""
#    #    vars, commands = ParseScriptFile(
#    #        os.path.join(TEST_FILES_PATH, "commands.bb"))
#
#    #    self.assertRaises(
#    #        ErrorCollection,
#    #        GetStepsForSelectedCommands,
#    #            commands, "tes")
#
#    def test_parsestepdata_basic(self):
#
#        step_data = {' run ui ': '\nrunning  \n'}
#        action_type, qualifiers, step_info = ParseStepData(step_data)
#        self.assertEquals(action_type, 'run')
#        self.assertEquals(qualifiers, ['ui'])
#        self.assertEquals(step_info, 'running')
#
#    def test_parsestepdata_string(self):
#
#        step_data = '\nrunning  \n'
#        action_type, qualifiers, step_info = ParseStepData(step_data)
#        self.assertEquals(action_type, 'run')
#        self.assertEquals(qualifiers, [])
#        self.assertEquals(step_info, 'running')
#
#    def test_parsestepdata_basic_non_dict_error(self):
#
#        step_data = []
#        self.assertRaises(
#            RuntimeError,
#            ParseStepData,
#                step_data)
#
#    def test_parsestepdata_basic_wrong_dict_error(self):
#
#        step_data = {}
#        self.assertRaises(
#            RuntimeError,
#            ParseStepData,
#                step_data)
#
#        # dict len > 1
#        step_data = {"run": 'test', "check": "test2"}
#        self.assertRaises(
#            RuntimeError,
#            ParseStepData,
#                step_data)
#
#    def test_parsestepdata_None(self):
#
#        step_data = None
#        data = ParseStepData(step_data)
#        self.assertEquals(data, ('run', [], ''))
#
#    def test_parsestepdata_empty_string(self):
#
#        step_data = ""
#        data = ParseStepData(step_data)
#        self.assertEquals(data, ('run', [], ''))
#

class test_ValidateArgumentCounts(unittest.TestCase):
    def setUp(self):
        self.count_db = {
        'robocopy': [5, '*'],
        'robocopy.exe': [5, '*'],
        'cd': [1, 1]}

#    def test_ValidateArgs_pass_1(self):
#        step = Step(*ParseStepData("robocopy /z  over here sdfs sdfdsf"))
#        ValidateArgumentCounts([step], self.count_db)
#
#        step = Step(*ParseStepData("robocopy /z  over here sdfs sdfdsf sdf sdf"))
#        ValidateArgumentCounts([step], self.count_db)
#
#    def test_ValidateArgs_pass_2(self):
#        step = Step(*ParseStepData("cd here"))
#        ValidateArgumentCounts([step], self.count_db)
#
#    def test_ValidateArgs_pass_3(self):
#        step = Step(*ParseStepData('cd "here there are spaces"'))
#        ValidateArgumentCounts([step], self.count_db)
#
#    def test_ValidateArgs_fail_1(self):
#        step = Step(*ParseStepData("robocopy /z  here sdf sdf"))
#        self.assertRaises(
#            RuntimeError,
#            ValidateArgumentCounts,
#                [step], self.count_db)
#
#    def test_ValidateArgs_fail_2(self):
#        step = Step(*ParseStepData("cd"))
#        self.assertRaises(
#            RuntimeError,
#            ValidateArgumentCounts,
#                [step], self.count_db)
#
#    def test_ValidateArgs_fail_3(self):
#        step = Step(*ParseStepData("cd here there"))
#        self.assertRaises(
#            RuntimeError,
#            ValidateArgumentCounts,
#                [step], self.count_db)
#
#    def test_ValidateArgs_unknown_command(self):
#        step = Step(*ParseStepData("blah here there"))
#        ValidateArgumentCounts([step], self.count_db)

    def test_ReadParamRestrictions_parser_error(self):
        test_file = os.path.join(TEST_FILES_PATH, 'test_params.ini')
        self.assertEquals(ReadParamRestrictions(test_file), {})

    def test_ReadParamRestrictions_missing_file(self):
        self.assertEquals(ReadParamRestrictions('test_params_na.ini'), {})


if __name__ == "__main__":
    unittest.main()
