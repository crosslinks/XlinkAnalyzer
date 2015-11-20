from sys import platform as _platform
import re
import inspect

from collections import OrderedDict
from copy import deepcopy
from functools import partial

import Tkinter
from Tkinter import LabelFrame, Button, Entry, Frame, StringVar, \
                    Toplevel, Label, OptionMenu, TclError, Tk
import tkMessageBox, tkFileDialog

from Pmw import ScrolledFrame, EntryField

import ttk

import chimera
from chimera import MaterialColor
from chimera.tkoptions import ColorOption

from data import FileGroup,Mapping,Subset
from __builtin__ import True

class FileFrame(Frame):
    def __init__(self,parent,active=False,fileGroup=FileGroup(),\
                 *args,**kwargs):
        Frame.__init__(self,parent,*args,**kwargs)
        self.parent = parent
        self.active = active
        self.fileGroup = fileGroup
        self.initUIElements()
        self.gridUIElements()

    def initUIElements(self):
        filePaths = self.fileGroup.getResourcePaths()
        self.var = StringVar(self)
        if filePaths:
            self.var.set(filePaths[0])
            self.fileMenu = OptionMenu(self,self.var,*filePaths)
        else:
            self.fileMenu = OptionMenu(self,self.var,())
        if self.active:
            self.select = Button(self,text="Browse",command=self.onSelect)

    def gridUIElements(self):
        self.fileMenu.config(width=10)
        self.fileMenu.grid(row=0,column=0)
        if self.active:
            self.select.grid(row=0,column=1)

    def onSelect(self):
        menu = self.fileMenu["menu"]
        menu.delete(0, "end")
        paths = tkFileDialog.askopenfilenames(parent=self)
        if len(paths) > 0:
            map(self.fileGroup.addFile,paths)
            self.resetFileMenu(paths,0)

    def resetFileMenu(self, options, index=None):
        menu = self.fileMenu["menu"]
        menu.delete(0, "end")
        for string in options:
            command=Tkinter._setit(self.var, string, None)
            menu.add_command(label=string,command=command)
        if index is not None:
            self.var.set(options[index])

    def getResourcePaths(self):
        return self.fileGroup.getResourcePaths()

class MenuFrame(Frame):
    """
    __str__ must be an unique identifier
    """
    def __init__(self,parent,items,callback=None,current=None,*args,**kwargs):
        Frame.__init__(self,parent,*args,**kwargs)
        self.var = StringVar(self)
        self.items = items
        if current in self.items:
            self.var.set(current)
        self.var.trace("w", lambda x,y,z,v=self.var: self.onChoice())
        self.delete = None
        self.choice = None
        self.callback = callback
        self.listeners = []
        self.menu = OptionMenu(self,self.var,*([i.name for i in self.items]+["None"]))
        self.menu.configure(width=10)
        
    def onChoice(self):
        if self.callback:
            candidates = [i for i in self.items if i.name == self.var.get()]
            item = None
            if candidates:
                item = candidates[0]
                self.choice = item
            else:
                self.delete = self.choice
            self.callback(item)
            
    def grid(self,*args,**kwargs):
        Frame.grid(self,*args,**kwargs)
        self.menu.grid()
    
    def get(self):
        return self.choice
    
    def set(self,item):
        if item in self.items:
            self.var.set(item)
            
