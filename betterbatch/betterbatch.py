"Read a betterbatch script file and execute commands from it"

import os
import sys
import re
import logging
import shlex
import ConfigParser

import yaml

import built_in_commands
import cmd_line

# too few public methods   #pylint: disable-msg=R0903

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
cmd_line.LOG = LOG
built_in_commands.LOG = LOG

PARAM_FILE = os.path.join(os.path.dirname(__file__), "param_counts.ini")


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


class UndefinedVariableError(RuntimeError):
    "Error raised when a variable is used that has not been defined"

    def __init__(self, variable, string):
        RuntimeError.__init__(
            self, "Undefined Variable '%s' '%s'"% (variable, string))

        self.variable = variable
        self.string = string


class NumericVarNotAllowedError(TypeError):
    """Class when a scalar type other than a string is found in the YAML

    Only strings are supported to ensure that values like 01, 0x409, are
    kept as strings - i.e. it will have the same textual representation"""

    def __init__(self, variable, value, script_file):
        TypeError.__init__(
            self,
            (
                "Variable '%s' ('%s') is of type %s. Please "
                "surround it with single quotes e.g. '%s'")% (
                    variable, script_file, type(value).__name__, str(value)))


def ParseVariableBlock(var_block, script_file):
    "Parse the variable block and return the variables"

    # if there are no variables
    if not var_block:
        return {}

    # if the variables have been defined as a list - then fix the block by
    # converting it to a dictionary
    elif isinstance(var_block, list):
        temp = {}
        for v in var_block:
            # if the variable isn't "key: value" then raise an error
            if isinstance(v, basestring):
                raise RuntimeError(
                    "Variable not defined correctly: '%s'"% v)

        # get the single item dict from each of the array items and update
        # the variables
        for v in var_block:
            temp.update(v)

        # replace the existing block with the improved data
        var_block = temp

    elif isinstance(var_block, basestring):
        raise RuntimeError(
            "Variables not defined correctly: '%s'"% var_block)

    errors = []
    variables = {}
    for name, value in var_block.items():
        # wrap the variable
        if isinstance(value, (int, float, long)):
            errors.append(NumericVarNotAllowedError(name, value, script_file))
            continue

        # check that we don't have two variables the same
        if (name.lower() in variables and
            variables[name.lower()] != value):
            errors.append((
                "Key already defined with different value, Key: '%s'"
                "\n\tVal1: '%s'"
                "\n\tVal2: '%s'")% (
                    name, variables[name.lower()], value))
        else:
            variables[name.lower()] = value

    if errors:
        raise ErrorCollection(errors)

    return variables


def ParseScriptFile(script_file, variables = None):
    """Load the script file and return the variables and commands

    Recursively parse any included script files. Included files are parsed
    first so that data will be overridden by the including script file.
    """

    all_errors = []
    script_data = {}
    if variables is None:
        variables = {}

    try:
        script_data = ParseYAMLFile(script_file)
    except RuntimeError, e:
        raise ErrorCollection([e])

    # file is empty - just return empty data
    if not script_data:
        return {}

    # update the script data to have lower case keys
    # only for the root level (e.g. includes/variables/commands)
    script_data = dict([(k.lower(), v) for k, v in script_data.items()])

    # Parse the includes files first (so the including script file
    # can override items as necessary)
    commands = {}
    includes = script_data.setdefault('includes', {})
    includes = ReplaceVarRefsInStructure(includes, variables)
    # load and parse all the data from the included files
    try:
        commands = LoadIncludes(
            includes, os.path.dirname(script_file), variables)
    except ErrorCollection, e:
        # don't raise errors yet - just collect the errors. If there are
        # errors - then we will raise all the errors before returning
        all_errors.extend(e.errors)

    script_vars = script_data.setdefault('variables', {})
    this_file_variables = ParseVariableBlock(script_vars, script_file)
    variables.update(this_file_variables)

    # we don't need this anymore
    del script_data['includes']

    # Now delete the variables from the script data - so that all we have
    # are the commands
    del script_data['variables']

    commands = {}

    # And the commands (everything else is a command)
    commands.update(script_data)

    if all_errors:
        raise ErrorCollection(all_errors)

    return commands


