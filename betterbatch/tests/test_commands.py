import unittest
import os
import glob

import sys
sys.path.append(".")
sys.path.append("..")

from betterbatch import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


class CommandTests(unittest.TestCase):
    "Unit tests for the commands"

    #def test_ListCommands(self):
    #    """"""
    #    vars, commands = ParseScriptFile(
    #        os.path.join(TEST_FILES_PATH, "commands.yaml"))

    #    ListCommands(commands)

    #def test_GetCommands(self):
    #    """"""
    #    vars, commands = ParseScriptFile(
    #        os.path.join(TEST_FILES_PATH, "commands.yaml"))

    #    steps = GetStepsForSelectedCommands(commands)#, "test")
    #    self.assertEquals(len(steps), 1)

    #    steps = GetStepsForSelectedCommands(commands)#, "test,test2")
    #    self.assertEquals(len(steps), 2)

    #def test_GetCommands_missing(self):
    #    """"""
    #    vars, commands = ParseScriptFile(
    #        os.path.join(TEST_FILES_PATH, "commands.yaml"))

    #    self.assertRaises(
    #        ErrorCollection,
    #        GetStepsForSelectedCommands,
    #            commands, "test123")

    #def test_GetCommands_ambiguous(self):
    #    """"""
    #    vars, commands = ParseScriptFile(
    #        os.path.join(TEST_FILES_PATH, "commands.yaml"))

    #    self.assertRaises(
    #        ErrorCollection,
    #        GetStepsForSelectedCommands,
    #            commands, "tes")

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

    def test_parsestepdata_None(self):

        step_data = None
        data = ParseStepData(step_data)
        self.assertEquals(data, ('run', [], ''))

    def test_parsestepdata_empty_string(self):

        step_data = ""
        data = ParseStepData(step_data)
        self.assertEquals(data, ('run', [], ''))


class IfElseTests(unittest.TestCase):
    def test_working_do(self):
        for filename in glob.glob(os.path.join(TEST_FILES_PATH, "if_else_*")):
            
            command = os.path.basename(filename)
            command = command[:-len(".yaml")]
            command = command[len("if_else_"):]
            
            # skip tests which are meant to fail
            if 'if_else_broken' in filename:
                continue
            
            vars = {}
            commands = ParseScriptFile(
                os.path.join(TEST_FILES_PATH, filename), vars)
            steps = commands.values()[0]

            try:
                executable_steps = BuildExecutableSteps(steps, vars)
            except ErrorCollection, e:
                print "ERROR WHEN RUNNING", command
                e.LogErrors()
                raise

            for step in executable_steps:
                ret, out = step.Execute()
                if "if_else_empty" in filename:
                    self.assertEquals(out.strip(), "")
                else:
                    self.assertEquals(out.strip(), command)

    def test_broken_not_list(self):
        vars = {}
        commands = ParseScriptFile(
            os.path.join(TEST_FILES_PATH, "if_else_broken_not_list.yaml"), 
            vars)
        steps = commands.values()[0]

        self.assertRaises(
            ErrorCollection,
            BuildExecutableSteps,
                steps, vars)            
        
    def test_broken_not_list2(self):
        vars = {}
        commands = ParseScriptFile(
            os.path.join(TEST_FILES_PATH,   "if_else_broken_not_list2.yaml"), 
            vars)
        steps = commands.values()[0]

        self.assertRaises(
            ErrorCollection,
            BuildExecutableSteps,
                steps, vars)

    def test_broken_too_few_clauses(self):
        vars = {}
        commands = ParseScriptFile(
            os.path.join(TEST_FILES_PATH, "if_else_broken_only_one.yaml"),
            vars)
        steps = commands.values()[0]

        try:
            BuildExecutableSteps(steps, vars)
        except ErrorCollection, e:
            print "\n\n"
            e.LogErrors()
        self.assertRaises(
            ErrorCollection,
            BuildExecutableSteps,
                steps, vars)

    def test_broken_too_many_clauses(self):
        vars = {}
        commands = ParseScriptFile(
            os.path.join(TEST_FILES_PATH, "if_else_broken_too_many.yaml"),
            vars)
        steps = commands.values()[0]

        self.assertRaises(
            ErrorCollection,
            BuildExecutableSteps,
                steps, vars)

    def test_broken_do_name(self):
        vars = {}
        commands = ParseScriptFile(
            os.path.join(TEST_FILES_PATH, "if_else_broken_do_name.yaml"), vars)
        steps = commands.values()[0]

        self.assertRaises(
            ErrorCollection,
            BuildExecutableSteps,
                steps, vars)

    def test_broken_else_name(self):
        vars = {}
        commands = ParseScriptFile(
            os.path.join(TEST_FILES_PATH, "if_else_broken_else_name.yaml"),
            vars)
        steps = commands.values()[0]

        self.assertRaises(
            ErrorCollection,
            BuildExecutableSteps,
                steps, vars)


class test_ValidateArgumentCounts(unittest.TestCase):
    def setUp(self):
        self.count_db = {
        'robocopy': [5, '*'],
        'robocopy.exe': [5, '*'],
        'cd': [1, 1]}

    def test_ValidateArgs_pass_1(self):
        step = Step(*ParseStepData("robocopy /z  over here sdfs sdfdsf"))
        ValidateArgumentCounts([step], self.count_db)

        step = Step(*ParseStepData("robocopy /z  over here sdfs sdfdsf sdf sdf"))
        ValidateArgumentCounts([step], self.count_db)

    def test_ValidateArgs_pass_2(self):
        step = Step(*ParseStepData("cd here"))
        ValidateArgumentCounts([step], self.count_db)
       
    def test_ValidateArgs_pass_3(self):
        step = Step(*ParseStepData('cd "here there are spaces"'))
        ValidateArgumentCounts([step], self.count_db)

    def test_ValidateArgs_fail_1(self):
        step = Step(*ParseStepData("robocopy /z  here sdf sdf"))
        self.assertRaises(
            RuntimeError,
            ValidateArgumentCounts,
                [step], self.count_db)

    def test_ValidateArgs_fail_2(self):
        step = Step(*ParseStepData("cd"))
        self.assertRaises(
            RuntimeError,
            ValidateArgumentCounts,
                [step], self.count_db)

    def test_ValidateArgs_fail_3(self):
        step = Step(*ParseStepData("cd here there"))
        self.assertRaises(
            RuntimeError,
            ValidateArgumentCounts,
                [step], self.count_db)

    def test_ValidateArgs_unknown_command(self):
        step = Step(*ParseStepData("blah here there"))
        ValidateArgumentCounts([step], self.count_db)

    def test_ReadParamRestrictions_parser_error(self):
        test_file = os.path.join(TEST_FILES_PATH, 'test_params.ini')
        self.assertEquals(ReadParamRestrictions(test_file), {})

    def test_ReadParamRestrictions_missing_file(self):
        self.assertEquals(ReadParamRestrictions('test_params_na.ini'), {})


if __name__ == "__main__":
    unittest.main()
