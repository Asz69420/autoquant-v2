import importlib.util, pathlib, json, sys
root = pathlib.Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
sys.path.insert(0, str(root / 'scripts'))
path = root / 'scripts' / 'cycle-postprocess.py'
spec = importlib.util.spec_from_file_location('cycle_postprocess_mod', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
rows = []
card, metrics = mod.build_log_card(64, rows, 13.0, 0)
print(json.dumps({"card": card, "metrics": metrics}, indent=2))
