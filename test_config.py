"Read a config file and execute commands from it"

import re
import yaml
import os
import logging
import built_in_commands
import cmd_line

# too few public methods   #pylint: disable-msg=R0903

def CreateLogger():
    "Create and set up the logger - returns the new logger"

    # allow the handler to  print everything - we will set the actual level
    # through the logger
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.INFO)

    # make the output format very simple
    basic_formatter = logging.Formatter("%(levelname)s - %(message)s")
    stdout_handler.setFormatter(basic_formatter)

    # set up the logger with handler and to output debug messages
    logger = logging.getLogger("config_expert")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_handler)
    return logger
LOG = CreateLogger()
cmd_line.LOG = LOG
built_in_commands.LOG = LOG


class ErrorCollection(RuntimeError):
    "Class used to track many errors "

    def __init__(self, errors):
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

    def __init__(self, variable, value, config_file):
        TypeError.__init__(
            self,
            (
                "Variable '%s' ('%s') is of type %s. Please "
                "surround it with single quotes e.g. '%s'")% (
                    variable, config_file, type(value).__name__, str(value)))


def ParseYAMLFile(yaml_file):
    """Parse a single YAML file

    Most of the work of this function is to convert various different errors
    into RuntimeErrors
    """
    try:

        f = open(yaml_file, "rb")
        # load the config file
        config_data = yaml.load(f.read())
        f.close()
        return config_data

    except IOError, e:
        raise RuntimeError(e)

    except yaml.parser.ScannerError, e:
        raise RuntimeError("%s - %s"% (yaml_file, e))

    except yaml.parser.ParserError, e:
        raise RuntimeError("%s - %s"% (yaml_file, e))


def LoadIncludes(includes, base_path):
    "Load each of the include files"

    if not includes:
        return {}, {}

    all_included_vars = {}
    all_included_cmds = {}
    errors = []
    # load each of the included config files
    for inc in includes:
        if not inc:
            continue
        LOG.debug("Parsing include: '%s'"% inc)
        inc = os.path.join(base_path, inc)
        try:
            inc_vars, inc_cmds = ParseConfigFile(inc)

            # Update the total included variables
            all_included_vars.update(inc_vars)
            all_included_cmds.update(inc_cmds)
        except ErrorCollection, e:
            errors.extend(e.errors)

    if errors:
        raise ErrorCollection(errors)

    return all_included_vars, all_included_cmds


def ParseVariableBlock(var_block, config_file):
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

    errors = []
    variables = {}
    for name, value in var_block.items():
        # wrap the variable
        if isinstance(value, (int, float, long)):
            errors.append(NumericVarNotAllowedError(name, value, config_file))
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


def ParseConfigFile(config_file):
    """Load the config files -return the variables and commands

    Recursively parse any included config files. Included files are parsed
    first so that data will be overridden by the including config file.
    """

    all_errors = []
    config_data = {}
    try:
        config_data = ParseYAMLFile(config_file)
    except RuntimeError, e:
        raise ErrorCollection([e])

    # file is empty - just return empty data
    if not config_data:
        return {}, {}

    # update the config data to have lower case keys
    # only for the root level (e.g. includes/variables/commands)
    config_data = dict([(k.lower(), v) for k, v in config_data.items()])

    # Parse the includes files first (so the including config file
    # can override items as necessary)
    variables = {}
    commands = {}
    includes = config_data.setdefault('includes', {})
    # load and parse all the data from the included files
    try:
        variables, commands = LoadIncludes(
            includes, os.path.dirname(config_file))
    except ErrorCollection, e:
        # don't raise errors yet - just collect the errors. If there are
        # errors - then we will raise all the errors before returning
        all_errors.extend(e.errors)

    config_vars = config_data.setdefault('variables', {})
    this_file_variables = ParseVariableBlock(config_vars, config_file)
    variables.update(this_file_variables)

    # we don't need this anymore
    del config_data['includes']

    # Now delete the variables from the config data - so that all we have
    # are the commands
    del config_data['variables']

    commands = {}

    # And the commands (everything else is a command)
    commands.update(config_data)

    if all_errors:
        raise ErrorCollection(all_errors)

    return variables, commands


def CalculateExternalVariable(variable):
    """If variable has (system) marking it as an external variable - calculate
    and return"""

    SYSTEM_VARIABLE = re.compile("^\s*\(\s*SYSTEM\s*\)\s*(?P<cmd>.*)$", re.I)

    # calculate any values
    system_variable = SYSTEM_VARIABLE.match(variable)
    if not system_variable:
        return variable

    LOG.debug("Calculating variable: %s"% repr(variable))

    # run the external command and grab it's output
    # this will raise an exception if the return is not 0 so we ignore
    # the return value here
    ret, out = built_in_commands.SystemCommand(
        system_variable.group('cmd'))

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


def ListCommands(commands):
    "Print out the available commands"
    LOG.info("Availale commands are:   ")
    for cmd in sorted(commands.keys()):
        LOG.info("  " + cmd)


