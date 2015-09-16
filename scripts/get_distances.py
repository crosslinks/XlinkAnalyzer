'''
chimera --pypath /struct/cmueller/kosinski/devel/XlinkAnalyzer/xlinkanalyzer --pypath /struct/cmueller/kosinski/devel/pyxlinks/ --nogui --script "/struct/cmueller/kosinski/devel/XlinkAnalyzer/scripts/get_distances.py file.pdb/cif xlink_file1.csv xlink_file2.csv"
'''

import os.path
from optparse import OptionParser
import json
from os.path import dirname

import xlinkanalyzer as xla
import xlinkanalyzer.data
import xlinkanalyzer.manager
import xlinkanalyzer.data
import xlinkanalyzer.minify_json
import chimera


def getXlinkItems(config):
    data = []
    for item in config.dataItems:
        if xlinkanalyzer.data.isXlinkItem(item):
            if item.data.active:
                data.append(item.data)

    return data


def loadFromJson(json_fn):
    config = xlinkanalyzer.data.Assembly()
    with open(json_fn,'r') as f:
        data = json.loads(xlinkanalyzer.minify_json.json_minify(f.read()))
        config.root = dirname(json_fn)
        if config.frame:
            config.frame.clear()
        config.loadFromDict(data)

    return config


def loadFromStructure(chimeraModel, xfiles):
    config = xlinkanalyzer.data.Assembly()
    config.loadFromStructure(chimeraModel)

    fg = xla.data.FileGroup(files=xfiles)
    xi = xla.data.XQuestItem(fileGroup=fg, config=config)
    config.addItem(xi)
    for name in xi.getMappingElements()[0]:
        guess = xi.getMappingDefaults(name)
        if guess is not None:
            xi.mapping[name] = [guess.name]
        # else:
        #     xi.mapping[name] = None

    print 'Mapping: ', xi.mapping

    return config


def main():
    usage = 'usage: %prog [options] chimera --pypath /struct/cmueller/kosinski/devel/XlinkAnalyzer/xlinkanalyzer --pypath /struct/cmueller/kosinski/devel/pyxlinks/ --nogui --script "/struct/cmueller/kosinski/devel/XlinkAnalyzer/scripts/get_distances.py file.pdb/cif xlink_file1.csv xlink_file2.csv"'
    parser = OptionParser(usage=usage)

    parser.add_option("--proj", dest="proj_fn", default=None,
                      help="path to project json file [default: %default (try to guess protein name mapping)]")

    (options, args) = parser.parse_args()

    model_filename = args[0]
    xfiles = args[1:]

    print model_filename

    chimera.openModels.open(model_filename)
    chimeraModel = chimera.openModels.list()[-1]

    if options.proj_fn:
        config = loadFromJson(options.proj_fn)
    else:
        config = loadFromStructure(chimeraModel, xfiles)

    model = xla.manager.Model(chimeraModel, config)
    mgr = xla.manager.XlinkDataMgr(model, getXlinkItems(config))
    mgr.showAllXlinks()

    wrong = mgr.getNonCrosslinkableXlinks()
    if len(wrong) > 0:
        print 'Non crosslinkable resi xlinked'
        for xl in wrong:
            print ', '.join([xl.xlink.get('Protein1'), xl.xlink.get('Protein2'), xl.xlink.get('AbsPos1'), xl.xlink.get('AbsPos2'), xl.xlink.get('Spectrum'), xl.xlink.get('Type'), xl.xlink.get('XLType'), xl.xlink.get('ld-Score')])


    stats = mgr.countSatisfied(xlinkanalyzer.XLINK_LEN_THRESHOLD)

    print 'No. of xlinks mapped to structure: {0}'.format(stats['all'])

    filename = os.path.splitext(os.path.basename(model_filename))[0] + '.distances.csv'
    mgr.exportXlinksWithDistancesToCSV(stats, filename)
    print 'Output filename:', filename

if __name__ == '__main__':
    main()