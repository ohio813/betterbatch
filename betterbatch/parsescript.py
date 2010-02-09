"""Parse a script and return the list of steps ready to executed"""
import re
import os
import logging
import shlex
import sys
import ConfigParser

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
        for var, strings in sorted(undef_var_errs.items()):
            LOG.fatal("'%s'"% var)

            for string in strings:
                LOG.fatal("    %s"% string)

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

        # Parse the yaml data
        script_data = yaml.load(yaml_data)
        return script_data

    except IOError, e:
        raise RuntimeError(e)

    except yaml.parser.ScannerError, e:
        raise RuntimeError("%s - %s"% (yaml_file, e))

    except yaml.parser.ParserError, e:
        raise RuntimeError("%s - %s"% (yaml_file, e))


def ParseVariableDefinition(var_def):
    """Return the variable name and variable value of a variable definition"""

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
        if variable in loop:
            if len (loop) > 1:
                errors.append("Loop found in variable definition "
                    "'%s', variable %s"% (original_text, loop))
            continue
        loop.append(variable)

        try:
            # ensure that any variables in the variable value are also
            # replaced
            var_value = ReplaceVariableReferences(
                variables[variable].value, variables, loop)

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


def ReplaceVariablesInSteps(steps, defined_variables, update = False):
    "Replace variables in all the steps"

    # don't modify the variables passed in
    if not update:
        defined_variables = defined_variables.copy()

    errors = []
    for step in steps:
        try:
            step.replace_vars(defined_variables, update = update)

            if isinstance(step, VariableDefinition):
                defined_variables[step.name] = step

        except ErrorCollection, e:
            errors.extend(e.errors)

    if errors:
        raise ErrorCollection(errors)


def ReplaceExecutableSections(text, variables, execute = True):
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

        if execute:
            # text before the section
            replaced.append(text[last_section_end:section.start()])
            #step.replace_vars(variables, update=True)
            ReplaceVariableReferences(text, variables)
            step.execute(variables)

            replaced.append(step.output.strip())
            last_section_end = section.end()
        else:
            # if we are not actually executing - don't actually replace the
            # variables references. We still try and replace vars to ensure
            # that they are defined
            step.replace_vars(variables, update=False)

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

    parsed_step = None
    # get the correct handler, if the handler is not a known one
    # then treat it as a command
    if statement_type in STATEMENT_HANDLERS:
        handler = STATEMENT_HANDLERS[statement_type]
        # as all known statement types have statements without spaces
        # we can use the simple splitting used above to construct the type
        parsed_step = handler(step, step_data)

    else:
        # more complex splitting maybe required so we let the command do
        # the parsing
        parsed_step = CommandStep(step)

    return parsed_step


def ParseComplexStep(step):
    "The step is not a string - so parse what kind of step it is"
    statements_by_type = {}
    for key in step.keys():
        clean_key, key_data = SplitStatementAndData(key)
        statements_by_type[clean_key.lower()] = (key, key_data, step[key])

    # if it iss an IF statement
    if 'if' in statements_by_type:

        if 'and' in statements_by_type and 'or' in statements_by_type:
            raise RuntimeError(
                "You cannot mix AND and OR statements in a single IF '%s'"%
                    step)

        conditions = []
        if_steps = []
        else_steps = []
        # check that there are no invalid blocks
        and_or = []
        for key in statements_by_type:
            type, condition, steps = statements_by_type[key]

            if key in ("if", 'and', 'or'):

                # if there are steps they must be the 'if' steps
                if steps:
                    if if_steps:
                        raise RuntimeError(
                            "Only one of the if/and/or "
                            "statements can have steps: %s"% step)

                    if_steps = ParseSteps(steps)

                conditions.append((key, ParseStep(condition)))

            elif key == 'else':
                else_steps = ParseSteps(steps)

            else:
                raise RuntimeError(
                    "If is not correclty defined expected \n"
                    "- if COND:\n"
                    "[- and/or COND:]\n"
                    "    - DO_STEPS\n"
                    "  else:\n"
                    "    - ELSE_STEPS")

        if not if_steps + else_steps:
            raise RuntimeError(
                "IF statement has no 'if_true' or 'else' statements '%s'"%
                    conditions)

        return IfStep(step, conditions, if_steps, else_steps)

    elif 'for' in statements_by_type:
        raise NotImplementedError("For steps are not implemented yet")

    else:
        raise RuntimeError("Unknown Complex step type: '%s'"%
            statements_by_type.keys())


