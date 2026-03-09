import sys
from pathlib import Path

ROOT = Path(r"C:/Users/Clamps/.openclaw/workspace-oragorn")
sys.path.insert(0, str(ROOT / "scripts"))
from text_io import read_text_best_effort

p = ROOT / "data" / "state" / "_decode_smoke_bad_bytes.txt"
p.write_bytes(b"hello\x96world")
print(read_text_best_effort(p))
p.unlink()
