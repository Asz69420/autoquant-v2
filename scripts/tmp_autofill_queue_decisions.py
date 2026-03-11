import json
from pathlib import Path
import ensure_quandalf_decisions_complete as eq

reflection = eq.load_json(eq.REFLECTION, {})
decisions = eq.load_json(eq.DECISIONS, {})
changed = eq.autofill_queue_decisions_from_strategy(reflection, decisions)
code, payload, stdout, stderr = eq.run_validator()
print(json.dumps({"changed": changed, "validator": payload, "code": code}, indent=2))
