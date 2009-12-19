"Read a config file and execute commands from it"

# todo: work on logging
# Todo: remote Python Perl Extensions
# Todo: add unit tests!!!!

# todo - warn/fail for integers in variables

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


SYSTEM_MARKER = re.compile("^\s*\(\s*SYSTEM\s*\)\s*(.*)$", re.I)


def CreateLogger():
    "Create and set up the logger - returns the new logger"
    stdout_handler = logging.StreamHandler()
    # allow the handler to  print everything - we will set the actual level
    # through the logger
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
        err_messages = []
        for error in self.errors:
            if str(error) not in filtered:
                print "----", str(error)
                filtered.append(str(error))
        return filtered

    def __str__(self):
        return "\n".join([msg for msg in self.FilterDuplicateErrors()])
    

class ParseError(RuntimeError):
    def __init__(self, data):
        self.names = []
        self.data = data


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


class VariableMissingError(PreRequisiteError):
    "Class used to track errors when a used variable is is missing"
    def __init__(self, text_where_var_missing, missing_var):
        PreRequisiteError.__init__(self, text_where_var_missing)
        self.message = "Variable '%s' is not defined '%s''"% (
            missing_var, text_where_var_missing)


class NumericVarNotAllowedError(TypeError):
    """Class when a scalar type other than a string is found in the YAML

    Only strings are supported to ensure that values like 01, 0x409, are
    kept as strings - i.e. it will have the same textual representation"""

    def __init__(self, variable, value):
        self.msg = ("Variable '%s' is of type %s. Please "
                "surround it with single quotes e.g. '%s'")% (
                    variable, type(value).__name__, str(value))

    def __str__(self):
        return self.msg


class Variable(object):
    def __init__(self, name, value, file):
        self.name = name
        self.key = name.lower()
        self.value = value
        self.file = file
        
        if isinstance(value, (int, float, long)):
            raise NumericVarNotAllowedError(name, value)

    def resolve(self, variables):
            
        # replace any variables
        value, errors = ReplaceVariableReferences(self.value, variables)
        if errors:
            raise ErrorCollection(errors)
        
        # calculate any values
        if SYSTEM_MARKER.match(value):
            LOG.debug("Calculating variable: %s - %s"% (
                repr(self.key), repr(value)))

            # remove the system marker
            system_command = SYSTEM_MARKER.search(value).group(1)

            # run the external command and grab it's output
            ret, out = built_in_commands.SystemCommand(system_command)
            
            out.strip()

            if ret:
                raise RuntimeError("possible error setting variable from system command")
        
        return value

    def __repr__(self):
        return "<var:'%s'>"% (self.name)


class Variables(dict):
    def __init__(self, var_structure, file):
        
        if isinstance(var_structure, Variables):
            return var_structure
            
        errors = []
        for name, value in var_structure.items():
            # wrap the variable
            var = Variable(name, value, file)
            
            # check that we don't have two variables the same
            if var.key in self and self[var.key] != value:
                errors.append((
                    "Key already in structure but different values, Key: '%s'"
                    "\n\tVal1: '%s'"
                    "\n\tVal2: '%s'")% (name, self[var.key], value))
            else:
                self[var.key] = var
        
        if errors:
            raise ErrorCollection(errors)
    
    def update(self, other):
        assert(isinstance(other, Variables))
        dict.update(self, other)

    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())


def CaseInsenstitizeKeys(data):
    errors = []
    if isinstance(data, dict):
        new_dict = {}
        for key, val in data:
            
            # make sure that the value has case insensitive keys also
            new_val, val_errs = CaseInsenstitizeKeys(val)
            # even though there may be errors - we don't stop at this point
            # so that we can report as many issues as possible
            for e in val_errs:
                e.context.append(key)
                errors.append(e)

            if not val_errs:
                val = new_val
            
            new_key = iStr(key)
            if new_key in new_dict and val != new_dict[new_key]:
                e = ParseError("")
                errors.append()
            else:
                new_dict[new_key] = val
        data = new_dict
                
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_item, item_errs = CaseInsenstitizeKeys(item)
            
            new_item.extend(item_errs)
            
            if not item_errs:
                data[i] = new_item
            
    else:
        pass
    
    return data, item



