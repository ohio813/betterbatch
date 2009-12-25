"Read a config file and execute commands from it"

# todo: work on logging

import re
import sys
import yaml
import os
import logging
from pprint import pprint
import built_in_commands
import cmd_line
# two problems:
# (a)
# Variables:
#  var1: <<var2>>
#  var2:
# even though <<var2>> is NOT a variable reference - it may get treated as one
# idea - delay resolving until the very last moment possible
#
# (b)
# Variables:
#  var1 = <<<var2>
#  var2 = <test>>
# after resolution it will look like <test>

# recursive definition var: <var>

#pylint: disable-msg=R0903


SYSTEM_VARIABLE = re.compile("^\s*\(\s*SYSTEM\s*\)\s*(?P<cmd>.*)$", re.I)


def CreateLogger():
    "Create and set up the logger - returns the new logger"

    # allow the handler to  print everything - we will set the actual level
    # through the logger
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.DEBUG)

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

    def FilterDuplicateErrors(self):
        "Remove duplicate error messages"

        filtered = []
        for error in self.errors:
            if str(error) not in filtered:
                filtered.append(str(error))
        return filtered

    def __str__(self):
        return "\n".join([msg for msg in self.FilterDuplicateErrors()])


class PreRequisiteError(object):
    "Error when a pre-requisite is missing"

    def __init__(self, item):
        self.names = []
        self.message = "'%s' - No information"% item

    def __str__(self):
        names_text = ''
        #if self.names:
        #    names_text = "%s: "% "->".join(reversed(self.names))

        return names_text + self.message

    def __eq__(self, other):
        if type(self) != type(other):
            return False

        return (
            self.names == other.names and
            self.message == other.message)


class UndefinedVariableError(PreRequisiteError):
    "Class used to track errors when a used variable is is missing"

    def __init__(self, text_where_var_missing, missing_var):
        PreRequisiteError.__init__(self, text_where_var_missing)
        self.message = "Undefined Variable '%s' '%s'"% (
            missing_var, text_where_var_missing)


class NumericVarNotAllowedError(TypeError):
    """Class when a scalar type other than a string is found in the YAML

    Only strings are supported to ensure that values like 01, 0x409, are
    kept as strings - i.e. it will have the same textual representation"""

    def __init__(self, variable, value, config_file):
        self.msg = ("Variable '%s' ('%s') is of type %s. Please "
                "surround it with single quotes e.g. '%s'")% (
                    variable, config_file, type(value).__name__, str(value))

    def __str__(self):
        return self.msg


class Variable(object):
    "Represents a single variable definition"

    def __init__(self, name, value, config_file):
        self.name = name
        self.key = name.lower()
        self.value = value
        self.file = config_file

        if isinstance(value, (int, float, long)):
            raise NumericVarNotAllowedError(name, value, config_file)

    def resolve(self, variables):
        """Fully resolve the variable

        If the variable has variables then they will be replaced
        If the variable is a 'system' variable then the command will be run
        and the output retrieved."""


        # replace any variables
        value = ReplaceVariableReferences(self.value, variables)

        # calculate any values
        system_variable = SYSTEM_VARIABLE.match(value)
        if system_variable:
            LOG.debug("Calculating variable: %s - %s"% (
                repr(self.key), repr(value)))

            # run the external command and grab it's output
            ret, out = built_in_commands.SystemCommand(
                system_variable.group('cmd'))

            if ret:
                raise RuntimeError(
                    "possible error setting variable from system command")

            # remove any extra spaces that may have been present
            value = out.strip()

        return value

    def __repr__(self):
        return "<var:'%s'>"% (self.name)


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

            # Update the total included vars
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
        [temp.update(v) for v in var_block]

        # replace the existing block with the improved data
        var_block = temp

    all_errors = []
    this_file_variables = {}
    for name, value in var_block.items():
        # wrap the variable
        try:
            var = Variable(name, value, config_file)
        except NumericVarNotAllowedError, e:
            all_errors.append(e)
            continue

        # check that we don't have two variables the same
        if (name.lower() in this_file_variables and
            this_file_variables[name.lower()] != value):
            all_errors.append((
                "Key already defined with different value, Key: '%s'"
                "\n\tVal1: '%s'"
                "\n\tVal2: '%s'")% (
                    name, this_file_variables[name.lower()], value))
        else:
            this_file_variables[name.lower()] = var

    if all_errors:
        raise ErrorCollection(all_errors)

    return this_file_variables


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


def ParseVariableOverrides(variable_overrides):
    "Parse variable overrides passed on the command line"
    overrides = {}
    for override in variable_overrides:
        parsed = override.split("=")
        if len(parsed) != 2:
            raise RuntimeError(
                "overrides need to be var=value: '%s'"% override)

        var, value = parsed
        var = var.strip()


        overrides[var.lower()] = Variable(var, value, "SCRIPT ARG")

    return overrides


def ReplaceVarRefsInStructure(structure, vars):
    "Replace all variable references in a structure"

    # Handle different structure types differently
    if isinstance(structure, dict):
        # check all the values in the dictionary
        for key, value in structure.items():
            # call this function recursively - as the value may itself
            # be a dictionary or a list
            new_val = ReplaceVarRefsInStructure(value, vars)
            structure[key] = new_val

    elif isinstance(structure, list):
        # Similar to dicts above - iterate over the list
        # calling ourselves recursively for each element
        # and only updating the value if there were no errors
        for i, value in enumerate(structure):
            new_val = ReplaceVarRefsInStructure(value, vars)
            structure[i] = new_val
    else:
        # It is a value - we can replace the variable references directly
        new_val = ReplaceVariableReferences(structure, vars)
        structure = new_val

    # return the updated structure and any errors
    return structure


