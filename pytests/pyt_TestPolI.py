import chimera

import XlaGuiTests

import xlinkanalyzer as xla

from chimera import runCommand as rc

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestPolI(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['PolI/4C3H.pdb']
        cPath = 'PolI/PolI_components.json'
        super(TestPolI, self).setUp(mPaths, cPath)

        ms = xla.get_gui().Subunits.table.modelSelect
        m = chimera.openModels.list()[0]
        ms.setvalue([m])

        self.g = xla.get_gui()

        self.g.modelSelect.doSync(ms)

    def testPolI(self):
        xFrame = self.g.Xlinks

        xFrame.displayDefault()

        self.assertEqual(1, len(xFrame.getXlinkDataMgrs()))

        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(171, len(xmgr.pbg.pseudoBonds))

        xFrame.ld_score_var.set(30.0)

        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(106, displayed)

        #just test open windows
        self.g.configFrame.domainsButton.invoke()
        self.g.configFrame.subCompButton.invoke()

    def testDeleteStuff(self):
        subUnitFrame = self.g.configFrame.subUnitFrame
        self.assertEqual(14, len(subUnitFrame.frames))
        self.assertEqual(14, len(g.configFrame.config.subunits))
        subUnitFrame.frames[0].onDelete()
        self.assertEqual(13, len(subUnitFrame.frames))
        self.assertEqual(13, len(g.configFrame.config.subunits))

        dataFrame = self.g.configFrame.dataFrame
        self.assertEqual(10, len(dataFrame.frames))
        self.assertEqual(10, len(g.configFrame.config.dataItems))
        dataFrame.frames[0].onDelete()
        self.assertEqual(9, len(dataFrame.frames))
        self.assertEqual(9, len(g.configFrame.config.dataItems))

    def tearDown(self):
        rc('close #0')