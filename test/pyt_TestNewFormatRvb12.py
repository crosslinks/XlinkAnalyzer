import XlaGuiTests

# for this test to run do:
# ln -s [full path]/pyt_TestExample.py [Chimeradir]/test/pytests/pyt_[Name].py
# /Applications/Chimera.app/Contents/MacOS/chimera --silent --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ --pypath ~/devel/XlinkAnalyzer/test/ 

RUNME = True

description = "Tests gui class"


class TestXla_Rvb12_new_format(XlaGuiTests.XlaBaseTest):

    def setUp(self):
        mPaths = ['Rvb12/yRvb12.hexamer.pdb']
        cPath = 'Rvb12/Rvb12.json'
        super(TestXla_Rvb12_new_format, self).setUp(mPaths, cPath)
