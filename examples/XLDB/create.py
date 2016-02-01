import csv
import itertools
import subprocess
from collections import defaultdict
import json

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

        row['score'] = 100

        data.append(row)

    reader.fieldnames.append('Protein1')
    reader.fieldnames.append('Protein2')

    reader.fieldnames.append('AbsPos1')
    reader.fieldnames.append('AbsPos2')

    print 'Protein1' in fieldnames

    data = sorted(data, key=lambda x: x['PDB-ID'])

    for k, g in itertools.groupby(data, lambda x: x['PDB-ID']):

        json_content = {}
        json_content['data'] = []
        json_content['subunits'] = []

        g_rows = list(g)
        dirname = 'XLdb/{0}/xlinks'.format(g_rows[0]['PDB-ID'])
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
                "componentToChain": {},
                "domains": None,
                "sequence": "",
                "type": "component"
            }

        for row in g_rows:
            if row['Chain-ID 1'] not in subunits[row['Protein1']]['chainIds']:
                subunits[row['Protein1']]['chainIds'].append(row['Chain-ID 1'])

            if row['Chain-ID 2'] not in subunits[row['Protein2']]['chainIds']:
                subunits[row['Protein2']]['chainIds'].append(row['Chain-ID 2'])

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

        dirname = 'XLdb/{0}'.format(g_rows[0]['PDB-ID'])
        with open('{0}/{1}.json'.format(dirname, g_rows[0]['PDB-ID']),'w') as f:
            f.write(json.dumps(json_content,\
                    sort_keys=True,\
                    indent=4,\
                    separators=(',', ': ')))
            f.close()
            print '{0}/{1}.json'.format(dirname, g_rows[0]['PDB-ID'])

        # subprocess.call('curl -O http://www.rcsb.org/pdb/files/{0}.pdb'.format(g_rows[0]['PDB-ID']), shell=True, cwd=dirname)
