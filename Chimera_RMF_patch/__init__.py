def open_rmf(fn):
	# Save and restore "didInitialView" state so that even if
	# we open other files, we will update the camera view as necessary.
	import chimera
	if not chimera.nogui:
		from chimera import viewer
		d = viewer.didInitialView
	import os.path
	if os.path.splitext(fn)[1] == ".rmf2info":
		fn = os.path.split(fn)[0]
	models = RMFFile(fn).getModels()
	if not chimera.nogui:
		viewer.didInitialView = d
	return models

def _isinf(v):
	from math import isinf
	try:
		return isinf(v)
	except TypeError:
		# If not floating point, just leave it alone
		return False

class RMFFile:

	def __init__(self, fn):
		#import IMP ; IMP.set_check_level(IMP.NONE)
		import os.path
		if not os.path.exists(fn):
			import chimera
			raise chimera.UserError("no such file: %s" % fn)
		self.filename = fn
		self.name = os.path.basename(fn)
		import RMF
		self.rh = RMF.open_rmf_file_read_only(str(fn))
		self.frameCount = self.rh.get_number_of_frames()
		if self.frameCount <= 0:
			import chimera
			raise chimera.UserError("%s: %d frames of data" %
						(fn, self.frameCount))
		self.setCurrentFrame(0)
		self.componentMap = dict()
		self.rootComponent = None
		self.rootFeature = Feature(self, None)
		self.molecules = list()
		self.geometryModels = dict()
		self.meshModels = dict()
		self.pbg = None
		try:
			self._createModels()
			for m in self.getModels():
				m.name = fn + " - " + m.name
		except IOError, e:
			import sys
			try:
				msg = self.rh.validate()
			except IOError:
				msg = "File validation failed."
			if not msg:
				extra = ""
				from chimera import LimitationError as Error
			else:
				extra = "\n"+msg+"\nYour file appears corrupt."
				from chimera import UserError as Error
			raise Error("%s%s" % (str(e), extra))
		except:
			import traceback, sys
			traceback.print_exc(file=sys.stdout)

	def destroy(self):
		# Clean up references so garbage collection/reference
		# counting will get rid of everything
		self.dialog = None
		self.rootComponent.destroy()
		self.rootFeature.destroy()
		self.alternativesFactory = None
		self.ballFactory = None
		self.cylFactory = None
		self.segFactory = None
		self.colorFactory = None
		self.particleFactory = None
		self.atomFactory = None
		self.residueFactory = None
		self.chainFactory = None
		self.domainFactory = None
		self.ipFactory = None
		self.scoreFactory = None
		self.representationFactory = None
		self.referenceFrameFactory = None
		self.externalFactory = None
		self.bondFactory = None
		self.rh = None
		import chimera
		if self.pbg:
			mgr = chimera.PseudoBondMgr.mgr()
			mgr.deletePseudoBondGroup(self.pbg)
			self.pbg = None
		chimera.openModels.close(self.getModels())
		self.molecules = list()
		self.geometryModels = dict()
		self.meshModels = dict()

	def getModels(self):
		"Return all Chimera models created for RMF file"

		return (self.molecules + self.geometryModels.values()
						+ self.meshModels.values())

	def replaceDialog(self, dialog):
		self.dialog = dialog

	def doubleclick(self, c):
		# Called by components when user doubleclicks on
		# tree element in "Structure" pane
		self.dialog.doubleclick(c)

	def setCurrentFrame(self, frame):
		from RMF import FrameID
		self.rh.set_current_frame(FrameID(frame))

	def getCurrentFrame(self):
		return self.rh.get_current_frame().get_index()

	def getFrameName(self, frame=0):
		self.setCurrentFrame(frame)
		return self.rh.get_name()

	def displayAtResolution(self, frame, resolution):
		self.setCurrentFrame(frame)
		self.rootComponent.displayAtResolution(resolution, self)

	def redisplayFrame(self, frame):
		self.setCurrentFrame(frame)
		self.rootComponent.redisplayFrame(self)

	#
	# Convert RMF file into Chimera models and feature list
	#
	def _createModels(self):
		self._bonds = list()
		self._geomFrameMap = dict()
		self._nodeMap = dict()
		import RMF
		self.alternativesFactory = RMF.AlternativesConstFactory(self.rh)
		self.ballFactory = RMF.BallConstFactory(self.rh)
		self.cylFactory = RMF.CylinderConstFactory(self.rh)
		self.segFactory = RMF.SegmentConstFactory(self.rh)
		self.colorFactory = RMF.ColoredConstFactory(self.rh)
		self.particleFactory = RMF.ParticleConstFactory(self.rh)
		self.atomFactory = RMF.AtomConstFactory(self.rh)
		self.residueFactory = RMF.ResidueConstFactory(self.rh)
		self.chainFactory = RMF.ChainConstFactory(self.rh)
		self.domainFactory = RMF.DomainConstFactory(self.rh)
		self.ipFactory = RMF.IntermediateParticleConstFactory(self.rh)
		self.scoreFactory = RMF.ScoreConstFactory(self.rh)
		self.representationFactory = RMF.RepresentationConstFactory(self.rh)
		self.referenceFrameFactory = RMF.ReferenceFrameConstFactory(self.rh)
		self.externalFactory = RMF.ExternalConstFactory(self.rh)
		self.bondFactory = RMF.BondConstFactory(self.rh)
		self._hasBoundingSphere = False

		#self._listKeys()
		self._processNodes()
		self._postprocess()

		del self._bonds
		del self._geomFrameMap
		del self._nodeMap
		del self._hasBoundingSphere

	#
	# Process RMF nodes depth-first
	#
	def _processNodes(self):
		self._components = [ self.rootComponent ]
		self._features = [ self.rootFeature ]
		self._curChainId = " "
		self._curResidue = None
		self._resolutions = set()
		import RMF
		rf = RMF.CoordinateTransformer()
		self._processNode(self.rh.get_root_node(), 0, rf)

	def getParentChainId(self, c):
	    while hasattr(c, 'parent'):
	        c = c.parent
	        if hasattr(c, 'chainId'):
	            return c.chainId
	#
	# Postprocess what we read in
	#
	def _postprocess(self):
		self.rootComponent.updateReprLeaf()
		from chimera import Coord
		showBounds = not self.molecules
		if self._hasBoundingSphere:
			from chimera import Element, Atom
			m = self._makeNewMolecule("bounds - " + self.name)
			m.isRealMolecule = False
			m.noprefs = True
			# We cannot use coordinate sets because we
			# need to update the radius depending on frame
			LP = Element("LonePair")
			for c in self._nodeMap.itervalues():
				if not c.hasBoundingSphere():
					continue
				xyz, radius = c.getBoundingSphere()
				ccolor = self._getChimeraColor(m, c.getColor())

				chainId = self.getParentChainId(c) or " "
				# print c, dir(c)
				try:
					rPos = int(c.name)
					#print c.name, rPos
				except ValueError:
					rPos = None
				r = self._makeNewResidue(m, c.name, chainId, color=ccolor, rPos=rPos)
				# r = self._makeNewResidue(m, "BSP", color=ccolor)
				a = self._makeNewAtom(m, r, "B", LP, xyz,
					ccolor, Atom.Sphere, radius,
					showBounds)
				c.boundingAtom = a
				c.setFrameUpdate("bounding sphere", a)
				self._resolutions.add(radius * 2)
			self.molecules.append(m)
		self._makeBonds()
		r = list(self._resolutions)
		r.sort()
		self.resolutions = r
		del self._resolutions

		# Set up GUI if necessary
		UIStyle = "viewer"
		self._coordSetsLoaded = False
		import chimera
		if chimera.nogui:
			self.dialog = None
		elif UIStyle == "trajectory":
			self._loadAllCoordSets()
			from gui import RMFTrajDialog as RMFDialog
		elif UIStyle == "viewer":
			from gui import RMFViewerDialog as RMFDialog
		import chimera
		if chimera.nogui:
			self.dialog = None
		else:
			self.dialog = RMFDialog(self)

		# Start monitoring closing of molecules so we
		# drop our references when needed
		self.removeHandlerId = chimera.openModels.addRemoveHandler(
						self._removeModelCB, None)

		# TODO: handle session saving

	#
	# Create bonds between nodes
	#
	def _makeBonds(self):
		from chimera import Bond, connectMolecule
		usedBonds = set()
		for idPair in self._bonds:
			n0id, n1id = idPair
			try:
				c0 = self._nodeMap[n0id]
				c1 = self._nodeMap[n1id]
			except KeyError:
				continue
			try:
				a0 = c0.atom
				a1 = c1.atom
			except AttributeError:
				try:
					a0 = c0.boundingAtom
					a1 = c1.boundingAtom
				except AttributeError:
					continue
			if a0.molecule != a1.molecule:
				print "Skipping intermolecular bond"
				continue
			self._makeNewBond(a0.molecule, a0, a1,
							drawMode=Bond.Stick)
			usedBonds.add(idPair)

		#
		# Report on any unused bonds
		#
		for idPair in self._bonds:
			if idPair not in usedBonds:
				print "Unused bond: (%s, %s)" % idPair

		#
		# Molecules with no bonds are connected using Chimera heuristics
		#
		for m in self.molecules:
			if not m.bonds:
				connectMolecule(m)

	def _loadAllCoordSets(self):
		# Initialize alternate coordinate sets
		if self._coordSetsLoaded:
			return
		molList = self.getModels()
		for frame in range(1, self.frameCount):
			self.loadFrame(frame, molList, True)
		for m in molList:
			m.activeCoordSet = m.findCoordSet(0)
		self._coordSetsLoaded = True

	def loadFrame(self, frame, molList=None, create=False):
		if molList is None:
			molList = self.getModels()
		if not self._coordSetsLoaded:
			if create:
				for m in molList:
					m.activeCoordSet = m.newCoordSet(frame,
								len(m.atoms))
			self.setCurrentFrame(frame)
			import RMF
			rf = RMF.CoordinateTransformer()
			self.rootComponent.setupFrame(frame, self, rf)
		else:
			for m in molList:
				cs = m.findCoordSet(frame)
				if cs:
					m.activeCoordSet = cs

	#
	# Process RMF node and dispatch to handler
	#
	def _processNode(self, node, depth, rf, check_alt=True):
		#print "  " * depth, "process node", node.get_type(), node, node.get_name()
		#self._listValues(node, depth, showMissing=False)
		import RMF
		if check_alt and self.alternativesFactory.get_is(node):
			alt = self.alternativesFactory.get(node)
			#print "  " * (depth + 1), "ALTERNATIVES!", alt.get_alternatives(RMF.PARTICLE)
			for n in alt.get_alternatives(RMF.PARTICLE):
				self._processNode(n, depth + 1, rf,
							check_alt=(n != node))
			return

		node.component = self._pushComponent(node)
		#print "  " * depth, " maps to component", node.component
		if self.referenceFrameFactory.get_is(node):
			rf = RMF.CoordinateTransformer(rf,
					self.referenceFrameFactory.get(node))
			#print "  " * depth, "rigid body", rf
		nodeType = node.get_type()
		if nodeType == RMF.REPRESENTATION:
			# Part of a molecule
			node.component.setIsRepr(True)
			saveChainId = self._curChainId
			self._addMolecule(node, depth, rf)
			self._addGeometry(node, depth, rf)
			for c in node.get_children():
				self._processNode(c, depth + 1, rf)
			self._curChainId = saveChainId
		elif nodeType == RMF.BOND:
			# Geometric object
			self._addBond(node, depth, rf)
		elif nodeType == RMF.GEOMETRY:
			# Geometric object
			self._addGeometry(node, depth, rf)
			for c in node.get_children():
				self._processNode(c, depth + 1, rf)
		elif nodeType == RMF.FEATURE:
			# Feature of the system
			self._addFeature(node, depth, rf)
			node.component.setShowInGUI(False)
		elif nodeType == RMF.ALIAS:
			for n in node.get_children():
				self._processNode(n, depth + 1, rf)
		elif nodeType == RMF.ROOT:	# Root node
			for n in node.get_children():
				self._processNode(n, depth + 1, rf)
		elif nodeType == RMF.ORGANIZATIONAL:
			for n in node.get_children():
				self._processNode(n, depth + 1, rf)
		else:
			# CUSTOM or unrecognized
			print "ignored", node.get_type(), node, node.get_name()
			pass
		del node.component
		self._popComponent()

	def _addMolecule(self, node, depth, rf):
		#print "  " * depth, "_addMolecule", node.get_type(), node, node.get_name()
		c = node.component
		c.setIsMolecule(True)
		color = c.color
		nodeName = node.get_name()
		if self.atomFactory.get_is(node):
			#c.setIsMolecule(True)
			from chimera import Coord
			atom = self.atomFactory.get(node)
			m = c.getMolecule(True, self.molecules)
			ccolor = self._getChimeraColor(m, color)
			if not self._curResidue:
				self._curResidue = self._makeNewResidue(m,
							"UNK", color=ccolor)
			from chimera import Atom, Element
			element = Element(atom.get_element())
			radius = atom.get_radius()
			mass = atom.get_mass()
			particle = self.particleFactory.get(node)
			xyz = Coord(*rf.get_global_coordinates(
						particle.get_coordinates()))
			a = self._makeNewAtom(m, self._curResidue, nodeName,
						element, xyz, ccolor,
						Atom.Dot, radius, True)
			self._nodeMap[node.get_id()] = c
			c.atom = a
			c.setFrameUpdate("atom", a)
		elif self.chainFactory.get_is(node):
			#c.setIsMolecule(True)
			chain = self.chainFactory.get(node)
			self._curChainId = chain.get_chain_id()
			c.chainId = self._curChainId
			self._nodeMap[node.get_id()] = c
			self._setBoundingSphere(node, c, rf)
		elif self.residueFactory.get_is(node):
			#c.setIsMolecule(True)
			residue = self.residueFactory.get(node)
			m = c.getMolecule(True, self.molecules)
			ccolor = self._getChimeraColor(m, color)
			rType = residue.get_residue_type()
			pos = residue.get_residue_index()
			self._curResidue = self._makeNewResidue(m, rType,
							self._curChainId,
							pos, '', color=ccolor)
			c.residue = self._curResidue
			self._nodeMap[node.get_id()] = c
			self._setBoundingSphere(node, c, rf)
		elif self.domainFactory.get_is(node):
			#c.setIsMolecule(True)
			domain = self.domainFactory.get(node)
			self._nodeMap[node.get_id()] = c
			self._setBoundingSphere(node, c, rf)
			c.domain = domain.get_residue_indexes()
		elif self.externalFactory.get_is(node):
			ed = self.externalFactory.get(node)
			path = ed.get_path()
			# Assume that path is absolute and reference PDB file
			# TODO: Instead of opening model multiple times,
			# use references to first opened model
			import chimera
			mList = chimera.openModels.open(path, type="PDB",
							checkForChanges=False)
			from chimera import Xform
			xf = Xform.translation(*rf.get_translation())
			xf.multiply(Xform.quaternion(*rf.get_rotation()))
			if len(mList) > 1:
				openStates = set([ m.openState for m in mList ])
			else:
				openStates = [ m.openState for m in mList ]
			for openState in openStates:
				openState.xform = xf
			import weakref
			c.moleculesData = [ xf, weakref.WeakSet(mList) ]
			c.setFrameUpdate("molecules", c.moleculesData)
		else:
			#print "  " * depth, "unknown molecule type"
			# Molecule or group
			self._curResidue = None
			self._nodeMap[node.get_id()] = c
			self._setBoundingSphere(node, c, rf)

	def _setBoundingSphere(self, node, c, rf):
		if self.ipFactory.get_is(node):
			from chimera import Coord
			ip = self.ipFactory.get(node)
			xyz = Coord(*rf.get_global_coordinates(
						ip.get_coordinates()))
			radius = ip.get_radius()
			if c.setBoundingSphere(xyz, radius):
				self._hasBoundingSphere = True

	def _addBond(self, node, depth, rf):
		#print "_addBond", node.get_type(), node, node.get_name()
		#self._listValues(node, depth)
		if not self.bondFactory.get_is(node):
			return
		bond = self.bondFactory.get(node)
		self._bonds.append((bond.get_bonded_0().get_id(),
					bond.get_bonded_1().get_id()))

	def _addGeometry(self, node, depth, rf):
		#print "  " * depth, "_addGeometry", node.get_type(), node, node.get_name()
		#self._listValues(node, depth)
		# Process ordering is important because Cylinders are
		# also Segments
		if self.ballFactory.get_is(node):
			#print "sphere"
			self._addSphere(node, rf)
		elif self.cylFactory.get_is(node):
			#print "cylinder"
			self._addCylinder(node, rf)
		elif self.segFactory.get_is(node):
			#print "segment"
			self._addSegment(node, rf)
		else:
			#print "unknown geometry"
			#print "  " * depth, "unknown geometry"
			pass

	def _addFeature(self, node, depth, rf):
		#print "_addFeature", node.get_type(), node, node.get_name()
		#if not hasattr(self, "shownComponentMap"):
		#	import pprint
		#	pprint.pprint(self.componentMap)
		#	self.shownComponentMap = True
		f = self._pushFeature(node)
		from RMF import ALIAS
		for n in node.get_children():
			if n.get_type() != ALIAS:
				self._processNode(n, depth + 1, rf)
		self._popFeature()

	#
	# Add RMF geometry nodes into Chimera geometry or mesh models
	#
	def _addCylinder(self, node, rf):
		cyl = self.cylFactory.get(node)
		coords = cyl.get_coordinates_list()
		radius = cyl.get_radius()
		c = node.component
		color = c.color
		b = self._addLink(node, coords, radius, color, rf)
		if b:
			c.geomBond = b
			c.setFrameUpdate("cylinder", b)

	def _addSegment(self, node, rf):
		seg = self.segFactory.get(node)
		coords = seg.get_coordinates_list()
		c = node.component
		color = c.color
		b = self._addLink(node, coords, None, color, rf)
		if b:
			c.geomBond = b
			c.setFrameUpdate("segment", b)

	def _addLink(self, node, coords, radius, color, rf):
		if len(coords) != 2:
			return None
		if _isinf(radius):
			radius = None
		from chimera import Element, Atom, Bond, Coord
		if radius is None:
			mode = Bond.Wire
		else:
			mode = Bond.Stick
		start = Coord(*rf.get_global_coordinates(coords[0]))
		end = Coord(*rf.get_global_coordinates(coords[1]))
		m = self._getGeometryModel()
		ccolor = self._getChimeraColor(m, color)
		r = self._makeNewResidue(m, "CYL", color=ccolor)
		LP = Element("LonePair")
		a1 = self._makeNewAtom(m, r, "C1", LP, start,
					ccolor, Atom.Dot, radius, False)
		a2 = self._makeNewAtom(m, r, "C2", LP, end,
					ccolor, Atom.Dot, radius, False)
		b = self._makeNewBond(m, a1, a2, ccolor, mode,
					radius, Bond.Always, False)
		return b

	def _addSphere(self, node, rf):
		sph = self.ballFactory.get(node)
		radius = sph.get_radius()
		from chimera import Coord
		center = Coord(*rf.get_global_coordinates(
						sph.get_coordinates()))
		m = self._getGeometryModel()
		c = node.component
		color = c.color
		ccolor = self._getChimeraColor(m, color)
		r = self._makeNewResidue(m, "SPH", color=ccolor)
		from chimera import Element, Atom
		LP = Element("LonePair")
		a = self._makeNewAtom(m, r, "S", LP, center,
					ccolor, Atom.Sphere, radius, True)
		c.geomAtom = a
		c.setFrameUpdate("sphere", a)

	def _makeNewMolecule(self, name):
		from chimera import Molecule
		m = Molecule()
		m.name = name
		m.colorCache = dict()
		# Keep a weak reference so that others
		# (in particular rmfalias command) can
		# find RMFFile instance from Molecule
		import weakref
		m.rmf = weakref.ref(self)
		return m

	def _makeNewResidue(self, m, rType,
				chainId=" ", rPos=None, insertCode='',
				color=None):
		if not chainId.isalnum():
			chainId = " "
		if rPos is None:
			rPos = len(m.residues)
		r = m.newResidue(rType, chainId, rPos, insertCode)
		if color is not None:
			r.ribbonColor = color
		return r

	def _makeNewAtom(self, m, r, name, element, coord, color,
				drawMode, radius, display):
		a = m.newAtom(name, element)
		if coord is not None:
			a.setCoord(coord)
		if color is not None:
			a.color = color
		if drawMode is not None:
			a.drawMode = drawMode
		if radius is not None:
			a.radius = radius
			self._resolutions.add(radius * 2)
		if display is not None:
			a.display = display
		r.addAtom(a)
		return a

	def _makeNewBond(self, m, a1, a2, color=None, drawMode=None,
				radius=None, display=None, halfbond=None):
		b = m.newBond(a1, a2)
		if color is not None:
			b.color = color
		if drawMode is not None:
			b.drawMode = drawMode
		if radius is not None:
			b.radius = radius
		if display is not None:
			b.display = display
		if halfbond is not None:
			b.halfbond = halfbond
		return b

	#
	# Routines for handling components stack
	#
	def _currentComponent(self):
		return self._components[-1]

	def _pushComponent(self, node):
		#name = "%s {%s}" % (node.get_name(), node.get_id())
		if self.rootComponent is None:
			name = self.name
		else:
			name = node.get_name()
		color = self._getRGBColor(node)
		c = Component(self, name, self._components[-1],
					isMolecule=False, color=color)
		self._components.append(c)
		if self.rootComponent is None:
			self.rootComponent = c
		nodeId = node.get_id()
		self.componentMap[nodeId] = c
		self.componentMap[c] = nodeId
		return c

	def _popComponent(self):
		return self._components.pop()

	def getComponentNode(self, c):
		try:
			nodeId = self.componentMap[c]
		except KeyError:
			return None
		return self.rh.get_node(nodeId)

	#
	# Routines for handling feature stack
	#
	def _currentFeature(self):
		return self._features[-1]

	def _pushFeature(self, node):
		f = Feature(self, node, self._features[-1])
		self._features.append(f)
		return f

	def _popFeature(self):
		return self._features.pop()

	#
	# Get geometry or mesh model for the current molecule
	#
	def _getGeometryModel(self):
		curMol = self._currentComponent().getMolecule(False)
		try:
			return self.geometryModels[curMol]
		except KeyError:
			m = self._makeNewMolecule("geometry - " + self.name)
			m.isRealMolecule = False
			m.noprefs = True
			self.geometryModels[curMol] = m
			return m

	def _getMeshModel(self):
		curMol = self._currentComponent().getMolecule(False)
		try:
			return self.meshModels[curMol]
		except KeyError:
			from _surface import SurfaceModel
			m = SurfaceModel()
			self.meshModels[curMol] = m
			return m

	#
	# Get RGB color from an RMF node
	#
	def _getRGBColor(self, node, defaultColor=None):
		if not self.colorFactory.get_is(node):
			return defaultColor
		return tuple(self.colorFactory.get(node).get_rgb_color())

	def _getChimeraColor(self, m, rgb):
		if rgb is None or _isinf(rgb[0]):
			return None
		try:
			return m.colorCache[rgb]
		except KeyError:
			from chimera import MaterialColor
			c = MaterialColor(*rgb)
			m.colorCache[rgb] = c
			return c

	def _getFloatValue(self, node, key, defaultValue=None):
		value = node.get_value_always(key)
		if value is None:
			return defaultValue
		else:
			return value

	def _getStringValue(self, node, key, defaultValue=None):
		from RMF import NullString
		value = node.get_value_always(key)
		if value == NullString:
			return defaultValue
		else:
			return value

	#
	# Debugging routines for dumping keys and values
	#
	def _listValues(self, node, depth, showMissing=True):
		self._getAllKeys()
		for k in self._allKeys:
			c = self.rh.get_category(k)
			cname = self.rh.get_name(c)
			kname = self.rh.get_name(k)
			if node.get_has_value(k):
				value = node.get_value(k)
			elif not showMissing:
				continue
			else:
				value = "no data"
			print "  " * (depth + 1), cname, kname, value

	def _listKeys(self):
		self._getAllKeys()
		for k in self._allKeys:
			c = self.rh.get_category(k)
			cname = self.rh.get_name(c)
			kname = self.rh.get_name(k)
			print "key", cname, kname
			print "  is_per_frame:", self.rh.get_is_per_frame(k)
			if self.rh.get_is_per_frame(k):
				print "  number_of_frames:", \
						self.rh.get_number_of_frames(k)

	def _getAllKeys(self):
		if hasattr(self, "_allKeys"):
			return
		self._allKeys = list()
		for c in self.rh.get_categories():
			self._allKeys.extend(self.rh.get_keys(c))

	#
	# Routine for tracking PseudoBondGroup for this RMF instance
	#

	def getPBG(self):
		if not self.pbg:
			import chimera
			mgr = chimera.PseudoBondMgr.mgr()
			basename = "Restraints - %s" % self.filename
			name = basename
			i = 2
			while mgr.findPseudoBondGroup(name):
				name = "%s (%d)" % (basename, i)
				i += 1
			self.pbg = mgr.newPseudoBondGroup(name)
			chimera.openModels.add([ self.pbg ], hidden=True)
			#self.pbg.lineType = 2	# Dashed lines
		return self.pbg

	#
	# Clean up routine called when a model is closed
	#
	def _removeModelCB(self, trigger, data, models):
		invMeshModels = dict([ (v, k)
				for k, v in self.meshModels.iteritems() ])
		invGeometryModels = dict([ (v, k)
				for k, v in self.geometryModels.iteritems() ])
		removedMolecules = set()
		for m in models:
			if m in self.molecules:
				removedMolecules.add(m)
			else:
				mol = invGeometryModels.get(m, None)
				if mol:
					self._removeGeometryModel(m, mol)
				mol = invMeshModels.get(m, None)
				if mol:
					self._removeMeshModel(m, mol)
		if removedMolecules:
			self._removeMolecule(removedMolecules)
		if not self.getModels() and self.dialog:
			self.dialog.destroy()
			self.dialog = None

	def _removeMolecule(self, removedMolecules):
		for m in removedMolecules:
			geomModel = self.geometryModels.get(m, None)
			if geomModel:
				self._removeGeometryModel(geomModel, m)
			meshModel = self.meshModels.get(m, None)
			if meshModel:
				self._removeMeshModel(meshModel, m)
		for c in self.componentMap.itervalues():
			try:
				a = c.atom
			except AttributeError:
				pass
			else:
				if a.molecule in removedMolecules:
					del c.atom
			try:
				r = c.residue
			except AttributeError:
				pass
			else:
				if r.molecule in removedMolecules:
					del c.residue
		self.molecules = list(set(self.molecules) - removedMolecules)

	def _removeGeometryModel(self, m, mol):
		del self.geometryModels[mol]

	def _removeMeshModel(self, m, mol):
		del self.meshModels[mol]

	#
	# Routine for fetching all scores for all given features
	#
	def getAllScores(self, master, features):
		scoreFactory = self.scoreFactory
		currentFrame = self.getCurrentFrame()
		import numpy
		scores = numpy.empty((len(features), self.frameCount))
		scores[:] = numpy.NAN
		needProgressBar = self.frameCount > 20
		if needProgressBar:
			from CGLtk.PmwProgressBarDialog import ProgressBarDialog
			d = ProgressBarDialog(master, title="Loading Scores...",
								buttons=())
			d.transient(master)
			d.focus()
		for frame in range(self.frameCount):
			if needProgressBar:
				progress = float(frame) / self.frameCount
				d.updatebarlength(progress)
			self.setCurrentFrame(frame)
			for i, f in enumerate(features):
				if f.node is None:
					continue
				if not scoreFactory.get_is(f.node):
					continue
				score = scoreFactory.get(f.node)
				try:
					s = score.get_frame_score()
				except IOError:
					pass
				else:
					scores[i, frame] = s
		if needProgressBar:
			d.destroy()
		self.setCurrentFrame(currentFrame)
		return scores

