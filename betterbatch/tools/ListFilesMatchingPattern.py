import os
import sys
from fnmatch import fnmatch
from optparse import OptionParser


def ParseArguments():
    parser = OptionParser(
        usage = "%prog [options] (path) (patern1) (pattern2) ...")

    parser.add_option(
        "-s", "--recursive",
        default = False,
        action = "store_true",
        help = "scan recursively")

    options, args = parser.parse_args()

    if not args:
        parser.print_help()

    if len(args) < 2:
        print "Too few arguments, please provide search path and at least one pattern"
        sys.exit(2)

    options.search_path = args[0]
    options.patterns = args[1:]

    if not os.path.exists(options.search_path):
        print "Search folder does not exist: '%s'"% options.search_path
        sys.exit(3)

    return options


if __name__ == "__main__":
    options = ParseArguments()

    for root, dir, files in os.walk(options.search_path):
        for filename in files:
            for pattern in options.patterns:
                if fnmatch(filename, pattern):
                    print '%s'% os.path.abspath(os.path.join(root, filename))
                    break
                    
        if not options.recursive:
            break
