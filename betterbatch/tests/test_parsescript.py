import unittest
import os
import logging

import sys
# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(package_root)

#import betterbatch
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
            "set Hello=World",
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

    def test_escaped_var_ref(self):
        self.assertEquals(
            FindVariableReferences("cd <<dir>>"),
            {})


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
            betterbatch.ErrorCollection,
            ReplaceVariableReferences,
                "<not_here>", {'here': DummyVar('there')})

    def test_recursive_var_err(self):
        """"""
        self.assertRaises(
            betterbatch.ErrorCollection,
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
            betterbatch.ErrorCollection,
            ReplaceVariableReferences,
                "<here>", {
                    'here': DummyVar('<not_there>'),
                    'there': DummyVar('<here>')})



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
        self.assertEquals(statement, "set")
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
        self.assertRaises(
            OSError,
            SetupLogFile,
                path)
        #os.close(file)
        #os.unlink(file)

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

    def test_simple_exe(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(" -  {{{echo This value}}}  - ", {}),
            " -  This value  - ")

    def test_simple_wiht_var(self):
        """"""
        self.assertEquals(
            ReplaceExecutableSections(
                "here {{{echo This <value>}}} <value>",
                {'value': DummyVar('car')}),
            "here This car <value>")

    def test_not_a_command(self):
        """"""
        text = "{{{not_a_command}}} echo This <var>}}}"
        variables = {'var': DummyVar('car')}
        self.assertRaises(
            RuntimeError,
            ReplaceExecutableSections,
                text, variables, execute=True)



class ParseStepTests(unittest.TestCase):
    ""

    # dict
    # non dict

    # in handlers
    # not in handlers


    def test_dict_step(self):
        """"""
        step = ParseStep({r"if exists c:\temp": None, 'else': None})
        self.assertEquals(step.condition.raw_step,  "exists c:\\temp")

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
        self.assertEquals(step.condition.raw_step,  "exists c:\\temp")
        self.assertEquals(step.if_steps[0].raw_step, 'cd 1')
        self.assertEquals(step.else_steps[0].raw_step, 'cd 2')

    def test_broken_if_step_wrong_key(self):
        """"""
        step = {r"if exists c:\temp": ["cd 1"], 'there': ["cd 2"]}
        self.assertRaises(
            RuntimeError,
            ParseComplexStep,
                step)

    def test_if_step_none_value(self):
        """"""
        step = {r"if 1": None,}
        step = ParseComplexStep(step)
        self.assertEquals(step.condition.raw_step,  "1")
        self.assertEquals(step.if_steps, [])
        self.assertEquals(step.else_steps, [])

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


class StepTests(unittest.TestCase):
    ""

    def test_basic_step(self):
        """"""
        s = Step("here")
        self.assertEquals(s.raw_step, "here")

    def test_basic_step_str_(self):
        s = Step("here")
        self.assertEquals(s.__str__(), "here")


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
            betterbatch.ErrorCollection,
            s.execute,
                {})

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("test_parsescript")
    # needs to be called before importing the modules
    import coverage
    cov = coverage.coverage(branch = True)
    cov.start()
    unittest.TextTestRunner(verbosity=1).run(suite)
    cov.stop()
    print cov.report([parsescript])
