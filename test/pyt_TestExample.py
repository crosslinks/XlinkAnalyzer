import unittest
from os import path

import chimera

import xlinkanalyzer
from xlinkanalyzer import Assembly, ResourceManager
from xlinkanalyzer.manager import Model
# for this test to run do:
# ln -s pyt_TestExample.py [Chimeradir]/test/pytests/pyt_[Name].py


RUNME = True

description = "Provides the model and config of PolI"


class XLABaseTest(unittest.TestCase):
    """Provides the model and config of PolI"""

    def setUp(self):
        mPath = xlinkanalyzer.__path__[0]
        xlaTestPath = path.join(path.split(mPath)[0],'test/test_data/PolI')
        xlaTestModel = path.join(xlaTestPath,'4C3H.pdb')
        xlaTestConfig =path.join(xlaTestPath,'PolI_with_interacting_resi.json')

        self.config = Assembly()
        self.rManager = ResourceManager(self.config)
        self.rManager.loadAssembly(None,xlaTestConfig)

        chimera.openModels.open(xlaTestModel)
        self.models = chimera.openModels.list()
        self.xla_models = [Model(chimeraModel, self.config) for chimeraModel in self.models]

    def runTest(self):
        print self.config
