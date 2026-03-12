# Quandalf Journal — Cycle 92

- ts_iso: 2026-03-12T11:10:30.246178+00:00
- mode: explore
- lane: ETH / 1h
- research_direction: explore_new

## My Current Decision Summary
{
  "pass": 0,
  "refine": 0,
  "abort": 3,
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
    "pass": 0,
    "refine": 0,
    "abort": 11,
    "zero_trade": 1,
    "strategies": 11,
    "queue_rows": 27,
    "queue_rows_decided": 27,
    "saved_results": 18
  },
  "diagnosis_breakdown": {
    "bad idea": 8,
    "too sparse": 3
  },
  "assets_touched": [
    "AXS",
    "BTC",
    "ETH",
    "TAO"
  ],
  "timeframes_touched": [
    "1h",
    "4h"
  ],
  "cycle_ids": [
    88,
    89,
    90,
    91,
    92
  ]
}

## What Worked
- On QD-20260312-C92-TAO-BREAKOUT-HOLD-v1, refine: PASS with QS 0.94, PF 1.28, DD 33.9%, trades 84
- On QD-20260312-C92-TAO-EMA-PULLBACK-v1, refine: PASS with QS 0.84, PF 1.20, DD 35.9%, trades 78
- On QD-20260312-C92-TAO-RANGE-RECLAIM-v1, refine: PASS with QS 0.64, PF 0.95, DD 31.1%, trades 76

## Awaiting Evidence
- none

## What Failed
- none

## Why I Judged It That Way
- On QD-20260312-C92-TAO-BREAKOUT-HOLD-v1, bad idea
- On QD-20260312-C92-TAO-EMA-PULLBACK-v1, bad idea
- On QD-20260312-C92-TAO-RANGE-RECLAIM-v1, bad idea

## What I Would Improve Next
- On QD-20260312-C92-TAO-BREAKOUT-HOLD-v1, refine: PASS with QS 0.94, PF 1.28, DD 33.9%, trades 84
- On QD-20260312-C92-TAO-EMA-PULLBACK-v1, refine: PASS with QS 0.84, PF 1.20, DD 35.9%, trades 78
- On QD-20260312-C92-TAO-RANGE-RECLAIM-v1, refine: PASS with QS 0.64, PF 0.95, DD 31.1%, trades 76

## What Still Needs Testing
- none

## Strategy-by-Strategy Reasons
- QD-20260312-C92-TAO-BREAKOUT-HOLD-v1: asset=TAO | timeframe=4h | decision=abort | diagnosis=bad idea
  mechanism: breakout continuation after hold above broken structure with volatility expansion
  thesis: breakout continuation after hold above broken structure with volatility expansion
  train: QS 0.944 | Sharpe 0 | PF 1.283 | DD 33.88% | Trades 84
  why: refine: PASS with QS 0.94, PF 1.28, DD 33.9%, trades 84
  evidence: rq_4626fe468328=abort (Deterministic closure inherited abort for queue row rq_4626fe468328 from strategy outcome QD-20260312-C92-TAO-BREAKOUT-HOLD-v1.)
- QD-20260312-C92-TAO-EMA-PULLBACK-v1: asset=TAO | timeframe=4h | decision=abort | diagnosis=bad idea
  mechanism: trend pullback continuation after value reclaim
  thesis: trend pullback continuation after value reclaim
  train: QS 0.843 | Sharpe 0 | PF 1.202 | DD 35.94% | Trades 78
  why: refine: PASS with QS 0.84, PF 1.20, DD 35.9%, trades 78
  evidence: rq_f5871c046796=abort (Deterministic closure inherited abort for queue row rq_f5871c046796 from strategy outcome QD-20260312-C92-TAO-EMA-PULLBACK-v1.)
- QD-20260312-C92-TAO-RANGE-RECLAIM-v1: asset=TAO | timeframe=4h | decision=abort | diagnosis=bad idea
  mechanism: range reclaim continuation after false breakdown and value recovery
  thesis: range reclaim continuation after false breakdown and value recovery
  train: QS 0.642 | Sharpe 0 | PF 0.953 | DD 31.08% | Trades 76
  why: refine: PASS with QS 0.64, PF 0.95, DD 31.1%, trades 76
  evidence: rq_fbeaa895ece2=abort (Deterministic closure inherited abort for queue row rq_fbeaa895ece2 from strategy outcome QD-20260312-C92-TAO-RANGE-RECLAIM-v1.)
