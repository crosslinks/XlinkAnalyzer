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
        mPaths = ['PolI/4C3H.pdb']
        cPath = 'PolI/PolI_components.json'
        super(TestMover, self).setUp(mPaths, cPath)

    def testMover(self):
        m = xla.get_gui().Subunits.table.mover

        self.assertEqual('move component', m.mode)

        # name = 'A190'
        name = 'testdom'
        # name = 'testsubcomplex'
        xla.activateByName(name)
        #move around, should move
