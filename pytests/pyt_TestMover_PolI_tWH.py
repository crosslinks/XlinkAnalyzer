import chimera

import XlaGuiTests

import xlinkanalyzer as xla
from xlinkanalyzer import move as xmove

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestMover(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['PolI/4C3H_with_wHTH_start.pdb']
        cPath = 'PolI/PolI_with_domains.json'
        super(TestMover, self).setUp(mPaths, cPath)

    def testMover(self):
        m = xla.get_gui().Components.table.mover

        self.assertEqual('move component', m.mode)

        name = 'A49-tWH'
        xla.activateByName(name)
        #move around, should move
