"Read a config file and execute commands from it"

# todo: work on logging
# Todo: remote Python Perl Extensions
# Todo: add unit tests!!!!

import re
import sys
import yaml
import optparse
import os
from iStr import iStr
import subprocess
import logging
import tempfile
from pprint import pprint

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


class PreRequisiteErrorCollection(RuntimeError):
    "Class used to track errors when a used variable is is missing"
    def __init__(self, errors):
        self.errors = errors

    def FilterDuplicateErrors(self):
        filtered = []
        for error in self.errors:
            if error not in filtered:
                filtered.append(error)
        return filtered

    def __str__(self):
        return "\n".join([str(e) for e in self.FilterDuplicateErrors()])


class PreRequisiteError(object):
    "Error when a pre-requisite is missing"
    def __init__(self, item):
        self.names = []
        self.message = "'%s' - No information"% item

    def __str__(self):
        names_text = ''
        if self.names:
            names_text = "%s: "% "->".join(reversed(self.names))

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
        self.message = "'%s'  Variable '%s' is not defined,'"% (
            text_where_var_missing, missing_var)


class NonStringValueError(PreRequisiteError):
    """Class when a scalar type other than a string is found in the YAML

    Only strings are supported to ensure that values like 01, 0x409, are
    kept as strings - i.e. it will have the same textual representation"""

    def __init__(self, text):
        PreRequisiteError.__init__(self, text)
        self.message = ("%%s is not a string. Please "
                "surround it with single quotes e.g. '%s'")% str(text)


class MissingFileDirError(PreRequisiteError):
    """A required file or directory is missing"""

    def __init__(self, text, path):
        PreRequisiteError.__init__(self, text)
        self.path = path
        self.message = "'%s' - File/Dir not be found - %s"% (path, text)


class FailedExternalCheck(PreRequisiteError):
    def __init__(self, command, ret, output):
        PreRequisiteError.__init__(self, command)
        self.message = (
            "External command '%s' failed "
            "with non zero return (%d).")% (command, ret)
        
        if output:
            output = output.strip()
            output = output.replace('\r\n', "\r\n   ")
            self.message += "\n   " + output


def LoadConfigFile(config_file):
    """Load the config files -return the variables and commands

    Recursively parse any included config files. Included files are parsed
    first so that data will be overridden by the including config file.
    """

    try:
        # load the config file
        f = open(config_file, "rb")
        config_data = yaml.load(f.read())
        f.close()

        # ensure that the keys in the config file are case insensitive
        errors = []
        
        config_data, was_error_case = ForEachKeyValue(
            config_data, MakeKeysCaseInsensitive, None, errors)
        
        config_data, was_error_string = ForEachKeyValue(
            config_data, EnsureStringValue, None, errors)
            
        if was_error_case or was_error_string:
            print errors
            
        variables = {}
        commands = {}

        # Parse the includes files
        if 'includes' in config_data and config_data['includes']:
            # load each of the included config files
            for inc in config_data['includes']:
                inc_vars, inc_cmds = LoadConfigFile(inc)
                variables.update(inc_vars)
                commands.update(inc_cmds)

            # we don't need this anymore
            del config_data['includes']

        # Now update the variables from this particular config file
        if 'variables' in config_data:
            variables.update(config_data['variables'])
            del config_data['variables']

        # And the commands (everything else is a command)
        commands.update(config_data)

        return variables, commands

    except yaml.parser.ScannerError, e:
        LOG.fatal("%s - %s"% (config_file, e))
        sys.exit()
    except yaml.parser.ParserError, e:
        LOG.fatal("%s - %s"% (config_file, e))
        sys.exit()


