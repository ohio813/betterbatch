"""Parse a script and return the list of steps ready to executed"""

from __future__ import absolute_import

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

from . import built_in_commands
from . import cmd_line
from .tools import which

PARAM_FILE = os.path.join(os.path.dirname(__file__), "param_counts.ini")

# pylint: disable-msg=C0103

# Copied and adapted from http://stackoverflow.com/questions/384076#2205909
class ColoredConsoleHandler(logging.StreamHandler):
    "Allow outputing messages in color"
    def emit(self, record):
        "Emit the message in color"
        # Need to make a actual copy of the record
        # to prevent altering the message for other loggers
        myrecord = copy.copy(record)
        levelno = myrecord.levelno
        if(levelno >= 50):  # CRITICAL / FATAL
            color = '\x1b[31;1m'  # red
        elif(levelno >= 40):  # ERROR
            color = '\x1b[31m'  # red
        elif(levelno >= 30):  # WARNING
            color = '\x1b[33m'  # yellow
        elif(levelno >= 20):  # INFO
            color = '\x1b[0m'  # green
        elif(levelno >= 10):  # DEBUG
            color = '\x1b[35m'  # pink
        else:  # NOTSET and anything else
            color = '\x1b[0m'  # normal
        myrecord.msg = color + str(myrecord.msg) + '\x1b[0m'  # normal
        logging.StreamHandler.emit(self, myrecord)


def ConfigLogging(use_colors=False):
    "Create and set up the logger - returns the new logger"
    # allow the handler to output everything - we will set the actual level
    # through the logger

    logger = logging.getLogger("betterbatch")
    logger.setLevel(logging.DEBUG)

    # make the output format very simple
    basic_formatter = logging.Formatter("%(message)s")

    if not logger.handlers:
        if use_colors:
            stdout_handler = ColoredConsoleHandler()
        else:
            stdout_handler = logging.StreamHandler()

        stdout_handler.setLevel(logging.INFO)

        logger.addHandler(stdout_handler)

    for handler in logger.handlers:
        handler.setFormatter(basic_formatter)

    return logger


class CommandPathNotFoundError(RuntimeError):
    "Error raised when a path or command is not found"

    def __init__(self, command_path, string):
        self.command_path = command_path
        RuntimeError.__init__(
            self, "Command not found: '%s'" % (command_path))

        self.command_path = command_path
        self.string = string


class UndefinedVariableError(RuntimeError):
    "Error raised when a variable is used that has not been defined"

    def __init__(self, variable, string):
        RuntimeError.__init__(
            self, "Undefined Variable '%s' '%s'" % (variable, string))

        self.variable = variable
        self.string = string


class ErrorCollection(RuntimeError):
    "Class used to track many errors "

    def __init__(self, errors):
        RuntimeError.__init__(self, "%d errors" % len(errors))
        self.errors = errors

    def LogErrors(self):
        "Log all the errors in a user friendly format"

        # collect any Undefined Variables so we can log those better
        undef_var_errs = {}
        cmd_path_errs = {}
        other_errs = []
        for e in self.errors:
            if isinstance(e, UndefinedVariableError):
                var = e.variable.lower()
                strings = undef_var_errs.setdefault(var, [])
                if e.string not in strings:
                    strings.append(e.string)
            elif isinstance(e, CommandPathNotFoundError):
                cmd_path = e.command_path.lower()
                strings = cmd_path_errs.setdefault(cmd_path, [])
                if e.string not in strings:
                    strings.append(e.string)
            elif str(e) not in other_errs:
                other_errs.append(e)

        for e in other_errs:
            LOG.fatal(e)

        def print_err_summary(errs, heading, message):
            if errs:
                LOG.fatal("======== %s ========" % heading)
                LOG.error(message)
            for cmd_path, strings in sorted(errs.items()):
                LOG.fatal("\t'%s'" % cmd_path)
                for string in strings:
                    LOG.debug("\t%s" % string)
            if errs:
                LOG.info("")

        print_err_summary(
            cmd_path_errs,
            heading = "MISSING COMMANDS",
            message = '(The following commands were referenced, '
                'but the path was not found')
        print_err_summary(
            undef_var_errs,
            heading = "UNDEFINED VARIABLES",
            message = '(Check scripts or pass value on '
            'command line e.g. "var=value")')

    def __repr__(self):
        return "<ERRCOL %s>" % self.errors

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
            yaml_data = yaml_data.replace("\t", "    ")
            LOG.warning(
                "WARNING: Script contained one or more tab (\\t) characters.\n"
                "         They have been replaced by spaces for processing:\n"
                "         '%s'" % yaml_file)

        # ensure that all opening braces are also closed
        if yaml_data.count('{{{') != yaml_data.count('}}}'):
            raise RuntimeError(
                "Mismatched opening {{{ and closing }}} in '%s'" % yaml_file)

        # only colons at the end of lines to be treated as YAML mappings
        re_non_end_colon = re.compile(r":( *)(?!\s*$)", re.MULTILINE)
        yaml_data = re_non_end_colon.sub(r"+++++colon+++++\1", yaml_data)

        # and allow colons in echo statements
        echo_end_colon = re.compile(r'^(\s*\-\s+echo\s+.*)\:', re.I | re.M)
        yaml_data = echo_end_colon.sub(r"\1+++++colon+++++", yaml_data)

        # avoid the 'double quote parsing of YAML'
        yaml_data = yaml_data.replace('"', '+++++dblquote+++++')

        # ensure that USAGE, echo or end statements are treated
        # as pre-formatted strings
        blocks_to_preformat = re.compile(
            r"^( *)\-( +)((set +usage *=\s*|echo\s+|end\s+)[^\r\n]*$)", re.I | re.M)
        yaml_data = blocks_to_preformat.sub(r"\1- |\n\1    \3", yaml_data)

        # allow new-lines in {{{ }}} quoted strings
        brace_quoted = re.compile(r"\{\{\{.*?\}\}\}", re.DOTALL)
        for quoted in brace_quoted.finditer(yaml_data):
            quoted_text = quoted.group(0)

            #  we keep the same length with these replacements
            quoted_text = quoted_text.replace("\r\n", "  ")
            quoted_text = quoted_text.replace("\n", " ")
            quoted_text = quoted_text.replace("\r", " ")

            yaml_data = (
                yaml_data[:quoted.start()] +
                quoted_text +
                yaml_data[quoted.end():])

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
            if isinstance(item, list):
                for i, elem in enumerate(item):
                    item[i] = strip_string_forcers(elem)
                return item
            if isinstance(item, dict):
                new_dict = {}
                for key, value in item.items():
                    new_key = strip_string_forcers(key)
                    new_val = strip_string_forcers(value)
                    new_dict[new_key] = new_val
                return new_dict
            if item is None:
                return None
            raise RuntimeError("Unknown structure type! '%s'" % item)

        script_data = strip_string_forcers(script_data)

        return script_data

    # allow IOErrors to propogate up - they can be handled better at a
    # higher level
    #except IOError, e:
    #    raise RuntimeError(e)

    except yaml.parser.ScannerError, e:
        raise RuntimeError("%s - %s" % (yaml_file, e))

    except yaml.parser.ParserError, e:
        raise RuntimeError("%s - %s" % (yaml_file, e))


