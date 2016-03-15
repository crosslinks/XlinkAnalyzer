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
        cPath = 'PolI/PolI_components.json'
        super(TestPolI, self).setUp(mPaths, cPath)

        ms = xla.get_gui().Subunits.table.modelSelect
        m = chimera.openModels.list()[0]
        ms.setvalue([m])

        self.g = xla.get_gui()

        self.g.modelSelect.doSync(ms)

    def testPolI_1(self):
        xFrame = self.g.Xlinks

        xFrame.displayDefault()

        self.assertEqual(1, len(xFrame.getXlinkDataMgrs()))

        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(171, len(xmgr.pbg.pseudoBonds))

        xFrame.ld_score_var.set(30.0)

        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(106, displayed)

        self._testThis()

        guiWin = self.g
        guiWin.configFrame.resMngr.loadAssembly(guiWin, self.xlaTestCPath)
        guiWin.configFrame.clear()
        guiWin.configFrame.update()
        guiWin.configFrame.mainWindow.setTitle(guiWin.configFrame.config.file)
        guiWin.configFrame.config.state = "unchanged"

        self.config = guiWin.configFrame.config

        self._testThis()

    def _testThis(self):
        self.g.configFrame.domainsButton.invoke()
        domWind = self.g.configFrame._getDomainsWindow()
        self.assertIsNotNone(domWind)
        itemList = domWind.winfo_children()[0]
        activeItemFrame = itemList.activeItemFrame

        from xlinkanalyzer.data import Subunit, Domain, Subcomplex
        self.assertEqual(len(self.config.subunits), len(activeItemFrame.data.config.getInstances(Subunit)))
        self.assertEqual(len(self.config.domains), len(activeItemFrame.data.config.getInstances(Domain)))
        self.assertEqual(len(self.config.subcomplexes), len(activeItemFrame.data.config.getInstances(Subcomplex)))

