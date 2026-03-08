#!/usr/bin/env python3
import argparse
import json
import sys


def validate_spec(spec_path):
    errors = []
    warnings = []

    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except Exception as e:
        return {"passed": False, "errors": [f"Cannot read spec: {e}"], "warnings": []}

    required_fields = ["id", "name", "asset", "timeframe", "variants"]
    for field in required_fields:
        if field not in spec or not spec[field]:
            errors.append(f"Missing required field: {field}")

    variants = spec.get("variants", [])
    if not isinstance(variants, list) or len(variants) == 0:
        errors.append("No variants defined")
    else:
        for i, v in enumerate(variants):
            if not isinstance(v, dict):
                errors.append(f"Variant {i} is not a dict")
                continue

            if not v.get("name"):
                errors.append(f"Variant {i} missing name")

            rp = v.get("risk_policy", {})
            if not isinstance(rp, dict):
                errors.append(f"Variant {v.get('name', i)} missing risk_policy")
            else:
                if rp.get("risk_per_trade_pct", 0) > 0.05:
                    errors.append(f"Variant {v.get('name', i)}: risk_per_trade_pct > 5% is too high")
                if rp.get("stop_atr_mult", 0) <= 0 and rp.get("stop_type") == "atr":
                    errors.append(f"Variant {v.get('name', i)}: ATR stop mult must be > 0")

            ep = v.get("execution_policy", {})
            if not isinstance(ep, dict):
                warnings.append(f"Variant {v.get('name', i)} missing execution_policy")

    asset = spec.get("asset", "")
    if asset and len(asset) > 20:
        warnings.append(f"Unusual asset name: {asset}")

    tf = spec.get("timeframe", "")
    valid_tfs = ["1m", "5m", "15m", "1h", "4h", "1d"]
    if tf and tf not in valid_tfs:
        warnings.append(f"Non-standard timeframe: {tf}")

    passed = len(errors) == 0
    return {"passed": passed, "errors": errors, "warnings": warnings}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True)
    a = p.parse_args()

    result = validate_spec(a.spec)
    result["spec_path"] = a.spec
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
