import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class TestPolI(XlaGuiTests.TestLoadFromStructure):

    def setUp(self):
        mPaths = ['PolI/4C3H.pdb']
        super(TestPolI, self).setUp(mPaths)

    def testThis(self):
        from xlinkanalyzer.data import SubunitMatcher
        s = SubunitMatcher()
        self.assertEqual('dna-directed rna polymerase I subunit RPA34',
                        s.getSubunit('sp|P47006|RPA34_YEAST').name)

        self.assertEqual('dna-directed rna polymerase I subunit RPA34',
                        s.getSubunit('sp|P47006|RPA34_YEAST blashsdf').name)

        self.assertEqual('dna-directed rna polymerase I subunit RPA34',
                        s.getSubunit('P47006').name)

        self.assertEqual('dna-directed rna polymerase I subunit RPA34',
                        'dna-directed rna polymerase I subunit RPA34')

        self.assertIsNone(s.getSubunit('47006'))