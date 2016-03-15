import os
import tempfile
import csv
import chimera
from chimera.specifier import evalSpec

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
        self.model = chimera.openModels.list()[0]
        ms.setvalue([self.model])

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

        configfilename = tempfile.mkstemp()[1]
        self.g.configFrame.resMngr._saveAssembly(configfilename)
        self.assertEqual(configfilename, xla.getRecentPaths()[0])

        self.g.Subunits.table.colorAll.invoke()

        for chain in ['A','C','E']:
            color = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).atoms()[0].color
            self.assertEqual(color, chimera.MaterialColor(0,255,0))
        for chain in ['B','D','F']:
            color = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).atoms()[0].color
            self.assertEqual(color, chimera.MaterialColor(0.392,0.584,0.929))

        ctable = self.g.Subunits.table
        ctable.table.tixTable.hlist.selection_clear()
        ctable.table.tixTable.hlist.selection_set(0)
        ctable.hide.invoke()
        for chain in ['A','C','E']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, False)
        for chain in ['B','D','F']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, True)
        ctable.showAll.invoke()
        ctable.table.tixTable.hlist.selection_clear()
        ctable.table.tixTable.hlist.selection_set(1)
        ctable.hide.invoke()
        for chain in ['A','C','E']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, True)
        for chain in ['B','D','F']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, False)
        ctable.show.invoke()
        for chain in ['B','D','F']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, True)

        ctable.showAll.invoke()
        ctable.table.tixTable.hlist.selection_clear()
        ctable.table.tixTable.hlist.selection_set(0)
        ctable.showOnly.invoke()
        for chain in ['A','C','E']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, True)
        for chain in ['B','D','F']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, False)

        ctable.showAll.invoke()
        ctable.table.tixTable.hlist.selection_clear()
        ctable.table.tixTable.hlist.selection_set(0)
        chimera.selection.clearCurrent()
        ctable.select.invoke()
        self.assertListEqual(['A', 'C', 'E'], [s.chain for s in chimera.selection.currentChains()])
        chimera.selection.clearCurrent()

        self.assertEqual(2, len(ctable.table._sortedData()))
        ctable.chainVar.set(1)
        self.assertEqual(6, len(ctable.table._sortedData()))

        ctable.showAll.invoke()
        ctable.table.tixTable.hlist.selection_clear()
        ctable.table.tixTable.hlist.selection_set(0)
        ctable.hide.invoke()
        for chain in ['A']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, False)
        for chain in ['C','E']:
            ribbonDisplay = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).residues()[0].ribbonDisplay
            self.assertEqual(ribbonDisplay, True)

        ctable.table.tixTable.hlist.selection_set(1)
        ctable.hide.invoke()
        ctable.table.tixTable.hlist.selection_set(2)
        ctable.hide.invoke()
        ctable.chainVar.set(0)
        self.assertEqual(False, self.g.configFrame.config.subunits[0].show)
        self.assertEqual(2, len(ctable.table._sortedData()))


        ctable.showAll.invoke()
        self.assertEqual(True, self.g.configFrame.config.subunits[0].show)

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
        self.assertEqual(1, len(self.g.configFrame.config.dataItems))
        self.assertEqual(1, len(dataFrame.frames))

        dataMgrTab = self.g.__dict__['Data manager']
        self.assertEqual(3, len(dataMgrTab.winfo_children()))

        xFrame = self.g.Xlinks
        xFrame.displayDefaultBtn.invoke()
        self.assertEqual(1, len(xFrame.getXlinkDataMgrs()))
        xmgr = xFrame.getXlinkDataMgrs()[0]
        self.assertEqual(216, len(xmgr.pbg.pseudoBonds))
        xFrame.ld_score_var.set(30.0)
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(57, displayed)

        xFrame.hideAllXlinksBtn.invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(0, displayed)
        xFrame.displayDefaultBtn.invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(57, displayed)
        xFrame.hideIntraXlinksBtn.invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(24, displayed)

        xFrame.displayDefaultBtn.invoke()
        xFrame.hideInterXlinksBtn.invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(33, displayed)

        xFrame.showAllXlinksBtn.invoke()
        xFrame.smartModeBtn.invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(162, displayed)
        xFrame.smartModeBtn.invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(57, displayed)

        xFrame.confOligBtn.invoke()
        xFrame.confOligWindow.winfo_children()[0].winfo_children()[0].invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(18, displayed)
        xFrame.confOligWindow.winfo_children()[0].winfo_children()[0].invoke()

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
        self.assertEqual(2, len(self.g.configFrame.config.dataItems))
        self.assertEqual(2, len(dataFrame.frames))

        sequenceFrame = dataFrame.frames[-1]
        mapFrame = sequenceFrame.fields['mapping'][1]
        mapFrame.mapButton.invoke()
        for seqName, subset in mapFrame.subsetframes.iteritems():
            if 'RUVB1' in seqName:
                subset.menus[0].var.set('Rvb1')
            if 'RUVB2' in seqName:
                subset.menus[0].var.set('Rvb2')
        mapFrame.onSave()

        self.g.configFrame.resMngr._saveAssembly(self.g.configFrame.config.file)

        self.assertEqual(5, len(dataMgrTab.winfo_children()))

        dataMgrTab.winfo_children()[2].invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(0, displayed)
        dataMgrTab.winfo_children()[2].invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(57, displayed)

        xFrame.showModifiedFrame.showModifiedMap()

        for chain in ['A','C','E']:
            color = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).atoms()[0].color
            self.assertEqual(color, chimera.colorTable.getColorByName('light gray'))
        for chain in ['B','D','F']:
            color = evalSpec('#{0}:.{1}'.format(self.model.id, chain)).atoms()[0].color
            self.assertEqual(color, chimera.colorTable.getColorByName('light gray'))

        some_red_resi = map(str, [81, 128, 161, 174, 276])
        for resi in some_red_resi:
            for chain in ['B','D','F']:
                color = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].color
                self.assertEqual(color, chimera.colorTable.getColorByName('red'))

        some_red_resi = map(str, [85, 116, 193, 210, 239, 377])
        for resi in some_red_resi:
            for chain in ['A','C','E']:
                color = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].color
                self.assertEqual(color, chimera.colorTable.getColorByName('red'))

        some_yellow_resi = map(str, [15, 130, 201, 285, 438])
        for resi in some_yellow_resi:
            for chain in ['B','D','F']:
                color = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].color
                self.assertEqual(color, chimera.colorTable.getColorByName('yellow'))

        some_blue_resi = map(str, [198, 331, 338, 357])
        for resi in some_blue_resi:
            for chain in ['B','D','F']:
                color = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].color
                self.assertEqual(color, chimera.colorTable.getColorByName('blue'))


        xFrame.ld_score_var.set(0.0)
        xFrame.showModifiedFrame.showModifiedMap()
        some_blue_resi = map(str, [377])
        for resi in some_blue_resi:
            for chain in ['A','C','E']:
                color = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].color
                self.assertEqual(color, chimera.colorTable.getColorByName('blue'))

        xFrame.ld_score_var.set(30.0)
        xFrame.showModifiedFrame.showModifiedMap()


        modelStatsTable = self.g.Xlinks.modelStatsTable
        modelStatsTable.xlinkToolbar.resetView()
        self.g.Subunits.table.colorAll.invoke()

        self.assertEqual(6, len(modelStatsTable.winfo_children()))

        csvfilename = tempfile.mkstemp()[1]
        with open(csvfilename, 'w') as f:
            modelStatsTable._exportTable(f)

        with open(csvfilename, 'rU') as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.readline(), ['\t', ','])
            csvfile.seek(0)

            reader = csv.DictReader(csvfile, dialect=dialect)

            self.assertListEqual(['All xlinks', 'Satisfied', 'Violated', 'Satisfied [%]', 'Violated [%]', 'model'], reader.fieldnames)

            rows = list(reader)
            self.assertEqual(1, len(rows))

            row = rows[0]
            self.assertEqual(2, int(row['Violated']))
            self.assertEqual(18, int(row['All xlinks']))
            self.assertEqual(16, int(row['Satisfied']))
            self.assertEqual('88.9', row['Satisfied [%]'])
            self.assertEqual('11.1', row['Violated [%]'])
            self.assertEqual('yRvb12.hexamer.pdb', row['model'])

        modelStatsTable.modelListFrame.winfo_children()[8].invoke()
        detailsFrame = modelStatsTable.detailsFrame
        self.assertEqual(2,len(detailsFrame.winfo_children()))
        detailsFrame.showHistogram()
        xlinksSet = detailsFrame.xlinkDataMgr.getXlinksWithDistances(detailsFrame.xlinkStats)
        self.assertEqual(18,len(xlinksSet.data))
        #TODO: test exportSelectedXlinkList

        detailsFrame.byCompViolatedListFrame.highlightSelBtn.invoke()
        self.assertEqual(6, len(chimera.selection.currentPseudobonds()))
        csvfilename = tempfile.mkstemp()[1]
        with open(csvfilename, 'w') as f:
            detailsFrame.byCompViolatedListFrame._exportSelectedXlinkList(f)
        with open(csvfilename, 'rU') as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.readline(), ['\t', ','])
            csvfile.seek(0)
            reader = csv.DictReader(csvfile, dialect=dialect)
            self.assertEqual(6, len(list(reader)))

        chimera.selection.clearCurrent()
        detailsFrame.byPairViolatedListFrame.highlightSelBtn.invoke()
        self.assertEqual(6, len(chimera.selection.currentPseudobonds()))
        csvfilename = tempfile.mkstemp()[1]
        with open(csvfilename, 'w') as f:
            detailsFrame.byCompViolatedListFrame._exportSelectedXlinkList(f)
        with open(csvfilename, 'rU') as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.readline(), ['\t', ','])
            csvfile.seek(0)
            reader = csv.DictReader(csvfile, dialect=dialect)
            self.assertEqual(6, len(list(reader)))

        chimera.selection.clearCurrent()

        modelStatsTable.xlinkToolbar.lengthThreshVar.set(40.0)
        modelStatsTable.xlinkToolbar.lengthThresholdFrameApplyBtn.invoke()
        modelStatsTable.updateBtn.invoke()
        self.assertEqual(6, len(modelStatsTable.winfo_children()))

        csvfilename = tempfile.mkstemp()[1]
        with open(csvfilename, 'w') as f:
            modelStatsTable._exportTable(f)

        with open(csvfilename, 'rU') as csvfile:
            dialect = csv.Sniffer().sniff(csvfile.readline(), ['\t', ','])
            csvfile.seek(0)

            reader = csv.DictReader(csvfile, dialect=dialect)

            self.assertListEqual(['All xlinks', 'Satisfied', 'Violated', 'Satisfied [%]', 'Violated [%]', 'model'], reader.fieldnames)

            rows = list(reader)
            self.assertEqual(1, len(rows))

            row = rows[0]
            self.assertEqual(1, int(row['Violated']))
            self.assertEqual(18, int(row['All xlinks']))
            self.assertEqual(17, int(row['Satisfied']))
            self.assertEqual('94.4', row['Satisfied [%]'])
            self.assertEqual('5.6', row['Violated [%]'])
            self.assertEqual('yRvb12.hexamer.pdb', row['model'])

        modelStatsTable.xlinkToolbar.lengthThreshVar.set(30.0)
        modelStatsTable.xlinkToolbar.lengthThresholdFrameApplyBtn.invoke()
        modelStatsTable.updateBtn.invoke()

        xFrame.showXlinksFromTabNameCompOptMenuFrom.var.set('Rvb1')
        xFrame.showXlinksFromTabNameCompOptMenuTo.var.set('Rvb2')
        xFrame.showXlinksFromBtn.invoke()
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(24, displayed)
        xFrame.ld_score_var.set(0.0)
        displayed = len([pb for pb in xmgr.pbg.pseudoBonds if pb.display == True])
        self.assertEqual(27, displayed)
        xFrame.ld_score_var.set(30.0)


        colorXlinkedFrame = xFrame.colorXlinkedFrame
        colorXlinkedFrame.compOptMenuFrom.var.set('Rvb1')
        colorXlinkedFrame.compOptMenuTo.var.set('Rvb2')
        colorXlinkedFrame.colorOptionVar.set(1)
        colorXlinkedFrame.colorBtn.invoke()
        some_test_resi = map(str, [31, 171, 174, 432, 450, 454])
        for resi in some_test_resi:
            for chain in ['A','C','E']:
                color = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].color
                self.assertEqual(color, chimera.colorTable.getColorByName('red'))
                display = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].display
                self.assertEqual(display, True)

        colorXlinkedFrame.colorOptionVar.set(2)
        colorXlinkedFrame.colorBtn.invoke()

        some_test_resi = map(str, [31, 171, 174, 432, 450, 454])
        for resi in some_test_resi:
            for chain in ['A','C','E']:
                color = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].color
                self.assertEqual(color, chimera.MaterialColor(0.392,0.584,0.929))
                display = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].display
                self.assertEqual(display, True)

        colorXlinkedFrame.compOptMenuFrom.var.set('Rvb2')
        colorXlinkedFrame.compOptMenuTo.var.set('Rvb1')
        colorXlinkedFrame.uncolorOthersBtn.var.set(True)
        colorXlinkedFrame.colorOptionVar.set(2)
        colorXlinkedFrame.colorBtn.invoke()
        some_test_resi = map(str, [31, 171, 174, 432, 450, 454])
        for resi in some_test_resi:
            for chain in ['A','C','E']:
                display = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].display
                self.assertEqual(display, False)

        some_test_resi = map(str, [123, 157, 198, 357, 414])
        for resi in some_test_resi:
            for chain in ['B','D','F']:
                color = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].color
                self.assertEqual(color, chimera.MaterialColor(0,255,0))
                display = evalSpec('#{0}:{2}.{1}'.format(self.model.id, chain, resi)).atoms()[0].display
                self.assertEqual(display, True)