def ParseArguments():
    "Build up the command line parser and parse the arguments"

    # create the parser
    parser = optparse.OptionParser(
        description='Parse and run the config file',
        epilog = "Examples:\n\ttest1\n\ttest2",
        version = 0.0)

    # set up the basic options
    #parser.add_option(
    #    'config_file', metavar='config.yaml', type=str,
    #    help='YAML configuration file')

    parser.add_option(
        '-e', '--execute',  
        metavar = "cmd1,cmd2,cmd3", help='Run the commands')

    parser.add_option(
        '-i', '--include', action = "append",
        help='Other config files to include variables/commands from')

    #sp = parser.add_subparsers(
    #    title ="Commands",
    #    help = "Use 'COMMAND -h' for more information on the command" )

    parser.add_option(
        '-l', '--list', action = "store_true",
        help='List available commands')

    parser.add_option(
        '-t', '--test', action = "store_true",
        help='Perform some tests')

    parser.add_option(
        "-v", '--variables', metavar='var=value', type=str,
        action = "append", default = [],
        help='Override or define a variable')

    parser.add_option(
        '--validate', action = "store_true",
        help='Validate the config files')

    # parse the command line
    options, args = parser.parse_args()

    # validate that at least one config file was passed and that it exists
    if not args:
        LOG.fatal("You must specify a config file")
        sys.exit()

    elif len(args) > 1:
        LOG.fatal("Specify only one config file - '%s' "% ", ".join(args))
        sys.exit()

    config_file = args[0]
    if not os.path.exists(config_file):
        LOG.fatal("The config file does not exist: '%s'"% config_file)
        sys.exit()

    # ensure that the keys are all treated case insensitively
    variables, commands = LoadConfigFile(config_file)
    
    
    print repr(options), options
    print dir(options)
    # get the variable overrides passed at the command line
    variable_overrides = {}
    errors = []
    if options.variables:
        variable_overrides, was_error = ForEachKeyValue(
            ParseVariableOverrides(options.variables), 
            MakeKeysCaseInsensitive, 
            None,
            errors
            )
        if was_error:
            print errors

    print "xxxx", variable_overrides

    # update the read variables from the overrides
    variables = OverrideVariables(variables, variable_overrides)

    # calculate any values that need to be processed
    # todo - don't do this yet!!
    CalculateValues(variables)

    LOG.debug("Options: %s"% options)
    if options.execute:
        ExecuteCommands(variables, commands, options.execute)
    elif options.list:
        ListCommands(variables, commands, args)
    #elif options.test:
    #    Test(variables, commands, args)
    elif options.validate:
        sys.exit()

    os.environ["xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"] = "34"


def CalculateValues(variables):
    """Run through the variables and for any value that needs to be calculated
    Get it's value and run it."""

    # for each of the variables
    for key, value in variables.items():
        print key, value
        if SYSTEM_MARKER.match(value):
            
            # remove the system marker
            system_command = SYSTEM_MARKER.search(value).group(1)
            
            ret, out = ExecuteSystemCommand(system_command)
            variables[key] = out.strip()
            
            if ret:
                print ret, out
                raise RuntimeError("possible error setting variable from system command")


def EnsureStringValue(key, value, data, errors):
    """Add an error to the list if the value is not a string 
    
    (also allowed are dicts and lists) because their values will be checked
    later"""
    
    errors = []
    was_error = False
    if isinstance(value, (list, dict, basestring)):
        errors = [NonStringValueError(key), ]
        was_error = True

    return key, value, data, was_error


def MakeKeysCaseInsensitive(key, value, data, errors):
    "Make the key case insensitive"
    return iStr(key), value, data, False


def ForEachKeyValue(structure, func, data, errors):
    """Allow a function to be run on all key/value pairs
    
    For dictionaries both key and value are passed to func
    for Lists - we just interate the values
    for items - we pass just the value to func"""


    if not isinstance(errors, list):
        raise ValueError("errors value to ForEachKey must be a Python list")
    
    was_error = False
    
    # Handle different structure types differently
    if isinstance(structure, dict):
        # check all the values in the dictionary
        for key, value in structure.items():
            
            new_key, new_val, data, was_error = func(key, value, data, errors)
            
            # call this function recursively - as the value may itself
            # be a dictionary or a list
            new_val, was_error = ForEachKeyValue(new_val, func, data, errors)

            # if there were errors
            if not was_error:
                # only update the value if there were no errrors
                # Even if there were errors new_val may have been partially
                # updated
                
                # key has been updated so add the new key, and remove the old
                if new_key != key or repr(new_key) != repr(key):
                
                    # check if the new key would override something already
                    # in the structure
                    if new_key in structure and structure[key] != new_val:
                        errors.append((
                            "Warning - you have specified the value for %s "
                            "more than once, with different values "
                            "\n\t'%s'\n\t'%s')")% (
                                str(new_key), 
                                str(value), 
                                str(structure[new_key])))
                    else:
                        del structure[key]
                        structure[new_key] = new_val
                else:
                    structure[key] = new_val

    elif isinstance(structure, list):
        # Similar to dicts above - iterate over the list
        # calling ourselves recursively for each element
        # and only updating the value if there were no errors
        # note - we don't call the func for the list as a whole but rather
        # it will be called for each of the individual items
        for i, value in enumerate(structure):
            new_val, was_error = ForEachKeyValue(value, func, data, errors)

            if not was_error:
                structure[i] = new_val
    else:
        # It is a value - we can replace the variable references directly
        new_key, new_val, data, was_error = func(None, structure, data, errors)
        if not was_error:
            structure = new_val

    # return the updated structure and any errors
    return structure, was_error


