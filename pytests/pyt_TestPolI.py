import os
import chimera
import unittest

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

        self.assertEqual(len(self.g.configFrame.config.subunits), len(self.g.configFrame.config.getSequences()))

        self.assertEqual(1, len(xFrame.getXlinkDataMgrs()))

        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(171, len(xmgr.pbg.pseudoBonds))

        xFrame.ld_score_var.set(30.0)

        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(106, displayed)

        #just test open windows
        self.g.configFrame.domainsButton.invoke()
        self.g.configFrame.subCompButton.invoke()

    @unittest.skip("Skip because it opens (itentionally) the error message that unittest cannot close.")
    def testAddDomainWrong(self):
        self.g.configFrame.domainsButton.invoke()
        domWind = self.g.configFrame._getDomainsWindow()
        self.assertIsNotNone(domWind)
        itemList = domWind.winfo_children()[0]
        self.assertEqual(1, len(self.g.configFrame.config.domains))
        self.assertEqual(1, len(itemList.frames))
        activeItemFrame = itemList.activeItemFrame
        activeItemFrame.add.invoke()

    def testAddDomainsSubcomplexes(self):
        self.g.configFrame.domainsButton.invoke()
        domWind = self.g.configFrame._getDomainsWindow()
        self.assertIsNotNone(domWind)
        itemList = domWind.winfo_children()[0]
        self.assertEqual(1, len(self.g.configFrame.config.domains))
        self.assertEqual(1, len(itemList.frames))
        activeItemFrame = itemList.activeItemFrame
        activeItemFrame.fields['name'][1].insert(0, 'testdom')
        activeItemFrame.fields['subunit'][3].set('A135')
        activeItemFrame.fields['ranges'][1].insert(0, '1-200')
        activeItemFrame.fields['color'][1].set(chimera.MaterialColor(0,255,0))
        activeItemFrame.add.invoke()

        self.assertEqual(2, len(self.g.configFrame.config.domains))
        self.assertEqual(2, len(itemList.frames))

        self.g.configFrame.subCompButton.invoke()
        subWind = self.g.configFrame._getSubcomplexesWindow()
        self.assertIsNotNone(subWind)

        itemList = subWind.winfo_children()[0]
        self.assertEqual(1, len(self.g.configFrame.config.subcomplexes))
        self.assertEqual(1, len(itemList.frames))
        activeItemFrame = itemList.activeItemFrame
        activeItemFrame.fields['name'][1].insert(0, 'new_subcomplex')
        activeItemFrame.fields['color'][1].set(chimera.MaterialColor(0,255,0))
        activeItemFrame.add.invoke()
        self.assertEqual(2, len(self.g.configFrame.config.subcomplexes))
        self.assertEqual(2, len(itemList.frames))

        newSubcomplex = self.g.configFrame.config.subcomplexes[-1]
        self.assertEqual(0, len(newSubcomplex.items))
        subFrame = itemList.frames[-1]

    def testDeleteStuff(self):
        '''Test deletion of Subunits and Data, adding them back, setting mapping, and mapping copy from.
        '''
        xFrame = self.g.Xlinks
        xFrame.displayDefault()

        subUnitFrame = self.g.configFrame.subUnitFrame
        self.assertEqual(14, len(subUnitFrame.frames))
        self.assertEqual(14, len(self.g.configFrame.config.subunits))
        subUnitFrame.frames[0].delete.invoke()
        self.assertEqual(13, len(subUnitFrame.frames))
        self.assertEqual(13, len(self.g.configFrame.config.subunits))
        self.assertEqual(0, len(self.g.configFrame.config.domains))

        dataFrame = self.g.configFrame.dataFrame
        self.assertEqual(10, len(dataFrame.frames))
        self.assertEqual(10, len(self.g.configFrame.config.dataItems))
        dataFrame.frames[0].delete.invoke()
        self.assertEqual(9, len(dataFrame.frames))
        self.assertEqual(9, len(self.g.configFrame.config.dataItems))
        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(74, len(xmgr.pbg.pseudoBonds))

        #Test adding after deleting:
        activeItemFrame = subUnitFrame.activeItemFrame
        activeItemFrame.fields['name'][1].insert(0, 'A190')
        activeItemFrame.fields['chainIds'][1].insert(0, 'A')
        activeItemFrame.fields['color'][1].set(chimera.MaterialColor(0,255,0))
        activeItemFrame.add.invoke()
        self.assertEqual(14, len(self.g.configFrame.config.subunits))
        self.assertEqual(170, len(xmgr.pbg.pseudoBonds))

        dataFrame = self.g.configFrame.dataFrame
        activeItemFrame = dataFrame.activeItemFrame
        activeItemFrame.fields['name'][1].insert(0, '0.05 mM X-linker, 30min at 37 C')
        paths = ['xlinks/Pol1_1_Inter.xls',
            'xlinks/Pol1_1_Intra.xls',
            'xlinks/Pol1_1_Loop.xls,',
            'xlinks/Pol1_1_Mono.xls'
        ]
        dirname = os.path.dirname(self.xlaTestCPath)
        paths = [os.path.join(dirname, p) for p in paths]
        fileFrame = activeItemFrame.fields['fileGroup'][1]
        map(fileFrame.fileGroup.addFile,paths)
        fileFrame.resetFileMenu(paths,0)
        activeItemFrame.fields['type'][3].set('xquest')
        activeItemFrame.add.invoke()

        for frame in dataFrame.frames[1:]:
            mapFrame = frame.fields['mapping'][1]
            mapFrame.mapButton.invoke()
            for seqName, subset in mapFrame.subsetframes.iteritems():
                if 'sp|P10964|RPA1_YEAST' in seqName:
                    subset.menus[0].var.set('A190')
            mapFrame.onSave()

        lastFrame = dataFrame.frames[-1]
        mapFrame = lastFrame.fields['mapping'][1]
        mapFrame.mapButton.invoke()
        mapFrame.mapVar.set('0.2 mM X-linker, 30min at 37 C')
        mapFrame.onSave()

        xFrame.displayDefault()
        self.assertEqual(171, len(xmgr.pbg.pseudoBonds))

    def testDeleteStuffSubcomplexes(self):
        self.g.configFrame.subCompButton.invoke()
        subWind = self.g.configFrame._getSubcomplexesWindow()
        self.assertIsNotNone(subWind)

        itemList = subWind.winfo_children()[0]
        self.assertEqual(1, len(itemList.frames))
        self.assertEqual(1, len(self.g.configFrame.config.subcomplexes))
        self.assertEqual(1, len(subWind.winfo_children()))
        itemList.frames[0].delete.invoke()
        self.assertEqual(0, len(self.g.configFrame.config.subcomplexes))

    def testDeleteStuffDomains(self):
        self.g.configFrame.domainsButton.invoke()
        domWind = self.g.configFrame._getDomainsWindow()
        self.assertIsNotNone(domWind)

        self.assertEqual(1, len(domWind.winfo_children()))
        itemList = domWind.winfo_children()[0]
        self.assertEqual(1, len(itemList.frames))
        itemList.frames[0].delete.invoke()
        self.assertEqual(0, len(self.g.configFrame.config.domains))
        self.assertEqual(0, len(itemList.frames))

    def tearDown(self):
        rc('close #0')