import chimera
import xlinkanalyzer

def is_satisfied(b, threshold):
    if b:
        return b.length() < threshold

def restyleXlinks(xMgrs, threshold=None):
    '''Restyle xlinks in provided XlinkDataMgr objects.'''
    good_color = chimera.MaterialColor(0,0,255)
    bad_color = chimera.MaterialColor(255,0,0)

    for xMgr in xMgrs:
        for b in xMgr.iterXlinkPseudoBonds():
            if b is not None:
                b.drawMode = chimera.Bond.Stick

                if threshold is not None:
                    if is_satisfied(b, threshold):
                            b.color = good_color
                            b.radius = 0.6
                    else:
                            b.color = bad_color
                            b.radius = 0.6
                else:
                    b.color = bad_color
                    b.radius = 0.6

chimeraModel = chimera.openModels.list()[-1]
gui = xlinkanalyzer.get_gui()
x = gui.Xlinks.getXlinkDataMgrs()
xMgrs = gui.Xlinks.getXlinkDataMgrs()

restyleXlinks(xMgrs, threshold=30)