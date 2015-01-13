import math
import string
import csv
from sys import platform as _platform
from functools import partial

import chimera
from chimera import selection
import xlinkanalyzer

from chimera.baseDialog import ModelessDialog
from chimera import runCommand
from chimera.widgets import ModelScrolledListBoxBase, ModelItems

from chimera.mplDialog import MPLDialog
from chimera.tkoptions import ColorOption
from chimera import UserError,MaterialColor

from operator import mul

import Pmw
import Tkinter
import tkFileDialog
import tkMessageBox

from Pmw import ScrolledFrame, EntryField

from Tkinter import Toplevel,LabelFrame,Button,StringVar,Entry,\
                    OptionMenu,Label,Frame, TclError
import ttk
import pyxlinks


from data import Component,DataItem,SimpleDataItem,XQuestItem, SequenceItem,\
                 Assembly, ResourceManager, Item, InteractingResidueItem,\
                 Domain, Subcomplex

import manager as xmanager
from manager import Model, RMF_Model, XlinkDataMgr, InteractingResiDataMgr

DEBUG_MODE = False
DEV = True

class XlinkAnalyzer_Dialog(ModelessDialog):

    title = 'Xlink Analyzer'
    name = 'Xlink Analyzer'
    buttons = ('Close')
    help = 'blah.html'


    loadDataTabName = 'Setup'

    models = []
    dataMgrs = []

    def __init__(self, **kw):
        from chimera.extension import manager
        manager.registerInstance(self)

        chimera.triggers.addTrigger('newAssemblyCfg')
        chimera.triggers.addTrigger('componentAdded')
        chimera.triggers.addTrigger('modelLoaded')
        chimera.triggers.addTrigger('configUpdated')
        chimera.triggers.addTrigger('lengthThresholdChanged')
        chimera.triggers.addTrigger('activeDataChanged')
        chimera.triggers.addTrigger('afterAllUpdate')

        self.height = 1000

        self._handlers = []

        ModelessDialog.__init__(self, **kw)


        self.configCfgs = []

        self.configCfgsFrames = []

    def destroy(self):
        self.modelSelect.destroy()

        ModelessDialog.destroy(self)
        chimera.triggers.deleteTrigger('newAssemblyCfg')
        chimera.triggers.deleteTrigger('componentAdded')
        chimera.triggers.deleteTrigger('modelLoaded')
        chimera.triggers.deleteTrigger('configUpdated')
        chimera.triggers.deleteTrigger('lengthThresholdChanged')
        chimera.triggers.deleteTrigger('activeDataChanged')
        chimera.triggers.deleteTrigger('afterAllUpdate')

    def _deleteHandlers(self):
        if not self._handlers:
            return
        while self._handlers:
            triggers, trigName, handler = self._handlers.pop()
            triggers.deleteHandler(trigName, handler)

    def fillInUI(self, parent):
        self.notebook=Pmw.NoteBook(parent)

        self.notebook.pack(fill = 'both', expand = 1, padx = 10, pady = 10)

        self.createLoadDataTab()
        self.notebook.page(self.loadDataTabName).focus_set()
        print xlinkanalyzer.get_gui()
        self.addTab('Subunits', ComponentsTabFrame)
        self.addTab('Data manager', DataMgrTabFrame)

        self.addTab('Xlinks', XlinkMgrTabFrame)
        # self.addTab('Interacting', InteractingResiMgrTabFrame)

        self.notebook.setnaturalsize()

    def createLoadDataTab(self):

        tab = self.notebook.add(self.loadDataTabName)
        self.configFrame = SetupFrame(tab, mainWindow=self)

        self.modelSelect = ModelSelect()

    def setTitle(self,string):
        self._toplevel.title("Xlink Analyzer - " + string)

    def update_loadDataTab_configCfgsOptionMenu(self, trigName, sth, cfg):
        self.loadDataTab_configCfgsOptionMenu['menu'].add_command(label=cfg.name, command=Tkinter._setit(self.loadDataTab_configCfgsOptionMenu.var, cfg.name))
        self.loadDataTab_configCfgsOptionMenu.var.set(cfg.name)


    def show_addComponentFrame(self, cfgName, sth1, sth2):
        self.currAddComponentFrame.grid(row=self.configureSetupFrameRow, column=0, sticky='w')

    def hide_addComponentFrame(self):
        if self.currAddComponentFrame is not None:
            self.currAddComponentFrame.grid_forget()

    def getAssemblyConfig(self, name):
        for cfg in self.configCfgs:
            if cfg.name == name:
                return cfg

    def addComponentToCfg(self, cfgName, name, color=None, chains=None):
        cfg = self.getAssemblyConfig(cfgName)

        if cfgName is None:
            Tkinter.tkMessageBox.showwarning(
                'No such config', cfgName
            )
            return

        if cfg is not None:
            cfg.addItem(name, color=color, chains=chains)

        print help(chimera.triggers.activateTrigger)
        chimera.triggers.activateTrigger('componentAdded', [name, cfg])

    def addComponentToCfgCB(self):
        cfgName = self.loadDataTab_configCfgsOptionMenu.var.get()
        name = self.currAddComponentFrame.componentNameEntryField.get()
        color = self.currAddComponentFrame.coloropt.get()
        chains = self.currAddComponentFrame.chainEntryField.get()
        chains = [x.strip() for x in chains.split(',')]
        print 'chain', chains

        self.addComponentToCfg(cfgName, name, color=color, chains=chains)

    def getDataMgrsForModel(self, model):
        out = []
        for dataMgr in self.dataMgrs:
            if dataMgr.model is model:
                out.append(dataMgr)

        return out


    def addTab(self, name, cls):
        tab = self.notebook.add(name)
        tabCls = cls(tab)
        tabCls.pack(fill='both', expand=1)

        ############ debugging code ############
        setattr(self, name, tabCls)
        ########################################

    def loadFile(self, parent):
        #CARE! DEBUG SETTINGS!
        #TODO: Hide the freaking hidden Files!
        return tkFileDialog.askopenfilename(parent=parent,title="Choose file",\
                                            initialdir="/home/kai/xlinkanalyzer/test")


chimera.dialogs.register(XlinkAnalyzer_Dialog.name, XlinkAnalyzer_Dialog)


def show_dialog():
    from chimera import dialogs
    return dialogs.display(XlinkAnalyzer_Dialog.name)

class ComponentsOptionMenu(Tkinter.OptionMenu):
    def __init__(self, master, defOption, config):
        self.var = Tkinter.StringVar(master)
        defOption = defOption
        self.var.set(defOption)

        options = [defOption] + config.getComponentNames()
        Tkinter.OptionMenu.__init__(self, master, self.var, *options)
        self.config(font=('calibri',(10)),bg='white',width=20)
        self['menu'].config(font=('calibri',(10)), bg='white')

class ComponentsDomainsOptionMenu(Pmw.OptionMenu):
    def __init__(self, master, defOption, config):
        self.xlaConfig = config
        self.var = Tkinter.StringVar(master)
        defOption = defOption
        self.var.set(defOption)

        self.objectsToOptions = []

        options = [defOption]
        # options = [defOption] + self.xlaConfig.getComponentNames()

        self.objectsToOptions.append((None, defOption))

        for comp in self.xlaConfig.getComponents():
            options.append(comp.name)
            self.objectsToOptions.append((comp, comp.name))

        for comp, compDomains in self.xlaConfig.getDomains().iteritems():
            if len(compDomains) > 0:
                for dom in compDomains:
                    domOpt = "{0}, {1}".format(comp, dom.name)
                    options.append(domOpt)
                    self.objectsToOptions.append((dom, domOpt))

        Pmw.OptionMenu.__init__(self, master, menubutton_textvariable=self.var, items=options)
        # self.config(font=('calibri',(10)),bg='white',width=20)
        # self['menu'].config(font=('calibri',(10)), bg='white')

    def getSelected(self):
        idx = self.index(Pmw.SELECT)
        return self.objectsToOptions[idx][0]


class ComponentsHandleOptionMenu(Tkinter.OptionMenu):
    def __init__(self, master):
        self.var = Tkinter.StringVar(master)
        defOption = 'Select'
        self.var.set(defOption)

        options = [
            'Select',
            'Show',
            'Show only',
            'Hide'
        ]
        Tkinter.OptionMenu.__init__(self, master, self.var, *options)
        self.config(font=('calibri',(10)),bg='white',width=12)
        self['menu'].config(font=('calibri',(10)), bg='white')


class ShowModifiedFrame(Tkinter.Frame):
    def __init__(self, parent, xlinkMgrTabFrame, *args, **kwargs):
        Tkinter.Frame.__init__(self, parent, *args, **kwargs)

        self.xlinkMgrTabFrame = xlinkMgrTabFrame


        Label(self, anchor='w', bg='white', padx=4, pady=4,
                text='This panel allows coloring modified residues (i.e. mono-linked and/or cross-linked residues)').pack(anchor='w', fill = 'both', pady=1)

        modelSelect = xlinkanalyzer.get_gui().modelSelect.create(self)
        modelSelect.pack(anchor='w', fill = 'both', pady=1)

        btn = Tkinter.Button(self,
            text='Color modified',
            command=self.showModifiedMap)
        btn.pack()



        self.showVars = {
            'Monolinked': Tkinter.BooleanVar(),
            'Cross-linked': Tkinter.BooleanVar(),
            'Expected': Tkinter.BooleanVar(),
            'NotExpected': Tkinter.BooleanVar(),
            'NotExpectedByLength': Tkinter.BooleanVar(),
            'NotExpectedByPredictor': Tkinter.BooleanVar()
        }

        for varName, showVar in self.showVars.iteritems():
            showVar.set(True)
            if varName in ('Expected', 'NotExpected', 'NotExpectedByLength', 'NotExpectedByPredictor') and not self._isSequenceMappingComplete():
                showVar.set(False)

        def updateCB(name, *args):
            pass

        btn = Tkinter.Checkbutton(self, text='Mono-linked', foreground='blue', variable=self.showVars['Monolinked'])
        btn.pack(anchor='w')
        btn.var = self.showVars['Monolinked']
        btn.var.trace("w", updateCB)

        btn = Tkinter.Checkbutton(self, text='Cross-linked', foreground='blue', variable=self.showVars['Cross-linked'])
        btn.pack(anchor='w')
        btn.var = self.showVars['Cross-linked']
        btn.var.trace("w", updateCB)

        btn = Tkinter.Checkbutton(self, text='Expected to be mono-linked', foreground='red', variable=self.showVars['Expected'])
        btn.pack(anchor='w')
        btn.var = self.showVars['Expected']
        btn.var.trace("w", updateCB)
        if not self._isSequenceMappingComplete():
            btn.configure(state='disabled')


        btn = Tkinter.Checkbutton(self, text='Not expected to be mono-linked', foreground='yellow', variable=self.showVars['NotExpected'])
        btn.pack(anchor='w')
        btn.var = self.showVars['NotExpected']
        btn.var.trace("w", updateCB)
        if not self._isSequenceMappingComplete():
            btn.configure(state='disabled')

        f = LabelFrame(self, bd=4, relief="groove", text='Expected/Not Expected criteria')
        f.pack(anchor='w')

        btn = Tkinter.Checkbutton(f,text='By peptide length (min: 6, max: 50)', variable=self.showVars['NotExpectedByLength'])
        btn.pack(anchor='w', ipadx=10)
        btn.var = self.showVars['NotExpectedByLength']
        btn.var.trace("w", updateCB)
        if not self._isSequenceMappingComplete():
            btn.configure(state='disabled')

        btn = Tkinter.Checkbutton(f, text='Observability prediction', variable=self.showVars['NotExpectedByPredictor'])
        btn.pack(anchor='w', ipadx=10)
        btn.var = self.showVars['NotExpectedByPredictor']
        btn.var.trace("w", updateCB)
        if not self._isSequenceMappingComplete():
            btn.configure(state='disabled')

        btn = Tkinter.Button(self,
            text='Update',
            command=self.showModifiedMap)
        btn.pack(anchor='e')

    def _isSequenceMappingComplete(self):
        config = xlinkanalyzer.get_gui().configFrame.config
        compMapped = [True if c in config.getSequences() else False \
                      for c in config.getComponentNames()]
        return reduce(mul,compMapped,1)

    def showModifiedMap(self):
        dataMgrs = self.xlinkMgrTabFrame.getXlinkDataMgrs()
        for mgr in dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                mgr.showModifiedMap(colorMonolinked=self.showVars['Monolinked'].get(),
                    colorXlinked=self.showVars['Cross-linked'].get(),
                    colorExpected=self.showVars['Expected'].get(),
                    colorNotExpected=self.showVars['NotExpected'].get(),
                    byPredictor=self.showVars['NotExpectedByPredictor'].get(),
                    byLength=self.showVars['NotExpectedByLength'].get())

#new implementation

