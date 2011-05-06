from __future__ import absolute_import

import unittest
import os
import sys
import logging
import glob

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

# ensure that the package root is on the path
PACKAGE_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.append(PACKAGE_ROOT)

from betterbatch import parsescript
from betterbatch. parsescript import *

parsescript.LOG = ConfigLogging()


class ConfigLoggingTests(unittest.TestCase):

    def test_use_colors(self):

        logger = logging.getLogger("betterbatch")
        logger.handlers = []

        logger = ConfigLogging(use_colors=True)

        colored_handler_found = False
        for handler in logger.handlers:
            if isinstance(handler, ColoredConsoleHandler):
                colored_handler_found = True
                break

        self.assertEqual(colored_handler_found, True)


class ParseYAMLFileTests(unittest.TestCase):

    def test_simple_file(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'basic.bb')
        details = ParseYAMLFile(full_path)
        self.assertEquals(details, [
            "set Hello=.",
            "cd <hello>"])

    def test_doesnt_exist(self):
        """"""
        self.assertRaises(
            IOError,
            ParseYAMLFile,
                "some non existant file")

    def test_scanner_error(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'scanner_error.bb')
        self.assertRaises(
            RuntimeError,
            ParseYAMLFile,
                full_path)

    def test_parser_error(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'parser_error.bb')
        self.assertRaises(
            RuntimeError,
            ParseYAMLFile,
                full_path)

    def test_colon_mid_string(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'parser_error.bb')
        self.assertRaises(
            RuntimeError,
            ParseYAMLFile,
                full_path)

    def test_with_tab(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'with_tab.bb')
        steps = ParseYAMLFile(full_path)
        self.assertEquals(
            steps,
            ["set    Hello    =    .", "cd    <hello>"])

    def test_empty_file(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'empty_file.bb')
        steps = ParseYAMLFile(full_path)
        self.assertEquals(steps, None)

    def test_numeric_value(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'number.bb')
        self.assertRaises(
            RuntimeError,
            ParseYAMLFile,
                full_path)

    def test_mismatched_braces(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'mismatched_braces.bb')
        self.assertRaises(
            RuntimeError,
            ParseYAMLFile,
                full_path)

    def test_usage(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'usage_returned_with_new_line.bb')
        self.assertEquals(
            ParseYAMLFile(full_path),
            ['set USAGE =\nshould return with new line after this\nand before this line'])

class ErrorCollectionTests(unittest.TestCase):
    def test_LOGErrors(self):
        """"""
        errs = ['err1', "err1"]

        collection = ErrorCollection(errs)
        collection.LogErrors()

        errs += [
            UndefinedVariableError("var", "yo"),
            UndefinedVariableError("var", "yo2"),
            UndefinedVariableError("var", "yo2"),
            UndefinedVariableError("var2", "yo"),
            ]

        collection = ErrorCollection(errs)
        collection.LogErrors()

    def test_LOGErrors_command_path_errors(self):
        """"""
        errs = ['err1', "err"]

        collection = ErrorCollection(errs)
        collection.LogErrors()

        errs += [
            CommandPathNotFoundError("robocopy123", "yo"),
            CommandPathNotFoundError("robocopy123", "yo2"),
            CommandPathNotFoundError("robocopy123", "yo2"),
            CommandPathNotFoundError("robocopy456", "yo"),
            ]

        collection = ErrorCollection(errs)
        collection.LogErrors()

    def test_LOGErrors_combination(self):
        """"""
        errs = ['err1', "err"]

        collection = ErrorCollection(errs)
        collection.LogErrors()

        errs += [
            CommandPathNotFoundError("robocopy123", "yo"),
            CommandPathNotFoundError("robocopy123", "yo2"),
            CommandPathNotFoundError("robocopy123", "yo2"),
            CommandPathNotFoundError("robocopy456", "yo"),
            UndefinedVariableError("var", "yo"),
            UndefinedVariableError("var", "yo2"),
            UndefinedVariableError("var", "yo2"),
            UndefinedVariableError("var2", "yo"),
            ]

        collection = ErrorCollection(errs)
        collection.LogErrors()

    def test_repr__(self):
        """"""
        errs = ['err1', "err1"]

        collection = ErrorCollection(errs)
        repr(collection)


class ParseVariableDefinitionTests(unittest.TestCase):
    "Unit tests for variable definitions"

    def test_simple_var_def(self):
        self.assertEquals(
            ParseVariableDefinition("var_name = var value"),
            ("var_name", "var value"))

        # '=' stuck to the variable name
        self.assertEquals(
            ParseVariableDefinition('var_name= var value'),
            ("var_name", "var value"))

        # '=' stuck to the variable value
        self.assertEquals(
            ParseVariableDefinition(' var_name =var value'),
            ("var_name", "var value"))

        # '=' no spaces
        self.assertEquals(
            ParseVariableDefinition(' var_name=var value'),
            ("var_name", "var value"))

    def test_variable_with_space(self):
        # '=' no spaces
        self.assertRaises(
            RuntimeError,
            ParseVariableDefinition,
                ' var name=var value')

    def test_variable_no_var_name(self):
        # '=' no spaces
        self.assertRaises(
            RuntimeError,
            ParseVariableDefinition,
                ' =var value')

    def test_only_set(self):
        self.assertRaises(
            RuntimeError,
            ParseVariableDefinition,
                ' ')

    def test_no_equals(self):
        self.assertRaises(
            RuntimeError,
            ParseVariableDefinition,
                'blah')

    def test_no_equals_allowed(self):
        self.assertEquals(
            ('blah', None),
            ParseVariableDefinition('blah', function = "definition"))

    def test_no_value_equals_allowed(self):
        self.assertEquals(
            ('blah', ''),
            ParseVariableDefinition('blah=', function = "definition"))

    def test_with_executable_section(self):
        v = VariableDefinition("set x = {{{abspath .}}}")
        vars = {}
        v.execute(vars, "run")

        self.assertEquals(vars['x'], os.path.abspath('.'))

    def test_with_missing_vars(self):
        v = VariableDefinition("set x = <missing>")
        vars = {}

        v.execute(vars, "run")

        v.execute(vars, "test")
        #self.assertEquals(vars['x'], '')

    def test_wrong_function_value(self):
        self.assertRaises(
            ValueError,
            ParseVariableDefinition,
                'blah=here', function = "wrong")


class ParseMappingVariableDefinitionTests(unittest.TestCase):
    "Unit tests for mapping variables"

    def test_simple_correct(self):
        parsed = ParseComplexStep({"set x": ['a -> 1', 'b -> 2'] } )
        self.assertEquals(len(parsed), 4)

    def test_no_values(self):
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                {"set x": None} )

    def test_broken_sub_def(self):
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                {"set x": ['a', 'b'] })

    def test_multiple_keys(self):
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                {"set x": ['here -> there'], "set y": ['this -> that']} )

    def test_parse_steps_can_handle_multiple(self):
        ParseSteps([{"set x": ['here -> there']}])