def ParseVariableDefinition(var_def, function=None):
    """Return the variable name and variable value of a variable definition

    allow_no_value was added to allow variables to be defined but not have
    a value - currently this is only used for Function definitions"""

    # NOTE: do not add %var_def after the errors - this will be added by the
    # the code that calls this method!!

    name_value = [p.strip() for p in var_def.split("=", 1)]

    if function not in (None, 'definition', 'call'):
        raise ValueError(
            "Call to ParseVariableDefinition() seems to have been "
            "called with an incorrect value of function: '%s'" % function)

    if len(name_value) == 1:
        if function is None:
            raise RuntimeError(
                "Variable not defined correctly (no '='): '%s'")

        elif function == 'definition':
            #  "= Value" not required
            name, value = name_value[0], None

        elif function == 'call':
            # "name =" not required
            name, value = None, name_value[0]
    else:
        name, value = name_value


    # perform some sanity checks on the name
    if name is not None:
        if len(name.split()) > 1:
            raise RuntimeError(
                "Variable names cannot have spaces: '%s'")
        # empty name (equals was supplied but not text preceding)
        if not name:
            raise RuntimeError(
                "Variable name missing in variable definition: '%s'")

    return name, value


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

    variable_reference_re = re.compile("""
            (\<
                ([^\>\<]+)
            \>)
        """, re.X)

    # find all the variable references
    found = variable_reference_re.findall(text)

    variables_referenced = {}

    # for each of the refernece variables in this variable
    for var_ref in found:
        var_def = var_ref[0]

        # clean the variable name
        var_name = var_ref[1].strip().lower()

        # add it and the text that needs to be replaced to the dictionary
        variables_referenced.setdefault(var_name, []).append(var_def)

    return variables_referenced


def ReplaceVariableReferences(
    text, variables, loop=None, ignore_errors = False):
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
                "'%s', variables %s" % (original_text, list(set(loop))))
            continue

        loop.append(variable)

        try:
            # ensure that any variables in the variable value are also
            # replaced
            var_value = ReplaceVariableReferences(
                variables[variable], variables, loop, ignore_errors)

            for ref_to_replace in refs_to_replace:
                text = text.replace(ref_to_replace, var_value)

        except ErrorCollection, e:
            for err in e.errors:
                if isinstance(err, UndefinedVariableError):
                    new_string = "%s -> %s" % (original_text, err.string)

                    errors.append(
                        UndefinedVariableError(err.variable, new_string))
                else:
                    errors.append(err)

        loop.pop()

    if errors:
        if not ignore_errors:
            raise ErrorCollection(errors)
    else:
        # if there were any variable references - pass through it again
        if var_refs:
            text = ReplaceVariableReferences(
                text, variables, ignore_errors = ignore_errors)

    text = text.replace("{{_LT_}}", "<")
    text = text.replace("{{_GT_}}", ">")

    return text


def ParseExecSectionTokens(tokens, exe_sections, cur_block=None):
    "get the blocks"

    if cur_block is None:
        cur_block = []

    while tokens:
        token = tokens.pop()
        if token == '{{{':

            # store the ref to the exe section in the current block
            cur_block.append("{{{%d}}}" % (len(exe_sections)))

            # fill up the latest exe section
            exe_sections.append([])
            ParseExecSectionTokens(tokens, exe_sections, exe_sections[-1])
            continue

        elif token == "}}}":
            # exe section is complete - so just return
            return cur_block

        # add the normal token to the current block
        cur_block.append(token)

    return cur_block


