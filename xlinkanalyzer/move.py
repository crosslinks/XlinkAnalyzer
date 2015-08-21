from MoveSelection import Selection_Mover
from MoveSelection import move as chimera_move
from chimera.specifier import evalSpec

import xlinkanalyzer as xla


COMPONENT_MOVEMENT = 'move component'  # YES, keep "component"!


class ComponentMover(Selection_Mover):
    COMPONENT_MOVEMENT = COMPONENT_MOVEMENT  # YES, keep "component"!

    def __init__(self):
        Selection_Mover.__init__(self)
        self.ctable = None

    def record_movable_objects(self, event):
        if self.mode == self.COMPONENT_MOVEMENT and self.ctable:  # YES, keep "component"!

            atoms = []
            for selection in self.ctable.getMovableAtomSpecs():
                atoms.extend(evalSpec(selection).atoms())

            chains = []
            spieces = []
            self.movable_groups = chimera_move.objects_grouped_by_model(atoms, chains, spieces)
        else:
            Selection_Mover.record_movable_objects(self, event)
