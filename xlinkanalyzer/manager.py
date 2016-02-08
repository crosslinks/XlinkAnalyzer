import xlinkanalyzer
import chimera
import re
import weakref
import pyxlinks
import tkFileDialog
import csv
import copy
from itertools import product, groupby, tee, izip, izip_longest, combinations_with_replacement, ifilter
from collections import defaultdict
from sys import __stdout__

from chimera import runCommand, Bond, selection
from chimera.misc import getPseudoBondGroup

#TODO: check these
from xlinkanalyzer import get_gui, getConfig
from xlinkanalyzer import XLINK_LEN_THRESHOLD

class Model(object):
    active = True
    def __init__(self, chimeraModel, config):
        self.chimeraModel = chimeraModel
        self.resi_lookup_map = self.get_resi_lookup_map()
        self.config = config

    def getModelId(self):
        return self.chimeraModel.id

    def getChimeraModel(self):
        return self.chimeraModel

    def getModelName(self):
        return self.chimeraModel.name

    def get_resi_lookup_map(self):
        '''Create a dict that can be queried like self.resi_lookup_map[chain][resi_d]'''

        resi_lookup_map = {}

        for resi in self.iterateResidues():
            res_id = resi.id.position
            chain_id = resi.id.chainId
            if not chain_id in resi_lookup_map:
                resi_lookup_map[chain_id] = {res_id: [resi]}
            else:
                if res_id in resi_lookup_map[chain_id]:
                    resi_lookup_map[chain_id][res_id].append(resi)
                else:
                    resi_lookup_map[chain_id][res_id] = [resi]

        return resi_lookup_map

    def iterateResidues(self):
        for resi in self.chimeraModel.residues:
            yield resi

    def color(self, comp, color=None):
        '''Color specified component of the model by color from config or specified color.'''
        if color is None:
            color = comp.color

        if isinstance(color, dict):
            colors_by_chain = color
            for chain in colors_by_chain:
                color = colors_by_chain[chain]
                runCommand('color ' + color + ' #' + str(self.getModelId()) + ':.' + chain)
        else:
            if hasattr(color, 'rgba'):
                color = color.rgba()
            if isinstance(color, tuple) or isinstance(color, list):
                color = ','.join(map(str,color))
            runCommand('color ' + color + ' #' + str(self.getModelId()) + comp.getSelection())

    def colorByDomains(self, name):
        self.color(name, color='gray')
        try:
            cfg = self.config.getDomains(name)
        except KeyError:
            print 'No domains for ', name
        else:
            chains = self.config.getChainIdsBySubunitName(name)
            for chain in chains:
                for dom in cfg:
                    color = dom.color
                    for resiID in dom.getRangesAsResiList():
                        try:
                            resi_list = self.resi_lookup_map[chain][resiID]
                        except:
                            pass
                        else:
                            for resi in resi_list:
                                resi.color = color
                                resi.ribbonColor = color

                                for atom in resi.atoms:
                                    atom.color = color


    def colorAll(self):
        '''Color all subunit of the model by colors from the config'''
        for comp in self.config.getSubunits():
            self.color(comp)

    def showOnly(self, comp):
        '''Show only a given component of the model'''

        for otherComp in self.config.getSubunits():
            if otherComp != comp:
                runCommand('~display ' + ' #' + str(self.getModelId()) + otherComp.getSelection())
                runCommand('~ribbon '+ ' #' + str(self.getModelId()) + otherComp.getSelection())
        self.show(comp)

    def show(self, comp):
        '''Show a component of the model'''
        runCommand('ribbon ' + ' #' + str(self.getModelId()) + comp.getSelection())
        # show_missing_loops_for_name(name)

    def hide(self, comp):
        '''Hide a component of the model'''
        runCommand('~display ' + ' #' + str(self.getModelId()) + comp.getSelection())
        runCommand('~ribbon ' + ' #' + str(self.getModelId()) + comp.getSelection())

    def showAll(self):
        '''Show all subunits.'''
        for comp in self.config.getSubunits():
            self.show(comp)

    def get_monolinks_possible_in_structure(self, possible_fn=None):
        out = []
        for resi in self.iterateResidues():
            if is_crosslinkable(resi):
                res_id = resi.id.position
                chain_id = resi.id.chainId
                out.append((chain_id, res_id))

        return out

def restyleXlinks(xMgrs, threshold=None):
    '''Restyle xlinks in provided XlinkDataMgr objects.'''
    good_color = chimera.MaterialColor(0,0,255)
    bad_color = chimera.MaterialColor(255,0,0)

    for xMgr in xMgrs:
        for b in xMgr.iterXlinkPseudoBonds():
            if b is not None:
                b.drawMode = chimera.Bond.Stick

                if threshold is not None:
                    if is_satisfied(b, threshold):
                            b.color = good_color
                            b.radius = 0.6
                    else:
                            b.color = bad_color
                            b.radius = 0.6
                else:
                    b.color = bad_color
                    b.radius = 0.6




class RMFFakeResi(object):
    '''Wrapper resi for bead resi exposing real resi pos for low res beads
    '''
    def __init__(self, resi, chain_id, resi_id):
        self.resi = resi
        self.id = chimera.MolResId(chain_id, resi_id)
        self.type = resi.type
        self.atoms = resi.atoms