class ModelXlinkStatsTable(Tkinter.Frame):
    def __init__(self, master, xlinkMgrTabFrame, *args, **kwargs):
        Tkinter.Frame.__init__(self, master, *args, **kwargs)

        self.xlinkMgrTabFrame = xlinkMgrTabFrame
        self.detailsFrame = None

        self.xlinkToolbar = XlinkToolbar(self, self.xlinkMgrTabFrame.ld_score_var, self.xlinkMgrTabFrame.lengthThreshVar, self.xlinkMgrTabFrame)

        self.render()
        self._handlers = []

        # self._addHandlers()

    def _addHandlers(self):
        # handler = chimera.triggers.addHandler('modelLoaded', lambda x, y, z: self.render(), None)
        # self._handlers.append((chimera.triggers, 'modelLoaded', handler))

        handler = chimera.triggers.addHandler('activeDataChanged', lambda x, y, z: self.render(), None)
        self._handlers.append((chimera.triggers, 'activeDataChanged', handler))

    def _deleteHandlers(self):
        if not self._handlers:
            return
        while self._handlers:
            triggers, trigName, handler = self._handlers.pop()
            triggers.deleteHandler(trigName, handler)

    def clear(self):
        # for child in self.winfo_children():
        #     child.destroy()

        for child in self.winfo_children():
            if isinstance(child, XlinkToolbar): #destroying XlinkToolbar was making problems with bound ld_score_var
                child.pack_forget()
            else:
                child.destroy()


    def render(self):
        self.clear()
        self.detailsFrame = None

        Label(self, anchor='w', bg='white', padx=4, pady=4,
                    text='This panel allows performing statistics of satisfied and violated cross-links').pack(anchor='w', pady='4')

        legendFrame = Tkinter.Frame(self, borderwidth=2, relief='groove', padx=4, pady=4)
        legendFrame.pack(anchor='w', pady='4')

        Label(legendFrame, anchor='w',
                    text='Counting xlinks with ld Score above ' + str(self.xlinkMgrTabFrame.ld_score_var.get())
                    ).grid(row=0, column=0, sticky="w")

        Label(legendFrame, anchor='w',
                    foreground = 'red',
                    text=u'Violated: xlinks longer than %s \u212B' % (str(xlinkanalyzer.XLINK_LEN_THRESHOLD),)
                    ).grid(row=1, column=0, sticky="w")

        Label(legendFrame, anchor='w',
                    foreground = 'blue',
                    text=u'Satisfied: xlinks shorter or equal to %s \u212B' % (str(xlinkanalyzer.XLINK_LEN_THRESHOLD),)
                    ).grid(row=2, column=0, sticky="w")

        updateBtn = Tkinter.Button(legendFrame, text="Refresh", command=self.render, padx=4, pady=4)
        updateBtn.grid(row=0, rowspan=3, column=1)



        modelSelect = xlinkanalyzer.get_gui().modelSelect.create(self)
        modelSelect.pack(anchor='w', fill = 'both', pady=1)


        models = xlinkanalyzer.get_gui().modelSelect.getActiveModels()

        colNames = [' ', 'id', 'All xlinks', 'Satisfied', 'Violated', 'Satisfied [%]', 'Violated [%]', 'model']

        tableData = [colNames[2:]]

        modelListFrame = Tkinter.Frame(self, background="black")
        modelListFrame.pack(fill='both', pady='4')

        for col in range(len(colNames)):
            if colNames[col] == 'id':
                width = 5
            else:
                width = 12
            label = Label(modelListFrame, text="%s" % colNames[col],
                             borderwidth=0, width=width)
            label.grid(row=0, column=col, sticky="nsew", padx=1, pady=1)


        for row in range(1, len(models) + 1):
            rowData = []
            col = 0
            model = models[row-1]
            xlinkDataMgrs = self.getDataMgrsForModel(model)

            for xlinkDataMgr in xlinkDataMgrs:
                xlinkStats = xlinkDataMgr.countSatisfied(xlinkanalyzer.XLINK_LEN_THRESHOLD)

                col = 0

                showBtn = Tkinter.Button(modelListFrame, text="Details", command=lambda rebindItem=xlinkDataMgr: self.showDetails(rebindItem))
                showBtn.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                col = col + 1

                label = Label(modelListFrame, text=str(model.chimeraModel.id),
                                 borderwidth=0)
                label.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                col = col + 1

                statsToShow = ['all', 'satisfied', 'violated', 'satisfied %', 'violated %']



                for key in statsToShow:
                    if key.startswith('satisfied'):
                        foreground = 'blue'
                    elif key.startswith('violated'):
                        foreground = 'red'
                    else:
                        foreground = None

                    label = Label(modelListFrame, text=str(xlinkStats[key]),
                                     borderwidth=0, foreground=foreground)

                    label.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)
                    col = col + 1

                    rowData.append(xlinkStats[key])

            if len(rowData) > 0:
                label = Label(modelListFrame, text=model.chimeraModel.name,
                                 borderwidth=0)
                label.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

                rowData.append(model.chimeraModel.name)

                tableData.append(rowData)


        self.tableData = tableData
        modelListFrame.grid_columnconfigure(len(colNames)-1, minsize=10, weight=1)

        exportTableBtn = Tkinter.Button(self, text="Export table", command=self.exportTable)
        exportTableBtn.pack(anchor='e', padx=4)

        self.xlinkToolbar.pack(padx=4, pady=4)

    def exportTable(self):
        #TODO: change initialdir to project dir
        f = tkFileDialog.asksaveasfile(mode='w', defaultextension=".csv", initialdir=None, parent=self)
        if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
            return

        quoting = csv.QUOTE_NONNUMERIC

        fieldnames = self.tableData[0]
        data = self.tableData[1:]

        wr = csv.writer(f, quoting=quoting)
        wr.writerow(fieldnames) #do not use wr.writeheader() to support also python 2.6
        wr.writerows(data)

        f.close()

    def getDataMgrsForModel(self, model):
        out = []
        for dataMgr in self.xlinkMgrTabFrame.getXlinkDataMgrs():
            if dataMgr.model is model:
                out.append(dataMgr)

        return out

    def showDetails(self, xlinkDataMgr):
        if self.detailsFrame:
            self.detailsFrame.destroy()
        text = 'Details for #%s: %s' % (str(xlinkDataMgr.model.chimeraModel.id), xlinkDataMgr.model.chimeraModel.name)

        self.detailsFrame = DetailXlinkStats(self, xlinkDataMgr, text=text)
        self.xlinkToolbar.pack_forget()
        self.detailsFrame.pack(fill='x')
        self.xlinkToolbar.pack(padx=4, pady=4)

class DetailXlinkStats(LabelFrame):
    def __init__(self, master, xlinkDataMgr, *args, **kwargs):
        LabelFrame.__init__(self, master, *args, **kwargs)

        xlinkStats = xlinkDataMgr.countSatisfied(xlinkanalyzer.XLINK_LEN_THRESHOLD)

        # Label(self, text='dupa', foreground='red').pack()

        buttonsFrame = Tkinter.Frame(self)
        buttonsFrame.pack(fill='both', pady='4')

        xlinksHistogramBtn = Tkinter.Button(buttonsFrame, text="Histogram of distances", command=lambda: self.showHistogram(xlinkStats, xlinkDataMgr))
        xlinksHistogramBtn.pack(side='left', anchor='w', padx=4)

        xlinksHistogramBtn = Tkinter.Button(buttonsFrame, text="Export xlinks with distances", command=lambda: self.exportXlinkList(xlinkStats, xlinkDataMgr))
        xlinksHistogramBtn.pack(side='left', anchor='w', padx=4)

        body = Pmw.ScrolledFrame(self,
            horizflex='expand',
            usehullsize = 1,
            hull_height = 500
            )
        body.pack(fill='x', padx=4)

        byCompViolatedListFrame = ByCompViolatedListFrame(body.interior(), xlinkStats, xlinkDataMgr)
        byCompViolatedListFrame.pack(fill='x', padx=4)

        byPairViolatedListFrame = ByPairViolatedListFrame(body.interior(), xlinkStats, xlinkDataMgr)
        byPairViolatedListFrame.pack(fill='x', padx=4)

    def showHistogram(self, xlinkStats, xlinkDataMgr):
        XlinksHistogram(xlinkStats, xlinkDataMgr)

    def exportXlinkList(self, xlinkStats, xlinkDataMgr):
        xlinks = []
        for xlinkBond in xlinkStats['reprXlinks']:
            oriXlinks = xlinkDataMgr.getOriXlinks(xlinkBond.xlink, copiesWithSource=True)
            comp1 = pyxlinks.get_protein(xlinkBond.xlink, 1)
            comp2 = pyxlinks.get_protein(xlinkBond.xlink, 2)

            for xlink in oriXlinks:
                xlink['distance'] = xlinkBond.pb.length()
                xlink['Subunit1'] = comp1
                xlink['Subunit2'] = comp2

            xlinks.extend(oriXlinks)

        if len(xlinks) > 0:
            fieldnames = xlinkDataMgr.xlinksSetsMerged.fieldnames
            if 'distance' not in fieldnames:
                fieldnames.append('distance')
            if 'Subunit1' not in fieldnames:
                fieldnames.insert(fieldnames.index('Protein1')+1, 'Subunit1')
            if 'Subunit2' not in fieldnames:
                fieldnames.insert(fieldnames.index('Protein2')+1, 'Subunit2')
            xlinksSet = pyxlinks.XlinksSet(xlink_set_data=xlinks, fieldnames=fieldnames)

            #TODO: change initialdir to project dir
            f = tkFileDialog.asksaveasfilename(defaultextension=".csv", initialdir=None, parent=self)
            if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
                return
            if f:
                xlinksSet.save_to_file(f, quoting=csv.QUOTE_NONNUMERIC)
        else:
            raise UserError("No cross-links.\n \
                No crosslinks found in current data sets above current score threshold.")

class ViolatedListFrame(LabelFrame):
    """Abstract class"""
    def __init__(self, master, xlinkStats, xlinkDataMgr, text, *args, **kwargs):
        LabelFrame.__init__(self, master, text=text, *args, **kwargs)

        self.xlinkStats = xlinkStats
        self.xlinkDataMgr = xlinkDataMgr

        self.createList()

        self.createListFrame()

        buttonsFrame = Tkinter.Frame(self)
        buttonsFrame.pack(anchor='w')
        highlightSelBtn = Tkinter.Button(buttonsFrame, text="Highlight selected in structure", command=self.highlightCB)
        highlightSelBtn.pack(side='left')

        exportSelBtn = Tkinter.Button(buttonsFrame, text="Export selected xlinks", command=self.exportSelectedXlinkList)
        exportSelBtn.pack(side='left')

    def createList(self):
        raise NotImplementedError("To implement in subclasses")

    def getData(self):
        raise NotImplementedError("To implement in subclasses")

    def getName(self, item):
        raise NotImplementedError("To implement in subclasses")


    def createListFrame(self):
        itemListFrame = Pmw.ScrolledFrame(self,
            usehullsize = 1,
            hull_height = 100
            )
        itemListFrame.pack(anchor='w', fill='x')

        row = 0
        for item in self.items:
            var = Tkinter.BooleanVar()
            if row == 0:
                var.set(True)
                item['toHighlight'] = True
            else:
                var.set(False)

            btn = Tkinter.Checkbutton(itemListFrame.interior(),
                variable=var,
                command=lambda rebindItem=item, rebindVar=var: self.toggleActive(rebindItem, rebindVar))
            btn.var = var

            btn.grid(row = row, column=0)

            Label(itemListFrame.interior(), text=str(len(item['violated'])), foreground='red').grid(row=row, column=1, sticky='w')

            name = self.getName(item)
            Label(itemListFrame.interior(), text=name).grid(row=row, column=2, sticky='w')

            row += 1

        noOfCols = 3
        for col in range(noOfCols):
            itemListFrame.interior().grid_columnconfigure(col, pad=2)

    def toggleActive(self, item, var):
        item['toHighlight'] = var.get()

    def getSelected(self):
        bondsToHighlight = []
        for item in self.items:
            if item['toHighlight']:
                for xlinkSet in item['violated']:
                    for x in xlinkSet:
                        if x.pb.display:
                            if x not in bondsToHighlight:
                                bondsToHighlight.append(x)

        return bondsToHighlight

    def highlightCB(self):
        selection.setCurrent(selection.ItemizedSelection([x.pb for x in self.getSelected()]))

    def exportSelectedXlinkList(self):
        xlinks = []
        for xlinkBond in self.getSelected():
            oriXlinks = self.xlinkDataMgr.getOriXlinks(xlinkBond.xlink, copiesWithSource=True)
            comp1 = pyxlinks.get_protein(xlinkBond.xlink, 1)
            comp2 = pyxlinks.get_protein(xlinkBond.xlink, 2)

            for xlink in oriXlinks:
                xlink['distance'] = xlinkBond.pb.length()
                xlink['Subunit1'] = comp1
                xlink['Subunit2'] = comp2

            xlinks.extend(oriXlinks)

        if len(xlinks) > 0:
            fieldnames = self.xlinkDataMgr.xlinksSetsMerged.fieldnames
            if 'distance' not in fieldnames:
                fieldnames.append('distance')
            if 'Subunit1' not in fieldnames:
                fieldnames.insert(fieldnames.index('Protein1')+1, 'Subunit1')
            if 'Subunit2' not in fieldnames:
                fieldnames.insert(fieldnames.index('Protein2')+1, 'Subunit2')
            xlinksSet = pyxlinks.XlinksSet(xlink_set_data=xlinks, fieldnames=fieldnames)

            #TODO: change initialdir to project dir
            f = tkFileDialog.asksaveasfile(mode='w', defaultextension=".csv", initialdir=None, parent=self)
            if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
                return

            xlinksSet.save_to_file(f, quoting=csv.QUOTE_NONNUMERIC)

        else:
            raise UserError("No cross-links.\n \
                No crosslinks found in current data sets above current score threshold.")

