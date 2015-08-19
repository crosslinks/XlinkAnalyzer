import chimera

import XlaGuiTests

import xlinkanalyzer as xla

# for this test to run do:
# chimera --pypath ~/devel/XlinkAnalyzer --pypath ~/devel/pyxlinks/ run.py <name of this file>
RUNME = True

description = "Tests gui class"


class Test4A8J(XlaGuiTests.TestLoadFromStructure):

    def setUp(self):
        mPaths = ['4A8J/4A8J.cif']
        super(Test4A8J, self).setUp(mPaths)

    def testThis(self):
        self.assertEqual(len(self.config.getComponents()), 3)

        info = {
                'ELONGATOR COMPLEX PROTEIN 4': {'db_name': 'UNP', 'db_code': 'ELP4_YEAST', 'pdbx_db_accession': 'Q02884'},
                'ELONGATOR COMPLEX PROTEIN 5': {'db_name': 'UNP', 'db_code': 'ELP5_YEAST', 'pdbx_db_accession': 'P38874'},
                'ELONGATOR COMPLEX PROTEIN 6': {'db_name': 'UNP', 'db_code': 'ELP6_YEAST', 'pdbx_db_accession': 'Q04868'},
        }

        self.assertSetEqual(set(info.keys()), set([s.name for s in self.config.getComponents()]))
        
        for subunit in self.config.getComponents():
            self.assertDictContainsSubset(subunit.info, info[subunit.name])
