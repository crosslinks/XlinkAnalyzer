import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestRvb12(XlaGuiTests.TestLoadFromStructure):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        super(TestRvb12, self).setUp(mPaths)

    def testRvb12(self):
        self.assertEqual(len(self.config.getSubunits()), 2)
        self.assertEqual(len(self.config.getSubunits()[0].chainIds), 3)
        self.assertEqual(len(self.config.getSubunits()[1].chainIds), 3)
        self.assertEqual(self.config.getSubunits()[0].chainIds, ['A','C','E'])
        self.assertEqual(self.config.getSubunits()[1].chainIds, ['B','D','F'])