def LoadConfigFile(config_file):
    """Load the config files -return the variables and commands

    Recursively parse any included config files. Included files are parsed
    first so that data will be overridden by the including config file.
    """
    all_errors = []
    LOG.debug("Parsing include: '%s'"% config_file)
    try:
        # load the config file
        f = open(config_file, "rb")
        config_data = yaml.load(f.read())
        f.close()

        # update the config data to have lower case keys
        # only for the root level (e.g. includes/variables/commands)
        config_data = dict([(k.lower(), v) for k, v in config_data.items()])
        
        variables = Variables({}, config_file)
        commands = {}

        # Parse the includes files
        if 'includes' in config_data and config_data['includes']:
            # load each of the included config files
            for inc in config_data['includes']:
                inc_vars, inc_cmds, errors = LoadConfigFile(inc)

                if not errors:
                    all_errors.extend(errors)

                variables.update(inc_vars)
                commands.update(inc_cmds)

            # we don't need this anymore
            del config_data['includes']

        # Now update the variables from this particular config file
        if 'variables' in config_data:
                
            variables.update(
                Variables(config_data['variables'], config_file))
            del config_data['variables']

        #all_errors.extend(CheckVariablesNonNumeric(variables))

        # And the commands (everything else is a command)
        commands.update(config_data)
        

        #print "---" * 20
        #print "CONF PARSING ERRS:", all_errors

        return variables, commands, all_errors

    except yaml.parser.ScannerError, e:
        LOG.fatal("%s - %s"% (config_file, e))
        sys.exit()
    except yaml.parser.ParserError, e:
        LOG.fatal("%s - %s"% (config_file, e))
        sys.exit()


def CalculateValues(variables):
    """Run through the variables and for any value that needs to be calculated
    Get it's value and run it."""

    # for each of the variables
    for key, value in variables.items():
        print value
        print value.resolve(variables)
        if SYSTEM_MARKER.match(value):
            LOG.debug("Calculate variable: %s - %s"% (repr(key), repr(value)))

            # remove the system marker
            system_command = SYSTEM_MARKER.search(value).group(1)

            ret, out = built_in_commands.SystemCommand(system_command)
            variables[key] = out.strip()

            if ret:
                print `ret`, out
                raise RuntimeError("possible error setting variable from system command")


def MakeKeysCaseInsensitive(key, value):
    "Make the key case insensitive"
    if key is not None:
        key = key.lower()
    return key, value, []


def ForEachKeyValue(structure, func):
    """Allow a function to be run on all key/value pairs

    For dictionaries both key and value are passed to func
    for Lists - we just interate the values
    for items - we pass just the value to func"""

    errors = []

    was_error = False

    # Handle different structure types differently
    if isinstance(structure, dict):

        # build up the new structure
        new_struct = {}
        # iterate over all the values in the dictionary
        for key, value in structure.items():

            # get new key, new value 
            new_key, new_value, func_errs = func(key, value)

            # if there were errors then stop
            if func_errs:
                return None, func_errs
            
            # use the new value
            value = new_value

            #  now iterate over all the value (as it may be a structure)
            new_value, func_errs = ForEachKeyValue(new_value, func)

            # if there were errors then stop
            if func_errs:
                return None, func_errs

            # again use the value if there were no errors
            value = new_value

            # before adding the item - check if it exists already
            if new_key in new_struct and new_value != new_struct[new_key]:
                errors.append((
                    "Key already in structure - have you specified the same "
                    "key but only differing in case, Key: '%s'"
                    "\n\tVal1: '%s'"
                    "\n\tVal2: '%s'")% (
                        new_key, new_value, new_struct[new_key]))

            else:
                new_struct[new_key] = new_value

        structure = new_struct

    elif isinstance(structure, list):
        # Similar to dicts above - iterate over the list
        # calling ourselves recursively for each element
        # and only updating the value if there were no errors
        # note - we don't call the func for the list as a whole but rather
        # it will be called for each of the individual items
        for i, value in enumerate(structure):
            new_val, func_errs = ForEachKeyValue(value, func)

            errors.extend(func_errs)
            if not func_errs:
                structure[i] = new_val
    else:
        # It is a value - we can replace the variable references directly
        new_key, new_val, func_errs = func(None, structure)

        errors.extend(func_errs)

        if not func_errs:
            structure = new_val

    # return the updated structure and any errors
    return structure, errors


