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





def is_crosslinkable(resi, biodssp=None, acc_thresh=None):
    if biodssp and acc_thresh:
        raise NotImplementedError
        rel_aa = 0
        return resi.type == 'LYS' and rel_aa > acc_thresh
    else:
        return resi.type == 'LYS'

def get_atoms_for_obj(obj):
    return [atom for atom in obj.atoms]

def get_chain_for_atom(at):
    return str(at.residue.id).split('.')[1]

def get_chain_for_residue(resi):
    return str(resi.id).split('.')[1]

def get_chain_for_chimera_obj(obj):
    if hasattr(obj, 'atoms'):
        chain = get_chain_for_residue(obj)
    else:
        chain = get_chain_for_atom(obj)

    return chain

def get_gui():
    for insta in chimera.extension.manager.instances:
        if hasattr(insta, 'name') and insta.name == 'Xlink Analyzer':
            return insta

def get_assembly():
    gui = get_gui()
    if gui:
        return gui.assemblyFrame.assembly

def is_satisfied(b, threshold):
    return b.length() < threshold


def get_group(groupName):
    mgr = chimera.PseudoBondMgr.mgr()
    group = mgr.findPseudoBondGroup(groupName)
    return group

def hideGroup(groupName):
    group = get_group(groupName)
    if group:
        group.display = 0


def is_normal_pdb_resi(resi):
    '''Distinguish from rmf resi'''
    return hasattr(resi, 'hasRibbon')

def get_rmf_viewers():
    return [insta for insta in chimera.extension.manager.instances if hasattr(insta, 'rmf')]

def is_rmf_mol(mol):
    if hasattr(mol, 'openedAs'):
        if mol.openedAs[0].endswith('.rmf'):
            return True
    return False
