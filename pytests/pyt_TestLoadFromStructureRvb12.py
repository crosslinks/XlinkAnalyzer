import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestRvb12(XlaGuiTests.TestLoadFromStructure):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        super(TestRvb12, self).setUp(mPaths)

    def testRvb12(self):
        pass
