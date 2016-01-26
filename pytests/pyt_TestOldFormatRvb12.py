import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# ln -s [full path]/pyt_TestExample.py [Chimeradir]/test/pytests/pyt_[Name].py
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>

RUNME = True

description = "Tests gui class"


class TestXla_Rvb12_old_format(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        cPath = 'Rvb12/Rvb12_old_format.json'
        super(TestXla_Rvb12_old_format, self).setUp(mPaths, cPath)

    def testLoad(self):
        ms = xla.get_gui().Subunits.table.modelSelect
        m = chimera.openModels.list()[0]
        ms.setvalue([m])

        g = xla.get_gui()

        g.modelSelect.doSync(ms)

        xFrame = g.Xlinks

        xFrame.displayDefault()

        self.assertEqual(1, len(xFrame.getXlinkDataMgrs()))

        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(216, len(xmgr.pbg.pseudoBonds))

        xFrame.ld_score_var.set(30.0)


        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(162, displayed)