def HandleCommandLine():
    config_file, options = cmd_line.ParseArguments()
    # ensure that the keys are all treated case insensitively
    variables, commands, errors = LoadConfigFile(config_file)

    if errors:
        for e in errors:
            LOG.fatal(e)
        sys.exit()

    #variables, erors = ForEachKeyValue(variables, MakeKeysCaseInsensitive)

    if errors:
        for e in errors:
            LOG.fatal(e)
        sys.exit()

    # get the variable overrides passed at the command line
    variable_overrides = {}
    errors = []
    variables.update(ParseVariableOverrides(options.variables))

    # update the read variables from the overrides
    #variables = OverrideVariables(variables, variable_overrides)

    # calculate any values that need to be processed
    # todo - don't do this yet!!
    #CalculateValues(variables)

    LOG.debug("Options: %s"% options)
    if options.execute:
        found_commands, errors = GetCommands(
            commands, options.execute, variables)

        if errors:
            for e in errors: 
                print e
            sys.exit()
        
        try:
            for cmd in found_commands:
                cmd.Execute()
        except ErrorCollection, e:
            print "xxxx" ,e
        
    elif options.list:
        ListCommands(variables, commands, args)
    #elif options.test:
    #    Test(variables, commands, args)
    elif options.validate:
        sys.exit()





def ParseVariableOverrides(variable_overrides):
    "Parse variable overrides passed on the command line"
    overrides = {}
    for override in variable_overrides:
        parsed = override.split("=")
        if len(parsed) != 2:
            raise RuntimeError("overrides need to be var=value: '%s'"% override)

        var, value = parsed
        var = var.strip()

        overrides[var] = value
    
    return Variables(overrides, 'PARAMETER')


def ReplaceVarRefsInStructure(structure, vars):
    "Replace all variable references in a structure"
    errors = []

    # Handle different structure types differently
    if isinstance(structure, dict):
        # check all the values in the dictionary
        for key, value in structure.items():

            # call this function recursively - as the value may itself
            # be a dictionary or a list
            new_val, sub_errors = ReplaceVarRefsInStructure(value, vars)

            # if there were errors
            if sub_errors:

                # update each of the errors with the current key
                # makes it easier to track down the particular instance
                for se in sub_errors:
                    se.names.append(key)
                errors.extend(sub_errors)
            else:
                # only update the value if there were no errrors
                # Even if there were errors new_val may have been partially
                # updated
                structure[key] = new_val

    elif isinstance(structure, list):
        # Similar to dicts above - iterate over the list
        # calling ourselves recursively for each element
        # and only updating the value if there were no errors
        for i, value in enumerate(structure):
            new_val, sub_errors = ReplaceVarRefsInStructure(value, vars)

            if sub_errors:
                errors.extend(sub_errors)
            else:
                structure[i] = new_val
    else:
        # It is a value - we can replace the variable references directly
        new_val, sub_errors = ReplaceVariableReferences(structure, vars)
        if sub_errors:
            errors.extend(sub_errors)
        else:
            structure = new_val

    # return the updated structure and any errors
    return structure, errors


VARIABLE_REFERENCE_RE = re.compile("\<([^\>\<]+)\>")
def ReplaceVariableReferences(item, vars):
    """Replace variable references like <VAR_NAME> with the variable value"""

    # If item is None just return
    # and there were no errors because we didn't do anything.
    if item is None or item == '':
        return item, []

    # Force that the YAML data only has string values - imagine
    # a float that can't be represented, instead of having 1.1 - you might end
    # up with 1.000000009 :(
    if isinstance(item, float):
        return None, [NumericVarNotAllowedError(item)]

    if not isinstance(item, basestring):
        return item, []


    # We need some way to allow > and < so the user doubles them when
    # they are not supposed to be around a variable reference.
    # Replacing them like this - makes finding the acutal variable references
    # much easier
    item = item.replace("<<", "{LT}")

    # We replace greater than >> a bit differently - because if there are an
    # odd number of greater than signs in a row we want to split from the end
    # not from the start
    item = "{GT}".join(item.rsplit(">>"))

    # find all the variable references
    found = VARIABLE_REFERENCE_RE.findall(item)

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
            errors.append(VariableMissingError(item, var))

    item = item.replace("{LT}", "<")
    item = item.replace("{GT}", ">")

    return item, errors