class ByCompViolatedListFrame(ViolatedListFrame):
    def __init__(self, master, xlinkStats, xlinkDataMgr, *args, **kwargs):
        ViolatedListFrame.__init__(self, master, xlinkStats, xlinkDataMgr, text='Subunits with violated xlinks', *args, **kwargs)

    def createList(self):
        self.items = []
        for comp, violated in self.getData():
            item = {
                'toHighlight': False,
                'comp': comp,
                'violated': violated
                }

            self.items.append(item)

    def getData(self):
        return self.xlinkStats['sorted_by_component_violated']

    def getName(self, item):
        return item['comp']

class ByPairViolatedListFrame(ViolatedListFrame):
    def __init__(self, master, xlinkStats, xlinkDataMgr, *args, **kwargs):
        ViolatedListFrame.__init__(self, master, xlinkStats, xlinkDataMgr, text='Pairs of subunits with violated xlinks', *args, **kwargs)

    def createList(self):
        self.items = []
        for comps, violated in self.getData():
            comps = list(comps)

            if len(comps) == 1: #intra_link
                comps.append(comps[0])

            item = {
                'toHighlight': False,
                'comps': comps,
                'violated': violated
                }

            self.items.append(item)

    def getData(self):
        return self.xlinkStats['sorted_by_pair_violated']

    def getName(self, item):
        return ' - '.join(item['comps'])

class XlinksHistogram(MPLDialog):

    help = "blah"
    buttons = ("Close" )

    def __init__(self, xlinkStats, xlinkDataMgr):
        self.title = "#%s: %s - histogram of measured C-alpha distances between cross-linked residues" \
            % (xlinkDataMgr.model.chimeraModel.id, xlinkDataMgr.model.chimeraModel.name)

        MPLDialog.__init__(self)


        reprXlinks = xlinkStats['reprXlinks']

        self.lengths = []
        for xlink in reprXlinks:
            self.lengths.append(xlink.pb.length())

        if len(self.lengths) > 0:
            ax = self.add_subplot(1,1,1)
            self.subplot = ax
            self._displayData()
        else:
            raise UserError("No cross-links.\n \
                No crosslinks found in current data sets above current score threshold.")

    def fillInUI(self, parent):
        Label(parent, text='control stuff here').pack(pady=5)

        f = Tkinter.Frame(parent)
        f.pack(fill="both", expand=True)
        MPLDialog.fillInUI(self, f)

    def _displayData(self):
        ax = self.subplot
        ax.clear()

        binsize = 3
        maxLength = max(self.lengths)
        bins = range(0, int(math.ceil(maxLength)), binsize)

        bins = bins[1:] #strip 0
        bins.append(bins[-1]+3)


        colors = []
        for bin in bins:
            if bin >= xlinkanalyzer.XLINK_LEN_THRESHOLD:
                colors.append('#CC0000')
            else:
                colors.append('#348ABD') #blue
            print bin, colors[-1]
        n, bins, patches = ax.hist(self.lengths, bins=bins, rwidth=.5)
        for c, p in zip(colors, patches):
            p.set_color(c)
        ticks = map(int, bins)
        ax.set_xticks(ticks)
        ax.set_ylabel("Number of cross-links")
        ax.set_xlabel(r"Euclidan C$\alpha$ pair distance [$\AA$]")
        ax.yaxis.grid(True)
        self.draw()

    def _recalcLengths(self):
        '''
        Return lengths which compress long distances
        into single bin > (XLINK_LEN_THRESHOLD + 3)
        '''
        lengths = []
        for l in self.lengths:
            if l > xlinkanalyzer.XLINK_LEN_THRESHOLD + 3:
                lengths.append(xlinkanalyzer.XLINK_LEN_THRESHOLD + 3 + 1)
            else:
                lengths.append(l)
        return lengths

class ItemFrame(LabelFrame):
    def __init__(self,master,item,configFrame,active=False,*args,**kwargs):
        LabelFrame.__init__(self,master,*args,**kwargs)
        self.master = master
        self.item = item
        self.frame = configFrame
        self.config = item.config
        self.active = active
        self.layout = {"padx":5,"pady":3}
        self.applied = True

        if active:
            self.nameField = EntryField(self,labelpos="w",\
                                             label_text="Name: ",\
                                             entry_width=10,\
                                             command=self.populate)
            self.nameField.grid(sticky='W',row = 0,column=0,**self.layout)
            if issubclass(item.__class__,Component):
                self.chainField = EntryField(self,labelpos="w",\
                                                  label_text="Chains: ",\
                                                  entry_width=10,\
                                                  command=self.populate)
                self.chainField.grid(sticky='W',row = 0,column=1,**self.layout)
                self.colorField = ColorOption(self,0,None,None,self.populate,\
                                              startCol=2,**self.layout)
            elif issubclass(item.__class__,DataItem):
                Button(self,text="Browse files",command=self.onSource)\
                      .grid(row=0,column=1,sticky="w",**self.layout)

                self.sourceVar = StringVar("")
                self.menu = OptionMenu(self,self.sourceVar,"")
                self.menu.config(width=20)
                self.menu.grid(row=0,column=2,sticky="w",**self.layout)

                self.typeVar = StringVar("")
                self.typeVar.set("Data Type")
                if DEV:
                    self.typeMenu = OptionMenu(self,\
                                           self.typeVar,\
                                           xlinkanalyzer.XLINK_ANALYZER_DATA_TYPE,\
                                           xlinkanalyzer.XQUEST_DATA_TYPE,\
                                           xlinkanalyzer.SEQUENCES_DATA_TYPE,\
                                           xlinkanalyzer.INTERACTING_RESI_DATA_TYPE)
                else:
                    self.typeMenu = OptionMenu(self,\
                                           self.typeVar,\
                                           xlinkanalyzer.XLINK_ANALYZER_DATA_TYPE,\
                                           xlinkanalyzer.XQUEST_DATA_TYPE,\
                                           xlinkanalyzer.SEQUENCES_DATA_TYPE)
                self.typeMenu.config(width=10)
                self.typeMenu.grid(row=0,column=3,sticky="w",**self.layout)
                self.resource = []
        else:
            self.nameVar = StringVar("")
            self.nameField = EntryField(self,label_text="Name: ",\
                                        labelpos="w",\
                                        entry_width=10,\
                                        entry_textvariable=self.nameVar)
            self.nameField.grid(sticky='W',row = 0,column=0,**self.layout)
            self.nameVar.set(item.name)
            self.nameVar.trace("w", lambda n,i,m: self.onEdit(n,i,m))
            if issubclass(item.__class__,Component):
                self.chainVar = StringVar("")
                self.chainField = EntryField(self,\
                                        label_text="ChainIds: ",\
                                        labelpos="w",\
                                        entry_width=10,\
                                        entry_textvariable=self.chainVar)
                self.chainField.grid(row=0,column=1)
                self.chainVar.set(item.commaList(item.chainIds))
                self.chainVar.trace("w", lambda n,i,m: self.onEdit(n,i,m))
                self.cOption = ColorOption(self,0,None,None,self.populate,\
                            startCol=2,**self.layout)
                self.cOption.set(item.color)
                self.apply = Button(self,text=unichr(10004),\
                                    command=self.onApply)
                self.createToolTip(self.apply,"Apply Changes")
                self.apply.grid(row=0,column=3,sticky="w",**self.layout)
                self.delete = Button(self,text="x",command=self.onDelete)
                self.delete.grid(row=0,column=4,sticky="w",**self.layout)
                self.createToolTip(self.delete,"Delete")

            elif issubclass(item.__class__,DataItem):
                Button(self,text="Configure",command=self.configureMenu)\
                    .grid(sticky='W',row=0,column=1,**self.layout)
                self.sourceVar = StringVar("")
                if type(item.resource)==list:
                    try:
                        self.sourceVar.set(item.resource[0])
                    except IndexError:
                        print item
                else:
                    self.sourceVar.set(item.resource)
                self.menu = OptionMenu(self,self.sourceVar,*item.resource)
                self.menu.config(width=30)
                self.menu.grid(row=0,column=2,sticky="w",**self.layout)
                self.delete = Button(self,text="x",command=self.onDelete)
                self.delete.grid(row=0,column=3,sticky="w",**self.layout)
                self.createToolTip(self.delete,"Delete")
            elif issubclass(item.__class__,SimpleDataItem):
                Button(self,text="Configure",command=self.configureMenu)\
                    .grid(sticky='W',row=0,column=1,**self.layout)
                self.delete = Button(self,text="x",command=self.onDelete)
                self.delete.grid(row=0,column=3,sticky="w",**self.layout)
                self.createToolTip(self.delete,"Delete")

    def onEdit(self,n=None,i=None,m=None):
        if self.nameVar.get() != self.item.name \
           or self.chainVar.get() != self.item.commaList(self.item.chainIds)\
           or self.cOption.get() != self.item.color:
            self.apply.configure(bg="#00A8FF")
        else:
            self.apply.configure(bg="light grey")

    def onApply(self):
        self.populate()
        self.frame.update()
        self.apply.configure(bg="light grey")

    def onDelete(self):
        self.config.deleteItem(self.item)
        self.frame.update()

    def onSource(self):

        self.resource = tkFileDialog.askopenfilenames(parent=self.master)

        #FIX: http://stackoverflow.com/questions/4116249/parsing-the-results-of-askopenfilenames
        if isinstance(self.resource, basestring):
            self.resource = self.master.tk.splitlist(self.resource)

        if self.resource:
            for source in self.resource:
                self.menu['menu'].add_command(label=source)
            self.menu['menu'].delete(0)
            self.sourceVar.set(self.resource[0])
            self.populate()

    def populate(self,colorOption= None):
        if colorOption:
            self.onEdit()
        oldName = self.item.name
        self.item.name = self.nameField.get()
        if type(self.item) == Component:
            self.item.chainIds = self.item.getList(self.chainField.get())
            self.item.selection = self.item.createComponentSelectionFromChains(self.item.chainIds)
            self.item.setChainToComponent(self.item.createChainToComponentFromChainIds(self.item.chainIds))
            if colorOption:
                self.item.color = colorOption.get()
        elif type(self.item) == DataItem:
            self.item.resource = self.resource
            print self.typeVar.get()
            if self.typeVar.get() == xlinkanalyzer.INTERACTING_RESI_DATA_TYPE:
                self.item = InteractingResidueItem(self.item.name,\
                                             self.item.config)
                print self.item.type
            elif self.typeVar.get() == xlinkanalyzer.XQUEST_DATA_TYPE:
                self.item = XQuestItem(self.item.name,\
                                       self.item.config,\
                                       self.item.resource)
            elif self.typeVar.get() == xlinkanalyzer.SEQUENCES_DATA_TYPE:
                self.item = SequenceItem(self.item.name,\
                                         self.item.config,\
                                         self.item.resource)
        self.update()
        if oldName != self.item.name:
            for item in [i for i in self.config.items \
                         if issubclass(i.__class__, DataItem)]:
                if item.mapping:
                    if oldName in item.mapping:
                        item.mapping[self.item.name] = item.mapping[oldName]
                        item.mapping.pop(oldName)
                    for k,v in item.mapping.iteritems():
                        if oldName in v and oldName:
                            item.mapping[k].remove(oldName)
                            item.mapping[k].append(self.item.name)
        return self.item.validate()

    def populateMapping(self):
        if type(self.item) == XQuestItem:
            self.item.mapping = dict([(xQN,[self.userNames[i].get()]) for\
                                i,xQN in enumerate(self.item.xQuestNames)])
        elif type(self.item) == SequenceItem:
            self.item.mapping = dict([(sqN,[self.userNames[i].get()]) \
                                        for i,sqN in enumerate(\
                                            self.item.sequences.keys())])
        self.item.updateData()
        chimera.triggers.activateTrigger('configUpdated', self.config)
        self.menu.destroy()

    def empty(self):
        if self.active:
            self.nameField.setvalue("")
            if issubclass(self.item.__class__,Component):
                self.chainField.setvalue("")
                self.colorField.set(MaterialColor(*[0.0,0.0,0.0,1.0]))
            elif issubclass(self.item.__class__,DataItem):
                self.sourceVar.set("")
                self.menu = OptionMenu(self,self.sourceVar,"")
                self.menu.config(width=20)
                self.menu.grid(row=0,column=2,sticky="w",**self.layout)

                self.typeVar = StringVar("")
                self.typeVar.set("")
                self.typeMenu = OptionMenu(self,\
                                       self.typeVar,\
                                       xlinkanalyzer.XLINK_ANALYZER_DATA_TYPE,\
                                       xlinkanalyzer.XQUEST_DATA_TYPE,\
                                       xlinkanalyzer.SEQUENCES_DATA_TYPE,
                                       xlinkanalyzer.INTERACTING_RESI_DATA_TYPE)
                self.typeMenu.config(width=10)
                self.typeMenu.grid(row=0,column=3,sticky="w",**self.layout)
                self.resource = []

    def configureMenu(self):
        if self.item.type in [xlinkanalyzer.XQUEST_DATA_TYPE,\
                              xlinkanalyzer.SEQUENCES_DATA_TYPE]:
            self.configureXQuestSequence()
        elif self.item.type in [xlinkanalyzer.INTERACTING_RESI_DATA_TYPE]:
            self.configureInteractingResidue()

    def configureXQuestSequence(self):
        components = [item.name for item in self.config.items\
                if type(item)==Component]
        if not components:
            title = "No Components"
            message = "There are currently no subunits loaded in xlinkanalyzer! Create or load subunits to configure Data Items."
            tkMessageBox.showinfo(title,message)
            return

        self.menu = Toplevel()
        frame = Frame(self.menu,padx=5,pady=5)

        self.fromNames = []
        mapping = []

        if type(self.item) == XQuestItem:
            self.fromNames = self.item.xQuestNames
            mapping = self.item.mapping

        elif type(self.item) == SequenceItem:
            self.fromNames = self.item.sequences.keys()
            mapping = self.item.mapping

        self.userNames = []
        userNameMenus = []

        msg = "Match protein names in data files to\nsubunit names."
        msgFont = "Verdana 11 bold"
        h1 = "Name in data file"
        h2 = "Subunit name"
        hFont = "Verdana 11"

        row = 0
        Label(frame,text=msg,font=msgFont)\
             .grid(sticky='W',row = row,column=0,pady=10)
        row+=2
        Label(frame,text=h1,font=hFont)\
             .grid(sticky='W',row = row,column=0,pady=5)
        Label(frame,text=h2,font=hFont)\
             .grid(sticky='W',row = row,column=2,pady=5)
        row+=2
        for i,fromName in enumerate(self.fromNames):
            Label(frame,text=fromName).grid(sticky='W',\
                                              row = i+row,\
                                              column=0)
            self.userNames.append(StringVar(""))
            userNameMenus.append(\
            OptionMenu(frame,self.userNames[i],*[item.name for item\
                           in self.config.items \
                           if type(item)==Component]))
            userNameMenus[i].configure(width=20)
            userNameMenus[i].grid(sticky='W',row = i+row,column=2)
            if mapping:
                if mapping.has_key(fromName):
                    if type(mapping[fromName]) == list:
                        name = mapping[fromName][0]
                    else:
                        name = mapping[fromName]
                    self.userNames[i].set(name)
        Button(frame,text="Save",command=self.populateMapping)\
               .grid(sticky='W',row = len(self.fromNames)+row,column=0)
        Label(frame,text="Copy Mapping:")\
              .grid(sticky='W',row = len(self.fromNames)+row,column=1)
        row+=len(self.fromNames)

        copyVar = StringVar("")
        copyVar.set(self.item.name)
        copyMenu=OptionMenu(frame,copyVar,\
                            *[item.name for item in self.config.items \
                           if type(item)==type(self.item)],\
                           command=self.copyMapping)
        copyMenu.configure(width=20)
        copyMenu.grid(sticky='W',row = row,column=2)
        frame.grid()
        self.menu.grid()
        self.frame.update()

    def configureInteractingResidue(self):

        compNames = self.config.getComponentNames()
        if not compNames:
            title = "No subunits yet"
            message = "Please add some subunits before configuring."
            tkMessageBox.showinfo(title,message,parent=self.master)
            return

        row = 0
        self.menu = Toplevel()
        frame = Frame(self.menu,padx=5,pady=5)
        listFrame = Frame(frame,padx=5,pady=5)
        _dict = self.item.data
        resiList = []

        def _onDel(_from,_to,i):
            print _dict[_from][_to]
            if _dict[_from]:
                _dict[_from].pop(_to)
                if not _dict[_from]:
                    _dict.pop(_from)
            else:
                _dict.pop(_from)
            resiList.pop(i)
            _updateList()

        def _onApply(_from,_to,i):
            _dict[_from][_to] = [int(s.strip()) for s in \
                                 resiList[i].get().split(",")]

        def _updateList():
            _str = lambda l: str(l)[1:-1]
            _del = lambda: _dict.__getitem__(_from).pop

            for child in listFrame.winfo_children():
                child.destroy()

            for i,_from in enumerate(_dict):
                l = len(_dict[_from])
                for j,_to in enumerate(_dict[_from]):
                    f = EntryField(listFrame,labelpos="w",label_text="From: ",\
                               entry_width=14,value=_from)
                    f.configure(entry_state="readonly")
                    f.grid(sticky='W', row=i*l+j,column=0,columnspan=2)
                    t = EntryField(listFrame,labelpos="w",label_text="To: ",\
                               entry_width=14, value=_to)
                    t.configure(entry_state="readonly")
                    t.grid(sticky='W', row=i*l+j,column=2,columnspan=2)
                    e = EntryField(listFrame,labelpos="w",\
                                   label_text="Residues: ", entry_width=20,\
                                   value=_str(_dict[_from][_to]))
                    e.grid(sticky='W', row=i*l+j,column=4)
                    resiList.append(e)
                    _apply = Button(listFrame,text=unichr(10004),\
                                       command=lambda:_onApply(_from,_to,i*l+j))
                    _apply.grid(sticky='W', row=i*l+j,column=5)
                    self.createToolTip(_apply,"Apply Changes")
                    _delete = Button(listFrame,text="x",\
                                     command=lambda:_onDel(_from,_to,i*l+j))
                    _delete.grid(sticky='W', row=i*l+j,column=6)
                    self.createToolTip(_delete,"Delete")

        def _onAdd():
            _from = fromVar.get()
            _to = toVar.get()
            if not _from in self.item.data:
                self.item.data[_from]={}
            self.item.data[_from][_to] = [int(s.strip()) for s in \
                                                   entry.get().split(",")]
            print _from,_to,self.item.data[_from][_to]
            _updateList()

        def _onSave():
            chimera.triggers.activateTrigger('configUpdated', self.config)
            self.menu.destroy()

        Label(frame,text="From: ").grid(row=row,column=0,sticky="W")
        fromVar = StringVar("")
        fromMenu = OptionMenu(frame,fromVar,*compNames)
        fromMenu.configure(width=10)
        fromMenu.grid(sticky='W', row=row,column=1)

        Label(frame,text="To: ").grid(row=row,column=2,sticky="W")
        toVar = StringVar("")
        toMenu = OptionMenu(frame,toVar,*compNames)
        toMenu.configure(width=10)
        toMenu.grid(sticky='W', row=row,column=3)

        entry = EntryField(frame,labelpos="w",label_text="Residues: ",\
                           entry_width=20)
        entry.grid(sticky='W', row=row,column=4)
        Button(frame,text="Add",command=_onAdd)\
              .grid(sticky='W', row=row,column=5)
        _updateList()
        listFrame.grid(sticky='W', row=1,column=0,columnspan=6)

        Button(frame,text="Save",command=_onSave)\
               .grid(sticky='W',row=2,column=0)
        frame.grid()
        self.menu.grid()
        self.frame.update()

    def copyMapping(self,name):
        #there is an ambiguity here, items need an unique identifier
        firstHit = [item for item in self.config.items \
                 if (type(item)==type(self.item) and name==item.name)][0]
        mapping = firstHit.mapping
        for i,name in enumerate(self.fromNames):
            if mapping.has_key(name):
                self.userNames[i].set(self.item.commaList(mapping[name]))
                self.item.mapping[name] = mapping[name]

    def createToolTip(self, widget, text):
        toolTip = ToolTip(widget)
        def enter(event):
            toolTip.showtip(text)
        def leave(event):
            toolTip.hidetip()
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)



