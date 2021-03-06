import json
import os
from copy import deepcopy
from collections import deque, defaultdict
from weakref import WeakSet
import itertools
import re


import chimera
import tkFileDialog
import pyxlinks
from os.path import relpath, normpath, dirname, commonprefix
from chimera import MaterialColor
from MultAlignViewer.parsers import readFASTA
from pyxlinks import XlinksSet
import tkMessageBox

import xlinkanalyzer
from xlinkanalyzer import minify_json
from xlinkanalyzer import getConfig
from xlinkanalyzer import utils as xutils

def samefileCrossplatform(file1, file2):
    try:
        from os.path import samefile
    except ImportError:
        return os.stat(file1) == os.stat(file2)
    else:
        return samefile(file1, file2)

class Item(object):
    """
    The Base Item class. Derive Components, DataItems, Complex Data Structures from this class.
    Properties: 
    Type: XLA Item Type
    Config: the current configuration, instance of the assembly class
    Fake: True if the Item is not used for representation of a real data item, e.g. for the Active ItemFrame in the ItemList
    show,active,sym: Flags for chimera
    SHOW: properties to be interpreted and view by the ItemFrame
    """
    SHOW = ["name"]
    OMIT = ["config","fake","_active","_show","_sym","defaults"]
    _show = True
    _active = True
    _sym = True
    def __init__(self,name="",config=None,fake=False,*args,**kwargs):
        self.type = "item"
        self.name = name
        self.config = config
        self.fake = fake
    
    @property
    def sym(self):
        return self._active

    @sym.setter
    def sym(self, val):
        self._sym = val
    
    @property
    def show(self):
        return self._show

    @show.setter
    def show(self, val):
        self._show = val
        chimera.triggers.activateTrigger('component shown/hidden', self)

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, val):
        self._active = val

    def __getitem__(self,slice):
        return self.__dict__

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name

    def serialize(self):
        '''
        Save the defining parameters of this object in a dict
        ''' 
        return dict([(k,v) for k,v in self.__dict__.items() if not k in Item.OMIT])

    def deserialize(self,_dict):
        """
        Set the object properties to the pairs values of the dict
        """
        for key,value in _dict.items():
            if key == "domains" and _dict[key] is None: #TODO: this is temporal
                self.__setattr__(key,[])
            else:
                self.__setattr__(key,value)

    def validate(self):
        """
        check a few basic properties. this is to be implemented for all derived classes
        """
        return True if type(self.name) == str and len(self.name) > 0 else False

    def convert(self,_input):
        """
        Encodes Unicode, List and Dict instances to utf-8
        """
        if isinstance(_input, dict):
            return dict([(self.convert(key), self.convert(value)) \
                        for key, value in _input.iteritems()])
        elif isinstance(_input, list):
            return [self.convert(element) for element in _input]
        elif isinstance(_input, unicode):
            return _input.encode('utf-8')
        else:
            return _input
    
    def getAllInstances(self,_class=None):
        if _class is None:
            return self.config.getInstances(self.__class__)
        else:
            return self.config.getInstances(_class)
    
class Chain(Item):
    """
    Symbolizes a molecular chain
    """
    def __init__(self,_id,item,*args,**kwargs):
        super(Chain,self).__init__(self,*args,**kwargs)
        self.id = _id
        self.item = item
        self.name = item.name + " - Chain: " + _id
        self.color = self.item.color

        self.setSelection(':.'+_id)


    @Item.active.setter
    def active(self, val):
        self._active = val
        if hasattr(self.item, 'domains'):
            for dom in self.item.domains:
                for chain in dom.getChains():
                    if chain.id == self.id:
                        chain.active = val

    @Item.show.setter
    def show(self, val):
        if hasattr(self.item, 'domains'):
            for dom in self.item.domains:
                for chain in dom.getChains():
                    if chain.id == self.id:
                        chain._show = val # _show to not to activate children's triggers
        Item.show.fset(self, val)



    def setSelection(self,sel):
        self.selection = sel

    def getSelection(self):
        return self.selection

