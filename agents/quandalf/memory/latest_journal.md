# Quandalf Journal — Cycle 145

- ts_iso: 2026-03-13T04:13:33.703472+00:00
- mode: explore
- lane: DOGE / 4h
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
    "pass": 13,
    "refine": 0,
    "abort": 2,
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
    "SOL",
    "TAO"
  ],
  "timeframes_touched": [
    "4h"
  ],
  "cycle_ids": [
    141,
    142,
    143,
    144,
    145
  ]
}

## What Worked
- On QD-20260313-C145-DOGE-BREAKOUT-HOLD-v1, refine: PASS with QS 0.87, PF 1.04, DD 16.6%, trades 77
- On QD-20260313-C145-DOGE-EMA-PULLBACK-v1, refine: PASS with QS 0.73, PF 0.92, DD 19.3%, trades 79

## Awaiting Evidence
- none

## What Failed
- On QD-20260313-C145-DOGE-RANGE-RECLAIM-v1, abort: fail with QS 0.84, PF 1.06, DD 21.6%, trades 32

## Why I Judged It That Way
- On QD-20260313-C145-DOGE-BREAKOUT-HOLD-v1, bad idea
- On QD-20260313-C145-DOGE-EMA-PULLBACK-v1, bad idea
- On QD-20260313-C145-DOGE-RANGE-RECLAIM-v1, bad idea

## What I Would Improve Next
- On QD-20260313-C145-DOGE-BREAKOUT-HOLD-v1, pass: PASS with QS 0.87, PF 1.04, DD 16.6%, trades 77
- On QD-20260313-C145-DOGE-EMA-PULLBACK-v1, pass: PASS with QS 0.73, PF 0.92, DD 19.3%, trades 79
- On QD-20260313-C145-DOGE-RANGE-RECLAIM-v1, abort: fail with QS 0.84, PF 1.06, DD 21.6%, trades 32

## What Still Needs Testing
- none

## Strategy-by-Strategy Reasons
- QD-20260313-C145-DOGE-BREAKOUT-HOLD-v1: asset=DOGE | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: breakout continuation after hold above broken structure with volatility expansion
  thesis: breakout continuation after hold above broken structure with volatility expansion
  train: QS 0.873 | Sharpe 0 | PF 1.039 | DD 16.56% | Trades 77
  why: pass: PASS with QS 0.87, PF 1.04, DD 16.6%, trades 77
  evidence: rq_9b3727e64975=pass (Deterministic closure inherited pass for queue row rq_9b3727e64975 from strategy outcome QD-20260313-C145-DOGE-BREAKOUT-HOLD-v1.)
- QD-20260313-C145-DOGE-EMA-PULLBACK-v1: asset=DOGE | timeframe=4h | decision=pass | diagnosis=bad idea
  mechanism: trend pullback continuation after value reclaim
  thesis: trend pullback continuation after value reclaim
  train: QS 0.729 | Sharpe 0 | PF 0.922 | DD 19.31% | Trades 79
  why: pass: PASS with QS 0.73, PF 0.92, DD 19.3%, trades 79
  evidence: rq_f46ad9080ac8=pass (Deterministic closure inherited pass for queue row rq_f46ad9080ac8 from strategy outcome QD-20260313-C145-DOGE-EMA-PULLBACK-v1.)
- QD-20260313-C145-DOGE-RANGE-RECLAIM-v1: asset=DOGE | timeframe=4h | decision=abort | diagnosis=bad idea
  mechanism: range reclaim continuation after false breakdown and value recovery
  thesis: range reclaim continuation after false breakdown and value recovery
  train: QS 1.008 | Sharpe 0 | PF 1.224 | DD 21.64% | Trades 71
  test: runs=1 | trades=32 | best QS 0.844 | best Sharpe 0 | best PF 1.06 | max DD 21.64%
  why: abort: fail with QS 0.84, PF 1.06, DD 21.6%, trades 32
  evidence: rq_80cf8ab52252=abort (Deterministic closure inherited abort for queue row rq_80cf8ab52252 from strategy outcome QD-20260313-C145-DOGE-RANGE-RECLAIM-v1.)
  evidence: rq_0797d7b7e3f1=abort (Deterministic closure inherited abort for queue row rq_0797d7b7e3f1 from strategy outcome QD-20260313-C145-DOGE-RANGE-RECLAIM-v1.)