def GetStepsForSelectedCommands(commands_info, requested_commands):
    "Execute the commands passed in"

    available_commands = commands_info.keys()

    # commands are in a comma separated list, so we split them,
    # make them case insesitive, and strip off any spaces
    requested_commands = [
        cmd.strip().lower() for cmd in requested_commands.split(",")]

    command_steps = []
    errors = []
    for cmd_requested in requested_commands:
        matched_cmd_names = []
        cmd_requested = cmd_requested.lower()

        for command in available_commands:
            # if it matches exactly then that is the command they want
            if cmd_requested.lower() == command:
                matched_cmd_names = [command]
                break

            # if it doesn't match exactly - we need to find all matching
            # commands
            elif command.lower().startswith(cmd_requested):
                matched_cmd_names.append(command)

        # the command requested matches more than one command
        if len(matched_cmd_names) > 1:
            errors.append(
                "Requested command '%s'is ambiguous it matches: %s"% (
                cmd_requested,
                ", ".join([str(cmd) for cmd in matched_cmd_names])))
            continue

        # it doesn't match any more command
        if not matched_cmd_names:
            errors.append(
                "Requested command '%s' not in available commands: %s"% (
                    cmd_requested,
                    ", ".join([str(cmd) for cmd in available_commands])))
            continue

        cmd_name = matched_cmd_names[0]
        command_steps.extend(commands_info[cmd_name])

    if errors:
        raise ErrorCollection(errors)

    return command_steps


def ParseStepData(step_data):
    "Given a single step - parse the data into individual bits"
    # default is RUN action - if no action given RUN will be assumed
    if isinstance(step_data, basestring):
        step_data = {'run': step_data}

    # ensure it is a dictionary with a single value
    if isinstance(step_data, dict):
        #ensure only a single value
        if len(step_data) != 1:
            raise RuntimeError(
                'Step must be in format "- ACTION: COMMAND_INFO" \'%s\''%
                    step_data)

        # get the action type, and parameters
        action_type, step_info = step_data.items()[0]
        action_type = action_type.lower()
    else:
        raise RuntimeError(
            'Step must be in format "- ACTION: COMMAND_INFO" \'%s\''%
                step_data)

    # split up the action_type - as it may have qualifiers:
    qualifiers = action_type.strip().split()

    # if there are qualifiers then the action type is the
    # first element, and the qualifiers are after that.
    if len(qualifiers) > 1:
        action_type = qualifiers[0]

    # remove the action type from the qualifiers
    del qualifiers[0]

    return action_type, qualifiers, step_info.strip()


class Step(object):
    "Represent a single step"

    def __init__(self, action_type, qualifiers, step_info):

        self.action_type = action_type
        self.qualifiers = qualifiers
        self.params = step_info

        if action_type not in built_in_commands.NAME_ACTION_MAPPING:
            raise RuntimeError("Unknown action type: '%s'"% action_type)

        self.action = built_in_commands.NAME_ACTION_MAPPING[action_type]

    def Execute(self):
        "Execute the step"

        LOG.debug("Executing step '%s': '%s'"% (
            self.action_type, self.params))
        ret, output = self.action(self.params, self.qualifiers)

        if ret:
            LOG.warning("Command returned non zero(%d) return value", ret)

        if output:
            indented_output = "\n".join(
                ["   " + line for line in output.split("\r\n")])

            LOG.debug("Output from command:\n%s"% indented_output)

        return ret, output


def SetupLogFile(variables):
    "Create the log file if it has been requested"

    if 'logfile' in variables:
        log_filename = ReplaceVariableReferences(
            variables['logfile'], variables)
        if os.path.exists(log_filename):
            os.unlink(log_filename)
        h = logging.FileHandler(log_filename)
        # make the output format very simple
        basic_formatter = logging.Formatter("%(levelname)s - %(message)s")
        h.setFormatter(basic_formatter)

        LOG.addHandler(h)


def Main():
    "Parse command line arguments, read config and dispatch the request(s)"

    options = cmd_line.GetValidatedOptions()

    # ensure that the keys are all treated case insensitively
    variables, commands = ParseConfigFile(options.config_file)

    SetupLogFile(variables)

    # get the variable overrides passed at the command line and
    # update the read variables from the overrides
    variables.update(options.variables)

    LOG.debug("Options: %s"% options)
    if options.list:
        ListCommands(commands)

    elif options.execute:

        errors = []
        executable_steps = []

        # Scan and construct all the steps first before trying to execute
        # any of them. This way - we can report errors before doing any
        # step execution
        steps = GetStepsForSelectedCommands(commands, options.execute)
        for step in steps:
            try:
                action, qualifiers, step_info = ParseStepData(step)
                step_info = ReplaceVarRefsInStructure(step_info, variables)
                executable_steps.append(Step(action, qualifiers, step_info))
            except ErrorCollection, e:
                errors.extend(e.errors)
                continue
            except RuntimeError, e:
                errors.append(e)
                continue

        # if there were errors - then raise them
        if errors:
            raise ErrorCollection(errors)

        # now execute each of the steps
        for cmd in executable_steps:
            cmd.Execute()


if __name__ == '__main__':
    #import cProfile
    #import pstats

    try:
        Main()
        #cProfile.run('Main()', "profile_stats")
        #p = pstats.Stats('profile_stats')
        #p.sort_stats('cumulative').print_stats(10)

    except ErrorCollection, err:
        err.LogErrors()
    except RuntimeError, err:
        LOG.critical(err)
    except Exception, err:
        LOG.critical('Unknown Error: %s'% err)
        LOG.exception(err)
