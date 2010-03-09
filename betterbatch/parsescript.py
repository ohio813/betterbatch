"""Parse a script and return the list of steps ready to executed"""
import re
import os
import logging
import shlex
import sys
import ConfigParser
import copy
import threading
import time

import yaml

import built_in_commands
import cmd_line

PARAM_FILE = os.path.join(os.path.dirname(__file__), "param_counts.ini")


def ConfigLogging():
    "Create and set up the logger - returns the new logger"
    # allow the handler to output everything - we will set the actual level
    # through the logger

    logger = logging.getLogger("betterbatch")
    logger.setLevel(logging.DEBUG)

    # make the output format very simple
    basic_formatter = logging.Formatter("%(message)s")

    if not logger.handlers:
        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(logging.INFO)

        logger.addHandler(stdout_handler)

    for handler in logger.handlers:
        handler.setFormatter(basic_formatter)

ConfigLogging()
LOG = logging.getLogger('betterbatch')


class UndefinedVariableError(RuntimeError):
    "Error raised when a variable is used that has not been defined"

    def __init__(self, variable, string):
        RuntimeError.__init__(
            self, "Undefined Variable '%s' '%s'"% (variable, string))

        self.variable = variable
        self.string = string


class ErrorCollection(RuntimeError):
    "Class used to track many errors "

    def __init__(self, errors):
        RuntimeError.__init__(self, "%d errors"% len(errors))
        self.errors = errors

    def LogErrors(self):
        "Log all the errors in a user friendly format"

        # collect any Undefined Variables so we can log those better
        undef_var_errs = {}
        other_errs = []
        for e in self.errors:
            if isinstance(e, UndefinedVariableError):
                var = e.variable.lower()
                strings = undef_var_errs.setdefault(var, [])
                if e.string not in strings:
                    strings.append(e.string)
            elif str(e) not in other_errs:
                other_errs.append(e)

        for e in other_errs:
            LOG.fatal(e)

        if undef_var_errs:
            LOG.fatal("======== UNDEFINED VARIABLES ========")
            LOG.info(
                '(Check scripts or pass value on '
                'command line e.g. "var=value")')
        for var, strings in sorted(undef_var_errs.items()):
            LOG.fatal("'%s'"% var)

            for string in strings:
                LOG.debug("    %s"% string)

    def __repr__(self):
        return "<ERRCOL %s>"% self.errors

    __str__ = __repr__


class EndExecution(Exception):
    "Raised when an End statement called"

    def __init__(self, ret, msg):
        self.msg = msg
        self.ret = ret


def ParseYAMLFile(yaml_file):
    """Parse a single YAML file

    Most of the work of this function is to convert various different errors
    into RuntimeErrors
    """
    try:
        # read the YAML contents
        f = open(yaml_file, "rb")
        yaml_data = f.read()
        f.close()

        # replace tabs with spaces
        # and log a warning if we changed the file
        if "\t" in yaml_data:
            yaml_data = yaml_data.replace("\t", "  ")
            LOG.warning(
                "WARNING: Script contained one or more tab (\\t) "
                    "characters.\n"
                "         They have been replaced by spaces for "
                    "processing")

        # only allow mapping at the end of a string
        re_non_end_colon = re.compile(r":( *)(?!\s*$)", re.MULTILINE)
        yaml_data = re_non_end_colon.sub(r"+++++colon+++++\1", yaml_data)

        # avoid the 'double quote parsing of YAML'
        yaml_data = yaml_data.replace('"', '+++++dblquote+++++')

        # Parse the yaml data
        script_data = yaml.load(yaml_data)

        # Now that we have parsed the file and everything has been treated as
        # a string we need to remove that text we added
        def strip_string_forcers(item):
            "Replace any string forcers we added previously"
            if isinstance(item, basestring):
                item = item.replace("+++++colon+++++", ":")
                item = item.replace("+++++dblquote+++++", '"')
                return item
            elif isinstance(item, list):
                for i, elem in enumerate(item):
                    item[i] = strip_string_forcers(elem)
                return item
            elif isinstance(item, dict):
                new_dict = {}
                for key, value in item.items():
                    new_key = strip_string_forcers(key)
                    new_val = strip_string_forcers(value)
                    new_dict[new_key] = new_val
                return new_dict
            elif item is None:
                return None
            else:
                raise RuntimeError("Unknown structure type!")

        script_data = strip_string_forcers(script_data)

        return script_data

    except IOError, e:
        raise RuntimeError(e)

    except yaml.parser.ScannerError, e:
        raise RuntimeError("%s - %s"% (yaml_file, e))

    except yaml.parser.ParserError, e:
        raise RuntimeError("%s - %s"% (yaml_file, e))


