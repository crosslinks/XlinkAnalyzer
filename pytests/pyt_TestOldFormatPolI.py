import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestPolI(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['PolI/4C3H.pdb']
        cPath = 'PolI/PolI_old_format.json'
        super(TestPolI, self).setUp(mPaths, cPath)

    def testPolI(self):
        ms = xla.get_gui().Subunits.table.modelSelect
        m = chimera.openModels.list()[0]
        ms.setvalue([m])

        g = xla.get_gui()

        g.modelSelect.doSync(ms)

        xFrame = g.Xlinks

        xFrame.displayDefault()

        self.assertEqual(1, len(xFrame.getXlinkDataMgrs()))

        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(171, len(xmgr.pbg.pseudoBonds))

        xFrame.ld_score_var.set(30.0)

        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(106, displayed)

        #just test open windows
        g.configFrame.domainsButton.invoke()
        g.configFrame.subCompButton.invoke()