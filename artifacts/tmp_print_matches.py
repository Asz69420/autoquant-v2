from pathlib import Path
files=[r'scripts/build_cycle_orders.py',r'scripts/build_quandalf_research_program.py',r'scripts/ensure_quandalf_decisions_complete.py']
needles=['minimum_spec_count','maximum_spec_count','mode','explore','exploit','deterministic_decision_for_outcome','allowed_next_actions','target_asset','target_timeframe']
root=Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn')
for rel in files:
    print('\nFILE',rel)
    lines=(root/rel).read_text(encoding='utf-8', errors='ignore').splitlines()
    for i,l in enumerate(lines,1):
        if any(n in l for n in needles):
            print(f'{i}: {l}')
