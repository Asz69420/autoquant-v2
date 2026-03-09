Task: Recovery/stabilization pass for pipeline.

Steps:
1. Trace one clean path from cycle-start -> research-cycle -> capture-cycle-specs -> postprocess.
2. Identify remaining upstream cycle-state ownership bug causing current_cycle_status lag.
3. Identify remaining duplicate/noisy report paths.
4. Patch one-owner model for cycle state and one-owner model for cycle postprocess reporting.
5. Validate with local runs and commit/push.

Completed so far:
- Multiple downstream fixes already landed earlier (health per-cycle trigger removed, batch summary poisoning fixed, duplicate health sends reduced).

Next step:
- Inspect exact remaining writers and postprocess/reporting conditions.