class CustomModelItems(ModelItems):
    '''
    Shows rmf models only as single model
    '''
    columnTitle = "Model"

    def listFn(self):
        seen = []
        out = []
        for m in chimera.openModels.list():
            if m.id not in seen:
                seen.append(m.id)
                out.append(m)

        return out

    def __init__(self, **kw):

        kw['listFunc'] = self.listFn
        ModelItems.__init__(self, **kw)

class ModelSelect(object):
    def __init__(self):
        self.children = []
        self.models = [] #xlinkanalyzer Model list
        self.config = xlinkanalyzer.get_gui().configFrame.config
        self._onModelRemoveHandler = chimera.openModels.addRemoveHandler(self.onModelRemove, None)

    def destroy(self):
        chimera.openModels.deleteRemoveHandler(self._onModelRemoveHandler)

    def create(self, master, *args, **kwargs):

        box = CustomMoleculeScrolledListBox(master,
            listbox_selectmode="extended",
            labelpos="nw",
            label_text="Choose models(s) to act on:"
            )

        if len(self.children) > 0:
            box.setvalue(self.children[0].getvalue()[:])

        box.configure(selectioncommand=lambda: self.doSync(box))

        self.children.append(box)

        return box

    def isRMFmodel(self, chimeraModel):
        return chimeraModel.openedAs[0].endswith('.rmf')

    def createRMFmodel(self, chimeraModel):
        '''
        Find all submodels with this id
        '''
        idx = chimeraModel.id
        moleculeModel = None
        beadModel = None

        for omodel in chimera.openModels.list():
            if omodel.id == idx:
                if hasattr(omodel, 'isRealMolecule') and not omodel.isRealMolecule:
                    beadModel = omodel
                else:
                    moleculeModel = omodel

        model = RMF_Model(moleculeModel, beadModel, self.config)

        return model

    def doSync(self, callingChild):
        selChimeraModels = callingChild.getvalue()
        for child in self.children:
            if child is not callingChild:
                child.setvalue(selChimeraModels[:])

        oldActiveChimeraModels = [mdl.chimeraModel for mdl in self.models]

        for chimeraModel in selChimeraModels:
            if chimeraModel not in oldActiveChimeraModels:
                if self.isRMFmodel(chimeraModel):
                    newModel = self.createRMFmodel(chimeraModel)
                else:
                    newModel = Model(chimeraModel, self.config)
                newModel.active = False
                self.models.append(newModel)

        for model in self.models:
            if model.chimeraModel in selChimeraModels:
                model.active = True
            else:
                model.active = False


    def getActiveModels(self):
        return [model for model in self.models if model.active]

    def onModelRemove(self, trigger, userData, removedModels):
        chimeraModels = [mdl.chimeraModel for mdl in self.models]
        for mdl in removedModels:
            if mdl in chimeraModels:
                self.models.remove(self.models[chimeraModels.index(mdl)])

class CustomMoleculeScrolledListBox(ModelScrolledListBoxBase, CustomModelItems):
    """Modified to remove itself from ModelSelect.children list"""
    autoselectDefault = None
    def __init__(self, master, listbox_height=4, **kw):
        CustomModelItems.__init__(self, **kw)
        ModelScrolledListBoxBase.__init__(self, master,
                    listbox_height=listbox_height, **kw)

    def destroy(self):
        modelSelect = xlinkanalyzer.get_gui().modelSelect
        if self in modelSelect.children:
            modelSelect.children.remove(self)

        self.doHack()
        ModelScrolledListBoxBase.destroy(self)

    def doHack(self):
        """Avoid Attribute error that I got sometimes when destroying"""
        self.itemMap = {}
        self.valueMap = {}


class TabFrame(Tkinter.Frame):
    def __init__(self, master, *args, **kwargs):
        Tkinter.Frame.__init__(self, master, *args, **kwargs)

        self.config = xlinkanalyzer.get_gui().configFrame.config
        self.models = []
        self._handlers = []
        self._addHandlers()

    def destroy(self):
        self._deleteHandlers()
        Tkinter.Frame.destroy(self)

    def _addHandlers(self):
        handler = chimera.triggers.addHandler('configUpdated', self.reload, None)
        self._handlers.append((chimera.triggers, 'configUpdated', handler))

    def _deleteHandlers(self):
        if not self._handlers:
            return
        while self._handlers:
            triggers, trigName, handler = self._handlers.pop()
            triggers.deleteHandler(trigName, handler)

    def getActiveModels(self):
        self.models = xlinkanalyzer.get_gui().modelSelect.getActiveModels()

