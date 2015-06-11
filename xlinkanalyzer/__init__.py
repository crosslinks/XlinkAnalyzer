import chimera
# from data import *

XLINK_ANALYZER_DATA_TYPE = 'Xlink Analyzer'
XQUEST_DATA_TYPE = 'xquest'
EM_DATA_TYPE = 'em_map'
SEQUENCES_DATA_TYPE = 'sequences'
INTERACTING_RESI_DATA_TYPE = 'interacting_resi'
XLINK_LEN_THRESHOLD = 30

DEBUG_MODE = False


def get_gui():
    for insta in chimera.extension.manager.instances:
        if hasattr(insta, 'name') and insta.name == 'Xlink Analyzer':
            return insta

def getConfig():
    for insta in chimera.extension.manager.instances:
        if hasattr(insta, 'name') and insta.name == 'Xlink Analyzer':
            return insta.configFrame.config

def activateByName(name):  # this is for testing only
    if name is not None:
        comp = getConfig().getComponentByName(name)
        if not comp:
            comp = getConfig().getDomainByName(name)

        if comp:
            get_gui().Components.activeComponents = [comp]
    else:
        get_gui().Components.activeComponents = []