class FindVariableReferencesTests(unittest.TestCase):

    def test_no_var_ref(self):
        self.assertEquals(
            FindVariableReferences("cd this dir"), {})

    def test_easy_var_ref(self):
        self.assertEquals(
            FindVariableReferences("cd <this> dir"),
            {"this": ["<this>"]})

    def test_var_ref_with_spaces(self):
        self.assertEquals(
            FindVariableReferences("cd <   this > dir"),
            {"this": ["<   this >"]})

    def test_var_ref_same_twice(self):
        self.assertEquals(
            FindVariableReferences("cd <   this ><   this >dir"),
            {"this": ["<   this >", "<   this >"]})

    def test_two_var_refs(self):
        self.assertEquals(
            FindVariableReferences("cd <   this ><   this ><dir>"),
            {"this": ["<   this >", "<   this >"], "dir": ["<dir>"]})


#class DummyVar(object):
#    def __init__(self, name, val):
#        self.value = val
#        self.name = name


class ReplaceVariableReferencesTests(unittest.TestCase):

    def test_no_refs(self):
        """"""
        new = ReplaceVariableReferences("here", {})
        self.assertEquals("here", new)

    def test_exact_match(self):
        """"""
        new = ReplaceVariableReferences(
            "<here>", {'here': 'there'})
        self.assertEquals("there", new)

    def test_with_spaces(self):
        """"""
        new = ReplaceVariableReferences(
            " < here   >", {'here': 'there'})
        self.assertEquals(" there", new)

    def test_gt_escaping(self):
        """"""
        new = ReplaceVariableReferences(
            ">> <here>>>", {'here': 'there'})
        self.assertEquals("> there>", new)

    def test_lt_escaping(self):
        """"""
        new = ReplaceVariableReferences(
            "<< <<<here>>>", {'here': 'there'})
        self.assertEquals("< <there>", new)

    def test_missing_var(self):
        """"""
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<not_here>", {'here': 'there'})

    def test_recursive_var_err(self):
        """"""
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<here>", {
                    'here': '<there>',
                    'there': '<here>'})

    def test_recursive_var_good(self):
        """"""
        new_val = ReplaceVariableReferences("x<here>x", {
                'here': '-<there>-',
                'there': 'my value'})

        self.assertEquals(new_val, "x-my value-x")

    def test_2nd_level_undefined(self):
        """"""
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<here>", {
                    'here': '<not_there>',
                    'there': '<here>'})

    def test_2nd_level_single_var_loop(self):
        """"""
        variables = {'x': "uses <x>"}
        #ReplaceVariableReferences("using <x> again", variables)

    def test_2nd_level_multiple_var_loop(self):
        """"""
        variables = {
            'x': "uses <y>",
            'y': "uses <x>",
            }
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<x>", variables)

    def test_ignore_errors(self):
        """"""
        variables = {
            'x': "uses <y> <and_missing>",
            'y': "some value",
            }
        replaced = ReplaceVariableReferences(
            "<x>", variables, ignore_errors = True)

        self.assertEqual(replaced, "uses some value <and_missing>")

#class ReplaceVariablesInStepsTests(unittest.TestCase):
#    """"""
#    def test_normal_no_update(self):
#        steps = [
#            ParseStep("cd <var1>"),
#            ParseStep("echo <var1>")]
#        ReplaceVariablesInSteps(
#            steps, {'var1': 'here'}, phase = 'test')
#
#        self.assertEquals(steps[0].step_data, "cd <var1>")
#        self.assertEquals(steps[1].step_data, "echo <var1>")
#
#    def test_normal_update(self):
#        steps = [
#            ParseStep("cd <var1>"),
#            ParseStep("echo <var1>")]
#        ReplaceVariablesInSteps(
#            steps, {'var1': 'here'}, phase = 'test')
#
#        self.assertEquals(steps[0].step_data, "cd here")
#        self.assertEquals(steps[1].step_data, "echo here")


class SplitStatementAndDataTests(unittest.TestCase):

    def test_normal(self):
        """"""
        statement, data = SplitStatementAndData("set var=here")
        self.assertEquals(statement, "set")
        self.assertEquals(data, "var=here")

    def test_no_data(self):
        """"""
        statement, data = SplitStatementAndData("set")
        self.assertEquals(statement, "set")
        self.assertEquals(data, "")

    def test_with_spaces(self):
        """"""
        statement, data = SplitStatementAndData("   SeT   = var  = here  ")
        self.assertEquals(statement, "SeT")
        self.assertEquals(data, "= var  = here")


#def CloserAndRemoveLogHanlderwithPath(path):
#    for h in LOG.handlers:
#        if hasattr(h, 'baseFilename') and h.baseFilename == path:
#            h.flush()
#            LOG.removeHandler(h)
#            h.stream.close()
#
#            os.unlink(path)

class ColoredConsoleHandlerTests(unittest.TestCase):
    def test_normal(self):
        """"""
        handler = ColoredConsoleHandler()
        class record: pass
        record.msg = "test"
        record.lineno = 23
        record.filename = sys.stdout
        record.levelno = 50
        handler.emit(record)
        record.levelno = 40
        handler.emit(record)
        record.levelno = 30
        handler.emit(record)
        record.levelno = 20
        handler.emit(record)
        record.levelno = 10
        handler.emit(record)
        record.levelno = 0
        handler.emit(record)


class SetupLogFileTests(unittest.TestCase):

    def test_normal(self):
        """"""
        import tempfile
        file, path = tempfile.mkstemp(suffix = "log")
        os.close(file)

        SetupLogFile(path)
        # close the log file - so we can remove
        #CloserAndRemoveLogHanlderwithPath(path)

    def test_file_open(self):
        """"""
        import tempfile
        file, path = tempfile.mkstemp(suffix = "log")

        SetupLogFile(path)
        log = logging.getLogger('betterbatch')
        log.info("test message")

        #os.close(file)
        #os.unlink(path)

    def test_same_logfilepath_already_set(self):
        """"""
        import tempfile
        file, path = tempfile.mkstemp(suffix = "log")

        SetupLogFile(path)
        SetupLogFile(path)
        log = logging.getLogger('betterbatch')
        log.info("test message")


    def test_folder_doesnt_exist(self):
        """"""
        self.assertRaises(
            IOError,
            SetupLogFile,
                r"c:\temp\directory doesn't exist\I hope")

    def test_same_logfile(self):
        """"""
        import tempfile
        file, path = tempfile.mkstemp(suffix = "log")
        os.close(file)

        SetupLogFile(path)
        SetupLogFile(path)

        #CloserAndRemoveLogHanlderwithPath(path)


class RenderVariableValueTests(unittest.TestCase):

    def test_executable_except_ignore_error_false(self):
        """"""
        text = "{{{cd here}}} echo This <var>"
        variables = {'var': 'car'}

        self.assertRaises(
            RuntimeError,
            RenderVariableValue,
                text, variables, "run")

    def test_executable_except_ignore_error_true(self):
        """"""
        text = "{{{cd here}}} echo This <var>"
        variables = {'var': 'car'}

        self.assertEquals(RenderVariableValue(
                        text, variables,
                        "run", ignore_errors=True),
                        "{{{cd here}}} echo This car")