class SubsetFrame(Frame):
    def __init__(self,parent,subset,active=False,limit=None,*args,**kwargs):
        Frame.__init__(self,parent,*args,**kwargs)
        self.subset = subset
        self.menus = []
        self.initFlag = False
        self.limit = limit
        self.synchronize(subset)
        self.grid()
        
    def synchronize(self,subset=None):
        add = True
        if subset:
            for i,s in enumerate(subset):
                m = MenuFrame(self,self.subset.getElements(),self.onChoice)
                self.initFlag = True
                m.set(s)
                m.grid(sticky="w",row=0,column=i)
                self.menus.append(m)
        else:
            for m in self.menus:
                if m.delete and len(self.menus)>1:
                    self.menus.remove(m)
                    m.destroy()
                    add = False
                elif m.delete:
                    self.menus.remove(m)
                    m.destroy()
                    add = True
            double = []
            for i in range(len(self.menus)):
                m = self.menus[i]
                for j in range(i+1,len(self.menus)):
                    if m.get() == self.menus[j].get():
                        double.append(m)
                        double.append(self.menus[j])
                        break
            if double:
                m = double[1]
                self.menus.remove(m)
                m.destroy()
            for s in self.subset:
                if s not in [m.get() for m in self.menus]:
                    self.subset.remove(s)
        if add:
            if self.limit:
                if not (len(self.subset) >= self.limit):
                    m = MenuFrame(self,self.subset.getElements(),self.onChoice)
                    m.grid(sticky="w",row=0,column=len(self.subset)+1)
                    self.menus.append(m)
            else:
                m = MenuFrame(self,self.subset.getElements(),self.onChoice)
                m.grid(sticky="w",row=0,column=len(self.subset)+1)
                self.menus.append(m)
            
    def onChoice(self,item):
        self.subset.add(item)
        if not self.initFlag:
            self.synchronize()
        self.initFlag = False
        
class MapFrame(Frame):
    def __init__(self,parent,mapping,active=False,copy=None,*args,**kwargs):
        Frame.__init__(self,parent,*args,**kwargs)
        self.active = active
        self.mapping = mapping
        self.mapVar = StringVar(self)
        self.mapVar.trace("w",lambda a,b,c:self.copyMapping())
        self.copy = copy
        self.subsetframes = {}

        if self.mapping.isEmpty():
            title = "No elements to map yet"
            message = "Please add some elements before mapping."
            tkMessageBox.showinfo(title,message,parent=self.master)
            return

        self.mapButton = Button(self,text="Map",command=self.popUp)
        self.mapButton.grid()
        self.grid()
    
    def formatKey(self,key):
        if len(key) > 60:
            key = key[:21] + '...' + key[-19:]
        return key
    
    def popUp(self):
        self.pop = Toplevel()
        self.frame = Frame(self.pop,padx=5,pady=5)
        self.listFrame = ScrolledFrame(self.frame)
        self.similars = self.getSimilarItems()
      
        row = 0
        Label(self.frame,text="From: ").grid(row=row,column=0,sticky="W")
        Label(self.frame,text="To: ").grid(row=row,column=2,sticky="W")


        self.buildList()
        self.listFrame.grid(sticky='W', row=1,column=0,columnspan=4)

        Button(self.frame,text="Save",command=self.onSave)\
               .grid(sticky='W',row=2,column=0)

        Label(self.frame,text="Copy From: ").grid(sticky='W',row=2,column=1)
        OptionMenu(self.frame,self.mapVar,*self.similars.keys()).grid(sticky='W',row=2,column=2)

        self.frame.pack()
        self.frame.update()
        
    def getSimilarItems(self):
        ret = {"":None}
        if self.copy:
            ret = dict([(str(i),i) for i in self.mapping.explore(self.copy.__class__)])
        return ret

    def buildList(self):
        c = 0
        for i,key in enumerate(self.mapping.keys()):
            Label(self.listFrame.interior(),text=self.formatKey(key))\
                 .grid(row=i+c,column=0,pady=1,padx=3)
            #TODO: Change in 1.2
            ssf = SubsetFrame(self.listFrame.interior(),self.mapping.getSubset(key),limit=1)
            self.subsetframes[key] = ssf
            ssf.grid(sticky="w",row=i,column=1)

    def onSave(self):
        self.pop.destroy()
        for key,ssf in self.subsetframes.items():
            self.mapping[key] = ssf.subset
        chimera.triggers.activateTrigger('configUpdated', None)
        
    def copyMapping(self):
        copyFrom = self.similars[self.mapVar.get()].mapping
        self.mapping.copyFrom(copyFrom)
        self.buildList()
    
