"""Retrieve a value from the registry

Usage: GetRegistryValue Path [value]

Path should start with one of the standard keys 
    (e.g. HKLM, HKEY_CURRENT_USER, etc)
    
Leave Value blank to get the default value.
"""

from _winreg import *
import sys
import os

# add the shortcuts
HKLM = HKEY_LOCAL_MACHINE
HKCU = HKEY_CURRENT_USER

if __name__ == "__main__":
    # parse the arguments
    reg_value_path = sys.argv[1]
    value = ""
    if len(sys.argv) > 2:
        value = sys.argv[2]

    # get the root key separate from the rest of the path
    root_key, path = reg_value_path.split('\\', 1)

    # get the handle to the root key
    root_key_handle = locals().get(root_key.upper(), None)

    # and validate that it was found correctly
    if root_key_handle is None:
        print "Unknown root key: '%s'"% root_key
        sys.exit(1)

    # open the key
    opened_key = OpenKey(root_key_handle, path)

    # get the value
    value, val_type = QueryValueEx(opened_key, value)

    # print it out :)
    print value

