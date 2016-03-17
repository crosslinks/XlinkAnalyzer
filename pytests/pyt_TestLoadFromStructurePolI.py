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

        ms = xla.get_gui().Subunits.table.modelSelect
        m = chimera.openModels.list()[0]
        ms.setvalue([m])

        self.g = xla.get_gui()

        self.g.modelSelect.doSync(ms)

    def testPolI(self):
        self.assertEqual(14, len(self.g.configFrame.config.subunits))