class Subunit(Item):
    SHOW = ["name","chainIds","color"]
    OMIT = ["sequence","type","chains","subunitToChain","chainToSubunit"]
    def __init__(self,*args,**kwargs):
        super(Subunit,self).__init__(*args,**kwargs)
        self.type = "subunit"
        self.color = MaterialColor(*[1.0,1.0,1.0,0.0])
        self.chainIds = []
        self.selection = ""
        self.chainToSubunit = {}
        self.subunitToChain = {}
        self.domains = []
        self.chains = []
        self.info = {}

    @Item.show.getter
    def show(self):
        self._show = all([item.show for item in self.getChains()])
        return self._show

    @show.setter
    def show(self, val):
        chimera.triggers.blockTrigger('component shown/hidden')
        for child in self.getChains():
            child.show = val # do show by activating children's (chains) triggers
        for child in self.domains:
            child._show = val # do not activate domains triggers

        self._show = val # do not call Item setter, to not to call the trigger
        chimera.triggers.releaseTrigger('component shown/hidden')

    @Item.active.getter
    def active(self):
        self._active = all([item.active for item in self.getChains()])
        return self._active

    @active.setter
    def active(self, val):
        self._active = val
        for child in self.getChildren():
            child.active = val

    def getChains(self):
        if not self.chains:
            self.chains = [Chain(c,self,config=self.config) for c in self.chainIds]
        return self.chains

    def setColor(self,colorCfg):
        color = chimera.MaterialColor(*[0.0]*4)
        if isinstance(colorCfg, basestring):
            color = chimera.colorTable.getColorByName(colorCfg)
        elif isinstance(colorCfg, tuple) or isinstance(colorCfg, list):
            color = chimera.MaterialColor(*[x for x in colorCfg])
        else:
            color = colorCfg
        self.color = color

    def setChainIds(self,ids):
        self.chainIds = ids
        self.chains = [Chain(c,self,config=self.config) for c in self.chainIds]

    def addChain(self, chainId):
        if chainId not in self.chainIds:
            self.chainIds.append(chainId)
            self.chains.append(Chain(chainId,self,config=self.config))
            self.setSelection()

    def setSelection(self,sel=None):
        if sel is None:
            sel = self.createSubunitSelectionFromChains()
        self.selection = sel

    def getSelection(self):
        return self.createSubunitSelectionFromChains()

    def getSelectionsByChain(self):
        '''Return {chain_id: selection} object for use in selecting subset of chains.'''
        out = defaultdict(list)
        for chainId in self.chainIds:
            out[chainId].append([':.{0}'.format(chainId)])

        return out

    def createSubunitSelectionFromChains(self, chainIds = None):
        if chainIds is None:
            chainIds = self.chainIds
        return ':'+','.join(['.'+s for s in chainIds])

    def serialize(self):
        _dict = super(Subunit,self).serialize()
        _dict = dict([(k,v) for k,v in _dict.items() if not k in Subunit.OMIT])
        _dict["color"] = self.color.rgba()
        _dict["domains"] = [d.serialize() for d in self.domains]
        return _dict

    def deserialize(self,_dict):
        if type(_dict["color"]) == list:
            self.color = chimera.MaterialColor(*_dict["color"])
            _dict.pop("color")
        if "domains" in _dict:
            if _dict["domains"]:
                for _dom in _dict["domains"]:
                    d = Domain(_dom["name"],self.config)
                    d.deserialize(_dom)
                    d.subunit=self
                    self.domains.append(d)
            _dict.pop("domains")
        super(Subunit,self).deserialize(_dict)

    def contains(self, compName, resiId):
        return compName == self.name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __deepcopy__(self,x):
        """
        Returns a true copy of the object, used by copy.deepcopy. THis needs to be implmented for all Items!
        """
        subunitCopy =Subunit(name=self.name,config=self.config)
        subunitCopy.setColor(self.color)
        subunitCopy.setChainIds(self.chainIds)
        genSelection = self.createSubunitSelectionFromChains()
        subunitCopy.setSelection(genSelection)
        return subunitCopy

    def chainIdsToString(self,chainIds=None):
        if chainIds is None:
            chainIds = self.chainIds
        return reduce(lambda x,y: str(x)+str(y)+",",chainIds,"")[:-1]

    def parseChainIds(self,chainIdsS):
        ret = [s.strip() for s in chainIdsS.split(",")]
        self.selection =':'+','.join(['.'+s for s in ret])
        return ret

    def getChildren(self):
        return self.domains + self.getChains()

class DomainRangesException(Exception): pass
class Domain(Item):
    """
    An Item which can contain Ranges of a subunit. Has to implement addItem and deleteItem
    """
    
    SHOW = ["name","subunit","ranges","color"]
    OMIT = ["type","_chainIds","chainIds","chains","subunit"]
    def __init__(self,subunit=None,ranges=[[]],\
                 color=MaterialColor(*[1.0,1.0,1.0,0.0]),**kwargs):
        super(Domain,self).__init__(**kwargs)
        self.subunit = subunit
        self.ranges = self.parseRanges(ranges)
        self.color = color
        self.chains = []
        
    def __deepcopy__(self,x):
        r = Domain(name=self.name,config=self.config,subunit=self.subunit,\
                      ranges=self.ranges,color=self.color)
        return r

    def __eq__(self,other):
        if isinstance(other,self.__class__):
            if other.name == self.name and other.subunit == self.subunit\
            and other.ranges == self.ranges and other.color == self.color:
                return True
            else:
                return False
        else:
            return False

    @Item.show.getter
    def show(self):
        self._show = all([item.show for item in self.getChains()])
        return self._show

    @show.setter
    def show(self, val):
        chimera.triggers.blockTrigger('component shown/hidden')
        for child in self.getChains():
            child.show = val #do show by activating chains' triggers

        self._show = val
        # Item.show.fset(self, val)
        chimera.triggers.releaseTrigger('component shown/hidden')

    @Item.active.getter
    def active(self):
        self._active = all([item.active for item in self.getChains()])
        return self._active

    @active.setter
    def active(self, val):
        self._active = val
        for child in self.getChains():
            child.active = val

    def getChains(self):
        selsChains = self.getSelectionsByChain()
        if not self.chains:
            for c, sel in selsChains.iteritems():
                self.chains.append(Chain(c,self,config=self.config))
                self.chains[-1].setSelection(sel[0])
        return self.chains

    def getSelection(self):
        '''Get selection that acts on all chains of the corresponding subunit'''
        rStrings = []
        for oneRange in self.ranges:
            if len(oneRange) == 1:
                rStrings.append(str(oneRange[0]))
            elif len(oneRange) == 2:
                rStrings.append('{0}-{1}'.format(oneRange[0], oneRange[1]))

        forString = []
        for chainId, oneRange in itertools.product(self.subunit.chainIds, rStrings):
            forString.append('{0}.{1}'.format(oneRange, chainId))

        return ':' + ','.join(forString)

    def getSelectionsByChain(self):
        '''Return {chain_id: [[selection]]} object for use in selecting subset of chains.

        I think returns [[selection]] instead of just selection for compatibility with subcomplexes
        '''
        rStrings = []
        for oneRange in self.ranges:
            if len(oneRange) == 1:
                rStrings.append(str(oneRange[0]))
            elif len(oneRange) == 2:
                rStrings.append('{0}-{1}'.format(oneRange[0], oneRange[1]))

        out = defaultdict(list)
        for chainId, oneRange in itertools.product(self.subunit.chainIds, rStrings):
            out[chainId].append('{0}.{1}'.format(oneRange,chainId))

        for k, sels in out.iteritems():
            out[k] = [':' + ','.join(out[k])]

        return out

    def subunitToString(self,subunit):
        return subunit.name

    def parseRanges(self,rangeS):
        ret = []
        if rangeS and type(rangeS) == str:
            ret = [s.split("-") for s in rangeS.split(",")]
            try:
                ret = [[int(s) for s in l] for l in ret]
            except ValueError:
                raise DomainRangesException('Wrong ranges format. Use e.g.: "1-100", "1-100,150,200-300"')
        elif type(rangeS) and type(rangeS) == list:
            ret = rangeS
        return ret

    def parseSubunit(self,name):
        comp = self.config.getSubunitByName(name)
        self.moveDomain(comp)
        return comp

    def moveDomain(self,newSubunit):
        domains = self.subunit.domains
        if self in domains:
            domains.pop(domains.index(self))
        newSubunit.domains.append(self)

    def rangesToString(self,rlist=None):
        if rlist:
            if rlist[0]:
                return reduce(lambda x,y:x+y+",",[str(l[0])+"-"+str(l[1]) \
                   if len(l)>1 else str(l[0]) for l in rlist],"")[:-1]
            else:
                return ""
        else:
            if self.ranges and self.ranges[0]:
                return reduce(lambda x,y:x+y+",",[str(l[0])+"-"+str(l[1]) \
                    if len(l)>1 else str(l[0]) for l in self.ranges],"")[:-1]
            else:
                return ""

    def serialize(self):
        _dict = super(Domain,self).serialize()
        _dict = dict([(k,v) for k,v in _dict.items() if not k in Domain.OMIT])
        _dict["color"] = self.color.rgba()
        return _dict

    def deserialize(self,_dict):
        if "subunit" in _dict:
            _dict.pop("subunit")
        for key,value in _dict.items():
            self.__dict__[key] = value

        if type(_dict["color"]) == list:
            self.color = chimera.MaterialColor(*_dict["color"])

    def getRangesAsResiList(self):
        l = []
        if self.ranges:
            for r in self.ranges:
                if len(r) == 2:
                    l.extend(range(r[0], r[1]+1))
                else:
                    l.append(r[0])

        return l

    def contains(self, compName, resiId):
        return (compName == self.subunit.name) and (int(resiId) in self.getRangesAsResiList())

    def __str__(self):
        subName = "No Subunit"
        if self.subunit:
            subName = self.subunit.name
        s = "Domain: \n \
             -------------------------\n\
             Name:\t%s\n\
             Color:\t%s\n\
             Ranges:\t%s\n\
             Subunit:\t%s\n"%(self.name,self.color.rgba(),\
                                self.rangesToString(),subName)
        return str(s)

    def __repr__(self):
        return self.name

    def validate(self):
        #TODO: Extend this
        ret = True
        if not self.name:
            ret = False
        return ret

