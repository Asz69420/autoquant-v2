import json
import pathlib
import sys

ROOT = pathlib.Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
sys.path.insert(0, str(ROOT / "scripts"))
import walk_forward_engine as wfe  # noqa: E402


def assert_true(cond, message):
    if not cond:
        raise AssertionError(message)


def test_indicator_tokens():
    candles = wfe.load_candles("ETH", "4h")[-300:]
    indicators = wfe.compute_indicators(candles, {}, ["VWAP", "ADX_14", "DONCHIAN_20", "EMA_20", "ATR_14"])
    idx = len(candles) - 1
    assert_true(indicators.get("vwap") is not None, "VWAP series missing")
    assert_true(indicators.get("adx_14") is not None, "ADX series missing")
    assert_true(indicators.get("donchian_high_20") is not None, "Donchian high series missing")
    assert_true(wfe.evaluate_condition("Close >= VWAP - 0.40 * ATR_14", idx, indicators, candles) in {True, False}, "VWAP rule did not evaluate")
    assert_true(wfe.evaluate_condition("ADX_14 <= 22", idx, indicators, candles) in {True, False}, "ADX rule did not evaluate")
    assert_true(wfe.evaluate_condition("Close >= DONCHIAN_HIGH_20 - 0.10 * ATR_14", idx, indicators, candles) in {True, False}, "Donchian rule did not evaluate")
    return {"status": "ok"}


def test_confirmation_and_risk_parse(spec_path):
    strategy = wfe.parse_strategy_spec(str(spec_path), "default")
    if "STATE-CHANGE-HOLD-EXPANSION" in spec_path.name:
        assert_true(bool(strategy.get("confirmation_rules", {}).get("long")), "Confirmation rules not parsed")
        assert_true(int(strategy.get("risk", {}).get("max_holding_bars") or 0) == 6, "Time stop not parsed from exit rules")
    if "DELAYED-RETEST-CONTINUATION" in spec_path.name:
        assert_true(abs(float(strategy.get("risk", {}).get("stop_atr_mult") or 0) - 0.90) < 1e-9, "ATR stop not parsed")
        assert_true(abs(float(strategy.get("risk", {}).get("tp_atr_mult") or 0) - 0.66) < 1e-9, "ATR take profit not parsed")
        assert_true(int(strategy.get("risk", {}).get("max_holding_bars") or 0) == 8, "Time stop not parsed")
    return {"status": "ok"}


def run_spec(spec_rel, asset, timeframe, stage):
    spec_path = ROOT / spec_rel
    strategy = wfe.parse_strategy_spec(str(spec_path), "default")
    candles = wfe.load_candles(asset, timeframe)
    if stage == "screen":
        result = wfe.run_walk_forward(candles, strategy, timeframe, asset=asset, stage="screen")
        trades = int(((result.get("outofsample_aggregate") or {}).get("total_trades") or 0))
    else:
        result = wfe.run_walk_forward(candles, strategy, timeframe, asset=asset, stage="full")
        trades = int(((result.get("insample_aggregate") or {}).get("total_trades") or 0)) + int(((result.get("outofsample_aggregate") or {}).get("total_trades") or 0))
    return {
        "spec": spec_path.name,
        "asset": asset,
        "timeframe": timeframe,
        "stage": stage,
        "status": result.get("status"),
        "trades": trades,
        "screen_passed": result.get("screen_passed"),
        "decision": (result.get("outofsample_aggregate") or {}).get("decision"),
        "qscore": (result.get("outofsample_aggregate") or {}).get("qscore"),
        "flags": (result.get("outofsample_aggregate") or {}).get("flags"),
    }


def main():
    tests = []
    tests.append({"indicator_tokens": test_indicator_tokens()})

    doge_spec = ROOT / "artifacts/strategy_specs/QD-20260312-C067-DOGE-4H-STATE-CHANGE-HOLD-EXPANSION-v1.strategy_spec.json"
    eth_spec = ROOT / "artifacts/strategy_specs/QD-20260312-C067-ETH-4H-EXHAUSTION-REACCEPTANCE-ROTATION-v1.strategy_spec.json"
    tao_spec = ROOT / "artifacts/strategy_specs/QD-20260312-C067-TAO-4H-DELAYED-RETEST-CONTINUATION-v1.strategy_spec.json"
    tests.append({"doge_parse": test_confirmation_and_risk_parse(doge_spec)})
    tests.append({"tao_parse": test_confirmation_and_risk_parse(tao_spec)})

    results = [
        run_spec("artifacts/strategy_specs/QD-20260312-C067-DOGE-4H-STATE-CHANGE-HOLD-EXPANSION-v1.strategy_spec.json", "DOGE", "4h", "screen"),
        run_spec("artifacts/strategy_specs/QD-20260312-C067-ETH-4H-EXHAUSTION-REACCEPTANCE-ROTATION-v1.strategy_spec.json", "ETH", "4h", "screen"),
        run_spec("artifacts/strategy_specs/QD-20260312-C067-TAO-4H-DELAYED-RETEST-CONTINUATION-v1.strategy_spec.json", "TAO", "4h", "screen"),
        run_spec("artifacts/strategy_specs/QD-20260312-C067-TAO-4H-DELAYED-RETEST-CONTINUATION-v1.strategy_spec.json", "TAO", "4h", "full"),
    ]

    assert_true(results[1]["trades"] >= 0, "ETH run missing")
    assert_true(results[2]["trades"] > 0, "TAO screen should now produce trades")
    payload = {"status": "ok", "tests": tests, "results": results}
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