class SetupFrame(TabFrame):
    def __init__(self,master,mainWindow=None):
        """
        The SetupFrame represents an Assembly and offers the
        possibility to edit this config.
        """
        self.master = master
        self.itemFrames = []
        self.models={}
        self.selectedModel = StringVar()
        self.selectedModel.set("Displayed Models")
        self.config = Assembly(self)
        self.resMngr = ResourceManager(self.config)
        self.mainWindow = mainWindow
        self.mainWindow.setTitle(self.config.state)
        self.name = "AF"
        layout = {"pady":5,"padx":5}

        Frame.__init__(self,master)

        #ROW 0:
        curRow = 0

        #ROW 1:
        Label(self, text="Add subunit:").grid(row=curRow,\
                                    column=0,\
                                    sticky="W",\
                                    columnspan=2,\
                                    **layout)

        Label(self, text="Add data (e.g. files with cross-links):").grid(row=curRow,\
                                    column=3,\
                                    sticky="W",\
                                    columnspan=2,\
                                    **layout)
        curRow = curRow + 1

        #ROW 2:
        self.addComponentFrame = ItemFrame(self,\
                                           Component("",self.config),\
                                           self,\
                                           active=True)
        self.addComponentFrame.grid(row=curRow,\
                                    column=0,\
                                    sticky="W",\
                                    columnspan=2,\
                                    **layout)

        self.addCompButton = Button(self,\
                                    text="Add",\
                                    command=self.onComponentAdd)
        self.addCompButton.grid(row = curRow,\
                                column = 2, \
                                sticky = "W",**layout)
        self.addDataFrame = ItemFrame(self,\
                                      DataItem("",self.config,None),\
                                      self,\
                                      active=True)
        self.addDataFrame.grid(row = curRow, column = 3, sticky = "W",**layout)

        self.addDataButton = Button(self,text="Add",command=self.onDataItemAdd)
        self.addDataButton.grid(row = curRow,column = 4, sticky = "W",**layout)

        curRow = curRow + 1

        #ROW 3:
        self.prettyComponentFrame = LabelFrame(self,text="Subunits")
        self.prettyComponentFrame.grid(sticky="NESW",\
                                  row=curRow,\
                                  column=0,\
                                  columnspan=3,\
                                  **layout)
        self.prettyDataFrame = LabelFrame(self,text="Data Sets")
        self.prettyDataFrame.grid(sticky="NESW",\
                             row=curRow,\
                             column=3,\
                             columnspan=2,\
                             **layout)
        self.compFrame = ScrolledFrame(self.prettyComponentFrame)
        self.compFrame.pack(fill="both",expand=1,**layout)
        self.dataFrame = ScrolledFrame(self.prettyDataFrame)
        self.dataFrame.pack(fill="both",expand=1,**layout)

        self.grid_rowconfigure(curRow, weight=1)

        curRow = curRow + 1
        self.domainsButton = Button(self,text="Domains", command=self.onDomain)
        self.domainsButton.grid(row = curRow,column = 0, sticky = "W",**layout)

        if DEV:
            self.subButton = Button(self,text="Subcomplexes",command=self.onSub)
            self.subButton.grid(row = curRow,column = 1, sticky = "W",**layout)

        curRow = curRow + 1
        self.saveAsButton = Button(self,text="Save as", command=self.onSaveAs)
        self.saveAsButton.grid(row = curRow,column = 0, sticky = "W",**layout)
        self.saveButton = Button(self,text="Save", command=self.onSave)
        self.saveButton.grid(row = curRow,column = 1, sticky = "W",**layout)
        self.loadButton = Button(self,text="Load project", command=self.onLoad)
        self.loadButton.grid(row = curRow,column = 2, sticky = "W",**layout)

        curRow = curRow + 1

        #Deploy the components in self.config
        for i,item in enumerate(self.config.items):
            itemFrame = ItemFrame(self,item=item)
            itemFrame.grid(row=i+1,\
                                column = 0,\
                                columnspan = 3,\
                                sticky = "W")
            self.componentFrames.append(itemFrame)

        self.pack(fill='both', expand=1)

    def __iter__(self):
        for componentFrame in self.componentFrames:
            yield componentFrame

    def clear(self):
        self.config.items = []
        self.update()

    def onDomain(self):
        compNames = self.config.getComponentNames()
        if not compNames:
            title = "No components yet"
            message = "Please add some components before configuring."
            tkMessageBox.showinfo(title,message,parent=self.master)
            return

        self.applies = []
        self.nameVars = []
        self.rangeVars = []
        row = 0
        self.menu = Toplevel()
        self.menu.title('Domains')
        frame = Frame(self.menu,padx=5,pady=5)
        lFrame = Frame(frame,padx=5,pady=5)
        iFrame = LabelFrame(frame,padx=5,pady=5,borderwidth=1)
        _domains = self.config.domains

        def _onDel(_comp,_dom):
            _comp.domains.remove(_dom)
            _updateList()

        def _onEdit(_apply):
            _apply.configure(bg="#00A8FF")

        def _onColorChange(dom,_apply,cOption=None):
            _onEdit(_apply)
            dom.color = cOption.get()
            if self.config.state != "unsaved":
                self.mainWindow.setTitle(self.config.file+"*")
                self.config.state = "changed"

        def _onApply(dom,name,cVar,ranges,cIds,_apply):
            dom.name = name.get()
            dom.comp = self.config.getComponentByName(cVar.get())
            dom.ranges = dom.parse(ranges.get())
            dom.chainIds = cIds.get()

            chimera.triggers.activateTrigger('configUpdated', self.config)

            if self.config.state != "unsaved":
                self.mainWindow.setTitle(self.config.file+"*")
                self.config.state = "changed"

            _apply.configure(bg="light grey")

        def _updateList():
            _str = lambda l: str(l)[1:-1]
            _del = lambda: _dict.__getitem__(_from).pop
            self.compVars = []
            self.nameVars = []
            self.rangeVars = []
            self.chainVars = []

            for child in lFrame.winfo_children():
                child.destroy()

            comps = self.config.getComponentWithDomains()

            lrow = 0
            self.applies=[]
            for i,c in enumerate(comps):
                for j,d in enumerate(c.domains):
                    dFrame =  LabelFrame(lFrame,padx=5,pady=1,borderwidth=1)
                    _apply = Button(dFrame,text=unichr(10004),\
                             command=lambda:_onApply(d,n,cVar,r,cIds,_apply))
                    self.applies.append(_apply)
                    _nameVar = StringVar("")
                    self.nameVars.append(_nameVar)
                    _nameVar.set(d.name)
                    _nameVar.trace("w",lambda n,i,m: _onEdit(_apply))
                    n = EntryField(dFrame,labelpos="we",label_text="Name: ",\
                               entry_width=9,\
                               entry_textvariable=_nameVar)
                    n.grid(sticky='WE', row=0,column=0,padx=5)
                    Label(dFrame,text="Subunit: ")\
                    .grid(sticky='WE', row=0,column=1,padx=5)
                    compVar = StringVar("")
                    self.compVars.append(compVar)
                    compVar.set(c.name)
                    compVar.trace("w",lambda n,i,m: _onEdit(_apply))
                    cMenu = OptionMenu(dFrame,compVar,*compNames)
                    cMenu.configure(width=5)
                    cMenu.grid(sticky='W', row=0,column=2)

                    rVar = StringVar("")
                    self.rangeVars.append(rVar)
                    rVar.set(d.rangeString())
                    rVar.trace("w",lambda n,i,m: _onEdit(_apply))
                    r = EntryField(dFrame,labelpos="w",\
                                   label_text="Ranges: ", entry_width=9,\
                                   entry_textvariable=rVar)
                    r.grid(sticky='WE', row=0,column=3,padx=5)

                    cVar = StringVar("")
                    self.chainVars.append(cVar)
                    cVar.set(str(d.getChainIds()))
                    cVar.trace("w",lambda n,i,m: _onEdit(_apply))
                    cIds = EntryField(dFrame,labelpos="w",\
                                   label_text="ChainIds: ", entry_width=9,\
                                   entry_textvariable=cVar)
                    cIds.grid(sticky='WE', row=0,column=4,padx=5)

                    cOption = ColorOption(dFrame,0,None,None,partial(_onColorChange,d,_apply),startCol=5)
                    cOption.set(d.color)

                    _apply.grid(sticky='WE', row=0,column=6,padx=5)
                    self.createToolTip(_apply,"Apply Changes")
                    _delete = Button(dFrame,text="x",\
                                     command=lambda:_onDel(c,d))
                    _delete.grid(sticky='WE', row=0,column=7,padx=5)
                    self.createToolTip(_delete,"Delete")

                    dFrame.grid(sticky='WE',row=lrow,column=0,pady=1)
                    lrow += 1
                    self.menu.grid()


        def _onAdd():
            name = nField.get()
            ranges = rField.get()
            color = cOption.get()
            chains = cField.get()
            subunit = self.config.getComponentByName(compVar.get())
            config = subunit.config
            d = Domain(name,config,subunit,ranges,color,chains)
            subunit.domains.append(d)
            _updateList()

            if self.config.state != "unsaved":
                self.mainWindow.setTitle(self.config.file+"*")
                self.config.state = "changed"

        def _onSave():
            chimera.triggers.activateTrigger('configUpdated', self.config)
            self.menu.destroy()


        Label(frame,text="Add Domains:")\
             .grid(row=row,column=0,sticky="W",pady=5)

        row+=1
        nField = EntryField(iFrame,labelpos="w",label_text="Name: ",\
                                             entry_width=9,\
                                             command=None)
        nField.grid(sticky='W', row=0,column=0,padx=5)
        Label(iFrame,text="Subunit: ").grid(row=0,column=1,sticky="W",padx=5)
        compVar = StringVar("")
        compMenu = OptionMenu(iFrame,compVar,*compNames)
        compMenu.configure(width=5)
        compMenu.grid(sticky='W', row=0,column=2)
        rField = EntryField(iFrame,labelpos="w",label_text="Ranges: ",\
                                             entry_width=9)
        rField.grid(sticky='W', row=0,column=3,padx=5)
        self.createToolTip(rField.interior(),"E.g.: 1-22,99,50-101")
        cField = EntryField(iFrame,labelpos="w",label_text="ChainIds: ",\
                                             entry_width=9)
        cField.grid(sticky='W', row=0,column=4,padx=5)
        cOption = ColorOption(iFrame,0,None,None,None,startCol=5)

        Button(frame,text="Add",command=_onAdd)\
               .grid(sticky="W",row=1,column=1,padx=5,pady=9)
        _updateList()


        iFrame.grid(sticky='WE', row=1,column=0)
        lFrame.grid(sticky='WE', row=2,column=0,columnspan=8)

        Button(frame,text="Save",command=_onSave)\
               .grid(sticky="W",row=3,column=0,padx=5,pady=9)

        frame.grid(sticky='WE', row=0,column=0)
        self.menu.grid()

    def onSub(self):
        domNames = self.config.getDomainNames()
        compNames = self.config.getComponentNames()
        names = domNames+compNames

        if not compNames:
            title = "No components or domains yet"
            message = "Please add some components or domains before configuring."
            tkMessageBox.showinfo(title,message,parent=self.master)
            return

        row = 0
        self.menu = Toplevel()
        frame = Frame(self.menu,padx=5,pady=5)
        lFrame = Frame(frame,padx=5,pady=5)
        iFrame = LabelFrame(frame,padx=5,pady=5,borderwidth=1)
        _domains = self.config.domains

        def _onDel(_comp,_dom):
            _comp.domains.remove(_dom)
            _updateList()


        def _onApply(dom,name,cVar,ranges,cIds,cOption):
            dom.name = name.get()
            dom.comp = self.config.getComponentByName(cVar.get())
            dom.ranges = dom.parse(ranges.get())
            dom.color = cOption.get()
            dom.chainIds = cIds.get()
            _apply.configure(bg="light grey")


        def _updateList():
            _str = lambda l: str(l)[1:-1]
            _del = lambda: _dict.__getitem__(_from).pop
            _compVars = []
            _nameVars = []

            for child in lFrame.winfo_children():
                child.destroy()

            domains = self.config.getDomains()

            lrow = 0
            for i,c in enumerate(comps):
                for j,d in enumerate(c.domains):
                    dFrame =  LabelFrame(lFrame,padx=5,pady=1,borderwidth=1)
                    _apply = Button(dFrame,text=unichr(10004),\
                             command=lambda:_onApply(d,n,cVar,r,cIds,cOption))
                    _nameVar = StringVar("")
                    _nameVars.append(_nameVar)
                    _nameVar.set(d.name)
                    _nameVar.trace("w",lambda n,i,m: n+i)
                    n = EntryField(dFrame,labelpos="we",label_text="Name: ",\
                               entry_width=9,\
                               entry_textvariable=_nameVar)
                    n.grid(sticky='WE', row=0,column=0,padx=5)
                    Label(dFrame,text="Subunit: ")\
                    .grid(sticky='WE', row=0,column=1,padx=5)
                    cVar = StringVar("")
                    cVar.set(d.comp.name)
                    cMenu = OptionMenu(dFrame,cVar,*compNames)
                    cMenu.configure(width=5)
                    cMenu.grid(sticky='W', row=0,column=2)
                    r = EntryField(dFrame,labelpos="w",\
                                   label_text="Ranges: ", entry_width=9,\
                                   value=d.rangeString())
                    r.grid(sticky='WE', row=0,column=3,padx=5)
                    cIds = EntryField(dFrame,labelpos="w",\
                                   label_text="ChainIds: ", entry_width=9,\
                                   value=str(d.getChainIds()))
                    cIds.grid(sticky='WE', row=0,column=4,padx=5)

                    cOption = ColorOption(dFrame,0,None,None,None,startCol=5)
                    cOption.set(d.color)

                    _apply.grid(sticky='WE', row=0,column=6,padx=5)
                    self.createToolTip(_apply,"Apply Changes")
                    _delete = Button(dFrame,text="x",\
                                     command=lambda:_onDel(c,d))
                    _delete.grid(sticky='WE', row=0,column=7,padx=5)
                    self.createToolTip(_delete,"Delete")

                    dFrame.grid(sticky='WE',row=lrow,column=0,pady=1)
                    lrow += 1

                    self.menu.grid()

        def _onAdd():
            name = nField.get()
            ranges = rField.get()
            color = cOption.get()
            chains = cField.get()
            subunit = self.config.getComponentOrDomain(compVar.get())
            config = subunit.config
            if isinstance(subunit,Component):
                d = Domain(name,config,subunit,ranges,color,chains)
            elif isinstance(subunit,Domain):
                d = subunit
            subcomplex = Subcomplex(name,config)
            _updateList()

        def _onSave():
            chimera.triggers.activateTrigger('configUpdated', self.config)
            self.menu.destroy()


        Label(frame,text="Add Subcomplexes:")\
             .grid(row=row,column=0,sticky="W",pady=5)

        row+=1
        nField = EntryField(iFrame,labelpos="w",label_text="Name: ",\
                                             entry_width=9,\
                                             command=None)
        nField.grid(sticky='W', row=0,column=0,padx=5)
        Label(iFrame,text="Subunit/Domain: ")\
             .grid(row=0,column=1,sticky="W",padx=5)
        compVar = StringVar("")
        compMenu = OptionMenu(iFrame,compVar,*names)
        compMenu.configure(width=5)
        compMenu.grid(sticky='W', row=0,column=2)
        rField = EntryField(iFrame,labelpos="w",label_text="Ranges: ",\
                                             entry_width=9)
        rField.grid(sticky='W', row=0,column=3,padx=5)
        self.createToolTip(rField.interior(),"E.g.: 1-22,99,50-101")
        cField = EntryField(iFrame,labelpos="w",label_text="ChainIds: ",\
                                             entry_width=9)
        cField.grid(sticky='W', row=0,column=4,padx=5)
        cOption = ColorOption(iFrame,0,None,None,None,startCol=5)

        Button(frame,text="Add",command=_onAdd)\
               .grid(sticky="W",row=1,column=1,padx=5,pady=9)
        _updateList()


        iFrame.grid(sticky='WE', row=1,column=0)
        lFrame.grid(sticky='WE', row=2,column=0,columnspan=8)

        Button(frame,text="Save",command=_onSave)\
               .grid(sticky="W",row=3,column=0,padx=5,pady=9)

        frame.grid(sticky='WE', row=0,column=0)
        self.menu.grid()


    def onComponentAdd(self):
        if self.addComponentFrame.populate():
            self.config.addItem(self.addComponentFrame.item)
            self.addComponentFrame.item = Component("",self.config)
            self.addComponentFrame.empty()
            self.update()

    def onDataItemAdd(self):
        if self.addDataFrame.populate():
            if self.addDataFrame.item.type == "data":
                raise UserError("No Datatype specified")
            else:
                if self.checkName(self.addDataFrame.item):
                    self.config.addItem(self.addDataFrame.item)
                    self.addDataFrame.item = DataItem("",self.config,None)
                    self.addDataFrame.empty()
                    self.update()
                else:
                    title = "Chose different Name"
                    message = "This name is already occupied by a different data item. For consistencies' sake, please use a different name."
                    tkMessageBox.showinfo(title,message,parent=self.master)

    def onLoad(self):
        if self.resMngr.loadAssembly(self):
            self.clear()
        self.update()
        self.mainWindow.setTitle(self.config.file)
        self.config.state="unchanged"

    def onSaveAs(self):
        self.resMngr.saveAssembly(self)
        self.mainWindow.setTitle(self.config.file)
        self.config.state="unchanged"

    def onSave(self):
        if self.config.state == "unsaved":
            self.resMngr.saveAssembly(self)
        else:
            self.resMngr.saveAssembly(self,False)
        self.mainWindow.setTitle(self.config.file)
        self.config.state="unchanged"

    def update(self):
        #remove non neccessary frames
        for i in range(len(self.itemFrames)):
            if not self.itemFrames[i].item in self.config.items:
                self.itemFrames[i].destroy()
                self.itemFrames[i] = None
        #add frame for none present items
        self.itemFrames = [f for f in self.itemFrames if f is not None]

        for i in self.config.items:
            if i not in [f.item for f in self.itemFrames]:
                self.addItemFrame(i)

        if self.config.state != "unsaved":
            self.mainWindow.setTitle(self.config.file+"*")
            self.config.state = "changed"

        chimera.triggers.activateTrigger('configUpdated', self.config)


    def addItemMenu(self):
        resourcePath = StringVar()
        dataType = StringVar()
        dataType.set("DataType")
        componentName = StringVar()

        def loadItemFile():
            resourcePath.set(tkFileDialog.askopenfilename())

        menu = Toplevel()
        frame = LabelFrame(menu,text="Configure Item")

        Label(frame,text="Resource Path: ",\
                    pady=5).grid(row=0,column=0,sticky='W')
        Entry(frame,textvariable=resourcePath,)\
             .grid(row=0,column=1,pady=5,padx=5)
        Button(frame,text="Load resource",\
                     command=loadItemFile)\
              .grid(row=0,column=2,pady=5)

        Label(frame,text="Data Type: ",\
                    pady=5).grid(row=1,column=0,sticky='W')
        OptionMenu(frame,\
                   dataType,\
                   "Xquest",\
                   "Interaction Site",\
                   "Sequences")\
                  .grid(row=1,column=1,sticky='W',pady=5,padx=5)

        Label(frame,text="Name: ")\
             .grid(row=2,column=0,sticky='W',pady=5)
        Entry(frame,textvariable=componentName)\
             .grid(row=2,column=1,sticky='W',pady=5,padx=5)

        Button(frame,text="Add Item",command=menu.destroy)\
              .grid(row=3,column=0,sticky='W',pady=5,padx=5)

        frame.grid(pady=5,padx=5)
        menu.grid()

    def addItemFrame(self,item):
        if  issubclass(item.__class__,Item):
            if type(item) == Component:
                itemFrame = ItemFrame(self.compFrame.interior(),\
                                           item,\
                                           self)
            else:
                itemFrame = ItemFrame(self.dataFrame.interior(),\
                                        item,\
                                        self)
            itemFrame.grid(columnspan = 3, sticky = "WE")
            self.itemFrames.append(itemFrame)

            #if InteractingResidueItem present, add corresponding tab
            if item.type == xlinkanalyzer.INTERACTING_RESI_DATA_TYPE:
                if not hasattr(xlinkanalyzer.get_gui(), 'Interacting'):
                    xlinkanalyzer.get_gui().addTab('Interacting', InteractingResiMgrTabFrame)

    def checkName(self,item):
        if item.name in [item.name for item in self.config]:
            return False
        else:
            return True

    def createToolTip(self, widget, text):
        toolTip = ToolTip(widget)
        def enter(event):
            toolTip.showtip(text)
        def leave(event):
            toolTip.hidetip()
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

