import csv
import itertools
import subprocess
from collections import defaultdict
import json
import re

filename = 'journal.pone.0073411.s006.csv'

COLORS = [
    [
        0.439215686,
        0.831372549,
        1.0,
        1.0
    ],
    [
        0.133,
        0.545,
        0.133,
        1.0

    ],
    [
        1.000,
        0.412,
        0.706,
        1.0

    ],
    [
        1.0,
        0.843,
        0.0,
        1.0

    ],
    [
        0.957,
        0.643,
        0.376,
        1.000

    ],
    [
        0.0,
        0.545,
        0.545,
        1.0

    ]

]
templ1 = '''
        <tr>
          <td class="tg-b7b8"></td>
          <td class="tg-b7b8"><img src="./img/db/{name}.png" alt="{name}" height=100 width=100></img></td>
          <td class="tg-p5oz">
            <p>Crosslinks: <a target="_blank" href="{ref_url}">{ref}</a> via <a target="_blank" href="http://journals.plos.org/plosone/article?id=10.1371/journal.pone.0073411">XLdb</a></p>
            <p>Structure: <a target="_blank" href="http://www.rcsb.org/pdb/explore.do?structureId={pdbcode}">X-ray</a></p>
          </td>
          <td class="tg-p5oz"><a href="http://www.beck.embl.de/downloads/{name}.zip">Download</a></td>
        </tr>
'''
templ2 = '''
        <tr>
          <td class="tg-yw4l"></td>
          <td class="tg-yw4l"><img src="./img/db/{name}.png" alt="{name}" height=100 width=100></img></td>
          <td class="tg-lqy6">
            <p>Crosslinks: <a target="_blank" href="{ref_url}">{ref}</a> via <a target="_blank" href="http://journals.plos.org/plosone/article?id=10.1371/journal.pone.0073411">XLdb</a></p>
            <p>Structure: <a target="_blank" href="http://www.rcsb.org/pdb/explore.do?structureId={pdbcode}">X-ray</a></p>
          </td>
          <td class="tg-lqy6"><a href="http://www.beck.embl.de/downloads/{name}.zip">Download</a></td>
        </tr>
'''

