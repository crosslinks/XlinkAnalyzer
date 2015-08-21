import chimera
from chimera import match, numpyArrayFromAtoms
from chimera.match import matchPositions
from chimera.specifier import evalSpec
from chimera import Xform

import xlinkanalyzer as xla

from sys import __stdout__


class SymMover(object):
    def __init__(self):
        self.m = chimera.openModels.list()[0]
# Matchmaker yRvb12.hexamer.pdb, chain C (#1) with yRvb12.hexamer.pdb, chain A (#0), sequence alignment score = 1986.2

# with these parameters:
#     chain pairing: bb
#     Needleman-Wunsch using BLOSUM-62

#     ss fraction: 0.3
#     gap open (HH/SS/other) 18/18/6, extend 1
#     ss matrix: 
#  (H, O): -6
#  (S, S): 6
#  (H, H): 6
#  (O, S): -6
#  (O, O): 4
#  (H, S): -9


#     iteration cutoff: 2

# RMSD between 393 atom pairs is 0.001 angstroms



# Position of yRvb12.hexamer.pdb (#0) relative to yRvb12.hexamer.pdb (#1) coordinates:
#   Matrix rotation and translation
#     -0.50000042   0.86602516   0.00000116 -103.53997515
#     -0.86602516  -0.50000042   0.00000058 179.33655802
#      0.00000108  -0.00000072   1.00000000   0.00005125
#   Axis  -0.00000075   0.00000005  -1.00000000
#   Axis point  -0.00001174 119.55767842   0.00000000
#   Rotation angle (degrees) 120.00002798
#   Shift along axis   0.00003425


        self.series = [
            {
                'tr3d': Xform.xform(-0.50000042, 0.86602516, 0.00000116, -103.53997515,
                -0.86602516, -0.50000042, 0.00000058, 179.33655802,
                0.00000108, -0.00000072, 1.00000000, 0.00005125, orthogonalize=True),
                'chainIds': ['A', 'C', 'E'],
                'old': [],
                'new': []
            }
        ]



        # for a in evalSpec(':.A').atoms():
        #     a.setCoord(self.symTr3d.apply(a.coord()))

        for serie in self.series:
            serie['t3ds'] = [[None for i in range(len(serie['chainIds']))] for j in range(len(serie['chainIds']))]
            for i in range(len(serie['chainIds'])):
                # self.t3ds.append([])
                for j in range(len(serie['chainIds'])):
                    count = abs(j-i)

                    symTr3d = Xform.identity()
                    for c in range(count):
                        symTr3d.multiply(serie['tr3d'])

                    newT = Xform.identity()
                    if i < j:
                        newT = symTr3d
                    elif i > j:
                        newT = symTr3d.inverse()

                    serie['t3ds'][i][j] = newT

            for chainId in serie['chainIds']:
                atoms = evalSpec(':.{0}'.format(chainId)).atoms()
                serie['old'].append(numpyArrayFromAtoms(atoms))

            # for a in evalSpec(':.C').atoms():
            #     a.setCoord(serie['t3ds'][1][0].apply(a.coord()))

    def activate(self):
        handler = chimera.triggers.addHandler('CoordSet', self.update, None)
        self._handlers = []
        self._handlers.append((chimera.triggers, 'CoordSet', handler))

    def _deleteHandlers(self):
        if not self._handlers:
            return
        while self._handlers:
            triggers, trigName, handler = self._handlers.pop()
            triggers.deleteHandler(trigName, handler)

    # def was_changed(self):
    #     self.new = [numpyArrayFromAtoms(a) for a in self.sym_chains]
    #     return not (self.new == self.old).all()

    def update(self, trigName, myData, changes):
        # print >> __stdout__, "update", trigName, myData, dir(changes), changes.modified
        # coordSet = list(changes.modified)[0]
        # print >> __stdout__, len(coordSet.coords())
        # print >> __stdout__, dir(coordSet)
        # print >> __stdout__, "update"

        # atoms = []
        # for selection in xla.get_gui().Subunits.getMovableAtomSpecs():
        #     atoms.extend(evalSpec(selection).atoms())

        for serie in self.series:

            serie['new'] = []
            for chainId in serie['chainIds']:
                atoms = evalSpec(':.{0}'.format(chainId)).atoms()
                serie['new'].append(numpyArrayFromAtoms(atoms))
            # if self.was_changed():
            i = 0
            changed_c = None
            for old_c, new_c in zip(serie['old'], serie['new']):
                if not (old_c == new_c).all():
                    changed_c = i
                i = i + 1

            if changed_c is not None:
                other = set(range(len(serie['chainIds'])))
                other.remove(changed_c)

                t3d, rmsd = matchPositions(serie['new'][changed_c], serie['old'][changed_c])
                for o in other:
                    newT = Xform.identity()
                    newT.premultiply(serie['t3ds'][o][changed_c])

                    newT.premultiply(t3d)

                    newT.premultiply(serie['t3ds'][changed_c][o])

                    atoms = evalSpec(':.{0}'.format(serie['chainIds'][o])).atoms()
                    for a in atoms:
                        a.setCoord(newT.apply(a.coord()))

                serie['old'] = []
                for chainId in serie['chainIds']:
                    atoms = evalSpec(':.{0}'.format(chainId)).atoms()
                    serie['old'].append(numpyArrayFromAtoms(atoms))

