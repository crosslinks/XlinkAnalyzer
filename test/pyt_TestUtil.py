import unittest
from os import path

import chimera

import xlinkanalyzer
from xlinkanalyzer import Assembly, ResourceManager
from xlinkanalyzer.manager import Model


RUNME = False

description = "Provides the model and config of PolI"


class XLABaseTest(unittest.TestCase):
    """Provides the model and config of PolI"""

    def setUp(self, mPaths, cPath):
        mPath = xlinkanalyzer.__path__[0]
        xlaTestPath = path.join(path.split(mPath)[0], 'test/test_data')
        self.xlaTestMPaths = [path.join(xlaTestPath, _path) for _path in mPaths]
        self.xlaTestCPath = path.join(xlaTestPath, cPath)

        self.config = Assembly()
        self.rManager = ResourceManager(self.config)
        self.rManager.loadAssembly(None, self.xlaTestCPath)

        [chimera.openModels.open(_path) for _path in self.xlaTestMPaths]
        self.models = chimera.openModels.list()
        # self.xla_models = [Model(chimeraModel, self.config) for chimeraModel in self.models]

    def tearDown(self):
        chimera.openModels.close(chimera.openModels.list())