def CalculateExternalVariable(variable_value):
    """If variable has (system) marking it as an external variable - calculate
    and return"""

    EXTERNAL_VARIABLE = re.compile(
        """
            ^\s*
            \(
                \s*
                (?P<tool_name>[^ )]+)
                \s*
            \)
            \s*
            (?P<cmd_and_args>.*)
            $""", re.VERBOSE|re.DOTALL)

    # See if it matches the external variable pattern
    system_variable = EXTERNAL_VARIABLE.match(variable_value)

    # if it doesn't match return the value unchanged
    if not system_variable:
        return variable_value

    # ensure that the tool exists
    tool = system_variable.group('tool_name')
    if tool.lower() not in built_in_commands.NAME_ACTION_MAPPING:
        LOG.warning((
            "variable '%s' looks like an external call - i.e. '(TOOL) cmd' - "
            "but '%s' does not match any tools")% (tool, variable_value))
        return variable_value

    LOG.debug("Calculating variable: %s"% repr(variable_value))

    # run the external command and grab it's output
    # this will raise an exception if the return is not 0 so we ignore
    # the return value here
    action = built_in_commands.NAME_ACTION_MAPPING[tool.lower()]
    ret, out = action(system_variable.group('cmd_and_args'))

    if ret:
        raise RuntimeError("%d - %s"% (ret, out))

    # remove any extra spaces that may have been present
    return out.strip()


def ReplaceVarRefsInStructure(structure, variables):
    "Replace all variable references in a structure"

    errors = []
    # Handle different structure types differently
    if isinstance(structure, dict):
        # check all the values in the dictionary
        for key, value in structure.items():
            # call this function recursively - as the value may itself
            # be a dictionary or a list
            try:
                new_val = ReplaceVarRefsInStructure(value, variables)
                structure[key] = new_val
            except ErrorCollection, e:
                errors.extend(e.errors)

    elif isinstance(structure, list):
        # Similar to dicts above - iterate over the list
        # calling ourselves recursively for each element
        # and only updating the value if there were no errors
        for i, value in enumerate(structure):
            try:
                new_val = ReplaceVarRefsInStructure(value, variables)
                structure[i] = new_val
            except ErrorCollection, e:
                errors.extend(e.errors)
    else:
        # It is a value - we can replace the variable references directly
        new_val = ReplaceVariableReferences(structure, variables)
        structure = new_val

    if errors:
        raise ErrorCollection(errors)

    # return the updated structure and any errors
    return structure


def ReplaceVariableReferences(item, variables):
    """Replace variable references like <VAR_NAME> with the variable value"""

    # If item is None just return
    # and there were no errors because we didn't do anything.
    if item is None or item == '':
        return item

    # Force that the YAML data only has string values - imagine
    # a float that can't be represented, instead of having 1.1 - you might end
    # up with 1.000000009 :(
    if isinstance(item, (int, long, float)):
        raise NumericVarNotAllowedError('', item, '')

    # the item is not a base string - just return it
    if not isinstance(item, basestring):
        return item

    orig_string = item
    # We need some way to allow > and < so the user doubles them when
    # they are not supposed to be around a variable reference.
    # Replacing them like this - makes finding the acutal variable references
    # much easier
    item = item.replace("<<", "{LT}")

    # We replace greater than >> a bit differently - because if there are an
    # odd number of greater than signs in a row we want to split from the end
    # not from the start
    item = "{GT}".join(item.rsplit(">>"))

    variable_reference_re = re.compile("\<([^\>\<]+)\>")
    # find all the variable references
    found = variable_reference_re.findall(item)

    errors = []
    # for each of the refernece variables in this variable
    for var in found:
        var_name_lower = var.lower()
        if var_name_lower in variables and variables[var_name_lower]:
            # get the text to replace it with (replacing any references in
            # the replacement text first
            # This is the best time to replace the references in the variable
            # as we only replace the ones we use
            try:
                replace_with = ReplaceVariableReferences(
                    variables[var_name_lower], variables)

                item = item.replace("<%s>"%(var), replace_with)

            except ErrorCollection, e:
                errors.extend(e.errors)
            except RuntimeError, e:
                errors.append(e)

        else:
            errors.append(UndefinedVariableError(var, orig_string))

    # check for any mismatched brackets
    no_brackets = variable_reference_re.sub("", item)
    if ">" in no_brackets or "<" in no_brackets:
        errors.append("Mismatched angle brackets in '%s'"% (orig_string))

    item = item.replace("{LT}", "<")
    item = item.replace("{GT}", ">")

    try:
        item = CalculateExternalVariable(item)
    except RuntimeError, e:
        errors.append(e)

    # if there have been errors - then raise then
    if errors:
        raise ErrorCollection(errors)

    return item


