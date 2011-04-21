"""Retrieve a value from the registry

Usage: SetRegistryValue (path) (value_name) (value)

Path should start with one of the standard keys
    (e.g. HKLM, HKEY_CURRENT_USER, etc)

Leave Value blank to get the default value.
"""

import _winreg as winreg
import sys
from optparse import OptionParser


HANDLED_REGISTRY_TYPES = [
    "REG_DWORD",
    "REG_DWORD_LITTLE_ENDIAN",
    "REG_DWORD_BIG_ENDIAN",
    "REG_EXPAND_SZ",
    "REG_LINK",
    "REG_MULTI_SZ",
    "REG_NONE",
    "REG_SZ",]
# The following are not handled yet
#    "REG_BINARY",
#    "REG_RESOURCE_LIST",
#    "REG_FULL_RESOURCE_DESCRIPTOR",
#    "REG_RESOURCE_REQUIREMENTS_LIST",



def parse_args():
    "Parse and check the command line arguments"

    parser = OptionParser(
        usage = "%prog [options] (keypath) (value_name) (new_value)")

    parser.add_option(
        "-t", "--value-type", default = "REG_SZ",
        help = "when creating a new value - the value type to use."
            "When changing existing values - the same type is used.")

    parser.add_option(
        "--x64", default = False, action ="store_true",
        help = "operate on 64bit registry hive")

    options, args = parser.parse_args()

    if len(args) != 3:
        parser.print_help()

        # normal exit (no return code - no error message)
        if len(args) == 0:
            sys.exit()

        print "**ERROR** All three arguments are required"
        sys.exit(1)

    if options.value_type not in HANDLED_REGISTRY_TYPES:
        print "**ERROR** Unknown registry Value type"
        print "Supported registry types:", HANDLED_REGISTRY_TYPES
        sys.exit(1)

    options.value_type = winreg.__dict__[options.value_type.upper()]

    return options, args


def main():
    "Set a registry value"

    # parse the arguments
    options, (reg_value_path, value_name, value) = parse_args()

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
    open_flag = winreg.KEY_ALL_ACCESS
    if options.x64:
        open_flag = open_flag | winreg.KEY_WOW64_64KEY
    opened_key = winreg.OpenKey(root_key_handle, path, 0, open_flag)

    # Check if there is an existing value of that type
    try:
        # we don't care about the old value
        _, val_type = winreg.QueryValueEx(opened_key, value_name)
    except WindowsError:
        val_type = options.value_type

    if val_type in (winreg.REG_DWORD, winreg.REG_DWORD_LITTLE_ENDIAN):
        value = eval(value)

    winreg.SetValueEx(opened_key, value_name, 0, val_type, value)
    winreg.CloseKey(opened_key)

    sys.exit(0)


if __name__ == "__main__":
    main()
