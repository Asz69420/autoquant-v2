# Quandalf Journal — Cycle 141

- ts_iso: 2026-03-13T03:41:13.310709+00:00
- mode: explore
- lane: ETH / 4h
- research_direction: explore_new

## My Current Decision Summary
{
  "pass": 2,
  "refine": 0,
  "abort": 1,
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
    "pass": 11,
    "refine": 0,
    "abort": 4,
    "zero_trade": 0,
    "strategies": 15,
    "queue_rows": 16,
    "queue_rows_decided": 16,
    "saved_results": 16
  },
  "diagnosis_breakdown": {
    "bad idea": 15
  },
  "assets_touched": [
    "DOGE",
    "ETH",
    "SOL",
    "TAO"
  ],
  "timeframes_touched": [
    "1h",
    "4h"
  ],
  "cycle_ids": [
    137,
    138,
    139,
    140,
    141
  ]
}

## What Worked
- On QD-20260313-C141-ETH-EMA-PULLBACK-v1, refine: PASS with QS 0.93, PF 1.13, DD 20.1%, trades 76
- On QD-20260313-C141-ETH-BREAKOUT-HOLD-v1, refine: PASS with QS 0.85, PF 1.06, DD 20.9%, trades 75

## Awaiting Evidence
- none

## What Failed
- On QD-20260313-C141-ETH-RANGE-RECLAIM-v1, abort: fail with QS 0.38, PF 0.70, DD 31.6%, trades 83

## Why I Judged It That Way
- On QD-20260313-C141-ETH-EMA-PULLBACK-v1, bad idea
- On QD-20260313-C141-ETH-RANGE-RECLAIM-v1, bad idea
- On QD-20260313-C141-ETH-BREAKOUT-HOLD-v1, bad idea

## What I Would Improve Next
- On QD-20260313-C141-ETH-EMA-PULLBACK-v1, pass: PASS with QS 0.93, PF 1.13, DD 20.1%, trades 76
- On QD-20260313-C141-ETH-RANGE-RECLAIM-v1, abort: fail with QS 0.38, PF 0.70, DD 31.6%, trades 83
- On QD-20260313-C141-ETH-BREAKOUT-HOLD-v1, pass: PASS with QS 0.85, PF 1.06, DD 20.9%, trades 75

## What Still Needs Testing
- none

## Strategy-by-Strategy Reasons
- QD-20260313-C141-ETH-EMA-PULLBACK-v1: asset=ETH | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: trend pullback continuation after value reclaim
  thesis: trend pullback continuation after value reclaim
  train: QS 0.93 | Sharpe 0 | PF 1.131 | DD 20.07% | Trades 76
  why: pass: PASS with QS 0.93, PF 1.13, DD 20.1%, trades 76
  evidence: rq_b7ad1284f045=pass (Deterministic closure inherited pass for queue row rq_b7ad1284f045 from strategy outcome QD-20260313-C141-ETH-EMA-PULLBACK-v1.)
- QD-20260313-C141-ETH-RANGE-RECLAIM-v1: asset=ETH | timeframe=4h | decision=abort | diagnosis=bad idea
  mechanism: range reclaim continuation after false breakdown and value recovery
  thesis: range reclaim continuation after false breakdown and value recovery
  train: QS 0.381 | Sharpe 0 | PF 0.697 | DD 31.55% | Trades 83
  why: abort: fail with QS 0.38, PF 0.70, DD 31.6%, trades 83
  evidence: rq_10cbc088af86=abort (Deterministic closure inherited abort for queue row rq_10cbc088af86 from strategy outcome QD-20260313-C141-ETH-RANGE-RECLAIM-v1.)
- QD-20260313-C141-ETH-BREAKOUT-HOLD-v1: asset=ETH | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: breakout continuation after hold above broken structure with volatility expansion
  thesis: breakout continuation after hold above broken structure with volatility expansion
  train: QS 0.847 | Sharpe 0 | PF 1.056 | DD 20.91% | Trades 75
  why: pass: PASS with QS 0.85, PF 1.06, DD 20.9%, trades 75
  evidence: rq_fbde0ca6b5f0=pass (Deterministic closure inherited pass for queue row rq_fbde0ca6b5f0 from strategy outcome QD-20260313-C141-ETH-BREAKOUT-HOLD-v1.)
