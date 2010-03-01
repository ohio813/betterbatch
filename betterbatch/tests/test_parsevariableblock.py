import unittest
import os
import glob

import sys
# ensure that the package root is on the path
package_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(package_root)

from parsescript import *

TEST_PATH = os.path.dirname(__file__)
TEST_FILES_PATH = os.path.join(TEST_PATH, "test_files")


class ParseVariableBlockTests(unittest.TestCase):
    "Unit tests for the commands"

    def test_empty_var_block(self):
        self.assertEquals(ParseVariableBlock({}, 'this_file'), {})
    
    def test_list_var_block(self):
        block = [
            {'var': "value"},
            {'var2': "value2"}]
        self.assertEquals(
            ParseVariableBlock(block, 'this_file'), 
            {'var': "value", 'var2': "value2"})

    def test_list_var_block_error(self):
        block = ["string",]
        self.assertRaises(
            RuntimeError,
            ParseVariableBlock,
                block, 'this_file')


if __name__ == "__main__":
    unittest.main()
