from __future__ import absolute_import

import os
import sys
import coverage
import unittest

# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(package_root)
sys.path.append(os.path.join(package_root, "betterbatch\\tools"))

# needs to be called before importing the modules
cov = coverage.coverage(branch = True)
cov.start()

from betterbatch import cmd_line
from betterbatch import built_in_commands
from betterbatch import parsescript
from betterbatch import compare
import replace_in_file

modules_to_test = [
    cmd_line, built_in_commands, parsescript, compare, replace_in_file]

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
        directory = os.path.join(package_root, "Coverage_report"))

if __name__ == '__main__':
    run_tests()