def ParseVariableDefinition(var_def, allow_no_value = False):
    """Return the variable name and variable value of a variable definition"""

    # NOTE: do not add %var_def after the errors - this will be added by the
    # the code that calls this method!!

    if allow_no_value:
        if '=' not in var_def:
            return var_def.strip(), None

    try:
        name, value = [p.strip() for p in var_def.split("=", 1)]
    except ValueError, e:
        raise RuntimeError("Variable not defined correctly: '%s'")

    if len(name.split()) > 1:
        raise RuntimeError(
            "Variable names cannot have spaces: '%s'")

    if not name:
        raise RuntimeError(
            "Variable name missing in variable definition: '%s'")

    return name.lower(), value


def SplitStatementAndData(step):
    """Return the step split after the first 'word'

    This only cares for simple statements e.g. cd, if, echo, set
    and not actual commands c:\tools\robocopy.exe etc
    """
    parts = step.split(None, 1)
    for i, p in enumerate(parts):
        parts[i] = p.strip()

    # ensure that there is always a 2nd part
    if len(parts) == 1:
        parts.append('')

    return parts


def FindVariableReferences(text):
    """Find the variable references in the string

    Returns a dictionary of variable name -> texts to replace
    e.g.
    >>> FindVariableReferences("<var1> < var1> <  var2 >")
    >>> {'var1': ['<var1>', < var1>], 'var2': ['<  var2 >']}
    """

    variable_reference_re = re.compile("\<([^\>\<]+)\>")

    # find all the variable references
    found = variable_reference_re.findall(text)

    variables_referenced = {}

    # for each of the refernece variables in this variable
    for var in found:
        # clean the variable name
        var_name = var.strip().lower()

        # add it and the text that needs to be replaced to the dictionary
        variables_referenced.setdefault(var_name, []).append("<%s>"% var)

    return variables_referenced


def ReplaceVariableReferences(text, variables, loop = None):
    """Replace all variable references in the string

    If there are any variables references in a replaced variable those will
    also be replaced"""

    if loop is None:
        loop = []

    errors = []
    original_text = text

    # We need some way to allow > and < so the user doubles them when
    # they are not supposed to be around a variable reference.
    # Replacing them like this - makes finding the acutal variable
    # references much easier
    text = text.replace("<<", "{{_LT_}}")

    # We replace greater than >> a bit differently - because if there are
    # an odd number of greater than signs in a row we want to split from
    # the end not from the start
    text = "{{_GT_}}".join(text.rsplit(">>"))

    var_refs = FindVariableReferences(text)
    for variable, refs_to_replace in var_refs.items():

        # the variable referenced is not defined
        if variable not in variables:
            errors.append(UndefinedVariableError(variable, text))
            continue

        # ensure that we are not in a variable loop e.g x -> y -> x
        # a loop of 1 is OK e.g. x = <x>_ + 1
        if len(loop) > 100:
            errors.append("Loop found in variable definition "
                "'%s', variable %s"% (original_text, repr(loop)))
            continue

        loop.append(variable)

        try:
            # ensure that any variables in the variable value are also
            # replaced
            var_value = ReplaceVariableReferences(
                variables[variable], variables, loop)

            for ref_to_replace in refs_to_replace:
                text = text.replace(ref_to_replace, var_value)

        except ErrorCollection, e:
            for err in e.errors:
                if isinstance(err, UndefinedVariableError):
                    new_string = "%s -> %s"% (original_text, err.string)

                    errors.append(
                        UndefinedVariableError(err.variable, new_string))
                else:
                    errors.append(err)

        loop.pop()

    if errors:
        raise ErrorCollection(errors)

    text = text.replace("{{_LT_}}", "<")
    text = text.replace("{{_GT_}}", ">")

    return text


def ReplaceExecutableSections(text, variables, phase = "run"):
    """If variable has {{{cmd}}} - execute 'cmd' and update value with output
    """

    # replace qualifiers before finding sections
    text = re.sub(r"\{\*(.+?)\*\}", r"--#QUAL_#--\1--#_QUAL#--", text)

    EXECUTABLE_SECTION = re.compile(
        r"""
            \{\{\{
                \s*
                (?P<command_line>.+?)
                \s*
            \}\}\}""", re.VERBOSE)

    # See if it matches the executable section pattern
    sections = EXECUTABLE_SECTION.finditer(text)

    replaced = []
    # was going reversed so that it would be easier to replace the text
    # but that meant the commands were executed backwards when there was more
    # than one on a line (maybe not a big issue but a little confusing)
    last_section_end = 0
    for section in sections:
        if "{{{" in section.group('command_line'):
            raise RuntimeError(
                "Do not embed executable section {{{...}}} in another "
                "executable section: '%s'"% text)

        command = section.group('command_line').replace("--#QUAL_#--", "{*")
        command = command.replace("--#_QUAL#--", "*}")

        step = ParseStep(command)

        # text before the section
        replaced.append(text[last_section_end:section.start()])

        step.execute(variables, phase)

        # Escape any greater/less than characters in the output of the
        # command
        output = step.output.strip()
        output = output.replace("<", "<<")
        output = output.replace(">", ">>")

        replaced.append(output)

        last_section_end = section.end()

    # if we were not exectuing - then replaced will still contain the
    # original string
    replaced.append(text[last_section_end:])

    text = "".join(replaced)
    text = text.replace("--#QUAL_#--", "{*")
    text = text.replace("--#_QUAL#--", "*}")
    return text


