'''
chimera --pypath /struct/cmueller/kosinski/devel/XlinkAnalyzer/xlinkanalyzer --pypath /struct/cmueller/kosinski/devel/pyxlinks/ --nogui --script "/struct/cmueller/kosinski/devel/XlinkAnalyzer/scripts/get_distances.py file.pdb/cif xlink_file1.csv xlink_file2.csv"
'''

import os.path

import xlinkanalyzer as xla
import xlinkanalyzer.data
import xlinkanalyzer.manager
import chimera

model_filename = arguments[0]
xfiles = arguments[1:]

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

print xi.mapping

model = xla.manager.Model(chimeraModel, config)
mgr = xla.manager.XlinkDataMgr(model, [xi])
mgr.showAllXlinks()

wrong = mgr.getNonCrosslinkableXlinks()
if len(wrong) > 0:
    print 'Non crosslinkable resi xlinked'
    print wrong


stats = mgr.countSatisfied(xlinkanalyzer.XLINK_LEN_THRESHOLD)
# print stats['reprXlinks']
print stats['satisfied %']
print 'All: {0}'.format(stats['all'])

mgr.exportXlinksWithDistancesToCSV(stats, '/tmp/dupa.csv')
print '/tmp/dupa.csv'

