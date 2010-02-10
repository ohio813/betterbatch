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


class DummyVar(object):
    def __init__(self, val):
        self.value = val


class ReplaceVariableReferencesTests(unittest.TestCase):

    def test_no_refs(self):
        """"""
        new = ReplaceVariableReferences("here", {})
        self.assertEquals("here", new)

    def test_exact_match(self):
        """"""
        new = ReplaceVariableReferences(
            "<here>", {'here': DummyVar('there')})
        self.assertEquals("there", new)

    def test_with_spaces(self):
        """"""
        new = ReplaceVariableReferences(
            " < here   >", {'here': DummyVar('there')})
        self.assertEquals(" there", new)

    def test_gt_escaping(self):
        """"""
        new = ReplaceVariableReferences(
            ">> <here>>>", {'here': DummyVar('there')})
        self.assertEquals("> there>", new)

    def test_lt_escaping(self):
        """"""
        new = ReplaceVariableReferences(
            "<< <<<here>>>", {'here': DummyVar('there')})
        self.assertEquals("< <there>", new)

    def test_missing_var(self):
        """"""
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<not_here>", {'here': DummyVar('there')})

    def test_recursive_var_err(self):
        """"""
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<here>", {
                    'here': DummyVar('<there>'),
                    'there': DummyVar('<here>')})

    def test_recursive_var_good(self):
        """"""
        new_val = ReplaceVariableReferences("x<here>x", {
                'here': DummyVar('-<there>-'),
                'there': DummyVar('my value')})

        self.assertEquals(new_val, "x-my value-x")

    def test_2nd_level_undefined(self):
        """"""
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<here>", {
                    'here': DummyVar('<not_there>'),
                    'there': DummyVar('<here>')})

    def test_2nd_level_single_var_loop(self):
        """"""
        variables = {'x': DummyVar("uses <x>")}
        ReplaceVariableReferences("using <x> again", variables)

    def test_2nd_level_multiple_var_loop(self):
        """"""
        variables = {
            'x': DummyVar("uses <y>"),
            'y': DummyVar("uses <x>"),
            }
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<x>", variables)

class ReplaceVariablesInStepsTests(unittest.TestCase):
    """"""
    def test_normal_no_update(self):
        steps = [
            ParseStep("cd <var1>"),
            ParseStep("echo <var1>")]
        ReplaceVariablesInSteps(
            steps, {'var1': DummyVar('here')}, update = False)

        self.assertEquals(steps[0].step_data, "cd <var1>")
        self.assertEquals(steps[1].step_data, "echo <var1>")

    def test_normal_update(self):
        steps = [
            ParseStep("cd <var1>"),
            ParseStep("echo <var1>")]
        ReplaceVariablesInSteps(
            steps, {'var1': DummyVar('here')}, update = True)

        self.assertEquals(steps[0].step_data, "cd here")
        self.assertEquals(steps[1].step_data, "echo here")


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
                {'value': DummyVar('car')}, execute=True),
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
                " -  {{{echo This value}}}  - ", {}, execute = False),
            " -  {{{echo This value}}}  - ")

    def test_simple_with_var_execute(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(
                "here {{{echo This <value>}}} <value>",
                {'value': DummyVar('car')}, ),
            "here This car <value>")

    def test_simple_with_var_no_execute(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(
                "here {{{echo This <value>}}} <value>",
                {'value': DummyVar('car')}, execute=False),
            "here {{{echo This <value>}}} <value>")

    def test_not_a_command(self):
        """"""
        text = "{{{cd here}}} echo This <var>"
        variables = {'var': DummyVar('car')}
        self.assertRaises(
            RuntimeError,
            ReplaceExecutableSections,
                text, variables, )

    def test_with_embedded_braces(self):
        """"""
        text = "{{{cd {{{ echo hi echo This <var>}}}"
        variables = {'var': DummyVar('car')}
        self.assertRaises(
            RuntimeError,
            ReplaceExecutableSections,
                text, variables, )

    def test_command_fails(self):
        """"""
        text = "{{{ _bad_command_or_filename_ }}}"
        variables = {'var': DummyVar('car')}
        self.assertRaises(
            RuntimeError,
            ReplaceExecutableSections,
                text, variables, )

    def test_trailing_braces(self):
        """"""
        text = "{{{ echo <var> {*nocheck*}}}}-"
        variables = {'var': DummyVar('car')}
        replaced = ReplaceExecutableSections(text, variables)
        self.assertEquals(replaced, "car-")


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


    def test_for_step(self):
        """"""
        step = {r"for": None,}
        self.assertRaises(
            NotImplementedError,
            ParseComplexStep,
                step)

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
        s = VariableDefinition("set here=there", "here=there")
        self.assertEquals(s.name, "here")
        self.assertEquals(s.value, "there")

    def test_replace_vars(self):
        s = VariableDefinition("set here=<there>", "here=<there>")
        s.replace_vars({'there': DummyVar('value')}, update = False)
        self.assertEquals(s.value, '<there>')

        #s.replace_vars({'there': DummyVar('value')}, update = True)
        #self.assertEquals(s.value, 'value')

    def test_replace_vars_missing(self):
        s = VariableDefinition("set here=<there>", "here=<not_there>")
        # even though it is missing it should NOT raise an error
        # as the variable may be defined later
        s.replace_vars({'there': DummyVar('value')},update = True)
        self.assertEquals(s.value, "<not_there>")

    def test_execute_good(self):
        s = VariableDefinition("set here=<there>", "here=<there>")
        variables = {}
        s.execute(variables)
        self.assertEquals(variables['here'].value, '<there>')

    def test_execute_bad(self):
        s = VariableDefinition(
            "set here={{{<not_there>}}}",
            "here={{{<not_there>}}}")

        self.assertRaises(
            ErrorCollection,
            s.execute,
                {})

    def test_execute_ok_loop(self):
        steps = [
            ParseStep(s) for s in 
                ["set x = 0" ,"set x= <x> + 1", "set x= <x> + 2"]]
        
        variables = {}
        for s in steps:
            s.execute(variables)
        
        self.assertEquals(
            ReplaceVariableReferences("<x>", variables),
            "0 + 1 + 2")

    def test_execute_bad_loop(self):
        steps = [
            ParseStep(s) for s in 
                ["set x = 0" ,"set y= <x>", "set x= <y> + 2"]]
        
        variables = {}
        for s in steps:
            s.execute(variables)
        
        self.assertRaises(
            ErrorCollection,
            ReplaceVariableReferences,
                "<x>", variables)
       

    def test_basic_step_repr(self):
        s = VariableDefinition("blah blah", "_yikes_=_close_")
        self.assertEquals(s.__repr__(), '"_close_"')


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
        e = ExecutionEndStep("", " 123 ,hi ")
        self.assertEquals(e.ret, 123)
        self.assertEquals(e.message, "hi")

    def test_construct_no_message(self):
        """"""
        e = ExecutionEndStep("", " 123 , ")
        self.assertEquals(e.ret, 123)
        self.assertEquals(e.message, "")

        e = ExecutionEndStep("", " 123 ")
        self.assertEquals(e.ret, 123)
        self.assertEquals(e.message, "")


    def test_construct_bad_return_code(self):
        """"""
        self.assertRaises(
            RuntimeError,
            ExecutionEndStep,
                "", "123d, hi")

    def test_replace_vars_update_false(self):
        """"""
        variables = {'hi': DummyVar("there")}
        e = ExecutionEndStep("", " 123 , <hi>")
        
        e.replace_vars(variables)
        self.assertEquals(e.message, "<hi>")

    def test_replace_vars_update_true(self):
        """"""
        variables = {'hi': DummyVar("there")}
        e = ExecutionEndStep("", "123, <hi>")
        
        e.replace_vars(variables, True)
        self.assertEquals(e.message, "there")

    def test_replace_vars_update_false(self):
        """"""
        e = ExecutionEndStep("", "123, hi")
        
        self.assertRaises(
            EndExecution,
            e.execute,
                {})

                