def SetupLogFile(log_filename):
    "Create the log file if it has been requested"

    # try to find if the log file is already open
    # if it is - then just flush and return (without changing the logfilename)
    for h in LOG.handlers:
        if not isinstance(h, logging.FileHandler):
            continue

        # don't change anything if the current and old log file names are
        # the same
        if (os.path.abspath(h.baseFilename).lower() ==
            os.path.abspath(log_filename).lower()):
            return

        else:
            LOG.debug("Changing log file to: '%s'"% log_filename)
            h.flush()
            h.close()
            LOG.removeHandler(h)

    # if that logfile already exists - then try and delete it
    if os.path.exists(log_filename):
        try:
            os.unlink(log_filename)
        except OSError:
            LOG.warning("WARNING: Could not remove previous log file")

    h = logging.FileHandler(log_filename)

    # make the output format very simple, and remove the date
    basic_formatter = logging.Formatter(
        "%(asctime)s\t%(levelname)s\t%(message)s",
        "%H:%M:%S")
    h.setFormatter(basic_formatter)

    LOG.addHandler(h)


def ParseSteps(steps):
    "Parse a collection of steps"
    if steps is None:
        return []

    if isinstance(steps, basestring):
        steps = [steps]

    parsed_steps = []
    errors = []
    for step in steps:
        if step is None:
            continue

        try:
            parsed_steps.append(ParseStep(step))
        except ErrorCollection, e:
            errors.extend(e.errors)

    if errors:
        raise ErrorCollection(errors)

    return parsed_steps


def ParseStep(step):
    """Return the parsed step ready to check and execute"""
    # parse the if/for etc block
    if isinstance(step, dict):
        return ParseComplexStep(step)

    if step is None:
        return None

    # get the statement type
    statement_type, step_data = SplitStatementAndData(step)
    statement_type = statement_type.lower()

    # if it is a known statement type then use that - use 'CommandStep'
    # for all others
    handler = STATEMENT_HANDLERS.get(statement_type, CommandStep)
    parsed_step = handler(step)

    return parsed_step


def ParseIfStep(step, statements, clean_keys):
    "Parse an if complex step"

    if 'and' in clean_keys and 'or' in clean_keys:
        raise RuntimeError(
            "You cannot mix AND and OR statements in a single IF '%s'"%
                step)

    conditions = []
    if_steps = []
    else_steps = []
    # check that there are no invalid blocks
    for key, condition, steps in statements:

        if key in ("if", 'and', 'or'):

            # if there are steps they must be the 'if' steps
            if steps:
                # if there are already steps for the 'if' block
                if if_steps:
                    raise RuntimeError(
                        "Only one of the if/and/or "
                        "statements can have steps: %s"% step)
                if_steps = ParseSteps(steps)

            # check if NOT is applied to the condition
            negative_condition = False
            if condition.lower().startswith("not "):
                condition = condition[4:].strip()
                negative_condition = True
            conditions.append((key, ParseStep(condition)))
            conditions[-1][1].negative_condition = negative_condition

        elif key == 'else':
            else_steps = ParseSteps(steps)

        else:
            raise RuntimeError(
                "If is not correctly defined expected \n"
                "- if COND:\n"
                " [and/or COND:]\n"
                "    - DO_STEPS\n"
                "  else:\n"
                "    - ELSE_STEPS")

    if not if_steps + else_steps:
        raise RuntimeError(
            "IF statement has no 'if_true' or 'else' statements '%s'"%
                conditions)

    return IfStep(step, conditions, if_steps, else_steps)

def ParseForStep(step, statements):
    "Parse an for complex step"
    if len(statements) > 1:
        raise RuntimeError(
            "For statements should not have more than one 'key': %s"%
                statements)
    loop_info, steps = statements[0][1:]
    steps = ParseSteps(steps)

    if not steps:
        return None

    return ForStep(step, loop_info, steps)

def ParseParallelStep(step, statements):
    "Parse a parallel complex step"
    if len(statements) > 1:
        raise RuntimeError(
            "Parallel blocks can have more only one parent: %s"%
                statements)
    # just get the steps
    steps = statements[0][-1]
    steps = ParseSteps(steps)

    for loop_step in steps:
        if not isinstance(loop_step, (CommandStep, FunctionCall)):
            raise RuntimeError(
                "You can only have commands (no variable definitions, "
                "includes, logfile, etc. in Parallel blocks: %s"%
                    statements)

    return ParallelSteps(step, steps)

