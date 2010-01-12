import unittest
import os

import sys
sys.path.append(".")
sys.path.append("..")

from betterbatch import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")
COMMANDS_YAML = os.path.join(TEST_FILES_PATH, "commands.yaml")


class MainTests(unittest.TestCase):
    "Unit tests for the loadconfig function"

    def test_Main_none(self):
        """"""
        Main()

#    def test_Main_list(self):
#        """"""
#        sys.argv = ['main.py', "--list", COMMANDS_YAML]
#        Main()

    def test_Main_execute(self):
        """"""
        sys.argv = ['main.py', COMMANDS_YAML]
        Main()

    def test_Main_execute_fail(self):
        """"""
        sys.argv = [
            'main.py', os.path.join(TEST_FILES_PATH, "commands_broken.yaml")]
        self.assertRaises(
            ErrorCollection,
            Main)

    def test_Main_execute_fail2(self):
        """"""
        sys.argv = [
            'main.py', os.path.join(TEST_FILES_PATH, "commands_broken2.yaml")]

        self.assertRaises(
            ErrorCollection,
            Main)

    def test_Main_LogFile(self):
        """"""
        sys.argv = ['main.py', os.path.join(TEST_FILES_PATH, "logfile.yaml")]
        Main()

    def test_Main_verbose(self):
        """"""
        sys.argv = [
            'main.py', os.path.join(TEST_FILES_PATH, "logfile.yaml"), "-v"]
        Main()

    def test_CreateLogger(self):
        """"""
        log = CreateLogger()

    def test_ErrorCollection_LOGErrors(self):
        """"""
        errs = [
            'err1',
            "err1",
            "err2",
            "err3", ]

        collection = ErrorCollection(errs)
        collection.LogErrors()

        errs += [
            UndefinedVariableError("var", "yo"),
            UndefinedVariableError("var", "yo2"),
            UndefinedVariableError("var", "yo2"),
            UndefinedVariableError("var2", "yo"),
            ]

        collection = ErrorCollection(errs)
        collection.LogErrors()


    def test_SetUpLogFile_exists_cannot_del(self):
        """"""
        import tempfile
        handle, filename = tempfile.mkstemp()
        os.write(handle ,'sdf')
        self.assertRaises(
            OSError,
            SetupLogFile,
                {'logfile': filename})
                
        os.close(handle)
        os.remove(filename)

    #def test_SetUpLogFile_exists(self):
    #    """"""
    #    import tempfile
    #    handle, filename = tempfile.mkstemp()
    #    os.write(handle ,'sdf')
    #    os.close(handle)
    #    handle =  None
    #    f = open(filename, "w")
    #    f.close()
    #    import time
    #    time.sleep(1)
    #    h = SetupLogFile({'logfile': filename})
    #    LOG.info("some info")
    #    h.flush()

    #     os.remove(filename)


if __name__ == "__main__":
    unittest.main()