class Subcomplex(Item):
    """
    An Item which can contain Subunits and Domains. Has to implement addItem and deleteItem
    """
    
    SHOW = ["name","color","items"]
    OMIT = ["type","dataMap"]
    def __init__(self,config,fake=False):
        super(Subcomplex,self).__init__(config=config)
        self.name = ""
        self.color = MaterialColor(*[1.0,1.0,1.0,0.0])
        self.config = config
        self.items = []
        self.dataMap = dict([("items",\
            [Domain(config=self.config,fake=True),\
             Subunit(config=self.config,fake=True)])])

    @Item.show.getter
    def show(self):
        self._show = any([item.show for item in self.items])
        return self._show

    @show.setter
    def show(self, val):
        chimera.triggers.blockTrigger('component shown/hidden')
        self._show = val
        for child in self.items:
            child.show = val # do show by activating children's (chains) triggers

        self._show = val # do not call Item setter, to not to call the trigger
        chimera.triggers.releaseTrigger('component shown/hidden')

    @Item.active.getter
    def active(self):
        self._active = all([item.active for item in self.items])
        return self._active

    @active.setter
    def active(self, val):
        self._active = val
        for child in self.items:
            child.active = val

    def setColor(self,colorCfg):
        color = chimera.MaterialColor(*[0.0]*4)
        if isinstance(colorCfg, basestring):
            color = chimera.colorTable.getColorByName(colorCfg)
        elif isinstance(colorCfg, tuple) or isinstance(colorCfg, list):
            color = chimera.MaterialColor(*[x for x in colorCfg])
        else:
            color = colorCfg
        self.color = color

    def __deepcopy__(self,x):
        copy = Subcomplex(self.config)
        copy.setColor(self.color)
        copy.name = self.name
        [copy.append(ss) for ss in self.items]
        return copy

    def addItem(self,item):
        """
        Adds an Item to the Subcomplex. This method is to be implemented for all Item which can contain other Item object
        """
        if isinstance(item,Domain) or isinstance(item,Subunit):
            self.items.append(item)
    
    def deleteItem(self,item):
        """
        Deletes an Item from the Subcomplex. This method is to be implemented for all Item which can contain other Item object
        """
        if isinstance(item,Domain) or isinstance(item,Subunit):
            if item in self.items:
                self.items.remove(item)

    def serialize(self):
        _dict = super(Subcomplex,self).serialize()
        _dict = dict([(k,v) for k,v in _dict.items() if not k in Subcomplex.OMIT])
        _dict["items"] = [item.name for item in self.items]
        _dict["color"] = self.color.rgba()
        return _dict

    def getChains(self):
        return []

    def deserialize(self,_dict):
        #CAVEAT: The other items have to been loaded before this
        super(Subcomplex,self).deserialize(_dict)
        if type(_dict["color"]) == list:
            self.color = chimera.MaterialColor(*_dict["color"])
            _dict.pop("color")
        _iter =  [item for item in _dict["items"]]
        _dict["items"] = []
        for name in _iter:
            domain = self.config.getDomainByName(name)
            if domain:
                self.items.append(domain)
                self.items.remove(name)
                continue
            subunit = self.config.getSubunitByName(name)
            if subunit:
                self.items.append(subunit)
                self.items.remove(name)

    def getSelectionsByChain(self):
        out = defaultdict(list)

        for item in self.items:
            for chainId, sel in item.getSelectionsByChain().iteritems():
                out[chainId].extend(sel)

        return out

    def getSelection(self):
        out = []
        for item in self.items:
            out.append(item.getSelection()[1:])

        return ':{0}'.format(','.join(out))