def ParseFunctionNameAndArgs(name_args):

    # we need to parse out the name_args which should be something like:
    # function_name (arg, arg = default, arg = default)
    found = re.search("(.+)\((.*)\)(.*)", name_args)

    if not found:
        raise RuntimeError ("Function defintion seems to be incorrect: '%s'"%
            name_args)

    name = found.group(1).strip()
    args = found.group(2).split(",")

    parsed_args = []
    for arg in args:
        parsed_args.append(ParseVariableDefinition(arg, allow_no_value = True))

    # check that no item defined with a default is defined before an
    # item without a default e.g. just like python :)
    default_found = False
    for arg_name, arg_value in parsed_args:
        # None when no default (check arg_name too as it will be
        # empty if there is a trailing comma)
        if arg_value is None and arg_name:
            # and we have already passed one with a default
            if default_found:
                raise RuntimeError(
                    "In a function defintion or function call you cannot "
                    "define an argument without a default after an argument "
                    "that has a default. '%s'"% arg_name)
        else:
            default_found = True

    return name, parsed_args


def ParseFunctionDefinition(step, statements):
    "Parse a function definition complex step"
    if len(statements) > 1:
        raise RuntimeError(
            "Function blocks can have more only one header: %s"%
                statements)

    # Extract out the various bits of the function header
    dummy, name_args, steps = statements[0]
    name, args = ParseFunctionNameAndArgs(name_args)

    steps = ParseSteps(steps)

    return FunctionDefinition(step, name, args, steps)


def ParseComplexStep(step):
    "The step is not a string - so parse what kind of step it is"
    statements = []
    clean_keys = []
    for key in step.keys():
        clean_key, key_data = SplitStatementAndData(key)
        clean_key = clean_key.strip().lower()
        clean_keys.append(clean_key)
        statements.append((clean_key, key_data, step[key]))

    # if it iss an IF statement
    if 'if' in clean_keys:
        return ParseIfStep(step, statements, clean_keys)

    elif 'for' in clean_keys:
        return ParseForStep(step, statements)

    elif 'parallel' in clean_keys:
        return ParseParallelStep(step, statements)

    elif 'function' in clean_keys:
        return ParseFunctionDefinition(step, statements)
    else:
        raise RuntimeError("Unknown Complex step type: '%s'"%
            clean_keys)


class Step(object):
    "Represent a generic step - should never actually be instantiated"

    def __init__(self, raw_step):
        self.raw_step = raw_step
        #self.referenced_variables = FindVariableReferences(raw_step)
        self.step_type, self.step_data = SplitStatementAndData(raw_step)

    def __str__(self):
        return unicode(self.raw_step).encode('mbcs')

    def __repr__(self):
        return "<%s %s>"% (self.__class__.__name__, self.raw_step)


class VariableDefinition(Step):
    "A step in the form set varname = var value"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)

        # check if there are any qualifiers
        self.step_data, self.qualifiers = ParseQualifiers(self.step_data)

        try:
            self.name, self.value = ParseVariableDefinition(self.step_data)
        except RuntimeError, e:
            raise RuntimeError(str(e)% self.raw_step)

    def execute(self, variables, phase):
        """Set the variable

        Note - we don't replace all sub variables at this point."""
        new_val = self.value
        if 'delayed' not in self.qualifiers:
            new_val = ReplaceExecutableSections(new_val, variables, phase)

            new_val = ReplaceVariableReferences(new_val, variables)

            if self.value != new_val and phase != "test":
                LOG.debug("Set variable '%s' to value '%s'"% (
                    self.name, new_val))

        variables[self.name] = new_val

    def __repr__(self):
        return '"%s"'% self.value


def ParseQualifiers(text):
    "Find the qualifiers and replace them"

    # remove the executable sections first becuase we don't
    # need or want to parse the qualifiers in these sections yet

    exe_sections = []
    for i, exe_section in enumerate(
            re.findall(r"\{\{\{.+?\}\}\}", text)):
        text = text.replace(exe_section, "{{{%d}}}"% i)
        exe_sections.append(exe_section)

    qualifier_re = re.compile("""
        \{\*
        (?P<qualifier>.+?)
        \*\}""", re.VERBOSE)

    qualifiers = qualifier_re.findall(text)
    text = qualifier_re.sub("", text)

    # replace the executable sections
    for i, section in enumerate(exe_sections):
        text = text.replace("{{{%d}}}"%i, section)

    # ensure that the qualifiers are lower case and no extra spaces
    qualifiers = [q.lower().strip() for q in qualifiers]

    return text, qualifiers


