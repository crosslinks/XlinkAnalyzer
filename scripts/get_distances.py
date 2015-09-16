'''
chimera --pypath /struct/cmueller/kosinski/devel/XlinkAnalyzer/xlinkanalyzer --pypath /struct/cmueller/kosinski/devel/pyxlinks/ --nogui --script "/struct/cmueller/kosinski/devel/XlinkAnalyzer/scripts/get_distances.py file.pdb/cif xlink_file1.csv xlink_file2.csv"
'''

import os.path
from optparse import OptionParser

import xlinkanalyzer as xla
import xlinkanalyzer.data
import xlinkanalyzer.manager
import chimera


usage = "usage: %prog [options] xquest_filename dist > some_name.csv"
parser = OptionParser(usage=usage)

parser.add_option("--proj", dest="proj_fn", default=None,
                  help="path to project json file [default: %default]")

(options, args) = parser.parse_args()

model_filename = args[0]
xfiles = args[1:]

print model_filename

chimera.openModels.open(model_filename)
chimeraModel = chimera.openModels.list()[-1]

config = xlinkanalyzer.data.Assembly()
config.loadFromStructure(chimeraModel)

fg = xla.data.FileGroup(files=xfiles)
xi = xla.data.XQuestItem(fileGroup=fg, config=config)

for name in xi.getMappingElements()[0]:
    guess = xi.getMappingDefaults(name)
    if guess is not None:
        xi.mapping[name] = [guess.name]
    # else:
    #     xi.mapping[name] = None

print 'Mapping: ', xi.mapping

model = xla.manager.Model(chimeraModel, config)
mgr = xla.manager.XlinkDataMgr(model, [xi])
mgr.showAllXlinks()

wrong = mgr.getNonCrosslinkableXlinks()
if len(wrong) > 0:
    print 'Non crosslinkable resi xlinked'
    for xl in wrong:
        print ', '.join([xl.xlink.get('Protein1'), xl.xlink.get('Protein2'), xl.xlink.get('AbsPos1'), xl.xlink.get('AbsPos2'), xl.xlink.get('Spectrum'), xl.xlink.get('Type'), xl.xlink.get('XLType'), xl.xlink.get('ld-Score')])


stats = mgr.countSatisfied(xlinkanalyzer.XLINK_LEN_THRESHOLD)

print 'All mapped: {0}'.format(stats['all'])

filename = os.path.splitext(os.path.basename(model_filename))[0] + '.csv'
mgr.exportXlinksWithDistancesToCSV(stats, filename)
print filename