class ValidateCommandPathTests(unittest.TestCase):
    """"""

    def test_which_not_exists(self):
        """"""

        command = "robocopy123 c:\\ c:\\"
        self.assertRaises(
            CommandPathNotFoundError,
            ValidateCommandPath,
            command, )

    def test_which_exists(self):
        """"""

        ValidateCommandPath("robocopy c:\\ c:\\")

    def test_path_not_exists(self):
        """"""

        command = "c:\\temp\\file_not_exists.txt"
        self.assertRaises(
            CommandPathNotFoundError,
            ValidateCommandPath,
            command, )

    def test_path_exists(self):
        """"""

        ValidateCommandPath("c:\\")


class FindVariableMatchingLoopVarTests(unittest.TestCase):
    def test_pass(self):
        variables = {
            "xyz_testxyz": "blah blah",
            "xyz_testxyz_blh": "blah blah",
        }

        self.assertEqual(
            FindVariableMatchingLoopVar('__loopvar___test__loopvar___blh', variables),
            'xyz_testxyz_blh')

    def test_fail(self):
        variables = {
            "xyz_testxyz": "blah blah",
            "xyz_testxyzblhit": "blah blah",
        }

        self.assertEqual(
            FindVariableMatchingLoopVar('__loopvar___test__loopvar__blh', variables),
            None)

    def test_fail(self):
        variables = {
            "xyz_testxyz": "blah blah",
            "xyz_testabc_blh": "blah blah",
        }

        self.assertEqual(
            FindVariableMatchingLoopVar('__loopvar___test__loopvar___blh', variables),
            None)


class ReplaceExecutableSectionsTests(unittest.TestCase):
    ""

    def test_no_section(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections("echo This value", {}),
            "echo This value")

    def test_no_section_with_var(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(
                "here <value>",
                {'value': 'car'}),
            "here <value>")

    def test_simple_exec(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(" -  {{{echo This value}}}  - ", {}),
            " -  This value  - ")

    def test_simple_no_exec(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(
                " -  {{{dir This value}}}  - ", {}, phase = "test"),
            " -    - ")

    def test_simple_with_var_execute(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(
                "here {{{echo This <value>}}} <value>",
                {'value': 'car'}),
            "here This car <value>")

    def test_simple_with_var_no_execute(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(
                "here {{{echo This <value>}}} <value>",
                {'value': 'car'}, phase = "test"),
            "here  <value>")

    def test_not_a_command(self):
        """"""
        text = "{{{cd here}}} echo This <var>"
        variables = {'var': 'car'}
        self.assertRaises(
            RuntimeError,
            ReplaceExecutableSections,
                text, variables, )

    def test_with_embedded_braces(self):
        """"""
        text = "{{{cd {{{ echo hi echo This <var>}}}"
        variables = {'var': 'car'}
        self.assertRaises(
            RuntimeError,
            ReplaceExecutableSections,
                text, variables, )

    def test_command_fails(self):
        """"""
        text = "{{{ _bad_command_or_filename_ }}}"
        variables = {'var': 'car'}
        self.assertRaises(
            RuntimeError,
            ReplaceExecutableSections,
                text, variables, )

    def test_trailing_braces(self):
        """"""
        text = "{{{ echo <var> {*nocheck*}}}}-"
        variables = {'var': 'car'}
        replaced = ReplaceExecutableSections(text, variables)
        self.assertEquals(replaced, "car-")

    def test_escaping_symbols(self):
        """"""
        text = r"{{{ dir \ }}}"
        replaced = ReplaceExecutableSections(text, {})
        self.assertEquals("<<" in replaced , True)
        self.assertEquals(">>" in replaced, True)


class ParseStepTests(unittest.TestCase):
    ""

    # dict
    # non dict

    # in handlers
    # not in handlers


    def test_dict_step(self):
        """"""
        step = ParseStep({r"if exists c:\temp": 'here', 'else': 'there'})
        self.assertEquals(step.conditions[0][1].raw_step,  "exists c:\\temp")

    def test_command_step(self):
        """"""
        step = ParseStep("cd <options> there")
        self.assertEquals(step.raw_step,  "cd <options> there")

    def test_handled_step(self):
        """"""
        step = ParseStep("set var=value")
        self.assertEquals(step.raw_step,  "set var=value")
        self.assertEquals(step.name,  "var")
        self.assertEquals(step.value,  "value")

    def test_empty_include(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ParseStep,
                "include")

    def test_empty_logfile(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ParseStep,
                "logfile")

    def test_empty_set(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ParseStep,
                "set")

    def test_None_step(self):
        """"""
        self.assertEquals(ParseStep(None), None)


class ParseComplexStepTests(unittest.TestCase):
    ""

    def test_basic_if_step(self):
        """"""
        step = ParseComplexStep({r"if exists c:\temp": ["cd 1"], 'else': ["cd 2"]})
        self.assertEquals(step.conditions[0][1].raw_step,  "exists c:\\temp")
        self.assertEquals(step.if_steps[0].raw_step, 'cd 1')
        self.assertEquals(step.else_steps[0].raw_step, 'cd 2')

    def test_basic_if_and_plus_or_step(self):
        """"""
        step = {
            'if  exists blah blah': None,
            'or  exists blah blah': None,
            'and exists blah blah': 'echo found',
        }

        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)

    def test_if_step_string_actions(self):
        """"""
        step = ParseComplexStep({r"if exists c:\temp": "cd 1", 'else': "cd 2"})

    def test_broken_if_step_wrong_key(self):
        """"""
        step = {r"if exists c:\temp": ["cd 1"], 'there': ["cd 2"]}
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)

    def test_if_step_none_when(self):
        """"""
        step = {r"if 1": None, }
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)

    def test_if_step_none_else(self):
        step = {r"if 1": "echo here", 'else': None}
        ParseComplexStep(step)

    def test_if_step_many_if_step_blocks(self):
        step = {r"if 1": "echo here", 'or': "echo there",'else': None}
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)

    def test_for_step(self):
        """"""
        step = {r"for i in 1\n2\n3\n4": ["echo <i>"],}
        step = ParseComplexStep(step)
        self.assertEquals(isinstance(step, ForStep), True)
        step.execute({}, "run")

    def test_for_too_many_statements(self):
        """"""
        step = {r"for i in 1\n2\n3\n4": ["echo <i>"], "anohter": None}
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)

    def test_for_loopvar_var_name(self):
        """"""
        variables = {'1_v': 'test'}
        step = ParseComplexStep({r"for i in 1\n2\n3\n4": ["echo < <i>_v> "]})

        step.execute(variables, 'test')

    def test_for_loopvar_var_name_missing(self):
        """"""
        variables = {'not_here': 'test'}
        step = ParseComplexStep({r"for i in 1\n2\n3\n4": ["echo < <i>_v>"]})

        self.assertRaises(
            ErrorCollection,
            step.execute,
                variables, 'test')

    def test_for_none_steps(self):
        """"""
        step = {r"for i in 1\n2\n3\n4": None}
        self.assertEquals(ParseComplexStep(step), None)

    def test_parallel_step(self):
        """"""
        step = {r"parallel": ["echo a", "echo b"],}
        step = ParseComplexStep(step)
        self.assertEquals(isinstance(step, ParallelSteps), True)
        step.execute({}, "run")

    def test_parallel_too_many_statements(self):
        """"""
        step = {r"parallel": ["echo a", "echo b"], 'another' : None}
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)

    def test_parallel_empty_steps(self):
        """"""
        step = {r"parallel": [],}
        step = ParseComplexStep(step)
        self.assertEquals(isinstance(step, ParallelSteps), True)
        step.execute({}, "run")

    #def test_parallel_non_command_step(self):
    #    """"""
    #    step = {r"parallel": ['set x = 34'],}
    #    ParseComplexSte,(
    #            step)

    def test_unknown_step(self):
        """"""
        step = {r"blah": None,}
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)

    def test_empty_steps(self):
        step = {r"if 1": [None, None], 'else': [None, None]}
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)


