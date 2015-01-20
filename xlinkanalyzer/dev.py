import re
import inspect

from collections import OrderedDict
from copy import copy

from Tkinter import Frame, LabelFrame, Button, Entry, Frame,Tk, StringVar, \
                    Toplevel, Label, OptionMenu, TclError
import tkMessageBox

from chimera import MaterialColor
from chimera.tkoptions import ColorOption

from data import Item, Assembly, Component, Domain


class MapFrame(object):
    pass


class ItemFrame(LabelFrame):
    def __init__(self,parent,data,active=False,listFrame=None,*args,**kwargs):
        LabelFrame.__init__(self,parent,*args,**kwargs)
        self.data = data
        if active:
            self.data = copy(data)
        self.fields = OrderedDict()
        self.parent = parent
        self.listFrame = listFrame
        self.active = active
        self.add = None
        self.apply = None
        self.delete = None

        self.classDict = dict([\
                                (str,Entry),\
                                (unicode,Entry),\
                                (MaterialColor,ColorOption),\
                                (list,Entry),\
                                (dict,MapFrame)\
                             ])

        """
                                {GuiClass:(args,kwargsKeys)} - mostly value=...
        """
        self.analyzeData()
        self.initUIElements()
        self.gridUIElelemts()
        self.grid(pady=2)


    def analyzeData(self):
        _data = self.data
        _dict = _data.__dict__
        _classD = self.classDict
        fieldKeys = [key for key in _dict.keys() if key in _data.SHOW]
        fieldKeys.sort(lambda x,y:_data.SHOW.index(x)-_data.SHOW.index(y))

        for fK in fieldKeys:
            data = _dict[fK]
            if type(data) in _classD:
                self.fields[fK] = (data,_classD[type(data)],None)
            else:
                if hasattr(data,"__dict__"):
                    for v in data.__dict__.values():
                        if hasattr(v,"__dict__"):
                            for v1 in v.__dict__.values():
                                if type(v1) == list and v1:
                                    classL = [item for item in v1 if item.__class__==data.__class__]
                                    if classL:
                                        self.fields[fK] = (data,OptionMenu,\
                                                           classL)

    def initUIElements(self):

        _onEdit = lambda i,j,k: self.onEdit()

        for k,v in self.fields.items():
            _data = self.fields[k][0]
            _UIClass = self.fields[k][1]
            _context = self.fields[k][2]
            _toString = lambda x: x
            if hasattr(self.data,"TOSTRING"):
                if k in self.data.TOSTRING:
                    _toString = self.data.TOSTRING[k]

            if _UIClass == Entry:
                _var = StringVar("")
                _var.set(_toString(_data))
                _var.trace("w",_onEdit)
                _label = Label(self,text=self.parseName(k)+":")
                _entry = Entry(self,textvariable=_var)
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

        if not self.active:
            self.apply = Button(self,text=unichr(10004),command=self.onApply)
            self.createToolTip(self.apply,"Apply")
            self.delete = Button(self,text="x",command=self.onDelete)
            self.createToolTip(self.delete,"Delete")

        else:
            self.add = Button(self,text="Add",command=self.onAdd)
            self.createToolTip(self.add,"Add "+self.data.__class__.__name__)


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
            _dict = self.data.__dict__
            for k,v in self.fields.items():
                _ui = v[1]
                _var = v[3]
                _parse = lambda x: x
                if hasattr(self.data,"FROMSTRING"):
                    if k in self.data.FROMSTRING:
                        _parse = self.data.FROMSTRING[k]

                if isinstance(_ui,Entry):
                    _dict[k] = _parse(_var.get())

                elif isinstance(_ui,ColorOption):
                    _dict[k] = _parse(_ui.get())

                elif isinstance(_ui,OptionMenu):
                    _dict[k] = _parse(_var.get())

        else:
            self.data = data
            _dict = data.__dict__
            for k,v in self.fields.items():
                _data = _dict[k]
                _ui = v[1]
                _var = v[3]
                _toString = lambda x: x
                if hasattr(self.data,"TOSTRING"):
                    if k in self.data.TOSTRING:
                        _toString = self.data.TOSTRING[k]

                if isinstance(_ui,Entry):
                    _var.set(_toString(_dict[k]))

                elif isinstance(_ui,ColorOption):
                    _ui.set(_dict[k])

                elif isinstance(_ui,OptionMenu):
                    _var.set(_toString(_dict[k]))
            self.apply.config(bg="light grey")

    def onAdd(self):
        if self.validate():
            self.synchronize()
            if self.listFrame:
                self.listFrame.container.addItem(self.data)
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
            _ui= v[1]
            _var = v[3]
            if isinstance(_ui,Entry):
                _var.set("")

            elif isinstance(_ui,ColorOption):
                _ui.set(MaterialColor(*[0.0,0.0,0.0,1.0]))

            elif isinstance(_ui,OptionMenu):
                _var.set("")

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
                if hasattr(self.data,"TOSTRING"):
                    if k in self.data.TOSTRING:
                        _toString = self.data.TOSTRING[k]

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


    def commaList(self,l):
        return reduce(lambda x,y: x+","+str(y),l,"")[1:]

    def parseName(self,s):
        return re.sub('(.)([A-Z][a-z]+)', r'\1 \2', s).title()

    def getList(self,commaString):
        return [s.strip() for s in commaString.split(",")]

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
        self.x = self.y = 0

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
            print "No DataItems"


    def initUIElements(self):

        self.activeFrame = Frame(self,padx=5,pady=5,borderwidth=1)

        self.activeItemFrame = ItemFrame(self.activeFrame,self.items[0],True,\
                                         self,borderwidth=1)
        self.listFrame = LabelFrame(self,padx=5,pady=5,borderwidth=1)

        for item in self.items:
            self.frames.append(ItemFrame(self.listFrame,item,False,\
                                         self))

        self.quit = Button(self,text="Close",command=self.parent.destroy)

    def gridUIElements(self):
        r = 0

        self.activeItemFrame.grid()
        self.activeFrame.grid(sticky="WE",row=r,column=0)
        r += 1

        for i,frame in enumerate(self.frames):
            frame.grid(sticky="WE",row=i,column=0)

        self.listFrame.grid(sticky="WE",row=r,column=0)
        r += 1
        self.quit.grid(sticky="WE",row=r,column=0)

    def synchronize(self,container = None):
        if not container:
            for item in self.items:
                if not item in [frame.data for frame in self.frames]:
                    self.frames.append(ItemFrame(self.listFrame,item))
                    self.listFrame.grid()
        else:
            pass

if __name__ == "__main__":
    tl = Toplevel()
    A = Assembly()
    C = Component("Comp",A)
    C2 = Component("MegaComp",A)
    C.setColor([1,1,0,1])
    C.setChainIds(["A","B","C"])
    A.items.append(C)
    A.items.append(C2)
    D = Domain("Domain",A,C,[[11]],MaterialColor(*[0,0,0,0]),["A","B"])
    D2 = Domain("Domain2",A,C2,[[12]],MaterialColor(*[1,0,0,0]),["C","D"])
    A.domains.append(D)
    A.domains.append(D2)
    #F = ItemFrame(tl,D)
    #F.synchronize(D2)
    I = ItemList(tl,A,"domains",True)
    tl.grid()

    #TODO: Measure Textinput
    #TODO: Workout conventions for SHOW, TOSTRING, FROMSTRING
    #TODO:

