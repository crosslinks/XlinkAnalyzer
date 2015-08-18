import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestPolI(XlaGuiTests.TestLoadFromStructure):

    def setUp(self):
        mPaths = ['PolI/4C3H.pdb']
        super(TestPolI, self).setUp(mPaths)

    def testPolI(self):
        pass
