#!/usr/bin/env python3
import json
import sys

print(json.dumps({
  "status": "disabled",
  "reason": "research cards now come from cycle-postprocess.py --send-card-only so both research and reflection share one truthful metrics source"
}))
sys.exit(0)