class RMF_Model(Model):
    def __init__(self, moleculeModel, beadModel, config):
        self.moleculeModel = moleculeModel
        self.beadModel = beadModel
        self.rmf_viewer = self._get_rmf_viewer()
        chimeraModel = self.moleculeModel or self.beadModel
        super(RMF_Model, self).__init__(chimeraModel, config)

        self.removeSelHandler()
        self.set_beads(radius=None, opacity=1.0, radius_scale=0.5)
        if moleculeModel is not None and beadModel is not None:
            self.show_missing_loops()
        hideGroup('missing segments')

        handler = chimera.triggers.addHandler('CoordSet', self.afterAllUpdateHandler, None)
        self._handlers = []
        self._handlers.append((chimera.triggers, 'CoordSet', handler))

    def afterAllUpdateHandler(self, trigName, myData, frame):
        self.set_beads(radius=None, opacity=1.0, radius_scale=0.5)

    def _deleteHandlers(self):
        if not self._handlers:
            return
        while self._handlers:
            triggers, trigName, handler = self._handlers.pop()
            triggers.deleteHandler(trigName, handler)

    def showOnly(self, comp):
        '''Show only a given component of the model'''

        for cName in self.config.getSubunitNames():
            if cName != comp:
                runCommand('~display ' + ' #' + str(self.getModelId()) + comp.getSelection())
                if self.moleculeModel:
                    runCommand('~ribbon '+ ' #' + str(self.moleculeModel.id) + comp.getSelection())
        self.show(comp)

    def show(self, comp):
        '''Show a component of the model'''
        if self.moleculeModel:
            runCommand('ribbon ' + ' #' + str(self.moleculeModel.id) + comp.getSelection())
        # show_missing_loops_for_name(name)
        for bead in self.iterate_beads():
            if bead.residue.id.chainId in comp.getSelection():
                bead.display = True

    def hide(self, comp):
        '''Hide a component of the model'''
        runCommand('~display ' + ' #' + str(self.getModelId()) + comp.getSelection())
        if self.moleculeModel:
            runCommand('~ribbon '+ ' #' + str(self.moleculeModel.id) + comp.getSelection())

    def getModelId(self):
        if self.moleculeModel:
            return self.moleculeModel.id
        else:
            return self.beadModel.id

    def getModelName(self):
        if self.moleculeModel:
            return self.moleculeModel.name
        else:
            return self.beadModel.name


    def removeSelHandler(self):
        try:
            chimera.triggers.deleteHandler("selection changed", self.rmf_viewer._selHandler)
        except ValueError:
            pass

    def iterateResidues(self):
        if self.moleculeModel is not None:
            for resi in self.moleculeModel.residues:
                yield resi

        for bead in self.iterate_beads():
            start, end = self.get_bead_residue_indexes(bead)
            if start is not None and end is not None:
                for i in range(start, end):
                    yield RMFFakeResi(bead.residue, bead.residue.id.chainId, i)

    def iterate_CAs(self):
        if self.moleculeModel is not None:
            for resi in self.moleculeModel.residues:
                for atom in resi.atoms:
                    if atom.name == 'CA':
                        yield atom

    def _get_rmf_viewer(self):
        # for insta in chimera.extension.manager.instances:
        #         if hasattr(insta, 'rmf'): return insta

        viewers = get_rmf_viewers()
        for viewer in viewers:
            if (self.moleculeModel and self.moleculeModel in viewer.rmf.getModels()) or \
                (self.beadModel and self.beadModel in viewer.rmf.getModels()):
                return viewer
        #rmf_viewer.featureMap - mapping of feature rows in gui to features
        #rmf_viewer._featureNodeMap - maps chimera objects to lists of associated feature gui rows

    def iterate_bead_components(self):
        for c in self.rmf_viewer.hierarchyMap.itervalues():
            if not c.isReprLeaf():
                continue
            if c.hasBoundingSphere():
                yield c

    def iterate_beads(self):
        for c in self.iterate_bead_components():
            sel = set()
            c.addChimeraObjects(sel)
            for o in sel:
                yield o

    def set_beads(self, radius=None, opacity=1.0, radius_scale=1):
        for bead in self.iterate_beads():
            if bead.color:
                bead.color.opacity = opacity
            if radius is not None:
                bead.radius = radius
            else:
                bead.radius = bead.radius * radius_scale

    def get_bead_indexes(self, bead):
        if hasattr(bead, 'name'):
            name = bead.name

        elif hasattr(bead, 'get_name'):
            name = bead.get_name()
        m = re.search('\[([0-9]+)-([0-9]+)\)', name)

        start = end = None
        if m is not None:
            start, end = map(int, m.groups())

        return start, end

    def get_bead_residue_indexes(self, bead_resi):
        m = re.search('\[([0-9]+)-([0-9]+)\)', bead_resi.residue.type)

        start = end = None
        if m is not None:
            start, end = map(int, m.groups())

        return start, end

    def show_missing_loops(self, change_radius=True):
        self.missingLoopsPbgName = str(self.beadModel.id) + " missing_loops"
        cmps_to_connect = []
        for bead in self.iterate_beads():
            # chain_id = rmf_viewer.rmf.getParentChainId(bead)
            chain_id = bead.residue.id.chainId
            start, end = self.get_bead_indexes(bead)
            cmps_to_connect.append([bead, chain_id, start, end])

        cas = []
        for ca in self.iterate_CAs():

            res_id = ca.residue.id.position
            chain_id = ca.residue.id.chainId

            cas.append([ca, chain_id, res_id])

        cas_for_chains = {}
        for key, igroup in groupby(sorted(cas, key=lambda x: x[1]), lambda x: x[1]):
            cas_sorted = sorted(igroup, key=lambda x: x[2])

            #we could do:
            # cas_for_chains[key] = cas_sorted
            #but add just CAs flanking missing regions + Ca of first resi + Ca of second resi
            cas_for_chains[key] = [cas_sorted[0]]
            for a1, a2 in pairwise(cas_sorted):
                if a2[2] - a1[2] > 1:
                    cas_for_chains[key].extend([a1, a2])

            cas_for_chains[key].append(cas_sorted[-1])

        missing_bead_radius = 2
        missing_def_color = chimera.colorTable.getColorByName('gray')
        grp = getPseudoBondGroup(self.missingLoopsPbgName, create=False)
        if grp is None:
            grp = getPseudoBondGroup(self.missingLoopsPbgName, create=True)
            for key, igroup in groupby(sorted(cmps_to_connect, key=lambda x: x[1]), lambda x: x[1]):
                beads_sorted = sorted(igroup, key=lambda x: x[2])
                for b1, b2 in pairwise(beads_sorted):
                    if b2[2] == b1[3]:
                        at1 = b1[0]
                        at2 = b2[0]
                        grp.newPseudoBond(at1, at2)

                for b in beads_sorted:
                    chain_id = b[1]
                    start = b[2]
                    end = b[3]
                    if chain_id in cas_for_chains:
                        for ca in cas_for_chains[chain_id]:
                            if None not in (start, end):
                                if ca[2] == start - 1 or ca[2] == end:
                                    at1 = b[0]
                                    at2 = ca[0]
                                    grp.newPseudoBond(at1, at2)
                                    at1.display = True



        for b in grp.pseudoBonds:
            at1, at2 = b.atoms
            at1.display = True
            at2.display = True

            if at1.name != 'CA':
                if change_radius:
                    at1.radius = missing_bead_radius
                at1.color = missing_def_color
            at2.display = True
            if at2.name != 'CA':
                if change_radius:
                    at2.radius = missing_bead_radius
                at2.color = missing_def_color



        grp.lineType = chimera.Dash
        grp.lineWidth = 4
        grp.color = missing_def_color


def get_CA_of_resi(resi):
    for atom in resi.atoms:
        if atom.name == 'CA':
            return atom

class XlinkBond(object):
    def __init__(self, pseudo_bond, link_pos1, link_pos2, xquest_xlink):
        self.pb = pseudo_bond
        self.xlink = xquest_xlink

        #link_pos - tuple of chain [string] and residue id [string]
        self.link_pos1 = link_pos1
        self.link_pos2 = link_pos2

    def get_chain_pos_pair(self):
        '''Return a pair of tuples with residue positions
        as (chain [string], resi_id [string]'''
        return self.link_pos1, self.link_pos2

class DataMgr(object):
    def __init__(self, model, data):
        """
        Groups methods to analyze a given model with respect to data.

        Subclass this class to create Data Managers.
        See InteractingResiDataMgr and XlinkDataMgr for examples.
        """

        self.model = model
        self.data = data
        self._handlers = []

class InteractingResiDataMgr(DataMgr):
    def __init__(self, model, data):
        super(InteractingResiDataMgr, self).__init__(model, data)

    def colorInteractingResi(self, fromComp=None, to=None, hide_others=False):

        # self.model.colorAll()

        for dataItem in self.data:
            for comp_from in dataItem.data.keys():
                if fromComp is not None and fromComp != comp_from:
                    continue

                for comp_to in dataItem.data[comp_from]:
                    if to is not None and to != comp_to:
                        continue

                    to_color = self.model.config.getColor(comp_to)
                    chains = self.model.config.getChainIdsBySubunitName(comp_from)
                    for chain in chains:
                        all_chain_resi = self.model.resi_lookup_map.get(chain)
                        if all_chain_resi:
                            for resi_from_pos in dataItem.data[comp_from][comp_to]:
                                resi_from_list = all_chain_resi.get(resi_from_pos)
                                if resi_from_list:
                                    for resi_from in resi_from_list:
                                        for atom in resi_from.atoms:
                                            atom.drawMode = chimera.Atom.Sphere
                                            atom.display = True
                                            atom.color = to_color
                                        resi_from.ribbonColor = to_color

