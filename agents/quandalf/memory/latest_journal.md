# Quandalf Journal — Cycle 96

- ts_iso: 2026-03-12T21:39:29.240702+00:00
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
    "pass": 3,
    "refine": 0,
    "abort": 12,
    "zero_trade": 0,
    "strategies": 15,
    "queue_rows": 15,
    "queue_rows_decided": 15,
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
    "4h"
  ],
  "cycle_ids": [
    92,
    93,
    94,
    95,
    96
  ]
}

## What Worked
- On QD-20260312-C96-TAO-EMA-PULLBACK-v1, refine: PASS with QS 0.84, PF 1.20, DD 35.9%, trades 78
- On QD-20260312-C96-TAO-RANGE-RECLAIM-v1, refine: PASS with QS 0.64, PF 0.95, DD 31.1%, trades 76
- On QD-20260312-C96-TAO-BREAKOUT-HOLD-v1, refine: PASS with QS 0.94, PF 1.28, DD 33.9%, trades 84

## Awaiting Evidence
- none

## What Failed
- none

## Why I Judged It That Way
- On QD-20260312-C96-TAO-EMA-PULLBACK-v1, bad idea
- On QD-20260312-C96-TAO-RANGE-RECLAIM-v1, bad idea
- On QD-20260312-C96-TAO-BREAKOUT-HOLD-v1, bad idea

## What I Would Improve Next
- On QD-20260312-C96-TAO-EMA-PULLBACK-v1, pass: PASS with QS 0.84, PF 1.20, DD 35.9%, trades 78
- On QD-20260312-C96-TAO-RANGE-RECLAIM-v1, pass: PASS with QS 0.64, PF 0.95, DD 31.1%, trades 76
- On QD-20260312-C96-TAO-BREAKOUT-HOLD-v1, pass: PASS with QS 0.94, PF 1.28, DD 33.9%, trades 84

## What Still Needs Testing
- none

## Strategy-by-Strategy Reasons
- QD-20260312-C96-TAO-EMA-PULLBACK-v1: asset=TAO | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: trend pullback continuation after value reclaim
  thesis: trend pullback continuation after value reclaim
  train: QS 0.843 | Sharpe 0 | PF 1.202 | DD 35.94% | Trades 78
  why: pass: PASS with QS 0.84, PF 1.20, DD 35.9%, trades 78
  evidence: rq_819645545e53=pass (Deterministic closure inherited pass for queue row rq_819645545e53 from strategy outcome QD-20260312-C96-TAO-EMA-PULLBACK-v1.)
- QD-20260312-C96-TAO-RANGE-RECLAIM-v1: asset=TAO | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: range reclaim continuation after false breakdown and value recovery
  thesis: range reclaim continuation after false breakdown and value recovery
  train: QS 0.642 | Sharpe 0 | PF 0.953 | DD 31.08% | Trades 76
  why: pass: PASS with QS 0.64, PF 0.95, DD 31.1%, trades 76
  evidence: rq_c249f538b91c=pass (Deterministic closure inherited pass for queue row rq_c249f538b91c from strategy outcome QD-20260312-C96-TAO-RANGE-RECLAIM-v1.)
- QD-20260312-C96-TAO-BREAKOUT-HOLD-v1: asset=TAO | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: breakout continuation after hold above broken structure with volatility expansion
  thesis: breakout continuation after hold above broken structure with volatility expansion
  train: QS 0.944 | Sharpe 0 | PF 1.283 | DD 33.88% | Trades 84
  why: pass: PASS with QS 0.94, PF 1.28, DD 33.9%, trades 84
  evidence: rq_12485e40c97d=pass (Deterministic closure inherited pass for queue row rq_12485e40c97d from strategy outcome QD-20260312-C96-TAO-BREAKOUT-HOLD-v1.)
