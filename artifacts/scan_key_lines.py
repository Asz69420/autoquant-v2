from pathlib import Path
root=Path(r'C:\Users\Clamps\.openclaw\workspace-oragorn')
files=['scripts/build_quandalf_learning_memory.py','scripts/build_quandalf_experiment_memory.py','scripts/research-cycle.py','scripts/build_cycle_orders.py']
needles=['active_cycle_id','cycle_id = int(','run_state = load_json','CURRENT_CYCLE_STATUS','CURRENT_CYCLE_SPECS','RUN_STATE']
out=[]
for rel in files:
    p=root/rel
    txt=p.read_text(encoding='utf-8', errors='ignore').splitlines()
    out.append('\nFILE '+rel)
    for i,l in enumerate(txt,1):
        if any(n in l for n in needles):
            out.append(f'{i}: {l}')
(root/'artifacts'/'scan_key_lines.txt').write_text('\n'.join(out), encoding='utf-8')
print('done')
