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


        self.assertEqual(14, len(self.g.configFrame.config.subunits))
        self.assertEqual(1, len(self.g.configFrame.config.subcomplexes))
        self.assertEqual(1, len(self.g.configFrame.config.domains))
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

    def testDeleteStuff(self):
        subUnitFrame = self.g.configFrame.subUnitFrame
        self.assertEqual(14, len(subUnitFrame.frames))
        self.assertEqual(14, len(self.g.configFrame.config.subunits))
        subUnitFrame.frames[0].delete.invoke()
        # self.assertEqual(13, len(subUnitFrame.frames))
        self.assertEqual(13, len(self.g.configFrame.config.subunits))

        dataFrame = self.g.configFrame.dataFrame
        self.assertEqual(10, len(dataFrame.frames))
        self.assertEqual(10, len(self.g.configFrame.config.dataItems))
        dataFrame.frames[0].delete.invoke()
        # self.assertEqual(9, len(dataFrame.frames))
        self.assertEqual(9, len(self.g.configFrame.config.dataItems))


    def testDeleteStuffSubcomplexes(self):
        self.g.configFrame.subCompButton.invoke()
        subWind = self._getSubcomplexesWindow()
        self.assertIsNotNone(subWind)

        self.assertEqual(1, len(subWind.winfo_children()))
        itemList = subWind.winfo_children()[0]
        itemList.frames[0].delete.invoke()
        self.assertEqual(0, len(self.g.configFrame.config.subcomplexes))

    def testDeleteStuffDomains(self):
        self.g.configFrame.domainsButton.invoke()
        domWind = self._getDomainsWindow()
        self.assertIsNotNone(domWind)

        self.assertEqual(1, len(domWind.winfo_children()))
        itemList = domWind.winfo_children()[0]
        itemList.frames[0].delete.invoke()
        self.assertEqual(0, len(self.g.configFrame.config.domains))

    def _getSubcomplexesWindow(self):
        c = self.g.configFrame
        for child in c.winfo_children():
            if hasattr(child, 'title'):
                if child.title() == 'Subcomplexes':
                    return child

    def _getDomainsWindow(self):
        c = self.g.configFrame
        for child in c.winfo_children():
            if hasattr(child, 'title'):
                if child.title() == 'Domains':
                    return child

    def tearDown(self):
        rc('close #0')