class CommandStep(Step):
    "Any general command"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        self.output = ""
        self.ret = 0
        self.step_type = "command"
        self.step_data = self.raw_step

        self.step_data, self.qualifiers = ParseQualifiers(self.step_data)

    def command_as_string_for_log(self, cmd, params):
        "return the command as a string for logging"
        if isinstance(params, list):
            params = " ".join(params)

        command_message = params
        if cmd:
            command_message = " ".join((cmd, command_message))

        if command_message.split() != self.raw_step.split():
            command_message = "'%s' -> '%s'"% (
                self.raw_step, command_message)
        else:
            command_message = "'%s'"% command_message

        #command_message = command_message.replace('\\', '\\\\')
        command_message = command_message.replace('\r\n', '\\r\\n')

        return command_message

    def execute(self, variables, phase):
        "Run this step"

        command_text = ReplaceExecutableSections(
            self.step_data, variables, phase)
        command_text = ReplaceVariableReferences(command_text, variables)

        if phase == "test":
            return

        # Check if the command is a known command
        parts = SplitStatementAndData(command_text)

        cmd = parts[0].strip().lower()
        if cmd in built_in_commands.NAME_ACTION_MAPPING:
            func = built_in_commands.NAME_ACTION_MAPPING[cmd]
            params = parts[1]
            cmd_log_string = self.command_as_string_for_log(cmd, params)
        else:
            func = built_in_commands.SystemCommand
            params = command_text
            cmd_log_string = self.command_as_string_for_log("", params)

        if cmd == "echo":
            self.qualifiers.append('echo')

        #cmd_log_string = self.command_as_string_for_log(cmd, params)
        try:
            LOG.debug("Executing command %s"% cmd_log_string)
            # call the function and get the output and the return value
            self.ret, self.output = func(params, self.qualifiers)
        except KeyboardInterrupt:
            while 1:
                LOG.error(
                    "Step cancelled - Terminate script execution? [Y/n]")
                ans = raw_input()
                if ans.lower().startswith("y"):
                    raise RuntimeError("Script Cancelled")
                elif ans.lower().startswith("n"):
                    return

        if self.output:
            indented_output = "\n".join(
                ["   " + line for line in
                    self.output.strip().split("\r\n")])
        else:
            indented_output = '\n'

        if self.ret and not 'nocheck' in self.qualifiers:
            raise RuntimeError(
                'Non zero return (%d) CMD: %s \n %s'%
                    (self.ret, cmd_log_string, indented_output))

        if 'echo' in self.qualifiers and self.output.strip():
            LOG.info(self.output.strip())

        elif indented_output != "\n":
            LOG.debug("Output from command:\n%s"% indented_output)


class FunctionDefinition(Step):
    "An set of command steps to be executed in parallel"

    all_functions = {}

    def __init__(self, raw_step, name, args, steps):

        self.raw_step = raw_step

        self.name = name
        self.args = args
        self.steps = steps

        # arg has a default if the arg value is not None
        self.non_default_args = [
            arg[0] for arg in self.args if arg[1] == None]

        # keep a record of the function so that we can reference it
        FunctionDefinition.all_functions[name.lower()] = self

    def execute(self, variables, phase):
        """Only run the steps in test mode - they are not
        executed in run mode - because they should only run when called"""
        if phase == "test":
            vars_copy = copy.deepcopy(variables)
            for arg_name, arg_val in self.args:
                vars_copy[arg_name] = arg_val or 'dummy val'

            ExecuteSteps(self.steps, vars_copy, phase)

    def call_function(self, arg_values, variables, phase):

        if phase != "test":
            LOG.debug(
                "Function call: '%s' with args %s"% (self.name, arg_values))

        # make a copy of the variables
        vars_copy = copy.deepcopy(variables)
        vars_copy.update(arg_values)

        ExecuteSteps(self.steps, vars_copy, phase)


class ParallelSteps(Step):
    "An set of command steps to be executed in parallel"

    def __init__(self, raw_step, steps):

        self.raw_step = raw_step

        self.steps = steps

    def execute(self, variables, phase):
        "Run this step"

        # replace variables in the steps to be executed
        ExecuteSteps(self.steps, variables, "test")

        threads = []

        class ThreadStepRunner(threading.Thread):
            "Run a step in a separate thread"
            def __init__(self, step, variables):
                threading.Thread.__init__(self)
                self.step = step
                self.variables = variables
                self.exception = None
            def run(self):
                "Run the thread and store any exceptions for later retrieval"
                try:
                    self.step.execute(self.variables, phase)
                except Exception, e:
                    self.exception = e

        # start all the threads
        for step in self.steps:
            if phase != "test":
                LOG.debug("starting step in new thread: '%s'"% step)
            t = ThreadStepRunner(step, variables)
            t.start()
            threads.append(t)

        # wait for them to finish
        errs = []
        while threads:
            for t in threads:
                # Try to joiin the thread, but timeout very quickly
                t.join(.01)

                # if the thread has finished, print a message and
                # remove it
                if not t.isAlive():
                    if phase != "test":
                        LOG.debug("Thread finished: '%s'"% t.step)
                    threads.remove(t)
                    if t.exception:
                        errs.append(t.exception)

        # check if any threads
        if errs:
            raise ErrorCollection(errs)


