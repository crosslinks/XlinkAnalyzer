import json
import sys
import os
from numpy import unique
from sys import platform as _platform
from copy import deepcopy
from collections import deque
import itertools
from sys import __stdout__
from collections import defaultdict

import chimera
import tkMessageBox
import tkFileDialog
import pyxlinks
from os.path import relpath, exists, join, normpath, dirname, commonprefix, samefile
from chimera import MaterialColor
from MultAlignViewer.parsers import readFASTA
from pyxlinks import XlinksSet

import xlinkanalyzer
from xlinkanalyzer import minify_json
from xlinkanalyzer import getConfig
from util import addProperty

class Item(object):
    SHOW = ["name"]
    def __init__(self,name="",config=None,fake=False):
        self.type = "item"
        self.name = name
        self.config = config
        self.fake = fake
        self.show = True
        self.active = True
        self.sym = True

    def __getitem__(self,slice):
        return self.__dict__

    def serialize(self):
        _dict = dict([(k,v) for k,v in self.__dict__.items()])
        _dict.pop("config")
        _dict.pop("fake")
        _dict.pop("show")
        _dict.pop("active")
        _dict.pop("sym")
        return _dict

    def deserialize(self,_dict):
        for key,value in _dict.items():
            if key == "domains" and _dict[key] is None: #TODO: this is temporal
                self.__dict__[key] = []
            else:
                self.__dict__[key] = value


    def validate(self):
        return True if type(self.name) == str and len(self.name) > 0 else False

    def explore(self,_class,item=None):
        if item is None:
            item = self
        "returns a list of every child"
        visited = set()
        to_crawl = deque([item])
        while to_crawl:
            current = to_crawl.popleft()
            if current in visited:
                continue
            visited.add(current)
            node_children = set(current.flatten())
            to_crawl.extend(node_children - visited)
        visited = [v for v in visited if (isinstance(v,_class) and not v.fake)]
        return list(visited)

    def flatten(self,items = []):
        for obj in self.__dict__.values():
            if type(obj) == dict:
                for v in obj.values():
                    if isinstance(v,Item):
                        items.append(v)
            elif type(obj) == list:
                for v in obj:
                    if isinstance(v,Item):
                        items.append(v)
            else:
                if isinstance(obj,Item):
                    items.append(obj)
        return items

class Component(Item):
    SHOW = ["name","chainIds","color"]
    def __init__(self,*args,**kwargs):
        Item.__init__(self,*args,**kwargs)
        self.type = "component"
        self.color = MaterialColor(*[1.0,1.0,1.0,0.0])
        self.chainIds = []
        self.selection = ""
        self.chainToComponent = {}
        self.componentToChain = {}
        self.domains = []

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

    def setSelection(self,sel):
        self.selection = sel

    def getSelection(self):
        return self.selection

    def getSelectionsByChain(self):
        '''Return {chain_id: selection} object for use in selecting subset of chains.'''
        out = defaultdict(list)
        for chainId in self.chainIds:
            out[chainId].append([':.{0}'.format(chainId)])

        return out

    def createComponentSelectionFromChains(self, chainIds = None):
        if chainIds is None:
            chainIds = self.chainIds
        return ':'+','.join(['.'+s for s in chainIds])

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

    def serialize(self):
        _dict = super(Component,self).serialize()
        _dict["color"] = self.color.rgba()
        _dict["domains"] = [d.serialize() for d in self.domains]
        if "chainToComponent" in _dict:
            _dict.pop("chainToComponent")
        if "componentToChain" in _dict:
            _dict.pop("componentToChain")
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
        super(Component,self).deserialize(_dict)

    def contains(self, compName, resiId):
        return compName == self.name

    def __str__(self):
        s = "Component: \n \
             -------------------------\n\
             Name:\t%s\n\
             Color:\t%s\n\
             Chains:\t%s\n"%(self.name,self.color.rgba(),self.chainIds)
        return str(s)

    def __repr__(self):
        return self.__str__()

    def __deepcopy__(self,x):
        componentCopy =Component(name=self.name,config=self.config)
        componentCopy.setColor(self.color)
        componentCopy.setChainIds(self.chainIds)
        genSelection = self.createComponentSelectionFromChains()
        componentCopy.setSelection(genSelection)
        return componentCopy

    def chainIdsToString(self,chainIds=None):
        if chainIds is None:
            chainIds = self.chainIds
        return reduce(lambda x,y: str(x)+str(y)+",",chainIds,"")[:-1]

    def parseChainIds(self,chainIdsS):
        ret = [s for s in chainIdsS.split(",")]
        self.selection =':'+','.join(['.'+s for s in ret])
        return ret