class Step(object):
    "Represent a generic step - should never actually be instantiated"

    def __init__(self, raw_step):
        self.raw_step = raw_step
        #self.referenced_variables = FindVariableReferences(raw_step)
        self.step_data = raw_step

    def __str__(self):
        return str(self.raw_step)

    def __repr__(self):
        return "<%s %s>"% (self.__class__.__name__, self.raw_step)


class VariableDefinition(Step):
    "A step in the form set varname = var value"

    def __init__(self, raw_step, step_data):
        Step.__init__(self, raw_step)
        try:
            self.name, self.value = ParseVariableDefinition(step_data)
        except RuntimeError, e:
            raise RuntimeError(str(e)% self.raw_step)

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced. Note that we do NOT call ReplaceVariableReferences
        for VariableDefinition instances - ReplaceVariableReferences will do
        that when we actually need it. The reason for this is that a variable
        may reference a variable that is defined/changed later.
        """
        #if update:
        #    self.value = ReplaceVariableReferences(self.value, variables)
        # Replace executable sections - If execute is False - then the
        # command will not be actually run
        new_val = ReplaceExecutableSections(
            self.value, variables, execute = update)

        if update:
            self.value = new_val

    def execute(self, variables, raise_on_error = True):
        """Set the variable

        Note - we don't replace all sub variables at this point"""

        # does the variable reference itself
        refs = FindVariableReferences(self.value)
        value = self.value
        if self.name in refs:

            # get a new name for the old value (so we have it)
            i = 0
            prev_var = self.name
            while prev_var in variables:
                prev_var = "%s._%d_"% (self.name, i)
                i += 1

            # keep a copy of the old value under the new name
            variables[prev_var] = variables[self.name]
            variables[prev_var].name = prev_var

            # and update the current value to reference the new variable
            for match in refs[self.name]:
                self.value = self.value.replace(match, "<%s>"% prev_var)

        #self.value = ReplaceExecutableSections(
        #    self.value, variables, execute = True)
        self.replace_vars(variables, update = True)

        # all we do at this point is to ensure that the variables
        # includes the current value.
        variables[self.name] = self

    def __repr__(self):
        return '"%s"'% self.value


class CommandStep(Step):
    "Any general command"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        #self.output = None
        #self.ret = None
        self.qualifiers, self.step_data = self._parse_qualifiers()

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced
        """
        new_val = ReplaceExecutableSections(self.step_data, variables, execute = update)
        new_val = ReplaceVariableReferences(new_val, variables)
        if update:
            self.step_data = new_val

    def _parse_qualifiers(self):
        "Find the qualifiers and replace them"

        qualifier_re = re.compile("""
            \{\*
            (?P<qualifier>.+?)
            \*\}""", re.VERBOSE)

        qualifiers = qualifier_re.findall(self.step_data)
        parsed_step = qualifier_re.sub("", self.step_data)
        return qualifiers, parsed_step

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

    def execute(self, variables, raise_on_error = True):
        "Run this step"
        self.replace_vars(variables, update = True)

        # Check if the command in the mapping
        parts = SplitStatementAndData(self.step_data)

        cmd = parts[0].strip().lower()
        if cmd in built_in_commands.NAME_ACTION_MAPPING:
            func = built_in_commands.NAME_ACTION_MAPPING[cmd]
            params = parts[1]
            cmd_log_string = self.command_as_string_for_log(cmd, params)
        else:
            func = built_in_commands.SystemCommand
            params = self.step_data
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
                ["   " + line for line in self.output.strip().split("\r\n")])
        else:
            indented_output = '\n'

        if self.ret and raise_on_error and not 'nocheck' in self.qualifiers:
            message = (
                'Non zero return (%d) CMD: %s \n %s'%(
                    self.ret, cmd_log_string, indented_output))

            raise RuntimeError(message)

        if 'echo' in self.qualifiers and self.output.strip():
            LOG.info(self.output.strip())

        elif indented_output != "\n":
            LOG.debug("Output from command:\n%s"% indented_output)


class IfStep(Step):
    "An IF block"

    def __init__(self, raw_step, conditions, if_steps, else_steps):
        Step.__init__(self, raw_step)
        self.conditions = conditions
        self.if_steps = if_steps
        self.else_steps = else_steps

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced"""

        for cond_type, cond in self.conditions:
            cond.replace_vars(variables, update = update)

        # only try to replace the variables when NOT executing
        # because when executing both sides will not be exucuted
        # and we will explictily update the one we are executing.
        if not update:
            # replace in the 'else' section
            ReplaceVariablesInSteps(
                self.else_steps, variables, update = False)

            # if the condition is checking if a variable is defined
            # then we can take it for granted that it is defined, so
            variables_copy = variables.copy()
            for cond_type, condition in self.conditions:
                if (isinstance(condition, VariableDefinedCheck) and
                    condition.variable not in variables):
                    variables_copy[condition.variable] = \
                        VariableDefinition("",'%s='% condition.variable)
            # use the copy of the variables as they may be required
            ReplaceVariablesInSteps(
                self.if_steps, variables_copy, update = False)

    def execute(self, variables, raise_on_error = True):
        "Run this step"
        self.replace_vars(variables, update=True)

        # check if the condition is true
        #try:
        conditions_type = 'and'
        condition_values = []
        for cond_type, condition in self.conditions:
            LOG.debug("Testing Condition: '%s'"% condition)
            condition.execute(variables, raise_on_error = False)
            condition_values.append(condition.ret)

            if cond_type == "or":
                conditions_type = "or"

        # either AND and All should have passed (not any failed)
        # or OR and at least one pass
        if ((conditions_type == "and" and not any(condition_values)) or
            (conditions_type == "or" and 0 in condition_values)):
            LOG.debug("Condition evaluated to true: %s"% condition.output)
            steps_to_exec = self.if_steps
        else:
            LOG.debug(
                "Condition evaluated to false: %s"% condition.output)
            steps_to_exec = self.else_steps

        steps_to_exec = FinalizeSteps(steps_to_exec, variables)

        # replace variables in the steps to be executed
        ReplaceVariablesInSteps(steps_to_exec, variables, update = True)

        # Execute the steps
        for step in steps_to_exec:
            step.execute(variables)

    def __repr__(self):
        return "<IF %s...>"% self.conditions


