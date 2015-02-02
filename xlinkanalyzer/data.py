import json
import sys
import os
from numpy import unique
from sys import platform as _platform

import chimera
import tkMessageBox
import tkFileDialog
import pyxlinks
from os.path import relpath, exists, join, normpath, dirname
from chimera import MaterialColor
from MultAlignViewer.parsers import readFASTA
from pyxlinks import XlinksSet

import xlinkanalyzer
from xlinkanalyzer import minify_json

class Item(object):
    SHOW = ["name"]
    def __init__(self,name="",config=None):
        self.type = "item"
        self.name = name
        self.config = config

    def commaList(self,l):
        return reduce(lambda x,y: x+","+str(y),l,"")[1:]

    def getList(self,commaString):
        return [s.strip() for s in commaString.split(",")]

    def serialize(self):
        _dict = dict([(k,v) for k,v in self.__dict__.items()])
        _dict.pop("config")
        return _dict

    def deserialize(self,_dict):
        for key,value in _dict.items():
            if key == "domains" and _dict[key] is None: #TODO: this is temporal
                self.__dict__[key] = []
            else:
                self.__dict__[key] = value


    def validate(self):
        return True if type(self.name) == str and len(self.name) > 0 else False

class Component(Item):
    SHOW = ["name","chainIds","color"]
    def __init__(self,name="",config=None):
        Item.__init__(self,name,config)
        self.type = "component"
        self.color = MaterialColor(*[1.0,1.0,1.0,0.0])
        self.chainIds = []
        self.selection = ""
        self.chainToComponent = {}
        self.componentToChain = {}
        self.sequence = ""
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

    def setChainToComponent(self,mapping):
        self.chainToComponent = mapping

    def createChainToComponentFromChainIds(self, chainIds):
        return dict([(chain, self.name) for chain in chainIds])

    def createComponentSelectionFromChains(self, chainIds):
        return ':'+','.join(['.'+s for s in chainIds])

    def setComponentToChain(self,mapping):
        self.componentToChain = mapping

    def setDomains(self,domains):
        self.domains = domains

    def setSequence(self,seq):
        self.sequence = seq

    def readJson(self,filename):
        """
        Reads JsonFile to JsonObject (Dict/Lists)
        """

        with open(filename) as f:
            data = self.convert(json.loads(minify_json.json_minify(f.read())))
        return data

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

class Domain(object):
    def __init__(self,name="",\
                      config=None,\
                      subunit=None,\
                      ranges=[[]],\
                      color=MaterialColor(*[1.0,1.0,1.0,0.0]),\
                      chains=[]):
        self.name = name
        self.config = config
        self.subunit = subunit
        self.ranges = self.parse(ranges)
        self.color = color
        self.chainIds = chains

        #all this could easily be avoided by following conventions
        self.SHOW = ["name","subunit","ranges","color"]
        self.TOSTRING = dict([("ranges",self.rangeString),\
                                ("subunit",lambda x:x.name)])
        self.FROMSTRING = dict([("ranges",self.parse),\
                                ("subunit",self.getComponentByName)])

    def __deepcopy__(self,x):
        return Domain(name=self.name,config=self.config,subunit=self.subunit,\
                      ranges=self.ranges,color=self.color,chains=self.chainIds)

    def __eq__(self,other):
        if other.name == self.name and other.subunit == self.subunit\
        and other.ranges == self.ranges and other.color == self.color\
        and other.chainIds == self.chainIds:
            return True
        else:
            return False

    def parse(self,rangeS):
        ret = []
        if rangeS and type(rangeS) == str:
            ret = [s.split("-") for s in rangeS.split(",")]
            ret = [[int(s) for s in l] for l in ret]
        elif type(rangeS) and type(rangeS) == list:
            ret = rangeS
        return ret

    def getComponentByName(self,name):
        return self.config.getComponentByName(name)

    def rangeString(self,rlist=None):
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

    def getChainIds(self):
        if self.chainIds is None:
            return self.comp.chainIds
        else:
            return self.chainIds

    def serialize(self):
        _dict = dict([(k,v) for k,v in self.__dict__.items()])
        _dict["color"] = self.color.rgba()
        _dict.pop("config")
        _dict.pop("subunit")
        _dict.pop("SHOW")
        _dict.pop("FROMSTRING")
        _dict.pop("TOSTRING")
        return _dict

    def deserialize(self,_dict):
        #TODO: Temporal
        if "subunit" in _dict:
            _dict.pop("subunit")
        for key,value in _dict.items():
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
             Subununit:\t%s\n"%(self.name,self.color.rgba(),\
                                self.rangeString(),subName)
        return str(s)

    def __repr__(self):
        return self.__str__()

    def validate(self):
        #TODO: Extend this
        ret = True
        if not self.name:
            ret = False
        return ret