class Domain(Item):
    SHOW = ["name","subunit","ranges","color"]
    def __init__(self,subunit=None,ranges=[[]],\
                 color=MaterialColor(*[1.0,1.0,1.0,0.0]),chains=[],**kwargs):
        super(Domain,self).__init__(**kwargs)
        self.subunit = subunit
        self.ranges = self.parseRanges(ranges)
        self.color = color
        self._chainIds = chains

    def __deepcopy__(self,x):
        r = Domain(name=self.name,config=self.config,subunit=self.subunit,\
                      ranges=self.ranges,color=self.color,\
                      chains=self._chainIds)
        return r

    def __eq__(self,other):
        if isinstance(other,self.__class__):
            if other.name == self.name and other.subunit == self.subunit\
            and other.ranges == self.ranges and other.color == self.color\
            and other._chainIds == self._chainIds:
                return True
            else:
                return False
        else:
            return False

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
        '''Return {chain_id: selection} object for use in selecting subset of chains.'''
        rStrings = []
        for oneRange in self.ranges:
            if len(oneRange) == 1:
                rStrings.append(str(oneRange[0]))
            elif len(oneRange) == 2:
                rStrings.append('{0}-{1}'.format(oneRange[0], oneRange[1]))

        out = defaultdict(list)
        for chainId, oneRange in itertools.product(self.subunit.chainIds, rStrings):
            out[chainId].append([':{0}.{1}'.format(oneRange,chainId)])

        return out

    def subunitToString(self,subunit):
        return subunit.name

    def parseRanges(self,rangeS):
        ret = []
        if rangeS and type(rangeS) == str:
            ret = [s.split("-") for s in rangeS.split(",")]
            ret = [[int(s) for s in l] for l in ret]
        elif type(rangeS) and type(rangeS) == list:
            ret = rangeS
        return ret

    def parseSubunit(self,name):
        comp = self.config.getComponentByName(name)
        self.moveDomain(comp)
        return comp

    def moveDomain(self,newComponent):
        domains = self.subunit.domains
        if self in domains:
            domains.pop(domains.index(self))
        newComponent.domains.append(self)

    def rangesToString(self,rlist=None):
        if rlist:
            if rlist[0]:
                return reduce(lambda x,y:x+y+",",[str(l[0])+"-"+str(l[1]) \
                   if len(l)>1 else str(l[0]) for l in rlist],"")[:-1]
            else:
                return ""
        else:
            if self.ranges[0]:
                return reduce(lambda x,y:x+y+",",[str(l[0])+"-"+str(l[1]) \
                    if len(l)>1 else str(l[0]) for l in self.ranges],"")[:-1]
            else:
                return ""

    def serialize(self):
        _dict = super(Domain,self).serialize()
        _dict["color"] = self.color.rgba()
        _dict.pop("subunit")
        return _dict

    def deserialize(self,_dict):
        #TODO: Temporal
        if "subunit" in _dict:
            _dict.pop("subunit")
        for key,value in _dict.items():
            if key == "chainIds":
                self.__dict__["_chainIds"] = value
            else:
                self.__dict__[key] = value

        if type(_dict["color"]) == list:
            self.color = chimera.MaterialColor(*_dict["color"])

    def getRangesAsResiList(self):
        l = []
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
        return self.__str__()

    def validate(self):
        #TODO: Extend this
        ret = True
        if not self.name:
            ret = False
        return ret

