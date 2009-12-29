import optparse
import sys
import os

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
    return parser.parse_args()


def ParseVariableOverrides(variable_overrides):
    "Parse variable overrides passed on the command line"
    overrides = {}
    for override in variable_overrides:
        parsed = override.split("=")
        if len(parsed) != 2:
            raise RuntimeError(
                "overrides need to be var=value: '%s'"% override)

        name, value = parsed
        name = name.strip().lower()

        overrides[name] = value

    return overrides


def ValidateOptions(options, args):
    # validate that at least one config file was passed and that it exists
    
    if not args:
        raise RuntimeError("You must specify a config file")

    elif len(args) > 1:
        raise RuntimeError(
            "Specify only one config file - '%s' "% ", ".join(args))

    options.config_file = args[0]
    if not os.path.exists(options.config_file):
        raise RuntimeError(
            "The config file does not exist: '%s'"% options.config_file)
    
    override_vars = ParseVariableOverrides(options.variables)
    options.variables = override_vars
    
    return options


def GetValidatedOptions():
    options, args = ParseArguments()
    return ValidateOptions(options, args)