def ReplaceVariableReferences(item, vars):
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
    # for each of the variables we found
    for var in found:
        var_name_lower = var.lower()
        if var_name_lower in vars and vars[var_name_lower]:
            # get the text to replace it with (replacing any references in
            # the replacement text first
            # This is the best time to replace the references in the variable
            # as we only replace the ones we use
            try:
                replace_with = vars[var_name_lower].resolve(vars)
                item = item.replace("<%s>"%(var), replace_with)
            except ErrorCollection, e:
                errors.extend(e.errors)

            #replace_with, sub_errors = ReplaceVariableReferences(
            #    vars[var_name_lower], vars)
            #errors.extend(sub_errors)
            #if not sub_errors:

        else:
            errors.append(UndefinedVariableError(item, var))

    # if there have been errors - then raise then
    if errors:
        raise ErrorCollection(errors)

    item = item.replace("{LT}", "<")
    item = item.replace("{GT}", ">")

    return item


def ListCommands(commands):
    "Print out the available commands"
    print "Availale commands are:   "
    for cmd in sorted(commands.keys()):
        print "  ", cmd


def GetCommands(commands_info, requested_commands, variables):
    "Execute the commands passed in"

    available_commands = commands_info.keys()

    # commands are in a comma separated list, so we split them,
    # make them case insesitive, and strip off any spaces
    requested_commands = [
        cmd.strip().lower() for cmd in requested_commands.split(",")]

    steps_to_run = []
    errors = []
    for cmd_requested in requested_commands:
        matched_cmd_names = []
        cmd_requested = cmd_requested.lower()

        for command in available_commands:
            # if it matches exactly then that is the command they want
            if cmd_requested == command:
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
        command_steps = commands_info[cmd_name]
        
        for step_data in command_steps:
            #try:                    
            steps_to_run.append(Step(step_data, variables))
            #except RuntimeError, e:
            #    errors.extend(e)

    if errors:
        raise ErrorCollection(errors)

    return steps_to_run


class Step(object):
    "Represent a single step"

    def __init__(self, step_data, variables):
        
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

        step_info = ReplaceVarRefsInStructure(step_info, variables)

        if action_type not in built_in_commands.NAME_ACTION_MAPPING:
            raise RuntimeError("Unknown action type: '%s'"% action_type)

        self.action_type = action_type
        self.action = built_in_commands.NAME_ACTION_MAPPING[action_type]
        self.qualifiers = qualifiers
        self.params = step_info

    def Execute(self):
        "Execute the step"
        
        LOG.debug("Executing step '%s': '%s'"% (self.action_type, self.params))
        ret, output = self.action(self.params, self.qualifiers)

        if output:
            indented_output = "\n".join(
                ["   " + line for line in output.split("\r\n")])
            
            LOG.debug("Output from command:\n%s"% indented_output)
        return ret, output


class BatchSteps(object):
    "Represent a set of steps"

    def __init__(self, cmd_info, cmd_name, variables):
        self.cmd_info = cmd_info
        self.cmd_name = cmd_name

        self.ReplaceVars(variables)
        self.variables = variables

    def ReplaceVars(self, variables):
        "Replace the vars in all steps"
        pprint(self.cmd_info)
        updated_structure = ReplaceVarRefsInStructure(
            self.cmd_info, variables)

        #if errors:
        #    for error in errors:
        #        error.names.append(self.cmd_name)
        #    raise ErrorCollection(errors)
        #else:
        self.cmd_info = updated_structure

    def Execute(self):
        "Run the command after checking pre-requisites"

        for item in self.cmd_info:
            if isinstance(item, basestring):
                item = {'run': item}
            if isinstance(item, dict):
                #ensure only a single value
                if len(item) != 1:
                    raise RuntimeError(
                        "Item must be action: command: '%s'"% item)

                # get the values
                step_type, step_info = item.items()[0]
                step_type = step_type.lower()

                step = Step(step_type, step_info)
                try:
                    ret, output = step.Execute()
                    LOG.debug(output)
                except Exception, e:
                    LOG.exception(e)
                    raise
                
                if ret != 0:
                    LOG.critical("Non Zero error return")
                    raise RuntimeError("Non Zero return value")
                    

            else:
                raise RuntimeError(
                    "unknown type - use only strings or dictionaries")


def Main():
    "Parse command line arguments, read config and dispatch the request(s)"

    config_file, options = cmd_line.ParseArguments()

    try:
        # ensure that the keys are all treated case insensitively
        variables, commands = ParseConfigFile(config_file)
    except ErrorCollection, e:
        for err in sorted(e.errors):
            LOG.fatal(err)
        sys.exit()

    if 'logfile' in variables:
        log_filename = variables['logfile'].resolve(variables)
        if os.path.exists(log_filename):
            os.unlink(log_filename)
        h = logging.FileHandler(log_filename)
        # make the output format very simple
        basic_formatter = logging.Formatter("%(levelname)s - %(message)s")
        h.setFormatter(basic_formatter)
        
        LOG.addHandler(h)
        
    # get the variable overrides passed at the command line and
    # update the read variables from the overrides
    variables.update(ParseVariableOverrides(options.variables))

    errors = []

    LOG.debug("Options: %s"% options)
    if options.execute:
        try:
            executable_steps = GetCommands(
                commands, options.execute, variables)
        except ErrorCollection, e:
            for err in e.errors:
                LOG.fatal(err)
            sys.exit()

        try:
            for cmd in executable_steps:
                cmd.Execute()
        except ErrorCollection, e:
            for err in e.errors:
                LOG.fatal(err)
        except RuntimeError, e:
            LOG.fatal(e)

    elif options.list:
        ListCommands(commands)
    #elif options.test:
    #    Test(variables, commands, args)
    elif options.validate:
        sys.exit()


if __name__ == '__main__':
    Main()
