import TestSuiteExt
import TestSuiteExt.cmd
import sys
import os

TestSuiteExt.testdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
testfilename = sys.argv[-1][4:]
TestSuiteExt.cmd.testsuite(None, 'run {0}'.format(testfilename))