class SimpleDataItem(Item):
    """
    An Item which symbolizes a data structure which does not refer to files.
    """
    def __init__(self, data=None, **kwargs):
        super(SimpleDataItem,self).__init__(**kwargs)

        self.type = "simpleData"
        if kwargs.get('data'):
            self.data = kwargs.get('data')
        self.active = True

    def __str__(self):
        s = "SimpleDataItem: \n \
             -------------------------\n\
             Name:\t%s\n\
             Type:\t%s\n\
             Structure:\t%s\n"%(self.name,self.type,self.data)
        return str(s)

    def __repr__(self):
        return self.__str__()

    def __deepcopy__(self,x):
        dataCopy = deepcopy(self.data)
        itemCopy = type(self)(config=self.config,name=self.name,\
                            data=dataCopy)
        itemCopy.type = self.type
        return itemCopy

class InteractingResidueItem(SimpleDataItem):
    def __init__(self,**kwargs):
        super(InteractingResidueItem,self).__init__(**kwargs)

        self.type = xlinkanalyzer.INTERACTING_RESI_DATA_TYPE
        self.active = True
        self.data = {}
        if kwargs.get('data'):
            self.data = kwargs.get('data')

    def deserialize(self):
        #mirror the old structure
        self.config = self.data
        self.active = True

    def __deepycopy__(self,x):
        super(InteractingResidueItem).__deepcopy__(self)


class File(object):
    """
    Represents a file on disk.
    """
    def __init__(self,path=""):
        self.path = path

    def __str__(self):
        return self.path

    def __repr__(self):
        return self.__str__()

    def getResourcePath(self):
        return self.path

    def serialize(self):
        '''
        the files are saved and loaded with relative paths, to enable moving json files and data files while not relying on absolute paths
        '''
        #Normalize just in case:
        path = normpath(self.path)
        cfg = getConfig()
        if cfg is not None:
            root = normpath(getConfig().root)
        else:
            root = ''
        
        if root and samefileCrossplatform(commonprefix([root, path]), root): #i.e. if is contained in the project dir
            return relpath(path, root)
        else:
            return self.path

    def validate(self):
        return os.path.exists(self.path)

class FileGroup(object):
    """
    represents a group of File objects
    """
    def __init__(self,files=[]):
        self.files=[]
        map(self.addFile,files)

    def __iter__(self):
        for f in self.files:
            yield f

    def __str__(self):
        return "".join([str(f)+"\n" for f in self.files])

    def __repr__(self):
        return self.__str__()

    def __deepcopy__(self,x):
        return FileGroup(self.files)

    def validate(self):
        bools = [f.validate() for f in self.files]
        return reduce(lambda x,y:x and y,bools,True)

    def serialize(self):
        # self.locate()
        _dict = {}
        _dict["files"] = [f.serialize() for f in self.files]
        return _dict

    def deserialize(self,_dict, root):
        """
        Deserializes paths, and returns all missing file paths
        """
        missing = []
        if "files" in _dict:
            for f in _dict["files"]:
                _file = self.addFile(os.path.join(root, f))
                if not _file.validate():
                    missing.append(os.path.join(root, f))
        return missing

    def addFile(self,_file):
        if not isinstance(_file,File):
            _file = File(_file)
        self.files.append(_file)
        return _file

    def getResourcePaths(self):
        ret = [f.getResourcePath() for f in self.files if f.validate()]
        return ret

    def empty(self):
        self.files = []

class Subset(object):
    def __init__(self,items,chosen=None,getElements=lambda:[]):
        '''
        Holds elements for mapping drop downs (all possible as self.items, chosen as self.chosen)
        Refers always to a totality of possible objects and selects a subset of those.
        '''
        self.items = items
        self.getElements = getElements
        if chosen:
            self.chosen = self.intersect(chosen, items)
        else:
            self.chosen = []
        
    def __str__(self):
        return list.__str__([i for i in self.chosen])

    def __iter__(self):
        return self.chosen.__iter__()
    
    def __len__(self):
        return len(self.chosen)
    
    def __contains__(self,i):
        return i in self.chosen

    def __getitem__(self,key):
        try:
            return self.chosen[key]
        except TypeError:
            raise TypeError('Subset indices must be integers')
    
    def intersect(self,l1,l2):
        lret = []
        for el in l1:
            if el in l2:
                lret.append(el)
        return lret
    
    def setChosen(self,items):
        if self.getElements:
            self.items = self.getElements()
        self.chosen = self.items.intersection(WeakSet(items))
    
    def getElements(self):
        return self.items
    
    def serialize(self):
        _list = []
        for item in self:
            _list.append(str(item))
        return _list
    
    def add(self,v):
        if self.getElements:
            self.items = self.getElements()
        if v in self.items and not v in self.chosen:
            self.chosen.append(v)
    
    def remove(self,v):
        if v in self.items:
            self.chosen.remove(v)
            
class Mapping(Item):    
    """
    Symbolizes a Mapping. DataItem has to implement keys() and getElements() which return all possible elements being used 
    as keys and values for the mapping
    """
    def __init__(self,dataItem):
        self.mapping = {}
        self.dataItem = dataItem
        self.name = "Mapping for %s"%(dataItem.name)
    
    def __str__(self,*args,**kwargs):
        ret = ""
        ret += "Mapping of DataItem %s:\n" % (self.dataItem.name)
        for key in self:
            ret += "\t %s --> \t %s\n"%(key,self[key])
        return ret
    
    def __len__(self):
        return reduce(lambda x,y: x+int(len(y)>0),self.mapping.values(),0)
    
    def __contains__(self,key):
        return self.mapping.__contains__(key)
    
    def __iter__(self):
        return self.mapping.__iter__()
    
    def __setitem__(self,key,value):
        if isinstance(value, Subset): 
            self.mapping[key] = value
        elif isinstance(value,list):
            self.mapping[key] = Subset(self.getElements(),chosen=value,getElements=self.getElements)
        
    def __getitem__(self,key):
        ret = []
        if not key in self.mapping:
            return ret
        else:
            return self.mapping[key]
        
    def getSubset(self,key):
        if key in self:
            return self.mapping[key]
        else:
            return Subset(self.getElements(),getElements=self.getElements)

    def keys(self):
        return self.dataItem.keys()
    
    def values(self):
        return self.mapping.values()
    
    def copyFrom(self,other):
        for key in other:
            if key in self:
                self[key] = other.getSubset(key)
    
    def items(self):
        return self.mapping.items()
    
    def getElements(self):
        return self.dataItem.getElements()
    
    def serialize(self):
        _dict = {}
        for k in self.keys():
            _dict[k] = self.getSubset(k).serialize()
        return _dict
    
    def isEmpty(self):
        return not bool(len(self.getElements()))
    
    def isExhausted(self,key):
        return not bool(WeakSet(self.getElements()).difference(WeakSet(self[key])))
    
    def getCopySources(self):
        return self.dataItem.config.getDataItems(self.dataItem.type)

