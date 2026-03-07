# Balrog — Goals
## Primary Mission
Immutable security firewall. Three functions:
1. Input sanitization — scan ALL external data for prompt injection
2. Schema validation — every artifact between pipeline steps must validate
3. Agent boundary enforcement — block agents acting outside scope
## Hard Rules
- rules.json is immutable from inside the system
- Only Asz can modify firewall rules
- All blocked actions logged with full context
- Deterministic ONLY — no LLM reasoning ever
- QScore gates enforced: pass >= 1.0, promote >= 3.0
