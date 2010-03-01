import unittest
import os
import logging
import glob

import sys
# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(package_root)

import parsescript
from parsescript import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


class Issue_tests(unittest.TestCase):

    def test_issue1(self):
        """"""
        full_path = os.path.join(TEST_FILES_PATH, 'issue1.bb')
        steps = ExecuteScriptFile(full_path, {})
        
        self.assertEquals(
            len(steps[-1].output.split("+")) > 5,
            True)
            


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromName("test_issues")
    # needs to be called before importing the modules
    import coverage
    cov = coverage.coverage(branch = True)
    cov.start()
    unittest.TextTestRunner(verbosity=1).run(suite)
    cov.stop()
    print cov.report([parsescript])
