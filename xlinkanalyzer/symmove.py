import chimera
from chimera import match, numpyArrayFromAtoms
from chimera.match import matchPositions
from chimera.specifier import evalSpec
from chimera import Xform

import xlinkanalyzer as xla

from sys import __stdout__


class SymMover(object):
    def __init__(self):
        self.sym_chains = []

    def activate(self):


        self.m = chimera.openModels.list()[0]
        # self.old = numpyArrayFromAtoms(self.m.atoms)

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


        tr3d = [-0.50000042, 0.86602516, 0.00000116, -103.53997515,
                -0.86602516, -0.50000042, 0.00000058, 179.33655802,
                0.00000108, -0.00000072, 1.00000000, 0.00005125]



        # trans = [, , 0.00005125]
        # tr3d = rot+trans
        self.symTr3d = Xform.xform(*tr3d, orthogonalize=True)

        self.sym_chains = [
            evalSpec(':.A').atoms(),
            evalSpec(':.C').atoms(),
            evalSpec(':.E').atoms()
        ]

        # for a in evalSpec(':.A').atoms():
        #     a.setCoord(self.symTr3d.apply(a.coord()))

        self.old = [numpyArrayFromAtoms(a) for a in self.sym_chains]

# 

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
        print >> __stdout__, "update"
        atoms = []
        for selection in xla.get_gui().Components.getMovableAtomSpecs():
            atoms.extend(evalSpec(selection).atoms())

        self.sym_chains = [
            evalSpec(':.A').atoms(),
            evalSpec(':.C').atoms(),
            evalSpec(':.E').atoms()
        ]
        self.new = [numpyArrayFromAtoms(a) for a in self.sym_chains]
        # if self.was_changed():
        i = 0
        changed_c = None
        for old_c, new_c in zip(self.old, self.new):
            if not (old_c == new_c).all():
                changed_c = i
            i = i + 1

        if changed_c == 0:
            # other = set(range(len(self.sym_chains)))
            # other.remove(changed_c)
#GOOD:
            # t3d, rmsd = matchPositions(self.old[changed_c], self.new[changed_c])
            # print >> __stdout__, t3d

            # newT = self.symTr3d.inverse()
            # newT.premultiply(t3d.inverse())
            # newT.premultiply(self.symTr3d)
#----

            t3d, rmsd = matchPositions(self.new[changed_c], self.old[changed_c])
            print >> __stdout__, t3d

            newT = self.symTr3d.inverse()
            newT.premultiply(t3d)
            newT.premultiply(self.symTr3d)

            # newT = Xform.identity()
            # newT.multiply(self.symTr3d)
            # newT.multiply(t3d)
            # newT.multiply(self.symTr3d.inverse())
            # t3d1 = self.symTr3d.multiply(t3d)

            # for a in self.sym_chains[1]:
            #     a.setCoord(newT.apply(a.coord()))

            for a in self.sym_chains[1]:
                a.setCoord(newT.apply(a.coord()))
                # a.setCoord(self.symTr3d.inverse().apply(a.coord()))
                # a.setCoord(t3d.apply(a.coord()))
                # a.setCoord(self.symTr3d.apply(a.coord()))
            # for o in other:
            #     t3d, rmsd = matchPositions(self.old[o], self.new[o])
            #     print >> __stdout__, t3d

            # print >> __stdout__, other

            self.sym_chains = [
                evalSpec(':.A').atoms(),
                evalSpec(':.C').atoms(),
                evalSpec(':.E').atoms()
            ]
            
            self.old = [numpyArrayFromAtoms(a) for a in self.sym_chains]
        # print >> __stdout__, changed
        # xf, rmsd = match.matchAtoms(atoms, atoms, fCoordSet=self.oldCoordSet,
        #         mCoordSet=coordSet)

        # print >> __stdout__, xf, dir(xf)