class DataMgrTabFrame(TabFrame):
    def __init__(self, master, *args, **kwargs):
        TabFrame.__init__(self, master, *args, **kwargs)

        Label(self, text="Add data in Setup tab").pack(anchor='w', pady=1)

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def reload(self, name, userData, cfg):
        self.clear()
        curRow = 0
        Label(self, anchor='w', bg='white', padx=4, pady=4,
                text='This panel allows selecting which data sets should be used for displaying cross-links and statistics.').grid(row=curRow, columnspan=2)
        curRow += 1

        if len(self.config.getDataItems()) > 0:


            for item in self.config.getDataItems():
                Label(self, text=item.name).grid(row=curRow, column=0)

                var = Tkinter.BooleanVar()
                var.set(True)
                btn = Tkinter.Checkbutton(self,
                    variable=var,
                    command=lambda rebindItem=item, rebindVar=var: self.toggleActive(rebindItem, rebindVar))
                btn.var = var
                btn.grid(row = curRow, column=1)
                curRow += 1

    def toggleActive(self, item, var):
        item.active = var.get()
        chimera.triggers.activateTrigger('activeDataChanged', self)


class ComponentsTabFrame(TabFrame):
    def __init__(self, master, *args, **kwargs):
        TabFrame.__init__(self, master, *args, **kwargs)

        Label(self, text="Add subunits Setup tab").pack(anchor='w', pady=1)

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def reload(self, name, userData, cfg):
        if len(cfg.getComponentNames()) > 0:
            self.clear()

            modelSelect = xlinkanalyzer.get_gui().modelSelect.create(self)
            modelSelect.pack(anchor='w', fill = 'both', pady=1)

            # curRow = 0
            f1 = Tkinter.Frame(self)
            Label(f1, text="Choose action: ").pack(side='left')
            self.componentsTabHandlerOptMenu = ComponentsHandleOptionMenu(f1)

            self.componentsTabHandlerOptMenu.pack(side='left')

            f1.pack(anchor='w', pady=1)

            f2 = LabelFrame(self, bd=4, relief="groove", text='Apply to:', padx=4, pady=4)
            f2.pack(anchor='w', pady=1)
            self.addComponentButtons(f2, callback=self.handleComponent, startRow=0)

            f3 = Tkinter.Frame(self)
            f3.pack(anchor='w', pady=4)

            btn = Tkinter.Button(f3,
                text='Show all subunits',
                command=self.showAllComponents)

            btn.pack(side='left')


            btn = Tkinter.Button(f3,
                text='Color all subunits',
                command=self.colorAllComponents)

            btn.pack(side='left')

        else:
            self.clear()
            Label(self, text="Add some components first").pack(anchor='w', pady=1)


    def handleComponent(self, name):
        handler = self.componentsTabHandlerOptMenu.var.get()
        if handler == 'Select':
            self.selectComponent(name)
        elif handler == 'Show':
            self.showComponent(name)
        elif handler == 'Show only':
            self.showComponentOnly(name)
        elif handler == 'Hide':
            self.hideComponent(name)

    def addComponentButtons(self, parent, callback, startRow=0):
        cols = 4
        cur_row = startRow
        cur_col = 0
        cfg = xlinkanalyzer.get_gui().configFrame.config

        for i, name in enumerate(cfg.getComponentNames()):
            color_cfg = cfg.getComponentColors(name)
            color = cfg.getColor(name)

            if color_cfg is None:
                color = chimera.MaterialColor(0,0,0)

            rgb = [int(255*x) for x in color.rgba()[:3]]
            color = '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])

            if is_mac():
                ttk.Style().configure(str(i)+'.TButton', foreground=color)
                btn = ttk.Button(parent,
                    text=name,
                    style=str(i)+'.TButton',
                    command=lambda rebind=name: callback(rebind))
            else:
                btn = Tkinter.Button(parent,
                    text=name,
                    foreground=color,
                    command=lambda rebind=name: callback(rebind))
            # btn.pack(side=Tkinter.TOP)
            btn.grid(row = cur_row, column = cur_col)
            cur_col = cur_col + 1
            if cur_col == cols:
                cur_col = 0
                cur_row = cur_row + 1

        return cur_row


    def selectComponent(self, name):
        self.getActiveModels()
        # selectItems = []
        modelIds = []

        for model in self.models:
            modelIds.append(str(model.chimeraModel.id))
            # selectItems.append(' #' + str(model.chimeraModel.id) + self.config.component_selections[name])

        selectStr =  ' #' +','.join(modelIds) + \
                              self.config.getComponentSelections(name)
        runCommand('select ' + selectStr)

    def showComponentOnly(self, name):
        self.getActiveModels()
        for model in self.models:
            if model.active:
                model.showOnly(name)

    def showComponent(self, name):
        self.getActiveModels()
        for model in self.models:
            if model.active:
                model.show(name)

    def hideComponent(self, name):
        self.getActiveModels()
        for model in self.models:
            if model.active:
                model.hide(name)

    def showAllComponents(self):
        self.getActiveModels()
        for model in self.models:
            if model.active:
                model.showAll()

    def colorAllComponents(self):
        self.getActiveModels()
        for model in self.models:
            if model.active:
                model.colorAll()

class LdScoreFilterEntry(EntryField):
    def __init__(self, parent, var, command):
        self.var = var
        EntryField.__init__(self, parent,
                labelpos = 'w',
                value = '0.0',
                label_text = 'Custom (from 0 to 100)',
                # validate = {'validator' : 'real'},
                validate = {'validator' : 'real',
                        'min' : 0, 'max' : 100, 'minstrict' : 1},
                entry_textvariable = self.var,
                modifiedcommand = command)
        command1 = lambda x,y,z: command()
        self.var.trace('w', command1)

class LdScoreFilterScale(Tkinter.Scale):
    def __init__(self, parent, var):
        self.var = var
        Tkinter.Scale.__init__(self, parent,
                orient=Tkinter.HORIZONTAL,
                length=300,
                from_=0,
                to=100,
                variable=self.var
                )

class XlinkLengthThresholdEntry(EntryField):
    def __init__(self, parent, lengthThreshVar):
        self.var = lengthThreshVar
        EntryField.__init__(self, parent,
                labelpos = 'w',
                value = '30.0',
                label_text = 'Xlink length threshold',
                entry_textvariable = self.var,
                validate = {'validator' : 'real',
                        'min' : 0, 'minstrict' : 1})

