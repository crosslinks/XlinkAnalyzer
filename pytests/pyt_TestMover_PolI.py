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
        cPath = 'PolI/PolI.json'
        super(TestMover, self).setUp(mPaths, cPath)

    def testMover(self):
        m = xla.get_gui().Components.mover
        self.assertEqual('move normal', m.mode)
        self.assertEqual('move component', m.COMPONENT_MOVEMENT)

        m.mode = xmove.COMPONENT_MOVEMENT

        self.assertEqual('move component', m.mode)

        # from MoveSelection import Selection_Mover
        # from chimera import runCommand as rc
        # m.mode = Selection_Mover.MOVE_SELECTION
        # rc('select :.A')
        m.mode = xmove.COMPONENT_MOVEMENT
        #move around, should not move