class ForStep(Step):
    "One or more steps repeated"

    def __init__(self, raw_step, loop_condition, steps):

        self.steps = steps
        self.raw_step = raw_step

        #split on ' in '
        self.variable, self.command = [
            part.strip() for part in loop_condition.split(' in ', 1)]
        self.variable = self.variable.lower()

    def execute(self, variables, phase):
        "Run this step"

        cmd_output = ReplaceExecutableSections(
            self.command, variables, phase)

        # split the variables
        values = cmd_output.split("\n")

        for val in values:

            # add or update the loop variable in the variables
            #var = VariableDefinition('set %s = %s'% (self.variable, val))
            variables[self.variable] = val

            # loop over the steps
            loop_steps = copy.deepcopy(self.steps)

            ExecuteSteps(loop_steps, variables, phase)

class IfStep(Step):
    "An IF block"

    def __init__(self, raw_step, conditions, if_steps, else_steps):

        self.raw_step = raw_step

        self.conditions = conditions
        self.if_steps = if_steps
        self.else_steps = else_steps

    def __test_step(self, variables):
        """Test that there are no problems with the step

        As the If step has more complex checking it has been broken out to a
        separate method"""

        if_defined_vars = []
        else_defined_vars = []
        for cond_type, condition in self.conditions:
            condition.execute(variables, 'test')

            if isinstance(condition, VariableDefinedCheck):
                if condition.variable not in variables:
                    # so it's not defined - we will need to add it for
                    # complete checking. If it is a negative condtions
                    # e.g. if not defined test: then we will need to add it
                    # to for the else steps, otherwise we will need to add it
                    # for the if steps
                    if condition.negative_condition:
                        else_defined_vars.append(condition.variable)
                    else:
                        if_defined_vars.append(condition.variable)

        def CheckStepsWithExtraVars(steps, variables, extra_vars):
            "Check the steps with the extra vars defined"
            # add a dummy value so that IF Block checking works correctly
            for var in extra_vars:
                variables[var] = ''

            # now that we have temporarily defined any definitions
            # needed - check the 'if' steps
            ExecuteSteps(steps, variables, 'test')

            for var in extra_vars:
                del variables[var]

        CheckStepsWithExtraVars(self.if_steps, variables, if_defined_vars)
        CheckStepsWithExtraVars(self.else_steps, variables, else_defined_vars)

    def execute(self, variables, phase):
        "Run this step"

        # check if the condition is true
        #try:
        conditions_type = 'and'
        condition_values = []

        # Check the 'else' steps now. We may temporarily define variable
        # due to a 'defined' check which would upset the 'else' checks
        if phase == 'test':
            self.__test_step(variables)
            return

        for cond_type, condition in self.conditions:
            LOG.debug("Testing Condition: '%s'"% condition)
            try:
                condition.execute(variables, phase)
            except Exception, e:
                # swallow exceptions - it just means that the check failed
                pass

            ret = condition.ret
            if condition.negative_condition:
                ret = not ret

            condition_values.append(ret)

            if cond_type == "or":
                conditions_type = "or"

        # either AND and All should have passed (not any failed)
        # or OR and at least one pass
        if ((conditions_type == "and" and not any(condition_values)) or
            (conditions_type == "or" and 0 in condition_values)):
            LOG.debug("Condition evaluated to true: %s"% condition.output)
            self.steps_to_exec = self.if_steps

        else:
            LOG.debug(
                "Condition evaluated to false: %s"% condition.output)
            self.steps_to_exec = self.else_steps

        # Execute the steps
        ExecuteSteps(self.steps_to_exec, variables, phase)

    def __repr__(self):
        return "<IF %s...>"% self.conditions


class FunctionCall(Step):
    "A request to call a function"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)

        name_argvals = SplitStatementAndData(raw_step)[1]

        self.name, self.arg_vals = ParseFunctionNameAndArgs(name_argvals)
        
        # a positional arg is any that has a None value and the
        # arg name (which is actually the value) is not empty
        self.positional_args = [
            arg for (arg, val) in self.arg_vals 
                if (val == None and arg)]

        self.keyword_args = dict([
            (arg.lower(), val) for (arg, val) in self.arg_vals
                if val != None])

    def execute(self, variables, phase):
        # ensure that the function name exists
        if not self.name.lower() in FunctionDefinition.all_functions:
            raise RuntimeError(
                "Attempt to call an unknown function '%s' in call '%s'"%
                    (self.name, self.raw_step))

        function = FunctionDefinition.all_functions[self.name.lower()]

        if len(self.arg_vals) > len(function.args):
            raise RuntimeError("Too many arguments passed in function "%
                self.raw_step)

        # if the arg is a simple value (i.e. not arg = val) then it will
        # be simply passed in the order in the call
        args_to_pass = {}

        # for each of the remaining function definition arguments
        # match passed arguments against function arguments
        for i, (arg_name, arg_value) in enumerate(function.args):
            arg_name = arg_name.lower()

            # this will populate arguments from the positional args in the
            # function call
            if len(self.positional_args) > i:
                args_to_pass[arg_name] = self.positional_args[i]
                continue

            # If it is one of the passed our keyword arguments
            if arg_name.lower() in self.keyword_args:
                if arg_name in args_to_pass:
                    raise RuntimeError(
                        "Value for parameter '%s' already supplied"% arg_name)

                args_to_pass[arg_name] = self.keyword_args[arg_name]

            # otherwise just use the default value
            else:
                args_to_pass[arg_name] = arg_value
            #elif arg_value is None:
            #    raise RuntimeError((
            #        "No Value passed for function parameter %d '%s' in "
            #        "function call:\n\t%s")%
            #            (i + len(arg_values_to_pass), arg_name, self.raw_step))

        function.call_function(args_to_pass, variables, phase)