class Subcomplex(Item):
    SHOW = ["name","color","items"]
    def __init__(self,config,fake=False):
        self.name = ""
        self.color = MaterialColor(*[1.0,1.0,1.0,0.0])
        self.config = config
        self.items = []
        self.dataMap = dict([("items",\
            [Domain(config=self.config,fake=True),\
             Component(config=self.config,fake=True)])])

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
        if isinstance(item,Domain) or isinstance(item,Component):
            self.items.append(item)

    def serialize(self):
        _dict = super(Subcomplex,self).serialize()
        _dict.pop("dataMap")
        _dict["items"] = [item.name for item in self.items]
        _dict["color"] = self.color.rgba()
        return _dict

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
            subunit = self.config.getComponentByName(name)
            if subunit:
                self.items.append(subunit)
                self.items.remove(name)

    def getSelectionsByChain(self):
        out = defaultdict(list)

        for item in self.items:
            for chainId, sel in item.getSelectionsByChain().iteritems():
                out[chainId].extend(sel)

        return out

class SimpleDataItem(Item):
    def __init__(self,name,config,data):
        super(SimpleDataItem,self).__init__(name,config)
        self.type = "simpleData"
        self.data = data

    def __str__(self):
        s = "SimpleDataItem: \n \
             -------------------------\n\
             Name:\t%s\n\
             Type:\t%s\n\
             Structure:\t%s\n"%(self.name,self.type,self.data)
        return str(s)

    def __repr__(self):
        return self.__str__()

class InteractingResidueItem(SimpleDataItem):
    def __init__(self,name,config,data=None):
        super(InteractingResidueItem,self).__init__(name,config,data)
        self.type = xlinkanalyzer.INTERACTING_RESI_DATA_TYPE
        self.active = True
        self.data = {}
        if data:
            self.data = data

    def deserialize(self):
        #mirror the old structure
        self.config = self.data
        self.active = True

class File(object):
    def __init__(self,path=""):
        self.path = path

    def __str__(self):
        return self.path

    def __repr__(self):
        return self.__str__()

    def getResourcePath(self):
        path = self.path
        # if not os.path.exists(path):
        #     path = ""
        return path

    def serialize(self):
        #Normalize just in case:
        path = normpath(self.path)
        root = normpath(getConfig().root)
        if samefile(commonprefix([root, path]), root): #i.e. if is contained in the project dir
            return relpath(path, root)
        else:
            return self.path

    def validate(self):
        return os.path.exists(self.path)

class FileGroup(object):
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

    # def locate(self):
    #     [f.path for f in self.files]

    def validate(self):
        bools = [f.validate() for f in self.files]
        return reduce(lambda x,y:x and y,bools,True)

    def serialize(self):
        # self.locate()
        _dict = {}
        _dict["files"] = [f.serialize() for f in self.files]
        return _dict

    def deserialize(self,_dict, root):
        if "files" in _dict:
            for f in _dict["files"]:
                self.addFile(os.path.join(root, f))
        # self.locate()

    def addFile(self,_file):
        if not isinstance(_file,File):
            _file = File(_file)
        self.files.append(_file)

    def getResourcePaths(self):
        # self.locate()
        return [f.getResourcePath() for f in self.files]

    def empty(self):
        self.files = []

