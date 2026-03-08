import subprocess

p = r"C:\Users\Clamps\AppData\Roaming\npm\openclaw.CMD"
msg = (
    "Research cycle time. Follow these steps: "
    "1. Run briefing builder: exec python C:\\Users\\Clamps\\.openclaw\\workspace-oragorn\\scripts\\research-cycle.py "
    "2. Read briefing: read agents/quandalf/memory/briefing_packet.json "
    "3. Spawn Quandalf: use sessions_spawn with agentId quandalf and task \"Read briefing at agents/quandalf/memory/briefing_packet.json. Design ONE strategy. Output strategy_spec JSON in ```json fences. Write journal in ```journal fences. Templates: ema_crossover, rsi_pullback, macd_confirmation, supertrend_follow, bollinger_breakout, stochastic_reversal, ema_rsi_atr, choppiness_donchian_fade\" "
    "4. After Quandalf announces: save strategy spec to artifacts/strategy_specs/, run backtester with exec python ~/.openclaw/skills/autoquant-backtester/engine.py --asset ASSET --tf TIMEFRAME --strategy-spec SPEC_PATH --variant VARIANT "
    "5. Run post-processing: exec python C:\\Users\\Clamps\\.openclaw\\workspace-oragorn\\scripts\\cycle-postprocess.py --since-minutes 30"
)

r = subprocess.run([p, "cron", "edit", "4304d16b-a34d-4856-bc0f-985261bb0ab2", "--message", msg], capture_output=True, text=True)
print(r.stdout)
print("rc=", r.returncode)
if r.stderr:
    print(r.stderr)