class ExecutionEndStep(Step):
    "Request end execution of the script"

    def __init__(self, raw_step, ret_message = None):
        Step.__init__(self, raw_step)
        self.ret = 0
        self.message = ''

        parts = ret_message.split(',', 1)
        try:
            self.ret = int(parts[0])
        except ValueError:
            raise RuntimeError(
                "First item of END should be the error return (number), "
                "0 for success: '%s'"% raw_step)

        if len(parts) == 2:
            self.message = parts[1].strip()

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced
        """
        message = ReplaceVariableReferences(self.message, variables)
        if update:
            self.message = message

    def execute(self, variables, raise_on_error = True):
        "Run this step"
        self.replace_vars(variables, update = True)
        raise EndExecution(self.ret, self.message)


class IncludeStep(Step):
    "Include steps from elsewhere"

    def __init__(self, raw_step, filename):
        Step.__init__(self, raw_step)
        if not filename:
            raise RuntimeError("Include with no filename.")
        self.filename = filename

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced
        """
        new_val = ReplaceVariableReferences(self.filename, variables)
        if update:
            self.filename = new_val

    def execute(self, variables, raise_on_error = True):
        "Run this step"
        # todo: should the __script_dir__ be updated to the include
        # directory? if yes- then don't forget to set it back afterwards
        # in a safe try finally!

        self.replace_vars(variables, update = True)

        self.filename = os.path.join(
            variables['__script_dir__'].value, self.filename)

        self.steps = LoadScriptFile(self.filename)
        # we may not be abel to do this at this stage
        # as execute for includes will be done before the variables are
        # added!, so steps inside the includes will not have the all
        # the variables available
        #self.steps = FinalizeSteps(self.steps, variables)