def TokenizeExecSections(text):
    "Split up the executable sections, keeping delimiters"
    EXECUTABLE_SECTION = re.compile(
        r"""
            (\{\{\{|\}\}\})
                (.*?)
            (\{\{\{|\}\}\})""", re.VERBOSE | re.DOTALL)

    return EXECUTABLE_SECTION.split(text)


def ReplaceExecutableSections(text, variables, phase="run"):
    """If variable has {{{cmd}}} - execute 'cmd' and update value with output
    """

    # this is necessary - as otherwise {{{{* or *}}}} will not be interpreted
    # correctly
    text = text.replace("{*", "--#QUAL_#--")
    text = text.replace("*}", "--#_QUAL#--")

    tokens = TokenizeExecSections(text)
    tokens.reverse()
    exe_sections = []
    base_value = ParseExecSectionTokens(tokens, exe_sections)
    base_value = "".join(base_value)

    def PushOutputsIntoString(recieving, outputs):
        "replace any command reference e.g. {{{1}}} with the computed output"
        sub_sections = re.findall("\{\{\{(\d+)\}\}\}", recieving)
        for sub_section in sub_sections:
            recieving = recieving.replace(
                "{{{%s}}}" % (sub_section),
                outputs[int(sub_section)])
        return recieving

    # go over them backwards - because the later ones do not rely on
    # earlier ones - in case of exe sections within exe sections
    outputs = [None] * len(exe_sections)
    for i, command in enumerate(reversed(exe_sections)):
        # convert it back to a string
        command = "".join(command).strip()

        command = PushOutputsIntoString(command, outputs)

        # replace the escaped qualifiers
        command = command.replace("--#QUAL_#--", "{*")
        command = command.replace("--#_QUAL#--", "*}")

        step = ParseStep(command)
        step.execute(variables, phase)
        if not hasattr(step, 'output') and isinstance(step, FunctionCall):
            raise RuntimeError(
                "Function call with no return statement, "
                "No value to retrieve:\n\t'%s'" % text)

        # Escape any greater/less than characters in the output of the
        # command
        output = step.output.strip()
        output = output.replace("<", "<<")
        output = output.replace(">", ">>")

        # ensure that the output is stored at teh correct position in the
        # list (a bit more complicated as we are going backwards)
        outputs[len(exe_sections) - i - 1] = output

    text = PushOutputsIntoString(base_value, outputs)
    text = text.replace("--#QUAL_#--", "{*")
    text = text.replace("--#_QUAL#--", "*}")

    return text


def RenderVariableValue(
    value, variables, phase, loop=None, ignore_errors=False):
    """Replace variables and run + capture executable sections

    if ignore_errors = True then any missing variables and any errors with
    the executable sections are ignored
    """

    value = ReplaceVariableReferences(
        value, variables, loop, ignore_errors=ignore_errors)
    try:
        value = ReplaceExecutableSections(value, variables, phase)
    except Exception, e:
        if not ignore_errors:
            raise

    return value


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
            LOG.debug("Changing log file to: '%s'" % log_filename)
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
    for step in steps:
        if step is None:
            continue

        tmp_steps = ParseStep(step)
        if isinstance(tmp_steps, list):
            parsed_steps.extend(tmp_steps)
        else:
            parsed_steps.append(tmp_steps)

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
            "You cannot mix AND and OR statements in a single IF '%s'" %
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
                        "statements can have steps: %s" % step)
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
                "'If' statement is not correctly defined\n"
                "- if COND:\n"
                " [and/or COND:]\n"
                "    - DO_STEPS\n"
                "  else:\n"
                "    - ELSE_STEPS")

    if not if_steps + else_steps:
        raise RuntimeError(
            "IF statement has no 'if_true' or 'else' statements '%s'" %
                conditions)

    return IfStep(step, conditions, if_steps, else_steps)


def ParseForStep(step, statements):
    "Parse an for complex step"
    if len(statements) > 1:
        raise RuntimeError(
            "For statements should not have more than one 'key': %s" %
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
            "Parallel blocks can have more only one parent: %s" %
                statements)
    # just get the steps
    steps = statements[0][-1]
    steps = ParseSteps(steps)

    return ParallelSteps(step, steps)


def ParseFunctionNameAndArgs(name_args, def_or_call):

    # we need to parse out the name_args which should be something like:
    # function_name (arg, arg = default, arg = default)
    found = re.search("^([^(]+)\((.*)\)(.*)", name_args)

    if not found:
        raise RuntimeError("Function definition seems to be incorrect: '%s'" %
            name_args)

    name = found.group(1).strip()
    args = found.group(2).split(",")

    # strip off 1 trailing empty arg (caused by a trailing comma)
    if args and args[-1].strip() == "":
        del args[-1]

    parsed_args = []
    for arg in args:
        try:
            parsed_args.append(
                ParseVariableDefinition(arg, function=def_or_call))
        except RuntimeError, e:
            raise RuntimeError(str(e) % arg + " - '%s" % name_args)

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
                    "In a function definition or function call you cannot "
                    "define an argument without a default after an argument "
                    "that has a default. '%s'" % arg_name)
        else:
            default_found = True

    return name, parsed_args


