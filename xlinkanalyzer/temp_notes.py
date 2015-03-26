import xlinkanalyzer as xla
reload(xla)

gui = xla.get_gui()

xframe = gui.Xlinks

def get_first_xlinkMgr():
    gui = xla.get_gui()
    xframe = gui.Xlinks
    return xframe.dataMgrs[0]

xframe.getActiveData()

x = get_first_xlinkMgr()
x.countSatisfiedBetweenSelections(30, '#0:.C', '#0:.C')
x.pbg.pseudoBonds