class LogFileStep(Step):
    "Specify the log file"

    def __init__(self, raw_step, filename):
        Step.__init__(self, raw_step)
        if not filename:
            raise RuntimeError("logfile with no filename.")
        self.filename = filename

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced
        """
        new_val = ReplaceVariableReferences(self.filename, variables)
        if update:
            self.filename = new_val

    def execute(self, variables, raise_on_error = True):
        "Run this step"
        self.replace_vars(variables, update = True)
        SetupLogFile(self.filename)
        LOG.debug('Variables at logfile creation: %s'% variables)


class VariableDefinedCheck(Step):
    "Check if a variable is defined"

    def __init__(self, raw_step, variable_name):
        Step.__init__(self, raw_step)
        if not variable_name:
            raise RuntimeError("Cannot check if null variable is defined")
        self.variable = variable_name

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced
        """
        new_val = ReplaceVariableReferences(self.variable, variables)
        if new_val != self.variable:
            raise RuntimeError(
                "Checking a variable cannot use a variable reference, "
                    "remove the angle brackets: '%s'"% self.variable)

    def execute(self, variables, raise_on_error = True):
        "Run this step"

        key = self.variable.strip().lower()
        if key in variables:
            LOG.debug("Variable is defined: %s : '%s'"%
                (self.variable, variables[key]))
            self.ret = 0
        else:
            LOG.debug("Variable is not defined: '%s'"% self.variable)
            self.ret = 1
        self.output = ''

        LOG.debug('Variables at logfile creation: %s'% variables)


STATEMENT_HANDLERS = {
    'set': VariableDefinition,
    'include': IncludeStep,
    'logfile': LogFileStep,
    'defined': VariableDefinedCheck,
    #'if':   ,
    #'usage':   ,
    # 'for'
    'end': ExecutionEndStep, }



def FinalizeSteps(steps, variables):
    finalized_steps = []
    for i, step in enumerate(steps):

        if isinstance(step, IncludeStep):
            step.execute(variables)
            finalized_steps.extend(step.steps)

        else:
            #if isinstance(step, IfStep):
            #    step.if_steps = FinalizeSteps(step.if_steps, variables)
            #    step.else_steps = FinalizeSteps(step.else_steps)

            finalized_steps.append(step)

    ReplaceVariablesInSteps(finalized_steps, variables, update = False)

    return finalized_steps


def LoadScriptFile(filepath):
    "Load the script file and check that variable references work"

    steps = ParseYAMLFile(filepath)

    if not steps:
        return []

    if not isinstance(steps, list):
        raise RuntimeError(
            "Configuration file not correctly defined (remember to start each "
            "statement with '-')")

    return ParseSteps(steps)


def ExecuteSteps(steps, variables):
    "Execute the steps"
    for step in steps:
        step.execute(variables)


def PopulateVariables(script_file, cmd_line_vars):
    "Allow variables from the command line to be used also"
    variables = {}
    vars_to_wrap = dict(os.environ)
    vars_to_wrap.update(cmd_line_vars)
    for var, val in vars_to_wrap.items():
        var = var.lower()
        variables[var] = ParseStep(
            "set %s=%s"%(var, val))

    variables.update({
        '__script_dir__':
            ParseStep('set __script_dir__ = %s'%
                os.path.abspath(os.path.dirname(script_file))),
        '__script_filename__':
            ParseStep('set __script_dir__ = %s'%
                os.path.basename(script_file)),
        '__working_dir__':
            ParseStep('set __working_dir__ = %s'%
                os.path.abspath(os.getcwd()))})

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

        parts = shlex.split(step.step_data, posix = False)

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


def Main():
    "Parse command line arguments, read script and dispatch the request(s)"

    options = cmd_line.GetValidatedOptions()

    # make sure that all handlers print debug messages if verbose has been
    # requested
    if options.verbose:
        for handler in LOG.handlers:
            handler.setLevel(logging.DEBUG)

    LOG.debug("Run Options:"% options)

    variables = PopulateVariables(options.script_file, options.variables)

    LOG.debug("Environment:"% variables)

    try:
        steps = LoadScriptFile(options.script_file)
        steps = FinalizeSteps(steps, variables)

        arg_counts_db = ReadParamRestrictions(PARAM_FILE)
        ValidateArgumentCounts(steps, arg_counts_db)

        # only checking - so quit before executing steps
        if options.check:
            print "No Errors"
            sys.exit(0)

        ExecuteSteps(steps, variables)

    except ErrorCollection, e:
        e.LogErrors()
        sys.exit(1)
    except EndExecution, e:
        LOG.info(e.msg)
        sys.exit(e.ret)
    except RuntimeError, e:
        LOG.error(e)
        sys.exit(1)
    except Exception, e:
        LOG.critical('Unknown Error: %s'% e)
        LOG.exception(e)
        sys.exit(99)
    finally:
        logging.shutdown()

    sys.exit(0)


if __name__ == "__main__":
    Main()
