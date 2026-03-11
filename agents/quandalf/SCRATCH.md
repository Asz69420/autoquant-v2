Active task: Rebuild full strategy batch for current cycle using live packet context.

Steps:
1. Read briefing_packet.json, cycle_orders.json, research_program.json, reflection_packet.json, current_cycle_status.json.
2. Verify the current allowed basket / supported universe.
3. Design 2-4 materially distinct specs for the live mode.
4. Write all specs to artifacts/strategy_specs/.
5. Update agents/quandalf/memory/current_cycle_status.json with the same cycle_id.

Completed so far:
- Received cycle design instruction.

Next step:
- Read live cycle files and latest reflection before designing replacements.
