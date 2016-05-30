import chimera
from chimera import preferences

# from data import *

from sys import __stdout__

XLINK_ANALYZER_DATA_TYPE = 'Xlink Analyzer'
XQUEST_DATA_TYPE = 'xquest'
EM_DATA_TYPE = 'em_map'
SEQUENCES_DATA_TYPE = 'sequences'
INTERACTING_RESI_DATA_TYPE = 'interacting_resi'
CONSURF_DATA_TYPE = 'Consurf'
XLINK_LEN_THRESHOLD = 30

DEBUG_MODE = False

__version__ = '1.2'

def get_gui():
    for insta in chimera.extension.manager.instances:
        if hasattr(insta, 'name') and insta.name == 'Xlink Analyzer':
            return insta


def getConfig():
    for insta in chimera.extension.manager.instances:
        if hasattr(insta, 'name') and insta.name == 'Xlink Analyzer':
            return insta.configFrame.config

prefs = preferences.addCategory("xlinkanalyzer", preferences.HiddenCategory)

def pushRecentToPrefs(path):
    otherPaths = [p for p in getRecentPaths() if p != path]
    prefs["path1"]=path
    for i, p in zip(range(2,11), otherPaths):
        prefs["path{0}".format(i)] = p

def getRecentPaths():
    ret = []
    for s in ["path"+str(i) for i in range(1,11)]:
        if s in prefs:
            ret.append(prefs[s])
    return ret

def activateByName(name, chainIds=None):  # this is for testing only
    if name is not None:
        comp = getConfig().getSubunitByName(name)
        if not comp:
            comp = getConfig().getDomainByName(name)
            if not comp:
                comp = getConfig().getSubcomplexByName(name)

        if comp:
            if not chainIds:
                if hasattr(comp, 'chainIds'):
                    chainIds = comp.chainIds
                elif hasattr(comp, 'subunit'):
                    chainIds = comp.subunit.chainIds
                else:
                    #must be subcomplex:
                    chainIds = []
                    for item in comp.items:
                        if hasattr(item, 'chainIds'):
                            chainIds.extend(item.chainIds)
                        elif hasattr(item, 'subunit'):
                            chainIds.extend(item.subunit.chainIds)
            for chainId in chainIds:
                get_gui().Subunits.table.activeComponents.append((comp, chainId))
    else:
        get_gui().Subunits.table.activeComponents = []
