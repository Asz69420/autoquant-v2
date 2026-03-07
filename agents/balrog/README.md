# Balrog — The Firewall

Balrog is NOT an LLM agent. He is a deterministic validation script.
He does not think. He does not reason. He checks rules and returns pass/fail.

## Files
- rules.json — the immutable rule set (only Asz modifies)
- README.md — this file
- memory/ — status tracking only

## What Balrog Validates
1. External input sanitization (prompt injection detection)
2. JSON schema validation on all pipeline artifacts
3. Agent boundary enforcement (who can write what)
4. Circuit breaker thresholds (DD, PF, position limits)
5. QScore gates (pass/promote thresholds)

## Security Model
- No other agent can modify rules.json
- Balrog's workspace should be read-only to all other agents
- All blocked actions are logged to event_log with full context
- Balrog never makes exceptions — rules are binary
