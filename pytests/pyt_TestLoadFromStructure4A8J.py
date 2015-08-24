import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class Test4A8J(XlaGuiTests.TestLoadFromStructure):

    def setUp(self):
        mPaths = ['4A8J/4A8J.pdb']
        super(Test4A8J, self).setUp(mPaths)

    def testThis(self):
        self.assertEqual(len(self.config.getSubunits()), 3)

        info = {
                'elongator complex protein 4': {'db_name': 'UNP', 'db_code': 'ELP4_YEAST', 'pdbx_db_accession': 'Q02884'},
                'elongator complex protein 5': {'db_name': 'UNP', 'db_code': 'ELP5_YEAST', 'pdbx_db_accession': 'P38874'},
                'elongator complex protein 6': {'db_name': 'UNP', 'db_code': 'ELP6_YEAST', 'pdbx_db_accession': 'Q04868'},
        }

        self.assertSetEqual(set(info.keys()), set([s.name for s in self.config.getSubunits()]))
        
        for subunit in self.config.getSubunits():
            self.assertDictContainsSubset(subunit.info, info[subunit.name])