class LengthThresholdLabel(Label):
    def __init__(self, parent):
        self.textSrc = string.Template("Current length threshold: $val A")
        self.var = StringVar()
        self.var.set(self.textSrc.substitute({'val': xlinkanalyzer.XLINK_LEN_THRESHOLD}))
        Label.__init__(self, parent, textvariable=self.var)

        self._handlers = []

        self._addHandlers()

    def destroy(self):
        self._deleteHandlers()
        Label.destroy(self)

    def _addHandlers(self):
        handler = chimera.triggers.addHandler('lengthThresholdChanged',lambda x, y, val: self.var.set(self.textSrc.substitute({'val': val})), None)
        self._handlers.append((chimera.triggers, 'lengthThresholdChanged', handler))

    def _deleteHandlers(self):
        if not self._handlers:
            return
        while self._handlers:
            triggers, trigName, handler = self._handlers.pop()
            triggers.deleteHandler(trigName, handler)

class XlinkToolbar(Tkinter.Frame):
    def __init__(self, master, ld_score_var, lengthThreshVar, xlinkMgrTabFrame, *args, **kwargs):
        Tkinter.Frame.__init__(self, master, borderwidth=2, relief='groove', padx=4, pady=4, *args, **kwargs)
        self.ld_score_var = ld_score_var
        self.lengthThreshVar = lengthThreshVar
        self.xlinkMgrTabFrame = xlinkMgrTabFrame

        curRow = 0

        ldscoreThresholdFrame = Tkinter.Frame(self, borderwidth=2, relief='groove', padx=4, pady=4)
        ldscoreThresholdFrame.grid(row = curRow, column = 0, sticky="we")
        scoresFrame = Tkinter.Frame(ldscoreThresholdFrame)
        scoresFrame.pack()
        # scoresFrame.grid(row = curRow, column = 0)
        Label(scoresFrame, text="Minimal xlink score").pack(side='left')

        btn = Tkinter.Button(scoresFrame,
            text='20',
            # foreground=color,
            command=lambda: ld_score_var.set(20.0))
        btn.pack(side='left')

        btn = Tkinter.Button(scoresFrame,
            text='25',
            # foreground=color,
            command=lambda: ld_score_var.set(25.0))
        btn.pack(side='left')

        btn = Tkinter.Button(scoresFrame,
            text='30',
            # foreground=color,
            command=lambda: ld_score_var.set(30.0))
        btn.pack(side='left')

        # curRow += 1

        customScoresFrame = Tkinter.Frame(ldscoreThresholdFrame)
        customScoresFrame.pack()
        curRow += 1

        self.generalTabldScoreFilter = LdScoreFilterEntry(customScoresFrame, ld_score_var, self.reshowByLdScore)
        self.generalTabldScoreFilter.pack()


        self.generalTabldScoreFilterScale = LdScoreFilterScale(
            customScoresFrame,
            ld_score_var)
        self.generalTabldScoreFilterScale.pack()


        lengthThresholdFrame = Tkinter.Frame(self, borderwidth=2, relief='groove', padx=4, pady=4)
        lengthThresholdFrame.grid(row=curRow, column=0)
        curRow += 1
        lengthThresholdEntry = XlinkLengthThresholdEntry(lengthThresholdFrame, self.lengthThreshVar)
        lengthThresholdEntry.grid(row=1, column=0)
        btn = Tkinter.Button(lengthThresholdFrame,
            text='Apply',
            command=lambda: chimera.triggers.activateTrigger('lengthThresholdChanged', lengthThresholdEntry.var.get()))
        btn.grid(row=1, column=1)
        LengthThresholdLabel(lengthThresholdFrame).grid(row=0, column=0, sticky='w')


        curRow = 1
        btn = Tkinter.Button(self,
            text='Reset view',
            command=self.resetView)
        btn.grid(row = curRow, column=1, sticky='s', padx=2, pady=2)
        curRow += 1

        self._handlers = []
        self._addHandlers()

    def destroy(self):
        self._deleteHandlers()
        Tkinter.Frame.destroy(self)

    def _addHandlers(self):
        handler = chimera.triggers.addHandler('lengthThresholdChanged', self.onLengthThresholdChanged, None)
        self._handlers.append((chimera.triggers, 'lengthThresholdChanged', handler))

    def _deleteHandlers(self):
        if not self._handlers:
            return
        while self._handlers:
            triggers, trigName, handler = self._handlers.pop()
            triggers.deleteHandler(trigName, handler)

    def onLengthThresholdChanged(self, x, y, val):
        xlinkanalyzer.XLINK_LEN_THRESHOLD = val
        self.xlinkMgrTabFrame.restyleXlinks()

    def reshowByLdScore(self):
        val = self.ld_score_var.get()
        dataMgrs = self.xlinkMgrTabFrame.getXlinkDataMgrs()
        try:
            minScore = float(val)
        except ValueError:
            pass
        else:
            for mgr in dataMgrs:
                if hasattr(mgr, 'objToXlinksMap'):
                    if self.xlinkMgrTabFrame.smartMode.get():
                        mgr.show_xlinks_smart(xlinkanalyzer.XLINK_LEN_THRESHOLD, show_only_one=self.xlinkMgrTabFrame.showFirstOnlyOliMode.get())
                    else:
                        mgr.showAllXlinks()
                    mgr.hide_by_ld_score(minScore)

    def resetView(self):
        dataMgrs = self.xlinkMgrTabFrame.getXlinkDataMgrs() #TODO: remove when modelList widget will be updating self.models and self.dataMgrs

        self.xlinkMgrTabFrame.showAllXlinks()
        for dataMgr in dataMgrs:
            dataMgr.resetView()

class ColorXlinkedFrame(Tkinter.Frame):
    def __init__(self, master, xlinkMgrTabFrame, *args, **kwargs):
        Tkinter.Frame.__init__(self, master, *args, **kwargs)
        self.xlinkMgrTabFrame = xlinkMgrTabFrame
        curRow = 0

        Label(self, anchor='w', bg='white', padx=4, pady=4,
                text='This panel allows coloring cross-linked residues').grid(row = curRow, columnspan=2, sticky="we")
        curRow += 1

        modelSelect = xlinkanalyzer.get_gui().modelSelect.create(self)
        modelSelect.grid(row = curRow, columnspan=2, sticky="we")
        curRow += 1

        self.compOptMenuFrom = ComponentsOptionMenu(self, 'on subunit (def: all)', xlinkMgrTabFrame.config)
        self.compOptMenuFrom.grid(row = curRow, column = 0)
        self.compOptMenuTo = ComponentsDomainsOptionMenu(self, 'to subunit or domain (def: all)', xlinkMgrTabFrame.config)
        self.compOptMenuTo.grid(row = curRow, column=1)
        curRow += 1

        self.colorOptionVar = Tkinter.IntVar()
        self.colorOptionVar.set(1)

        Tkinter.Radiobutton(self, text="Color red", variable=self.colorOptionVar, value=1).grid(row=curRow, columnspan=2, sticky='w')
        curRow += 1
        Tkinter.Radiobutton(self, text="Color by a color of xlinked subunit or domain", variable=self.colorOptionVar, value=2).grid(row=curRow, columnspan=2, sticky='w')
        curRow += 1

        var = Tkinter.BooleanVar()
        self.uncolorOthersBtn = Tkinter.Checkbutton(self,
            text="Clear showing of other xlinked residues",
            variable=var)
        self.uncolorOthersBtn.var = var
        self.uncolorOthersBtn.grid(row = curRow, columnspan=2, sticky='w')
        curRow += 1

        btn = Tkinter.Button(self,
            text='Color',
            # foreground=color,
            command=self.colorXlinked)

        btn.grid(row = curRow, column=1, sticky='e')
        curRow += 1

    def colorXlinked(self):
        dataMgrs = self.xlinkMgrTabFrame.getXlinkDataMgrs() #TODO: remove when modelList widget will be updating self.models and self.dataMgrs

        fromComp = None
        fromCompSel = self.compOptMenuFrom.var.get()
        if fromCompSel in self.xlinkMgrTabFrame.config.getComponentNames():
            fromComp = fromCompSel

        to = self.compOptMenuTo.getSelected()

        colorOption = self.colorOptionVar.get()
        color = None
        colorByCompTo = False
        if colorOption == 1:
            color = "red"
        elif colorOption == 2:
            colorByCompTo = True

        if self.uncolorOthersBtn.var.get():
            uncolorOthers = True
        else:
            uncolorOthers = False

        for mgr in dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                mgr.color_xlinked(to=to, fromComp=fromComp, minLdScore=mgr.minLdScore, color=color, colorByCompTo=colorByCompTo, uncolorOthers=uncolorOthers)