class DataItem(Item):
    SHOW = ["name","fileGroup","mapping"]
    def __init__(self,fileGroup=FileGroup(),mapping=None,**kwargs):
        super(DataItem,self).__init__(**kwargs)
        self.type = "data"
        self.mapping = mapping or {}
        self.fileGroup = fileGroup
        self.active = True

    def __str__(self):
        s = "DataItem: \n \
             -------------------------\n\
             Name:\t%s\n\
             Type\t%s\n\
             Files:\t%s\n"%(self.name,self.type,self.fileGroup)
        return str(s)

    def __repr__(self):
        return self.__str__()

    def __getitem__(self,key):
        if key in self.mapping:
            return self.mapping[key][0]
        else:
            return None

    def __setitem__(self,key,value):
        if type(value) != list:
            if key in self.mapping:
                self.mapping[key].append(value)
            else:
                self.mapping[key]=[value]
        else:
            self.mapping[key] = value

    def __contains__(self,key):
        return key in self.mapping

    def __deepcopy__(self,x):
        fileGroupCopy = deepcopy(self.fileGroup)
        itemCopy = type(self)(config=self.config,name=self.name,\
                            fileGroup=fileGroupCopy,mapping=self.mapping)
        itemCopy.type = self.type
        return itemCopy

    def hasMapping(self):
        return bool(len(self.mapping))

    def updateData(self):
        pass

    def parseFiles(self,filePaths):
        map(self.fileGroup.addFile,filePaths)

    # def locate(self):
    #     self.fileGroup.locate()

    def resourcePaths(self):
        return [f.getResourcePath() for f in self.fileGroup]

    def deserialize(self,_dict):
        super(DataItem,self).deserialize(_dict)
        if "fileGroup" in _dict:
            fileGroup = FileGroup()
            fileGroup.deserialize(_dict["fileGroup"], self.config.root)
            self.__dict__["fileGroup"] = fileGroup
        self.updateData()

    def serialize(self):
        # self.locate()
        _dict = super(DataItem,self).serialize()
        _dict["fileGroup"] = self.fileGroup.serialize()
        if "data" in _dict:
            _dict.pop("data")
        return _dict

    def validate(self):
        allExist = reduce(lambda x,y: x and y, \
                          [f.validate() for f in self.files],True)
        return True if super(DataItem,self).validate() and allExist else False

    def getProteinsByComponent(self,name):
        return [k for k,v in self.mapping.items() if name in v]

    def getMappingElements(self):
        return [[],[]]

class XQuestItem(DataItem):
    SHOW = ["name","fileGroup","mapping"]
    def __init__(self,**kwargs):
        super(XQuestItem,self).__init__(**kwargs)
        self.type = xlinkanalyzer.XQUEST_DATA_TYPE
        self.data={}
        self.xQuestNames = []
        self.xlinksSets = []
        # self.locate()
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

            self.data = self

            self.xQuestNames = list(self.xlinksSets.get_protein_names())

    def serialize(self):
        _dict = super(XQuestItem,self).serialize()
        _dict.pop("xlinksSets")
        _dict.pop("xQuestNames")
        return _dict

    def getMappingElements(self):
        _from = [e for e in self.xQuestNames] if self.xQuestNames else [""]
        _to = [s.name for s in self.config.subunits] if self.config.subunits\
              else [""]
        return [_from,_to]

class XlinkAnalyzerItem(XQuestItem):
    def __init__(self,*args,**kwargs):
        super(XQuestItem,self).__init__(*args,**kwargs)
        self.type = xlinkanalyzer.XLINK_ANALYZER_DATA_TYPE

class SequenceItem(DataItem):
    SHOW = ["name","fileGroup","mapping"]
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
        _dict.pop("sequences")
        return _dict

    def getMappingElements(self):
        _from = [e for e in self.sequences.keys()]\
                 if self.sequences.keys() else [""]
        _to = [s.name for s in self.config.subunits] if self.config.subunits\
            else [""]
        return [_from,_to]

