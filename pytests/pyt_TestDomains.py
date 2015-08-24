import chimera

import xlinkanalyzer
from xlinkanalyzer.data import Assembly, ResourceManager
from xlinkanalyzer.manager import Model
from xlinkanalyzer import gui
import pyt_TestUtil as util

# for this test to run do:
# ln -s pyt_TestExample.py [Chimeradir]/test/pytests/pyt_[Name].py
# /Applications/Chimera.app/Contents/MacOS/chimera --silent --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ --pypath ~/devel/XlinkAnalyzer/test/ 

RUNME = True

description = "Tests Domains class"


class TestDomains_PolI(util.XLABaseTest):

    def setUp(self):
        mPaths = ['PolI/4C3H.pdb']
        cPath = 'PolI/PolI_with_domains.json'
        super(TestDomains_PolI, self).setUp(mPaths, cPath)

    def testDomainsLoaded(self):
        self.assertEqual(len(self.config.getDomains('A49')), 1)
        self.assertEqual(len(self.config.getSubunitWithDomains()), 1)

    def testSubunitsDomainsOptionMenu(self):
        self._createTestWindow()
        compOptMenuTo = gui.SubunitsDomainsOptionMenu(self.testWindow, 'to subunit (def: all)', self.config)
        compOptMenuTo.pack()


# class TestDomains_Rvb12(util.XLABaseTest):

#     def setUp(self):
#         mPaths = ['Rvb12/yRvb12.hexamer.pdb']
#         cPath = 'Rvb12/Rvb12.json'
#         super(TestDomains_Rvb12, self).setUp(mPaths, cPath)
