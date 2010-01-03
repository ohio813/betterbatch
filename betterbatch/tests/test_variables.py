import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from betterbatch import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

# how to raise a yaml.parser.ParserError???

class VariableTests(unittest.TestCase):
    "Unit tests for the loadconfig function"

    def test_empty(self):
        """"""
        vars_and_commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "empty_variables.yaml"))
        self.assertEquals(vars_and_commands, ({}, {}))

    def test_broken(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ParseConfigFile,
            os.path.join(TEST_FILES_PATH, "broken_variables.yaml"))

    def test_simple(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(
            ReplaceVariableReferences(vars['simple'], vars), 'here')

    def test_replace_mismatched_bracket(self):
        """"""
        try:
            ReplaceVariableReferences("<her<e>", {})
        except ErrorCollection, e:
            self.assertEquals(len(e.errors), 2)
            self.assertEquals(
                str(e.errors[1]),
                "Mismatched angle brackets in '<her<e>'")

    def test_replacement(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(
            ReplaceVariableReferences(vars['replace'], vars),
            'This is here')

    def test_system(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))

        self.assertEquals(
            ReplaceVariableReferences(vars['system'], vars),
            'This is a test')

    def test_replace_and_system(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "standard_variables.yaml"))


        self.assertEquals(
            ReplaceVariableReferences(vars['system+replace'], vars),
            'This is here that is there')

    def test_system_variable_error(self):
        """"""

        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
            "(system) failure", {})

    def test_ReplaceVarRefsInStructure_string(self):
        """"""
        variables = dict(
            var1 = '123',
            var2 = '<var1>456'
        )
        structure = 'replace <var2>'
        new_struct = ReplaceVarRefsInStructure(structure, variables)
        self.assertEquals(new_struct, 'replace 123456')

    def test_ReplaceVarRefsInStructure_list(self):
        """"""
        variables = dict(
            var1 = '123',
            var2 = '<var1>456'
        )
        structure = ['replace 123456', '<<<var2><VaR1>>>']
        new_struct = ReplaceVarRefsInStructure(structure, variables)
        self.assertEquals(new_struct, ['replace 123456', '<123456123>'])

    def test_ReplaceVarRefsInStructure_list_error(self):
        """"""
        variables = dict(
            var1 = '123',
            var2 = '<var1>456'
        )
        structure = [" <please> replace these <undefined> variables<"]
        self.assertRaises(
            ErrorCollection,
            ReplaceVarRefsInStructure,
                structure, variables)

    def test_ReplaceVarRefsInStructure_dict(self):
        """"""

        variables = dict(
            var1 = '123',
            var2 = '<var1>456'
        )
        structure = {'<abc>': 'replace <var2>', 'b c d': '<<<var2><var1>>>'}
        new_struct = ReplaceVarRefsInStructure(structure, variables)
        self.assertEquals(new_struct, {'<abc>': 'replace 123456', 'b c d': '<123456123>'})

    def test_ReplaceVariableReferences_dict_error(self):
        """"""
        variables = dict(
            var1 = '123',
            var2 = '<var1>456'
        )
        structure = {"test" :" <please> replace these <undefined> variables<"}
        self.assertRaises(
            ErrorCollection,
            ReplaceVarRefsInStructure,
                structure, variables)

    def test_ReplaceVariableReferences_undefined_errors(self):
        """"""
        variables = dict(
            var1 = '123',
            var2 = '<var1>456'
        )
        structure = "<please> replace these <undefined> variables<"
        try:
            ReplaceVarRefsInStructure(structure, variables)
        except ErrorCollection, e:
            e.LogErrors()

    def test_ReplaceVariableReferences_recursive(self):
        """"""
        vars, commands = ParseConfigFile(
            os.path.join(TEST_FILES_PATH, "recursive_variables.yaml"))

        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
            vars['test'],
            vars)

        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
            vars['test2'],
            vars)

        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
            vars['test3'],
            vars)

        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
            vars['test4'],
            vars)


if __name__ == "__main__":
    unittest.main()