def ListCommands(variables, commands, args):
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

    matched_commands = []
    errors = []
    for cmd_requested in requested_commands:
        matched_cmd_names = []
        cmd_requested = cmd_requested.lower()

        for command in available_commands:
            # if it matches exactly then that is the command they want
            if cmd_requested == command:
                matched_cmd_names = [command]
                break
            
            # if it doesn't match exactly - we need to find all matching commands
            elif command.lower().startswith(cmd_requested):
                matched_cmd_names.append(command)

        # the command requested matches more than one command
        if len(matched_cmd_names) > 1:
            errors.append(
                "Requested command '%s'is ambiguous it matches: %s"% (
                cmd_requested,
                ", ".join([str(cmd) for cmd in matched_cmd_names])))
            return [], errors

        # it doesn't match any more command
        if not matched_cmd_names:
            errors.append(
                "Requested command '%s' not in available commands: %s"% (
                    cmd_requested, 
                    ", ".join([str(cmd) for cmd in available_commands])))
            return [], errors

        cmd_name = matched_cmd_names[0]
        command_steps = commands_info[cmd_name]
        
        try:
            matched_commands.append(
                Command(command_steps, cmd_name, variables))
        except ErrorCollection, e:
            errors.extend(e.errors)

    return matched_commands, errors


#def OverrideVariables(variables, overrides):
#    "We want to work with the variables case sensitively"
#
#    for ovr_key, ovr_value in overrides.items():
#        if ovr_key in variables:
#            print "INFO: Variable '%s', value '%s' overriden with value '%s'"% (
#                ovr_key, variables[ovr_key], ovr_value)

#        variables[ovr_key] = ovr_value

#    return variables


class Step(object):
    def __init__(self, action_type, params):
        # split up the action_type - as it may have qualifiers:
        qualifiers = action_type.strip().split()
        
        # if there are qualifiers then the action type is the 
        # first element, and the qualifiers are after that.
        if len(qualifiers) > 1:
            action_type = qualifiers[0]
            del qualifiers[0]
        
        action_type = action_type.lower()
        if action_type not in built_in_commands.NAME_ACTION_MAPPING:
            raise RuntimeError("Unknown action type: '%s'"% action_type)
        
        self.action_type = action_type
        self.action = built_in_commands.NAME_ACTION_MAPPING[action_type]
        self.qualifiers = qualifiers
        self.params = params

    def Execute(self):
        LOG.debug("Executing step '%s': '%s'"% (self.action_type, self.params))
        return self.action(self.params, self.qualifiers)


class Command(object):
    "Represent a command that can be run"

    def __init__(self, cmd_info, cmd_name, variables):
        self.cmd_info = cmd_info
        self.cmd_name = cmd_name

        self.ReplaceVars(variables)
        self.variables = variables

    def ReplaceVars(self, variables):
        updated_structure, errors = ReplaceVarRefsInStructure(
            self.cmd_info, variables)

        if errors:
            for error in errors:
                error.names.append(self.cmd_name)
            raise ErrorCollection(errors)
        else:
            self.cmd_info = updated_structure

    def Execute(self):
        "Run the command after checking pre-requisites"

        for item in self.cmd_info:
            if isinstance(item, basestring):
                item = {'run': item}
            if isinstance(item, dict):
                #ensure only a single value
                if len(item) != 1:
                    raise RuntimeError("Item must be action: command: '%s'"% item)
                
                # get the values
                step_type, step_info = item.items()[0]
                step_type = step_type.lower()
                
                step = Step(step_type, step_info)
                try:
                    step.Execute()
                except Exception, e:
                    print "sssssssssssssssssssssss", e

            else:
                raise RuntimeError(
                    "unknown type - use only strings or dictionaries")

            if step_type in built_in_commands.NAME_ACTION_MAPPING:
                step_function = built_in_commands.NAME_ACTION_MAPPING[step_type]
                LOG.debug("Executing step '%s': '%s'"% (step_type, step_info))
                
#                try:
#                    returned = step_function(step_info)
#                except RuntimeError, e:
#                    
#                    LOG.critical(e)
#                    return
#                    
#                if isinstance(returned , tuple):
#                    ret = returned[0]
#                    output = returned[1]
#                else:
#                    ret = returned
#                    output = ''
#
#                if ret:
#                    LOG.warning(
#                        "Command '%s' returned error code = %d\n%s"%
#                            (step_type, ret, output))
#
            #if step_type.lower == 'check':
            #    ret, output = SystemCommand(step_info)
            #    print output
            #    if ret:
            #        print "Possible error return!!"
            #        print output

