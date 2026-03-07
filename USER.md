# USER.md — Asz

## Identity
- User name: Asz
- Timezone: Australia/Brisbane
- Role: Project lead, R&D strategy, execution oversight

## How Asz Works
- Visual learner, non-coder, highly creative
- Communicates via Telegram DMs
- Never downloads files — all work goes through agents via code blocks
- Wants to see results and dashboards, not implementation details
- Prefers ONE clean solution over ten iterations
- Gets frustrated by circular debugging and wasted tokens
- Speech-to-text aliases for Frodex: "throw decks", "throwx", "throw deck"## Hard Rules
1. Never store secrets (keys/tokens/wallets/credentials) in chat or files.
2. Never overwrite/delete existing files without explicit approval.
3. Big generated outputs belong in artifacts/ or data/ — not git-tracked.
4. Follow schema contracts in schemas/ when creating artifacts.
5. If a behavior change is agreed upon, codify it in a config file immediately. Don't defer.
6. Treat committed config files as source of truth, not agent memory.

## Reporting Contract
- Default for checks/audits/status: plain-language verdict + one short context line.
- No raw log lines, file paths, timestamps, or IDs unless explicitly asked.
- Keep Telegram replies brief (1-3 sentences for routine updates).
- If uncertain, say so in one line and give one concrete next action.

## Noise Gate
- For routine cron completions with no state change: suppress notification.
- Only notify Asz when something actually changed, needs action, failed, or matters.
- If uncertain whether an event is meaningful, send one concise update.
