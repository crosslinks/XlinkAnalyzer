import chimera

import random

def areSequencesSame(s1, s2, min_overlap=5):
    pairs = {}
    for r in s1.residues:
        pairs[r.id.position] = r.type

    same = 0
    for r in s2.residues:
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
