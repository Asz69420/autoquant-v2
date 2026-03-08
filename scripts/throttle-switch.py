#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


VALID_MODES = ("paused", "slow", "normal", "fast", "turbo")


def config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "throttle.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"Error: config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"Error: unable to read config file '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def save_config(path: Path, data: dict) -> None:
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except Exception as exc:
        print(f"Error: unable to write config file '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def get_modes(config: dict) -> dict:
    modes = config.get("modes")
    if not isinstance(modes, dict):
        print("Error: invalid config format: 'modes' must be an object", file=sys.stderr)
        sys.exit(1)
    return modes


def print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show or switch throttle mode.",
        usage="python scripts/throttle-switch.py --status\n       python scripts/throttle-switch.py --mode <paused|slow|normal|fast|turbo>",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="Show current throttle mode and settings")
    group.add_argument("--mode", metavar="MODE", help="Set throttle mode")
    args = parser.parse_args()

    path = config_path()
    config = load_config(path)
    modes = get_modes(config)

    if args.status:
        current_mode = config.get("current_mode")
        current_settings = modes.get(current_mode)
        if current_settings is None:
            print(
                f"Error: current_mode '{current_mode}' is not defined in config modes",
                file=sys.stderr,
            )
            sys.exit(1)
        print_json({
            "current_mode": current_mode,
            "settings": current_settings,
        })
        return

    new_mode = args.mode
    if new_mode not in VALID_MODES:
        print(
            f"Error: invalid mode '{new_mode}'. Valid modes: {', '.join(VALID_MODES)}",
            file=sys.stderr,
        )
        sys.exit(2)

    if new_mode not in modes:
        print(
            f"Error: mode '{new_mode}' is not defined in config/throttle.json",
            file=sys.stderr,
        )
        sys.exit(1)

    old_mode = config.get("current_mode")
    config["current_mode"] = new_mode
    save_config(path, config)

    print_json({
        "old_mode": old_mode,
        "new_mode": new_mode,
        "settings": modes[new_mode],
    })


if __name__ == "__main__":
    main()
