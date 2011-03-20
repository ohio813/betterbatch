from __future__ import absolute_import

import unittest
import os
import sys
import codecs

# ensure that the package root is on the path
TOOLS_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'tools')
FILE_UNDER_TEST = os.path.join(TOOLS_FOLDER, 'replace_in_file.py')
sys.path.append(TOOLS_FOLDER)

import replace_in_file

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")

class DummyOptions(object):
    def __init__(self):
        self.encoding = 'AUTO'
        self.regex = False
        self.noerr = False


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
        options.encoding = "utf-32"
        ret = replace_in_file.main(
            os.path.join(TEST_FILES_PATH, 'replace_in_file_test_ansi.txt'),
            '',
            '',
            options)
        self.assertEquals(ret, 20)

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
            with open(test_file, "rb") as f:
                prev_contents = f.read()
            try:
                ret = replace_in_file.main(test_file, 'a', 'b', options)
                self.assertEquals(ret, 0)

                with open(test_file, "rb") as f:
                    new_contents = f.read()

                self.assertEquals(
                    prev_contents.replace('a', 'b'), new_contents)

            finally:
                with open(test_file, "wb") as f:
                    f.write(prev_contents)

    def test_replacing_in_file_regex(self):
        # test that it fails if the file doesn't exist
        for encoding in ('ansi', 'utf_8', 'utf_16_be', 'utf_16_le'):
            options = DummyOptions()
            options.regex = True
            test_file = os.path.join(
                TEST_FILES_PATH, 'replace_in_file_test_%s.txt' % encoding)
            with open(test_file, "rb") as f:
                prev_contents = f.read()
            try:
                ret = replace_in_file.main(test_file, r'([a-z ])', r'\1', options)
                self.assertEquals(ret, 0)

                with open(test_file, "rb") as f:
                    new_contents = f.read()

                #emulated = []
                #for c in prev_contents:
                #    if ord(c) < 128 and c != "\0":
                #        emulated.append("-" + c)
                #    else:
                #        emulated.append(c)
                #emulated = "".join(emulated)

                self.assertEquals(prev_contents, new_contents)

            finally:
                with open(test_file, "wb") as f:
                    f.write(prev_contents)

    def test_replacing_noerr_false(self):
        options = DummyOptions()
        #options.noerr = True
        test_file = os.path.join(
            TEST_FILES_PATH, 'replace_in_file_test_ansi.txt')
        ret = replace_in_file.main(
            test_file, 'not found', r'doesnt matter', options)
        self.assertEquals(ret, 40)

    def test_ansi_encoding(self):
        options = DummyOptions()
        options.encoding = "mbcs"
        test_file = os.path.join(
            TEST_FILES_PATH, 'replace_in_file_test_ansi.txt')

        with open(test_file, "rb") as f:
            prev_contents = f.read()
        try:
            ret = replace_in_file.main(
                test_file, 'a', 'b', options)
            self.assertEquals(ret, 0)
        finally:
            with open(test_file, "wb") as f:
                f.write(prev_contents)


if __name__ == "__main__":
    unittest.main()
