import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class Test4A8J(XlaGuiTests.TestLoadFromStructure):

    def setUp(self):
        mPaths = ['4A8J/4A8J.cif']
        super(Test4A8J, self).setUp(mPaths)

    def testThis(self):
        pass
