import json
d = json.load(open("agents/quandalf/memory/briefing_packet.json"))
for k, v in d.items():
    size = len(json.dumps(v))
    count = ""
    if isinstance(v, (list, dict)):
        count = f" ({len(v)} items)"
    print(f"{k}: {size:,} chars{count}")
print(f"\nTOTAL: {len(json.dumps(d)):,} chars")
# Estimate tokens (~4 chars per token)
print(f"EST TOKENS: ~{len(json.dumps(d))//4:,}")