class Assembly(Item):
    def __init__(self,frame=None):
        super(Assembly,self).__init__()
        self.items = []
        self.subunits = []
        self.subcomplexes = []
        self.dataItems = []
        self.domains = []
        self.root = ""
        self.file = ""
        self.state = "unsaved"
        self.frame = frame
        self.componentToChain = {}
        self.chainToComponent = {}
        self.chainToProtein = {}

        self.dataMap = dict([\
            ("domains",Domain(config = self,subunit=Component(config=self,fake=True),fake=True)),\
            ("subunits",Component(config=self,fake=True)),\
            ("subcomplexes",Subcomplex(config=self,fake=True)),\
            ("dataItems",[SequenceItem(config=self,fake=True),\
                          XQuestItem(config=self,fake=True),\
                          XlinkAnalyzerItem(config=self,fake=True)])])

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
        _iter = self.subunits+self.dataItems
        for item in _iter:
            yield item

    def __contains__(self,item):
        _contains = self.subunits+self.dataItems
        return reduce(lambda x,y: x or y, [item == i for i\
                                            in _contains],False)

    def __len__(self):
        return len(self.subunits+self.dataItems)

    def loadFromDict(self,_dict):
        classDir = dict([(xlinkanalyzer.XQUEST_DATA_TYPE,XQuestItem),\
                         (xlinkanalyzer.SEQUENCES_DATA_TYPE,SequenceItem),\
                         (xlinkanalyzer.INTERACTING_RESI_DATA_TYPE,\
                          InteractingResidueItem)])
        components = _dict.get("subunits")
        dataItems = _dict.get("data")
        subcomplexes = _dict.get("subcomplexes")
        #TODO: this is a temporary solution
        for compD in components:
            c = Component(compD["name"],self)
            c.deserialize(compD)
            self.addItem(c)
        for dataD in dataItems:
            if "data" in dataD:
                d = classDir[dataD["type"]]\
                    (dataD["name"],self,dataD["data"])
            elif "resource" in dataD:
                paths = [os.path.join(self.root, r) for r in dataD["resource"]]
                fileGroup = FileGroup(paths)
                d = classDir[dataD["type"]]\
                    (name=dataD["name"],\
                     config=self,\
                     fileGroup=fileGroup,\
                     mapping=dataD["mapping"])
            elif "fileGroup" in dataD:
                d = classDir[dataD["type"]](config=self)
                d.deserialize(dataD)
            self.addItem(d)
        self.domains = self.getDomains()
        if subcomplexes:
            for subD in subcomplexes:
                s = Subcomplex(config=self)
                s.deserialize(subD)
                self.addItem(s)

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


    def getColor(self, name):
        #TODO: Try to simplify
        color = chimera.MaterialColor(*[0.0]*4)
        if self.getComponentColors(name):
            colorCfg = self.getComponentColors(name)
            if isinstance(colorCfg, basestring):
                color = chimera.colorTable.getColorByName(colorCfg)
            elif isinstance(colorCfg, tuple) or isinstance(colorCfg, list):
                color = chimera.MaterialColor(*[x for x in colorCfg])
            else:
                color = colorCfg
        return color

    def addItem(self,item):
        if isinstance(item,Component):
            self.subunits.append(item)
        elif isinstance(item,DataItem):
            self.dataItems.append(item)
        elif isinstance(item,Domain):
            self.domains.append(item)
        elif isinstance(item,Subcomplex):
            self.subcomplexes.append(item)
        self.state = "changed"

    def deleteItem(self,item):
        if isinstance(item,Component):
            if item in self.subunits:
                self.subunits.remove(item)
        elif isinstance(item,DataItem):
            if item in self.dataItems:
                self.dataItems.remove(item)
        elif isinstance(item,Domain):
            if [item==d for d in self.getDomains()]:
                self.domains.remove(item)
            if item in item.subunit.domains:
                item.subunit.domains.remove(item)
        elif isinstance(item,Subcomplex):
            if item in self.items:
                self.items.remove(item)
        self.state = "changed"

    def clear(self):
        for subunit in self.subunits:
            self.subunits.remove(item)
        for dataItem in self.dataItems:
            self.dataItems.remove(item)

    def getComponentByName(self,name):
        candidates = [c for c in self.getComponents() if c.name==name]
        if candidates:
            return candidates[0]
        else:
            return None

    def getComponents(self):
        return self.subunits

    def getComponentNames(self):
        return [i.name for i in self.subunits]

    def getDataItems(self,_type = None):
        if not _type:
            return [dI for dI in self.dataItems]
        else:
            typeDataItems = [dI for dI in self.dataItems if dI.type == _type]
            return typeDataItems

    def getComponentColors(self,name=None):
        if name:
            compL = [i for i in self.subunits if i.name == name]
            if compL:
                return compL[0].color
            else:
                return None
        else:
            return dict([(i.name,i.color) for i in self.subunits])

    def getComponentSelections(self,name = None):
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
                    compNames = item.mapping[seqName]
                except KeyError:
                    pass
                else:
                    for compName in compNames:
                        sequence[compName] = str(seq)
        return sequence

    def getDomains(self,name=None):
        if name:
            compL = [i for i in self.subunits if i.name == name]
            if compL:
                return compL[0].domains
            else:
                return None
        else:
            ret = sum([c.domains for c in self.getComponents()],[])
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

    def getSubcomplexByName(self,name):
        for subcomp in self.subcomplexes:
            if subcomp.name == name:
                return subcomp

    def getChainIdsByComponentName(self,name=None):
        if name:
            comps = self.getComponents()
            chainsList = [c.chainIds for c in comps if c.name == name]
            if chainsList:
                chains = reduce(lambda x,y: x+y,chainsList,[])
                self.componentToChain[name] = chains
                return chains
            else:
                raise KeyError
        else:
            for name in self.getComponentNames():
                self.getChainIdsByComponentName(name)
            return self.componentToChain

    def getComponentByChain(self,chain=None):
        #returns a Component NAME
        if chain:
            if chain in self.chainToComponent:
                return self.chainToComponent[chain]
            else:
                comps = self.getComponents()
                candidates = [c for c in comps if chain in c.chainIds]
                if candidates:
                    component = candidates[0].name
                    self.chainToComponent[chain] = component
                    return component
                else:
                    return None
        else:
            #this might return an empty dict
            return self.chainToComponent

    def serialize(self):
        _dict = {}
        _dict["xlinkanalyzerVersion"] = "1.1"
        _dict["subunits"] = [subunit.serialize() for subunit in self.subunits]
        _dict["data"] = [dataItem.serialize() for dataItem in self.dataItems]
        _dict["subcomplexes"] = [sub.serialize() for sub in self.subcomplexes]
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
        cfg.components = self.getComponentNames()
        cfg.chain_to_comp = self.getComponentByChain()
        cfg.component_chains = self.getChainIdsByComponentName()
        cfg.data = self.getDataItems()
        cfg.cfg_filename = self.file
        cfg.sequences = self.getSequences()

        return cfg

    # def locate(self):
    #     for item in self.dataItems:
    #         item.locate()

class ResourceManager(object):
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
        if _file:
            # self.config.locate()
            self.dumpJson(_file)
            self.config.file = _file
            self.state = "unchanged"

    def loadAssembly(self,parent,_file=None):
        if not _file:
            _file = tkFileDialog.askopenfilename(title="Choose file",\
                                                 parent=parent)
        if _file:
            self.config.file = _file
            with open(_file,'r') as f:
                data = json.loads(minify_json.json_minify(f.read()))
                self.config.root = dirname(_file)
                if self.config.frame:
                    self.config.frame.clear()
                self.config.loadFromDict(data)

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

if __name__ == "__main__":
    if True:
        import numpy
        config = Assembly()
        resMngr = ResourceManager(config)
        resMngr.loadAssembly(None,"/home/kai/repos/XlinkAnalyzer/examples/PolI/PolI_with_domains.json")
        d=config.getDomains()[0]
        print d.explore(Domain)