def ParseFunctionDefinition(step, statements):
    "Parse a function definition complex step"
    if len(statements) > 1:
        raise RuntimeError(
            "Function blocks can have more only one header: %s" %
                statements)

    # Extract out the various bits of the function header
    dummy, name_args, steps = statements[0]
    name, args = ParseFunctionNameAndArgs(name_args, def_or_call="definition")

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

    # if it is an IF statement
    if 'if' in clean_keys:
        return ParseIfStep(step, statements, clean_keys)

    elif 'for' in clean_keys:
        return ParseForStep(step, statements)

    elif 'parallel' in clean_keys:
        return ParseParallelStep(step, statements)

    elif 'function' in clean_keys:
        return ParseFunctionDefinition(step, statements)

    elif 'set' in clean_keys:
        return ParseMappingVariableDefinition(step, statements)

    elif set(clean_keys).intersection(['else', 'or', 'and']):
        raise RuntimeError(
            "'%s' without 'if'. Please ensure that you do *not* have "
            "a dash in front of %s, and the first letter of '%s' should be "
            "indented to the same level as the 'i' of if" % (
                clean_keys[0], clean_keys[0], clean_keys[0]))

    else:
        raise RuntimeError("Unknown Complex step type: '%s'" %
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
        return "<%s %s>" % (self.__class__.__name__, self.raw_step)


def ParseMappingVariableDefinition(step, statements):
    """Parse a mapping variable definition

    A mapping variable is defined like:
        - set var_name:
            - key1 -> value 1
            - key2 -> value 2
            - key3 -> value 3

    Usage is like <var_name.key1>

    There is also a special method <var_name.keys> which allows you to iterate
    over the items e.g.

    - for key in <var_name.keys>:
        - echo KEY: <key> with VALUE: <var_name.<key> >
    """

    if len(step.keys()) > 1:
        raise RuntimeError(
            "Cannot have more than one key in "
            "a mapping variable definition: '%s'" % step)

    var_name = step.keys()[0].split()[1]
    key_values = statements[0][2]
    variable_defs = [VariableDefinition(
        "set %s = %s" % (var_name, key_values))]
    keys = []

    if not key_values:
        raise RuntimeError(
            "Mapping variable has no key, value pairs: '%s'" % step)

    for item in key_values:

        # ensure that the key -> value is defined correctly
        if '->' not in item:
            raise RuntimeError(
                "Mapping variable item is not defined "
                "correctly - it must be in the form key -> value. '%s' (%s)" %
                    (step, item))

        # split the key and value up
        key_name, value = [i.strip() for i in item.split("->")]

        # add  a variable definition for this key
        variable_defs.append(VariableDefinition("set %s.%s = %s" % (
            var_name, key_name, value)))

        # Keep the keys as we need to add the .keys variable also
        keys.append(key_name)

    # add the 'keys' values
    variable_defs.append(
        VariableDefinition("set %s.keys = %s" % (var_name, "\n".join(keys))))

    return variable_defs


class VariableDefinition(Step):
    "A step in the form set varname = var value"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)

        # check if there are any qualifiers
        self.step_data, self.qualifiers = ParseQualifiers(self.step_data)

        try:
            self.name, self.value = ParseVariableDefinition(self.step_data)
            self.name = self.name.lower()
        except RuntimeError, e:
            raise RuntimeError(str(e) % self.raw_step)

    def execute(self, variables, phase):
        """Set the variable

        Note - we don't replace all sub variables at this point."""

        new_val = self.value
        if 'delayed' not in self.qualifiers:
            try:
                new_val = ReplaceVariableReferences(new_val, variables)
            except ErrorCollection:
                # when testing - even if there is an issue where this variable
                # references missing variables, this varialbe is still
                # defined - and shouldn't be raised an a missing variable
                if phase == "test":
                    variables[self.name] = ""

            new_val = ReplaceExecutableSections(new_val, variables, phase)

        if phase != "test":
            LOG.debug("Set variable '%s' to value '%s'" % (
                self.name, new_val))

        variables[self.name] = new_val

    def __repr__(self):
        return '"%s"' % self.value


class Qualifier(str):
    def __hash__(self):
        return hash(self.lower().strip())


def ParseQualifiers(text):
    "Find the qualifiers and replace them"

    # remove the executable sections first becuase we don't
    # need or want to parse the qualifiers in these sections yet
    exe_sections = []
    for i, exe_section in enumerate(
            re.findall(r"\{\{\{.+?\}\}\}", text)):
        text = text.replace(exe_section, "{{{%d}}}" % i)
        exe_sections.append(exe_section)

    qualifier_re = re.compile("""
        \{\*
        (?P<qualifier>.+?)
        \*\}""", re.VERBOSE)

    qualifiers = qualifier_re.findall(text)
    text = qualifier_re.sub("", text)

    # replace the executable sections
    for i, section in enumerate(exe_sections):
        text = text.replace("{{{%d}}}" % i, section)

    # ensure that the qualifiers are lower case and no extra spaces
    # though keep the original also - as some command need to use those
    qualifiers = [Qualifier(q) for q in qualifiers]

    return text, qualifiers


