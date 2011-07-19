from __future__ import absolute_import

import unittest
import os
import sys

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

# ensure that the package root is on the path
PACKAGE_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.append(PACKAGE_ROOT)

from betterbatch import built_in_commands
from betterbatch.built_in_commands import *
from betterbatch import parsescript
parsescript.LOG = parsescript.ConfigLogging()


class BuiltInCommandsTests(unittest.TestCase):
    "Unit tests for the built in commands"

    def test_PathExists_true(self):
        """"""

        self.assertEquals(
            PathExists(__file__)[0], 0)

    def test_PathExists_false(self):
        """"""

        ret, out = PathExists("does not exist.blah")
        self.assertNotEquals(ret ,0)

    def test_PathNotExists_true(self):
        """"""

        self.assertEquals(
            PathNotExists("does not exist.blah")[0], 0)

    def test_PathNotExists_false(self):
        """"""

        self.assertNotEquals(PathNotExists(__file__), 0)


    def test_count_passes(self):
        """"""
        test_file = os.path.join(TESTS_DIR, "run_tests.py")
        VerifyFileCount(test_file, [1])
        VerifyFileCount(test_file, 1)
        VerifyFileCount(test_file, ">0")
        VerifyFileCount(test_file, "<2")
        VerifyFileCount(test_file, ">=1")
        VerifyFileCount(test_file, "<=1")
        VerifyFileCount(test_file, "=1")

    def test_count_fail(self):
        """"""

        ret, out = VerifyFileCount("cmd_line.py", 12)
        self.assertNotEquals(ret, 0)


    def test_missing_count(self):
        self.assertRaises(
            RuntimeError,
            VerifyFileCount,
            "cmd_line.py")

    def test_SystemCommand_ui(self):
        SystemCommand("echo here", ['ui'])

    def test_SystemCommand_no_ui(self):
        SystemCommand("echo here", [])

    def test_SystemCommand_nocapture(self):
        SystemCommand("echo here",  ['nocapture'])

    def test_SystemCommand_echo(self):
        SystemCommand("echo here",  ['echo'])

    def test_SystemCommand_echo_nocapture(self):
        SystemCommand("echo here",  ['echo', 'nocapture'])

    def test_SystemCommand_no_too_long(self):
        self.assertRaises(
            RuntimeError,
            SystemCommand,
                "echo here" + "888" * 4000, [])

    def test_SystemCommand_with_spaces(self):
        ret = SystemCommand(
            '"c:\Program Files\Common Files\Microsoft Shared\DW\DW20.EXE"', [])
        self.assertEqual(ret, (0, ''))

        ret = SystemCommand(
            '"c:\Program Files\Common Files\Microsoft Shared\DW\DW20.EXE" "test here"', [])
        self.assertEqual(ret, (0, ''))


    def test_dirname(self):
        self.assertEquals(dirname(r"c:\tes\temp\here.txt"), (0, r"c:\tes\temp"))

    def test_basename(self):
        self.assertEquals(basename(r"c:\tes\temp\here.txt"), (0, r"here.txt"))

    def test_ChangeCurrentDirectory_pass(self):
        """"""
        cur_dir = os.path.abspath(os.getcwd())

        ret, out = ChangeCurrentDirectory("\\")

        self.assertEquals((ret, out), (0, ""))
        self.assertEquals(os.getcwd(), os.path.abspath("\\"))

        # change it back
        ChangeCurrentDirectory(cur_dir)

    def test_ChangeCurrentDirectory_quotes(self):
        """Check that it can ignore leading/trailing quotes"""
        cur_dir = os.path.abspath(os.getcwd())
        ret, out = ChangeCurrentDirectory('"\\"')

        self.assertEquals((ret, out), (0, ""))
        self.assertEquals(os.getcwd(), os.path.abspath("\\"))

        # change it back
        ChangeCurrentDirectory(cur_dir)

    def test_ChangeCurrentDirectory_fail(self):
        """Test the "cd" command that will fail"""
        cur_dir = os.path.abspath(os.getcwd())

        ret, out = ChangeCurrentDirectory("\\non_existing_directory_somewhere")

        self.assertNotEquals(ret, 0)
        self.assertEquals(os.getcwd(), cur_dir)

    def test_ChangeCurrentDirectory_list(self):
        """Test the "cd" command that will fail"""
        cur_dir = os.path.abspath(os.getcwd())

        ret, out = ChangeCurrentDirectory(["\\"])

        self.assertEquals(ret, 0)
        self.assertEquals(os.path.splitdrive(os.getcwd())[1], "\\" )
        os.chdir(cur_dir)

    def test_PushDirectory_pass(self):
        cur_dir = os.path.abspath(os.getcwd())

        ret, out = PushDirectory("\\")

        self.assertEquals((ret, out), (0, ""))
        self.assertEquals(os.getcwd(), os.path.abspath("\\"))

        # change it back
        PopDirectory()

    def test_PushDirectory_fail(self):
        """Try to push a directory that doesn't exist"""
        cur_dir = os.path.abspath(os.getcwd())

        ret, out = PushDirectory("\\non_existing_directory_somewhere")

        self.assertNotEquals((ret, out), (0, ""))
        self.assertEquals(os.getcwd(), cur_dir)

    def test_PushDirectory_quotes(self):
        """Check that it can ignore leading/trailing quotes"""
        cur_dir = os.path.abspath(os.getcwd())
        ret, out = PushDirectory('"\\"')

        self.assertEquals((ret, out), (0, ""))
        self.assertEquals(os.getcwd(), os.path.abspath("\\"))

        # change it back
        PopDirectory()

    def test_PopDirectory_pass(self):
        cur_dir = os.path.abspath(os.getcwd())
        PushDirectory("\\")
        self.assertEquals(os.getcwd(), os.path.abspath("\\"))
        ret, out = PopDirectory()
        self.assertEquals(ret, 0)
        self.assertEquals(os.getcwd(), cur_dir)

    def test_PopDirectory_fail(self):
        self.assertRaises(
            RuntimeError,
            PopDirectory)

        PushDirectory("\\")
        PushDirectory("\\")
        PopDirectory()
        PopDirectory()

        self.assertRaises(
            RuntimeError,
            PopDirectory)

    def test_PopDirectory_fail2(self):
        # simulate that a directory stored (in a PushDirectory call) has
        # been removed since

        built_in_commands.PUSH_DIRECTORY_LIST.append("not_here_at_all")
        cur_dir = os.getcwd()

        ret, out = PopDirectory()

        self.assertNotEquals(ret, 0)
        self.assertEquals(cur_dir, os.getcwd())

    def test_ExternalCommand_pass(self):
        tool_path = os.path.join(PACKAGE_ROOT, "betterbatch\\tools", "GetLanguage.py")
        ec = ExternalCommand(tool_path)

        #print tool_path
        #print ec(["a", "=", "A", "nocase"])

        expected_ret = (0, 'de-DE\r\n')
        self.assertEquals(ec("deu  dotnet"), expected_ret)
        self.assertEquals(ec("deu dotnet", ["nocase"]), expected_ret)
        self.assertRaises(
            RuntimeError,
            ec,
                ("a", "=", "A", "nocase"))
        self.assertRaises(
            RuntimeError,
            ec,
                ["a", "=", "A"], ["nocase"])

    def test_ExternalCommand_missing_cmd(self):
        """Test external path with tool that doesn't exitst"""

        tool_path = os.path.join(PACKAGE_ROOT, "betterbatch\\tools", "compare_not_here.py")
        self.assertRaises(
            RuntimeError,
            ExternalCommand,
                tool_path)

    def test_ExternalCommand_fail2(self):
        "   "
        tool_path = os.path.join(PACKAGE_ROOT, "betterbatch\\tools", "getlanguage.py")
        ec = ExternalCommand(tool_path)

        self.assertRaises(
            RuntimeError,
            ec,
                None)

    def test_ExternalCommand_qualifier(self):
        """All qualifiers were being passed to external tools as arguments

        so we need to validate that only 'non-standard' qualifiers are passed
        as args, and standard qualifiers are passed as qualifers.
        """
        tool_path = os.path.join(PACKAGE_ROOT, "betterbatch\\tools", "getlanguage.py")

        ec = ExternalCommand(tool_path)

        #let's try a bit of monkey patching ;)
        old_SystemCommand = built_in_commands.SystemCommand
        built_in_commands.SystemCommand = lambda cmd, quals: (cmd, quals)
        cmd, quals = ec("my_command", ['ui', 'test'])
        self.assertEquals(quals, ['ui'])
        self.assertEquals(cmd, "%s my_command test" % tool_path)

        built_in_commands.SystemCommand = old_SystemCommand

    def test_PopulateFromToolsFolder_pass(self):
        old_mapping = built_in_commands.NAME_ACTION_MAPPING.copy()
        tools_dir = os.path.join(PACKAGE_ROOT, "tools")
        PopulateFromToolsFolder(PACKAGE_ROOT)
        built_in_commands.NAME_ACTION_MAPPING = old_mapping

    def test_PopulateFromToolsFolder_duplicate(self):
        old_mapping = built_in_commands.NAME_ACTION_MAPPING.copy()
        tools_dir = os.path.join(PACKAGE_ROOT, "tools")
        try:
            PopulateFromToolsFolder(PACKAGE_ROOT)
            PopulateFromToolsFolder(PACKAGE_ROOT)
        finally:
            built_in_commands.NAME_ACTION_MAPPING = old_mapping

    def test_PopulateFromToolsFolder_fail(self):
        tools_dir = os.path.join(PACKAGE_ROOT, "betterbatch\\tools")
        old_mapping = built_in_commands.NAME_ACTION_MAPPING.copy()

        compare_func = built_in_commands.NAME_ACTION_MAPPING['compare']
        try:
            built_in_commands.NAME_ACTION_MAPPING['replace_in_file'] = lambda x=1, y=1: (0,"")
            self.assertRaises(
                RuntimeError,
                PopulateFromToolsFolder,
                    tools_dir)
        finally:
            built_in_commands.NAME_ACTION_MAPPING['compare'] = compare_func
            built_in_commands.NAME_ACTION_MAPPING = old_mapping

    def test_Split_no_split_text(self):
        self.assertEquals(Split("1 2"), (0, "1\n2"))

    def test_Split_split_text(self):
        self.assertEquals(Split("1\n2", "\n"), (0, "1\n2"))

    def test_Replace_basic(self):
        self.assertEquals(Replace("some text", ["e", "a"]), (0, "soma taxt"))

    def test_Replace_ParseQualifiers_making_qualifiers_lowercase(self):
        """ParseQualifiers was making all qualifiers lowercase
        So replacement text was being passed to replace as lowercase text
        """
        s = parsescript.ParseStep("replace InPut {*In*} {*OuT*}")
        s.execute({}, 'run')
        self.assertEqual(s.output, "OuTPut")

    def test_Replace_case_unmatching(self):
        s = parsescript.ParseStep("replace InPut {*in*} {*OuT*}")
        s.execute({}, 'run')
        self.assertEqual(s.output, "InPut")

    def test_Replace_ignore_case(self):
        s = parsescript.ParseStep("replace InPut {*in*} {*OuT*} {*nocase*}")
        s.execute({}, 'run')
        self.assertEqual(s.output, "OuTPut")

    def test_EscapeNewLines_basic(self):
        self.assertEquals(EscapeNewlines("some\ntext"), (0, r"some\\ntext"))

    def test_uppercase(self):
        self.assertEquals(UpperCase("Some\nTexT"), (0, "SOME\nTEXT"))

    def test_lowercase(self):
        self.assertEquals(LowerCase("Some\nTexT"), (0, "some\ntext"))

    def test_compare_equal(self):
        self.assertEquals(Compare("a = a"), (0, ""))
        self.assertEquals(Compare("a = A"), (1, ""))
        self.assertEquals(Compare("a = A", ['nocase']), (0, ""))

        self.assertEquals(Compare("099 = 99", ['asint']), (0, ""))
        self.assertEquals(Compare("099 = 99", ), (1, ""))

    def test_compare_broken(self):
        self.assertRaises(
            RuntimeError,
            Compare,
                "a = =  a")

    def test_compare_ge(self):
        self.assertEquals(Compare("1 >= 1"), (0, ""))
        self.assertEquals(Compare("1 >= 2"), (1, ""))

    def test_compare_gt(self):
        self.assertEquals(Compare("a > a"), (1, ""))
        self.assertEquals(Compare("a > A"), (0, ""))

    def test_compare_le(self):
        self.assertEquals(Compare("a <= a"), (0, ""))
        self.assertEquals(Compare("a <= A"), (1, ""))

    def test_compare_lt(self):
        self.assertEquals(Compare("a < a"), (1, ""))
        self.assertEquals(Compare("A < a"), (0, ""))

    def test_compare_eq(self):
        self.assertEquals(Compare("a = a"), (0, ""))
        self.assertEquals(Compare("a == a"), (0, ""))
        self.assertEquals(Compare("A = a"), (1, ""))

    def test_compare_ne(self):
        self.assertEquals(Compare("a != a"), (1, ""))
        self.assertEquals(Compare("a != A"), (0, ""))

    def test_compare_startswith(self):
        self.assertEquals(Compare("abc startswith ab"), (0, ""))
        self.assertEquals(Compare("abc startswith bc"), (1, ""))

    def test_compare_endswith(self):
        self.assertEquals(Compare("abc endswith ab"), (1, ""))
        self.assertEquals(Compare("abc endswith bc"), (0, ""))

    def test_compare_contains(self):
        self.assertEquals(Compare("abc contains x"), (1, ""))
        self.assertEquals(Compare("abc contains abc"), (0, ""))

    def test_compare_matchesregex(self):
        self.assertEquals(Compare("abc matches_regex ^a..$"), (0, ""))
        self.assertEquals(Compare("abc matches_regex ^z.*$"), (1, ""))

    def test_compare_unknown_op(self):
        self.assertRaises(
            RuntimeError,
            Compare,
                "abc blah ^a..$")

    def test_replace(self):
        self.assertEquals(
            Replace("here", ['e', 'b']),
            (0, 'hbrb'))

    def test_replace_nocase(self):
        self.assertEquals(
            Replace("hErE", ['e', 'b']),
            (0, 'hErE'))

        self.assertEquals(
            Replace("hErE", ['e', 'b', 'nocase']),
            (0, 'hbrb'))

    def test_replace_re(self):
        self.assertEquals(
            Replace("here", ['e(?!r)', 'b', 're']),
            (0, 'herb'))

    def test_replace_require(self):
        self.assertEquals(
            Replace("herf", ['require', 'f', 'b']),
            (0, 'herb'))

        self.assertRaises(
            RuntimeError,
            Replace,
                "here", ['f', 'b', 'require'])




if __name__ == "__main__":
    unittest.main()
