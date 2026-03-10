# DB and Backtest Reference

## Backtest Architecture
AutoQuant uses `scripts/walk_forward_engine.py` as the primary backtester.

### Stages
- **screen**
  - recent ~3 months only
  - must meet:
    - `SCREEN_MIN_TRADES = 30`
    - profit factor >= 1.0
    - max drawdown <= 15%
- **full**
  - rolling walk-forward train/blind folds
  - true out-of-sample aggregation is scored
- **validation**
  - follow-up validation queue for stronger candidates

### Main trade gates
- `MIN_PASS_TRADES = 50`
- `MIN_PROMOTE_TRADES = 50`

Important: the **30-trade screen threshold is not the main scoring floor**. It is only the earlier screen gate. The real pass/promote floor is **50 trades**.

## Key DB Tables
### `backtest_results`
Stores valid saved walk-forward results only.
Important columns include:
- `strategy_spec_id`
- `variant_id`
- `asset`
- `timeframe`
- `total_trades`
- `score_total`
- `score_decision`
- `qscore_insample`
- `qscore_outofsample`
- `degradation_pct`
- `walk_forward_folds`
- `walk_forward_config`
- `fold_results`
- `strategy_family`
- `stage`

### `research_funnel_queue`
Tracks queued/running/done funnel jobs.
Important columns include:
- `cycle_id`
- `strategy_spec_id`
- `variant_id`
- `asset`
- `timeframe`
- `stage`
- `bucket`
- `status`
- `notes`
- `result_id`

### `event_log`
Operational event history for pipeline/worker behavior.

## Classification Update
Zero-trade integrity skips are now treated as **integrity skips**, not generic terminal failures.
That means:
- true runner crashes stay failures
- non-trading strategies stay visible without looking like infrastructure collapse

## Snapshot Tool
Run:

```powershell
python scripts/db_schema_snapshot.py
```

Output:
- `data/state/db_schema_snapshot.json`