class ConsurfDataMgr(DataMgr):
    def __init__(self, model, data):
        super(ConsurfDataMgr, self).__init__(model, data)
        self.defConsurfColors()
        self.load()

    def defConsurfColors(self):
        runCommand('colordef CONS10 1.00 1.00 0.59')
        runCommand('colordef CONS9 0.63 0.15 0.38')
        runCommand('colordef CONS8 0.94 0.49 0.67')
        runCommand('colordef CONS7 0.98 0.79 0.87')
        runCommand('colordef CONS6 0.99 0.93 0.96')
        runCommand('colordef CONS5 1.00 1.00 1.00')
        runCommand('colordef CONS4 0.92 1.00 1.00')
        runCommand('colordef CONS3 0.84 1.00 1.00')
        runCommand('colordef CONS2 0.55 1.00 1.00')
        runCommand('colordef CONS1 0.06 0.78 0.82')

    def color(self, subName):
        sels = defaultdict(list)
        subunit = getConfig().getSubunitByName(subName)
        if subunit is not None:
            chains = subunit.getChains()
            print self.data
            for dataItem in self.data:
                if dataItem.hasMapping() and subName in dataItem.mapping.values()[0]:
                    gr = dataItem.getGroupedByColor()
                    for colorId, resis in gr.iteritems():
                        for chain in chains:
                            sels[colorId].extend([str(resi)+'.'+chain.id for resi in resis])
        for colorId, sel in sels.iteritems():
            sel = ','.join(sel)
            runCommand('color CONS{colorId} #{modelId}:{sel}'.format(colorId=colorId, modelId=self.model.getModelId(), sel=sel))

    def load(self):
        pass

    def reload(self, config):
        data = []
        for item in config.dataItems:
            if item.type == xlinkanalyzer.CONSURF_DATA_TYPE:
                if item.data.active:
                    data.append(item.data)
        self.data = data
        self.load()

