# Quandalf Journal — Cycle 112

- ts_iso: 2026-03-12T23:41:09.600269+00:00
- mode: explore
- lane: BTC / 4h
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
    "BTC",
    "DOGE",
    "ETH",
    "TAO"
  ],
  "timeframes_touched": [
    "1h",
    "4h"
  ],
  "cycle_ids": [
    108,
    109,
    110,
    111,
    112
  ]
}

## What Worked
- On QD-20260312-C112-BTC-EMA-PULLBACK-v1, refine: PASS with QS 0.77, PF 0.98, DD 21.6%, trades 116
- On QD-20260312-C112-BTC-BREAKOUT-HOLD-v1, refine: PASS with QS 0.79, PF 1.01, DD 21.2%, trades 107
- On QD-20260312-C112-BTC-RANGE-RECLAIM-v1, refine: PASS with QS 0.97, PF 1.09, DD 11.2%, trades 99

## Awaiting Evidence
- none

## What Failed
- none

## Why I Judged It That Way
- On QD-20260312-C112-BTC-EMA-PULLBACK-v1, bad idea
- On QD-20260312-C112-BTC-BREAKOUT-HOLD-v1, bad idea
- On QD-20260312-C112-BTC-RANGE-RECLAIM-v1, bad idea

## What I Would Improve Next
- On QD-20260312-C112-BTC-EMA-PULLBACK-v1, pass: PASS with QS 0.77, PF 0.98, DD 21.6%, trades 116
- On QD-20260312-C112-BTC-BREAKOUT-HOLD-v1, pass: PASS with QS 0.79, PF 1.01, DD 21.2%, trades 107
- On QD-20260312-C112-BTC-RANGE-RECLAIM-v1, pass: PASS with QS 0.97, PF 1.09, DD 11.2%, trades 99

## What Still Needs Testing
- none

## Strategy-by-Strategy Reasons
- QD-20260312-C112-BTC-EMA-PULLBACK-v1: asset=BTC | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: trend pullback continuation after value reclaim
  thesis: trend pullback continuation after value reclaim
  train: QS 0.769 | Sharpe 0 | PF 0.985 | DD 21.64% | Trades 116
  why: pass: PASS with QS 0.77, PF 0.98, DD 21.6%, trades 116
  evidence: rq_ed9e8c882c26=pass (Deterministic closure inherited pass for queue row rq_ed9e8c882c26 from strategy outcome QD-20260312-C112-BTC-EMA-PULLBACK-v1.)
- QD-20260312-C112-BTC-BREAKOUT-HOLD-v1: asset=BTC | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: breakout continuation after hold above broken structure with volatility expansion
  thesis: breakout continuation after hold above broken structure with volatility expansion
  train: QS 0.794 | Sharpe 0 | PF 1.006 | DD 21.24% | Trades 107
  why: pass: PASS with QS 0.79, PF 1.01, DD 21.2%, trades 107
  evidence: rq_0f43ac708b36=pass (Deterministic closure inherited pass for queue row rq_0f43ac708b36 from strategy outcome QD-20260312-C112-BTC-BREAKOUT-HOLD-v1.)
- QD-20260312-C112-BTC-RANGE-RECLAIM-v1: asset=BTC | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: range reclaim continuation after false breakdown and value recovery
  thesis: range reclaim continuation after false breakdown and value recovery
  train: QS 0.974 | Sharpe 0 | PF 1.086 | DD 11.2% | Trades 99
  why: pass: PASS with QS 0.97, PF 1.09, DD 11.2%, trades 99
  evidence: rq_bd6b625fabdb=pass (Deterministic closure inherited pass for queue row rq_bd6b625fabdb from strategy outcome QD-20260312-C112-BTC-RANGE-RECLAIM-v1.)