def ValidateCommandPath(command, qualifiers = None):
    "Check command path and raise CommandPathNotFoundError if path not found"

    command_path = shlex.split(command, posix = False)[0]
    command_path = command_path.strip('"')
    # Shell commands, there is no need for checking
    if command_path.lower() in built_in_commands.SHELL_COMMANDS:
        pass
    else:
        try:
            # If the path does not exist and which.which() cannot find it
            # on the path, which.which() raises an error
            if (os.path.exists(command_path) or which.which(command_path)):
                pass
        except which.WhichError:
            raise CommandPathNotFoundError(command_path, command)


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
            command_message = "'%s' -> '%s'" % (
                self.raw_step, command_message)
        else:
            command_message = "'%s'" % command_message

        #command_message = command_message.replace('\\', '\\\\')
        command_message = command_message.replace('\r\n', '\\r\\n')

        return command_message

    def execute(self, variables, phase):
        "Run this step"

        errors = []

        try:
            command_text = RenderVariableValue(
                            self.step_data, variables, phase)
        except ErrorCollection, e:
            if phase != "test":
                raise
            # if we are in the test phase we want to be able to continue (and
            # do the command path testing, but still not lose the
            # UndefinedVariable errors raised.
            for err in e.errors:
                errors.append(err)
            # Re-run RenderVariableValue() to replace as many variables
            # as possible while ignoring errors
            command_text = RenderVariableValue(
                self.step_data, variables, phase, ignore_errors=True)

        variables['__last_return__'] = '0'

        # split up statement/executable name from the arguments
        parts = SplitStatementAndData(command_text)

        cmd = parts[0].strip().lower()

        # if we are in test mode - then just do some testing and exit
        if phase == 'test':
            # if it is not a built in
            if cmd not in built_in_commands.NAME_ACTION_MAPPING:
                # check if the path can be found
                try:
                    ValidateCommandPath(command_text)
                except CommandPathNotFoundError, CmdErr:
                    errors.append(CmdErr)
            if errors:
                raise ErrorCollection(errors)
            return
        # Figure out if it is an internal or external command that
        # is being executed.
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
            LOG.debug("Executing command %s" % cmd_log_string)
            # call the function and get the output and the return value
            self.ret, self.output = func(params, self.qualifiers)
            variables['__last_return__'] = str(self.ret)
        except KeyboardInterrupt:
            variables['__last_return__'] = 'cancelled'
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
                'Non zero return (%d) CMD: %s \n %s' %
                    (self.ret, cmd_log_string, indented_output))

        #if 'echo' in self.qualifiers and self.output.strip():
        #    LOG.info(self.output.strip())

        elif indented_output != "\n":
            LOG.debug("Output from command:\n%s" % indented_output)


class EchoStep(Step):
    "Request end execution of the script"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        step_data = SplitStatementAndData(raw_step)[1]
        self.message, self.qualifiers = ParseQualifiers(step_data)
        self.output = ""

    def execute(self, variables, phase):
        message = RenderVariableValue(self.message, variables, phase)

        logging_func = LOG.info
        if 'as_fatal' in self.qualifiers:
            logging_func = LOG.fatal
        if 'as_error' in self.qualifiers:
            logging_func = LOG.error
        if 'as_warning' in self.qualifiers:
            logging_func = LOG.warning
        if 'as_debug' in self.qualifiers:
            logging_func = LOG.debug

        if phase != "test":
            logging_func(message)
            self.output = message


class ParallelSteps(Step):
    "An set of command steps to be executed in parallel"

    def __init__(self, raw_step, steps):

        self.raw_step = raw_step

        self.steps = steps

    def execute(self, variables, phase):
        "Run this step"

        # Test the steps
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
                LOG.debug("starting step in new thread: '%s'" % step)

            # define variables immediately
            if isinstance(step, VariableDefinition):
                step.execute(variables, phase)
            else:
                # otherwise add the step to be executed with the
                # current values of the variables
                t = ThreadStepRunner(step, copy.deepcopy(variables))
                t.start()
                threads.append(t)

        # wait for the threads to finish
        errs = []
        while threads:
            for t in threads:
                # Try to joiin the thread, but timeout very quickly
                t.join(.01)

                # if the thread has finished, print a message and
                # remove it
                if not t.isAlive():
                    if phase != "test":
                        LOG.debug("Thread finished: '%s'" % t.step)
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

        loop_condition, self.qualifiers = ParseQualifiers(loop_condition)

        #split on ' in '
        self.variable, self.command = [
            part.strip() for part in loop_condition.split(' in ', 1)]
        self.variable = self.variable.lower()

    def execute(self, variables, phase):
        "Run this step"

        cmd_output = RenderVariableValue(self.command, variables, phase)

        # split the variables
        values = cmd_output.split("\n")

        # unloop the loop
        loop_steps = []
        for val in values:
            # create a variableDefinition for this
            loop_steps.append(
                VariableDefinition(
                    "set %s = %s" % (self.variable, val)))
            loop_steps.extend(self.steps)

        if 'parallel' in self.qualifiers:
            loop_steps = [ParallelSteps(self.raw_step, loop_steps)]

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
            self.output = ''
            return

        for cond_type, condition in self.conditions:
            LOG.debug("Testing Condition: '%s'" % condition)
            try:
                condition.execute(variables, phase)
            except Exception, e:
                # swallow exceptions - it just means that the check failed
                # though still output some debug data
                LOG.debug("Condition raised: '%s'" % e)
                # and ensure that the failure return value is set
                condition.ret = 1

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
            LOG.debug("Condition evaluated to true: %s" % condition.output)
            self.steps_to_exec = self.if_steps

        else:
            LOG.debug(
                "Condition evaluated to false: %s" % condition.output)
            self.steps_to_exec = self.else_steps

        # Execute the steps
        if self.steps_to_exec:
            ExecuteSteps(self.steps_to_exec, variables, phase)
            if hasattr(self.steps_to_exec[-1], 'output'):
                self.output = self.steps_to_exec[-1].output

    def __repr__(self):
        return "<IF %s...>" % self.conditions


