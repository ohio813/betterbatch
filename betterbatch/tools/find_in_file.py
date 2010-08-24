"""Script to search for text in a file"""
import re
import sys
from optparse import OptionParser


def GetArguments():
    parser = OptionParser("$prog [-r] file text_to_find [text_to_find...]")

    parser.add_option("-r", "--regex", default = False, action = "store_true",
                      help="search and replacement are regular expressions")
    parser.add_option("-n", "--noerr", default = False, action = "store_true",
                      help="do not report an error if the text is not found")
    parser.add_option("-i", "--ignorecase", default = False, action = "store_true",
                      help="ignore case when searching")

    # parse the command line arguments
    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(0)

    return options, args


if __name__ == "__main__":
    options, args = GetArguments()
    filename = args[0]
    texts_to_find = args[1:]

    # open and read the file
    f = open(filename, "rb")
    contents = f.read()
    f.close()

    flags = 0
    if options.ignorecase:
        flags = re.I

    # for each of the search texts
    for text in texts_to_find:
        # escape it if it is not a regular expression
        if not options.regex:
            text = re.escape(text)

        # compile the search into a regular expression
        search_re = re.compile(text, flags)

        # search for the text
        found = search_re.findall(contents)

        # if it was not found - then check if we need to return an error code
        if not found and not options.noerr:
            sys.exit(1)

        # print out any found items
        for found_item in found:
            print found_item

        # return success
        sys.exit(0)
