import xlinkanalyzer as xla
reload(xla)

gui = xla.get_gui()

xframe = gui.Xlinks


xframe.dataMgrs


config = gui.configFrame.config

rm = xla.RMF_Model(m, config)

def get_first_xlinkMgr():
    gui = xla.get_gui()
    xframe = gui.Xlinks
    return xframe.dataMgrs[0]


x = get_first_xlinkMgr()
x.countSatisfiedBetweenSelections(30, '#0:.C', '#0:.C')




#OLD:

gui.addPDBModel(chimera.openModels.list()[1])

gui.addRMFModel(chimera.openModels.list())


m = gui.models[-1]

#access the one already created
x = gui.dataMgrs[-1]

#create new one:
x = xla.XlinkDataMgr(m, gui.data.items[:3])
#for Pol1 test
x = xla.XlinkDataMgr(m, gui.data.items)



x.show_monolinks_map()

xla.restyleXlinks([x], 40)
x.show_xlinks_smart(40)
x.hide_by_ld_score(30)

x.hideAllXlinks()
x.showAllXlinks()

x.color_xlinked()
x.color_xlinked(to='AC19')
x.color_xlinked('AC19', minLdScore=30)

x.show_xlinks_from('AC40', 'C160')

x.mapXlinkResi('C160', 'C25')



r = gui.models[0]._get_rmf_viewer()
p = r.rmf.dialog.playback

chimera.triggers.triggerNames()

chimera.triggers.addHandler('PseudoBond', dupa, None)



i = gui.dataMgrs[1]
dataItem = i.data[0]
print dataItem.config

m.colorByDomains('C82')


import xla
gui = xla.get_gui()
x = gui.dataMgrs[-1]
x.hide_by_ld_score(30)
x.count_satisfied(30)
x.predict_monolinkable()
