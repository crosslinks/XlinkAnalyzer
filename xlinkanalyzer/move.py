from MoveSelection import Selection_Mover
from MoveSelection import move as chimera_move
from chimera.specifier import evalSpec

import xlinkanalyzer as xla


COMPONENT_MOVEMENT = 'move component'


class ComponentMover(Selection_Mover):
    COMPONENT_MOVEMENT = COMPONENT_MOVEMENT

    def __init__(self):
        Selection_Mover.__init__(self)

    def record_movable_objects(self, event):
        if self.mode == self.COMPONENT_MOVEMENT:

            atoms = []
            for selection in xla.get_gui().Components.getMovableAtomSpecs():
                atoms.extend(evalSpec(selection).atoms())

            chains = []
            spieces = []
            self.movable_groups = chimera_move.objects_grouped_by_model(atoms, chains, spieces)
        else:
            Selection_Mover.record_movable_objects(self, event)
