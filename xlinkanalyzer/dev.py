
import re
import inspect

from collections import OrderedDict
from copy import deepcopy

import Tkinter
from Tkinter import Frame, LabelFrame, Button, Entry, Frame,Tk, StringVar, \
                    Toplevel, Label, OptionMenu, TclError
import tkMessageBox, tkFileDialog

from Pmw import ScrolledFrame, EntryField

import chimera
from chimera import MaterialColor
from chimera.tkoptions import ColorOption

from data import Item, Assembly, Component, Domain, FileGroup, DataItem

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

class MapFrame(Frame):
    def __init__(self,parent,mapDict,getElements=None,\
                 mappings={},active=False,*args,**kwargs):
        Frame.__init__(self,parent,*args,**kwargs)
        if not (mapDict.keys() and mapDict.values()) and getElements:
            self.getElements = getElements
            self.mapFrom,self.mapTo = getElements()
        else:
            self.mapFrom = mapDict.keys()
            self.mapTo = mapDict.values()
        self.mapTo = [self.parse(v) for v in self.mapTo]
        self.mapDict = mapDict
        self.active = active
        self.mappings = mappings
        self.mapVar = StringVar(self)
        self.mapVar.trace("w",lambda a,b,c:self.copyMapping())
        self.vars = []

        if not (self.mapFrom or self.mapTo or active):
            title = "No elements to map yet"
            message = "Please add some elements before mapping."
            tkMessageBox.showinfo(title,message,parent=self.master)
            return

        self.mapButton = Button(self,text="Map",command=self.popUp)
        self.mapButton.grid()
        self.grid()


    def popUp(self):
        if not (self.mapDict.keys() and self.mapDict.values())\
        and self.getElements:
            self.mapFrom,self.mapTo = self.getElements()

        self.pop = Toplevel()
        self.frame = Frame(self.pop,padx=5,pady=5)
        self.listFrame = LabelFrame(self.frame,padx=5,pady=5)

        row = 0
        Label(self.frame,text="From: ").grid(row=row,column=0,sticky="W")
        Label(self.frame,text="To: ").grid(row=row,column=2,sticky="W")


        self.buildList()
        self.listFrame.grid(sticky='W', row=1,column=0,columnspan=4)

        Button(self.frame,text="Save",command=self.onSave)\
               .grid(sticky='W',row=2,column=0)

        if self.mappings:
            Label(self.frame,text="Copy Mapping From: ")\
                  .grid(sticky='W',row=2,column=1)
            OptionMenu(self.frame,self.mapVar,*self.mappings.keys())\
                       .grid(sticky='W',row=2,column=2)

        self.frame.grid()
        self.grid()
        self.frame.update()

    def buildList(self):
        c = 1
        self.vars = []
        for i,_from in enumerate(self.mapFrom):
            Label(self.listFrame,text=_from)\
                 .grid(row=i+c,column=0,pady=1,padx=3)
            Frame(self.listFrame)\
                 .grid(row=i+c,column=1,pady=1,padx=50)
            var = StringVar(self)
            self.vars.append(var)
            if _from in self.mapDict:
                if self.mapDict[_from]:
                    var.set(self.parse(self.mapDict[_from]))
            var.trace("w",lambda a,b,c,index=i,key=_from:\
                      self.updateMap(index,key))
            OptionMenu(self.listFrame,var,*self.mapTo)\
            .grid(row=i+c,column=2,sticky="W",pady=1,padx=3)

    def parse(self,value):
        if value and type(value) == list:
            return value[0]
        else:
            return value

    def updateMap(self,index,key):
        self.mapDict[key]= self.vars[index].get()

    def onSave(self):
        self.pop.destroy()

    def copyMapping(self):
        key = self.mapVar.get()
        mapping = self.mappings[key]
        for name in self.mapFrom:
            if name in mapping:
                self.mapDict[name] = mapping[name]
        self.buildList()

