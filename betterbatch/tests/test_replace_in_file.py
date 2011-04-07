from __future__ import absolute_import

import unittest
import os
import sys
import codecs
import re

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

# ensure that the package root is on the path
PACKAGE_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.append(PACKAGE_ROOT)

TOOLS_FOLDER = os.path.abspath(os.path.join(
    os.path.dirname(TESTS_DIR), 'tools'))
FILE_UNDER_TEST = os.path.join(TOOLS_FOLDER, 'replace_in_file.py')
sys.path.append(TOOLS_FOLDER)

import replace_in_file


TEST_PATH = os.path.abspath(TESTS_DIR)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

class DummyOptions(object):
    def __init__(self):
        self.encoding = None
        self.regex = False
        self.noerr = False
        self.universal_newlines = False


def get_file_contents(filepath):
    f = open(filepath, "rb")
    contents = f.read()
    f.close()
    return contents

def reset_file_contents(filepath, contents):
    f = open(filepath, "wb")
    f.write(contents)
    f.close()


class ReplaceInFileTests(unittest.TestCase):
    "Perform some simple tests on replace_in_file"

    #def setUp(self):
    #    self.vars = {}
    #    self.vars['var'] = "value"
    #    self.vars['var2'] = "value<here>"

    def test_no_args(self):
        "Test with no args"
        ret = os.system(FILE_UNDER_TEST)
        self.assertEquals(ret, 0)

    def test_wrong_arg_count(self):
        "Test with any except 3 args"
        ret = os.system("%s one_arg" % FILE_UNDER_TEST)
        self.assertEquals(ret, 5)

        ret = os.system("%s one_arg two" % FILE_UNDER_TEST)
        self.assertEquals(ret, 5)

        ret = os.system("%s one_arg two three four" % FILE_UNDER_TEST)
        self.assertEquals(ret, 5)

    def test_get_arguments_no_args(self):
        sys.argv = ["prog.py"]
        self.assertRaises(
            SystemExit,
            replace_in_file.get_arguments,)

    def test_get_arguments_not_correct_args(self):
        sys.argv = ["prog.py", "hi"]
        self.assertRaises(
            SystemExit,
            replace_in_file.get_arguments,)

        sys.argv = ["prog.py", "there's", "ants", "in", "my", "pants"]
        self.assertRaises(
            SystemExit,
            replace_in_file.get_arguments,)

    def test_get_arguments_correct_args(self):
        sys.argv = ["prog.py", "there's", "ants", "in"]
        options, args = replace_in_file.get_arguments()

        sys.argv = ["prog.py", "there's", "ants", "in", "--encoding=Auto"]
        options, args = replace_in_file.get_arguments()
        self.assertEquals(options.encoding, "AUTO")

        sys.argv = ["prog.py", "there's", "ants", "in", "--encoding=None"]
        options, args = replace_in_file.get_arguments()
        self.assertEquals(options.encoding, None)


    def test_getting_encoding_known_BOM(self):
        "test that it guesses the encoding correctly"

        for bom, encoding in replace_in_file.BOM_ENCODING_NAMES:

            enc_got = replace_in_file.get_encoding_from_BOM(bom + "a")
            self.assertEquals(encoding, enc_got)

    def test_getting_encoding_no_BOM(self):
        "test that it guesses the encoding correctly - when no BOM"

        enc_got = replace_in_file.get_encoding_from_BOM("a")
        self.assertEquals(enc_got, None)

        enc_got = replace_in_file.get_encoding_from_BOM("")
        self.assertEquals(enc_got, None)

    def test_missing_file(self):
        "test that it fails if the file doesn't exist"
        ret = replace_in_file.main('file_doesnt_exist', 'b', 'c', DummyOptions())
        self.assertEquals(ret, 10)

    def test_working_with_wrong_encoding(self):
        "return non zero when file is not in the same encoding"
        options = DummyOptions()
        options.encoding = "utf-8"
        test_file = os.path.join(TEST_FILES_PATH, 'replace_in_file_test_utf_16_le.txt')
        prev_contents = get_file_contents(test_file)
        try:
            ret = replace_in_file.main(
                test_file,
                '',
                '',
                options)
            self.assertEquals(ret, 20)
        finally:
            reset_file_contents(test_file, prev_contents)

    def test_perform_replacements_not_found(self):
        options = DummyOptions()
        self.assertRaises(
            RuntimeError,
            replace_in_file.perform_replacements,
                "contents", "to_find", "replace_with", options)

        options.noerr = True
        new_contents = replace_in_file.perform_replacements(
            "contents", "to_find", "replace_with", options)
        self.assertEquals(new_contents, "contents")

    def test_perform_replacements_regex_not_found(self):
        options = DummyOptions()
        options.regex = True
        self.assertRaises(
            RuntimeError,
            replace_in_file.perform_replacements,
                "contents", "to_find", "replace_with", options)

        options.noerr = True
        new_contents = replace_in_file.perform_replacements(
            "contents", "to_find", "replace_with", options)
        self.assertEquals(new_contents, "contents")

    def test_replacing_in_file(self):
        # test that it fails if the file doesn't exist
        for encoding in ('ansi', 'utf_8', 'utf_16_be', 'utf_16_le'):
            options = DummyOptions()
            test_file = os.path.join(
                TEST_FILES_PATH, 'replace_in_file_test_%s.txt' % encoding)
            prev_contents = get_file_contents(test_file)
            try:
                ret = replace_in_file.main(test_file, 'a', 'b', options)
                self.assertEquals(ret, 0)

                new_contents = get_file_contents(test_file)

                self.assertEquals(
                    prev_contents.replace('a', 'b'), new_contents)

            finally:
                reset_file_contents(test_file, prev_contents)

    def test_ensure_bom_is_added(self):
        test_file = os.path.join(
            TEST_FILES_PATH, 'replace_in_file_test_ansi.txt')

        options = DummyOptions()
        options.regex = True
        options.encoding = 'utf-16-be'

        prev_contents = get_file_contents(test_file)
        try:
            encoded_contents = prev_contents.decode('mbcs').encode('utf-16-be')
            reset_file_contents(test_file, encoded_contents)

            ret = replace_in_file.main(test_file, r'([a-z ])', r'\1', options)

            new_contents = get_file_contents(test_file)
            self.assertEquals(new_contents, codecs.BOM_UTF16_BE + encoded_contents)
        finally:
            reset_file_contents(test_file, prev_contents)

    def test_replacing_in_file_regex(self):
        # test that it fails if the file doesn't exist
        for encoding in ('ansi', 'utf_8', 'utf_16_be', 'utf_16_le'):
            options = DummyOptions()
            options.encoding = "AUTO"
            options.regex = True
            test_file = os.path.join(
                TEST_FILES_PATH, 'replace_in_file_test_%s.txt' % encoding)
            prev_contents = get_file_contents(test_file)
            try:
                ret = replace_in_file.main(test_file, r'([a-z ])', r'\1', options)
                self.assertEquals(ret, 0)

                new_contents = get_file_contents(test_file)

                #emulated = []
                #for c in prev_contents:
                #    if ord(c) < 128 and c != "\0":
                #        emulated.append("-" + c)
                #    else:
                #        emulated.append(c)
                #emulated = "".join(emulated)

                self.assertEquals(prev_contents, new_contents)

            finally:
                reset_file_contents(test_file, prev_contents)

    def test_replacing_noerr_false(self):
        options = DummyOptions()
        #options.noerr = True
        test_file = os.path.join(
            TEST_FILES_PATH, 'replace_in_file_test_ansi.txt')

        prev_contents = get_file_contents(test_file)
        try:
            ret = replace_in_file.main(
                test_file, 'not found', r'doesnt matter', options)
            self.assertEquals(ret, 40)
        finally:
            reset_file_contents(test_file, prev_contents)

    def test_ansi_encoding(self):
        options = DummyOptions()
        options.encoding = "mbcs"
        test_file = os.path.join(
            TEST_FILES_PATH, 'replace_in_file_test_ansi.txt')

        prev_contents = get_file_contents(test_file)
        try:
            ret = replace_in_file.main(
                test_file, 'a', 'b', options)
            self.assertEquals(ret, 0)
            new_contents = get_file_contents(test_file)
            self.assertEquals(prev_contents.replace('a', 'b'), new_contents)
        finally:
            reset_file_contents(test_file, prev_contents)

    def test_broken_regexp(self):
        options = DummyOptions()
        options.regex = True
        self.assertRaises(
            re.error,
            replace_in_file.perform_replacements,
                "", "(.", r"\1", options)

    def test_broken_regexp_main(self):
        options = DummyOptions()
        options.regex = True
        test_file = os.path.join(
            TEST_FILES_PATH, 'replace_in_file_test_ansi.txt')

        ret = replace_in_file.main(
            test_file, '(', r'doesnt matter', options)
        self.assertEquals(ret, 50)


    def test_newlines_replaced(self):
        # issue 12: replace_in_file changes line ending to LF if line
        # ending is involved in regexp
        options = DummyOptions()
        options.regex = True
        options.universal_newlines = True

        for line_ending, chr in (('crlf', '\r\n'), ('lf', '\n'), ('cr', '\r')):
            test_file = os.path.join(
                TEST_FILES_PATH,
                'replace_in_file_test_multi_%s.txt' % line_ending)

            prev_contents = get_file_contents(test_file)
            #normalize prev contents
            test_against = prev_contents.replace(chr, "\r\n")
            test_against = test_against.replace('a', '--')
            try:
                ret = replace_in_file.main(
                    test_file, r'^a.*$', '--', options)
                self.assertEquals(ret, 0)
                new_contents = get_file_contents(test_file)
                self.assertEquals(
                    new_contents,
                    test_against,
                    "newline support failed for '%s'\n%r <-> %r" % (
                        line_ending, new_contents, test_against))
            finally:
                reset_file_contents(test_file, prev_contents)

    def test_cr_newlines_replaced(self):
        # we need to specify Binary - if we want to work with files with
        # CR line endings
        options = DummyOptions()
        options.regex = True

        test_file = os.path.join(
            TEST_FILES_PATH, 'replace_in_file_test_multi_cr.txt')

        prev_contents = get_file_contents(test_file)
        try:
            ret = replace_in_file.main(
                test_file, r'^a[^\r]*$', '--', options)
            self.assertEquals(ret, 0)
            new_contents = get_file_contents(test_file)
            self.assertEquals(
                new_contents,
                prev_contents.replace('a', '--'))
        finally:
            reset_file_contents(test_file, prev_contents)

if __name__ == "__main__":
    unittest.main()