class ParallelStepTests(unittest.TestCase):
    def test_empty_steps(self):
        step = {r"parallel": ["dir \\", "dir \\"]}
        ParseComplexStep(step).execute({}, 'run')
        ParseComplexStep(step).execute({}, 'test')

    def test_with_var_def(self):
        step = {r"parallel": ["set x= 1"]}
        ParseComplexStep(step).execute({}, 'run')
        ParseComplexStep(step).execute({}, 'test')

    def test_with_error(self):
        step = {r"parallel": ["dir NO FIL EXISTS HERE"]}
        self.assertRaises(
            RuntimeError,
            ParseComplexStep(step).execute,
                {}, 'run')

        ParseComplexStep(step).execute({}, 'test')


class StepTests(unittest.TestCase):
    ""

    def test_basic_step(self):
        """"""
        s = Step("here")
        self.assertEquals(s.raw_step, "here")

    def test_basic_step_str(self):
        s = Step("here")
        self.assertEquals(s.__str__(), "here")

    def test_basic_step_repr(self):
        s = Step("here")
        self.assertEquals(s.__repr__(), "<Step here>")


class VariableDefinitionTests(unittest.TestCase):
    ""
    def test_basic_varstep(self):
        """"""
        s = VariableDefinition("set here=there")
        self.assertEquals(s.name, "here")
        self.assertEquals(s.value, "there")

    def test_replace_vars(self):
        s = VariableDefinition("set here=<there>")
        vars = {'there': 'value'}
        s.execute(vars, phase = "test")
        self.assertEquals(vars['here'], 'value')

        #s.replace_vars({'there': 'value'}, update = True)
        #self.assertEquals(s.value, 'value')

    #def test_replace_vars_missing(self):
    #    s = VariableDefinition("set here=<not_there>")
    #    # even though it is missing it should NOT raise an error
    #    # as the variable may be defined later
    #    s.execute({'there': 'value'}, phase = "run")
    #    self.assertEquals(s.value, "<not_there>")

    def test_execute_good(self):
        s = VariableDefinition("set here=test_value")
        variables = {}
        s.execute(variables, phase = 'run')
        self.assertEquals(variables['here'], 'test_value')

    def test_execute_bad(self):
        s = VariableDefinition("set here={{{<not_there>}}}")

        self.assertRaises(
            ErrorCollection,
            s.execute,
                {}, "run")

    def test_execute_ok_loop(self):
        steps = ParseSteps([
            "set x = 0" ,
            "set x= <x> + 1",
            "set x= <x> + 2"])

        variables = {}
        for s in steps:
            s.execute(variables, "run")

        self.assertEquals(
            ReplaceVariableReferences("<x>", variables),
            "0 + 1 + 2")

    def test_execute_bad_loop(self):
        steps = ParseSteps([
                "set x = 345 " ,
                "set y = <x> + 2",
                "echo <x>",])

        variables = {}
        for s in steps:
            s.execute(variables, "run")

    def test_basic_step_repr(self):
        s = VariableDefinition("set _yikes_=_close_")
        self.assertEquals(s.__repr__(), '"_close_"')

    def test_delayed_step(self):
        vars = {'a': 'here'}
        s = VariableDefinition("set _yikes_=_close_ <a> {*delayed*}")
        s.execute(vars, "run")

        self.assertEquals(vars["_yikes_"], '_close_ <a>')

    def test_not_delayed_step(self):
        vars = {'a': 'here'}
        s = VariableDefinition("set _yikes_=_close_ <a>")
        s.execute(vars, "run")

        self.assertEquals(vars["_yikes_"], '_close_ here')


class EndExecutionTests(unittest.TestCase):
    ""
    def test_construct(self):
        """"""
        e = EndExecution(123, "hi")
        self.assertEquals(e.ret, 123)
        self.assertEquals(e.msg, "hi")


class ExecutionEndStepTests(unittest.TestCase):
    ""
    def test_construct(self):
        """"""
        e = ExecutionEndStep("end 123 ,hi ")
        self.assertEquals(e.ret, 123)
        self.assertEquals(e.message, "hi")

    def test_construct_no_message(self):
        """"""
        e = ExecutionEndStep("end 123 , ")
        self.assertEquals(e.ret, 123)
        self.assertEquals(e.message, "")

        e = ExecutionEndStep("end 123 ")
        self.assertEquals(e.ret, 123)
        self.assertEquals(e.message, "")

    def test_do_not_exit_when_testing(self):
        """"""
        step = ExecutionEndStep("end 123, hi")
        step.execute({}, phase = "test")

    def test_construct_bad_return_code(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ExecutionEndStep,
                "end 123d, hi")

    def test_replace_vars_update_false(self):
        """"""
        variables = {'hi': "there"}
        e = ExecutionEndStep("end  123 , <hi>")

        e.execute(variables, phase = "test")
        self.assertEquals(e.msg, "<hi>")

    def test_replace_vars_update_true(self):
        """"""
        variables = {'hi': "there"}
        e = ExecutionEndStep("end 123, <hi>")

        try:
            e.execute(variables, phase = "run")
        except EndExecution, err:
            self.assertEquals(err.msg, "there")

    def test_replace_vars_update_false(self):
        """"""
        e = ExecutionEndStep("end 123, hi")

        self.assertRaises(
            EndExecution,
            e.execute,
                {}, "run")

    def test_replaced_exe_sections(self):
        """"""
        vars = {'name': 'john'}
        e = ExecutionEndStep("end 123, hi {{{ uppercase <name> }}}")
        try:
            e.execute(vars, phase = "run")
        except EndExecution, err:
            self.assertEquals(err.msg, "hi JOHN")



def DebugAction(to_exec, dummy = None):
    exec to_exec
    return 0, "no message"
built_in_commands.NAME_ACTION_MAPPING['debug'] = DebugAction


