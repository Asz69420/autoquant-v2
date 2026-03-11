# Quandalf Learning Loop

## Purpose
Separate Quandalf's internal learning artifact from the human daily journal.

## Model
- **Internal learning loop** = structured, machine-usable, promotion-ready
- **Daily journal DM** = human-facing summary for Asz

## Source of truth
- `agents/quandalf/memory/latest_journal.md`

## Structured outputs
- `data/state/quandalf_learning_loop.json`
- `agents/quandalf/memory/latest_learning_loop.json`

## Why this is better
- preserves nuanced learning for iteration
- supports promotion into shared memory
- reduces dependence on a human-readable markdown journal as the only memory object
- scales better as strategy reasoning becomes more complex

## Expected use
Quandalf should learn in terms of:
- thesis
- what worked
- what failed
- why it failed
- what to iterate next
- what to abandon
- what to bench for later
- regime/family/indicator/management notes

The Telegram journal should be treated as a rendered summary, not the primary memory artifact.
