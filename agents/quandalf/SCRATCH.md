Active task: Refresh live cycle authority and write the full strategy batch for the currently active cycle.

Steps:
1. Read briefing_packet.json, cycle_orders.json, research_program.json, reflection_packet.json, and current_cycle_status.json.
2. Determine active cycle_id, mode, allowed basket, and regime.
3. Design 2-4 materially distinct specs inside the supported/fetchable universe.
4. Write all spec files to artifacts/strategy_specs/.
5. Update current_cycle_status.json with the same active cycle_id.

Completed so far:
- Read SCRATCH.md, SOUL.md, USER.md, MEMORY.md.
- Confirmed daily memory files for 2026-03-11 and 2026-03-10 are absent.
- Correcting mistaken doubled workspace path before reading live cycle files.

Next step:
- Read the five live authority files from the correct agents/quandalf/memory path and write the new batch for the active cycle.