class DataItem(Item):
    """
    DataItem symbolizes data which is contained in files on disk. It holds the paths for these files and has to implement methods
    to parse and interprete the data files
    """
    SHOW = ["name","fileGroup","mapping"]
    OMIT = ["data"]
    def __init__(self,fileGroup=FileGroup(),**kwargs):
        super(DataItem,self).__init__(**kwargs)
        self.type = "data"
        self.mapping = Mapping(self)
        self.fileGroup = fileGroup
        self.active = True

    def __str__(self):
        return self.name

    def __repr__(self):
        s = "DataItem: \n \
        -------------------------\n\
        Name:\t%s\n\
        Type\t%s\n\
        Files:\t%s\n"%(self.name,self.type,self.fileGroup)
        return str(s)

    def __getitem__(self,key):
        if key in self.mapping:
            return self.mapping[key]
        else:
            return None

    def __setitem__(self,key,value):
        if type(value) != list:
            if key in self.mapping:
                self.mapping[key].add(value)
            else:
                self.mapping[key]=[value]
        else:
            self.mapping[key] = value

    def __contains__(self,key):
        return key in self.mapping

    def __deepcopy__(self,x):
        fileGroupCopy = deepcopy(self.fileGroup)
        itemCopy = type(self)(config=self.config,name=self.name,\
                            fileGroup=fileGroupCopy)
        itemCopy.type = self.type
        return itemCopy

    def hasMapping(self):
        return bool(len(self.mapping))

    def updateData(self):
        pass

    def keys(self):
        return []

    def parseFiles(self,filePaths):
        map(self.fileGroup.addFile,filePaths)

    def resourcePaths(self):
        return [f.getResourcePath() for f in self.fileGroup if f.validate()]

    def deserialize(self,_dict):
        """
        Returns missing file paths
        """
        missing = []
        if "fileGroup" in _dict:
            fileGroup = FileGroup()
            missing = fileGroup.deserialize(_dict["fileGroup"], self.config.root)
            self.__dict__["fileGroup"] = fileGroup
            _dict.pop("fileGroup")
        if "mapping" in _dict:
            self.mapping = Mapping(self)
            for k,v in _dict["mapping"].items():
                #TODO: this depends on the mapped object 
                subUnits = [self.config.getSubunitByName(name) for name in v if self.config.getSubunitByName(name) is not None]
                self.mapping[k] = subUnits
            _dict.pop("mapping")
        super(DataItem,self).deserialize(_dict)
        self.updateData()
        return missing

    def serialize(self):
        _dict = super(DataItem,self).serialize()
        _dict = dict([(k,v) for k,v in _dict.items() if not k in DataItem.OMIT])
        _dict["fileGroup"] = self.fileGroup.serialize()
        _dict["mapping"] = self.mapping.serialize()
        if 'resource' in _dict:
            _dict.pop("resource")
        if 'informed' in _dict:
            _dict.pop("informed")

        return _dict

    def validate(self):
        allExist = reduce(lambda x,y: x and y, \
                          [f.validate() for f in self.files],True)
        return True if super(DataItem,self).validate() and allExist else False

    def getProteinsBySubunit(self,name):
        return [k for k in self.mapping if name in self.mapping[k]]

    def getElements(self):
        return []

    def getMappingDefaults(self, text):
        '''
        Guess a subunit based on the name read from the data file.

        @param text Name read from the data file (a key of self.mapping)

        Return Subunit object or None.
        '''
        return SubunitMatcher(self.config).getSubunit(text)

class XQuestItem(DataItem):
    SHOW = ["name","fileGroup","mapping"]
    OMIT = ["xQuestNames","xlinksSets"]
    def __init__(self,**kwargs):
        super(XQuestItem,self).__init__(**kwargs)
        self.type = xlinkanalyzer.XQUEST_DATA_TYPE
        self.xQuestNames = []
        self.xlinksSets = []
        self.updateData()

    def __deepycopy__(self,x):
        super(XQuestItem).__deepcopy__(self)

    def updateData(self):
        if self.resourcePaths():
            xlinksSets = []
            for f in self.resourcePaths():
                xlinksSets.append(XlinksSet(f,description=self.name))

            self.xlinksSets = sum(xlinksSets)
            self.xQuestNames = self.xlinksSets.get_protein_names()

            self.xQuestNames = list(self.xlinksSets.get_protein_names())

            for name in self.xQuestNames:
                if name not in self.mapping:
                    guess = self.getMappingDefaults(name)
                    if guess is not None:
                        self.mapping[name] = [guess]
                    else:
                        self.mapping[name] = []

    def serialize(self):
        _dict = super(XQuestItem,self).serialize()
        _dict = dict([(k,v) for k,v in _dict.items() if not k in XQuestItem.OMIT])
        return _dict
    
    def getElements(self):
        return self.config.getSubunits()
    
    def keys(self):
        self.updateData()
        return self.xQuestNames
    
class XlinkAnalyzerItem(XQuestItem):
    def __init__(self,*args,**kwargs):
        super(XlinkAnalyzerItem,self).__init__(*args,**kwargs)
        self.type = xlinkanalyzer.XLINK_ANALYZER_DATA_TYPE

