import unittest
from os import path

import chimera

import xlinkanalyzer
from xlinkanalyzer import Assembly,ResourceManager

# for this test to run do:
# ln -s TestExample.py [Chimeradir]/test/pytests/pyt_[Name].py


RUNME = True

description = "Provides the model and config of PolI"


class XLABaseTest(unittest.TestCase):
    """Provides the model and config of PolI"""

    def setUp(self):
        mPath = xlinkanalyzer.__path__[0]
        xlaTestPath = path.join(path.split(mPath)[0],'examples/PolI')
        xlaTestModel = path.join(xlaTestPath,'4C3H.pdb')
        xlaTestConfig =path.join(xlaTestPath,'PolI_with_interacting_resi.json')

        self.model = chimera.openModels.open(xlaTestModel)
        self.config = Assembly()
        self.rManager = ResourceManager(self.config)
        self.rManager.loadAssembly(None,xlaTestConfig)

    def runTest(self):
        print self.config
