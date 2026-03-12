# Quandalf Journal — Cycle 95

- ts_iso: 2026-03-12T12:44:56.489783+00:00
- mode: explore
- lane: SOL / 4h
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
    "abort": 12,
    "zero_trade": 0,
    "strategies": 12,
    "queue_rows": 12,
    "queue_rows_decided": 12,
    "saved_results": 12
  },
  "diagnosis_breakdown": {
    "bad idea": 12
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
    91,
    92,
    93,
    94,
    95
  ]
}

## What Worked
- On QD-20260312-C95-SOL-BREAKOUT-HOLD-v1, refine: PASS with QS 0.71, PF 1.01, DD 30.1%, trades 109
- On QD-20260312-C95-SOL-EMA-PULLBACK-v1, refine: PASS with QS 0.80, PF 1.05, DD 24.5%, trades 107
- On QD-20260312-C95-SOL-RANGE-RECLAIM-v1, refine: PASS with QS 0.65, PF 0.94, DD 28.4%, trades 120

## Awaiting Evidence
- none

## What Failed
- none

## Why I Judged It That Way
- On QD-20260312-C95-SOL-BREAKOUT-HOLD-v1, bad idea
- On QD-20260312-C95-SOL-EMA-PULLBACK-v1, bad idea
- On QD-20260312-C95-SOL-RANGE-RECLAIM-v1, bad idea

## What I Would Improve Next
- On QD-20260312-C95-SOL-BREAKOUT-HOLD-v1, refine: PASS with QS 0.71, PF 1.01, DD 30.1%, trades 109
- On QD-20260312-C95-SOL-EMA-PULLBACK-v1, refine: PASS with QS 0.80, PF 1.05, DD 24.5%, trades 107
- On QD-20260312-C95-SOL-RANGE-RECLAIM-v1, refine: PASS with QS 0.65, PF 0.94, DD 28.4%, trades 120

## What Still Needs Testing
- none

## Strategy-by-Strategy Reasons
- QD-20260312-C95-SOL-BREAKOUT-HOLD-v1: asset=SOL | timeframe=4h | decision=abort | diagnosis=bad idea
  mechanism: breakout continuation after hold above broken structure with volatility expansion
  thesis: breakout continuation after hold above broken structure with volatility expansion
  train: QS 0.706 | Sharpe 0 | PF 1.007 | DD 30.13% | Trades 109
  why: refine: PASS with QS 0.71, PF 1.01, DD 30.1%, trades 109
  evidence: rq_c90dea16a539=abort (Deterministic closure inherited abort for queue row rq_c90dea16a539 from strategy outcome QD-20260312-C95-SOL-BREAKOUT-HOLD-v1.)
- QD-20260312-C95-SOL-EMA-PULLBACK-v1: asset=SOL | timeframe=4h | decision=abort | diagnosis=bad idea
  mechanism: trend pullback continuation after value reclaim
  thesis: trend pullback continuation after value reclaim
  train: QS 0.802 | Sharpe 0 | PF 1.047 | DD 24.53% | Trades 107
  why: refine: PASS with QS 0.80, PF 1.05, DD 24.5%, trades 107
  evidence: rq_db9ec32c00b0=abort (Deterministic closure inherited abort for queue row rq_db9ec32c00b0 from strategy outcome QD-20260312-C95-SOL-EMA-PULLBACK-v1.)
- QD-20260312-C95-SOL-RANGE-RECLAIM-v1: asset=SOL | timeframe=4h | decision=abort | diagnosis=bad idea
  mechanism: range reclaim continuation after false breakdown and value recovery
  thesis: range reclaim continuation after false breakdown and value recovery
  train: QS 0.654 | Sharpe 0 | PF 0.938 | DD 28.4% | Trades 120
  why: refine: PASS with QS 0.65, PF 0.94, DD 28.4%, trades 120
  evidence: rq_20fadd46ac83=abort (Deterministic closure inherited abort for queue row rq_20fadd46ac83 from strategy outcome QD-20260312-C95-SOL-RANGE-RECLAIM-v1.)
