import unittest
import os
import sys

# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(package_root)

from built_in_commands import *
import built_in_commands

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


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
        test_file = os.path.join(TEST_PATH, "run_tests.py")
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

    def test_SystemCommand_no_too_long(self):
        self.assertRaises(
            RuntimeError,
            SystemCommand,
                "echo here" + "888" * 4000, [])

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
        
        ret, out = PopDirectory()
        
        self.assertNotEquals(ret, 0)
        

    def test_ExternalCommand_pass(self):
        tool_path = os.path.join(package_root, "tools", "compare.py")
        ec = ExternalCommand(tool_path)
        
        expected_ret = (0, '')
        self.assertEquals(ec("a = A nocase"), expected_ret)
        self.assertEquals(ec("a = A", ["nocase"]), expected_ret)
        self.assertEquals(ec(["a", "=", "A", "nocase"]), expected_ret)
        self.assertEquals(ec(["a", "=", "A"], ["nocase"]), expected_ret)
            
    def test_ExternalCommand_missing_cmd(self):
        """Test external path with tool that doesn't exitst"""
        
        tool_path = os.path.join(package_root, "tools", "compare_not_here.py")
        self.assertRaises(
            RuntimeError,
            ExternalCommand,
                tool_path)

    def test_ExternalCommand_fail2(self):
        "   "
        tool_path = os.path.join(package_root, "tools", "compare.py")
        ec = ExternalCommand(tool_path)
        
        self.assertRaises(
            RuntimeError,
            ec,
                None)

    def test_PopulateFromToolsFolder_pass(self):
        tools_dir = os.path.join(package_root, "tools")
        PopulateFromToolsFolder(package_root)

    def test_PopulateFromToolsFolder_fail(self):
        tools_dir = os.path.join(package_root, "tools")

        built_in_commands.NAME_ACTION_MAPPING['compare'] = lambda x=1, y=1: (0,"")
        self.assertRaises(
            RuntimeError,
            PopulateFromToolsFolder,
                tools_dir)
        
        del(built_in_commands.NAME_ACTION_MAPPING['compare'])

    def test_Split_no_split_text(self):
        self.assertEquals(Split("1 2"), (0, ["1", "2"]))

    def test_Split_split_text(self):
        self.assertEquals(Split("1\n2", "\n"), (0, ["1", "2"]))

    def test_Replace_basic(self):
        self.assertEquals(Replace("some text", ["e", "a"]), (0, "soma taxt"))

    def test_EscapeNewLines_basic(self):
        self.assertEquals(EscapeNewlines("some\ntext"), (0, r"some\\ntext"))





if __name__ == "__main__":
    unittest.main()