def ParseVariableOverrides(variable_overrides):
    "Parse variable overrides passed on the command line"
    overrides = {}
    for override in variable_overrides:
        parsed = override.split("=")
        if len(parsed) != 2:
            raise RuntimeError("overrides need to be var=value")

        var, value = parsed
        var = var.strip()

        overrides[var] = value

    return overrides


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
    if not isinstance(item, basestring):
        return None, [NonStringValueError(item)]

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
            replace_with, sub_errors = ReplaceVariableReferences(
                vars[var_name_lower], vars)
            errors.extend(sub_errors)
            if not sub_errors:
                item = item.replace("<%s>"%(var), replace_with)
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


def ExecuteCommands(variables, commands, to_run):
    "Execute the commands passed in"

    available_commands = commands.keys()

    # commands are in a comma separated list, so we split them,
    # make them case insesitive, and strip off any spaces
    commands_to_run = [iStr(cmd.strip()) for cmd in to_run.split(",")]

    # try to execute the commands in order
    #LOG.debug("Commands to run:    %s"% ", ".join(commands_to_run))
    #LOG.debug("Available commands: %s"% ", ".join(available_commands))

    errs =  False
    for cmd_to_lookup in commands_to_run:
        matches = []
        cmd_to_lookup = cmd_to_lookup.lower()
        for command in available_commands:
            if cmd_to_lookup == command.lower():
                matches = [command]
                break
            elif command.lower().startswith(cmd_to_lookup):
                matches.append(command)
    
        if len(matches) > 1:
            LOG.fatal("The command you requested is ambiguous it matches: %s"% 
                ", ".join([str(cmd) for cmd in matches]))
            errs = True
            
        if not matches:
            LOG.fatal("Requested command '%s' not in available commands: %s"% (
                cmd_to_lookup, ", ".join([str(cmd) for cmd in unknown_cmds])))
            errs = True

    
        try:
            cmd = Command(commands[matches[0]], matches[0], variables)
            cmd.CheckPrerequisites()
            cmd.Execute()
        except PreRequisiteErrorCollection, e:            
            print e


def OverrideVariables(variables, overrides):
    "We want to work with the variables case sensitively"

    for ovr_key, ovr_value in overrides.items():
        if ovr_key in variables:
            print "INFO: Variable '%s', value '%s' overriden with value '%s'"% (
                ovr_key, variables[ovr_key], ovr_value)

        variables[ovr_key] = ovr_value

    return variables


def ExecuteSystemCommand(command, capture_output = True):
    "Execute a system command, and optionally capture the output"
    if capture_output:
        new_stdout = tempfile.TemporaryFile()
        #new_stderr = tempfile.TemporaryFile()
    else:
        new_stdout = sys.stdout
        #new_stderr = sys.stderr

    ret_value = subprocess.call(
        command,
        shell = True,
        stdout = new_stdout,
        stderr = subprocess.STDOUT)

    output = ''
    if capture_output:
        new_stdout.seek(0)
        output = new_stdout.read()

        #new_stderr.seek(0)
        #errors = new_stderr.read()

    return ret_value, output


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
            raise PreRequisiteErrorCollection(errors)
        else:
            self.cmd_info = updated_structure

    def CheckPrerequisites(self):
        "Run a check that the required files/folders exist"

        # if there are no pre-requisites - then just return
        if 'prechecks' not in self.cmd_info:
            return

        failed_prereqs = []
        pre_reqs = self.cmd_info['prechecks']
        for item in pre_reqs:
            # if it is just a plain string then check that the file exists
            if isinstance(item, basestring):
                if SYSTEM_MARKER.match(item):
                    # remove the system marker
                    system_command = SYSTEM_MARKER.search(item).group(1)
                    
                    ret, out = ExecuteSystemCommand(system_command)
                    
                    if ret != 0:
                        failed_prereqs.append(
                            FailedExternalCheck(command, ret, output))

                elif not os.path.exists(os.path.normpath(item)):
                    failed_prereqs.append(MissingFileDirError(item, item))

            else:
                raise RuntimeError("Should not have a list or dict within "
                    "the pre-requisites")
        
        if failed_prereqs:    
            raise PreRequisiteErrorCollection(failed_prereqs)


    def Execute(self):
        "Run the command after checking pre-requisites"
        self.CheckPrerequisites()
        #if missing:
        #    raise RuntimeError(
        #        "Some requirements are missing. Command cannot execute: %s"%
        #         str(missing))

        steps = self.cmd_info['run']
        for step in steps:
            ret, output = ExecuteSystemCommand(step)
            print output
            if ret:
                print "Possible error return!!"
                print output


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
#    exec_return, output = ExecuteSystemCommand(
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
    ParseArguments()

