"Performa a simple or regular expression replacement in the file"

import sys
import re
import os
import codecs
from optparse import OptionParser


BOM_ENCODING_NAMES = [
    (getattr(codecs, "BOM_UTF16_BE"), 'utf-16-be'),
    (getattr(codecs, "BOM_UTF16_LE"), 'utf-16-le'),
    (getattr(codecs, "BOM_UTF8"),  'utf-8-sig'),]

# python 2.5 does not have utf-32 encodings
if not (sys.version_info[0] == 2 and sys.version_info[1] == 5):
    BOM_ENCODING_NAMES.insert(
        0, (getattr(codecs, "BOM_UTF32_BE"), 'utf-32-be'))
    BOM_ENCODING_NAMES.insert(
        1, (getattr(codecs, "BOM_UTF32_LE"), 'utf-32-le'))


def get_arguments():
    parser = OptionParser("$prog [-rn] [--encoding enc] filepath to_find replace_with")

    parser.add_option("-r", "--regex",
                      default=False, action="store_true",
                      help="search and replacement are regular expressions")
    parser.add_option("-n", "--noerr",
                      default=False, action="store_true",
                      help="do not report an error if the text is not found")
    parser.add_option("--universal-newlines",
                      default=False, action="store_true",
                      help="open the file in a mode that converts all line "
                        "endings (EOL) to \\n internally. NOTE when the file "
                        "is written all EOLs will be the current OS native "
                        "EOL e.g. \\r\\n on Windows, \\r on MAC, \\n on *nix")
    parser.add_option("--encoding",
                      default='None', action="store",
                      metavar="(auto,none,...)",
                      help="specify the encoding of the text. "
                        "A value of 'AUTO' will have the script try and find "
                        "out the encoding - based on any BOMs present. "
                        "A value of 'NONE' (default) will not decode the "
                        "contents. The contents will be processed as "
                        "'binary'. Any other value should be a valid Python "
                        "encoding see "
                        "http://docs.python.org/library/codecs.html#standard-encodings.")

    # parse the command line arguments
    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(0)

    if len(args) != 3:
        parser.print_help()
        print "\n**ERROR** 3 required arguments!"
        sys.exit(5)

    options.encoding = options.encoding.upper()
    if options.encoding == "NONE":
        options.encoding = None

    return options, args


def get_encoding_from_BOM(contents):
    """Get the encoding from the BOM"""

    # try and see if it starts with any known BOM
    encoding = None
    # we need to test in the right order - otherwise
    # UTF16 will be returned for utf32
    for bom, enc_name in BOM_ENCODING_NAMES:
        if contents.startswith(bom):
            encoding = enc_name
            break

    return encoding


def perform_replacements(contents, to_find, replace_with, options):
    if options.regex:
        # compile the regular expression
        to_find = re.compile(to_find, re.M)
        # replace and find how many were replaced
        contents, count = to_find.subn(replace_with, contents)
        #import pdb; pdb.set_trace()
        # unless told to ignore errors - report the error
        if count == 0:
            if not options.noerr:
                raise RuntimeError(
                        "Regex '%s' not in the file: '%%s'" % to_find.pattern)
            else:
                print "Regex not found: %s" % to_find
        else:
            print "Replaced %d instances"% count

    else:
        # check that the string is in the contents
        if to_find not in contents:
            if not options.noerr:
                raise RuntimeError(
                    "String '%s' not in the file: '%%s'" % to_find)
            else:
                print "Text not found: %s" % to_find
        else:
            contents = contents.replace(to_find, replace_with)
            print "Replaced all instances"

    return contents


def main(filename, to_find, replace_with, options):

    read_mode = 'rb'
    write_mode = 'wb'
    if options.universal_newlines:
        read_mode = 'rU'
        write_mode = 'w'

    try:
        # open and read the file
        f = open(filename, read_mode)
        contents = f.read()
        f.close()
    except IOError, e:
        print ("**ERROR** file could not be read: '%s'"% filename)
        return 10

    # if we have been asked to guess the encoding
    if options.encoding == "AUTO":
        options.encoding = get_encoding_from_BOM(contents)

    # Encode if we need to
    if options.encoding:
        try:
            contents = contents.decode(options.encoding)
        except UnicodeError, e:
            print("**ERROR** Contents are not in encoding: '%s'"%
                options.encoding)
            return 20

    # replace in the contents
    try:
        contents = perform_replacements(
            contents, to_find, replace_with, options)
    except re.error, e:
        print "**ERROR** (REGEX) %s" % str(e)
        return 50
    except RuntimeError, e:
        print "**ERROR** %s" % (str(e) % filename)
        return 40

    if options.encoding:
        # re-encode for writing to the file
        contents = contents.encode(options.encoding)
        # ensure that teh BOM is added back
        if options.encoding in [b[1] for b in BOM_ENCODING_NAMES]:
            bom = [bn[0] for bn in BOM_ENCODING_NAMES
                    if bn[1] == options.encoding][0]
            if not contents.startswith(bom):
                contents = bom + contents

    # write out the updated contents
    f = open(filename, write_mode)
    f.write(contents)
    f.close()

    return 0


if __name__ == "__main__":
    options, args = get_arguments()
    filename = os.path.abspath(args[0])
    to_find = args[1]
    replace_with = args[2]

    sys.exit(main(filename, to_find, replace_with, options))