def DebugAction(to_exec, dummy = None):
    exec to_exec
    return 0, "no message"
built_in_commands.NAME_ACTION_MAPPING['debug'] = DebugAction


class CommandStepTests(unittest.TestCase):
    ""
    def test_command_as_string_for_log_list(self):
        """"""
        c = CommandStep("")
        self.assertEquals(
            c.command_as_string_for_log('', ['1', '2', '3']),
            "'' -> '1 2 3'")

    def test_command_as_string_for_log_long_string_diff(self):
        """"""
        c = CommandStep("")
        self.assertEquals(
            c.command_as_string_for_log('', "s" * 300),
            "'' -> '%s'"% ("s"*300))

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

        CommandStep('debug raise KeyboardInterrupt()').execute({})
        sys.stdin.close()
        sys.stdin = old_stdin

    def test_Step_interupted_stop(self):
        """"""
        old_stdin = sys.stdin
        sys.stdin = open(os.path.join(TEST_FILES_PATH, "yes.txt"), "r")
        s = CommandStep('debug raise KeyboardInterrupt')

        self.assertRaises(RuntimeError, s.execute, {})

        sys.stdin.close()
        sys.stdin = old_stdin

    def test_Step_no_output(self):
        """"""

        s = CommandStep('cd \\')

        s.execute({})
        self.assertEquals(s.output, "")

    def test_Step_no_error_and_output(self):
        """"""

        s = CommandStep('dir')

        s.execute({})
        self.assertEquals(s.ret, 0)


class IfStepTests(unittest.TestCase):

    def test_working_do(self):
        for filename in glob.glob(os.path.join(TEST_FILES_PATH, "if_else_*")):

            # skip tests which are meant to fail
            if 'if_else_broken' in filename:
                continue

            script_filepath = os.path.join(TEST_FILES_PATH, filename)
            vars = PopulateVariables(script_filepath, {})

            steps = LoadScriptFile(script_filepath)
            steps = FinalizeSteps(steps, vars)

            try:
                ExecuteSteps(steps, vars)

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
            steps = FinalizeSteps(steps, vars)

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
        steps = FinalizeSteps(steps, vars)
        
        ExecuteSteps(steps, vars)

    def test_broken_else_name(self):
        script_filepath = os.path.join(TEST_FILES_PATH, "if_else_broken_else_name.yaml")

        self.assertRaises(
            RuntimeError,
            LoadScriptFile,
                script_filepath)

    def test_minimal_if(self):
        pass



if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("test_parsescript")
    # needs to be called before importing the modules
    import coverage
    cov = coverage.coverage(branch = True)
    cov.start()
    unittest.TextTestRunner(verbosity=1).run(suite)
    cov.stop()
    print cov.report([parsescript])
