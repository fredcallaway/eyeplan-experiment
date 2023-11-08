import os
import json
import pandas as pd

version = sys.argv[1]
# wid = 'fred'

trials = []
for file in os.listdir(f"data/exp/{version}/"):
    with open(f"data/exp/{version}/{file}") as f:
        data = json.load(f)
        wid = file.rsplit('-', 1)[1].replace('.json', '')
        for i, t in enumerate(data["trial_data"]):
            t["wid"] = wid
            t["trial_index"] = i
            trials.append(t)

os.makedirs(f'data/processed/{version}/', exist_ok=True)
with open(f'data/processed/{version}/trials.json', 'w') as f:
    json.dump(trials, f)
