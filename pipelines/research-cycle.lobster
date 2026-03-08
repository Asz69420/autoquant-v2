name: research-cycle
steps:
 - id: briefing
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py

 - id: oragorn-review
   command: openclaw agent --agent oragorn --message "Research cycle briefing ready at agents/quandalf/memory/briefing_packet.json. Review it now. Check QScore trends from the last 3 cycles. Check if quality is improving or declining. Then write specific orders to agents/quandalf/memory/cycle_orders.json with: target_asset, target_timeframe, research_direction (explore_new OR iterate_existing), specific_family_to_iterate (if applicable), thesis_hint, max_variants (cap at 5), and stop_condition. If recent QScores are declining, set research_direction to iterate_existing and pick the best-performing family. If quality is good, allow exploration. Do NOT give Quandalf generic orders." --timeout 120000

 - id: quandalf-design
   command: openclaw agent --agent quandalf --message "Read your cycle orders at agents/quandalf/memory/cycle_orders.json. Follow Oragorn's direction exactly. Design your strategy and variants according to his instructions. Write your strategy spec and journal entry." --timeout 300000

 - id: postprocess
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\parallel_runner.py --spec LATEST_SPEC --variant all

 - id: reflection
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build-reflection-packet.py

 - id: quandalf-reflect
   command: openclaw agent --agent quandalf --message "Review the reflection packet. Extract lessons. Propose refinements for strategies that showed promise." --timeout 300000

 - id: refine-postprocess
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py

 - id: xqs-check
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\xqs_runner.py --run

 - id: tv-grabber
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_tv_grabber.py
