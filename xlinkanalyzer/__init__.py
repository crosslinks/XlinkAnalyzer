import chimera

from sys import platform as _platform


'''
PDB/RMF input spec


o every protein defined as a protein in xlink data must be a single chain,
  so if there are two PDB structures of two domains of the same protein,
  their chain must be the same
'''

XLINK_ANALYZER_DATA_TYPE = 'XlinkAnalyzer'
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

def get_assembly():
    gui = get_gui()
    if gui:
        return gui.assemblyFrame.assembly




def get_group(groupName):
    mgr = chimera.PseudoBondMgr.mgr()
    group = mgr.findPseudoBondGroup(groupName)
    return group

def hideGroup(groupName):
    group = get_group(groupName)
    if group:
        group.display = 0



