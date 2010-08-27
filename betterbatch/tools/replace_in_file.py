"Performa a simple or regular expression replacement in the file"

import sys
import re
from optparse import OptionParser

def GetArguments():
    parser = OptionParser("$prog [-r] file to_find replace_with")

    parser.add_option("-r", "--regex", default = False, action = "store_true",
                      help="search and replacement are regular expressions")
    parser.add_option("-n", "--noerr", default = False, action = "store_true",
                      help="do not report an error if the text is not found")

    # parse the command line arguments
    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(0)
    
    return options, args

if __name__ == "__main__":
    options, args = GetArguments()
    filename = args[0]
    to_find = args[1]
    replace_with = args[2]

    # open and read the file
    f = open(filename, "rb")
    contents = f.read()
    f.close()

    if options.regex:
        # compile the regular expression
        to_find = re.compile(to_find, re.M)
        # replace and find how many were replaced
        contents, count = to_find.subn(replace_with, contents)
        #import pdb; pdb.set_trace()
        # unless told to ignore errors - report the error
        if not options.noerr and count == 0:
            print "Regex '%s' not in the file: '%s'"% (args[1], filename)
            sys.exit(1)
        
        print "Replaced %d instances"% count
            
    else:
        # check that the string is in the contents
        if not options.noerr and to_find not in contents:
            print "String '%s' not in the file: '%s'"% (to_find, filename)
            sys.exit(1)

        contents = contents.replace(to_find, replace_with)
        print "Replaced all instances"

    # write out the updated contents
    f = open(filename, "wb")
    f.write(contents)
    f.close()