class CommandStepTests(unittest.TestCase):
    ""
    def test_command_as_string_for_log_list(self):
        """"""
        c = CommandStep("test")
        self.assertEquals(
            c.command_as_string_for_log('', ['1', '2', '3']),
            "'test' -> '1 2 3'")

    def test_command_as_string_for_log_long_string_diff(self):
        """"""
        c = CommandStep("test")
        self.assertEquals(
            c.command_as_string_for_log('', "s" * 300),
            "'test' -> '%s'"% ("s"*300))

    def test_command_as_string_for_log_long_string_equal(self):
        """"""
        c = CommandStep("s" * 300)
        self.assertEquals(
            c.command_as_string_for_log("", "s" * 300),
            "'%s'"% ("s"*300) )

    def test_Step_interupted_continue(self):
        """"""
        old_stdin = sys.stdin
        sys.stdin = open(os.path.join(TEST_FILES_PATH, "no.txt"), "r")

        CommandStep('debug raise KeyboardInterrupt()').execute({}, "run")
        sys.stdin.close()
        sys.stdin = old_stdin

    def test_Step_interupted_stop(self):
        """"""
        old_stdin = sys.stdin
        sys.stdin = open(os.path.join(TEST_FILES_PATH, "yes.txt"), "r")
        s = CommandStep('debug raise KeyboardInterrupt')

        self.assertRaises(RuntimeError, s.execute, {}, "run")

        sys.stdin.close()
        sys.stdin = old_stdin

    def test_Step_no_output(self):
        """"""

        s = CommandStep('cd \\')

        s.execute({}, "run")
        self.assertEquals(s.output, "")

    def test_Step_no_error_and_output(self):
        """"""

        s = CommandStep('dir')

        s.execute({}, "run")
        self.assertEquals(s.ret, 0)

    def test_error_collection_in_execute(self):
        """"""

        s = CommandStep("robocopy123 <abc> c:\\temp\\")
        self.assertRaises(
            ErrorCollection,
            s.execute,
            {}, 'test', )


class EchoStepTests(unittest.TestCase):
    def test_with_as_error(self):
        """"""
        s = EchoStep('echo some text ')
        self.assertEquals(s.qualifiers, [])
        self.assertEquals(s.message, "some text")
        s.execute("run")
        self.assertEquals(s.output, "")
        s.execute("test")
        self.assertEquals(s.message, s.output)

    def test_with_as_debug(self):
        """"""
        s = EchoStep('echo some text {*as_debug*}')
        self.assertEquals(s.qualifiers, ["as_debug"])
        s.execute({}, "run")
        self.assertEquals(s.message, s.output)

    def test_with_as_warning(self):
        """"""
        s = EchoStep('echo some text {*as_warning*}')
        self.assertEquals(s.qualifiers, ["as_warning"])
        s.execute({}, "run")
        self.assertEquals(s.message, s.output)

    def test_with_as_error(self):
        """"""
        s = EchoStep('echo some text {*as_error*}')
        self.assertEquals(s.qualifiers, ["as_error"])
        s.execute({}, "run")
        self.assertEquals(s.message, s.output)

    def test_with_as_fatal(self):
        """"""
        s = EchoStep('echo some text {*as_fatal*}')
        self.assertEquals(s.qualifiers, ["as_fatal"])
        s.execute({}, "run")
        self.assertEquals(s.message, s.output)


class IncludeStepTests(unittest.TestCase):
    # log file testing is more or less the same as this!
    class_under_test = IncludeStep
    def test_file_not_existing(self):
        step = self.__class__.class_under_test("include file_doesn't_exist.bb")
        variables =  {"__script_dir__": "a"}
        step.execute(variables, 'test')

        self.assertRaises(
            IOError,
            step.execute,
               variables, 'run')

    def test_optional_file_not_existing(self):
        step = self.__class__.class_under_test(
            "include file_doesn't_exist.bb {*optional*}")
        variables =  {"__script_dir__": os.environ['temp']}
        step.execute(variables, 'test')
        step.execute(variables, 'run')

    def test_include_empty_file(self):
        self.assertRaises(
            RuntimeError,
            self.__class__.class_under_test,
                "include")

    def test_include_variable_in_filename(self):
        variables =  {
            "__script_dir__": TEST_FILES_PATH,
            'file_to_include': "basic_set_var.bb",}

        step = self.__class__.class_under_test("include <file_to_include>")
        step.execute(variables, "test")
        step.execute(variables, "run")

    def test_include_file_with_execute_errors(self):
        variables =  {
            "__script_dir__": TEST_FILES_PATH,
        }
        inc_step = IncludeStep(
            "include <__script_dir__>\include_with_errors.bb")

        self.assertRaises(
            RuntimeError,
            inc_step.execute,
                variables, 'run')

        inc_step.execute(variables, 'test')

    def test_optional_include_file_with_errors(self):
        variables =  {
            "__script_dir__": TEST_FILES_PATH,
        }
        inc_step = IncludeStep(
            "include <__script_dir__>\include_with_errors.bb {*optional*}")

        inc_step.execute(variables, 'test')

        self.assertRaises(
            RuntimeError,
            inc_step.execute,
                variables, 'run')

    def test_include_file_with_execute_only_errors(self):
        variables =  {
            "__script_dir__": TEST_FILES_PATH,
        }
        inc_step = IncludeStep(
            "include <__script_dir__>\include_with_missing_var_ref.bb")

        inc_step.execute(variables, 'test')

        self.assertRaises(
            RuntimeError,
            inc_step.execute,
                variables, 'run')

    def test_include_file_with_loopvar(self):
        steps = ParseSteps([{
            "for x in {{{ split basic.bb basic_set_var.bb }}}" :
                "include <x>"}])

        vars = {'__script_dir__': TEST_FILES_PATH}
        ExecuteSteps(steps, vars, "run")
        self.assertEqual(vars["test"], "Hello World")


#    def test_include_without_script_dir(self):
#        inc_step = IncludeStep(
#            "include %s" % os.path.join(TEST_FILES_PATH, "basic_set_var.bb"))
#
#        inc_step.execute({}, 'test')


class LogFileStepTests(IncludeStepTests):
    class_under_test = LogFileStep
    test_file_not_existing = lambda x: 1
    test_optional_file_not_existing = lambda x: 1
    test_optional_include_file_with_errors = lambda x: 1


class VariableDefinedCheckTests(unittest.TestCase):
    def test_emtpy_variable(self):
        self.assertRaises(
            RuntimeError,
            VariableDefinedCheck,
                "defined")

    def test_variable_defined(self):
        variables = {'test': "abc"}
        s = VariableDefinedCheck('defined test')

        s.execute(variables, 'test')
        self.assertEquals(s.ret, 0)
        s.execute(variables, 'run')
        self.assertEquals(s.ret, 0)

    def test_variable_not_defined(self):
        variables = {'test': "abc"}
        s = VariableDefinedCheck('defined test234')

        s.execute(variables, 'test')
        self.assertEquals(s.ret, 1)
        s.execute(variables, 'run')
        self.assertEquals(s.ret, 1)

    def test_ref_variable_defined(self):
        variables = {'test': "abc", "abc" : "yo"}
        s = VariableDefinedCheck('defined <test>')

        s.execute(variables, 'test')
        self.assertEquals(s.ret, 0)
        s.execute(variables, 'run')
        self.assertEquals(s.ret, 0)

    def test_variable_ref_not_defined(self):
        variables = {'test': "abc"}
        s = VariableDefinedCheck('defined <test234>')

        s.execute(variables, 'test')
        self.assertEquals(s.ret, 1)
        self.assertRaises(
            ErrorCollection,
            s.execute,
                variables, 'run')

    def test_ref_variable_not_defined(self):
        variables = {'test': "abc"}
        s = VariableDefinedCheck('defined <test>')

        s.execute(variables, 'test')
        self.assertEquals(s.ret, 1)
        s.execute(variables, 'run')
        self.assertEquals(s.ret, 1)



