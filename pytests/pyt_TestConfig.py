import chimera

import xlinkanalyzer
from xlinkanalyzer.data import Assembly, ResourceManager
from xlinkanalyzer.manager import Model

import pyt_TestUtil as util

# for this test to run do:
# ln -s pyt_TestExample.py [Chimeradir]/test/pytests/pyt_[Name].py
# /Applications/Chimera.app/Contents/MacOS/chimera --silent --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ --pypath ~/devel/XlinkAnalyzer/test/ 

RUNME = True

description = "Tests Config class"

class TestConfig_PolI(util.XLABaseTest):

    def setUp(self):
        mPaths = ['PolI/4C3H.pdb']
        cPath = 'PolI/PolI_with_interacting.json'
        super(TestConfig_PolI, self).setUp(mPaths, cPath)

    def testSubunits(self):
        self.assertEqual(len(self.config.getSubunits()), 14)


class TestConfig_Rvb12(util.XLABaseTest):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        cPath = 'Rvb12/Rvb12.json'
        super(TestConfig_Rvb12, self).setUp(mPaths, cPath)

    def testSubunits(self):
        pass
        # self.assertEqual(len(self.config.getSubunits()), 14)