class XlinkDataMgr(DataMgr):
    def __init__(self, model, data):
        super(XlinkDataMgr, self).__init__(model, data)

        if 'configUpdated' in chimera.triggers.triggerNames():
            handler = chimera.triggers.addHandler('configUpdated', self.onConfigUpdated, None)
            self._handlers.append((chimera.triggers, 'configUpdated', handler))
        self.minLdScore = 0
        self.smartMode = False
        self.show_only_one = False
        self.load()

    def destroy(self):
        self._deleteHandlers()

        self.data = []
        self.deletePBG()
        self.xlinkAnalyzer = None

    def _deleteHandlers(self):
        while self._handlers:
            triggers, trigName, handler = self._handlers.pop()
            triggers.deleteHandler(trigName, handler)

    def scoreFilter(self, xb):
        '''
        xb - XlinkBond instance
        '''
        return ('ld-Score' in xb.xlink) and xb.xlink['ld-Score'] != '-' and float(xb.xlink['ld-Score']) >= self.minLdScore

    def compFilter(self, xb):
        return True

    def intraFilter(self, xb):
        return True

    def interFilter(self, xb):
        return True

    def load(self):

        self.ambig_xlink_sets = []

        self.objToXlinksMap = weakref.WeakKeyDictionary()

        self.xlinksSetsMerged = self._mergeDataSets()

        self.unique_xlinks_set = self.xlinksSetsMerged.get_unique_by_prots_resi()
        self.xlinks_grouped = self.unique_xlinks_set.group_by_pos()

        self.pbg = None
        self._make_PBG()
        self._createXlinkPseudobonds()

        for resi in self.model.iterateResidues():
            res_id = resi.id.position
            chain_id = resi.id.chainId
            xquest_name = self.model.config.getSubunitByChain(chain_id)
            if xquest_name:
                xlinks_for_prot = self.xlinks_grouped.get(xquest_name)
                if xlinks_for_prot:
                    xlinks_for_resi = xlinks_for_prot.get(str(res_id))
                    if xlinks_for_resi:
                        if hasattr(resi, 'resi'):
                            resi_key = resi.resi
                        else:
                            resi_key = resi
                        if resi not in self.objToXlinksMap:
                            self.objToXlinksMap[resi_key] = xlinks_for_resi
                        else:
                            self.objToXlinksMap[resi_key].extend(xlinks_for_resi)

    def onConfigUpdated(self, name, userData, o):
        self.reload(self.model.config)

    def reload(self, config):
        data = []
        for item in config.dataItems:
            if xlinkanalyzer.data.isXlinkItem(item):
                if item.data.active:
                    data.append(item.data)
        self.data = data
        self.deletePBG()
        self.xlinkAnalyzer = None
        self.load()
        self.updateDisplayed(threshold=xlinkanalyzer.XLINK_LEN_THRESHOLD, smart=self.smartMode, show_only_one=self.show_only_one)
        restyleXlinks([self], XLINK_LEN_THRESHOLD)

    def isCrosslinked(self, resId, chainId):
        isCrosslinked = False
        xquest_name = self.model.config.getSubunitByChain(chainId)

        if xquest_name is not None:
            xlinks_for_prot = self.xlinks_grouped.get(xquest_name)
            if xlinks_for_prot is not None:
                xlinks_for_resi = xlinks_for_prot.get(str(resId))
                if xlinks_for_resi is not None:
                    for xlink in xlinks_for_resi:
                        if ('ld-Score' in xlink) and xlink['ld-Score'] != '-' and float(xlink['ld-Score']) >= self.minLdScore:
                            if not pyxlinks.is_mono_link(xlink):
                                isCrosslinked = True
                            break

        return isCrosslinked

    def isMonolinked(self, resId, chainId):
        isMonolinked = False

        comp = self.model.config.getSubunitByChain(chainId)
        monolinks = self.xlinkAnalyzer.xlinks.get_by_both_pos(comp, resId, None, None)

        if monolinks is not None:
            for monolink in monolinks:
                if ('ld-Score' in monolink) and monolink['ld-Score'] != '-' and float(monolink['ld-Score']) >= self.minLdScore:
                    isMonolinked = True
                    break

        return isMonolinked

    def isExpectedMonolink(self, resId, chainId, byPredictor=True, byLength=True):
        '''Run predictMonolinkable before
        '''
        min_pept_length=6
        max_pept_length=50

        comp = self.model.config.getSubunitByChain(chainId)
        monolinks = self.xlinkAnalyzer.xlinks.get_by_both_pos(comp, resId, None, None)

        observable = None

        if monolinks is not None:

            observable_preds = []
            pept_lengths = []
            for monolink in monolinks:
                observable_preds.append(monolink.get('Observable'))
                pept = pyxlinks.get_pepts(monolink)[0]
                if pept is None:
                    return True

                pept_lengths.append(len(pept))

            if byPredictor:
                if len(observable_preds) > 0:
                    if 'Yes' in observable_preds:
                        observable = True
                    else:
                        observable = False

            if byLength and len(pept_lengths) > 0:
                for pept_len in pept_lengths:
                    if min_pept_length <= pept_len <= max_pept_length:
                        len_ok = True
                        break
                    else:
                        len_ok = False


                if not len_ok:
                    observable = False

                if len_ok and not byPredictor:
                    observable = True

        return observable

    def showModifiedMap(self, colorMonolinked=True, colorXlinked=True, colorExpected=True, colorNotExpected=True, byPredictor=True, byLength=True):
        expectedColor = 'red'

        self.xlinkAnalyzer = XlinkAnalyzer(get_gui().configFrame.config.getPyxlinksConfig())
        self.xlinkAnalyzer.load_xlinks(from_cfg=False, xlinksSet=self.xlinksSetsMerged.get_deep_copy())

        self.xlinkAnalyzer.gen_monolinks_possible_in_structure(self.model, possible_fn=is_crosslinkable)

        if (colorExpected or colorNotExpected):
            self.predictMonolinkable(min_pept_length=5, max_pept_length=50)

        for xlink in self.xlinkAnalyzer.xlinks.data:
            if ('ld-Score' in xlink) and xlink['ld-Score'] != '-' and float(xlink['ld-Score']) < self.minLdScore:
                xlink['Observed'] = 'No'


        # color_visible_xlinking_resi(chimera.colorTable.getColorByName('light gray'))
        runCommand('color light gray #' + str(self.model.getModelId()))

        for resi in self.model.iterateResidues():
            color = 'light gray'
            resId = resi.id.position
            chainId = resi.id.chainId

            crosslinked = self.isCrosslinked(resId, chainId)
            monolinked = self.isMonolinked(resId, chainId)

            observable = self.isExpectedMonolink(resId, chainId, byPredictor=byPredictor, byLength=byLength)

            show = False

            if is_crosslinkable(resi) and colorExpected:
                show = True
                color = expectedColor

            if colorNotExpected and observable is False and is_crosslinkable(resi):
                show = True
                color = 'yellow'

            if colorMonolinked and monolinked:
                show = True
                color = 'blue'

            if colorXlinked and crosslinked:
                show = True
                color = 'blue'

            if show:
                for atom in resi.atoms:
                    atom.drawMode = chimera.Atom.Sphere
                    atom.display = True
                    atom.color = chimera.colorTable.getColorByName(color)
                    atom.surfaceColor = chimera.colorTable.getColorByName(color)

    def predictMonolinkable(self, min_pept_length=None, max_pept_length=None):

        self.xlinkAnalyzer.make_xlinked_peptides_for_all_seqs(missed_cleavages=0,
                                                        min_pept_length=None, #keep all to have data which are too short/long
                                                        max_pept_length=None)

        self.xlinkAnalyzer.add_theoretical_xlinks()

        self.xlinkAnalyzer.add_seq_features_to_xlinks()

        self.xlinkAnalyzer.predict_monolinkable(min_pept_length=min_pept_length, max_pept_length=max_pept_length, min_ld_score=self.minLdScore)

    def _make_PBG(self):

        if not self.pbg:

            mgr = chimera.PseudoBondMgr.mgr()
            basename = "Restraints - %s" % self.model.getModelName()

            name = basename
            i = 2
            while mgr.findPseudoBondGroup(name):
                name = "%s (%d)" % (basename, i)
                i += 1

            self.pbg = getPseudoBondGroup(name, modelID=self.model.getModelId(), associateWith=[self.model.getChimeraModel()], hidden=True)

        return self.pbg

    def deletePBG(self):
        if self.pbg:
            chimera.openModels.close(self.pbg)
        self.pbg = None

    def _mergeDataSets(self):
        '''Create merged pyxlinks.XlinksSet object where all names were renamed to subunit names.

        Can handle input XlinksSets with different prot names, and unify the names to subunit names.
        '''
        xlinkDataSets = self.data
        xlinkSetsCopies = [] #xlinkSets copies with names changed to subunit names
        for xlinkDataSet in xlinkDataSets:
            if xlinkDataSet.xlinksSets:
                xlinkSetsCopies.append(xlinkDataSet.xlinksSets.get_deep_copy())

        for xlinkSet, xlinkDataSet in zip(xlinkSetsCopies, xlinkDataSets):
            for xlink in xlinkSet.data:
                if xlink['Protein1'] in xlinkDataSet:
                    comps = xlinkDataSet[xlink['Protein1']]
                    if comps:
                        xlink['Protein1'] = comps[0].name
                if xlink['Protein2'] in xlinkDataSet:
                    comps= xlinkDataSet[xlink['Protein2']]
                    if comps:
                        xlink['Protein2'] = comps[0].name

        if xlinkSetsCopies:
            xlinksSetsMerged = sum(xlinkSetsCopies)
        else:
            xlinksSetsMerged = pyxlinks.XlinksSet()

        return xlinksSetsMerged

    def _createXlinkPseudobonds(self):
        uniqueXlinksSetsMerged = self.xlinksSetsMerged.get_unique_by_prots_resi()

        self.obj_to_xlink_pbs_map = weakref.WeakKeyDictionary()
        self.pbToXlinkMap = weakref.WeakKeyDictionary()

        for xlink in uniqueXlinksSetsMerged.data:
            protein1 = pyxlinks.get_protein(xlink, 1)
            protein2 = pyxlinks.get_protein(xlink, 2)
            try:
                chains1 = self.model.config.getChainIdsBySubunitName(protein1)
                chains2 = self.model.config.getChainIdsBySubunitName(protein2)
            except:
                continue

            pos1 = pyxlinks.get_AbsPos(xlink, 1)
            pos2 = pyxlinks.get_AbsPos(xlink, 2)

            chain_pos_pair1 = product(chains1, [pos1])
            chain_pos_pair2 = product(chains2, [pos2])

            links = product(chain_pos_pair1, chain_pos_pair2)
            to_same_bead = False
            for link_pos1, link_pos2 in links:
                chain1 = link_pos1[0]
                link_resid1 = int(link_pos1[1])
                chain2 = link_pos2[0]
                link_resid2 = int(link_pos2[1])
                try:
                    resi_list1 = self.model.resi_lookup_map[chain1][link_resid1]
                    resi_list2 = self.model.resi_lookup_map[chain2][link_resid2]
                except KeyError:
                    continue

                for resi1, resi2 in product(resi_list1, resi_list2):
                    at1 = self.getAtomToLink(resi1)
                    at2 = self.getAtomToLink(resi2)

                    if (link_resid1 != link_resid2) and hasattr(resi1, 'resi') and hasattr(resi2, 'resi') and at1 is at2: #(resi1.resi.id.position == resi2.resi.id.position):  # can happen for beads
                        to_same_bead = True
                        break
            if to_same_bead:
                continue

            chain_pos_pair1 = product(chains1, [pos1])
            chain_pos_pair2 = product(chains2, [pos2])
            links = product(chain_pos_pair1, chain_pos_pair2)

            # xlink_set = {'xlink': xlink, 'xlinkBonds': []}
            xlink_set = []

            for link_pos1, link_pos2 in links:
                chain1 = link_pos1[0]
                link_resid1 = int(link_pos1[1])
                chain2 = link_pos2[0]
                link_resid2 = int(link_pos2[1])
                try:
                    resi_list1 = self.model.resi_lookup_map[chain1][link_resid1]
                    resi_list2 = self.model.resi_lookup_map[chain2][link_resid2]
                except KeyError:
                    continue

                for resi1, resi2 in product(resi_list1, resi_list2):
                    at1 = self.getAtomToLink(resi1)
                    at2 = self.getAtomToLink(resi2)

                    if at1 is not at2 and not (pyxlinks.is_clearly_dimeric(xlink) and (chain1 == chain2)): #cannot check this way because of beads
                        # if pyxlinks.is_clearly_dimeric(xlink) and (chain1 == chain2):
                        #     continue
                    # if not ((link_resid1 == link_resid2) and (chain1 == chain2)):
                        try:
                            pb = self.pbg.newPseudoBond(at1, at2)
                        except TypeError:  # may happen if at1 is at2, happens for beads
                            pb = None
                        else:
                            pb.drawMode = Bond.Spring
                            pb.display = Bond.Always
                            pb.halfbond = False
                            for ca in (at1, at2):
                                if ca in self.obj_to_xlink_pbs_map:
                                    self.obj_to_xlink_pbs_map[ca].append(pb)
                                else:
                                    self.obj_to_xlink_pbs_map[ca] = [pb]

                        xb = XlinkBond(pb, link_pos1, link_pos2, xlink)
                        if pb is not None:
                            self.pbToXlinkMap[pb] = xb
                        # xlink_set.append([xlink, link_pos1, link_pos2, pb])
                        # xlink_set['xlinkBonds'].append(xb)
                        xlink_set.append(xb)

            if len(xlink_set) > 0:
                self.ambig_xlink_sets.append(xlink_set)

    def getAtomToLink(self, resi):
        for atom in resi.atoms:
            if atom.name == 'CA':
                return atom
        return resi.atoms[0]

    def iterXlinkPseudoBonds(self):
        if self.pbg:
            for b in self.pbg.pseudoBonds:
                yield b

    def iter_all_xlinks(self):
        for x_set in self.ambig_xlink_sets:
            for x in x_set:
                yield x

    def hideAllXlinks(self):
        for b in self.iterXlinkPseudoBonds():
            b.display = False

    def showAllXlinks(self):
        self.compFilter = lambda x: True
        self.interFilter = lambda x: True
        self.intraFilter = lambda x: True
        self.updateDisplayed(threshold=xlinkanalyzer.XLINK_LEN_THRESHOLD, smart=self.smartMode, show_only_one=self.show_only_one)

    def updateDisplayed(self, threshold=XLINK_LEN_THRESHOLD, smart=True, show_only_one=False):

        def nFilter(filters, objects):
            for f in filters:
                objects = ifilter(f, objects)
            return objects

        for xlink_set in self.ambig_xlink_sets:
            to_hide = []
            if smart:
                to_show, to_hide = self._get_smart_list(xlink_set, threshold, show_only_one=show_only_one)
            else:
                to_show = xlink_set 

            out = nFilter([self.interFilter, self.intraFilter, self.compFilter, self.scoreFilter], to_show)
            for x in to_show:
                if x.pb is not None:
                    if x in out: 
                        x.pb.display = True
                    else:
                        x.pb.display = False

            if to_hide:
                for x in to_hide:
                    if x.pb:
                        x.pb.display = False

    def mapXlinkResi(self, name, to=None, hide_others=True):
        if hide_others:
            self.model.showOnly(name)
        else:
            self.model.show(name)

        self.model.color(name)
        self.hideAllXlinks()
        self.color_xlinked(to)

    def getNonCrosslinkableXlinks(self, method=None):
        if method is None:
            method = is_crosslinkable

        out = []
        for x in self.iter_all_xlinks():
            if not (method(x.pb.atoms[0].residue) and method(x.pb.atoms[1].residue)):
                out.append(x)

        return out
        
    def resetView(self):
        #undo crosslink resi mapped
        for obj, f in self.iter_obj_xlinks():
            obj_atoms = get_atoms_for_obj(obj)
            for atom in obj_atoms:
                if is_normal_pdb_resi(atom.residue):
                    atom.drawMode = 2 #default for chimera
                    atom.display = False

        #undo modified map
        for resi in self.model.iterateResidues():
            if is_crosslinkable(resi):
                obj_atoms = get_atoms_for_obj(resi)
                for atom in obj_atoms:
                    if is_normal_pdb_resi(atom.residue):
                        atom.drawMode = 2 #default for chimera
                        atom.display = False

        for resi in self.objToXlinksMap:
            obj_atoms = get_atoms_for_obj(resi)
            for atom in obj_atoms:
                if is_normal_pdb_resi(atom.residue):
                    atom.drawMode = 2 #default for chimera
                    atom.display = False

        if hasattr(self.model, 'show_missing_loops'):
            self.model.show_missing_loops()

    def color_xlinked(self, to=None, toDomain=None, fromComp=None, minLdScore=None, color=None, colorByCompTo=False, uncolorOthers=False):
        """
        toDomain - xlinkanalyzer.Domain object or domain name
        color - chimera.MaterialColor or string (overrides colorByCompTo)
        colorByCompTo - color by color of a subunit it crosslinks
        """

        if color is None and not colorByCompTo:
            to_color = chimera.MaterialColor(255,0,0)

        if color is not None:
            if isinstance(color, basestring):
                to_color = chimera.colorTable.getColorByName(color)
            elif isinstance(color, tuple) or isinstance(color, list):
                # color = chimera.MaterialColor(*[int(255*x) for x in color])
                to_color = chimera.MaterialColor(*[x for x in color])
            else:
                to_color = color

        good = []
        bad = []
        for obj, f in self.iter_obj_xlinks():
            xlinked_to_comp = None
            xlinked_to = None
            subunit = self.model.config.getSubunitByChain(get_chain_for_chimera_obj(obj))

            # xlinked_subunits = list(data_interface.get_xlinked_components(f))
            # xlinked_subunits = [pyxlinks.get_protein(f, 1), pyxlinks.get_protein(f, 2)] #xlinks return by self.iter_obj_xlinks are renamed to subunit names already

            prot1 = pyxlinks.get_protein(f, 1)
            pos1 = pyxlinks.get_AbsPos(f, 1)
            prot2 = pyxlinks.get_protein(f, 2)
            pos2 = pyxlinks.get_AbsPos(f, 2)
            objResiId = str(obj.id.position)

            if prot1 == subunit and pos1 == objResiId:
                posTo = pos2
                xlinked_to = prot2
            elif prot2 == subunit and pos2 == objResiId:
                posTo = pos1
                xlinked_to = prot1

            xlinked_to_comp = self.model.config.getSubunitByName(xlinked_to)

            if minLdScore is not None and float(f['ld-Score']) < minLdScore:
                bad.append([obj, xlinked_to])
                continue

            if to is not None and xlinked_to_comp is not None:
                if not to.contains(xlinked_to_comp.name, posTo):
                    bad.append([obj, xlinked_to])
                    continue

            if fromComp is not None and fromComp != subunit:
                bad.append([obj, xlinked_to])
                continue

            if xlinked_to is not None:
                good.append([obj, xlinked_to])

        if uncolorOthers:
            for obj, xlinked_to in bad:
                obj_atoms = get_atoms_for_obj(obj)
                for atom in obj_atoms:
                    # if atom.residue.type == 'LYS':
                    if is_normal_pdb_resi(atom.residue):
                        if atom.residue.ribbonDisplay:
                            atom.drawMode = chimera.Atom.Sphere
                            atom.display = False

                    if atom.display:
                        atom.color = self.model.config.getColor(xlinked_to)

                    atom.surfaceColor = self.model.config.getColor(xlinked_to)

        for obj, xlinked_to in good:
            if colorByCompTo:
                if to:
                    to_color = to.color
                else:
                    to_color = self.model.config.getColor(xlinked_to)

            obj_atoms = get_atoms_for_obj(obj)
            for atom in obj_atoms:
                # if atom.residue.type == 'LYS':
                if is_normal_pdb_resi(atom.residue):
                    if atom.residue.ribbonDisplay:
                        atom.drawMode = chimera.Atom.Sphere
                        atom.display = True

                if atom.display:
                    atom.color = to_color

                atom.surfaceColor = to_color

    def color_visible_xlinking_resi(self, color):
        for obj, f in self.iter_obj_xlinks():
            obj_atoms = get_atoms_for_obj(obj)
            for atom in obj_atoms:
                # if atom.residue.type == 'LYS':
                if is_normal_pdb_resi(atom.residue):
                    if atom.residue.ribbonDisplay:
                        atom.drawMode = chimera.Atom.Sphere
                        atom.display = True

                if atom.display:
                    atom.color = color

    def hide_intra_xlinks(self):
        def filter_fn(x):
            if not pyxlinks.is_intra(x.xlink):
                return True

        self.intraFilter = filter_fn
        self.updateDisplayed(threshold=xlinkanalyzer.XLINK_LEN_THRESHOLD, smart=self.smartMode, show_only_one=self.show_only_one)

    def hideInterxlinks(self):
        def filter_fn(x):
            if not pyxlinks.is_inter(x.xlink):
                return True

        self.interFilter = filter_fn
        self.updateDisplayed(threshold=xlinkanalyzer.XLINK_LEN_THRESHOLD, smart=self.smartMode, show_only_one=self.show_only_one)

    def iter_obj_xlinks(self, skip_mono=True):
        for obj, fs in self.objToXlinksMap.iteritems():
            for f in fs:
                if not pyxlinks.is_mono_link(f):
                    yield obj, f

    def hide_not_satisfied(self, threshold):
        for b in self.iterXlinkPseudoBonds():
            if not is_satisfied(b, threshold):
                    b.display = False

    def hide_by_ld_score(self, threshold):
        self.minLdScore = threshold
        for x in self.iter_all_xlinks():
            if x.pb is not None:
                if not self.scoreFilter(x):
                    x.pb.display = False

    def hideFromSelection(self, atomSpec):
        xfrom_sel = selection.OSLSelection(atomSpec)
        xfrom_sel = selection.ItemizedSelection(xfrom_sel.residues())
        for b in self.iterXlinkPseudoBonds():
            at1 = b.atoms[0]
            at2 = b.atoms[1]
            if xfrom_sel.contains(at1) or xfrom_sel.contains(at2):
                b.display = False

    def showOnlyFromSelection(self, atomSpec):
        '''
        Careful: doesn't support smart homo-oligomeric mode!
        TODO: use updateDisplayed
        '''
        xfrom_sel = selection.OSLSelection(atomSpec)
        xfrom_sel = selection.ItemizedSelection(xfrom_sel.residues())

        for x_set in self.ambig_xlink_sets:
            # found_satisfied = False
            xlink = x_set[0].xlink
            if float(xlink['ld-Score']) >= self.minLdScore:
                for x in x_set:
                    if x.pb:
                        at1 = x.pb.atoms[0]
                        at2 = x.pb.atoms[1]
                        if xfrom_sel.contains(at1) or xfrom_sel.contains(at2):
                            x.pb.display = True
                        else:
                            x.pb.display = False

    def _get_smart_list(self, xlink_set, threshold, show_only_one=False):
        '''
        Get a list of xlinks from ambigous xlink set (e.g. set of equivalent xlinks in homo-oligomers).

        Returns all satisfied as first list and others as second list.
        If there is no satisfied xlink, return shortest one in the first list.

        o xlink_set - xlink set from self.ambig_xlink_sets
        o threshold - satisfied threshold
        '''
        to_show = []
        to_hide = []

        #need to sort for groupby
        #sorted can sort by tuple
        xlink_set_sorted_by_first_resi = sorted(xlink_set, key=lambda x: x.get_chain_pos_pair()[0])
        grouped = groupby(xlink_set_sorted_by_first_resi, key=lambda x: x.get_chain_pos_pair()[0])  # grouped by first resi

        def sort_key(x):
            if x.pb is not None:
                return x.pb.length()
            else:
                return 10000000

        def cmp_by_chains(x, y):
            c1 = x.get_chain_pos_pair()[0][0]
            c2 = y.get_chain_pos_pair()[0][0]

            out1 = []
            out2 = []
            for a, b in izip_longest(c1, c2, fillvalue=' '):
                try:
                    int(a)
                except ValueError:
                    is_a_letter = True
                else:
                    is_a_letter = False

                try:
                    int(b)
                except ValueError:
                    is_b_letter = True
                else:
                    is_b_letter = False

                if is_a_letter and is_b_letter:
                    out1.append(cmp(a, b))
                    out2.append(-cmp(a, b))
                elif (not is_a_letter) and (not is_b_letter):
                    out1.append(cmp(a, b))
                    out2.append(-cmp(a, b))
                else:
                    out1.append(-cmp(a, b))
                    out2.append(cmp(a, b))

            return cmp(out1, out2)

        def approx_equal(a, b, tol):
            if a.pb is not None:
                a = a.pb.length()
            else:
                a = 1000000000

            if b.pb is not None:
                b = b.pb.length()
            else:
                b = 1000000000
            return abs(a-b) <= (abs(a)+abs(b))/2 * tol

        show_groups = []

        for k, g in grouped:
            show_groups.append({
                'satisfied': [],
                'shortest': []
                })
            found_satisfied = False
            inter_intra_ambig_list_sorted = sorted(g, key=lambda x: sort_key(x))
            #show xlink always if it is satisfied
            for link in inter_intra_ambig_list_sorted:
                b = link.pb
                if b is not None:
                    if is_satisfied(b, threshold) and (float(link.xlink['ld-Score']) >= self.minLdScore):
                        show_groups[-1]['satisfied'].append(link)
                        found_satisfied = True

            #get the shortest xlink if not found_satisfied
            if not found_satisfied:
                shortest = inter_intra_ambig_list_sorted[0]
                if shortest is not None:
                    if float(shortest.xlink['ld-Score']) >= self.minLdScore:
                        # to_show.append(shortest)
                        show_groups[-1]['shortest'].append(shortest)

        if show_only_one:
            satisfied = []
            shortest = []
            for sg in show_groups:
                satisfied.extend(sg['satisfied'])
                shortest.extend(sg['shortest'])

            satisfied = sorted(satisfied, key=lambda x: sort_key(x))
            shortest = sorted(shortest, key=lambda x: sort_key(x))

            if len(satisfied) > 0:
                if len(satisfied) > 1:
                    # print [(x.get_chain_pos_pair()[1][0], x.get_chain_pos_pair()[1][0]) for x in sorted(satisfied, cmp=cmp_by_chains)]
                    to_show.append(sorted(satisfied, cmp=cmp_by_chains)[0])
                    # to_show.extend(sorted(satisfied, cmp=cmp_by_chains))
                else:
                    to_show.append(satisfied[0])
            elif len(shortest) > 0:
                if len(shortest) > 1:
                    shortest_to_use = []
                    first_shortest = shortest[0]
                    shortest_to_use.append(first_shortest)
                    for other_shortest in shortest[1:]:
                        if approx_equal(first_shortest, other_shortest, 0.1):
                            shortest_to_use.append(other_shortest)
                    to_show.append(sorted(shortest_to_use, cmp=cmp_by_chains)[0])
                else:
                    to_show.append(shortest[0])
        else:
            for sg in show_groups:
                to_show.extend(sg['satisfied'])
                to_show.extend(sg['shortest'])

        for link in xlink_set:
            b = link.pb
            if b is not None:
                if link not in to_show:
                    to_hide.append(link)

        return to_show, to_hide

    def show_xlinks_smart(self, threshold=XLINK_LEN_THRESHOLD, show_only_one=False):
        self.updateDisplayed(smart=True, threshold=threshold, show_only_one=show_only_one)

    def show_xlinks_from(self, xfrom, to=None, threshold=XLINK_LEN_THRESHOLD, hide_others=True, smart=True, show_only_one=False):
        def xfrom_fn(x):
            protein1 = pyxlinks.get_protein(x.xlink, 1)
            protein2 = pyxlinks.get_protein(x.xlink, 2)
            xlinked_subunits = [protein1, protein2]
            if xfrom not in xlinked_subunits:
                if hide_others:
                    return False
                elif x.pb is not None:
                    return x.pb.display
            elif to is not None:                
                xlinked_subunits.remove(xfrom)
                subunit_other = xlinked_subunits[0]
                if to != subunit_other:
                    if hide_others:
                        return False
                    elif x.pb is not None:
                        return x.pb.display

            return True

        self.compFilter = xfrom_fn
        self.updateDisplayed(threshold, smart, show_only_one)

    def countSatisfiedBetweenSelections(self, threshold, xfrom=None, xto=None):
        """
        Count satisfied and violated between selections
        specified as Chimera atom spec strings
        (.e.g :100-200.A)

        """
        xfrom_sel = selection.OSLSelection(xfrom)
        xfrom_sel = selection.ItemizedSelection(xfrom_sel.residues())
        xto_sel = selection.OSLSelection(xto)
        xto_sel= selection.ItemizedSelection(xto_sel.residues())

        satisfied = []
        violated = []
        all_xlink_sets = []

        for x_set in self.ambig_xlink_sets:
            found_satisfied = False
            xlink = x_set[0].xlink
            if float(xlink['ld-Score']) >= self.minLdScore:
                for x in x_set:
                    if x.pb:
                        if is_satisfied(x.pb, threshold):
                            at1 = x.pb.atoms[0]
                            at2 = x.pb.atoms[1]
                            if (xfrom_sel.contains(at1) and xto_sel.contains(at2)) or \
                                (xfrom_sel.contains(at2) and xto_sel.contains(at1)):
                                satisfied.append(x_set)
                                found_satisfied = True
                                break

                if not found_satisfied:
                    sortedByLength = sorted([xl for xl in x_set if xl.pb], key=lambda xl1: xl1.pb.length())
                    at1 = sortedByLength[0].pb.atoms[0]
                    at2 = sortedByLength[0].pb.atoms[1]
                    if (xfrom_sel.contains(at1) and xto_sel.contains(at2)) or \
                        (xfrom_sel.contains(at2) and xto_sel.contains(at1)):
                        violated.append(x_set)

        return {
            'satisfied': len(satisfied),
            'violated': len(violated)
        }

    def getTable(self, selections, data):
        names = [sel['name'] for sel in selections]

        rows = []
        rows.append([' '] + names)
        cols_no = len(names)
        for name1 in names:
            row = []
            for name2 in names:
                count = data[frozenset((name1, name2))]
                row.append(count)

            #pad the list so it makes nice square table
            row = [name1] + [' '] * (cols_no - len(row)) + row
            rows.append(row)

        return rows


    def createTables(self, selections):
        """
        o x: xlinkDataMgr
        o selections: list like this:
            selections = [
                {
                    'name': 'PA nuc',
                    'sel': ':1-185.A',
                },
                {
                    'name': 'PA C',
                    'sel': ':201-714.A',
                },
                {
                    'name': 'PB1',
                    'sel': ':.B',
                },
                {
                    'name': 'PB2 N',
                    'sel': ':-1-250.C',
                },
                {
                    'name': 'PB2 C',
                    'sel': ':250-750.C',
                },
                {
                    'name': 'PB1-PB2 lobe',
                    'sel': ':662-754.B,-1-250.C',
                }
            ]
        """
        pairs = combinations_with_replacement(selections, 2)

        violated = {}
        satisfied = {}
        for xfrom, xto in pairs:
            counts = self.countSatisfiedBetweenSelections(30, xfrom['sel'], xto['sel'])

            satisfied[frozenset((xfrom['name'], xto['name']))] = counts['satisfied']

            violated[frozenset((xfrom['name'], xto['name']))] = counts['violated']

        # print "violated:"
        violatedRows = self.getTable(selections, violated)
        # print "satisfied:"
        satisfiedRows = self.getTable(selections, satisfied)

        outLines = ["violated:"]
        for row in violatedRows:
            outLines.append(','.join([str(s) for s in row]))
        outLines.append("satisfied:")
        for row in satisfiedRows:
            outLines.append(','.join([str(s) for s in row]))

        #TODO: change initialdir to project dir
        f = tkFileDialog.asksaveasfile(mode='w', defaultextension=".csv", initialdir=None)
        if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
            return

        f.write("\n".join(outLines))
        f.close()

    def countSatisfied(self, threshold):
        '''
        Count xlink sets with satisfied and violated xlinks.

        To remind, we use xlink sets from ambig_xlink_sets, which group
        symmetry related xlinks into xlink_sets.
        '''
        satisfied = []
        violated = []
        all_xlink_sets = []

        by_subunit_violated = defaultdict(list)
        by_pair_violated = defaultdict(list)

        reprXlinks = [] #xlinks from xlink sets used for distance calculation
        for x_set in self.ambig_xlink_sets:
            found_satisfied = False
            xlink = x_set[0].xlink
            if float(xlink['ld-Score']) >= self.minLdScore:
                all_xlink_sets.append(x_set)
                for x in x_set:
                    if x.pb:
                        if is_satisfied(x.pb, threshold):
                            satisfied.append(x_set)
                            reprXlinks.append(x)

                            found_satisfied = True
                            break

                if not found_satisfied:
                    x_set_with_pb = [xl for xl in x_set if xl.pb]
                    if len(x_set_with_pb) > 0:
                        sortedByLength = sorted(x_set_with_pb, key=lambda xl: xl.pb.length())
                        reprXlinks.append(sortedByLength[0])

                        violated.append(x_set)

                        if pyxlinks.is_inter(xlink):
                            for i in (1, 2):
                                by_subunit_violated[pyxlinks.get_protein(xlink, i)].append(x_set)
                        else:
                            by_subunit_violated[pyxlinks.get_protein(xlink, 1)].append(x_set)


                        by_pair_violated[frozenset([pyxlinks.get_protein(xlink, 1), pyxlinks.get_protein(xlink, 2)])].append(x_set)

        #sorted_by_subunit_violated - dict mapping comp [string] to list of ambig xlinks sets
        sorted_by_subunit_violated = sorted(by_subunit_violated.iteritems(), key=lambda a: len(a[1]), reverse=True)
        # for comp, comp_violated in sorted_by_subunit_violated:
        #     print comp, len(comp_violated)

        #sorted_by_pair_violated - dict mapping comp pair [frozenset] to list of ambig xlinks sets
        #for intra xlinks frozenset contains single subunit name e.g. frozenset(['A190'])
        sorted_by_pair_violated = sorted(by_pair_violated.iteritems(), key=lambda a: len(a[1]), reverse=True)
        # for comp, comp_violated in sorted_by_pair_violated:
        #     print comp, len(comp_violated)



        return {
            'satisfied': len(satisfied),
            'violated': len(violated),
            'all': len(all_xlink_sets),
            'satisfied %': self.percentage(len(satisfied), len(all_xlink_sets)),
            'violated %': self.percentage(len(violated), len(all_xlink_sets)),
            'sorted_by_subunit_violated': sorted_by_subunit_violated,
            'sorted_by_pair_violated': sorted_by_pair_violated,
            'reprXlinks': reprXlinks
        }

    def getSelectedXlinkPseudobonds(self):
        out = []
        for pb in selection.currentPseudobonds():
            if pb in self.pbg.pseudoBonds:
                out.append(pb)

        return out

    def exportSelectedXlinkList(self):
        selPbs = self.getSelectedXlinkPseudobonds()
        xlinks = []
        for pb in selPbs:
            xlinkBond = self.pbToXlinkMap[pb]
            oriXlinks = self.getOriXlinks(xlinkBond.xlink, copiesWithSource=True)
            comp1 = pyxlinks.get_protein(xlinkBond.xlink, 1)
            comp2 = pyxlinks.get_protein(xlinkBond.xlink, 2)

            for xlink in oriXlinks:
                xlink['distance'] = xlinkBond.pb.length()
                xlink['Subunit1'] = comp1
                xlink['Subunit2'] = comp2

            xlinks.extend(oriXlinks)

        if len(xlinks) > 0:
            fieldnames = self.xlinksSetsMerged.fieldnames
            if 'distance' not in fieldnames:
                fieldnames.append('distance')
            if 'Subunit1' not in fieldnames:
                fieldnames.insert(fieldnames.index('Protein1')+1, 'Subunit1')
            if 'Subunit2' not in fieldnames:
                fieldnames.insert(fieldnames.index('Protein2')+1, 'Subunit2')
            xlinksSet = pyxlinks.XlinksSet(xlink_set_data=xlinks, fieldnames=fieldnames)

            #TODO: change initialdir to project dir
            f = tkFileDialog.asksaveasfile(mode='w', defaultextension=".csv", initialdir=None)
            if f is None: # asksaveasfile return `None` if dialog closed with "cancel".
                return

            xlinksSet.save_to_file(f, quoting=csv.QUOTE_NONNUMERIC)

    def percentage(self, part, whole):
        try:
            return round(100 * float(part)/float(whole), 1)
        except ZeroDivisionError:
            return 0

    def color_by_satisfaction(self, threshold, show_satisfied_only=False):
        # color_visible_xlinking_resi(chimera.colorTable.getColorByName('light gray'))
        runCommand('color light gray')
        good_color = chimera.MaterialColor(0,0,255)
        # good_color = chimera.colorTable.getColorByName('green')
        bad_color = chimera.MaterialColor(255,0,0)
        for obj, pbs in self.iter_xlinked_atoms_and_pbs():
            for b in pbs:
                if is_satisfied(b, threshold):
                    for atom in obj.residue.atoms:
                        # if atom.residue.type == 'LYS':
                        if is_normal_pdb_resi(atom.residue):
                            atom.drawMode = chimera.Atom.Sphere
                        atom.display = True
                        atom.color = good_color
                    break
                else:
                    if not show_satisfied_only:
                        for atom in obj.residue.atoms:
                            # if atom.residue.type == 'LYS':
                            if is_normal_pdb_resi(atom.residue):
                                atom.drawMode = chimera.Atom.Sphere
                            atom.display = True
                            atom.color = bad_color

    def get_xlink_pbs_for_obj(self, obj):
        return self.obj_to_xlink_pbs_map.get(obj)

    def iter_xlinked_atoms_and_pbs(self):
        for at, pbs in self.obj_to_xlink_pbs_map.iteritems():
            yield at, pbs

    def getOriXlinks(self, xlink, copiesWithSource=False):
        """Retrieve xlinks from original unmerged, not renamed dataset.

        Works by reading subunit names from xlink, translating them back to xquest names,
        and retrieving by prot name/resi number from original datastes

        xlink - xlink for which to get original xlinks
        """
        comp1 = self.model.config.getSubunitByName(pyxlinks.get_protein(xlink, 1))
        comp2 = self.model.config.getSubunitByName(pyxlinks.get_protein(xlink, 2))
        resi1 = pyxlinks.get_AbsPos(xlink, 1)
        resi2 = pyxlinks.get_AbsPos(xlink, 2)

        oriXlinks = []
        for data in self.data:
            if not data.xlinksSets.grouped_by_both_pos:
                data.xlinksSets.group_by_both_pos()

            xQuestNames1 = data.getProteinsBySubunit(comp1)
            xQuestNames2 = data.getProteinsBySubunit(comp2)

            protPairs = product(xQuestNames1, xQuestNames2)

            for protein1, protein2 in protPairs:
                matching = data.xlinksSets.get_by_both_pos(protein1, resi1, protein2, resi2)

                if matching:
                    if copiesWithSource:
                        matching = map(copy.deepcopy, matching)
                        for xlinkMatch in matching:
                            xlinkMatch["source"] = data.name
                    oriXlinks.extend(matching)

        return oriXlinks

    def getXlinksWithDistances(self, xlinkStats):
        xlinks = []
        for xlinkBond in xlinkStats['reprXlinks']:
            oriXlinks = self.getOriXlinks(xlinkBond.xlink, copiesWithSource=True)
            comp1 = pyxlinks.get_protein(xlinkBond.xlink, 1)
            comp2 = pyxlinks.get_protein(xlinkBond.xlink, 2)

            for xlink in oriXlinks:
                xlink['distance'] = xlinkBond.pb.length()
                # xlink['Subunit1'] = comp1
                # xlink['Subunit2'] = comp2

            xlinks.extend(oriXlinks)

        fieldnames = self.xlinksSetsMerged.fieldnames
        if 'distance' not in fieldnames:
            fieldnames.append('distance')
        # if 'Subunit1' not in fieldnames:
        #     fieldnames.insert(fieldnames.index('Protein1')+1, 'Subunit1')
        # if 'Subunit2' not in fieldnames:
        #     fieldnames.insert(fieldnames.index('Protein2')+1, 'Subunit2')
        xlinksSet = pyxlinks.XlinksSet(xlink_set_data=xlinks, fieldnames=fieldnames)

        return xlinksSet

    def exportXlinksWithDistancesToCSV(self, xlinkStats, filename):
        xlinksSet = self.getXlinksWithDistances(xlinkStats)

        xlinksSet.save_to_file(filename, quoting=csv.QUOTE_NONNUMERIC)

