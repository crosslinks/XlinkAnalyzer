import chimera

import XlaGuiTests

import xlinkanalyzer as xla
from xlinkanalyzer import move as xmove
from xlinkanalyzer import symmove

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestMover(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        cPath = 'Rvb12/Rvb12.json'
        super(TestMover, self).setUp(mPaths, cPath)

    def testMover(self):
        m = xla.get_gui().Components.mover

        self.assertEqual('move component', m.mode)

        name = 'Rvb1'
        # xla.activateByName(name)
        xla.activateByName(name, 'C')
        # xla.activateByName(name, ['A', 'C'])
        #move around, should move
        symmover = symmove.SymMover()
        symmover.activate()