class FunctionDefinition(Step):
    "An set of command steps to be executed in parallel"

    all_functions = {}

    def __init__(self, raw_step, name, args, steps):

        self.raw_step = raw_step

        # don't allow a function with no steps
        if not steps:
            raise RuntimeError("Function definition with no steps: '%s'" %
                self.raw_step.keys()[0])

        self.name = name
        self.args = args
        self.steps = steps

        # arg has a default if the arg value is not None
        self.non_default_args = [
            arg[0] for arg in self.args if arg[1] == None]

        # keep a record of the function so that we can reference it
        FunctionDefinition.all_functions[name.lower()] = self

    def execute(self, variables, phase):
        """Nothing needs to be done here as both testing and execution
        will be done during calling"""
        pass

    def call_function(self, arg_values, variables, phase):

        if phase != "test":
            LOG.debug(
                "Function call: '%s' with args %s" % (self.name, arg_values))

        # make a copy of the variables
        vars_copy = copy.deepcopy(variables)
        vars_copy.update(arg_values)

        steps = ExecuteSteps(self.steps, vars_copy, phase)


class FunctionCall(Step):
    "A request to call a function"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)

        name_argvals = SplitStatementAndData(raw_step)[1]

        self.name, self.arg_vals = ParseFunctionNameAndArgs(
            name_argvals, def_or_call="call")

        self.positional_args = []
        self.keyword_args = {}
        for arg_name, arg_value in self.arg_vals:
            if arg_name is None:
                if self.keyword_args:
                    raise RuntimeError(
                        "Positional argument after keyword argument(s): '%s'" %
                        (arg_name))
                self.positional_args.append(arg_value)
            else:
                if arg_name in self.keyword_args:
                    raise RuntimeError(
                        "Argument '%s' specified twice in function call: '%s'" %
                        (arg_name, self.raw_step))
                self.keyword_args[arg_name] = arg_value

    def execute(self, variables, phase):
        # ensure that the function name exists
        if not self.name.lower() in FunctionDefinition.all_functions:
            raise RuntimeError(
                "Attempt to call an unknown function '%s' in call '%s'" %
                    (self.name, self.raw_step))

        function = FunctionDefinition.all_functions[self.name.lower()]

        if len(self.arg_vals) > len(function.args):
            raise RuntimeError(
                "Too many arguments passed in function call '%s'" %
                self.raw_step)

        # if the arg is a simple value (i.e. not arg = val) then it will
        # be simply passed in the order in the call
        args_to_pass = {}

        function_args = [arg[0].lower() for arg in function.args]
        unmatched_args = set(self.keyword_args.keys()).difference(
            function_args)
        if unmatched_args:
            raise RuntimeError((
                "Keyword argument(s) %s are not "
                "arguments of function '%s'") %
                    (unmatched_args, function.name))

        # for each of the remaining function definition arguments
        # match passed arguments against function arguments
        for i, (arg_name, arg_value) in enumerate(function.args):
            arg_name = arg_name.lower()

            # this will populate arguments from the positional args in the
            # function call (we have already validated that no positional arg
            # comes after a keyword arg - when parsing call)
            if len(self.positional_args) > i:
                if arg_name in self.keyword_args:
                    raise RuntimeError(
                        "Function parameter supplied as both positional "
                        "and keyword argument: '%s'" % arg_name)
                args_to_pass[arg_name] = self.positional_args[i]
                continue

            # If it is one of the passed keyword arguments
            if arg_name.lower() in self.keyword_args:
                args_to_pass[arg_name] = self.keyword_args[arg_name]

            # otherwise just use the default value after checking it
            else:
                if arg_value is None:
                    raise RuntimeError((
                        "No Value passed for function parameter %d '%s' in "
                        "function call:\n\t%s") % (
                            i + 1, arg_name, self.raw_step))

                args_to_pass[arg_name] = arg_value

        # If there was a return then set our output value
        try:
            function.call_function(args_to_pass, variables, phase)
        except FunctionReturnWrapper, e:
            self.output = e.ret.output


class FunctionReturnWrapper(Exception):
    def __init__(self, ret):
        self.ret = ret


class FunctionReturn(Step):

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        step_data = SplitStatementAndData(raw_step)[1]
        self.value, self.qualifiers = ParseQualifiers(step_data)

    def execute(self, variables, phase):
        self.output = RenderVariableValue(self.value, variables, phase)
        if phase != "test":
            message = "Returning from function: %s" % self.output
            LOG.debug(message)
        # throw ourselves up the stack!
        raise FunctionReturnWrapper(self)


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
                "0 for success: '%s'" % raw_step)

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
        self.filename, self.qualifiers = ParseQualifiers(self.filename)
        self.steps = []

    def execute(self, variables, phase):
        "Run this step"
        # todo: should the __script_dir__ be updated to the include
        # directory? if yes- then don't forget to set it back afterwards
        # in a safe try finally!

        filename = ReplaceVariableReferences(self.filename, variables)

        self.filename = os.path.abspath(os.path.join(
            variables['__script_dir__'], filename))

        # load the steps no matter
        try:
            self.steps = LoadScriptFile(self.filename)
        except Exception, e:
            # if not testing or
            # it's not an IO error
            # or it is not optional - raise the error
            if phase != "test":
                if not (isinstance(e, IOError) and
                    "optional" in self.qualifiers):
                    raise
            else:
                # so we are testing
                if not isinstance(e, IOError):
                    LOG.warning("Problem parsing include file '%s'" %
                        self.filename)
                    LOG.debug(e)
                else:
                    if "optional" in self.qualifiers:
                        LOG.debug(
                            "Optional Include missing during testing '%s'" %
                                self.filename)
                    else:
                        LOG.warning("Include missing during testing '%s'" %
                            self.filename)

        prev_script_dir = variables.get("__script_dir__", None)
        prev_script_file = variables.get("__script_filename__", None)
        try:
            if phase != "test":
                LOG.debug(
                    "Included steps from: %s" % self.filename)

            variables["__script_dir__"], variables["__script_filename__"] = \
                os.path.split(self.filename)

            self.steps = ExecuteSteps(self.steps, variables, phase)
        except Exception, e:
            if phase != "test":
                raise
        finally:
            if prev_script_dir:
                variables["__script_dir__"] = prev_script_dir

            if prev_script_file:
                variables["__script_filename__"] = prev_script_file


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
            LOG.debug('Variables at logfile creation: %s' % variables)
            variables['__logfile__'] = filename


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
                LOG.debug("Variable is defined: %s : '%s'" %
                    (self.variable, variables[key]))
            self.ret = 0
        else:
            if phase != "test":
                LOG.debug("Variable is not defined: '%s'" % self.variable)
            self.ret = 1
        self.output = ''


