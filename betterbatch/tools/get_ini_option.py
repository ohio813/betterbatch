"""
   Usage: get_config_option.py config_file section value [default]

   Example:
       get_config_option.py base_build_numbers.ini G015 adr_build
    or
       get_config_option.py base_build_numbers.ini G01* adr_build
"""

import sys
import fnmatch
import ConfigParser


class WildCardError(RuntimeError):
    "Error raised when the wildcard return more than 1 match"

    def __init__(self):
        RuntimeError.__init__(self)


class IniFileNotFoundError(RuntimeError):
    "Error raised when Ini File is not found"

    def __init__(self):
        RuntimeError.__init__(self)


def get_value_from_ini_file(ini_file, section, value):
    "Get the value from ini file"

    parser = ConfigParser.ConfigParser()

    # Raise if ini_file cannot be read
    if not parser.read(ini_file):
        raise IniFileNotFoundError

    section_list = parser.sections()

    # Raise NoSectionError if the input does not match any of the sections
    if not fnmatch.filter(section_list, section):
        raise ConfigParser.NoSectionError(section)

    # Raise WildCardError if section matches more than 1 section in ini file
    elif len(fnmatch.filter(section_list, section)) > 1:
        raise WildCardError

    else:
        matched_section = fnmatch.filter(section_list, section)[0]

    return parser.get(matched_section, value)


def main(ini_file, section, value, default):

    try:
        return_data = get_value_from_ini_file(ini_file, section, value)
        print return_data
        return 0
    except ConfigParser.NoOptionError:
        if default:
            print default
            return 0
        else:
            print "No Option: " + value + " in Section: " + section
            return -1
    except ConfigParser.NoSectionError, err:
        print err
        return -2
    except WildCardError:
        print "More than 1 match found with " + section
        return -3
    except IniFileNotFoundError:
        print "Invalid Ini file - " + ini_file
        return -4


if __name__ == "__main__":
    if len(sys.argv) <= 3:
        print __doc__
        sys.exit(1)
    else:
        ini_file = sys.argv[1]
        section = sys.argv[2]
        value = sys.argv[3]

    default = None
    if len(sys.argv) >= 5:
        default = sys.argv[4]

    sys.exit(main(ini_file, section, value, default))
