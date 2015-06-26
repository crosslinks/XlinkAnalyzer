import math
import string
import csv
from sys import platform as _platform
from functools import partial
import itertools
from sys import __stdout__

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
                    OptionMenu,Label,Frame, TclError, Checkbutton, IntVar
import ttk
import pyxlinks


from data import Component,DataItem,SimpleDataItem,XQuestItem, SequenceItem,\
                 Assembly, ResourceManager, Item, InteractingResidueItem,\
                 Domain, Subcomplex

import manager as xmanager
from manager import Model, RMF_Model, XlinkDataMgr, InteractingResiDataMgr
from xlinkanalyzer import getConfig
from xlinkanalyzer import move as xmove
###########
# TEMPORARY
###########

from item import ItemList

DEBUG_MODE = False
DEV = True

class XlinkAnalyzer_Dialog(ModelessDialog):

    title = 'Xlink Analyzer'
    name = 'Xlink Analyzer'
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

        self._handlers = []

        ModelessDialog.__init__(self, **kw)

        self.configCfgs = []

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

        self.addTab('Components', ComponentsTabFrame)
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

    def getAssemblyConfig(self, name):
        for cfg in self.configCfgs:
            if cfg.name == name:
                return cfg

    def addComponentToCfgCB(self):
        cfgName = self.loadDataTab_configCfgsOptionMenu.var.get()
        name = self.currAddComponentFrame.componentNameEntryField.get()
        color = self.currAddComponentFrame.coloropt.get()
        chains = self.currAddComponentFrame.chainEntryField.get()
        chains = [x.strip() for x in chains.split(',')]

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

        for dom in self.xlaConfig.getDomains():
            domOpt = "{0}, {1}".format(dom.subunit.name, dom.name)
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
        config = getConfig()
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
        for child in self.winfo_children():
            if isinstance(child, XlinkToolbar):
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

        n, bins, patches = ax.hist(self.lengths, bins=bins, rwidth=.5)
        for c, p in zip(colors, patches):
            p.set_color(c)
        ticks = map(int, bins)
        ax.set_xticks(ticks)
        ax.set_ylabel("Number of cross-links")
        ax.set_xlabel(r"Euclidan C$\alpha$ pair distance [$\AA$]")
        ax.yaxis.grid(True)
        self.draw()


class CustomModelItems(ModelItems):
    '''
    Shows rmf models only as single model
    '''

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
            label_text="Choose models to act on:"
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
    autoselectDefault = None
    """Modified to remove itself from ModelSelect.children list"""
    autoSelectDefault=True
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

        self._handlers = []
        self._addHandlers()

        #ROW 0:
        curRow = 0
        self.subUnitFrame = ItemList(self,self.config,"subunits",True)
        self.subUnitFrame.grid(row=curRow,column=0,columnspan=3)
        self.dataFrame = ItemList(self,self.config,"dataItems",True)
        self.dataFrame.grid(row=curRow,column=4)

        self.grid_rowconfigure(curRow, weight=1)

        curRow = curRow + 1
        self.domainsButton = Button(self,text="Domains", command=self.onDomain)
        self.domainsButton.grid(row = curRow,column = 0, sticky = "W",**layout)

        self.subCompButton = Button(self,text="Subcomplexes", \
                                         command=self.onSubcomplexes)
        self.subCompButton.grid(row = curRow,column = 1, sticky = "W",**layout)

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

    def onSubcomplexes(self):
        subunitNames = self.config.getComponentNames()
        domains = self.config.getDomains()
        if not (subunitNames or domains):
            title = "No Subunits or Domains yet"
            message = "Please add some subunits or domains before configuring."
            tkMessageBox.showinfo(title,message,parent=self.master)
            return
        ItemList(Toplevel(),self.config,"subcomplexes",True)

    def onDomain(self):
        subunitNames = self.config.getComponentNames()
        if not subunitNames:
            title = "No components yet"
            message = "Please add some components before configuring."
            tkMessageBox.showinfo(title,message,parent=self.master)
            return
        ItemList(Toplevel(),self.config,"domains",True)

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
        self.subUnitFrame.synchronize(self.config)
        self.dataFrame.synchronize(self.config)
        chimera.triggers.activateTrigger('configUpdated', None)

    def reload(self, name, userData, o):
        self.mainWindow.setTitle(self.config.file+"*")
        self.config.state = "changed"

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

    def reload(self, name, userData, o):
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
    def __init__(self, master,*args, **kwargs):
        TabFrame.__init__(self, master, *args, **kwargs)
        config = getConfig()
        self.table = ComponentTable(self,config)
        self.table.grid(sticky="nesw",row=1,column=0)
        self.grid(sticky="nesw")

    def clear(self):
        pass

    def reload(self, name, userData, o):
        self.table.reload()

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
        dataTypes = [xlinkanalyzer.XQUEST_DATA_TYPE, xlinkanalyzer.XLINK_ANALYZER_DATA_TYPE]
        data = []
        for item in self.config.getDataItems():
            if item.active and item.type in dataTypes and item.hasMapping():
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

    def reload(self, name, userData, o):
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

    def reload(self, name, userData, o):
        self.config = getConfig()

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

from CGLtk.Table import SortableTable

