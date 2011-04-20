"""Retrieve a value from the registry

Usage: GetRegistryValue Path [value]

Path should start with one of the standard keys
    (e.g. HKLM, HKEY_CURRENT_USER, etc)

Leave Value blank to get the default value.
"""

import _winreg as winreg
import sys
import os
import re
from optparse import OptionParser


def parse_args():
    "Parse and check the command line arguments"

    parser = OptionParser(
        usage = "%prog [options] (keypath) [value_name]")

    parser.add_option(
        "-e", "--expand", default = False, action ="store_true",
        help = "if the registry type is REG_EXPAND_SZ - then expand variables")

    parser.add_option(
        "--x64", default = False, action ="store_true",
        help = "operate on 64bit registry hive")

    options, args = parser.parse_args()

    if len(args) == 0:
        parser.print_help()
        sys.exit()

    if len(args) > 2:
        parser.print_help()
        # some args were supplied
        print "**ERROR** Too many arguments were supplied!"

        sys.exit(1)

    if len(args) == 1:
        args.append('')

    return options, args


def main():
    "Retrieve and print a registry value"

    # parse the arguments
    options, (reg_value_path, value_name) = parse_args()

    # get the root key separate from the rest of the path
    root_key, path = reg_value_path.split('\\', 1)

    # get the handle to the root key
    # add the shortcuts
    winreg.HKLM = winreg.HKEY_LOCAL_MACHINE
    winreg.HKCU = winreg.HKEY_CURRENT_USER
    root_key_handle = winreg.__dict__.get(root_key.upper(), None)

    # and validate that it was found correctly
    if root_key_handle is None:
        print "Unknown root key: '%s'"% root_key
        sys.exit(1)

    # open the key
    if options.x64:
        opened_key = winreg.OpenKey(
            root_key_handle, path, 0, winreg.KEY_WOW64_64KEY | winreg.KEY_READ)
    else:
        opened_key = winreg.OpenKey(root_key_handle, path)

    # get the value
    value, val_type = winreg.QueryValueEx(opened_key, value_name)

    if val_type == winreg.REG_EXPAND_SZ and options.expand:
        # mimic ExpandEnvironmentStrings in python
        env_var = re.compile(r"%([^%]+)%")
        for var in env_var.finditer(value):
            var_val = os.environ.get(var.group(1), None)
            if var_val:
                value = value.replace(var.group(0), var_val)

    # print it out :)
    print value


if __name__ == "__main__":
    main()


