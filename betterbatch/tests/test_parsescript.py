import unittest
import os
import logging
import glob

import sys
# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(package_root)

import parsescript
from parsescript import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


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
            RuntimeError,
            ParseYAMLFile,
                "some non existant file")

    def test_scanner_error(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'scanner_error.yaml')
        self.assertRaises(
            RuntimeError,
            ParseYAMLFile,
                full_path)

    def test_parser_error(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'parser_error.yaml')
        self.assertRaises(
            RuntimeError,
            ParseYAMLFile,
                full_path)

    def test_colon_mid_string(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'parser_error.yaml')
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
            ["set  Hello  =  .", "cd  <hello>"])

    def test_empty_file(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'empty_file.bb')
        steps = ParseYAMLFile(full_path)
        self.assertEquals(steps, None)

    def test_numeric_value(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'number.yaml')
        self.assertRaises(
            RuntimeError,
            ParseYAMLFile,
                full_path)


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

    def test_repr__(self):
        """"""
        errs = ['err1', "err1"]

        collection = ErrorCollection(errs)
        repr(collection)


class ParseVariableDefinitionTests(unittest.TestCase):
    "Unit tests for the commands"

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
            ParseVariableDefinition('blah', allow_no_value = True))

    def test_no_value_equals_allowed(self):
        self.assertEquals(
            ('blah', ''),
            ParseVariableDefinition('blah=', allow_no_value = True))

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


def CloserAndRemoveLogHanlderwithPath(path):
    for h in LOG.handlers:
        if hasattr(h, 'baseFilename') and h.baseFilename == path:
            h.flush()
            LOG.removeHandler(h)
            h.stream.close()

            os.unlink(path)


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
        step = {r"if 1": None,}
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


class IncludeStepTests(unittest.TestCase):
    class_under_test = IncludeStep
    def test_file_not_existing(self):
        step = self.__class__.class_under_test("include file_doesn't_exist.bb")
        variables =  {"__script_dir__": "a"}
        step.execute(variables, 'test')

        self.assertRaises(
            RuntimeError,
            step.execute,
               variables, 'run')

    def test_include_empty_file(self):
        self.assertRaises(
            RuntimeError,
            self.__class__.class_under_test,
                "include")

    def test_include_variable_in_filename(self):
        variables =  {
            "__script_dir__": TEST_FILES_PATH,
            'file_to_include': "basic.yaml",}

        step = self.__class__.class_under_test("include <file_to_include>")
        step.execute(variables, "test")
        step.execute(variables, "run")


class LogFileStepTests(IncludeStepTests):
    class_under_test = LogFileStep
    test_file_not_existing = lambda x: 1


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

    def test_variable_defined_brakets(self):
        variables = {'test': "abc"}
        s = VariableDefinedCheck('defined <test>')

        s.execute(variables, 'test')
        self.assertEquals(s.ret, 0)
        s.execute(variables, 'run')
        self.assertEquals(s.ret, 0)

    def test_variable_not_defined_brackets(self):
        variables = {'test': "abc"}
        s = VariableDefinedCheck('defined <test234>')

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
#            'file_to_include': "basic.yaml",}
#
#        step = IncludeStep("include <file_to_include>")
#        step.execute(variables, "test")
#        step.execute(variables, "run")
#

class ForStepTests(unittest.TestCase):

    def test_with_parallel_qualifier(self):
        step = {'for x in {{{split here there}}} {*parallel*}': ['echo 1']}
        ParseStep(step).execute({}, 'test')


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
        script_filepath = os.path.join(TEST_FILES_PATH,   "if_else_broken_not_list.yaml")

        self.assertRaises(
            RuntimeError,
            LoadScriptFile,
                script_filepath)

    def test_broken_not_list2(self):
        script_filepath = os.path.join(TEST_FILES_PATH,   "if_else_broken_not_list2.yaml")
        vars = PopulateVariables(script_filepath, {})
        try:

            steps = LoadScriptFile(script_filepath)
            steps = ExecuteSteps(steps, vars, 'test')

        except ErrorCollection, e:
            e.LogErrors()
            print e.errors
            import pdb; pdb.set_trace()

