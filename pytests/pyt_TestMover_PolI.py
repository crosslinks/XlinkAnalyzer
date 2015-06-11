import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestMover(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['PolI/4C3H.pdb']
        cPath = 'PolI/PolI.json'
        super(TestMover, self).setUp(mPaths, cPath)

    def testMover(self):
        m = xla.get_gui().mover
        self.assertEqual('move normal', m.mode)