#    def CheckPrerequisites(self):
#        "Run a check that the required files/folders exist"
#
#        # if there are no pre-requisites - then just return
#        if 'prechecks' not in self.cmd_info:
#            return
#
#        failed_prereqs = []
#        pre_reqs = self.cmd_info['prechecks']
#        for item in pre_reqs:
#            # if it is just a plain string then check that the file exists
#            if isinstance(item, basestring):
#                if SYSTEM_MARKER.match(item):
#                    # remove the system marker
#                    system_command = SYSTEM_MARKER.search(item).group(1)
#
#                    ret, out = SystemCommand(system_command)
#
#                    if ret != 0:
#                        failed_prereqs.append(
#                            FailedExternalCheck(command, ret, output))
#
#                elif not os.path.exists(os.path.normpath(item)):
#                    failed_prereqs.append(MissingFileDirError(item, item))
#
#            else:
#                raise RuntimeError("Should not have a list or dict within "
#                    "the pre-requisites")
#
#        if failed_prereqs:
#            raise ErrorCollection(failed_prereqs)
#
#def MakeKeysCaseInsensitive(structure):
#    if isinstance(structure, dict):
#        new_struct = dict()
#        # Make the keys of the dict case insensitive
#        for name, value in structure.items():
#            # check if the key already exists (i.e. - different in case only!
#            if name in new_struct:
#                if value != new_struct[name]:
#                    LOG.warn(("Warning - you have specified the value for %s "
#                        "more than once, with different values "
#                        "\n\t'%s'\n\t'%s')")%
#                            (str(name), str(value), str(new_struct[name])
#                        ))
#            else:
#                new_struct[iStr(name)] = MakeKeysCaseInsensitive(value)
#    elif isinstance(structure, list):
#        new_struct = list()
#        for list_item in structure:
#            new_struct.append(MakeKeysCaseInsensitive(list_item))
#    else:
#        new_struct = structure
#
#    return new_struct
#
#
#def ExecutePythonCode(python_code, variables = {}, allow_var_update = False):
#    "Execute Python code"
#    LOG.debug("PYTHON CODE:\n" + python_code)
#    try:
#        # execute the python code
#        # pass it a copy of the variables (becuase we don't want it updating
#        # anything
#        if not allow_var_update:
#            variables = variables.copy()
#        exec(python_code, variables)
#
#        return 0, '', ''
#
#    except Exception, e:
#        print "Exception in embedded Python code"
#        s = traceback.format_exc()
#        # get rid of the first 3 lines - as these are references to
#        # this file and the exec call
#        s = s.splitlines()
#        del s[0:3]
#        print "\n".join(s)
#        sys.exit()
#
#
#def ExecuteCode(code, extension, capture_output = False):
#    "Write the code to a temporary file and execute the file using the shell"
#
#    # create a temporary file which will store the code to run
#    temp_file, filename = tempfile.mkstemp(
#        prefix = "temp_code_", suffix = extension, text = True)
#
#    # write the code to it
#    os.write(temp_file, code)
#
#    # close the file
#    os.close(temp_file)
#
#    # execute the file via the shell
#    exec_return, output = SystemCommand(
#        filename, capture_output)
#
#    # delete the temporary code file file
#    os.unlink(filename)
#
#    return exec_return, output
#


#def ExecuteBatchScript(batch_code):
#    "Write batch_code to a temporary file and execute it"
#
#    #todo - tempfile.NamedTemporary or something like that
#    f = open(r"c:\_temp\temp_batch_code.bat", "w")
#    f.write(batch_code)
#    f.close()
#
#    return subprocess.call(
#        r"c:\_temp\temp_batch_code.bat",
#        shell = True,
#        cwd = os.getcwd())
#


def Test(variables, commands, args):
    "Perform some simple tests and exit"

    # check parsing a value with no vars
    assert ReplaceVariableReferences(
        "test string", []) == ("test string", [])
    assert ReplaceVariableReferences(
        ">>test string>>", []) == (">test string>", [])
    assert ReplaceVariableReferences(
        "<<test string<<" ,{}) == ("<test string<", [])
    assert ReplaceVariableReferences(
        "<<test string>>", {}) == ("<test string>", [])
    assert ReplaceVariableReferences(
        "<<<var>", {"var": "value"}) == ("<value", [])
    assert ReplaceVariableReferences(
        "<var>>>", {"var": "value"}) == ("value>", [])
    print("PASSED: No Errors")
    sys.exit()

    # check parsing a value with 1 var
    # check parsing a value which is only a variable reference
    # check that > and < work OK (begining, middle and end of the string)

if __name__ == '__main__':
    HandleCommandLine()

