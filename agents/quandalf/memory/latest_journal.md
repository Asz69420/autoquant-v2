# Quandalf Journal — Cycle 4

- ts_iso: 2026-03-11T07:06:58.682284+00:00
- mode: explore
- lane: ETH / 4h
- research_direction: explore_new

## Decision Summary
{
  "promote": 0,
  "refine": 0,
  "abort": 0,
  "zero_trade": 0
}

## Diagnosis Breakdown
{
  "bad idea": 3
}

## What Worked
- none

## What Failed
- QD-20260311-C004-ETH-VALUE-RECOVERY-SCALEIN-v1: pending: no backtest outcome recorded yet
- QD-20260311-C004-BTC-ASYMMETRIC-TREND-PERSISTENCE-v1: pending: no backtest outcome recorded yet
- QD-20260311-C004-TAO-RETEST-HOLD-DERISK-v1: pending: no backtest outcome recorded yet

## Why It Failed
- QD-20260311-C004-ETH-VALUE-RECOVERY-SCALEIN-v1: bad idea
- QD-20260311-C004-BTC-ASYMMETRIC-TREND-PERSISTENCE-v1: bad idea
- QD-20260311-C004-TAO-RETEST-HOLD-DERISK-v1: bad idea
- QD-20260311-C380-SOL-RANGE-FAILURE-REACCEPTANCE-v1: too sparse
- QD-20260311-C380-ETH-TREND-RESET-CONTINUATION-v1: too sparse
- QD-20260311-C380-TAO-COMPRESSION-FAKEOUT-REEXPANSION-v1: too sparse

## Iterate Next
- decision QD-20260311-C380-SOL-RANGE-FAILURE-REACCEPTANCE-v1: This SOL range-failure reacceptance branch produced 0 trades on valid data. Even with a broader failure-and-reacceptance structure, the mechanism still required too much staged alignment to engage on the lane, so another pass would just cosmetically loosen a dead grammar.
- decision QD-20260311-C380-ETH-TREND-RESET-CONTINUATION-v1: The ETH deeper-reset continuation branch also hard-skipped with zero trades. The reset zone plus reclaim plus participation filter remained structurally too restrictive, which makes this a density failure rather than a refinable near-miss.
- decision QD-20260311-C380-TAO-COMPRESSION-FAKEOUT-REEXPANSION-v1: This TAO compression fakeout branch also never generated a valid-data trade. Compression, fakeout, rejection, and directional handoff still overconstrained entry density, so it should be abandoned rather than diluted further.