#class IncludeStepTests(unittest.TestCase):
#
#    def test_include_not_existing(self):
#        step = IncludeStep("include file_doesn't_exist.bb")
#        variables =  {"__script_dir__": "a"}
#        step.execute(variables, 'test')
#
#        self.assertRaises(
#            RuntimeError,
#            step.execute,
#               variables, 'run')
#
#    def test_include_empty_file(self):
#        self.assertRaises(
#            RuntimeError,
#            IncludeStep,
#                "include")
#
#    def test_include_variable_in_filename(self):
#        variables =  {
#            "__script_dir__": TEST_FILES_PATH,
#            'file_to_include': "basic_set_var.bb",}
#
#        step = IncludeStep("include <file_to_include>")
#        step.execute(variables, "test")
#        step.execute(variables, "run")
#

class ForStepTests(unittest.TestCase):

    def test_with_parallel_qualifier(self):
        step = {'for x in {{{split here there}}} {*parallel*}': ['echo 1']}
        ParseStep(step).execute({}, 'test')

    def test_loop_variables(self):
        step = {'for to_be_replaced in {{{ split bb }}}': ['ECHO < aa_<to_be_replaced>_cc >\n']}
        variables = {
            'aa_bb_cc': "var_replaced",
            'not_required': 'abc'
            }
        ParseStep(step).execute(variables,'test')

    def test_loop_variables_error(self):
        step = {'for to_be_replaced in {{{ split bb }}}': ['ECHO < aa_<to_be_replaced>_cc >\n']}
        self.assertRaises(ErrorCollection, ParseStep(step).execute, {},'test')


class IfStepTests(unittest.TestCase):

    def test_working_do(self):
        for filename in glob.glob(os.path.join(TEST_FILES_PATH, "if_else_*")):

            # skip tests which are meant to fail
            if 'if_else_broken' in filename:
                continue

            script_filepath = os.path.join(TEST_FILES_PATH, filename)
            vars = PopulateVariables(script_filepath, {})

            steps = LoadScriptFile(script_filepath)
            #steps = FinalizeSteps(steps, vars)

            try:
                ExecuteSteps(steps, vars, "run")

                #if "if_else_empty" in filename:
                #    self.assertEquals(steps[1].output.strip(), "")
                #else:
                #    self.assertEquals(steps[1].output.strip(), filename)

            except ErrorCollection, e:
                print "ERROR WHEN RUNNING", filename
                e.LogErrors()
                raise

    def test_broken_not_list(self):
        script_filepath = os.path.join(TEST_FILES_PATH,   "if_else_broken_not_list.bb")

        self.assertRaises(
            RuntimeError,
            LoadScriptFile,
                script_filepath)

    def test_broken_not_list2(self):
        script_filepath = os.path.join(TEST_FILES_PATH,   "if_else_broken_not_list2.bb")
        vars = PopulateVariables(script_filepath, {})
        try:

            steps = LoadScriptFile(script_filepath)
            steps = ExecuteSteps(steps, vars, 'test')

        except ErrorCollection, e:
            e.LogErrors()
            print e.errors

#
#    def test_broken_too_few_clauses(self):
#        vars = {}
#        try:
#            LoadAndCheckFile(
#                os.path.join(TEST_FILES_PATH, "if_else_broken_only_one.bb"),
#                vars)
#        except ErrorCollection, e:
#            print "\n\n"
#            e.LogErrors()
#        self.assertRaises(
#            ErrorCollection,
#            ExecuteSteps,
#                steps, vars)
#
    def test_broken_too_many_clauses(self):
        script_filepath = os.path.join(TEST_FILES_PATH,   "if_else_broken_too_many.bb")

        self.assertRaises(
            RuntimeError,
            LoadScriptFile,
                script_filepath)

    def test_broken_do_name(self):
        script_filepath = os.path.join(TEST_FILES_PATH,   "if_else_broken_do_name.bb")
        vars = PopulateVariables(script_filepath, {})

        steps = LoadScriptFile(script_filepath)
        steps = ExecuteSteps(steps, vars, 'test')

        ExecuteSteps(steps, vars, 'run')

    def test_broken_else_name(self):
        script_filepath = os.path.join(TEST_FILES_PATH, "if_else_broken_else_name.bb")

        self.assertRaises(
            RuntimeError,
            LoadScriptFile,
                script_filepath)

    def test_un_supported_condition_type(self):
        should_fail_steps = {
            "if robocopy x y z":
                "echo -<test>-"}

        ifstep = ParseComplexStep(should_fail_steps)
        self.assertRaises(
            RuntimeError,
            ExecuteSteps,
                [ifstep], {}, 'test')

    def test_minimal_if(self):
        pass

    def test_if_defined_not_defined(self):
        should_fail_steps = {
            "if defined test": "echo -<test>-",
            'else': "echo no"}
        ifstep = ParseComplexStep(should_fail_steps)
        steps = ExecuteSteps([ifstep], {}, 'test')

        ExecuteSteps(steps, {}, 'run')
        self.assertEquals(
            steps[0].steps_to_exec[0].output.strip(),
            "no")

    def test_if_defined_is_defined(self):
        should_fail_steps = {
            "if defined test": "echo -<test>-",
            'else': "echo no"}
        ifstep = ParseComplexStep(should_fail_steps)
        steps = ExecuteSteps([ifstep], {}, 'test')

        ExecuteSteps(steps, {}, 'run')
        self.assertEquals(
            steps[0].steps_to_exec[0].output.strip(),
            "no")

    def test_parse_with_not(self):
        step = ParseComplexStep({'if not exists': ["echo 1",]})
        self.assertEquals(step.conditions[0][1].negative_condition, True)
        self.assertEquals(step.conditions[0][1].step_data, "exists")

    def test_not_defined_undefined(self):
        steps = [
            #'set test = 1',
            {'if not defined test':
                ["set test = if_block"],
             'else':
                ["set test = else_block",]}
            ]

        vars = {}
        ExecuteSteps(ParseSteps(steps), vars, "test")
        self.assertEquals('test' in vars, False)
        ExecuteSteps(ParseSteps(steps), vars, "run")
        self.assertEquals(vars['test'], 'if_block')

    def test_not_defined_defined(self):
        steps = [
            'set test = 1',
            {'if not defined test':
                ["set test = if_block"],
             'else':
                ["set test = else_block",]}
            ]

        vars = {}
        ExecuteSteps(ParseSteps(steps), vars, "test")
        self.assertEquals(vars['test'], 'else_block')
        ExecuteSteps(ParseSteps(steps), vars, "run")
        self.assertEquals(vars['test'], 'else_block')

    def test_repr(self):
        step = {'if test': "echo hello"}

        if_step = ParseStep(step)

        self.assertEquals(
            repr(if_step),
            "<IF [('if', <CommandStep test>)]...>")

    def test_and_else_or_steps(self):
        step = {'and test': None}

        self.assertRaises(
            RuntimeError,
            ParseStep, step)

    def test_with_or_step(self):
        step = {'if test': [], 'or test3': ['echo 1']}
        ParseStep(step).execute({}, 'run')

    def test_with_and_step(self):
        step = {'if test': [], 'AND test3': ['BLAH']}
        ParseStep(step).execute({}, 'run')

    def test_with_and_or_step(self):
        step = {'if test': [], 'or test2': [], 'AND test3': ['BLAH']}
        self.assertRaises(
            RuntimeError,
            ParseStep,
                step)

    def test_condition_raising_exception(self):
        """Found on Dec 14, 2010 that an exception while evaluating a condition
        was actually being evaluated as true - but it should raise an 
        exception (prior to 1.3.0 - it should have been False"""
        raw_step = {'if compare abc = 1 {*asint*}': ['set blah=21']}

        ifstep = ParseComplexStep(raw_step)
        vars = {'blah': '42'}
        self.assertRaises(
            RuntimeError,
            ExecuteSteps,
                [ifstep], vars, 'run')


    def test_blank_argument(self):
        raw_step = {'if compare <abc> = 1': ['set blah=21']}
        ifstep = ParseComplexStep(raw_step)
        vars = {'abc': ''}
        self.assertRaises(
            RuntimeError,
            ifstep.execute,
                vars, 'run')