class ApplyCommandLineVarsStep(Step):
    """Apply the command line variable override (again)

    The command line variables are set at the very start - but this does not
    allow the user to override variables set in the script - so this command
    will re-apply them, overriding any values previously set by the scripts.
    """

    def __init__(self, raw_step):
        Step.__init__(self, raw_step + " command line variables")

    def execute(self, variables, phase):
        # no difference between run/test
        variables.update(ApplyCommandLineVarsStep.cmd_line_vars)


STATEMENT_HANDLERS = {
    'set': VariableDefinition,
    'applycommandlinevars': ApplyCommandLineVarsStep,
    'include': IncludeStep,
    'logfile': LogFileStep,
    'defined': VariableDefinedCheck,
    'call': FunctionCall,
    'echo': EchoStep,
    'return': FunctionReturn,
    'end': ExecutionEndStep, }


def LoadScriptFile(filepath):
    "Load the script file and check that variable references work"

    steps = ParseYAMLFile(filepath)

    if not steps:
        return []

    if not isinstance(steps, list):
        raise RuntimeError(
            "Error parsing script file. Expected list of steps got "
            "'%s'. file: '%s'" % (type(steps).__name__, filepath))

    return ParseSteps(steps)


#import cmd
#class Debugger(cmd.Cmd):
#    prompt = "{%s} "% os.getcwd()
#    intro = "Simple command processor example."
#
#    def __init__(self, steps, variables):
#        cmd.Cmd.__init__(self)
#        self.steps = iter(steps)
#        self.variables = variables
#
#        self.cur_step = self.steps.next()
#        print "next:", self.cur_step
#
#    def do_next(self, arg):
#        "Execute the next step"
#        self.cur_step.execute(self.variables, "run")
#        self.cur_step = self.steps.next()
#        print "next:", self.cur_step
#    do_n = do_next
#
#    def do_vars(self, arg):
#        "print the list of variables"
#        print "variables:", self.variables.keys()
#
#    def do_var(self, var_name):
#        "print the valur of a variable"
#
#        if not var_name:
#            print "Please specify a variable name"
#        elif var_name not in self.variables:
#            print "Unknown variable '%s'"% var_name
#        else:
#            print "value of '%s': '%s'"% (var_name, self.variables[var_name])
#    do_v = do_var
#
#    def do_printstep(self, var_name):
#        "print the valur of a variable"
#        print self.cur_step
#    do_ps = do_printstep


def DebugExecuteSteps(steps_, variables, phase):
    "Execute the steps"

    errors = []
    try:
        Debugger(steps_, variables).cmdloop()
    except StopIteration:
        pass

    return steps


def ExecuteSteps(steps_, variables, phase):
    "Execute the steps"

    errors = []

    if phase == "test":
        steps = copy.deepcopy(steps_)
    else:
        steps = steps_

    function_return = None

    for step in steps:
        try:
            step.execute(variables, phase)

        except FunctionReturnWrapper, e:
            # we do not return immediately if we are testing - as we
            # want to test all the steps, so store the return value and raise
            # it when finished
            if phase == 'test':
                function_return = e
                continue
            else:
                raise
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

    # if there was a 'return' (during test phase - then bubble it's return
    # value up through the call stack now (after testing all steps)
    if function_return is not None:
        raise function_return
    return steps


