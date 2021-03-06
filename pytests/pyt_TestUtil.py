import unittest
from os import path

from Tkinter import Toplevel

import chimera

import xlinkanalyzer
from xlinkanalyzer.data import Assembly, ResourceManager
from xlinkanalyzer.manager import Model


RUNME = False

description = "Provides the model and config of PolI"


class XLABaseTest(unittest.TestCase):
    """Provides the model and config of PolI"""

    def setUp(self, mPaths, cPath):
        mPath = xlinkanalyzer.__path__[0]
        xlaTestPath = path.join(path.split(mPath)[0], 'pytests/test_data')
        self.xlaTestMPaths = [path.join(xlaTestPath, _path) for _path in mPaths]
        self.xlaTestCPath = path.join(xlaTestPath, cPath)

        self.config = Assembly()
        self.rManager = ResourceManager(self.config)
        self.rManager.loadAssembly(None, self.xlaTestCPath)

        [chimera.openModels.open(_path) for _path in self.xlaTestMPaths]
        self.models = chimera.openModels.list()
        # self.xla_models = [Model(chimeraModel, self.config) for chimeraModel in self.models]

    def _createTestWindow(self):
        self.testWindow = Toplevel()
        w = self.testWindow.winfo_screenwidth()
        h = self.testWindow.winfo_screenheight()
        x = w/2
        y = h/2
        self.testWindow.geometry("+%d+%d" % (x, y))
        self.testWindow.geometry("400x200")

    def tearDown(self):
        chimera.openModels.close(chimera.openModels.list())