class ExecutionEndStep(Step):
    "Request end execution of the script"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        self.ret = 0
        self.message = ''

        ret_message = SplitStatementAndData(raw_step)[1]
        parts = ret_message.split(',', 1)
        try:
            self.ret = int(parts[0])
        except ValueError:
            raise RuntimeError(
                "First item of END should be the error return (number), "
                "0 for success: '%s'"% raw_step)

        if len(parts) == 2:
            self.message = parts[1].strip()

    def execute(self, variables, phase):
        "Run this step"
        message = ReplaceVariableReferences(self.message, variables)
        if phase != "test":
            raise EndExecution(self.ret, message)


class IncludeStep(Step):
    "Include steps from elsewhere"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        dummy, self.filename = SplitStatementAndData(raw_step)
        if not self.filename:
            raise RuntimeError("Include with no filename.")
        self.steps = []

    def execute(self, variables, phase):
        "Run this step"
        # todo: should the __script_dir__ be updated to the include
        # directory? if yes- then don't forget to set it back afterwards
        # in a safe try finally!

        filename = ReplaceVariableReferences(self.filename, variables)

        self.filename = os.path.join(
            variables['__script_dir__'], filename)

        # load the steps no matter
        try:
            self.steps = LoadScriptFile(self.filename)
        except Exception, e:
            if phase == "test":
                LOG.debug(
                    "Could not open include file during testing: %s"%
                        self.filename)
            else:
                raise
        try:
            if phase != "test":
                LOG.debug(
                    "Included steps from: %s"% self.filename)
            self.steps = ExecuteSteps(self.steps, variables, phase)
        except Exception, e:
            if phase != "test":
                raise

        # we may not be abel to do this at this stage
        # as execute for includes will be done before the variables are
        # added!, so steps inside the includes will not have the all
        # the variables available
        #self.steps = FinalizeSteps(self.steps, variables)


class LogFileStep(Step):
    "Specify the log file"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        dummy, self.filename = SplitStatementAndData(raw_step)
        if not self.filename:
            raise RuntimeError("logfile with no filename.")

    def execute(self, variables, phase):
        "Run this step"
        filename = ReplaceVariableReferences(self.filename, variables)

        if phase != "test":
            SetupLogFile(filename)
            LOG.debug('Variables at logfile creation: %s'% variables)


class VariableDefinedCheck(Step):
    "Check if a variable is defined"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        dummy, self.variable = SplitStatementAndData(raw_step)
        if not self.variable:
            raise RuntimeError("Cannot check if null variable is defined")

    def execute(self, variables, phase):
        "Run this step"

        key = self.variable.lower()

        # remove leading and trailing brackets
        if key.startswith("<"):
            key = key[1:]
        if key.endswith(">"):
            key = key[:-1]
        key = key.strip()

        if key in variables:
            if phase != "test":
                LOG.debug("Variable is defined: %s : '%s'"%
                    (self.variable, variables[key]))
            self.ret = 0
        else:
            if phase != "test":
                LOG.debug("Variable is not defined: '%s'"% self.variable)
            self.ret = 1
        self.output = ''


STATEMENT_HANDLERS = {
    'set': VariableDefinition,
    'include': IncludeStep,
    'logfile': LogFileStep,
    'defined': VariableDefinedCheck,
    'call'   : FunctionCall,
    'end'    : ExecutionEndStep, }


def LoadScriptFile(filepath):
    "Load the script file and check that variable references work"

    steps = ParseYAMLFile(filepath)

    if not steps:
        return []

    if not isinstance(steps, list):
        raise RuntimeError(
            "Error parsing script file. Expected list of steps got "
            "'%s'. file: '%s'"% (type(steps).__name__, filepath))

    return ParseSteps(steps)


def ExecuteSteps(steps_, variables, phase):
    "Execute the steps"

    errors = []

    if phase == "test":
        steps = copy.deepcopy(steps_)
    else:
        steps = steps_

    for step in steps:
        try:
            step.execute(variables, phase)

        except ErrorCollection, e:
            if phase != "test":
                raise
            errors.extend(e.errors)
        except RuntimeError, e:
            if phase != "test":
                raise
            errors.append(e)

    if errors:
        raise ErrorCollection(errors)

    return steps