def PopulateVariables(script_file, cmd_line_vars):
    "Allow variables from the command line to be used also"

    for var, val in cmd_line_vars.items():
        if not var.islower():
            var_lower = var.lower()
            del cmd_line_vars[var]
            cmd_line_vars[var_lower] = val

    ApplyCommandLineVarsStep.cmd_line_vars = copy.deepcopy(cmd_line_vars)

    for key, value in dict(os.environ).items():
        cmd_line_vars["shell." + key.lower()] = value

    cmd_line_vars.update({
        '__last_return__': '0',
        '__script_dir__': os.path.abspath(os.path.dirname(script_file)),
        '__script_filename__': os.path.basename(script_file),
        '__working_dir__': os.path.abspath(os.getcwd())})

    return cmd_line_vars


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
        parts = list(shlex.shlex(step.step_data, posix=False))

        command = os.path.basename(parts[0].lower())

        # See if it is in the DB
        if command in count_db:

            # If it is then get the count of it's parameters
            arg_count = len(parts) - 1

            lower_limit, upper_limit = count_db[command]

            # check that is it appropriate
            if not lower_limit <= arg_count <= upper_limit:

                errors.append(RuntimeError((
                    "Invalid number of parameters '%d'. "
                    "Expected %d to %d. Command:\n\t%s") % (
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
        LOG.warning("WARNING: " + str(e))
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
                        "Param counts for '%s' are not valid: '%s'" % (
                            executable, counts))
                    continue
            parsed_counts.append(val)

        if len(parsed_counts) == 2:
            counts_db[executable] = parsed_counts

    return counts_db


def ExecuteScriptFile(file_path, cmd_vars, check=False):
    "Load and execute the script file"
    orig_cmd_vars = copy.deepcopy(cmd_vars)
    variables = PopulateVariables(file_path, cmd_vars)
    LOG.debug("Environment:" % variables)

    steps = LoadScriptFile(file_path)

    LOG.debug("TESTING STEPS")

    variables_copy = copy.deepcopy(variables)
    steps_copy = copy.deepcopy(steps)
    try:
        steps = ExecuteSteps(steps_copy, variables_copy, "test")
    except ErrorCollection, errs:
        # if the following conditions are True
        #   - usage variable is set
        #   - there were no variables passed on command line
        #   - there is at least one
        any_undefined_vars = any(
            [isinstance(e, UndefinedVariableError) for e in errs.errors])
        if ('usage' in variables_copy and
            any_undefined_vars and
            not orig_cmd_vars):
            LOG.info(
                ReplaceVariableReferences(
                    variables_copy['usage'],
                    variables_copy,
                    ignore_errors = True))
            # return empty steps & variables to stop the script
            return [], {}
        else:
            raise

    arg_counts_db = ReadParamRestrictions(PARAM_FILE)
    ValidateArgumentCounts(steps, arg_counts_db)

    # only checking - so quit before executing steps
    if check:
        return steps, variables

    LOG.debug("RUNNING STEPS")
    #DebugExecuteSteps(steps, variables, 'run')
    ExecuteSteps(steps, variables, 'run')

    return steps, variables


def CheckAllScriptsInDir(scripts_dir, variables):
    "Checks all the bb scripts in the same dir as scripts_dir"

    num_of_errors = 0
    for root, dirs, files in os.walk(scripts_dir):
        for file in files:
            if os.path.splitext(file)[1] == '.bb':
                try:
                    LOG.setLevel(logging.ERROR)
                    ExecuteScriptFile(
                        os.path.join(root,file),
                        variables,
                        check=True)
                except ErrorCollection, e:
                    LOG.setLevel(logging.DEBUG)
                    cmd_path_errs = [str(err) for err in e.errors
                        if isinstance(err, CommandPathNotFoundError)]
                    cmd_path_errs = set(cmd_path_errs)
                    if cmd_path_errs:
                        num_of_errors += 1
                        LOG.info("")
                        LOG.info(file)
                        for err in cmd_path_errs:
                            LOG.fatal(err)
    if not num_of_errors:
        LOG.info("No command path error")
    LOG.setLevel(logging.DEBUG)

    return num_of_errors


def Main():
    "Parse command line arguments, read script and dispatch the request(s)"

    start_time = time.time()

    global LOG
    try:
        options = cmd_line.GetValidatedOptions()
    except RuntimeError, e:
        LOG = ConfigLogging(use_colors = cmd_line.USE_COLORED_OUTPUT)
        LOG.fatal(e)
        sys.exit(1)

    LOG = ConfigLogging(use_colors=options.colored_output)

    # make sure that all handlers print debug messages if verbose has been
    # requested
    if options.verbose:
        for handler in LOG.handlers:
            handler.setLevel(logging.DEBUG)

    return_value = 0
    LOG.debug("Run Options:" % options)
    try:
        if options.check_dir:
            return_value = CheckAllScriptsInDir(
                os.path.dirname(options.script_file), options.variables)
        else:
            steps, vars = ExecuteScriptFile(
                options.script_file, options.variables, options.check)
            if not steps and not vars:
                options.timed = False
    except ErrorCollection, e:
        e.LogErrors()
        if options.debug:
            LOG.exception(e)
        return_value = 1
    except EndExecution, e:
        if e.ret == 0:
            LOG.info(e.msg)
        else:
            LOG.fatal(e.msg)
        return_value = e.ret
    except RuntimeError, e:
        LOG.error(e)
        if options.debug:
            LOG.exception(e)
        return_value = 1
    except Exception, e:
        LOG.critical('Unknown Error: %s' % e)
        LOG.exception(e)
        return_value = 99
    finally:
        if options.timed:
            time_taken = time.time() - start_time
            minutes = time_taken // 60
            secs = time_taken % 60
            LOG.info("Execution took %d minute(s) and %0.2f seconds" %
                (minutes, secs))

    if return_value != 0:
        if '__logfile__' in options.variables:
            print (
                "Script Error Log file may have more information:\n\t%s" %
                    options.variables['__logfile__'])
        else:
            print "Script Error!"

        sys.exit(return_value)


if __name__ == "__main__":

    #import cProfile
    #command = """Main()"""
    #cProfile.runctx(
    #    "Main()", globals(), locals(), filename="parsescript.profile" )

    try:
        Main()
    finally:
        logging.shutdown()