class ComponentTable(Frame):
    def __init__(self,parent,config,*args,**kwargs):
        Frame.__init__(self,parent,*args,**kwargs)

        c = Component(config)
        c.name = "Kai"

        self.config = config

        self.activeComponents = []
        self.mover = xmove.ComponentMover()
        self.mover.ctable = self
        self.mover.mode = xmove.COMPONENT_MOVEMENT

        curRow = 0
        self.modelSelect = xlinkanalyzer.get_gui().modelSelect.create(self)
        self.modelSelect.grid(sticky="wens",column=0,columnspan=3,row=curRow)


        curRow = curRow + 1
        self.chainVar = IntVar(self)
        self.chainVar.trace("w",lambda x,y,z: self.onShowChains())
        self.showChains = Checkbutton(self, text="Show Chains", \
                                            variable=self.chainVar)
        self.showChains.grid(row=curRow,column=1)

        self.chooseVar = StringVar(self)
        self.chooseVar.set("Subunits")
        self.chooseVar.trace("w",lambda x,y,z: self.reload())
        self.choices = dict([("Subunits",self.config.getComponents),\
                             ("Domains",self.config.getDomains),\
                             ("Subcomplexes", lambda x: x)])
        self.choose = OptionMenu(self,self.chooseVar,*self.choices.keys())
        self.choose.grid(column=0,row=curRow)


        curRow = curRow + 1
        self.activate = Button(self,text="Activate", command=self.onActivate)
        self.activate.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.activateAll = Button(self,text="Activate All", \
                                       command=self.onActivateAll)
        self.activateAll.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.activeOnly  = Button(self,text="Activate Only", \
                                       command=self.onActivateOnly)
        self.activeOnly.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.deactivate = Button(self,text="Deactivate", \
                                       command=self.onDeactivate)
        self.deactivate .grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.show = Button(self,text="Show", \
                                       command=self.onShow)
        self.show.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.hide  = Button(self,text="Hide", \
                                       command=self.onHide)
        self.hide.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.select = Button(self,text="Select", \
                                       command=self.onSelect)
        self.select.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.showOnly = Button(self,text="Show Only", \
                                       command=self.onShowOnly)
        self.showOnly.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.colorAll = Button(self,text="Color all", \
                                       command=self.onColorAll)
        self.colorAll.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.undo = Button(self,text="Undo Move", \
                                       command=self.onUndo)
        self.undo.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1
        self.redo = Button(self,text="Redo Move", \
                                       command=self.onRedo)
        self.redo.grid(row=curRow,column=3,sticky="W")

        curRow = curRow + 1

        self.table = SortableTable(self)
        self.table.addColumn("Active", "active")
        self.table.addColumn("Show", "show")
        self.table.addColumn("Symmetrical", "sym")
        self.table.addColumn("Name","name")
        self.table.setData([])
        self.table.launch()
        self.table.grid(sticky="wens",column=0,columnspan=2,row=2,rowspan=curRow)

    def reload(self):
        items = self.choices[self.chooseVar.get()]()
        if items:
            self.table.setData(items)

    def getActiveModels(self):
        self.models = xlinkanalyzer.get_gui().modelSelect.getActiveModels()

    def onActivate(self):
        for item in self.table.selected():
            item.active = True
        self.table.refresh()

    def onActivateAll(self):
        for item in self.choices[self.chooseVar.get()]():
            item.active = True
        self.table.refresh()

    def onActivateOnly(self):
        for item in self.choices[self.chooseVar.get()]():
            item.active = False
        for item in self.table.selected():
            item.active = True
        self.table.refresh()

    def onDeactivate(self):
        for item in self.table.selected():
            item.active = False
        self.table.refresh()

    def onShow(self):
        for item in self.table.selected():
            item.show = True
        self.table.refresh()

    def onHide(self):
        for item in self.table.selected():
            item.show = False
        self.table.refresh()

    def onSelect(self):
        pass

    def onShowOnly(self):
        for item in self.choices[self.chooseVar.get()]():
            item.show = False
        for item in self.table.selected():
            item.show = True
        self.table.refresh()

    def onColorAll(self):
        self.getActiveModels()
        for model in self.models:
            if model.active:
                model.colorAll()

    def onUndo(self):
        self.mover.undo_move()

    def onRedo(self):
        self.mover.redo_move()

    def onShowChains(self):
        print self.chainVar.get()

    def getComponentChoices(self, chooseVar):
        return self.choices[self.chooseVar.get()]()

    def getActiveComponents(self):
        curr = self.getComponentChoices(self.chooseVar.get())
        return [item for item in curr if item.active]

    def getCurrentSelections(self):
        sels = []
        if len(self.getActiveComponents()) != len(self.getComponentChoices(self.chooseVar.get())):
            for comp in self.getActiveComponents():
                sels.append(comp.getSelection())

        return sels

    def getMovableAtomSpecs(self):
        activeModelIds = []
        self.getActiveModels()
        for model in self.models:
            if model.active:
                activeModelIds.append(model.getModelId())

        currentSelections = self.getCurrentSelections()
        atomSpecs = []
        for modelId, sel in itertools.product(activeModelIds, currentSelections):
            atomSpecs.append('#{0}{1}'.format(modelId, sel))

        return atomSpecs


def is_mac():
    return _platform == "darwin"