def PopulateVariables(script_file, cmd_line_vars):
    "Allow variables from the command line to be used also"
    variables = {}
    vars_to_wrap = {}
    for key, value in dict(os.environ).items():
        vars_to_wrap["shell." + key] = value

    vars_to_wrap.update(cmd_line_vars)
    for var, val in vars_to_wrap.items():
        var = var.lower()
        variables[var] = val

    variables.update({
        '__script_dir__': os.path.abspath(os.path.dirname(script_file)),
        '__script_filename__': os.path.basename(script_file),
        '__working_dir__': os.path.abspath(os.getcwd())})

    return variables


def ValidateArgumentCounts(steps, count_db):
    """Ensure commands have the correct number of arguments"""
    # get the name of the command
    errors = []

    #try:
    #    parts = shlex.split(self.params)
    #except ValueError:
    #    LOG.info(
    #        "The command '%s' is not a valid shell command"%
    #            self.params)
    #    # it is not a valid shell command - so just use a normal split
    #    parts = self.params.split()

    for step in steps:
        # skip non command steps
        if not isinstance(step, CommandStep):
            continue

        # posix was not avilable for shlex.split in python 2.5.1
        parts = list(shlex.shlex(step.step_data, posix = False))

        command = os.path.basename(parts[0].lower())

        # See if it is in the DB
        if command in count_db:

            # If it is then get the count of it's parameters
            arg_count = len(parts) -1

            lower_limit, upper_limit = count_db[command]

            # check that is it appropriate
            if not lower_limit <= arg_count <= upper_limit:

                errors.append(RuntimeError((
                    "Invalid number of parameters '%d'. "
                    "Expected %d to %d. Command:\n\t%s")% (
                        arg_count,
                        lower_limit,
                        upper_limit,
                        step.raw_step)))

    if errors:
        raise ErrorCollection(errors)


def ReadParamRestrictions(param_file):
    "Read the param counts from param_file"
    params = ConfigParser.RawConfigParser()

    try:
        if (not params.read(param_file) or
            not params.has_section('param_counts')):

            LOG.debug(
                "Param file does not exist or does "
                "not contain [param_counts]")
            return {}

    except ConfigParser.ParsingError, e:
        LOG.warning("WARNING: "+ str(e))
        return {}

    counts_db = {}
    for (executable, counts) in params.items('param_counts'):
        executable = executable.lower().strip()
        if "-" in counts:
            upper_lower = [p.strip() for p in counts.split("-")]
        else:
            upper_lower = counts.strip(), counts.strip()

        parsed_counts = []
        for val in upper_lower:
            if val == "*":
                val = sys.maxint
            else:
                try:
                    val = int(val)
                except ValueError:
                    LOG.info(
                        "Param counts for '%s' are not valid: '%s'"%(
                            executable, counts))
                    continue
            parsed_counts.append(val)

        if len(parsed_counts) == 2:
            counts_db[executable] = parsed_counts

    return counts_db


def ExecuteScriptFile(file_path, cmd_vars, check = False):
    "Load and execute the script file"
    variables = PopulateVariables(file_path, cmd_vars)
    LOG.debug("Environment:"% variables)

    steps = LoadScriptFile(file_path)

    LOG.debug("TESTING STEPS")

    variables_copy = copy.deepcopy(variables)
    steps_copy = copy.deepcopy(steps)
    steps = ExecuteSteps(steps_copy, variables_copy, "test")

    arg_counts_db = ReadParamRestrictions(PARAM_FILE)
    ValidateArgumentCounts(steps, arg_counts_db)

    # only checking - so quit before executing steps
    if check:
        print "No Errors"
        return steps, variables

    LOG.debug("RUNNING STEPS")
    ExecuteSteps(steps, variables, 'run')

    return steps, variables


def Main():
    "Parse command line arguments, read script and dispatch the request(s)"

    start_time = time.time()

    try:
        options = cmd_line.GetValidatedOptions()
    except RuntimeError, e:
        LOG.info(e)
        sys.exit(1)

    # make sure that all handlers print debug messages if verbose has been
    # requested
    if options.verbose:
        for handler in LOG.handlers:
            handler.setLevel(logging.DEBUG)

    LOG.debug("Run Options:"% options)

    try:
        ExecuteScriptFile(options.script_file, options.variables, options.check)
    except ErrorCollection, e:
        e.LogErrors()
        if options.debug:
            LOG.exception(e)
        sys.exit(1)
    except EndExecution, e:
        LOG.info(e.msg)
        sys.exit(e.ret)
    except RuntimeError, e:
        LOG.error(e)
        if options.debug:
            LOG.exception(e)
        sys.exit(1)
    except Exception, e:
        LOG.critical('Unknown Error: %s'% e)
        LOG.exception(e)
        sys.exit(99)
    finally:
        if options.timed:
            time_taken = time.time() - start_time
            minutes = time_taken // 60
            secs = time_taken % 60
            LOG.info("Execution took %d minute(s) and %0.2f seconds"%
                (minutes, secs))


if __name__ == "__main__":
    try:
        Main()
    finally:
        logging.shutdown()
