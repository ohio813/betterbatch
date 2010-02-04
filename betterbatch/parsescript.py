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

def CreateLogger():
    "Create and set up the logger - returns the new logger"

    # allow the handler to output everything - we will set the actual level
    # through the logger
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.INFO)

    # make the output format very simple
    basic_formatter = logging.Formatter("%(levelname)s - %(message)s")
    stdout_handler.setFormatter(basic_formatter)

    # set up the logger with handler and to output debug messages
    logger = logging.getLogger("betterbatch")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_handler)
    return logger
LOG = CreateLogger()


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
    def __str__(self):
        return "<ERRCOL %s>"% self.errors

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
            errors.append("following variables cause a loop %s"% loop)
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
            if isinstance(step, VariableDefinition):
                defined_variables[step.name] = step

            step.replace_vars(defined_variables, update = update)
        except ErrorCollection, e:
            errors.extend(e.errors)

    if errors:
        raise ErrorCollection(errors)


def ReplaceExecutableSections(text, variables, execute = True):
    """If variable has {{{cmd}}} - execute 'cmd' and update value with output
    """

    EXECUTABLE_SECTION = re.compile(
        """
            \{\{\{
                \s*
                (?P<command_line>.+?)
                \s*
            \}\}\}""", re.VERBOSE)

    # See if it matches the external variable pattern
    sections = EXECUTABLE_SECTION.finditer(text)

    for section in reversed(list(sections)):
        if "{{{" in section.group('command_line'):
            raise RuntimeError(
                "Do not embed executable section {{{...}}} in another "
                "executable section: '%s'"% text)
        step = ParseStep(section.group('command_line'))

        if execute:
            step.replace_vars(variables, update=True)
            step.execute(variables)

            text = (
                text[:section.start()] +
                step.output.strip() +
                text[section.end():])
        else:
            # if we are not actually executing - don't actually replace the
            # variables references. We still try and replace vars to ensure
            # that they are defined
            step.replace_vars(variables, update=False)

    return text


def SetupLogFile(log_filename):
    "Create the log file if it has been requested"

    # try to find if the log file is already open
    # if it is - then just flush and return (without changing the logfilename)
    if os.path.exists(log_filename):
        for h in LOG.handlers:
            if (hasattr(h, 'baseFilename') and (h.baseFilename.lower() ==
                os.path.abspath(log_filename).lower())):

                h.flush()
                return
        # file is not an open handler - try removing it
        #try:
        os.unlink(log_filename)
        #except OSError:
        #    LOG.warning("Could not remove previous log file")

    h = logging.FileHandler(log_filename)
    # make the output format very simple
    basic_formatter = logging.Formatter("%(levelname)s - %(message)s")
    h.setFormatter(basic_formatter)

    LOG.addHandler(h)


def ParseStep(step):
    """Return the parsed step ready to check and execute"""
    # parse the if/for etc block
    if isinstance(step, dict):
        return ParseComplexStep(step)

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

        # check that there are no invalid blocks
        for key in statements_by_type:
            if key not in ('if', 'else'): #, 'elif'):

                raise RuntimeError(
                    "If is not correclty defined expected \n"
                    "- if COND:\n"
                    "    - DO_STEPS\n"
                    "  else:\n"
                    "    - ELSE_STEPS")

        # get the condition and the steps to run if the condition is true
        if_statement, condition, if_steps = statements_by_type['if']
        condition = ParseStep(condition)

        if if_steps is None:
            if_steps = []
        if isinstance(if_steps, basestring):
            if_steps = [if_steps]

        parsed_if_steps = []
        for step in if_steps:
            if step is None:
                continue
            parsed_if_steps.append(ParseStep(step))
        if_steps = parsed_if_steps

        # get the steps to run if the condition is false
        else_statement, else_data, else_steps = statements_by_type.get(
            'else', ('else', '', None))

        if else_steps is None:
            else_steps = []
        if isinstance(else_steps, basestring):
            else_steps = [else_steps]

        parsed_else_steps = []
        for step in else_steps:
            if step is None:
                continue
            parsed_else_steps.append(ParseStep(step))
        else_steps = parsed_else_steps

        if not if_steps + else_steps:
            raise RuntimeError("IF statement has no statements to run '%s'"% condition.raw_step)

        return IfStep(step, condition, if_steps, else_steps)

    elif 'for' in statements_by_type:
        raise NotImplementedError("For steps are not implemented yet")

    else:
        raise RuntimeError("Unknown Complex step type: '%s'"%
            statements_by_type.keys())


