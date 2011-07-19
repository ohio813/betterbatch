from __future__ import absolute_import

import unittest
import os
import sys
import ConfigParser


TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

TOOLS_FOLDER = os.path.abspath(os.path.join(
    os.path.dirname(TESTS_DIR), 'tools'))
FILE_UNDER_TEST = os.path.join(TOOLS_FOLDER, 'get_ini_option.py')
sys.path.append(TOOLS_FOLDER)

import get_config_option


class GetConfigOptionTest(unittest.TestCase):
    "Perform some simple tests on get_config_option"

    def test_no_args(self):
        "Test with no args"
        ret = os.system(FILE_UNDER_TEST)
        self.assertEquals(ret, 1)

    def test_invalid_ini_file(self):
        "Test with invalid ini file"
        self.assertRaises(
            get_config_option.IniFileNotFoundError,
            get_config_option.get_value_from_ini_file,
            "invalid.ini",
            "deu",
            "x86_ISO")

    def test_main_invalid_ini_file(self):
        "Test main() with invalid ini file"
        ret = get_config_option.main(
                    "invalid.ini",
                    "deu",
                    "x86_ISO")
        self.assertEquals(ret, -4)

    def test_invalid_section(self):
        "Test with invalid section"
        self.assertRaises(
            ConfigParser.NoSectionError,
            get_config_option.get_value_from_ini_file,
            TEST_FILES_PATH+"\get_config_option.ini",
            "invalid_section",
            "x86_ISO")

    def test_main_invalid_section(self):
        "Test main() with invalid section"
        ret = get_config_option.main(
                    TEST_FILES_PATH+"\get_config_option.ini",
                    "invalid_section",
                    "x86_ISO")
        self.assertEquals(ret, -2)

    def test_invalid_value(self):
        "Test with invalid value"
        self.assertRaises(
            ConfigParser.NoOptionError,
            get_config_option.get_value_from_ini_file,
            TEST_FILES_PATH+"\get_config_option.ini",
            "deu",
            "invalid_value")

    def test_main_invalid_value(self):
        "Test main() with invalid value"
        ret = get_config_option.main(
                    TEST_FILES_PATH+"\get_config_option.ini",
                    "deu",
                    "invalid_value")
        self.assertEquals(ret, -1)

    def test_more_than_1_matches(self):
        "Test with wildcard with more than 1 matches"
        self.assertRaises(
            get_config_option.WildCardError,
            get_config_option.get_value_from_ini_file,
            TEST_FILES_PATH+"\get_config_option.ini",
            "16.0.56*",
            "x86_ISO")

    def test_main_more_than_1_matches(self):
        "Test main() with wildcard with more than 1 matches"
        ret = get_config_option.main(
                    TEST_FILES_PATH+"\get_config_option.ini",
                    "16.0.56*",
                    "x86_ISO")
        self.assertEquals(ret, -3)

    def test_valid_result(self):
        "Test with correct arguments"
        ret = get_config_option.get_value_from_ini_file(
                TEST_FILES_PATH+"\get_config_option.ini",
                "deu",
                "x86_iso")
        self.assertEquals(ret, "valid_return")

    def test_main_valid_result(self):
        "Test main() with correct arguments"
        ret = get_config_option.main(
                TEST_FILES_PATH+"\get_config_option.ini",
                "deu",
                "x86_iso")
        self.assertEquals(ret, 0)

    def test_wildcard(self):
        "Test with correct wildcard arguments"
        ret = get_config_option.get_value_from_ini_file(
                TEST_FILES_PATH+"\get_config_option.ini",
                "de*",
                "x86_iso")
        self.assertEquals(ret, "valid_return")

    def test_main_wildcard(self):
        "Test main() with correct wildcard arguments"
        ret = get_config_option.main(
                TEST_FILES_PATH+"\get_config_option.ini",
                "de*",
                "x86_iso")
        self.assertEquals(ret, 0)


if __name__ == "__main__":
    unittest.main()