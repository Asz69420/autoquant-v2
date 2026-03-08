import json
from pathlib import Path

p = Path(r"C:\Users\Clamps\.openclaw\openclaw.json")
obj = json.loads(p.read_text(encoding="utf-8"))

obj["channels"]["telegram"]["accounts"]["default"]["botToken"] = "8266129328:AAGiu1YMInKw3xDXaGrmKDu_7Aj93bqFTHs"
obj["channels"]["telegram"]["accounts"]["oragorn"]["botToken"] = "8351662972:AAH1jnlWLfOZq7NRoiboGR_FRnWHMe42IK0"

p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
print("tokens_updated")
