import chimera

import random


def areSequencesSame(s1, s2, min_overlap=5):
    pairs = {}
    for r in s1.residues:
        if r is not None:  # was None in 4V7R
            pairs[r.id.position] = r.type

    same = 0
    for r in s2.residues:
        if r is not None:  # was None in 4V7R
            if r.id.position in pairs:
                if r.type == pairs[r.id.position]:
                    same = same + 1
                else:
                    return False

    return same >= min_overlap


def getRandomColor():
    table = chimera.colorTable
    name = random.choice(table.colors.keys())
    return table.getColorByName(name)


class CifHeaders(object):
    def __init__(self, mmCIFHeaders):
        self.mmCIFHeaders = mmCIFHeaders

    def getEntityIdForChain(self, chainId):
        for data in self.mmCIFHeaders['pdbx_poly_seq_scheme']:
            if data['pdb_strand_id'] == chainId:
                return data['entity_id']

    def getSeqNameForChain(self, chainId):
        entityId = self.getEntityIdForChain(chainId)

        for data in self.mmCIFHeaders['entity']:
            if data['id'] == entityId:
                return data['pdbx_description']


def getSeqName(s):
    name = s.descriptiveName

    if name is None:
        if s.molecule.mmCIFHeaders is not None:
            cif = CifHeaders(s.molecule.mmCIFHeaders)
            name = cif.getSeqNameForChain(s.chain)

    return name