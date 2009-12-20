import test_loadconfig
import test_variables
import coverage
import unittest

import os.path
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import test_config
import cmd_line
import built_in_commands
modules_to_test = [test_config, cmd_line, built_in_commands]

excludes = []
def run_tests():
    
    suite = unittest.TestSuite()
    testfolder = os.path.abspath(os.path.dirname(__file__))

    sys.path.append(testfolder)

    for root, dirs, files in os.walk(testfolder):
        test_modules = [
            file.replace('.py', '') for file in files if
                file.startswith('test_') and
                file.endswith('.py')]

        test_modules = [mod for mod in test_modules if mod.lower() not in excludes]
        for mod in test_modules:

            #globals().update(__import__(mod, globals(), locals()).__dict__)
            # import it
            imported_mod = __import__(mod, globals(), locals())
            
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(imported_mod))
            
            #print imported_mod.__dict__
            #globals().update(imported_mod.__dict__)




    #runner = unittest.TextTestRunner(verbosity = 2)
    cov = coverage.coverage()
    cov.start()
    unittest.TextTestRunner(verbosity=1).run(suite)
    cov.stop()
    #print cov.analysis()
    print cov.report(modules_to_test)

if __name__ == '__main__':
    run_tests()