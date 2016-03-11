import os

import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestTutorial(XlaGuiTests.XlaJustOpenXlaTest):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        cPath = 'Rvb12/Rvb12.json'
        super(TestTutorial, self).setUp(mPaths, cPath)
        ms = xla.get_gui().Subunits.table.modelSelect
        m = chimera.openModels.list()[0]
        ms.setvalue([m])

        self.g = xla.get_gui()

        self.g.modelSelect.doSync(ms)

    def testTutorial(self):
        subUnitFrame = self.g.configFrame.subUnitFrame
        self.assertEqual(0, len(subUnitFrame.frames))
        self.assertEqual(0, len(self.g.configFrame.config.subunits))
        activeItemFrame = subUnitFrame.activeItemFrame
        activeItemFrame.fields['name'][1].insert(0, 'Rvb1')
        activeItemFrame.fields['chainIds'][1].insert(0, 'A,C,E')
        activeItemFrame.fields['color'][1].set(chimera.MaterialColor(0,255,0))
        activeItemFrame.add.invoke()
        self.assertEqual(1, len(self.g.configFrame.config.subunits))
        self.assertEqual(1, len(subUnitFrame.frames))

        activeItemFrame.fields['name'][1].insert(0, 'Rvb2')
        activeItemFrame.fields['chainIds'][1].insert(0, 'B,D,F')
        activeItemFrame.fields['color'][1].set(chimera.MaterialColor(0.392,0.584,0.929))
        activeItemFrame.add.invoke()
        self.assertEqual(2, len(self.g.configFrame.config.subunits))
        self.assertEqual(2, len(subUnitFrame.frames))

        self.g.Subunits.table.colorAll.invoke()

        #TODO: test colors

        dataFrame = self.g.configFrame.dataFrame
        activeItemFrame = dataFrame.activeItemFrame
        activeItemFrame.fields['name'][1].insert(0, 'xlinks')
        paths = ['xlinks/inter.csv',
            'xlinks/intra.csv',
            'xlinks/monolinks.csv'
        ]
        dirname = os.path.dirname(self.xlaTestCPath)
        paths = [os.path.join(dirname, p) for p in paths]
        fileFrame = activeItemFrame.fields['fileGroup'][1]
        map(fileFrame.fileGroup.addFile,paths)
        fileFrame.resetFileMenu(paths,0)
        activeItemFrame.fields['type'][3].set('xquest')
        activeItemFrame.add.invoke()

        xFrame = self.g.Xlinks
        xFrame.displayDefault()
        self.assertEqual(1, len(xFrame.getXlinkDataMgrs()))
        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(216, len(xmgr.pbg.pseudoBonds))
        xFrame.ld_score_var.set(30.0)
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(57, displayed)

        activeItemFrame.fields['name'][1].insert(0, 'sequences')
        paths = ['sequences.yeast.fasta'
        ]
        dirname = os.path.dirname(self.xlaTestCPath)
        paths = [os.path.join(dirname, p) for p in paths]
        fileFrame = activeItemFrame.fields['fileGroup'][1]
        map(fileFrame.fileGroup.addFile,paths)
        fileFrame.resetFileMenu(paths,0)
        activeItemFrame.fields['type'][3].set('sequences')
        activeItemFrame.add.invoke()