class ItemFrame(LabelFrame):
    def __init__(self,parent,data,active=False,listFrame=None,*args,**kwargs):
        LabelFrame.__init__(self,parent,*args,**kwargs)
        self.data = data
        self.multiple = False
        if active:
            if type(self.data) == list:
                self.data = dict([(d.__class__.__name__,deepcopy(d)) \
                                  for d in self.data])
                for d in self.data.values():
                    if hasattr(d,"fake"):
                        d.fake = True
                self.multiple = True
            else:
                self.data = deepcopy(data)
                if hasattr(self.data,"fake"):
                    self.data.fake = True
        self.fields = OrderedDict()
        self.parent = parent
        self.listFrame = listFrame
        self.active = active
        self.mappings = {}
        self.typeDict = {}
        self.differs = False
        self.add = None
        self.apply = None
        self.delete = None

        self.classDict = dict([\
                                (str,Entry),\
                                (unicode,Entry),\
                                (MaterialColor,ColorOption),\
                                (list,Entry),\
                                (Mapping,MapFrame),
                                (FileGroup,FileFrame)\
                             ])

        """
                                {GuiClass:(args,kwargsKeys)} - mostly value=...
        """
        self.analyzeData()
        self.initUIElements()
        self.gridUIElelemts()

    def grid(self,*args,**kwargs):
        LabelFrame.grid(self,*args,pady=2,**kwargs)

    def isSimple(self,data):
        return type(data) in [list,unicode,MaterialColor,list,FileGroup]

    def flatten(self,obj,items=[]):
        #get rid of complex data mappings, just get elements
        if type(obj) == dict:
            for v in obj.values():
                if type(v) in [list,dict]:
                    flatten(items,v)
                else:
                    items.append(v)
        elif type(obj) == list:
            for v in obj:
                if type(v) in [list,dict]:
                    flatten(items,v)
                else:
                    items.append(v)
        else:
            items.append(obj)
        return items

    def analyzeData(self):
        #sort method used later on
        def sortKeys(shows):
            common = list(set.intersection(*[set(s) for s in shows]))
            diff = list(set.difference(*[set(s) for s in shows]))
            common.sort(lambda x,y: shows[0].index(x)-shows[0].index(y))
            ret = deepcopy(common)
            for key in diff:
                i = None
                _show = None
                for s in shows:
                    if key in s:
                        i=s.index(key)
                        _show = s
                for j,cKey in enumerate(common):
                    if not i>=_show.index(cKey):
                        ret.insert(j,key)
            boolret = False
            if len(shows) > 1:
                if diff:
                    boolret = True
            return ret, boolret

        # check for multiple data types to add
        if type(self.data) == dict and self.active:
            shows = [o.SHOW for o in self.data.values()]
            fields,self.differs = sortKeys(shows)
            _dict = self.data.values()[0].__dict__
        else:
            show = self.data.SHOW
            _dict = self.data.__dict__
            fields = _dict.keys()
            fields = [f for f in fields if f in show]
            fields.sort(lambda x,y: show.index(x)-show.index(y))

        #populate simple data fields with gui classes
        for fK in fields:
            data = _dict[fK]
            if type(data) in self.classDict:
                self.fields[fK] = (data,self.classDict[type(data)],None,None)
            else:
                if "explore" in dir(self.data):
                    classL = self.data.explore(data.__class__)
                    self.fields[fK] = (data,OptionMenu,classL,None)

        #redo keys for different types
        if self.differs:
            [self.fields.pop(k) for k in self.fields.keys()]
            itemNames = self.data.keys()
            itemDict = {}
            for name in itemNames:
                item=self.data[name]
                _class = item.__class__
                allItems = item.explore(_class)
                itemDict[name] = allItems
            self.fields["Type"] = (itemNames,OptionMenu,None,None)
            self.fields["Choose"] = (itemDict,OptionMenu,None,None)

        #look for complex data types
        if hasattr(self.data,"dataMap"):
            for k,v in self.data.dataMap.items():
                #erase already set primitive data type
                if k in self.fields: self.fields.pop(k)
                #container,ItemList,show
                self.fields[k] = (self.data,ItemList,k,None)

        if hasattr(self.data,"__dict__"):
            mapable = "mapping" in self.data.__dict__.keys()
            for k,v in self.data.__dict__.items():
                if hasattr(v,"__dict__"):
                    for v1 in v.__dict__.values():
                        if type(v1) == list:
                            if self.data in v1 and mapable:
                                self.mappings = dict([(dI.name,dI.mapping)\
                                                       for dI in v1 if hasattr(dI, 'mapping')])
    def initUIElements(self):
        _onEdit = lambda i,j,k: self.onEdit()
        _onType = lambda i,j,k: self.onType()

        for k,v in self.fields.items():
            _data = self.fields[k][0]
            _UIClass = self.fields[k][1]
            _context = self.fields[k][2]
            _toString = lambda x: x
            methods = [m for m in dir(self.data) \
                       if m.lower() == k.lower()+"tostring"]

            if methods:
                _toString = self.data.__getattribute__(methods[0])

            if _UIClass == Entry:
                _var = StringVar(self.parent)
                _var.set(_toString(_data))
                _var.trace("w",_onEdit)
                _label = Label(self,text=self.parseName(k)+":")
                _entry = Entry(self,textvariable=_var)
                _entry.config(width=10)
                self.fields[k] = (_data,_entry,_label,_var)

            elif _UIClass == ColorOption:
                self.fields[k] = (_data,_UIClass,None,None)

            elif _UIClass == OptionMenu and not self.differs:
                _var = StringVar(self.parent)
                _names = [c.name for c in _context]
                _var.set(_data.name)
                _var.trace("w",_onEdit)
                _label = Label(self,text=self.parseName(k)+":")
                _menu = OptionMenu(self,_var,*_names)
                _menu.configure(width=5)
                self.fields[k] = (_data,_menu,_label,_var)

            elif _UIClass == OptionMenu and self.differs:
                if k == "Type":
                    _var = StringVar(self.parent)
                    _names = _data
                    _var.set(_names[0])
                    _var.trace("w",_onType)
                    _label = Label(self,text=self.parseName(k)+":")
                    _menu = OptionMenu(self,_var,*_names)
                    _menu.configure(width=5)
                    self.fields[k] = (_data,_menu,_label,_var)
                elif k == "Choose":
                    _var = StringVar(self.parent)
                    _names = [dI.name for dI in _data.values()[0]]
                    if not _names:
                        _names.append("")
                    _var.set(_names[0])
                    _label = Label(self,text=self.parseName(k)+":")
                    _menu = OptionMenu(self,_var,*_names)
                    _menu.configure(width=5)
                    self.fields[k] = (_data,_menu,_label,_var)

            elif _UIClass == FileFrame:
                _menu = FileFrame(self,self.active,_data)
                self.fields[k] = (_data,_menu,None,None)

            elif _UIClass == MapFrame and not self.active:
                _mapping = _data
                _mapFrame = MapFrame(self,_data,True,self.data)
                self.fields[k] = (_data,_mapFrame,None,None)

            elif _UIClass == ItemList and not self.active:
                _itemList = ItemList(self,_data,_context,True)
                self.fields[k] = (_data,_itemList,None,None)

        if not self.active:
            if is_mac():
                self.apply = ttk.Button(self,text=unichr(10004),command=self.onApply, width=1)
            else:
                self.apply = Button(self,text=unichr(10004),command=self.onApply)
            self.createToolTip(self.apply,"Apply")
            self.delete = Button(self,text="x",command=self.onDelete)
            self.createToolTip(self.delete,"Delete")

        else:
            self.add = Button(self,text="Add",command=self.onAdd)
            self.createToolTip(self.add,"Add "+self.data.__class__.__name__)
            if self.multiple and not self.differs:
                _data = self.data
                self.typeDict = {}
                for dI in _data.values():
                    if "type" in dir(dI):
                        _type = dI.type
                    else:
                        _type = dI.__class__.__name__
                    self.typeDict[_type] = dI.__class__.__name__
                _var = StringVar(self.parent)
                _var.set(self.typeDict.keys()[0])
                _var.trace("w",_onType)
                _label = Label(self,text="Type: ")
                _menu = OptionMenu(self,_var,*self.typeDict.keys())
                _menu.configure(width=12)
                self.fields["type"] = (_data,_menu,_label,_var)
            elif self.multiple and self.differs:
                pass
            else:
                pass

    def onType(self):
        if "Type" in self.fields:
            if "Choose" in self.fields:
                _type = self.fields["Type"][3].get()
                _dict = self.fields["Choose"][0]
                _omenu = self.fields["Choose"][1]
                _ovar = self.fields["Choose"][3]
                if _type:
                    items = _dict[_type]
                    menu = _omenu["menu"]
                    menu.delete(0, "end")
                    for i in items:
                        command=Tkinter._setit(_ovar, i.name, None)
                        menu.add_command(label=i.name,command=command)

    def gridUIElelemts(self):
        _onEditColor = lambda i: self.onEdit()
        c = 0
        for k,v in self.fields.items():
            _ui = self.fields[k][1]
            _data = self.fields[k][0]
            _label = self.fields[k][2]

            if isinstance(_ui,Entry):
                _label.grid(column=c,row=0,sticky="E")
                c+=1
                _ui.grid(column=c,row=0,pady=5,padx=3)
                c+=1

            elif inspect.isclass(_ui):
                if issubclass(_ui,ColorOption):
                    _option = ColorOption(self,0,None,None,_onEditColor,\
                                          startCol=c)
                    _option.set(_data)
                    self.fields[k] = (_data,_option,None,None)
                    c+=1

            elif isinstance(_ui,OptionMenu):
                _label.grid(column=c,row=0,sticky="E")
                c+=1
                _ui.grid(column=c,row=0,pady=5,padx=3)
                c+=1

            elif isinstance(_ui,FileFrame):
                _ui.grid(column=c,row=0,pady=5,padx=3)
                c+=1

            elif isinstance(_ui,MapFrame):
                _ui.grid(column=c,row=0,pady=5,padx=3)
                c+=1

            elif isinstance(_ui,ItemList):
                _ui.grid(column=0,row=1,padx=3,columnspan=5)

        if not self.active:
            self.apply.grid(column=c,row=0,pady=5,padx=3)
            c+=1
            self.delete.grid(column=c,row=0,pady=5,padx=3)
            c+=1

        else:
            self.add.grid(column=c,row=0,pady=5,padx=3)

        if self.active:
            self.empty()

    def synchronize(self,data = None):
        if data is None:
            if not self.differs:
                if type(self.data) == dict:
                    _type = self.fields["type"][3].get()
                    _type = self.typeDict[_type]
                    _dict = self.data[_type].__dict__
                else:
                    _dict = self.data.__dict__
                for k,v in self.fields.items():
                    _ui = v[1]
                    _var = v[3]
                    _parse = lambda x: x
                    methods = [m for m in dir(self.data) if m.lower()\
                               == "parse"+k.lower()]
                    if methods:
                        _parse = self.data.__getattribute__(methods[0])

                    if isinstance(_ui,Entry):
                        _dict[k] = _parse(_var.get())
                        #Make this clean!
                        vL = list(v)
                        vL[0] = _parse(_var.get())
                        v = tuple(vL)
                        self.fields[k] = v

                    elif isinstance(_ui,ColorOption):
                        _dict[k] = _parse(_ui.get())

                    elif isinstance(_ui,OptionMenu):
                        _dict[k] = _parse(_var.get())

                    elif isinstance(_ui,FileFrame):
                        _dict[k] = _ui.fileGroup

        else:
            self.data = data
            _dict = data.__dict__
            for k,v in self.fields.items():
                _data = _dict[k]
                _ui = v[1]
                _var = v[3]
                _toString = lambda x: x
                methods = [m for m in dir(self.data) \
                           if m.lower() == k.lower()+"tostring"]
                if methods:
                    _toString = self.data.__getattribute__(methods[0])

                if isinstance(_ui,Entry):
                    _var.set(_toString(_dict[k]))

                elif isinstance(_ui,ColorOption):
                    _ui.set(_dict[k])

                elif isinstance(_ui,OptionMenu):
                    _var.set(_toString(_dict[k]))

            self.unHighlightApply()
        try:
            chimera.triggers.activateTrigger('configUpdated', None)
        except:
            print "No chimera config update!"

    def onAdd(self):
        if self.validate():
            self.synchronize()
            try:
                if not self.differs:
                    if self.listFrame:
                        if type(self.data) == dict:
                            _type = self.fields["type"][3].get()
                            _type = self.typeDict[_type]
                            cp = deepcopy(self.data[_type])
                        else:
                            cp = deepcopy(self.data)
                        self.listFrame.container.addItem(cp)
                        self.listFrame.synchronize()
                elif self.differs:
                    _type = self.fields["Type"][3].get()
                    name = self.fields["Choose"][3].get()
                    pool = self.fields["Choose"][0][_type]
                    choice = [p for p in pool if p.name == name][0]
                    if self.listFrame:
                        self.listFrame.container.addItem(choice)
                        self.listFrame.synchronize()
            finally:
                self.empty()
        else:
            title = "Empty Fields"
            message = "Please fill in all fields."
            tkMessageBox.showinfo(title,message,parent=self)

    def validate(self):
        #no real use for now. maybe rework later
        return True

    def empty(self):
         for k,v in self.fields.items():
            _data = v[0]
            _ui= v[1]
            _var = v[3]
            if isinstance(_ui,Entry):
                _var.set("")

            elif isinstance(_ui,ColorOption):
                _ui.set(MaterialColor(*[0.0,0.0,0.0,1.0]))

            elif isinstance(_ui,OptionMenu):
                _var.set("")

            elif isinstance(_ui,FileFrame):
                _ui.resetFileMenu([""],0)
                _data.empty()

    def onDelete(self):
        if self.listFrame:
            self.listFrame.container.deleteItem(self.data)
            self.listFrame.synchronize()
        self.destroy()

    def onApply(self):
        self.unHighlightApply()
        self.synchronize()

    def onEdit(self):
        if not self.active:
            bList = []
            for k,v in self.fields.items():
                _ui = v[1]
                _data = v[0]
                _var = v[3]
                #TODO move this to analysis
                _toString = lambda x: x
                methods = [m for m in dir(self.data) \
                       if m.lower() == k.lower()+"tostring"]
                if methods:
                    _toString = self.data.__getattribute__(methods[0])

                if isinstance(_ui,Entry):
                    bList.append(_var.get() != _toString(_data))

                elif isinstance(_ui,ColorOption):
                    bList.append(_ui.get() != _toString(_data))

                elif isinstance(_ui,OptionMenu):
                    bList.append(_var.get() != _toString(_data))

            changed = bool(sum(bList))

            if changed:
                self.highlightApply()
            else:
                self.unHighlightApply()

    def highlightApply(self):
        if is_mac():
            style = ttk.Style()
            style.configure('changed.TButton', foreground="red")
            self.apply.configure(style='changed.TButton')
        else:
            self.apply.configure(bg="#00A8FF")

    def unHighlightApply(self):
        if is_mac():
            style = ttk.Style()
            style.configure('applied.TButton', foreground="black")
            self.apply.configure(style='applied.TButton')
        else:
            self.apply.configure(bg="light grey")

    def gcs(self,*instances):
        classes = [type(x).mro() for x in instances]
        for x in classes[0]:
            if all(x in mro for mro in classes):
                return x

    def parseName(self,s):
        return re.sub('(.)([A-Z][a-z]+)', r'\1 \2', s).title()

    def createToolTip(self, widget, text):
        toolTip = ToolTip(widget)
        def enter(event):
            toolTip.showtip(text)
        def leave(event):
            toolTip.hidetip()
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