def ParseStepData(step_data):
    "Given a single step - parse the data into individual bits"
    # default is RUN action - if no action given RUN will be assumed
    if isinstance(step_data, type(None)):
        return 'run', [], ''

    if isinstance(step_data, basestring):
        step_data = {'run': step_data}

    # ensure it is a dictionary with a single value
    if not isinstance(step_data, dict):
        raise RuntimeError(
            'Step must be in format "- ACTION: COMMAND_INFO" \'%s\''%
                step_data)

    #ensure only a single value
    if len(step_data) != 1:
        raise RuntimeError(
            'Step must be in format "- ACTION: COMMAND_INFO" \'%s\''%
                step_data)

    # get the action type, and parameters
    action_type, step_info = step_data.items()[0]

    action_type = action_type.lower()

    # split up the action_type - as it may have qualifiers:
    qualifiers = action_type.strip().split()

    # if there are qualifiers then the action type is the
    # first element, and the qualifiers are after that.
    if len(qualifiers) > 1:
        action_type = qualifiers[0]

    # remove the action type from the qualifiers
    del qualifiers[0]

    # remove any newlines or spaces at the ends
    if isinstance(step_info, basestring):
        step_info = step_info.strip()

    return action_type, qualifiers, step_info


class Step(object):
    "Represent a single step"

    def __init__(self, action_type, qualifiers, step_info):

        self.action_type = action_type
        self.qualifiers = qualifiers

        if isinstance(step_info, list):
            self.params = step_info

        elif isinstance(step_info, basestring):
            self.params = step_info

        elif action_type != "if":
            raise RuntimeError("Mapping type used for non if step")

        # check if the command is one of the commands that change the 
        # environment in some way and have to be overridden
        if (action_type == "run" and
            self.command.lower() in built_in_commands.DOS_REPLACE):

            self.action_type = self.command.lower()

            # Now remove the option from the commands
            if isinstance(self.params, list):
                # Because it's a list we need to remove the command from the
                # first argument (and if it is then empty - remove the first
                # item of the list
                first_param = self.params[0].strip()[len(self.command) + 1:]
                if first_param:
                    self.params[0] = first_param
                else:
                    del self.params[0]
            if isinstance(self.params, basestring):
                # strings are easier - just remove the command and it's 
                # trailing space
                self.params = self.params.strip()[len(self.command) + 1:]

        # Assign the correct action to be run
        if action_type in ('if', 'output'):
            # 'if' or 'output' actions don't really have actions
            self.action = None
        elif self.action_type in built_in_commands.NAME_ACTION_MAPPING:
            # It's a known action
            self.action = built_in_commands.NAME_ACTION_MAPPING[self.action_type]
        else:
            raise RuntimeError("Unknown action type: '%s'"% action_type)

    def Execute(self):
        "Execute the step"

        if self.action_type == "output":
            LOG.info(self.params)
            return 0, self.params

        if self.command.lower() == 'echo':
            message = self.arg_string.strip()[5:]
            LOG.info(message)
            return 0, message

        LOG.debug("Executing step '%s': '%s'"% (
            self.action_type, self.params))
        try:
            ret, output = self.action(
                self.params, self.qualifiers)
        except KeyboardInterrupt:
            LOG.error(
                "Step interrupted - Terminate execution? [Y/n]")
            ans = raw_input()
            if ans.lower().startswith("y") or ans == "":
                raise RuntimeError("Script Cancelled")
            else:
                return

        output = "\n".join(["   " + line for line in output.split("\r\n")])
        message = (
            'Non zero return (%d) from command:\n  "%s: %s"\nOUTPUT:\n%s'%(
                ret, self.action_type, self.params, output))

        #if ret:
        #    if 'nocheck' not in self.qualifiers and ret:
        #        raise RuntimeError(message)
        #    else:
        #        LOG.debug(message)

        # Ensure the output is printed if 'echo' was in the qualifiers
        output_func = LOG.debug
        if 'echo' in self.qualifiers:
            output_func = LOG.info

        if output:
            indented_output = "\n".join(
                ["   " + line for line in output.split("\r\n")])

            output_func("Output from command:\n%s"% indented_output)

        return ret, output


    @property
    def command_parts(self):
        if isinstance(self.params, list):
            parts = self.params
        else:
            try:
                parts = shlex.split(self.params)
            except ValueError:
                LOG.info(
                    "The command '%s' is not a valid shell command"%
                        self.params)
                # it is not a valid shell command - so just use a normal split
                parts = self.params.split()
        return parts

    @property
    def arg_string(self):
        if isinstance(self.params, list):
            arg_str = " ".join(self.params)
        else:
            arg_str = self.params.strip()
        return arg_str

    @property
    def command(self):
        if self.action_type == 'run':
            parts = self.command_parts

            if not parts:
                cmd_name = ""
            else:
                cmd_name = parts[0]

            # if there is a path - strip it off
            cmd_name = os.path.basename(cmd_name)

        else:
            cmd_name = self.action_type

        return cmd_name

    @property
    def argcount(self):
        # get the parts of the command as a list
        count = len(self.command_parts)

        # if it is a 'run' action then the params contains the command
        # to run - so don't count that as an argument
        if self.action_type == 'run':
            count -= 1

        return count

    def __repr__(self):
        return "<Step: %s %s>"% (self.action_type, " ".join(self.qualifiers))