class PopulateVariablesTests(unittest.TestCase):
    def test_basic(self):
        vars = PopulateVariables("somefile.bb", {"testinG": "AbC", 't': 'v'})
        self.assertEqual(vars['testing'], "AbC")
        self.assertEqual(vars['t'], "v")


class ParseFunctionNameAndArgsTests(unittest.TestCase):
    def test_basic(self):
        name_args = "func_name (a, b, c=2,)"

        name, args = ParseFunctionNameAndArgs(name_args, 'definition')

        self.assertEquals(name, "func_name")
        self.assertEquals(len(args), 3)
        self.assertEquals(args[0], ("a", None))
        self.assertEquals(args[1], ("b", None))
        self.assertEquals(args[2], ("c", "2"))

    def test_invalid(self):
        name_args = "func_name (a, b, c"

        self.assertRaises(
            RuntimeError,
            ParseFunctionNameAndArgs,
                name_args, 'definition')

    def test_non_default_after_default(self):
        name_args = "func_name (a, b=34, c)"

        self.assertRaises(
            RuntimeError,
            ParseFunctionNameAndArgs,
                name_args, 'definition')

    def test_arg_with_space_def(self):
        name_args = "func_name (this is a test)"

        self.assertRaises(
            RuntimeError,
            ParseFunctionNameAndArgs,
                name_args, 'definition')

    def test_arg_with_space_call(self):
        name_args = "func_name (this is a test)"

        name, args = ParseFunctionNameAndArgs(name_args, 'call')
        self.assertEquals(name, "func_name")
        self.assertEquals(args[0], (None, "this is a test"))


    def test_embedded_paren(self):
        name_args = 'func_name (this is() a test, abc=123)'
        name, args = ParseFunctionNameAndArgs(name_args, "call")

        self.assertEquals(name, "func_name")
        self.assertEquals(len(args), 2)
        self.assertEquals(
            tuple(args),
            ((None, "this is() a test"), ("abc", "123")))


class ParseFunctionDefinitionTests(unittest.TestCase):
    def test_basic(self):
        func = ParseComplexStep({"function test(1)": ["echo 1", 'echo 2']})

        self.assertEquals(func.steps[0].raw_step, "echo 1")

    def test_more_than_one_header(self):
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                {"function test(a)": ["echo 1", 'echo 2'],
                "function test(b)": ["echo 1", 'echo 2']})

    def test_more_no_steps(self):
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                {"function test(a)": []})


class FunctionDefinitionTests(unittest.TestCase):
    def test_basic(self):
        vars = {"c": 'here'}

        step = {"function test(a)": ["echo <a>", 'echo 2']}
        func = ParseComplexStep(step)

        func.execute(vars, "test")
        func.execute(vars, "run")
        func.call_function(({'a': '123'}), vars, 'test')
        func.call_function(({'a': '123'}), vars, 'run')

    def test_test_error(self):
        vars = {"c": 'here'}

        step = {"function test(a)": ["echo <a>", 'echo <b>']}
        func = ParseComplexStep(step)

        self.assertRaises(
            ErrorCollection,
            func.call_function,
                ({'a': '123'}), vars, "test")


class ValidateArgumentCountsTests(unittest.TestCase):
    def test_no_count(self):
        x = CommandStep('robocopy')
        ValidateArgumentCounts([x], {})

    def test_count(self):
        x = CommandStep('robocopy')
        ValidateArgumentCounts([x], {'robocopy': (0,1)})

    def test_count_error_too_few(self):
        x = CommandStep('robocopy 1 2 3')
        self.assertRaises(
            RuntimeError,
            ValidateArgumentCounts,
                [x], {'robocopy': (4,5)})

    def test_count_error_just_right(self):
        x = CommandStep('robocopy 1 2 3 4')
        ValidateArgumentCounts([x], {'robocopy': (4,4)})

    def test_count_error_too_many(self):
        x = CommandStep('robocopy 1 2 3 4 5 6')
        self.assertRaises(
            RuntimeError,
            ValidateArgumentCounts,
                [x], {'robocopy': (4,5)})