from chimera.TreeWidget import TreeItem
class Component(TreeItem):
	"""Component represents an RMF particle which may map to a hierarchy
	of Chimera molecules or graphics objects"""

	def __init__(self, rmf, name, parent=None,
					isMolecule=False, color=None):
		self.rmf = rmf
		self.name = name
		self.parent = parent
		self.molecule = None
		self.amMolecule = isMolecule
		self.color = color
		self.components = list()
		self.bounds = None
		self.frameUpdate = None
		self.frameSetup = None
		self.showInGUI = True
		self.amRepr = False
		self.amReprLeaf = False
		if self.parent:
			self.molecule = parent.molecule
			self.parent.addComponent(self)

	def destroy(self):
		# Clean up references so garbage collection/reference
		# counting will get rid of everything
		self.rmf = None
		self.parent = None
		self.molecule = None
		for c in self.components:
			c.destroy()

	def addComponent(self, c):
		self.components.append(c)

	def isMolecule(self):
		return self.amMolecule

	def setIsMolecule(self, b):
		self.amMolecule = b

	def isRepr(self, b):
		return self.amRepr

	def setIsRepr(self, b):
		self.amRepr = b

	def isReprLeaf(self):
		return self.amReprLeaf

	def setShowInGUI(self, b):
		self.showInGUI = b

	def updateReprLeaf(self):
		hasReprLeaf = False
		for c in self.components:
			if c.updateReprLeaf():
				hasReprLeaf = True
		if hasReprLeaf:
			self.amReprLeaf = False
			return True
		elif self.amRepr:
			self.amReprLeaf = True
			return True
		else:
			return False

	def getMolecule(self, create, molList=None):
		# If we have a molecule, return it
		if self.molecule:
			return self.molecule
		# If any of our ancestors has a molecule, return it
		if self.parent:
			m = self.parent.getMolecule(False)
			if m:
				return m
		# If we're not supposed to create it, don't
		if not create:
			return None
		# Find the oldest ancestor that is marked as a molecule
		# and create a Chimera molecule instance there
		self.amMolecule = True
		s = self
		p = self.parent
		while p is not None and p.amMolecule:
			s = p
			p = p.parent
		m = self.rmf._makeNewMolecule(self.name)
		m.activeCoordSet = m.newCoordSet(0)
		s.molecule = m
		ns = self
		while ns is not s:
			ns.molecule = m
			ns = ns.parent
		if molList is not None:
			molList.append(m)
		return m

	def getLabel(self):
		import chimera
		if hasattr(self, "atom"):
			return self.atom.oslIdent(chimera.SelAtom)
		elif hasattr(self, "residue"):
			return self.residue.oslIdent(chimera.SelResidue)
		elif hasattr(self, "chainId"):
			return "Chain %s" % self.chainId
		elif hasattr(self, "domain"):
			return "Domain [%s,%s]" % self.domain
		else:
			return self.name

	def setColor(self, color):
		self.color = color

	def getColor(self):
		if self.color is not None:
			return self.color
		if self.parent is None:
			return None
		return self.parent.getColor()

	def setBoundingSphere(self, xyz, radius, frame=0):
		if xyz and radius:
			if self.bounds is None:
				self.bounds = dict()
			self.bounds[frame] = (xyz, radius)
			return True
		return False

	def hasBoundingSphere(self):
		return self.bounds is not None

	def getBoundingSphere(self, frame=0):
		if self.bounds is None:
			return None
		return self.bounds.get(frame, None)

	# These methods are called by the GUI
	SelectableLeafAttributes = [ "atom", "geomAtom" ]
	def addChimeraObjects(self, sel, depth=0):
		#print " " * depth, "component.addChimeraObjects", self.name
		for attrName in self.SelectableLeafAttributes:
			if hasattr(self, attrName):
				#print " " * depth, "add", attrName
				sel.add(getattr(self, attrName))
				return
		if hasattr(self, "geomBond"):
			#print " " * depth, "add geomBond"
			b = self.geomBond
			sel.add(b)
			for a in b.atoms:
				sel.add(a)
			return
		else:
			added = False
			for c in self.components:
				if c.addChimeraObjects(sel, depth + 1):
					added = True
			if not added and hasattr(self, "boundingAtom"):
				#print " " * depth, "add boundingAtom"
				sel.add(self.boundingAtom)
				added = True
			return added

	def displayAtResolution(self, resolution, rmf):
		if self.hasBoundingSphere():
			node = rmf.getComponentNode(self)
			ip = rmf.ipFactory.get(node)
			radius = ip.get_radius()
			if radius * 2 <= resolution:
				self.showGraphics(True, hideChildren=True)
			elif self.components:
				self.showGraphics(self.isReprLeaf(),
							hideChildren=False)
				for c in self.components:
					c.displayAtResolution(resolution, rmf)
			else:
				self.showGraphics(True, hideChildren=False)
			self.boundingAtom.radius = radius
		else:
			self.showGraphics(True, hideChildren=False)
			for c in self.components:
				c.displayAtResolution(resolution, rmf)

	def redisplayFrame(self, rmf):
		if self.frameUpdate:
			self.frameUpdate(rmf, self.frameUpdateData)
		for c in self.components:
			c.redisplayFrame(rmf)

	def setupFrame(self, frame, rmf, rf):
		node = rmf.getComponentNode(self)
		if rmf.referenceFrameFactory.get_is(node):
			import RMF
			rf = RMF.CoordinateTransformer(rf,
					rmf.referenceFrameFactory.get(node))
		if self.frameSetup:
			self.frameSetup(rmf, self.frameUpdateData, rf)
		for c in self.components:
			c.setupFrame(frame, rmf, rf)

	# These methods are functions for showing and hiding bounding spheres

	def getAtom(self):
		try:
			a = self.atom
		except AttributeError:
			try:
				a = self.boundingAtom
			except AttributeError:
				a = None
		return a

	def showGraphics(self, b, hideChildren=True):
		a = self.getAtom()
		ga = getattr(self, "geomAtom", None)
		gb = getattr(self, "geomBond", None)
		if a or ga or gb:
			if a:
				a.display = b
			if ga:
				ga.display = b
			if gb:
				gb.display = b
				for gba in gb.atoms:
					gba.display = b
			if hideChildren:
				self.hideChildren(False)
		else:
			if hideChildren:
				self.hideChildren(b)

	def hideChildren(self, show):
		# If "show" is True, make the first item we encounter
		# that has graphics representation displayed
		for c in self.components:
			c.showGraphics(show)

	def isShown(self):
		a = self._getAtom()
		if not a:
			return None
		else:
			return a.display

	# These methods are functions for redisplaying on frame changes

	def _redisplayAtom(self, rmf, a):
		node = rmf.getComponentNode(self)
		ip = rmf.ipFactory.get(node)
		a.radius = ip.get_radius()

	def _setupAtom(self, rmf, a, rf):
		from chimera import Coord
		node = rmf.getComponentNode(self)
		ip = rmf.ipFactory.get(node)
		a.setCoord(Coord(*rf.get_global_coordinates(
						ip.get_coordinates())))

	def _redisplaySphere(self, rmf, a):
		node = rmf.getComponentNode(self)
		if rmf.ballFactory.get_is(node):
			sph = rmf.ballFactory.get(node)
			a.radius = sph.get_radius()
		else:
			a.display = False

	def _setupSphere(self, rmf, a, rf):
		node = rmf.getComponentNode(self)
		if rmf.ballFactory.get_is(node):
			sph = rmf.ballFactory.get(node)
			from chimera import Coord
			xyz = Coord(*rf.get_global_coordinates(
						sph.get_coordinates()))
			a.setCoord(xyz)
		else:
			cs = a.molecule.findCoordSet(0)
			a.setCoord(a.coord(cs))

	def _redisplayCylinder(self, rmf, b):
		node = rmf.getComponentNode(self)
		if rmf.cylFactory.get_is(node):
			cyl = rmf.cylFactory.get(node)
			b.radius = cyl.get_radius()
		else:
			from chimera import Bond
			b.display = Bond.Never
			for a in b.atoms:
				a.display = False

	def _setupCylinder(self, rmf, b, rf):
		node = rmf.getComponentNode(self)
		a1, a2 = b.atoms
		if rmf.cylFactory.get_is(node):
			cyl = rmf.cylFactory.get(node)
			coords = cyl.get_coordinates_list()
			from chimera import Coord
			ggc = rf.get_global_coordinates
			a1.setCoord(Coord(*ggc(coords[0])))
			a2.setCoord(Coord(*ggc(coords[1])))
		else:
			cs = a1.molecule.findCoordSet(0)
			a1.setCoord(a1.coord(cs))
			a2.setCoord(a2.coord(cs))

	def _redisplaySegment(self, rmf, b):
		node = rmf.getComponentNode(self)
		if not rmf.segFactory.get_is(node):
			from chimera import Bond
			b.display = Bond.Never
			for a in b.atoms:
				a.display = False

	def _setupSegment(self, rmf, b, rf):
		node = rmf.getComponentNode(self)
		a1, a2 = b.atoms
		if rmf.segFactory.get_is(node):
			seg = rmf.segFactory.get(node)
			coords = seg.get_coordinates_list()
			from chimera import Coord
			ggc = rf.get_global_coordinates
			a1.setCoord(Coord(*ggc(coords[0])))
			a2.setCoord(Coord(*ggc(coords[1])))
		else:
			cs = a1.molecule.findCoordSet(0)
			a1.setCoord(a1.coord(cs))
			a2.setCoord(a2.coord(cs))

	def _redisplayMolecules(self, rmf, m):
		return

	def _setupMolecules(self, rmf, moleculesData, rf):
		oldXf, mList = moleculesData
		from chimera import Xform
		newXf = Xform.translation(*rf.get_translation())
		newXf.multiply(Xform.quaternion(*rf.get_rotation()))
		# If there are multiple models, they may well share
		# the same openState instance and we only need to
		# update it once
		if len(mList) > 1:
			openStates = set([ m.openState for m in mList ])
		else:
			openStates = [ m.openState for m in mList ]
		for openState in openStates:
			xf = openState.xform
			xf.multiply(oldXf.inverse())
			xf.multiply(newXf)
			openState.xform = xf
		moleculesData[0] = newXf
		# Make sure distances are updated
		import chimera
		if not chimera.nogui:
			from StructMeasure.DistMonitor import updateDistance
			updateDistance()

	def setFrameUpdate(self, updateType, data):
		if updateType == "atom":
			# Atom radii _should_ not change
			#self.frameUpdate = self._redisplayAtom
			self.frameSetup = self._setupAtom
		elif updateType == "bounding sphere":
			self.frameUpdate = self._redisplayAtom
			self.frameSetup = self._setupAtom
		elif updateType == "sphere":
			self.frameUpdate = self._redisplaySphere
			self.frameSetup = self._setupSphere
		elif updateType == "cylinder":
			self.frameUpdate = self._redisplayCylinder
			self.frameSetup = self._setupCylinder
		elif updateType == "segment":
			self.frameUpdate = self._redisplaySegment
			self.frameSetup = self._setupSegment
		elif updateType == "molecules":
			self.frameUpdate = self._redisplayMolecules
			self.frameSetup = self._setupMolecules
		else:
			print "Unknown update type: %s" % updateType
			return
		self.frameUpdateData = data