with open(filename, 'rU') as csvfile: #'U' is necessary, otherwise sometimes crashes with _csv.Error: new-line character seen in unquoted field - do you need to open the file in universal-newline mode?
    dialect = csv.Sniffer().sniff(csvfile.readline(), ['\t', ','])
    csvfile.seek(0)

    reader = csv.DictReader(csvfile, dialect=dialect)

    fieldnames = reader.fieldnames

    print fieldnames

    data = []

    for row in reader:
        # row = row.copy()
        row['Protein1'] = row['UniProt-Entry name 1']
        row['Protein2'] = row['UniProt-Entry name 2']



        row['AbsPos1'] = row['PDB amino-acid number 1']
        row['AbsPos2'] = row['PDB amino-acid number 2']

        #fix mistakes in PDB residue number (PDB number in wrong column)
        if row['Protein1'] in ('ODB2_HUMAN', 'PCCA_HUMAN', 'SET_HUMAN', 'MCCA_HUMAN', 'KCC2G_HUMAN', 'KCC2D_HUMAN', 'PYC_HUMAN', 'KCC2B_HUMAN', 'PPME1_HUMAN',
                            '2ABA_HUMAN', '2AAA_HUMAN', 'PP2AA_HUMAN', '2A5G_HUMAN', 'HSP7C_HUMAN', 'VIME_HUMAN', 'GRP78_HUMAN'):
            row['AbsPos1'] = row['UniProt amino-acid number 2'] 

        row['score'] = 100

        data.append(row)

    reader.fieldnames.append('Protein1')
    reader.fieldnames.append('Protein2')

    reader.fieldnames.append('AbsPos1')
    reader.fieldnames.append('AbsPos2')

    print 'Protein1' in fieldnames

    data = sorted(data, key=lambda x: x['PDB-ID'])

    templ_id = 1
    out_html = []
    for k, g in itertools.groupby(data, lambda x: x['PDB-ID']):
        json_content = {}
        json_content['data'] = []
        json_content['subunits'] = []

        g_rows = list(g)
        if g_rows[0]['PDB-ID'] in ('1wcm', '1hjo', '3dw8'): #skip those already in Xla DB
            continue

        # if g_rows[0]['PDB-ID'] != '3iuc':
        #     continue




        dirname = 'XLdb_Kahraman2013_{0}/xlinks'.format(g_rows[0]['PDB-ID'])
        cmd = 'mkdir -p {0}'.format(dirname)
        print cmd
        subprocess.call(cmd, shell=True)

        filename = '{0}/xlinks.csv'.format(dirname)
        print filename


        quoting = csv.QUOTE_NONE

        fieldnames = reader.fieldnames

        fieldnames = ['Protein1', 'Protein2', 'AbsPos1', 'AbsPos2', 'score']
        
        with open(filename, 'w') as nf:
            wr = csv.DictWriter(nf, fieldnames, quoting=quoting, extrasaction='ignore')
            wr.writeheader()
            # wr.writerow(dict((fn,fn) for fn in fieldnames)) #do not use wr.writeheader() to support also python 2.6
            wr.writerows(g_rows)

        all_names = []
        mapping = {}
        for row in g_rows:
            all_names.append(row['Protein1'])
            all_names.append(row['Protein2'])

            mapping[row['Protein1']] = [row['Protein1']]
            mapping[row['Protein2']] = [row['Protein2']]

        all_names = set(all_names)

        filename1 = 'xlinks/xlinks.csv'
        d_item = {
            'name': 'xlinks',
            'resource': [filename1],
            'mapping': mapping,
            'type': 'xquest',
            'active': True,
            'informed': False
        }
        json_content['data'].append(d_item)

        # subunits = defaultdict(dict)
        subunits = {}
        for name in all_names:
            subunits[name] = {
                'name': name,
                'chainIds': [],
                # "chainToComponent": {
                #     "N": "A34.5"
                # },
                # "color": [
                #     0.439215686,
                #     0.831372549,
                #     1.0,
                #     1.0
                # ],
                # "componentToChain": {},
                "domains": None,
                "sequence": "",
                "type": "component"
            }

        for row in g_rows:
            if row['Chain-ID 1'] not in subunits[row['Protein1']]['chainIds']:
                subunits[row['Protein1']]['chainIds'].append(row['Chain-ID 1'])

            if row['Chain-ID 2'] not in subunits[row['Protein2']]['chainIds']:
                subunits[row['Protein2']]['chainIds'].append(row['Chain-ID 2'])

        if g_rows[0]['PDB-ID'] == '1aon':
            subunits['CH10_ECOLI']['chainIds'] = ['O', 'P', 'Q', 'R', 'S', 'T', 'U']
        if g_rows[0]['PDB-ID'] == '1cmi':
            subunits['DYL1_HUMAN']['chainIds'] = ['A', 'B']
        if g_rows[0]['PDB-ID'] == '1efu':
            subunits['EFTS_ECOLI']['chainIds'] = ['B', 'D']
        if g_rows[0]['PDB-ID'] == '2c44':
            subunits['TNAA_ECOLI']['chainIds'] = ['A', 'B', 'C', 'D']
        if g_rows[0]['PDB-ID'] == '2e50':
            subunits['SET_HUMAN']['chainIds'] = ['A', 'B']
        if g_rows[0]['PDB-ID'] == '2g50':
            subunits['KPYM_RABIT']['chainIds'] = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        if g_rows[0]['PDB-ID'] == '3iuc':
            subunits['GRP78_HUMAN']['chainIds'] = ['A', 'C']
        color_i = 0
        for subunitnam, subunit in subunits.iteritems():
            subunit['selection'] = ':' + ','.join(['.'+c for c in subunit['chainIds']])

            try:
                subunit['color'] = COLORS[color_i]
            except IndexError:
                color_i = 0
                subunit['color'] = COLORS[color_i]
            json_content['subunits'].append(subunit)

            color_i = color_i + 1

        if g_rows[0]['PDB-ID'] == '1cmi':
            json_content['subunits'].append({
                    'name': 'Nos1',
                    'chainIds': ['C', 'D'],
                    "color": COLORS[color_i],
                    "domains": None,
                    "sequence": "",
                    "type": "component"
                    }
                )
        if g_rows[0]['PDB-ID'] == '1efu':
            json_content['subunits'].append({
                    'name': 'tufB',
                    'chainIds': ['A', 'C'],
                    "color": COLORS[color_i],
                    "domains": None,
                    "sequence": "",
                    "type": "component"
                    }
                )
        dirname = 'XLdb_Kahraman2013_{0}'.format(g_rows[0]['PDB-ID'])
        with open('{0}/{1}.json'.format(dirname, g_rows[0]['PDB-ID']),'w') as f:
            f.write(json.dumps(json_content,\
                    sort_keys=True,\
                    indent=4,\
                    separators=(',', ': ')))
            f.close()
            print '{0}/{1}.json'.format(dirname, g_rows[0]['PDB-ID'])

        with open('{0}/README.txt'.format(dirname), 'w') as f:
            f.write('Cross-links:\n')
            f.write('{0}\n'.format(g_rows[0]['Reference']))
            f.write('{0}\n'.format(g_rows[0]['Weblink to publication']))
            f.write('\n')
            f.write('Cross-link data downloaded from:\n')
            f.write('XLdb, Kahraman et al. 2013\n')
            f.write('http://journals.plos.org/plosone/article?id=10.1371/journal.pone.0073411\n')
            
        # subprocess.call('curl -O http://www.rcsb.org/pdb/files/{0}.pdb'.format(g_rows[0]['PDB-ID']), shell=True, cwd=dirname)

        if templ_id == 1:
            templ = templ1
        else:
            templ = templ2

        if g_rows[0]['PDB-ID'] in ('1jm7',):
            templ = templ.replace('X-ray', 'NMR')


        re_m = re.search('(^.*et al.|Mak).*(\(20..\)).*', g_rows[0]['Reference'])
        reference = re_m.groups()[0] + ' ' + re_m.groups()[1][1:-1]

        out_html.append(templ.format(
                name=dirname,
                ref_url=g_rows[0]['Weblink to publication'],
                ref=reference,
                pdbcode=g_rows[0]['PDB-ID']

            ))

        templ_id = templ_id + 1
        if templ_id == 3:
            templ_id = 1

    with open('html_table.html', 'w') as html:
        html.write(''.join(out_html))
