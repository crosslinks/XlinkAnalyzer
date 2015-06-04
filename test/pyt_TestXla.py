import chimera
import unittest
from os import path

import xlinkanalyzer
from xlinkanalyzer.data import Assembly, ResourceManager
from xlinkanalyzer.manager import Model
from xlinkanalyzer import gui
import pyt_TestUtil as util

# for this test to run do:
# ln -s [full path]/pyt_TestExample.py [Chimeradir]/test/pytests/pyt_[Name].py
# /Applications/Chimera.app/Contents/MacOS/chimera --silent --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ --pypath ~/devel/XlinkAnalyzer/test/ 

RUNME = True

description = "Tests gui class"



class XlaBaseTest(unittest.TestCase):

    def setUp(self, mPaths, cPath):

        mPath = xlinkanalyzer.__path__[0]
        xlaTestPath = path.join(path.split(mPath)[0], 'test/test_data')
        self.xlaTestMPaths = [path.join(xlaTestPath, _path) for _path in mPaths]
        self.xlaTestCPath = path.join(xlaTestPath, cPath)

        [chimera.openModels.open(_path) for _path in self.xlaTestMPaths]
        self.models = chimera.openModels.list()

    def _testGui(self):
        xlinkanalyzer.gui.show_dialog()
        gui = xlinkanalyzer.get_gui()
        gui.configFrame.resMngr.loadAssembly(gui, self.xlaTestCPath)
        gui.configFrame.clear()
        gui.configFrame.update()
        gui.configFrame.mainWindow.setTitle(gui.configFrame.config.file)
        gui.configFrame.config.state="unchanged"

class TestXla_Rvb12_old_format(XlaBaseTest):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        cPath = 'Rvb12/Rvb12.json'
        super(TestXla_Rvb12_old_format, self).setUp(mPaths, cPath)

    def testGui(self):
        self._testGui()