#
#    def test_broken_too_few_clauses(self):
#        vars = {}
#        try:
#            LoadAndCheckFile(
#                os.path.join(TEST_FILES_PATH, "if_else_broken_only_one.yaml"),
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
        script_filepath = os.path.join(TEST_FILES_PATH,   "if_else_broken_too_many.yaml")

        self.assertRaises(
            RuntimeError,
            LoadScriptFile,
                script_filepath)

    def test_broken_do_name(self):
        script_filepath = os.path.join(TEST_FILES_PATH,   "if_else_broken_do_name.yaml")
        vars = PopulateVariables(script_filepath, {})

        steps = LoadScriptFile(script_filepath)
        steps = ExecuteSteps(steps, vars, 'test')

        ExecuteSteps(steps, vars, 'run')

    def test_broken_else_name(self):
        script_filepath = os.path.join(TEST_FILES_PATH, "if_else_broken_else_name.yaml")

        self.assertRaises(
            RuntimeError,
            LoadScriptFile,
                script_filepath)

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



class ParseFunctionNameAndArgsTests(unittest.TestCase):
    def test_basic(self):
        name_args = "func_name (a, b, c=2,)"

        name, args = ParseFunctionNameAndArgs(name_args)

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
                name_args)

    def test_non_default_after_default(self):
        name_args = "func_name (a, b=34, c)"

        self.assertRaises(
            RuntimeError,
            ParseFunctionNameAndArgs,
                name_args)


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
            func.execute,
                vars, "test")

        func.execute(vars, "run")


class FunctionCallTests(unittest.TestCase):
    def test_working(self):
        vars = {"c": 'here'}
        steps = [
            {"function test(a)": ["echo <a>", 'echo 2'], },
            "call test(1)",]
        steps = ParseSteps(steps)
        ExecuteSteps(steps, vars, "test")

    def test_no_function(self):
        vars = {"c": 'here'}

        step = ParseStep("call test(a)")

        step.execute(vars, "test")

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
        ExecuteSteps(steps, vars, "test")


class FunctionReturnTests(unittest.TestCase):
    def test_single_step(self):
        vars = {}
        steps = [
            {"function test(a)": ['return <a>2'], },
            "set b = {{{ call test(1) }}}",]
        steps = ParseSteps(steps)
        steps = ExecuteSteps(steps, vars, "test")
        self.assertEquals(vars['b'], '12')

    def test_steps_after_return_run(self):
        vars = {}
        steps = [
            {"function test(a)": ['return <a>2', 'echo ' + '9'*8000 ], },
            "set b = {{{ call test(1) }}}",]
        steps = ParseSteps(steps)
        steps = ExecuteSteps(steps, vars, "run")
        self.assertEquals(vars['b'], '12')

    def test_steps_after_return_test(self):
        vars = {}
        steps = [
            {"function test(a)": ['return <a>2', 'echo ' + '9'*8000 ], },
            "set b = {{{ call test(1) }}}",]
        steps = ParseSteps(steps)
        steps = ExecuteSteps(steps, vars, "test")
        self.assertEquals(vars['b'], '12')

    def test_steps_no_return_no_output(self):
        vars = {}
        steps = [
            {"function test(a)": ['set x = 3 '], },
            "set b = {{{ call test(1) }}}",]
        steps = ParseSteps(steps)
        self.assertRaises(
            RuntimeError,
            ExecuteSteps,
                steps, vars, "test")


class ParseStepsTests(unittest.TestCase):
    def test_single_step(self):
        ParseSteps(["set z = <a>", "set n = <b>",])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("test_parsescript")
    # needs to be called before importing the modules
    import coverage
    cov = coverage.coverage(branch = True)
    cov.start()
    unittest.TextTestRunner(verbosity=1).run(suite)
    cov.stop()
    print cov.report([parsescript])
