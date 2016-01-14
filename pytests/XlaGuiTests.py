import chimera
import unittest
from os import path

import xlinkanalyzer
from xlinkanalyzer import gui

RUNME = False

description = "Base classes for testing gui"


class XlaBaseTest(unittest.TestCase):

    def setUp(self, mPaths, cPath):

        mPath = xlinkanalyzer.__path__[0]
        xlaTestPath = path.join(path.split(mPath)[0], 'pytests/test_data')
        self.xlaTestMPaths = [path.join(xlaTestPath, _path) for _path in mPaths]
        self.xlaTestCPath = path.join(xlaTestPath, cPath)

        [chimera.openModels.open(_path) for _path in self.xlaTestMPaths]
        self.models = chimera.openModels.list()

        gui.show_dialog()
        guiWin = xlinkanalyzer.get_gui()
        guiWin.configFrame.resMngr.loadAssembly(guiWin, self.xlaTestCPath)
        guiWin.configFrame.clear()
        guiWin.configFrame.update()
        guiWin.configFrame.mainWindow.setTitle(guiWin.configFrame.config.file)
        guiWin.configFrame.config.state = "unchanged"

        self.config = guiWin.configFrame.config

class TestLoadFromStructure(unittest.TestCase):
    def setUp(self, mPaths):

        mPath = xlinkanalyzer.__path__[0]
        xlaTestPath = path.join(path.split(mPath)[0], 'pytests/test_data')
        self.xlaTestMPaths = [path.join(xlaTestPath, _path) for _path in mPaths]

        [chimera.openModels.open(_path) for _path in self.xlaTestMPaths]
        self.models = chimera.openModels.list()

        gui.show_dialog()
        guiWin = xlinkanalyzer.get_gui()
        guiWin.configFrame.resMngr.config.loadFromStructure(self.models[-1])

        guiWin.configFrame.clear()
        guiWin.configFrame.update()
        guiWin.configFrame.config.state = "changed"

        self.config = guiWin.configFrame.config