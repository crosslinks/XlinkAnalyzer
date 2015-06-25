import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestRMF_PolI(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['PolI/4C3H_with_wHTH.rmf']
        cPath = 'PolI/PolI_components.json'
        super(TestRMF_PolI, self).setUp(mPaths, cPath)

    def testPolI(self):
        pass