class ToolTip(object):
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None

    def showtip(self, text):
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        try:
            # For Mac OS
            tw.tk.call("::tk::unsupported::MacWindowStyle",
                       "style", tw._w,
                       "help", "noActivates")
        except TclError:
            pass
        label = Label(tw, text=self.text, justify='left',
                      background="#ffffe0", relief='solid', borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class ItemList(LabelFrame):
    def __init__(self,parent,container,show,active=False,*args,**kwargs):
        LabelFrame.__init__(self,parent,*args,**kwargs)
        self.items = container.__dict__[show]
        self.active = active
        self.parent = parent
        self.frames = []
        self.show = show
        self.container = container

        self.analyzeData()
        self.initUIElements()
        self.gridUIElements()

    def analyzeData(self):
        pass

    def initUIElements(self):
        self.activeFrame = Frame(self,padx=5,pady=5,borderwidth=1)
        dummy = self.container.dataMap[self.show]
        self.activeItemFrame = ItemFrame(self.activeFrame,dummy,True,\
                                         self,borderwidth=1)

        if isinstance(self.parent,Toplevel):
            options = {"usehullsize":1,\
                       "hull_width":560,\
                       "hull_height":400}
        elif isinstance(self.parent,ItemFrame):
            options = {"usehullsize":1,\
                       "hull_width":540,\
                       "hull_height":150}
        else:
            options = {"usehullsize":1,\
                       "hull_width":460,\
                       "hull_height":320}

        self.scrolledFrame = ScrolledFrame(self,**options)

        for item in self.items:
            self.frames.append(\
                    ItemFrame(self.scrolledFrame.interior(),item,False,self))

        if isinstance(self.parent,Toplevel):
            self.quit = Button(self,text="Close",command=self.parent.destroy)

    def gridUIElements(self):
        r = 0

        self.activeItemFrame.grid()
        self.activeFrame.grid(sticky="WE",row=r,column=0)
        r += 1

        for i,frame in enumerate(self.frames):
            frame.grid(row=i,column=0,sticky="W",columnspan=2)

        self.scrolledFrame.grid(sticky = "WESN",row=r)

        r += 1
        if isinstance(self.parent,Toplevel):
            self.quit.grid(sticky="WE",row=r,column=0)
            self.grid()
            self.parent.grid()

    def grid(self,*args,**kwargs):
        LabelFrame.grid(self,*args,pady=2,**kwargs)

    def synchronize(self,container = None):
        if container:
            self.container = container
        #TODO: Thats lazy
        for i,item in enumerate(self.container.__dict__[self.show]):
            if not item in [frame.data for frame in self.frames]:
                frame = ItemFrame(self.scrolledFrame.interior(),\
                                  item,False,self)
                frame.grid(sticky="W")
                self.frames.append(frame)
        
        for f in self.frames:
            if not (f.data in self.container.__dict__[self.show]):
                f.destroy()
        self.scrolledFrame.grid()
        self.grid()
        try:
            chimera.triggers.activateTrigger('configUpdated', None)
        except:
            print "No chimera config update!"
    

if __name__ == "__main__":
    if False:
        class A(object):
            SHOW = ["list","string"]
            def __init__(self):
                self.list = [1,2,3]
                self.string = "String"
    
        class B(object):
            SHOW = ["oL"]
            def __init__(self):
                self.oL = []
                self.dataMap = dict([("oL",A())])
    
            def addItem(self,item):
                if isinstance(item,A):
                   self.oL.append(item)
    
        class C(object):
            def __init__(self):
                self.oLL = []
                self.string = ""
                self.numbers = []
                self.dataMap = dict([("oLL",B())])
    
            def addItem(self,item):
                if isinstance(item,B):
                   self.oLL.append(item)
    
        from Tkinter import Tk
        root = Tk()
        b = B()
        c = C()
        iL = ItemList(root,c,"oLL")
        iL.grid()
