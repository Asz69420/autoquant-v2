from pathlib import Path
files=[r'scripts/build_quandalf_experiment_memory.py',r'scripts/build_quandalf_learning_memory.py',r'scripts/leaderboard_render.py',r'scripts/research-cycle.py',r'scripts/build_cycle_orders.py',r'scripts/build-reflection-packet.py',r'scripts/capture_cycle_specs.py',r'scripts/cycle-postprocess.py']
root=Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn')
out=[]
for rel in files:
    p=root/rel
    txt=p.read_text(encoding='utf-8', errors='ignore').splitlines()
    out.append(f'FILE {rel}')
    for i,l in enumerate(txt,1):
        if 'research_cycle_started_at.json' in l or 'current_cycle_specs.json' in l or 'current_cycle_status.json' in l:
            out.append(f'{i}: {l}')
Path(root/'artifacts'/'state_ref_lines.txt').write_text('\n'.join(out), encoding='utf-8')
print('done')