class XlinkAnalyzer(pyxlinks.XlinkAnalyzerA):
    def __init__(self, data_config):
        super(XlinkAnalyzer, self).__init__(data_config)

    def make_contact_matrix(self, model, possible_fn=None):
        print "TODO"
        # self.contactMatrix = pyxlinks.ContactMatrix(pdb_structure, keep_fn=possible_fn)

    def gen_monolinks_possible_in_structure(self, model, possible_fn=None):
        self.possible_monolinks = model.get_monolinks_possible_in_structure(possible_fn=possible_fn)


def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

def is_crosslinkable(resi, biodssp=None, acc_thresh=None):
    if biodssp and acc_thresh:
        raise NotImplementedError
        rel_aa = 0
        return resi.type == 'LYS' and rel_aa > acc_thresh
    else:
        return resi.type == 'LYS'


# The following are re-usable convenience utilities


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


def is_normal_pdb_resi(resi):
    '''Distinguish from rmf resi'''
    return hasattr(resi, 'hasRibbon') and resi.hasRibbon()


def is_satisfied(b, threshold):
    if b:
        return b.length() < threshold


def get_rmf_viewers():
    return [insta for insta in chimera.extension.manager.instances if hasattr(insta, 'rmf')]

def getGroup(groupName):
    mgr = chimera.PseudoBondMgr.mgr()
    group = mgr.findPseudoBondGroup(groupName)
    return group

def hideGroup(groupName):
    group = getGroup(groupName)
    if group:
        group.display = 0
