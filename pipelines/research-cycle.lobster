name: research-cycle
steps:
 - id: briefing
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\research-cycle.py

 - id: quandalf-design
   command: openclaw agent --agent quandalf --message "Read your briefing packet at docs/shared/QUANDALF_ORDERS.md. Design a new strategy or refine an existing one. Write your strategy spec and journal entry." --no-input --timeout 300000

 - id: postprocess
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py

 - id: reflection
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\build-reflection-packet.py

 - id: quandalf-reflect
   command: openclaw agent --agent quandalf --message "Review the reflection packet. Extract lessons. Propose refinements for strategies that showed promise." --no-input --timeout 300000

 - id: refine-postprocess
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py

 - id: tv-grabber
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\run_tv_grabber.py
