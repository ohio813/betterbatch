from __future__ import absolute_import

import unittest
import os
import sys
import logging
import glob

TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_FILES_PATH = os.path.join(TESTS_DIR, "test_files")

# ensure that the package root is on the path
PACKAGE_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.append(PACKAGE_ROOT)

from betterbatch import parsescript
from betterbatch.parsescript import *


class Issue_tests(unittest.TestCase):

    def test_issue1(self):
        """Test that a variable can be updated in a for loop"""
        full_path = os.path.join(TEST_FILES_PATH, 'issue1.bb')
        steps, vars = ExecuteScriptFile(full_path, {})

        self.assertEquals(
            len(steps[-1].output.split("+")) > 5,
            True)

    def test_distribution_list_Yuhui(self):
        """Test that a missing tools directory does not raise a problem"""

        # this is not so easy to test, I don't particulary want to rename
        # the folder on my machine - and would like that "add_tools_dir" still
        # raises an error when the folder doesn't exist.
        # so for now this test doesn't do anything :(
        #
        # The issue was fixed by testing that the tools folder exists before
        # calling PopulateFromToolsFolder
        pass



if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("test_issues")
    # needs to be called before importing the modules
    import coverage
    cov = coverage.coverage(branch = True)
    cov.start()
    unittest.TextTestRunner(verbosity=1).run(suite)
    cov.stop()
    print cov.report([parsescript])