class Subcomplex(object):
    def __init__(self,name,config,color=None):
        self.name = name
        self.color = color
        self.config = config
        self.domains = []

    def addDomain(self,_struc):
        if isinstance(_struc,Domain):
            self.domains.append(struc)


class SimpleDataItem(Item):
    def __init__(self,name,config,data):
        super(SimpleDataItem,self).__init__(name,config)
        self.type = "simpleData"
        self.informed = False
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

class DataItem(Item):
    def __init__(self,name,config,resource,mapping=None):
        super(DataItem,self).__init__(name,config)
        self.type = "data"
        self.mapping = mapping or {}
        self.resource = resource
        self.active = True
        self.informed = False

    def __str__(self):
        s = "DataItem: \n \
             -------------------------\n\
             Name:\t%s\n\
             Type\t%s\n\
             Files:\t%s\n"%(self.name,self.type,self.resource)
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

    def updateData(self):
        pass

    def locate(self):
        formatedRes = []
        locatedRes = []
        missing = []
        root = self.config.root
        #check for windows paths in unix systems
        for r in self.resource:
            if '\\' in r and _platform == "linux" or _platform == "linux2":
                formatedRes.append(r.replace('\\','/'))
            else:
                formatedRes.append(r)
        for r in formatedRes:
            if exists(r):
                locatedRes.append(relpath(r,root))
            elif exists(join(root,r)):
                locatedRes.append(join(root,r))
            else:
                missing.append(r)
        if missing and not self.informed:
            title = "Missing Files"
            fileList = reduce(lambda x,y: x+"%s\n"%(y),missing,"")
            message = "These files could not be found:\n %s"%(fileList)
            tkMessageBox.showinfo(title,message)
            self.informed = True
        self.resource = locatedRes

    def resourcePaths(self):
        self.locate()
        paths = []
        root = self.config.root

        for res in self.resource:
            res = normpath(res)
            path = normpath(join(root,res))
            if os.path.exists(path):
                paths.append(path)
        return paths

    def serialize(self):
        self.locate()
        _dict = super(DataItem,self).serialize()
        if "data" in _dict:
            _dict.pop("data")
        return _dict

    def validate(self):
        allExist = reduce(lambda x,y: x and y, [os.path.exists(resPath) \
                          for resPath in self.resourcePaths()],True)
        return True if super(DataItem,self).validate() and allExist else False

    def getProteinsByComponent(self,name):
        return [k for k,v in self.mapping.items() if name in v]

class XQuestItem(DataItem):
    def __init__(self,name,config,resource,mapping=None):
        super(XQuestItem,self).__init__(name,config,resource,mapping)
        self.type = xlinkanalyzer.XQUEST_DATA_TYPE
        self.data={}
        self.xQuestNames = []
        self.xlinksSets = []
        self.resource = resource
        self.locate()
        self.updateData()

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
        return _dict


class SequenceItem(DataItem):
    def __init__(self,name,config,resource,mapping=None):
        super(SequenceItem,self).__init__(name,config,resource,mapping)
        self.type = xlinkanalyzer.SEQUENCES_DATA_TYPE
        self.sequences = {}
        self.data = {}
        for i,fileName in enumerate(self.resourcePaths()):
            sequences = readFASTA.parse(fileName)[0]
            for sequence in sequences:
                self.sequences[sequence.name] = sequence
        self.locate()

    def serialize(self):
        _dict = super(SequenceItem,self).serialize()
        _dict.pop("sequences")
        return _dict


