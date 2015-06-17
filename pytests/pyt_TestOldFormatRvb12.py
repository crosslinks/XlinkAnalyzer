import XlaGuiTests

# for this test to run do:
# ln -s [full path]/pyt_TestExample.py [Chimeradir]/test/pytests/pyt_[Name].py
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>

RUNME = True

description = "Tests gui class"


class TestXla_Rvb12_old_format(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        cPath = 'Rvb12/Rvb12_old_format.json'
        super(TestXla_Rvb12_old_format, self).setUp(mPaths, cPath)