class IfStep(Step):
    "Represent an if: block"

    def __init__(self, action_type, qualifiers, step_info):
        # ensure that step_info is a list and that there are at least 2
        # items in the list
        Step.__init__(self, action_type, qualifiers, step_info)

        if not isinstance(step_info, list):
            raise RuntimeError("IF step details must be a list")

        if len(step_info) < 2:
            raise RuntimeError("There must be at least 2 parts in an IF step")

        if len(step_info) > 3:
            raise RuntimeError(
                "There cannot be more than 3 parts in an IF step")

        # validate the "do" part
        if not (
            isinstance(step_info[1], dict) and
            len(step_info[1]) == 1 and
            step_info[1].keys()[0].lower() == "do"):

            raise RuntimeError(
                "The DO part of the if block is not defined correctly")

        do_block = step_info[1].values()[0]

        else_block = []
        if len(step_info) > 2:
            if not (
                isinstance(step_info[2], dict) and
                len(step_info[2]) == 1 and
                step_info[2].keys()[0].lower() == "else"):

                raise RuntimeError(
                    "The ELSE part of the if block is not defined correctly")
            else_block = step_info[2].values()[0]

        self.check = Step(*ParseStepData(step_info[0]))
        self.if_true_steps = BuildExecutableSteps(do_block, {})
        self.if_false_steps = BuildExecutableSteps(else_block, {})


    def Execute(self):
        """Run the 'if' step

        Check the condition, then execute the appropriate steps
        """
        full_output = []

        # check if the test works or fails
        check_passed = True
        try:
            ret, out = self.check.Execute()
            if ret:
                LOG.debug("'IF' condition evaluated to FALSE: '%s'"% out)
                check_passed = False
        except RuntimeError, e:
            check_passed = False
            LOG.warning("If Check raised an exception: %s"% str(e))

        if check_passed:

            for step in self.if_true_steps:
                ret, out = step.Execute()
                full_output.append(out)
        else:
            for step in self.if_false_steps:
                ret, out = step.Execute()
                full_output.append(out)

        return 0, "\n".join(full_output)