class Assembly(object):
    def __init__(self,frame=None):
        self.items = []
        self.domains = []
        self.subcomplexes = []
        self.root = ""
        self.file = ""
        self.state = "unsaved"
        self.frame = frame
        self.componentToChain = {}
        self.chainToComponent = {}
        self.proteinToChains = {}
        self.chainToProtein = {}
        self.componentToProtein = {}

        self.dataMap = dict([("domains",Domain(config = self,subunit=Component(config=self)))])

    def __str__(self):
        s = ""
        for item in self.items:
            s += str(item)+"\n"
        return s

    def __iter__(self):
        for item in self.items:
            yield item

    def __contains__(self,item):
        return reduce(lambda x,y: x or y, [item == i for i\
                                            in self.items],False)

    def __len__(self):
        return len(self.items)

    def loadFromDict(self,_dict):
        classDir = dict([(xlinkanalyzer.XQUEST_DATA_TYPE,XQuestItem),\
                         (xlinkanalyzer.SEQUENCES_DATA_TYPE,SequenceItem),\
                         (xlinkanalyzer.INTERACTING_RESI_DATA_TYPE,\
                          InteractingResidueItem)])
        components = _dict["subunits"]
        dataItems = _dict["data"]
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
                d = classDir[dataD["type"]]\
                    (dataD["name"],self,dataD["resource"],dataD["mapping"])
                #TODO: What does this achieve
                d.serialize()
            if not d.informed:
                self.addItem(d)

        self.domains = self.getAllDomains()

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
        if issubclass(item.__class__,Item):
            self.items.append(item)
        elif issubclass(item.__class__,Domain):
            self.domains.append(item)
            item.subunit.domains.append(item)
        self.state = "changed"

    def deleteItem(self,item):
        if issubclass(item.__class__,Item):
            if item in self:
                self.items.remove(item)
        elif issubclass(item.__class__,Domain):
            if [item==d for d in self.getAllDomains()]:
                self.domains.remove(item)
            if item in item.subunit.domains:
                item.subunit.domains.remove(item)
        self.state = "changed"

    def clear(self):
        for item in self:
            self.items.remove(item)

    def getComponentByName(self,name):
        candidates = [c for c in self.getComponents() if c.name==name]
        if candidates:
            return candidates[0]
        else:
            return None

    def getComponents(self):
        return [i for i in self.items \
                if isinstance(i,Component)]

    def getComponentNames(self):
        return [i.name for i in self.items \
                if isinstance(i,Component)]

    def getDataItems(self,_type = None):
        dataItems = [i for i in self.items \
                     if (isinstance(i,DataItem) \
                         or isinstance(i,SimpleDataItem))]
        if not _type:
            return dataItems
        else:
            typeDataItems = [dI for dI in dataItems if dI.type == _type]
            return typeDataItems

    def getComponentColors(self,name=None):
        if name:
            compL = [i for i in self.items \
                     if (isinstance(i,Component) and i.name == name)]
            if compL:
                return compL[0].color
            else:
                return None
        else:
            return dict([(i.name,i.color) for i in self.items\
                     if isinstance(i,Component)])

    def getComponentChains(self,name=None):
        if name:
            compL = [i for i in self.items \
                     if (isinstance(i,Component) and i.name == name)]
            if compL:
                return compL[0].chainIds
            else:
                return None
        else:
            return dict([(i.name,i.chainIds) for i in self.items\
                     if isinstance(i,Component)])

    def getComponentSelections(self,name = None):
        if name:
            compL = [i for i in self.getComponents() if i.name == name]
            if compL:
                return compL[0].selection
            else:
                return None
        else:
            return dict([(i.name,i.selection) for i in self.items\
                     if isinstance(i,Component)])

    def getComponentWithDomains(self):
        ret = self.getComponents()
        ret = [c for c in ret if len(c.domains)>0]
        return ret

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
            compL = [i for i in self.items \
                     if (isinstance(i,Component) and i.name == name)]
            if compL:
                return compL[0].domains
            else:
                return None
        else:
            return dict([(i.name,i.domains) for i in self.items\
                     if isinstance(i,Component)])

    def getDomainNames(self):
        ret = self.getAllDomains()
        ret = [d.name for d in ret]
        ret = list(unique(ret))
        return ret

    def getDomainByName(self):
        ret = self.getAllDomains()
        ret = [d.name for d in ret if d.name == name]
        if ret:
            return ret[0]
        else:
            return []

    def getComponentOrDomain(self,name):
        #TODO: Ambiguity!
        ret = None
        ret = self.getComponentByName(name)
        if ret is not None:
            ret = self.getDomainByName(name)
        return ret

    def getAllDomains(self):
        ret = sum([c.domains for c in self.getComponents()],[])
        return ret

    def getChains(self):
        chains = [c.chainIds for c in self.getComponents()\
                  if c.chainIds is not None]
        ret = reduce(lambda x,y:x+y,chains,[])
        return ret

    def getChainIdsByComponentName(self,name=None):
        if name:
            if name in self.componentToChain:
                return self.componentToChain[name]
            else:
                comps = self.getComponents()
                chainsList = [c.chainIds for c in comps if c.name == name]
                if chainsList:
                    chains = reduce(lambda x,y: x+y,chainsList,[])
                    self.componentToChain[name] = chains
                    return chains
                else:
                    raise KeyError
        else:
            return self.componentToChain

    def getProteinByChain(self,chain):
        if chain in self.chainToProtein:
            return self.chainToProtein[chain]
        else:
            comps = self.getComponentNames()
            dataItems = self.getDataItems()
            candidates = [c for c in comps \
                          if chain in self.getChainIdsByComponentName(c)]
            dCandidates =[d for d in dataItems \
                          if (set(candidates)&set(d.mapping.keys()))]
            proteins = [d[candidates[0]] for d in dCandidates]
            if proteins:
                protein = proteins[0]
                self.chainToProtein[chain] = protein
                return protein
            else:
                return None

    def getProteinByComponent(self,name=None):
        if name in self.componentToProtein:
            return self.componentToProtein[name]
        else:
            dataItems = self.getDataItems()
            dataItems = [d for d in dataItems \
                        if not d.type == xlinkanalyzer.INTERACTING_RESI_DATA_TYPE]
            candidates = []
            for d in dataItems:
                for k,v in d.mapping.items():
                    if name in v:
                        candidates.append(k)
            candidates = unique(candidates)
            if candidates:
                componentName = candidates[0]
                self.componentToProtein[name] = componentName
                return componentName
            else:
                return None

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

    def getChainsByProtein(self,protein):
        #this
        if protein in self.proteinToChains:
            return self.proteinToChains[protein]
        dataItems = self.getDataItems()
        kVPairs = reduce(lambda x,y:x+y,\
                         [d.mapping.items() for d in dataItems],[])
        chains = [v for (k,v) in kVPairs if k in protein]
        chains = list(unique(reduce(lambda x,y: x+y, chains,[])))
        if chains:
            self.proteinToChains[protein] = chains
            return chains
        else:
            raise KeyError

    def serialize(self):
        _dict = {}
        _dict["xlinkanalyzerVersion"] = "0.1"
        _dict["subunits"] = []
        _dict["data"] = []
        for item in self.items:
            if type(item) == Component:
                _dict["subunits"].append(item.serialize())
            else:
                _dict["data"].append(item.serialize())
        return _dict

    def dataItems(self):
        return [item for item in self.items if item.type in \
                [xlinkanalyzer.XQUEST_DATA_TYPE,xlinkanalyzer.SEQUENCES_DATA_TYPE]]

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

    def locate(self):
        for item in self.items:
            if  isinstance(item,DataItem):
                item.locate()

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
            self.config.locate()
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


    def dumpJson(self,_file):
        with open(_file,'w') as f:
            self.config.root = dirname(_file)
            content = self.config.serialize()
            f.write(json.dumps(content,\
                    sort_keys=True,\
                    indent=4,\
                    separators=(',', ': ')))
            f.close()
