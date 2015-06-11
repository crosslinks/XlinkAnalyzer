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
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        cPath = 'Rvb12/Rvb12.json'
        super(TestMover, self).setUp(mPaths, cPath)

    def testMover(self):
        m = xla.get_gui().Components.mover
        m.mode = xmove.COMPONENT_MOVEMENT

        self.assertEqual('move component', m.mode)

        # xla.get_gui().Components.modelSelect.selection_set(0)
        # xla.get_gui().Components.modelSelect.setvalue(chimera.openModels.list())
        name = 'Rvb1'
        # xla.activateByName(name)
        xla.activateByName(name, 'A')
        #move around, should move
