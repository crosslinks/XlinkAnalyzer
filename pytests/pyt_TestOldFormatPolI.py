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

        ms = xla.get_gui().Subunits.table.modelSelect
        m = chimera.openModels.list()[0]
        ms.setvalue([m])

        self.g = xla.get_gui()

        self.g.modelSelect.doSync(ms)

    def testPolI(self):
        xFrame = self.g.Xlinks

        xFrame.displayDefault()

        self.assertEqual(14, len(self.g.configFrame.config.subunits))
        self.assertEqual(0, len(self.g.configFrame.config.subcomplexes))
        self.assertEqual(0, len(self.g.configFrame.config.domains))
        self.assertEqual(10, len(self.g.configFrame.config.dataItems))
        self.assertSetEqual(set([u'A190', u'A135', u'AC40', u'A14', u'ABC27', u'ABC23', u'A43', u'ABC14.5', u'A12', u'ABC10beta', u'AC19', u'ABC10alpha', u'A49', u'A34.5']),
            set(self.g.configFrame.config.getSubunitNames()))

        self.assertEqual(1, len(xFrame.getXlinkDataMgrs()))

        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(171, len(xmgr.pbg.pseudoBonds))

        xFrame.ld_score_var.set(30.0)

        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(106, displayed)

        #just test open windows
        self.g.configFrame.domainsButton.invoke()
        self.g.configFrame.subCompButton.invoke()