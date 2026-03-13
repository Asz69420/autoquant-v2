# Quandalf Journal — Cycle 156

- ts_iso: 2026-03-13T05:43:01.720117+00:00
- mode: explore
- lane: TAO / 4h
- research_direction: explore_new

## My Current Decision Summary
{
  "pass": 3,
  "refine": 0,
  "abort": 0,
  "zero_trade": 0
}

## My Current Diagnosis Breakdown
{
  "bad idea": 3
}

## Rolling Last 5 Cycles
{
  "window_size": 5,
  "totals": {
    "cycles_considered": 5,
    "pass": 12,
    "refine": 0,
    "abort": 3,
    "zero_trade": 0,
    "strategies": 15,
    "queue_rows": 16,
    "queue_rows_decided": 16,
    "saved_results": 15
  },
  "diagnosis_breakdown": {
    "bad idea": 15
  },
  "assets_touched": [
    "BTC",
    "ETH",
    "SOL",
    "TAO"
  ],
  "timeframes_touched": [
    "1h",
    "4h"
  ],
  "cycle_ids": [
    152,
    153,
    154,
    155,
    156
  ]
}

## What Worked
- On QD-20260313-C156-TAO-BREAKOUT-HOLD-v1, refine: PASS with QS 1.01, PF 1.35, DD 33.9%, trades 85
- On QD-20260313-C156-TAO-EMA-PULLBACK-v1, refine: PASS with QS 0.93, PF 1.29, DD 35.9%, trades 80
- On QD-20260313-C156-TAO-RANGE-RECLAIM-v1, refine: PASS with QS 0.59, PF 0.90, DD 31.1%, trades 77

## Awaiting Evidence
- none

## What Failed
- none

## Why I Judged It That Way
- On QD-20260313-C156-TAO-BREAKOUT-HOLD-v1, bad idea
- On QD-20260313-C156-TAO-EMA-PULLBACK-v1, bad idea
- On QD-20260313-C156-TAO-RANGE-RECLAIM-v1, bad idea

## What I Would Improve Next
- On QD-20260313-C156-TAO-BREAKOUT-HOLD-v1, pass: PASS with QS 1.01, PF 1.35, DD 33.9%, trades 85
- On QD-20260313-C156-TAO-EMA-PULLBACK-v1, pass: PASS with QS 0.93, PF 1.29, DD 35.9%, trades 80
- On QD-20260313-C156-TAO-RANGE-RECLAIM-v1, pass: PASS with QS 0.59, PF 0.90, DD 31.1%, trades 77

## What Still Needs Testing
- none

## Strategy-by-Strategy Reasons
- QD-20260313-C156-TAO-BREAKOUT-HOLD-v1: asset=TAO | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: breakout continuation after hold above broken structure with volatility expansion
  thesis: breakout continuation after hold above broken structure with volatility expansion
  train: QS 1.009 | Sharpe 0 | PF 1.348 | DD 33.88% | Trades 85
  why: pass: PASS with QS 1.01, PF 1.35, DD 33.9%, trades 85
  evidence: rq_87c00e551635=pass (Deterministic closure inherited pass for queue row rq_87c00e551635 from strategy outcome QD-20260313-C156-TAO-BREAKOUT-HOLD-v1.)
  evidence: rq_e7d5fe2c7bfe=pass (Deterministic closure inherited pass for queue row rq_e7d5fe2c7bfe from strategy outcome QD-20260313-C156-TAO-BREAKOUT-HOLD-v1.)
- QD-20260313-C156-TAO-EMA-PULLBACK-v1: asset=TAO | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: trend pullback continuation after value reclaim
  thesis: trend pullback continuation after value reclaim
  train: QS 0.93 | Sharpe 0 | PF 1.289 | DD 35.94% | Trades 80
  why: pass: PASS with QS 0.93, PF 1.29, DD 35.9%, trades 80
  evidence: rq_bfd6f394b91e=pass (Deterministic closure inherited pass for queue row rq_bfd6f394b91e from strategy outcome QD-20260313-C156-TAO-EMA-PULLBACK-v1.)
- QD-20260313-C156-TAO-RANGE-RECLAIM-v1: asset=TAO | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: range reclaim continuation after false breakdown and value recovery
  thesis: range reclaim continuation after false breakdown and value recovery
  train: QS 0.588 | Sharpe 0 | PF 0.899 | DD 31.08% | Trades 77
  why: pass: PASS with QS 0.59, PF 0.90, DD 31.1%, trades 77
  evidence: rq_c7ecdcffde18=pass (Deterministic closure inherited pass for queue row rq_c7ecdcffde18 from strategy outcome QD-20260313-C156-TAO-RANGE-RECLAIM-v1.)
