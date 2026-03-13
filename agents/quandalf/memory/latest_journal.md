# Quandalf Journal — Cycle 163

- ts_iso: 2026-03-13T06:40:10.555674+00:00
- mode: explore
- lane: DOGE / 4h
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
    "pass": 14,
    "refine": 0,
    "abort": 1,
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
    "DOGE",
    "ETH",
    "SOL",
    "TAO"
  ],
  "timeframes_touched": [
    "4h"
  ],
  "cycle_ids": [
    159,
    160,
    161,
    162,
    163
  ]
}

## What Worked
- On QD-20260313-C163-DOGE-EMA-PULLBACK-v1, refine: PASS with QS 0.73, PF 0.93, DD 19.3%, trades 79
- On QD-20260313-C163-DOGE-BREAKOUT-HOLD-v1, refine: PASS with QS 0.87, PF 1.04, DD 16.6%, trades 77
- On QD-20260313-C163-DOGE-RANGE-RECLAIM-v1, refine: PASS with QS 0.99, PF 1.21, DD 22.4%, trades 72

## Awaiting Evidence
- none

## What Failed
- none

## Why I Judged It That Way
- On QD-20260313-C163-DOGE-EMA-PULLBACK-v1, bad idea
- On QD-20260313-C163-DOGE-BREAKOUT-HOLD-v1, bad idea
- On QD-20260313-C163-DOGE-RANGE-RECLAIM-v1, bad idea

## What I Would Improve Next
- On QD-20260313-C163-DOGE-EMA-PULLBACK-v1, pass: PASS with QS 0.73, PF 0.93, DD 19.3%, trades 79
- On QD-20260313-C163-DOGE-BREAKOUT-HOLD-v1, pass: PASS with QS 0.87, PF 1.04, DD 16.6%, trades 77
- On QD-20260313-C163-DOGE-RANGE-RECLAIM-v1, pass: PASS with QS 0.99, PF 1.21, DD 22.4%, trades 72

## What Still Needs Testing
- none

## Strategy-by-Strategy Reasons
- QD-20260313-C163-DOGE-EMA-PULLBACK-v1: asset=DOGE | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: trend pullback continuation after value reclaim
  thesis: trend pullback continuation after value reclaim
  train: QS 0.732 | Sharpe 0 | PF 0.925 | DD 19.31% | Trades 79
  why: pass: PASS with QS 0.73, PF 0.93, DD 19.3%, trades 79
  evidence: rq_22ce8548f8dc=pass (Deterministic closure inherited pass for queue row rq_22ce8548f8dc from strategy outcome QD-20260313-C163-DOGE-EMA-PULLBACK-v1.)
- QD-20260313-C163-DOGE-BREAKOUT-HOLD-v1: asset=DOGE | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: breakout continuation after hold above broken structure with volatility expansion
  thesis: breakout continuation after hold above broken structure with volatility expansion
  train: QS 0.874 | Sharpe 0 | PF 1.04 | DD 16.56% | Trades 77
  why: pass: PASS with QS 0.87, PF 1.04, DD 16.6%, trades 77
  evidence: rq_eda5ce808498=pass (Deterministic closure inherited pass for queue row rq_eda5ce808498 from strategy outcome QD-20260313-C163-DOGE-BREAKOUT-HOLD-v1.)
- QD-20260313-C163-DOGE-RANGE-RECLAIM-v1: asset=DOGE | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: range reclaim continuation after false breakdown and value recovery
  thesis: range reclaim continuation after false breakdown and value recovery
  train: QS 0.989 | Sharpe 0 | PF 1.213 | DD 22.37% | Trades 72
  why: pass: PASS with QS 0.99, PF 1.21, DD 22.4%, trades 72
  evidence: rq_81275f82b6e9=pass (Deterministic closure inherited pass for queue row rq_81275f82b6e9 from strategy outcome QD-20260313-C163-DOGE-RANGE-RECLAIM-v1.)
