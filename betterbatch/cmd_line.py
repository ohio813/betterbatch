import optparse
import sys
import os

USAGE = r"""
Executes a BetterBatch script file.

%prog [-c][-h][-v] (script file) [var=value] [var=value]...

Examples:
    bbrun.py --verbose my_script.bb test_dir=%temp%\there build=H099"""

def ParseArguments():
    "Build up the command line parser and parse the arguments"

    # create the parser
    parser = optparse.OptionParser(
        description='Parse and run the script file',
        usage = USAGE,
        epilog = "Examples:\n\ttest1\n\ttest2",
        version = 0.0)

    # set up the basic options
    #parser.add_option(
    #    'script_file', metavar='script.yaml', type=str,
    #    help='YAML scripturation file')

    parser.add_option(
        "-c", '--check',
        action = "store_true",
        help='do not execute any commands, read and validate script file')

    parser.add_option(
        "-d", '--debug',
        action = "store_true",
        default = False,
        help='do not execute any commands, read and validate script file')

    #parser.add_option(
    #    '-e', '--execute',
    #    metavar = "cmd1,cmd2,cmd3", help='Run the commands')

    #parser.add_option(
    #    '-i', '--include', action = "append",
    #    help='Other script files to include variables/commands from')

    #sp = parser.add_subparsers(
    #    title ="Commands",
    #    help = "Use 'COMMAND -h' for more information on the command" )

    #parser.add_option(
    #    '-l', '--list', action = "store_true",
    #    help='List available commands')

    parser.add_option(
        "-t", '--timed',
        action = "store_true",
        help='output how long the script took to execute')

    #parser.add_option(
    #    '--log-times',
    #    action = "store_true",
    #    help='include execution time in the log file')

    parser.add_option(
        '-v', '--verbose', action = "store_true",
        help='output debug messages to console')

    # parse the command line
    options, args =  parser.parse_args()
    if not args:
        print USAGE
        sys.exit()
    return options, args


def ParseVariableOverrides(variable_overrides):
    "Parse variable overrides passed on the command line"
    overrides = {}
    for override in variable_overrides:
        parsed = override.split("=")
        if len(parsed) != 2:
            raise RuntimeError(
                "Error: Variable Overrides need to be var=value: "
                "e.g. 'var_name=%s'"% override)

        name, value = parsed
        name = name.strip().lower()

        overrides[name] = value

    return overrides


def ValidateOptions(options, args):
    # validate that at least one script file was passed and that it exists


    #elif len(args) > 1:
    #    raise RuntimeError(
    #        "Specify only one script file - '%s' "% ", ".join(args))

    options.script_file = args[0]
    if not os.path.exists(options.script_file):
        raise RuntimeError(
            "The script file does not exist: '%s'"% options.script_file)

    override_vars = ParseVariableOverrides(args[1:])
    options.variables = override_vars

    return options


def GetValidatedOptions():
    options, args = ParseArguments()
    return ValidateOptions(options, args)