class FunctionCallTests(unittest.TestCase):
    def test_working(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(a)": ["echo <a>", 'echo 2'], },
            "call test(1)",]
        steps = ParseSteps(steps)
        ExecuteSteps(steps, vars, "test")

    def test_use_default(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(a, b=1)": ["echo <a>, <b>"], },
            "call test(1)",]
        steps = ParseSteps(steps)
        ExecuteSteps(steps, vars, "test")

    def test_no_function(self):
        vars = {"c": 'here'}

        step = ParseStep("call test1234567(a)")

        self.assertRaises(
            RuntimeError,
            step.execute,
                vars, "test")

    def test_too_many_args(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(a)": ["echo <a>", 'echo 2'], },
            "call test(1,2,3)",]
        steps = ParseSteps(steps)
        self.assertRaises(
            ErrorCollection,
            ExecuteSteps,
                steps, vars, "test")

    def test_positional(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(a, b)": ["echo <a>", 'echo 2'], },
            "call test(1, b=3)",]
        steps = ParseSteps(steps)
        ExecuteSteps(steps, vars, "test")

    def test_arg_supplied_as_pos_and_keyword(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(a, b)": ["echo <a>", 'echo 2'], },
            "call test(1, a = 3)",]
        steps = ParseSteps(steps)
        self.assertRaises(
            RuntimeError,
            ExecuteSteps,
                steps, vars, "test")

    def test_arg_supplied_as_keyword_twice(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(a, b)": ["echo <a>", 'echo 2'], },
            "call test(a = 2, a = 3)",]
        self.assertRaises(
            RuntimeError,
            ParseSteps,
                steps)

    def test_unmatched_args(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(a, b)": ["echo <a>"], },
            "call test(1, g = 3)",]
        steps = ParseSteps(steps)
        self.assertRaises(
            RuntimeError,
            ExecuteSteps,
                steps, vars, "test")

    def test_positional_after_keyword(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(xyz, bcd)": ["echo <a>"], },
            "call test(xyz = 3, 1)",]
        self.assertRaises(
            RuntimeError,
            ParseSteps,
                steps)

    def test_no_value_passed_for_arg(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(xyz, bcd)": ["echo <a>"], },
            "call test(1)",]
        steps = ParseSteps(steps)
        self.assertRaises(
            RuntimeError,
            ExecuteSteps,
                steps, vars, "test")

    # bug reported by Jan Svoboda
    # value passed directly to a function (not through a variable)
    # was always showing in lowercase - they shouldn't be
    def test_BUG_values_passed_as_lowercase(self):
        vars = {}
        steps = [
            {"function test(xYz, AbCd)": ["return <XyZ> <aBcD>"], },
            "set x = {{{ call test(TeSt1, tEsT2) }}}",]
        steps = ParseSteps(steps)
        ExecuteSteps(steps, vars, "run")
        print vars
        self.assertEquals(vars['x'], "TeSt1 tEsT2")


class FunctionReturnTests(unittest.TestCase):
    def test_single_step(self):
        vars = {}
        steps = [
            {"function test(a)": ['return <a>1'], },
            "set b = {{{ call test(1) }}}",]
        steps = ParseSteps(steps)
        steps = ExecuteSteps(steps, vars, "test")
        self.assertEquals(vars['b'], '11')

    def test_steps_after_return_run(self):
        vars = {}
        steps = [
            {"function test(a)": ['return <a>2', 'echo ' + '9'*8000 ], },
            "set b = {{{ call test(2) }}}",]
        steps = ParseSteps(steps)
        steps = ExecuteSteps(steps, vars, "run")
        self.assertEquals(vars['b'], '22')

    def test_steps_after_return_test(self):
        vars = {}
        steps = [
            {"function test(a)": [
                'return <a>3',
                'echo ' + '9'*8000 ],
            },
            "set b = {{{ call test(3) }}}",]
        steps = ParseSteps(steps)

        steps = ExecuteSteps(steps, vars, "test")
        self.assertEquals(vars['b'], '33')

    def test_steps_no_return_no_output(self):
        vars = {}
        steps = [
            {"function test(a)": ['set x = 3 '], },
            "set b = {{{ call test(4) }}}",]
        steps = ParseSteps(steps)
        self.assertRaises(
            RuntimeError,
            ExecuteSteps,
                steps, vars, "run")

    def test_return_in_nested_block(self):
        "Test that a return works correctly if inside an if, for, nested block"
        vars = {}
        steps = [
            {"function test(a)": [
                {'for x in a:': ["return <a>5"]}]
            },
            "set b = {{{ call test(5) }}}",]
        steps = ParseSteps(steps)
        #import pdb; pdb.set_trace()

        steps = ExecuteSteps(steps, vars, "run")
        self.assertEquals(vars['b'], '55')


class ParseStepsTests(unittest.TestCase):
    def test_single_step(self):
        ParseSteps(["set z = <a>", "set n = <b>",])

class ApplyCommandLineVarsStepTests(unittest.TestCase):

    def test_basic_override(self):
        ApplyCommandLineVarsStep.cmd_line_vars = {'yo': 'there'}
        variables = {'yo': 'not_there'}
        ApplyCommandLineVarsStep("").execute(variables, "test")
        self.assertEqual(variables, {'yo': 'there'})

        variables = {'yo': 'not_there'}
        ApplyCommandLineVarsStep("").execute(variables, "run")
        self.assertEqual(variables, {'yo': 'there'})

    def test_basic_add_new(self):
        ApplyCommandLineVarsStep.cmd_line_vars = {'yot': 'there'}
        variables = {'yo': 'not there'}
        ApplyCommandLineVarsStep("").execute(variables, "test")
        self.assertEqual(variables['yot'], 'there')
        self.assertEqual(variables['yo'], 'not there')

        variables = {'yo': 'not there'}
        ApplyCommandLineVarsStep("").execute(variables, "run")
        self.assertEqual(variables['yot'], 'there')
        self.assertEqual(variables['yo'], 'not there')


class CheckAllScriptsInDirTests(unittest.TestCase):
    def test_check_all_scripts_in_dir_errors(self):
        test_dir = os.path.join(
            TEST_FILES_PATH, "check_all_scripts_in_dir_with_errors")
        num_errors = CheckAllScriptsInDir(test_dir, {})
        self.assertEqual(num_errors, 1)

    def test_check_all_scripts_in_dir_no_errors(self):
        test_dir = os.path.join(
            TEST_FILES_PATH, "check_all_scripts_in_dir_without_errors")
        num_errors = CheckAllScriptsInDir(test_dir, {})
        self.assertEqual(num_errors, 0)

    def test_check_dir_with_broken_scripts(self):
        num_errors = CheckAllScriptsInDir(TEST_FILES_PATH, {})
        self.assertEqual(num_errors > 1, True)


class ExecuteScriptFileTests(unittest.TestCase):
    def test_usage_is_printed(self):
        path = os.path.join(TEST_FILES_PATH, "missing_variable.bb")
        ExecuteScriptFile(path, {})


class IntegrationTests(unittest.TestCase):

    def test_mixed_case_variable_usage(self):
        # validate that variables defined in one case can be used
        # in any case
        vars = {}
        steps = ParseSteps(["set A = Abc", "set n = <a>", "echo <n>"])
        ExecuteSteps(steps, vars, "run")

        self.assertEquals(vars['n'], "Abc")

        steps = ParseSteps(["set a = Abc", "set n = <A>", "echo <n>"])
        ExecuteSteps(steps, vars, "run")


class MainTests(unittest.TestCase):

    def test_GetValidatedOptions_exception(self):
        sys.argv = ["", "does not exist.bb"]
        try:
            Main()
        except SystemExit, e:
            self.assertEqual(e.code, 1)

    def test_check_dirs_fail(self):
        script_path = os.path.join(
                TEST_FILES_PATH,
                "check_all_scripts_in_dir_with_errors",
                "bb_script_with_no_command_path_errors.bb")
        sys.argv = [
            "",
            script_path,
            "-j"]
        try:
            Main()
        except SystemExit, e:
            self.assertEqual(e.code, 1)

    #def test_no_steps(self):
    #    sys.argv = ["", os.path.join(TEST_FILES_PATH, "empty.bb")]
    #    Main()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("test_parsescript")
    # needs to be called before importing the modules
    import coverage
    cov = coverage.coverage(branch = True)
    cov.start()
    unittest.TextTestRunner(verbosity=1).run(suite)
    cov.stop()
    print cov.report([parsescript])
