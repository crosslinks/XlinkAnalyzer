import subprocess

folders = [
    'Ffh-FtsY',
    'GroEL-GroES',
    'Hsp71',
    'NPC',
    'PP2A_network_3dw8',
    'PolI',
    'PolII',
    'PolIII',
    'Rvb12',
    'SMC2SMC4',
    'TFIIIC',
    'XLdb_Kahraman2013_1a9x',
    'XLdb_Kahraman2013_1ai2',
    'XLdb_Kahraman2013_1ako',
    'XLdb_Kahraman2013_1ao6',
    'XLdb_Kahraman2013_1aon',
    'XLdb_Kahraman2013_1blf',
    'XLdb_Kahraman2013_1bsq',
    'XLdb_Kahraman2013_1cmi',
    'XLdb_Kahraman2013_1dfo',
    'XLdb_Kahraman2013_1e58',
    'XLdb_Kahraman2013_1efu',
    'XLdb_Kahraman2013_1emd',
    'XLdb_Kahraman2013_1f88',
    'XLdb_Kahraman2013_1gqe',
    'XLdb_Kahraman2013_1hrc',
    'XLdb_Kahraman2013_1i2n',
    'XLdb_Kahraman2013_1ise',
    'XLdb_Kahraman2013_1jm7',
    'XLdb_Kahraman2013_1kkq',
    'XLdb_Kahraman2013_1mbo',
    'XLdb_Kahraman2013_1trk',
    'XLdb_Kahraman2013_1u6r',
    'XLdb_Kahraman2013_1ujz',
    'XLdb_Kahraman2013_1vix',
    'XLdb_Kahraman2013_1vs5',
    'XLdb_Kahraman2013_1w26',
    'XLdb_Kahraman2013_1zwv',
    'XLdb_Kahraman2013_2akq',
    'XLdb_Kahraman2013_2auk',
    'XLdb_Kahraman2013_2awb',
    'XLdb_Kahraman2013_2bbm',
    'XLdb_Kahraman2013_2c44',
    'XLdb_Kahraman2013_2cqy',
    'XLdb_Kahraman2013_2d3i',
    'XLdb_Kahraman2013_2e50',
    'XLdb_Kahraman2013_2ejm',
    'XLdb_Kahraman2013_2g50',
    'XLdb_Kahraman2013_2hgd',
    'XLdb_Kahraman2013_2lym',
    'XLdb_Kahraman2013_2v7o',
    'XLdb_Kahraman2013_2vn9',
    'XLdb_Kahraman2013_3bg3',
    'XLdb_Kahraman2013_3bhh',
    'XLdb_Kahraman2013_3c5w',
    'XLdb_Kahraman2013_3dfq',
    'XLdb_Kahraman2013_3fga',
    'XLdb_Kahraman2013_3fzf',
    'XLdb_Kahraman2013_3g1e',
    'XLdb_Kahraman2013_3iuc',
    'XLdb_Kahraman2013_3rsp',
    'XLdb_Kahraman2013_4blc',
    'XLdb_Kahraman2013_4f5s',
    'XLdb_Kahraman2013_4fgf',
    'bovineRNAPolII',
    'proteasome_lid',
    'vPol'
]

outdir = '~/Downloads/XlinkAnalyzerDB'
subprocess.call('mkdir -p {0}'.format(outdir), shell=True)

for folder in folders:
    print folder
    subprocess.call('zip -r {1}/{0}.zip {0}'.format(folder, outdir), shell=True)

cmd = 'zip -r ~/Downloads/XlinkAnalyzerDB/XlinkAnalyzerDB.zip {0}'.format(' '.join(folders))
print cmd
subprocess.call(cmd, shell=True)






