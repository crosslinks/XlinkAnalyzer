'''
chimera --nogui --script "<full path>/XlinkAnalyzer/scripts/get_distances.py file.pdb/cif xlink_file1.csv xlink_file2.csv"
'''

import os.path
from optparse import OptionParser
import json
from os.path import dirname
import math

import xlinkanalyzer as xla
import xlinkanalyzer.data
import xlinkanalyzer.manager
import xlinkanalyzer.data
import xlinkanalyzer.minify_json
import chimera
import pyxlinks

def getXlinkItems(config):
    data = []
    for item in config.dataItems:
        if xlinkanalyzer.data.isXlinkItem(item):
            if item.active:
                data.append(item)

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

    print 'Mapping of names to structure: (please check if you are not using --proj option): '
    print '\n'.join(str(xi.mapping).splitlines()[1:])

    return config


def main():
    usage = 'usage: chimera --nogui --script "[path to XlinkAnalyzer scripts]/%prog [options] --proj <json project> <pdb_or_cif_file> ..."'
    parser = OptionParser(usage=usage)

    parser.add_option("-o", "--out", dest="out_fn", default=None,
                      help="output filename")

    parser.add_option("-p", "--proj", dest="proj_fn", default=None,
                      help="path to project json file [default: %default (try to guess protein name mapping)]")

    parser.add_option("-d", "--distance", dest="distance_thresh", default=30., type=float,
                      help="Crosslink satisfaction Calpha-Calpha distance")

    (options, args) = parser.parse_args()

    model_filename = args[0]
    xfiles = args[1:]

    chimera.openModels.open(model_filename)
    chimeraModel = chimera.openModels.list()[-1]

    if options.proj_fn:
        config = loadFromJson(options.proj_fn)
    else:
        config = loadFromStructure(chimeraModel, xfiles) #this works only for specific cases where both PDB and CSV files have uniprot annotations

    model = xla.manager.Model(chimeraModel, config)
    mgr = xla.manager.XlinkDataMgr(model, getXlinkItems(config))
    mgr.showAllXlinks()


    statsToShow = ['all', 'satisfied', 'violated', 'satisfied %', 'violated %']

    out_lines = []

    out_lines.append(','.join(['score']+statsToShow))
    max_score = max([pyxlinks.get_score(x) for x in mgr.xlinksSetsMerged.data])
    for thresh in range(0,int(math.ceil(max_score)),5):
        mgr.minScore = thresh
        stats = mgr.countSatisfied(options.distance_thresh)
        out_lines.append(str(thresh) + ',' + ','.join([str(stats[key]) for key in statsToShow]))

    if options.out_fn:
        with open(options.out_fn, 'w') as f:
            f.write('\n'.join(out_lines))
    else:
        print('\n'.join(out_lines))

if __name__ == '__main__':
    main()
