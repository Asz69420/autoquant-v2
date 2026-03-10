# Quandalf Market Intelligence Design

## Objective
Give Quandalf richer external market awareness without flooding active context or letting noisy media dominate strategy design.

## Design Principles
- facts first, vibes second
- DB/state for exact snapshots
- shared memory only for promoted insights
- private notes allowed for draft thinking, not canonical truth
- every source must map to a trading use-case or be discarded

## Source Ladder
### Tier A — deterministic market state
Highest priority, structured first.
- liquidations
- funding
- open interest
- market-maker/positioning signals
- regime scans
- event timestamps

### Tier B — event context
- news catalysts
- exchange incidents
- macro/economic events
- listing/delisting changes

### Tier C — research media
- YouTube
- TradingView
- transcripts
- curated external research

## Promotion Flow
1. ingest raw source
2. normalize metadata
3. classify by source category
4. reject obvious noise
5. store hard facts in DB/state if structured
6. create short summary if strategically relevant
7. promote only reusable intelligence into shared memory
8. leave speculative residue in Quandalf private memory until proven useful

## Shared Memory Destinations
- `memory/shared/regimes/` for regime-changing observations
- `memory/shared/lessons/` for reusable market or strategy lessons
- `memory/shared/strategy_families/` for family-level suitability insights
- `memory/shared/handoffs/` for cross-agent urgent context

## Noise Rules
Discard if it is:
- generic commentary
- duplicated without new implication
- unconfirmed rumor
- not connected to regime, edge, risk, or execution
- not testable or decision-useful

## What This Enables
Quandalf should eventually be able to answer:
- what changed in market structure recently?
- which external conditions make this family more or less suitable?
- which assets are showing unusual liquidation or funding behavior?
- which research/media ideas are worth converting into strategy tests?

## Implementation Order
1. config complete
2. source registry
3. normalized storage for structured external facts
4. promotion policy hooks
5. retrieval rules in briefing/build-order flow
