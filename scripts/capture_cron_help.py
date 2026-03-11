#!/usr/bin/env python3
import subprocess, pathlib
out = subprocess.run(['openclaw','cron','add','--help'], capture_output=True, text=True)
text = (out.stdout or '') + '\n' + (out.stderr or '')
path = pathlib.Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\cron_add_help_capture.txt')
path.write_text(text, encoding='utf-8')
print(path)