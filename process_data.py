import os
import sys
import json
import pandas as pd
import subprocess

from config import VERSION

if len(sys.argv) > 1:
    VERSION = sys.argv[1]

def shorten_wid(wid):
    return wid.split('_')[-1]

trials = []
used_wids = set()
os.makedirs(f'data/processed/{VERSION}/', exist_ok=True)

participants = []

for file in sorted(os.listdir(f"data/exp/{VERSION}/")):
    if 'test' in file:
        continue
    wid = file.replace('.json', '')
    short_wid = wid.split('_')[-1]
    assert short_wid not in used_wids
    used_wids.add(short_wid)
    # wid = uid.rsplit('-', 1)[1]

    # experimental data
    fn = f"data/exp/{VERSION}/{file}"
    print(fn)
    with open(fn) as f:
        data = json.load(f)
    data.keys()
    wid
    for i, t in enumerate(data["trial_data"]):
        t["wid"] = short_wid
        t["trial_index"] = i
        trials.append(t)

    # eyelink data
    edf = f'data/eyelink/{wid}/raw.edf'
    assert os.path.isfile(edf)
    dest = f'data/eyelink/{wid}/samples.asc'
    if os.path.isfile(edf) and not os.path.isfile(dest):
        cmd = f'edf2asc {edf} {dest}'
        output = subprocess.getoutput(cmd)
        if 'Converted successfully' not in output:
            print(f'Error parsing {edf}', '-'*80, output, '-'*80, sep='\n')


with open(f'data/processed/{VERSION}/trials.json', 'w') as f:
    json.dump(trials, f)