class Step(object):
    "Represent a generic step - should never actually be instantiated"

    def __init__(self, raw_step):
        self.raw_step = raw_step
        self.step_data = raw_step
        #self.referenced_variables = FindVariableReferences(self.raw_step)

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

        Note - we don't replace all sub variables at this point
        """
        #self.value = ReplaceExecutableSections(
        #    self.value, variables, execute = True)
        self.replace_vars(variables, update = True)

        # all we do at this point is to ensure that the variables
        # includes the current value.
        variables[self.name] = self

    def __repr__(self):
        return "'%s'"% self.value


class CommandStep(Step):
    "Any general command"

    def __init__(self, raw_step):
        Step.__init__(self, raw_step)
        self.qualifiers, self.step_data = self._parse_qualifiers()
        #self.output = None
        #self.ret = None

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced
        """
        new_val = ReplaceVariableReferences(self.step_data, variables)
        if update:
            self.step_data = new_val

    def _parse_qualifiers(self):
        "Find the qualifiers and replace them"
    
        qualifier_re = re.compile("""
            \{\*
            (?P<qualifier>[a-zA-Z]+)
            \*\}""", re.VERBOSE)
    
        qualifiers = qualifier_re.findall(self.step_data)
        parsed_step = qualifier_re.sub("", self.step_data)
        return qualifiers, parsed_step

    def command_as_string_for_log(self, params):
        "return the command as a string for logging"
        if isinstance(params, list):
            params = " ".join(params)

        def shorten_string(string, length = 100):
            if len(string) > length:
                string = string[:length-3] + "..."
            return string

        command_message = params

        if command_message != self.raw_step:
            command_message = "'%s' -> '%s'"% (
                shorten_string(self.raw_step),
                shorten_string(command_message))
        else:
            command_message = "'%s'"% (command_message)

        command_message = command_message.replace('\\', '\\\\')
        command_message = command_message.replace('\r\n', '\\r\\n')

        return command_message

    def execute(self, variables, raise_on_error = True):
        "Run this step"
        self.replace_vars(variables, update = True)

        #self.qualifiers, self.step_data = self._parse_qualifiers()

        # Check if the command in the mapping
        parts = SplitStatementAndData(self.step_data)

        cmd = parts[0].strip().lower()
        if cmd in built_in_commands.NAME_ACTION_MAPPING:
            func = built_in_commands.NAME_ACTION_MAPPING[cmd]
            params = parts[1]
        else:
            func = built_in_commands.SystemCommand
            params = self.step_data

        if cmd == "echo":
            self.qualifiers.append('echo')

        cmd_log_string = self.command_as_string_for_log(params)
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

        if 'echo' in self.qualifiers and indented_output != '\n':
            LOG.info(indented_output)

        elif indented_output != "\n":
            LOG.debug("Output from command:\n%s"% indented_output)