def SetupLogFile(variables):
    "Create the log file if it has been requested"

    if 'logfile' in variables:

        log_filename = ReplaceVariableReferences(
            variables['logfile'], variables)

        if os.path.exists(log_filename):
            for h in LOG.handlers:
                if (
                    hasattr(h, 'baseFilename') and
                    h.baseFilename.lower() ==
                        os.path.abspath(log_filename).lower()):

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


def PopulateVariablesFromEnvironment():
    "Allow variables from the command line to be used also"
    variables = {}
    for var, val in os.environ.items():
        variables[var.lower()] = val

    return variables


def ValidateArgumentCounts(steps, count_db):
    # get the name of the command
    errors = []
    for step in steps:
        command = step.command.lower()

        # See if it is in the DB
        if command in count_db:

            # If it is then get the count of it's parameters
            arg_count = step.argcount

            lower, upper = count_db[command]

            # check that is it appropriate
            if not lower <= arg_count <= upper:
                print arg_count, step, step.params
                    
                errors.append(RuntimeError((
                    "Invalid number of parameters '%d'. "
                    "Expected %d to %s. Command:\n\t%s: %s")% (
                        arg_count,
                        lower,
                        count_db[command][1],
                        step.action_type,
                        step.params)))

    if errors:
        raise ErrorCollection(errors)


def BuildExecutableSteps(steps, variables):
    "Parse the step data into a list of steps ready to execute"
    executable_steps = []
    errors = []

    if isinstance(steps, basestring):
        steps = [steps]

    for step in steps:
        try:
            action, qualifiers, step_info = ParseStepData(step)
            step_info = ReplaceVarRefsInStructure(step_info, variables)

            step_class = Step
            if action == "if":
                step_class = IfStep

            executable_step = step_class(action, qualifiers, step_info)
            executable_steps.append(executable_step)

        except ErrorCollection, e:
            errors.extend(e.errors)
            continue
        except RuntimeError, e:
            errors.append(e)
            continue

    # if there were errors - then raise them
    if errors:
        raise ErrorCollection(errors)

    return executable_steps


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

    variables = PopulateVariablesFromEnvironment()
    # ensure that the keys are all treated case insensitively
    commands = ParseScriptFile(
        options.script_file, variables)

    # set the default path to where the script file is
    script_dir = os.path.dirname(os.path.abspath(options.script_file))
    os.chdir(script_dir)

    SetupLogFile(variables)

    # get the variable overrides passed at the command line and
    # update the read variables from the overrides
    variables.update(options.variables)

    LOG.debug("Options: %s"% options)

    if len(commands) > 1:
        raise RuntimeError("More than one executable block not supported")
    elif not(commands):
        return

    # Scan and construct all the steps first before trying to execute
    # any of them. This way - we can report errors before doing any
    # step execution
    steps = commands.values()[0]
    executable_steps = BuildExecutableSteps(steps, variables)

    arg_counts_db = ReadParamRestrictions(PARAM_FILE)
    #ValidateArgumentCounts(executable_steps, arg_counts_db)

    # now execute each of the steps
    for cmd in executable_steps:
        ret, out = cmd.Execute()
        if ret:
            raise RuntimeError("STOPPING %s %s"%( ret, out))



if __name__ == '__main__':
    #import cProfile
    #import pstats

    try:
        Main()
        #cProfile.run('Main()', "profile_stats")
        #p = pstats.Stats('profile_stats')
        #p.sort_stats('cumulative').print_stats(10)
        sys.exit(0)
    except ErrorCollection, err:
        err.LogErrors()
    except RuntimeError, err:
        LOG.critical(err)
    except Exception, err:
        LOG.critical('Unknown Error: %s'% err)
        LOG.exception(err)
    finally:
        logging.shutdown()

    sys.exit(1)