class Feature:
	"""Feature represents an RMF feature which may map to a hierarchy
	of restraints"""

	def __init__(self, rmf, node, parent=None):
		self.rmf = rmf
		self.node = node
		if not node:
			self.name = rmf.name
		else:
			self.name = node.get_name()
		self.parent = parent
		self.features = list()
		self._selection = None
		self._pbList = None
		if self.parent:
			self.parent.addFeature(self)

	def destroy(self):
		# Clean up references so garbage collection/reference
		# counting will get rid of everything
		self.rmf = None
		self.node = None
		self.parent = None
		self._pbList = None
		for f in self.features:
			f.destroy()

	def getScore(self):
		if self.node is None:
			raise KeyError("no score for frame")
		scoreFactory = self.rmf.scoreFactory
		if scoreFactory.get_is(self.node):
			return self.rmf.scoreFactory.get(self.node).get_score()
		else:
			raise KeyError("no score for frame")

	def addFeature(self, f):
		self.features.append(f)

	def addChimeraObjects(self, sel):
		for c in self._getComponentList():
			c.addChimeraObjects(sel)

	def _getComponentList(self):
		# No score, no components
		cList = list()
		if self.node is None:
			return cList
		representationFactory = self.rmf.representationFactory
		if representationFactory.get_is(self.node):
			score = representationFactory.get(self.node)
		else:
			return cList
		from RMF import NodeID
		representation = score.get_representation()
		for node in representation:
			try:
				c = self.rmf.componentMap[node.get_id()]
			except KeyError:
				#print "No id", nodeId
				pass
			else:
				cList.append(c)
		return cList

	def _showGraphics(self):
		# Construct pseudobonds between all component pairs
		cList = self._getComponentList()
		if not cList or len(cList) > 5:
			self._hideGraphics()
			return
		pbList = list()
		from chimera import MaterialColor, Bond
		c = MaterialColor(0.8, 0.8, 0.8)
		for i, ci in enumerate(cList):
			ai = ci.getAtom()
			if not ai:
				continue
			for cj in cList[i + 1:]:
				aj = cj.getAtom()
				if not aj:
					continue
				pbg = self.rmf.getPBG()
				pb = pbg.newPseudoBond(ai, aj)
				# TODO: calculate color based on
				# restraint satisfaction
				#pb.color = c
				#pb.radius = 1.0
				pb.drawMode = Bond.Spring
				pb.display = Bond.Always
				pb.halfbond = False
				pbList.append(pb)
		self._pbList = pbList

	def _hideGraphics(self):
		if self._pbList:
			pbg = self.rmf.getPBG()
			for pb in self._pbList:
				pbg.deletePseudoBond(pb)
			self._pbList = None

	def showLeaves(self, show):
		if self.features:
			for f in self.features:
				f.showLeaves(show)
		else:
			if show:
				self._showGraphics()
			else:
				self._hideGraphics()


if __name__ == "__main__" or __name__ == "chimeraOpenSandbox":
	print RMFFile("rnapii.rmf")
	#print RMFFile("geometry.rmf")
