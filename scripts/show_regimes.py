import json
d = json.load(open("data/state/regime_summary.json"))
for k, v in d["pairs"].items():
    print(f"{k}: {v['current']} ({v['confidence']}%)")
