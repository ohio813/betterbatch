"Registers the BetterBatch filetype with python.exe bbrun.py Scriptpath"
import sys
import os
import _winreg
import optparse

def ParseOptions():
    parser = optparse.OptionParser('Associate BetterBatch files on Windows')

    parser.add_option(
        "-b", "--bbrun",
        default = '',
        help='use the path to the specified bbrun.py')
    
    parser.add_option(
        "-t", "--timed",
        action = 'store_true',
        help='register bbrun.py so that scripts will be timed')

   # parse the command line
    options, args =  parser.parse_args()
    
    if options.bbrun:
        options.bbrun = os.path.abspath(options.bbrun)
    else:
        options.bbrun = os.path.join(sys.prefix, 'scripts', 'bbrun.py')
        if not os.path.exists(options.bbrun):
            options.bbrun = os.path.join(
                sys.prefix, 'scripts', 'bbrun-script.py')
        
    return options
    
#    Add timing arg
#    don't modify PATHEXT
#    use specified bbrun.py


def main():
    "Do the work"
    options = ParseOptions()

    # check that the bbrun.py exists in the scripts directory
    if not os.path.exists(options.bbrun):
        print "Script runner was not found: '%s'"% options.bbrun
        sys.exit(1)

    print "Setting up Association and Filetype"
    # Register the BB file type and associate the bbrun script to run it
    os.system("assoc .bb=BetterBatchScriptFile")
    timing = ''
    if options.timed:
        timing = '-t'
    os.system(
        'ftype BetterBatchScriptFile=%s %s %s "%%1" %%*'% (
            os.path.join(sys.prefix, "python.exe"),
            options.bbrun, timing))

    # update the pathext

    # Open the Reg Key that has the PATHEXT
    hkey = _winreg.OpenKey(
        _winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        0,
        _winreg.KEY_WRITE | _winreg.KEY_READ)

    # Read the Pathext Value
    val, reg_type = _winreg.QueryValueEx(hkey, 'PATHEXT')

    print "Adding BB to PATHEXT variable"
    # if BetterBatch is not there
    if ".BB" not in val.upper():
        if not val.endswith(';'):
            val += ";"
        val += ".BB"

        # add it
        _winreg.SetValueEx(hkey, r"PATHEXT", None, _winreg.REG_SZ, val)

    # and close the registry key
    _winreg.CloseKey(hkey)
    print "Completed!"


if __name__ == "__main__":
    main()
