import json
from pathlib import Path

PATH = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn\agents\quandalf\memory\strategy_status.json")
data = json.loads(PATH.read_text(encoding="utf-8"))

print(f"Top-level keys: {list(data.keys())}")
for k, v in data.items():
    size = len(json.dumps(v))
    if isinstance(v, list):
        print(f"  {k}: list[{len(v)}] = {size:,} chars")
        if v:
            print(f"    sample entry size: {len(json.dumps(v[0])):,} chars")
            print(f"    sample keys: {list(v[0].keys()) if isinstance(v[0], dict) else 'not dict'}")
    elif isinstance(v, dict):
        print(f"  {k}: dict[{len(v)}] = {size:,} chars")
    else:
        print(f"  {k}: {type(v).__name__} = {size:,} chars")