class SequenceItem(DataItem):
    SHOW = ["name","fileGroup","mapping"]
    OMIT = ["sequences"]
    def __init__(self,**kwargs):
        super(SequenceItem,self).__init__(**kwargs)
        self.type = xlinkanalyzer.SEQUENCES_DATA_TYPE
        self.sequences = {}
        self.data = {}

        # self.locate()
        self.updateData()

    def updateData(self):
        if self.resourcePaths():
            for i,fileName in enumerate(self.resourcePaths()):
                sequences = readFASTA.parse(fileName)[0]
                for sequence in sequences:
                    self.sequences[sequence.name] = sequence

    def serialize(self):
        _dict = super(SequenceItem,self).serialize()
        _dict = dict([(k,v) for k,v in _dict.items() if not k in SequenceItem.OMIT])
        return _dict

    def getElements(self):
        return self.config.getSubunits()

    def keys(self):
        self.updateData()
        return self.sequences.keys()
    

class ConsurfItem(DataItem):
    SHOW = ["name","fileGroup","mapping"]
    OMIT = ["scores"]
    def __init__(self,**kwargs):
        super(ConsurfItem,self).__init__(**kwargs)
        self.type = xlinkanalyzer.CONSURF_DATA_TYPE
        self.data = {}
        self.scores = {}
        # self.locate()
        self.updateData()

    def updateData(self):
        if self.resourcePaths():
            for i,fileName in enumerate(self.resourcePaths()):
                with open(fileName) as f:
                    for line in f:
                        lineData = line.split()
                        if '/' in line:
                            resiId = int(lineData[0])
                            colorId = int(lineData[4].strip('*'))
                            if colorId == 0:
                                colorId = 10
                            self.scores[resiId] = colorId

    def serialize(self):
        _dict = super(ConsurfItem,self).serialize()
        _dict = dict([(k,v) for k,v in _dict.items() if not k in ConsurfItem.OMIT])
        return _dict

    def getMappingElements(self):
        _from = ['unknown_protein']
        _to = [s.name for s in self.config.subunits] if self.config.subunits\
            else [""]
        return [_from,_to]

    def getGroupedByColor(self):
        v = defaultdict(list)

        for key, value in sorted(self.scores.iteritems()):
            v[value].append(key)

        return v


