from __future__ import absolute_import

import unittest
import os
import sys
import coverage
TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

# ensure that the package root is on the path
PACKAGE_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.append(PACKAGE_ROOT)

sys.path.append(os.path.join(PACKAGE_ROOT, "betterbatch\\tools"))

# needs to be called before importing the modules
cov = coverage.coverage(branch = True)
cov.start()

from betterbatch import cmd_line
from betterbatch import built_in_commands
from betterbatch import parsescript
from betterbatch import compare
import replace_in_file
import get_config_option

modules_to_test = [
    cmd_line, built_in_commands, parsescript, compare,
    replace_in_file, get_config_option]

parsescript.LOG = parsescript.ConfigLogging()


def run_tests():
    excludes = []

    suite = unittest.TestSuite()
    testfolder = os.path.abspath(os.path.dirname(__file__))

    sys.path.append(testfolder)

    for root, dirs, files in os.walk(testfolder):
        test_modules = [
            file.replace('.py', '') for file in files if
                file.startswith('test_') and
                file.endswith('.py')]

        test_modules = [
            mod for mod in test_modules if mod.lower() not in excludes]
        print test_modules
        for mod in test_modules:

            #globals().update(__import__(mod, globals(), locals()).__dict__)
            # import it
            imported_mod = __import__(mod, globals(), locals())

            suite.addTests(
                unittest.defaultTestLoader.loadTestsFromModule(imported_mod))

    #runner = unittest.TextTestRunner(verbosity = 2)
    unittest.TextTestRunner(verbosity=1).run(suite)
    cov.stop()
    #print cov.analysis()
    print cov.report(modules_to_test)
    cov.html_report(
        modules_to_test,
        directory = os.path.join(PACKAGE_ROOT, "Coverage_report"))

if __name__ == '__main__':
    run_tests()
