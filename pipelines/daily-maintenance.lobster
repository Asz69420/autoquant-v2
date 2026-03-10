name: daily-maintenance
steps:
 - id: health-check
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\logron-monitor.py

 - id: memory-compaction
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\compact_shared_memory.py

 - id: queue-housekeeping
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\queue_housekeeping.py

 - id: archive-old-specs
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\archive_old_specs.py

 - id: promote-quandalf-memory
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\backfill_quandalf_lessons.py

 - id: promote-agent-memory
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\backfill_agent_memory.py --agent all

 - id: audit-memory-governance
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\audit_memory_governance.py

 - id: score-external-intel
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\external_intel_relevance.py

 - id: agent-feedback
   command: python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\agent_feedback_loop.py

 - id: git-sync
   command: powershell -NoProfile -Command "cd C:\Users\Clamps\.openclaw\workspace-oragorn; git add -A; if (git diff --cached --quiet) { exit 0 } else { git commit -m 'auto-sync'; git push }"