class Assembly(Item):
    """Symbolizes the top level data object. All Items have a reference to this object and pass on data and events to other
    items through this reference. The datamap property maps data type names to the corresponding classes. Can be represented as
    a json file. Holds global properties such as the dataMap or the file path of the json file, also the file root for the project.
    Has, as a container item, addItem and deleteItem implemented. Keeps track of changes with the state property. Holds various
    getter methods to obtain items and several dictionaries to translate between data descriptor keys. the excessive property holds
    unused keys from the json, to be added during save again.
    """
    def __init__(self,frame=None):
        super(Assembly,self).__init__()
        self.subunits = []
        self.subcomplexes = []
        self.dataItems = []
        self.domains = []
        self.root = ""
        self.file = ""
        self.state = "changed"
        self.frame = frame
        self.subunitToChain = {}
        self.chainToSubunit = {}
        self.chainToProtein = {}
        self.excessive = {}

        self.dataMap = dict([\
            ("domains",Domain(config = self,subunit=Subunit(config=self,fake=True),fake=True)),\
            ("subunits",Subunit(config=self,fake=True)),\
            ("subcomplexes",Subcomplex(config=self,fake=True)),\
            ("dataItems",[SequenceItem(config=self,fake=True),\
                          XQuestItem(config=self,fake=True),\
                          XlinkAnalyzerItem(config=self,fake=True),\
                          # InteractingResidueItem(config=self,fake=True),\
                          ConsurfItem(config=self,fake=True)])])

    def __str__(self):
        s = ""
        s += "Subunits:\n"+\
             "---------------------\n"
        for subunit in self.subunits:
            s += str(subunit)+"\n"
        s += "Data Items:\n"+\
             "---------------------\n"
        for dataItem in self.dataItems:
            s += str(dataItem)+"\n"
        return s
    
    def __iter__(self):
        _iter = self.subunits+self.dataItems + self.subcomplexes + self.domains
        for item in _iter:
            yield item
            
    def __contains__(self,item):
        _contains = self.subunits+self.dataItems
        return reduce(lambda x,y: x or y, [item == i for i\
                                            in _contains],False)

    def __len__(self):
        return len(self.subunits+self.dataItems)
    
    def getInstances(self,_class):
        return [item for item in self if isinstance(item,_class)]

    def clear(self):
        self.subunits = []
        self.subcomplexes = []
        self.dataItems = []
        self.domains = []

    def isEmpty(self):
        return len(self.subunits+self.subcomplexes+self.dataItems+self.domains) == 0

    def loadFromDict(self,_dict):
        missing = []
        self.clear()
        classDir = dict([(xlinkanalyzer.XQUEST_DATA_TYPE,XQuestItem),\
                        (xlinkanalyzer.XLINK_ANALYZER_DATA_TYPE,XlinkAnalyzerItem),\
                         (xlinkanalyzer.SEQUENCES_DATA_TYPE,SequenceItem),\
                         (xlinkanalyzer.INTERACTING_RESI_DATA_TYPE,InteractingResidueItem),\
                         (xlinkanalyzer.CONSURF_DATA_TYPE,ConsurfItem)])
        subunits = _dict.pop("subunits",[])
        subcomplexes = _dict.pop("subcomplexes", [])
        dataItems = _dict.pop("data",[])
        
        
        for k,v in _dict.items():
            self.excessive[k] = v
        
        #first, load all Items that might appear in a mapping later on
        for subD in subunits:
            c = Subunit(subD["name"],self)
            c.deserialize(subD)
            self.addItem(c)
        if subcomplexes:
            for subCD in subcomplexes:
                s = Subcomplex(config=self)
                s.deserialize(subCD)
                self.addItem(s)
        #then, load DataItems
        for dataD in dataItems:
            d = None
            #SimpleDataItems, no file references
            if "data" in dataD:
                if dataD["type"] in classDir:
                    d = classDir[dataD["type"]]\
                    (name=dataD["name"],config=self,data=dataD["data"])
                else:
                    if "data" in self.excessive:
                        self.excessive["data"].append(dataD)
                    else:
                        self.excessive["data"] = [dataD]
            #load DataItems in old format, deprecate at some point
            elif "resource" in dataD:
                paths = [os.path.join(self.root, r) for r in dataD["resource"]]
                fileGroup = FileGroup(paths)
                dataD["fileGroup"] = fileGroup.serialize()
                d = classDir[dataD["type"]](config=self)
                d.deserialize(dataD)
            #load DataItems in new format
            elif "fileGroup" in dataD:
                d = classDir[dataD["type"]](config=self)
                missing += d.deserialize(dataD)
            if d:
                self.addItem(d)
        self.domains = self.getDomains()
        return missing
    #KILL IT! KILL IT WITH FIRE!
    def loadFromStructure(self, m):
        def getAddedBySeq(newS, m):
            for comp in self.getSubunits():
                for chainId in comp.chainIds:
                    for s in m.sequences():
                        if s.chain == chainId:
                            if xutils.areSequencesSame(newS, s):
                                return comp.name                        

            return None

        molId = 1
        for s in m.sequences():
            if s.hasProtein():
                name = xutils.getSeqName(s)
                if name is None:
                    addedName = getAddedBySeq(s, m)
                    if addedName is None:
                        name = 'Mol{0}'.format(molId)
                    else:
                        name = addedName

                oldSubunit = self.getSubunitByName(name)
                if oldSubunit is None:
                    molId = molId + 1

                    c = Subunit(name,self)
                    c.setChainIds([str(s.chain)])
                    c.setSelection(c.createSubunitSelectionFromChains())
                    c.color = xutils.getRandomColor()
                    self.addItem(c)

                    info = xutils.getDBrefInfo(s)
                    if info is not None:
                        for k, v in info.iteritems():
                            if v not in (None, '') and c.info.get(k) is None:
                                c.info[k] = info[k]

                else:
                    oldSubunit.addChain(str(s.chain))
    
    
    


    def getColor(self, name):
        color = chimera.MaterialColor(*[0.0]*4)
        if self.getSubunitColors(name):
            colorCfg = self.getSubunitColors(name)
            if isinstance(colorCfg, basestring):
                color = chimera.colorTable.getColorByName(colorCfg)
            elif isinstance(colorCfg, tuple) or isinstance(colorCfg, list):
                color = chimera.MaterialColor(*[x for x in colorCfg])
            else:
                color = colorCfg
        return color

    def addItem(self,item):
        if isinstance(item,Subunit):
            self.subunits.append(item)
        elif isinstance(item,DataItem):
            self.dataItems.append(item)
        elif isinstance(item,SimpleDataItem):
            self.dataItems.append(item)
        elif isinstance(item,Domain):
            self.domains.append(item)
        elif isinstance(item,Subcomplex):
            self.subcomplexes.append(item)
        self.state = "changed"

    def deleteItem(self,item):
        if isinstance(item,Subunit):
            for domain in item.domains:
                self.domains.remove(domain)
            if item in self.subunits:
                self.subunits.remove(item)
        elif isinstance(item,DataItem):
            if item in self.dataItems:
                self.dataItems.remove(item)
        elif isinstance(item,SimpleDataItem):
            if item in self.dataItems:
                self.dataItems.remove(item)
        elif isinstance(item,Domain):
            if [item==d for d in self.getDomains()]:
                self.domains.remove(item)
            if item in item.subunit.domains:
                item.subunit.domains.remove(item)
            for sub in self.subcomplexes:
                sub.deleteItem(item)
        elif isinstance(item,Subcomplex):
            if item in self.subcomplexes:
                self.subcomplexes.remove(item)
        self.state = "changed"

    def getSubunitByName(self,name):
        candidates = [c for c in self.getSubunits() if c.name==name]
        if candidates:
            return candidates[0]
        else:
            return None

    def getSubunits(self):
        return self.subunits

    def getSubunitNames(self):
        return [i.name for i in self.subunits]

    def getDataItems(self,_type = None):
        if not _type:
            return [dI for dI in self.dataItems]
        else:
            typeDataItems = [dI for dI in self.dataItems if dI.type == _type]
            return typeDataItems

    def getSubunitColors(self,name=None):
        if name:
            compL = [i for i in self.subunits if i.name == name]
            if compL:
                return compL[0].color
            else:
                return None
        else:
            return dict([(i.name,i.color) for i in self.subunits])

    def getSubunitSelections(self,name = None):
        if name:
            compL = [i for i in self.subunits if i.name == name]
            if compL:
                return compL[0].selection
            else:
                return None
        else:
            return dict([(i.name,i.selection) for i in self.subunits])

    def getSequences(self,key=None):
        sequence = {}
        for item in self.getDataItems(xlinkanalyzer.SEQUENCES_DATA_TYPE):
            for seqName, seq in item.sequences.iteritems():
                try:
                    comps = item.mapping[seqName]
                except KeyError:
                    pass
                else:
                    for comp in comps:
                        sequence[comp.name] = str(seq)
        return sequence

    def getDomains(self,name=None):
        if name:
            compL = [i for i in self.subunits if i.name == name]
            if compL:
                return [d for d in compL[0].domains]
            else:
                return None
        else:
            ret = sum([c.domains for c in self.getSubunits()],[])
            for d in ret:
                d.config = self
            return ret

    def getDomainByName(self,name):
        allDomains = self.getDomains()
        if allDomains:
            candidates = [d for d in allDomains if d.name == name]
            if candidates:
                return candidates[0]
            else:
                return None
        else:
            return None

    def getSubcomplexes(self):
        return self.subcomplexes

    def getSubcomplexByName(self,name):
        for subcomp in self.subcomplexes:
            if subcomp.name == name:
                return subcomp

    def getChainIdsBySubunitName(self,name=None):
        if name:
            comps = self.getSubunits()
            chainsList = [c.chainIds for c in comps if c.name == name]
            if chainsList:
                chains = reduce(lambda x,y: x+y,chainsList,[])
                self.subunitToChain[name] = chains
                return chains
            else:
                raise KeyError
        else:
            for name in self.getSubunitNames():
                self.getChainIdsBySubunitName(name)
            return self.subunitToChain

    def getSubunitByChain(self,chain=None):
        #returns a Subunit NAME
        if chain:
            if chain in self.chainToSubunit:
                return self.chainToSubunit[chain]
            else:
                comps = self.getSubunits()
                candidates = [c for c in comps if chain in c.chainIds]
                if candidates:
                    subunit = candidates[0].name
                    self.chainToSubunit[chain] = subunit
                    return subunit
                else:
                    return None
        else:
            #this might return an empty dict
            return self.chainToSubunit
   
    def serialize(self):
        _dict = {}
        _dict["xlinkanalyzerVersion"] = xlinkanalyzer.__version__
        _dict["subunits"] = [subunit.serialize() for subunit in self.subunits]
        _dict["data"] = [dataItem.serialize() for dataItem in self.dataItems]
        _dict["subcomplexes"] = [sub.serialize() for sub in self.subcomplexes]
            
        for k,v in self.excessive.items():
            if k == "data":
                for w in v:
                    _dict["data"].append(w)
            else:
                _dict[k] = v
        return _dict

    def dataItems(self):
        return self.dataItems

    def getPyxlinksConfig(self):
        '''
        Return pyxlinks.Config instance.

        It is used to utilize some of the pyxlinks functionality (e.g. statistics-related).

        pyxlinks.Config attributes are references to xlinkanalyzer.Config attributes whenever possible
        '''

        cfg = pyxlinks.Config()
        cfg.components = self.getSubunitNames()  # KEEP cfg.components for pyxlinks compatibility !!!
        cfg.chain_to_comp = self.getSubunitByChain()
        cfg.component_chains = self.getChainIdsBySubunitName()  # KEEP cfg.component_chains for pyxlinks compatibility !!!
        cfg.data = self.getDataItems()
        cfg.cfg_filename = self.file
        cfg.sequences = self.getSequences()

        return cfg

    # def locate(self):
    #     for item in self.dataItems:
    #         item.locate()

    def isAnyPartInactive(self):
        '''Return True if any of Subunits, Domains or Chains has active == False.
        '''
        parts = self.getSubunits()+self.getDomains()
        [parts.extend(s.getChains()) for s in self.getSubunits()]
        [parts.extend(d.getChains()) for d in self.getDomains()]
        active = [p.active for p in parts]

        return not all(active)

    def getActiveParents(self):
        '''Return active Subunit Chains.
        '''
        out = []
        for s in self.getSubunits():
            for c in s.getChains():
                if c.active:
                    out.append(c)

        return out

    def getInActiveChildren(self):
        '''Return Chain objects of inactive Domains
        '''
        children = []
        for s in self.getSubunits():
            for d in s.domains:
                for c in d.getChains():
                    if not c.active:
                        children.append(c)

        return children

    def getActiveChildren(self):
        '''Return Chain objects of active Domains
        '''
        children = []
        for s in self.getSubunits():
            for d in s.domains:
                for c in d.getChains():
                    if c.active:
                        children.append(c)

        return children