class IfStep(Step):
    "An IF block"

    def __init__(self, raw_step, condition, if_steps, else_steps):
        Step.__init__(self, raw_step)
        self.condition = condition
        self.if_steps = if_steps
        self.else_steps = else_steps

    def replace_vars(self, variables, update = False):
        """Replace variables referenced in the step with the variable values

        If update is False - then this will only test that the variables
        can be replaced
        """

        self.condition.replace_vars(variables, update = update)
        ReplaceVariablesInSteps(self.if_steps, variables, update = update)
        ReplaceVariablesInSteps(self.else_steps, variables, update = update)

    def execute(self, variables, raise_on_error = True):
        "Run this step"
        self.replace_vars(variables, update=True)

        LOG.debug("Testing Condition:")
        # check if the condition is true
        #try:
        self.condition.execute(variables, raise_on_error = False)
        if self.condition.ret  == 0:
            check_true = True
            LOG.debug("Condition evaluated to true: %s"% self.condition.output)
        #except RuntimeError, e:
        else:
            LOG.debug("Condition evaluated to false: %s"% self.condition.output)
            check_true = False

        # if it is - then execute true steps
        if check_true:
            for step in self.if_steps:
                step.execute(variables)
        else:
            for step in self.else_steps:
                step.execute(variables)

    def __repr__(self):
        return "<IF %s...>"% self.condition.raw_step

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
            self.message = parts[1]

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

        # ensure that it can be included

    def execute(self, variables, raise_on_error = True):
        "Run this step"
        self.replace_vars(variables, update = True)
        self.filename = os.path.join(
            variables['__script_dir__'].value, self.filename)

        # todo: should the __script_dir__ be updated to the include
        # directory? if yes- then don't forget to set it back afterwards
        # in a safe try finally!
        self.steps = LoadAndCheckFile(self.filename, variables)


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


STATEMENT_HANDLERS = {
    'set': VariableDefinition,
    'include': IncludeStep,
    'logfile': LogFileStep,
    #'if':   ,
    #'usage':   ,
    'end': ExecutionEndStep
    # 'for'
}
def LoadAndCheckFile(filepath, variables):
    steps = ParseYAMLFile(filepath)

    if not steps:
        return []

    if not isinstance(steps, list):
        raise RuntimeError(
            "Configuration file not correctly defined (remember to start each "
            "statement with '-')")

    parsed_steps = []
    errors = []
    for step in steps:
        try:
            parsed_steps.append(ParseStep(step))
            if isinstance(parsed_steps[-1] , IncludeStep):
                # note - because we load include steps before
                # executing other steps - we can only use variables defined outside
                # the script (either command line, environment vars or pseudo vars)
                include_step = parsed_steps.pop()
                include_step.execute(variables)
                parsed_steps.extend(include_step.steps)

        except ErrorCollection, e:
            errors.extend(e.errors)
        # todo: add a check for number of parameters

    try:
        ReplaceVariablesInSteps(parsed_steps, variables, update = False)
    except ErrorCollection, e:
        errors.extend(e.errors)

    if errors:
        raise ErrorCollection(errors)
    return parsed_steps


def ExecuteSteps(steps, variables):
    for step in steps:
        step.execute(variables)




def PopulateVariables(script_file):
    "Allow variables from the command line to be used also"
    variables = {}
    for var, val in os.environ.items():
        var = var.lower()
        variables[var] = ParseStep(
            "set %s=%s"%(var, val))

    variables.update({
        '__script_dir__':
            ParseStep('set __script_dir__ = %s'%
                os.path.abspath(os.path.dirname(script_file))),
        '__working_dir__':
            ParseStep('set __working_dir__ = %s'%
                os.path.abspath(os.getcwd()))})

    return variables


def ValidateArgumentCounts(steps, count_db):
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
    ""
    params = ConfigParser.RawConfigParser()


    try:
        if (
            not params.read(param_file) or
            not params.has_section('param_counts')):
                LOG.info(
                    "Param file does not exist or does "
                    "not contain [param_counts]")
                return {}

    except ConfigParser.ParsingError, e:
        LOG.warning(str(e))
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

    variables = PopulateVariables(options.script_file)

    LOG.debug("Environment:"% variables)

    try:
        steps = LoadAndCheckFile(options.script_file, variables)
    except ErrorCollection, e:
        e.LogErrors()
        sys.exit()

    arg_counts_db = ReadParamRestrictions(PARAM_FILE)
    try:
        ValidateArgumentCounts(steps, arg_counts_db)
    except ErrorCollection, e:
        e.LogErrors()
        sys.exit(1)
        

    try:
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


    sys.exit()