class XlinkMgrTabFrame(TabFrame):
    def __init__(self, master, *args, **kwargs):
        TabFrame.__init__(self, master, *args, **kwargs)
        Label(self, text="Load cross-files using Setup tab. See Tutorial for instructions.").pack(anchor='w', pady=1)
        self.dataMgrs = []
        self._onModelRemoveHandler = chimera.openModels.addRemoveHandler(self.onModelRemove, None)
        self._addHandlers()

        self.showFirstOnlyOliMode = Tkinter.BooleanVar()
        self.showFirstOnlyOliMode.set(False)

        self.smartMode = Tkinter.BooleanVar()
        self.smartMode.set(False)

    def _addHandlers(self):
        TabFrame._addHandlers(self)
        handler = chimera.triggers.addHandler('lengthThresholdChanged', self.onLengthThresholdChanged, None)
        self._handlers.append((chimera.triggers, 'lengthThresholdChanged', handler))

        handler = chimera.triggers.addHandler('CoordSet', self.onCoordSet, None)
        self._handlers.append((chimera.triggers, 'CoordSet', handler))

        handler = chimera.triggers.addHandler('activeDataChanged', self.onActiveDataChanged, None)
        self._handlers.append((chimera.triggers, 'activeDataChanged', handler))


    def destroy(self):
        chimera.openModels.deleteRemoveHandler(self._onModelRemoveHandler)
        TabFrame.destroy(self)

    def onModelRemove(self, trigger, userData, removedModels):
        for dataMgr in self.dataMgrs:
            if hasattr(dataMgr, 'objToXlinksMap'):
                if dataMgr.model.chimeraModel in removedModels:
                    dataMgr.destroy()
                    self.dataMgrs.remove(dataMgr)

        for model in self.models:
            if model in removedModels:
                self.models.remove(model)

    def onActiveDataChanged(self, trigger, userData, sth):
        self.getActiveModels()

        for mgr in self.dataMgrs:
            mgr.reload(self.config)

        if hasattr(self, 'modelStatsTable'):
            self.modelStatsTable.render()

        self.restyleXlinks()

    def onCoordSet(self, trigger, additional, coordChanges):
        self.restyleXlinks()

    def getActiveData(self):
        dataType = xlinkanalyzer.XQUEST_DATA_TYPE
        data = []
        for item in self.config.getDataItems():
            if item.active and item.type == dataType:
                data.append(item)
        return data

    def getXlinkDataMgrs(self):
        self.getActiveModels()
        dataMgrsForActive = []
        for model in self.models:
            xlinkDataMgrsForModel = []
            for mgr in self.dataMgrs:
                if hasattr(mgr, 'objToXlinksMap') and mgr.model is model:
                    xlinkDataMgrsForModel.append(mgr)
            if len(xlinkDataMgrsForModel) == 0:
                xlinkDataMgrsForModel.append(XlinkDataMgr(model, self.getActiveData()))
                self.dataMgrs.extend(xlinkDataMgrsForModel)
            dataMgrsForActive.extend(xlinkDataMgrsForModel)
        self.restyleXlinks()

        return dataMgrsForActive

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def reload(self, name, userData, cfg):

        if xlinkanalyzer.XQUEST_DATA_TYPE in [item.type for item in self.config.getDataItems()]:
            self.clear()

            xlNotebook = Pmw.NoteBook(self)
            xlNotebook.pack(fill = 'both', expand = 1, padx = 2, pady = 2)
            self.xlNotebook = xlNotebook

            curRow = 0
            totalCols = 2

            generalTabName = 'General'
            xlNotebook.add(generalTabName)

            modelSelect = xlinkanalyzer.get_gui().modelSelect.create(xlNotebook.page(generalTabName))
            modelSelect.grid(row = curRow, columnspan=totalCols, sticky="we")
            curRow += 1

            btn = Tkinter.Button(xlNotebook.page(generalTabName),
                text='Display crosslinks',
                # foreground=color,
                command=self.displayDefault)
            btn.grid(row = curRow, columnspan=totalCols)
            curRow += 1

            btn = Tkinter.Button(xlNotebook.page(generalTabName),
                text='Show all xlinks',
                # foreground=color,
                command=self.showAllXlinks)
            btn.grid(row = curRow, column = 0)

            btn = Tkinter.Button(xlNotebook.page(generalTabName),
                text='Hide all xlinks',
                # foreground=color,
                command=self.hideAllXlinks)
            btn.grid(row = curRow, column = 1)
            curRow += 1

            btn = Tkinter.Button(xlNotebook.page(generalTabName),
                text='Hide intra xlinks',
                # foreground=color,
                command=self.hideIntraXlinks)
            btn.grid(row = curRow, column = 0)

            btn = Tkinter.Button(xlNotebook.page(generalTabName),
                text='Hide inter xlinks',
                # foreground=color,
                command=self.hideInterXlinks)
            btn.grid(row = curRow, column = 1)
            curRow += 1

            self.smartModeBtn = Tkinter.Checkbutton(xlNotebook.page(generalTabName),
                text="Smart homoligomers mode",
                variable=self.smartMode,
                command=self.onSmartModeChange)
            self.smartModeBtn.var = self.smartMode
            if DEV:
                self.smartModeBtn.grid(sticky='E', row=curRow, column=0)
                Button(xlNotebook.page(generalTabName), text="Configure", command=self.configureOligomeric)\
                    .grid(sticky='W', row=curRow, column=1)
            else:
                self.smartModeBtn.grid(row=curRow, columnspan=totalCols)

            curRow += 1

            self.ld_score_var = Tkinter.DoubleVar()
            self.lengthThreshVar = Tkinter.DoubleVar()

            xlinkToolbar = XlinkToolbar(xlNotebook.page(generalTabName), self.ld_score_var, self.lengthThreshVar, self)
            xlinkToolbar.grid(row = curRow, columnspan=totalCols, padx=4, pady=4)
            curRow += 1

            modifiedTabName = 'Modified'
            xlNotebook.add(modifiedTabName)

            curRow = 0
            self.showModifiedFrame = ShowModifiedFrame(xlNotebook.page(modifiedTabName), self).grid(row=curRow, column=0)
            curRow += 1


            xlinkToolbar = XlinkToolbar(xlNotebook.page(modifiedTabName), self.ld_score_var, self.lengthThreshVar, self)
            xlinkToolbar.grid(row = curRow, column=0, padx=4, pady=4)

            curRow = 0
            colorXlinkedTabName = 'Color xlinked'
            xlNotebook.add(colorXlinkedTabName)

            self.colorXlinkedFrame = ColorXlinkedFrame(xlNotebook.page(colorXlinkedTabName), self)
            self.colorXlinkedFrame.grid(row = curRow, column = 0, padx=4, pady=4)
            curRow += 1


            xlinkToolbar = XlinkToolbar(xlNotebook.page(colorXlinkedTabName), self.ld_score_var, self.lengthThreshVar, self)
            xlinkToolbar.grid(row = curRow, columnspan=2, padx=4, pady=4)
            curRow += 1

            curRow = 0
            showXlinksFromTabName = 'Show xlinks from'
            xlNotebook.add(showXlinksFromTabName)

            Label(xlNotebook.page(showXlinksFromTabName), anchor='w', bg='white', padx=4, pady=4,
                    text='This panel allows displaying cross-links between specific subunits').grid(row = curRow, columnspan=2, sticky="we")
            curRow += 1

            modelSelect = xlinkanalyzer.get_gui().modelSelect.create(xlNotebook.page(showXlinksFromTabName))
            modelSelect.grid(row = curRow, columnspan=2, sticky="we")
            curRow += 1

            self.showXlinksFromTabNameCompOptMenuFrom = ComponentsOptionMenu(xlNotebook.page(showXlinksFromTabName), 'from subunit', self.config)
            self.showXlinksFromTabNameCompOptMenuFrom.grid(row = curRow, column = 0)

            self.showXlinksFromTabNameCompOptMenuTo = ComponentsOptionMenu(xlNotebook.page(showXlinksFromTabName), 'to all', self.config)
            self.showXlinksFromTabNameCompOptMenuTo.grid(row = curRow, column = 1)
            curRow += 1

            self.showXlinksFromTabsmartModeBtn = Tkinter.Checkbutton(xlNotebook.page(showXlinksFromTabName),
                text="Smart homoligomers mode",
                variable=self.smartMode,
                command=self.showXlinksFrom)
            self.showXlinksFromTabsmartModeBtn.var = self.smartMode
            self.showXlinksFromTabsmartModeBtn.grid(sticky='E', row=curRow, column=0)

            Button(xlNotebook.page(showXlinksFromTabName), text="Configure", command=self.configureOligomeric)\
                .grid(sticky='W', row=curRow, column=1)

            curRow += 1

            var = Tkinter.BooleanVar()
            var.set(True)
            self.showXlinksFromTabhideOthersBtn = Tkinter.Checkbutton(xlNotebook.page(showXlinksFromTabName),
                text="Hide other xlinks",
                variable=var,
                command=self.showXlinksFrom)
            self.showXlinksFromTabhideOthersBtn.var = var
            self.showXlinksFromTabhideOthersBtn.grid(row = curRow, columnspan=2)
            curRow += 1


            btn = Tkinter.Button(xlNotebook.page(showXlinksFromTabName),
                text='Show',
                command=self.showXlinksFrom)

            btn.grid(row = curRow, columnspan=2)
            curRow += 1

            xlinkToolbar = XlinkToolbar(xlNotebook.page(showXlinksFromTabName), self.ld_score_var, self.lengthThreshVar, self)
            xlinkToolbar.grid(row = curRow, columnspan=2, padx=4, pady=4)
            curRow += 1

            curRow = 0
            xlinksStatsTabName = 'Statistics'
            xlNotebook.add(xlinksStatsTabName)
            body = Pmw.ScrolledFrame(xlNotebook.page(xlinksStatsTabName),
                borderframe=0,
                horizflex='expand'
                )
            body.pack(fill='both', expand=1)


            self.modelStatsTable = ModelXlinkStatsTable(body.interior(), self)

            self.modelStatsTable.pack(fill='both')

    def configureOligomeric(self):
        menu = Toplevel()
        w = menu.winfo_screenwidth()
        h = menu.winfo_screenheight()
        x = w/2
        y = h/2
        menu.geometry("+%d+%d" % (x, y))
        menu.geometry("400x200")

        frame = Frame(menu, padx=5, pady=5)

        curRow = 0

        btn = Tkinter.Checkbutton(frame,
                                  variable=self.showFirstOnlyOliMode,
                                  command=self.showAllXlinks)
        btn.var = self.showFirstOnlyOliMode
        btn.grid(row=curRow, column=0)
        Label(frame, text='Show only first xlink').grid(row=curRow, column=1)
        curRow += 1

        frame.pack()

    def displayDefault(self):
        self.getXlinkDataMgrs()
        self.showAllXlinks()
        self.restyleXlinks()

    def showXlinksFrom(self):
        dataMgrs = self.getXlinkDataMgrs()
        fromComp = None
        fromCompSel = self.showXlinksFromTabNameCompOptMenuFrom.var.get()
        if fromCompSel in self.config.getComponentNames():
            fromComp = fromCompSel

        if fromComp is not None:
            toComp = None
            toCompSel = self.showXlinksFromTabNameCompOptMenuTo.var.get()
            if toCompSel in self.config.getComponentNames():
                toComp = toCompSel

            for mgr in dataMgrs:
                if hasattr(mgr, 'objToXlinksMap'):
                    if self.smartMode.get():
                        smart = True
                    else:
                        smart = False

                    if self.showXlinksFromTabhideOthersBtn.var.get():
                        hide_others = True
                    else:
                        hide_others = False

                    mgr.show_xlinks_from(fromComp, to=toComp, threshold=xlinkanalyzer.XLINK_LEN_THRESHOLD, hide_others=hide_others, smart=smart, show_only_one=self.showFirstOnlyOliMode.get())
        else:
            raise UserError("Select \"from subunit\"")

        self.restyleXlinks()

    def hideAllXlinks(self):
        dataMgrs = self.getXlinkDataMgrs()
        for mgr in dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                mgr.hideAllXlinks()

    def hideIntraXlinks(self):
        dataMgrs = self.getXlinkDataMgrs()
        for mgr in dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                mgr.hide_intra_xlinks()

    def hideInterXlinks(self):
        dataMgrs = self.getXlinkDataMgrs()
        for mgr in dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                mgr.hideInterxlinks()

    def showAllXlinks(self):
        dataMgrs = self.getXlinkDataMgrs()
        for mgr in dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                if self.smartMode.get():
                    mgr.show_xlinks_smart(xlinkanalyzer.XLINK_LEN_THRESHOLD, show_only_one=self.showFirstOnlyOliMode.get())
                else:
                    mgr.showAllXlinks()
                    mgr.hide_by_ld_score(mgr.minLdScore)

    def onSmartModeChange(self):
        dataMgrs = self.getXlinkDataMgrs()
        val = self.ld_score_var.get()
        try:
            minScore = float(val)
        except ValueError:
            pass

        for mgr in dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                if self.smartMode.get():
                    mgr.show_xlinks_smart(xlinkanalyzer.XLINK_LEN_THRESHOLD, show_only_one=self.showFirstOnlyOliMode.get())
                else:
                    mgr.showAllXlinks()
                    mgr.hide_by_ld_score(minScore)

    def showXlinksSmart(self):
        dataMgrs = self.getXlinkDataMgrs()
        for mgr in dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                mgr.show_xlinks_smart(xlinkanalyzer.XLINK_LEN_THRESHOLD, show_only_one=self.showFirstOnlyOliMode.get())

    def onLengthThresholdChanged(self, x, y, val):
        dataMgrs = self.getXlinkDataMgrs()
        if self.smartMode.get():
            for mgr in dataMgrs:
                if hasattr(mgr, 'objToXlinksMap'):
                    mgr.show_xlinks_smart(val, show_only_one=self.showFirstOnlyOliMode.get())

    def restyleXlinks(self):
        for mgr in self.dataMgrs:
            if hasattr(mgr, 'objToXlinksMap'):
                xmanager.restyleXlinks([mgr], xlinkanalyzer.XLINK_LEN_THRESHOLD)

class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        label = Label(tw, text=self.text, justify='left',
                      background="#ffffe0", relief='solid', borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class InteractingResiMgrTabFrame(TabFrame):
    def __init__(self, master, *args, **kwargs):
        TabFrame.__init__(self, master, *args, **kwargs)

        Label(self, text="This is experimental feature, and data must be added manually to the json file").pack(anchor='w', pady=1)
        self.dataMgrs = []

        self._onModelRemoveHandler = chimera.openModels.addRemoveHandler(self.onModelRemove, None)

    def destroy(self):
        chimera.openModels.deleteRemoveHandler(self._onModelRemoveHandler)

    def onModelRemove(self, trigger, userData, models):
        validDataMgrs = []
        validModels = []
        for model in models:
            for dataMgr in self.dataMgrs:
                if dataMgr.model.chimeraModel is not model:
                    validDataMgrs.append(dataMgr)

            for prevModel in self.models:
                if prevModel.chimeraModel is not model:
                    validModels.append(prevModel)

        self.dataMgrs = validDataMgrs
        self.models = validModels

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def getActiveDataMgrs(self):
        self.getActiveModels()
        dataMgrsForActive = []
        for model in self.models:
            dataMgrsForModel = []
            for mgr in self.dataMgrs:
                if hasattr(mgr, 'colorInteractingResi') and mgr.model is model:
                    dataMgrsForModel.append(mgr)

            if len(dataMgrsForModel) == 0:
                dataMgrsForModel.append(InteractingResiDataMgr(model, self.getActiveData()))
                self.dataMgrs.extend(dataMgrsForModel)

            dataMgrsForActive.extend(dataMgrsForModel)
        return dataMgrsForActive

    def getActiveData(self):
        data = []
        for item in self.config.getDataItems(xlinkanalyzer.INTERACTING_RESI_DATA_TYPE):
            if item.active:
                data.append(item)
        return data

    def reload(self, name, userData, cfg):
        self.config = xlinkanalyzer.get_gui().configFrame.config

        data = self.config.getDataItems(xlinkanalyzer.INTERACTING_RESI_DATA_TYPE)
        if data:
            self.clear()

            curRow = 0
            totalCols = 2

            modelSelect = xlinkanalyzer.get_gui().modelSelect.create(self)
            modelSelect.grid(row = curRow, columnspan=totalCols, sticky="we")
            curRow += 1

            btn = Tkinter.Button(self,
                text='Map interacting',
                # foreground=color,
                command=self.colorInteractingResi)
            btn.grid(row = curRow, columnspan=totalCols)
            curRow += 1

            self.interactingResiCompOptMenuFrom = ComponentsOptionMenu(self, 'from subunit', self.config)
            self.interactingResiCompOptMenuFrom.grid(row = curRow, column = 0)

            self.interactingResiCompOptMenuTo = ComponentsOptionMenu(self, 'to all', self.config)
            self.interactingResiCompOptMenuTo.grid(row = curRow, column = 1)
            curRow += 1

    def colorInteractingResi(self):
        self.getActiveDataMgrs()

        fromComp = None
        fromCompSel = self.interactingResiCompOptMenuFrom.var.get()
        if fromCompSel in self.config.getComponentNames():
            fromComp = fromCompSel

        toComp = None
        toCompSel = self.interactingResiCompOptMenuTo.var.get()
        if toCompSel in self.config.getComponentNames():
            toComp = toCompSel

        for mgr in self.dataMgrs:
            if hasattr(mgr, 'colorInteractingResi'):
                mgr.colorInteractingResi(fromComp,to=toComp,hide_others=False)

def is_mac():
    return _platform == "darwin"