class ItemFrame(LabelFrame):
    def __init__(self,parent,data,active=False,listFrame=None,*args,**kwargs):
        LabelFrame.__init__(self,parent,*args,**kwargs)
        self.data = data
        if active:
            if type(self.data) == list:
                self.data = dict([(d.__class__.__name__,deepcopy(d)) \
                                  for d in self.data])
            else:
                self.data = deepcopy(data)
        self.fields = OrderedDict()
        self.parent = parent
        self.listFrame = listFrame
        self.active = active
        self.mappings = {}
        self.typeDict = {}
        self.add = None
        self.apply = None
        self.delete = None

        self.classDict = dict([\
                                (str,Entry),\
                                (unicode,Entry),\
                                (MaterialColor,ColorOption),\
                                (list,Entry),\
                                (dict,MapFrame),
                                (FileGroup,FileFrame)\
                             ])

        """
                                {GuiClass:(args,kwargsKeys)} - mostly value=...
        """
        self.analyzeData()
        self.initUIElements()
        self.gridUIElelemts()
        self.grid(pady=2)

    def analyzeData(self):
        if type(self.data) == dict and self.active:
            shows = [data.SHOW for data in self.data.values()]
            common = list(set.intersection(*[set(s) for s in shows]))
            #TODO: Enter some checks for consistency of dataItems
            allFields = sum([d.__dict__.keys() for d in self.data.values()],[])
            fields = list(set.intersection(set(common),set(allFields)))
            fields.sort(lambda x,y: shows[0].index(x)-shows[0].index(y))
            _dict = self.data.values()[0].__dict__
        else:
            show = self.data.SHOW
            _dict = self.data.__dict__
            fields = _dict.keys()
            fields = [f for f in fields if f in show]
            fields.sort(lambda x,y: show.index(x)-show.index(y))

        for fK in fields:
            data = _dict[fK]
            if type(data) in self.classDict:
                self.fields[fK] = (data,self.classDict[type(data)],None,None)
            else:
                if hasattr(data,"__dict__"): #is it an object?
                    for v in data.__dict__.values(): #loop through fields
                        if hasattr(v,"__dict__"): #is it an object?
                            for v1 in v.__dict__.values(): #loop through fields
                                if type(v1) == list and v1:
                                    classL = [item for item in v1\
                                            if isinstance(item,data.__class__)]
                                    if classL:
                                        self.fields[fK] = (data,OptionMenu,\
                                                           classL)

        if hasattr(self.data,"__dict__"):
            mapable = "mapping" in self.data.__dict__.keys()
            for k,v in self.data.__dict__.items():
                if hasattr(v,"__dict__"):
                    for v1 in v.__dict__.values():
                        if type(v1) == list:
                            if self.data in v1 and mapable:
                                self.mappings = dict([(dI.name,dI.mapping)\
                                                       for dI in v1])
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
                _var = StringVar("")
                _var.set(_toString(_data))
                _var.trace("w",_onEdit)
                _label = Label(self,text=self.parseName(k)+":")
                _entry = Entry(self,textvariable=_var)
                _entry.config(width=10)
                self.fields[k] = (_data,_entry,_label,_var)

            elif _UIClass == ColorOption:
                self.fields[k] = (_data,_UIClass,None,None)

            elif _UIClass == OptionMenu:
                _var = StringVar("")
                _names = [c.name for c in _context]
                _var.set(_data.name)
                _var.trace("w",_onEdit)
                _label = Label(self,text=self.parseName(k)+":")
                _menu = OptionMenu(self,_var,*_names)
                _menu.configure(width=5)
                self.fields[k] = (_data,_menu,_label,_var)

            elif _UIClass == FileFrame:
                _menu = FileFrame(self,self.active,_data)
                self.fields[k] = (_data,_menu,None,None)

            elif _UIClass == MapFrame and not self.active:
                _dict = _data
                _getMapping = None
                if "getMappingElements" in dir(self.data):
                    _getMapping = self.data.getMappingElements
                _mapFrame = MapFrame(self,_data,_getMapping,self.mappings,True)
                self.fields[k] = (_data,_mapFrame,None,None)

        if not self.active:
            self.apply = Button(self,text=unichr(10004),command=self.onApply)
            self.createToolTip(self.apply,"Apply")
            self.delete = Button(self,text="x",command=self.onDelete)
            self.createToolTip(self.delete,"Delete")

        else:
            self.add = Button(self,text="Add",command=self.onAdd)
            self.createToolTip(self.add,"Add "+self.data.__class__.__name__)
            if type(self.data) == dict:
                _data = self.data
                self.typeDict = dict([(dI.type,dI.__class__.__name__) \
                                       for dI in _data.values()])
                _var = StringVar("")
                _var.set(self.typeDict.keys()[0])
                _var.trace("w",_onType)
                _label = Label(self,text="Type: ")
                _menu = OptionMenu(self,_var,*self.typeDict.keys())
                _menu.configure(width=12)
                self.fields["type"] = (_data,_menu,_label,_var)

    def gridUIElelemts(self):
        _onEditColor = lambda i: self.onEdit()
        c = 0
        for k,v in self.fields.items():
            _ui = self.fields[k][1]
            _data = self.fields[k][0]
            _label = self.fields[k][2]

            if isinstance(_ui,Entry):
                _label.grid(column=c,row=0)
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
                _label.grid(column=c,row=0)
                c+=1
                _ui.grid(column=c,row=0,pady=5,padx=3)
                c+=1

            elif isinstance(_ui,FileFrame):
                _ui.grid(column=c,row=0,pady=5,padx=3)
                c+=1

            elif isinstance(_ui,MapFrame):
                _ui.grid(column=c,row=0,pady=5,padx=3)
                c+=1

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
            self.apply.config(bg="light grey")

        chimera.triggers.activateTrigger('configUpdated', None)

    def onAdd(self):
        if self.validate():
            self.synchronize()
            if self.listFrame:
                if type(self.data) == dict:
                    _type = self.fields["type"][3].get()
                    _type = self.typeDict[_type]
                    cp = deepcopy(self.data[_type])
                else:
                    cp = deepcopy(self.data)
                self.listFrame.container.addItem(cp)
                self.listFrame.synchronize()
            self.empty()
        else:
            title = "Empty Fields"
            message = "Please fill in all fields."
            tkMessageBox.showinfo(title,message,parent=self)

    def validate(self):
        ret = True
        for k,v in self.fields.items():
            _ui= v[1]
            _var = v[3]
            if isinstance(_ui,Entry):
                ret = len(_var.get())>0

            elif isinstance(_ui,OptionMenu):
                ret = len(_var.get())>0
        return ret

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
        self.apply.configure(bg="light grey")
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
                self.apply.configure(bg="#00A8FF")
            else:
                self.apply.configure(bg="light grey")

    def onType(self):
        pass

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
        self.grid(pady=2)

    def analyzeData(self):
        if not self.items:
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
            frame.grid(sticky="WE",row=i,column=0)

        #self.scrolledFrame.grid(sticky = "WESN",row=r)
        self.scrolledFrame.grid(sticky = "WESN",row=r)


        r += 1
        if isinstance(self.parent,Toplevel):
            self.quit.grid(sticky="WE",row=r,column=0)
            self.grid()
            self.parent.grid()
        else:
            self.grid()

    def synchronize(self,container = None):
        if container:
            self.container = container

        for item in self.container.__dict__[self.show]:
            if not item in [frame.data for frame in self.frames]:
                frame = ItemFrame(self.scrolledFrame.interior(),item)
                self.frames.append(frame)
        self.scrolledFrame.grid()
        self.grid()
        chimera.triggers.activateTrigger('configUpdated', None)
        #TODO: Measure Textinput