class ResourceManager(object):
    """
    A manager object which handles the loading and saving of the json file representing the assembly object.
    """
    def __init__(self,config):
        self.config = config
        self.root = ""

    def saveAssembly(self,parent,saveAs=True):
        if saveAs:
            _file = tkFileDialog.asksaveasfilename(\
                initialfile = "myProject.json",\
                defaultextension=".json",\
                initialdir=self.config.root,\
                parent=parent)
        else:
            _file = self.config.file

        return self._saveAssembly(_file)

    def _saveAssembly(self, _file):
        if _file:
            # self.config.locate()
            self.dumpJson(_file)
            self.config.file = _file
            self.state = "unchanged"
            xlinkanalyzer.pushRecentToPrefs(self.config.file)
            return True
        else:
            return False

    def loadAssembly(self,parent,_file=None):
        if not _file:
            _file = tkFileDialog.askopenfilename(title="Choose file",\
                                                 parent=parent)
        if _file:
            missing = []
            self.config.file = _file
            with open(_file,'r') as f:
                data = json.loads(minify_json.json_minify(f.read()))
                self.config.root = dirname(_file)
                if self.config.frame:
                    self.config.frame.clear()
                missing += self.config.loadFromDict(data)
            xlinkanalyzer.pushRecentToPrefs(self.config.file)
            if missing:
                mstring = ""
                for f in missing:
                    mstring += (str(f)+"\n")
                tkMessageBox.showwarning("Missing files!", mstring)
        return _file
    
    def dumpJson(self,_file):
        with open(_file,'w') as f:
            self.config.root = dirname(_file)
            content = self.config.serialize()
            f.write(json.dumps(content,\
                    sort_keys=True,\
                    indent=4,\
                    separators=(',', ': ')))
            f.close()


class SubunitMatcher(object):
    def __init__(self, config):
        self.config = config

    def getSubunit(self, text):
        subunits = self.config.getSubunits()
        
        for s in subunits:
            if s.name.lower() == text.lower():
                return s

        acc = self._extractdbAccession(text)
        for s in subunits:
            s_acc = s.info.get('pdbx_db_accession')
            if s_acc and s_acc == acc:
                return s
        

    def _extractUniprotAccession(self, text):
        uniprotAccRgxp = '[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}'

        rgxp = '..\|({0})\|'.format(uniprotAccRgxp)
        m = re.match(rgxp, text)
        if m:
            return m.groups()[0]
        else:
            m = re.match(uniprotAccRgxp, text)
            if m:
                return m.group()

    def _extractdbAccession(self, text):
        # TODO: looking for accessions of other databases
        return self._extractUniprotAccession(text)


def isXlinkItem(item):
    return hasattr(item, 'xQuestNames')

import sys
if __name__ == "__main__":
    a = sys.argv[1]
    if a == 'stuff':
        config = Assembly()
        resMngr = ResourceManager(config)
        resMngr.loadAssembly(None,"/home/kai/repos/XlinkAnalyzer/examples/PolI/PolI_with_domains.json")
        d=config.getDomains()[0]
        print d.explore(Domain)
    elif a=='mapping':
        pass
