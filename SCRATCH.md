Task complete: Split YouTube research digest into Quandalf trading feed and Oragorn architecture feed; re-enabled broken trading channels; updated digest references; committed all changes.

Changes completed:
1. Patched watcher.py to split digest outputs by feed_target (quandalf vs oragorn)
2. Added digest helper functions (_read_digest_entries, _write_digest_entries, _append_digest_entry, _digest_target_for_channel, _build_digest_entry)
3. Created rolling 24h failure history instead of instant disable (fetch_fail_history tracks timestamps, auto-disables after 3 failures in 24h window)
4. Updated URL/mode configs in youtube_watchlist.json:
   - Fixed mobile URLs (m.youtube.com/@handle → www.youtube.com/@handle)
   - Removed /videos path suffixes
   - Re-enabled 6 trading channels (all 5 were disabled, now enabled)
   - Added feed_target tags to all channels
5. Updated youtube_channel_categories.json with feed_target routing
6. Added RileyBrown (UCMcoud_ZW7cfxeIugBflSBw) — AI/tooling channel for Oragorn feed
7. Created research-digest-trading.md at agents/quandalf/memory/research-digest-trading.md
8. Created ORAGORN_DIGEST.md at docs/shared/ORAGORN_DIGEST.md
9. Updated Quandalf SOUL.md to reference research-digest-trading.md as his trading-only digest

Channels re-enabled (trading/quandalf):
✅ TradeTravelChill — market structure, indicator concepts
✅ IntoTheCryptoverse — macro context, market structure
✅ ECKrown — market structure, trading concepts
✅ SoheilPKO — indicator concepts, trading
✅ MichaelIonita — trading concepts, risk/execution
✅ DaviddTech — market structure, trading, risk

Channels enabled (architecture/oragorn):
✅ OpenClawNewsFactor — OpenClaw architecture
✅ Openclawlabs — OpenClaw architecture
✅ IBMTechnology — AI systems, security
✅ RileyBrown — AI tooling, agent building (NEW)

Architecture:
- Both digest files now have rolling caps of 25 entries
- Digest entries include video ID, channel name, feed target, category, source URL, title, timestamp, and formatted body
- Failed channel fetch logic now uses 24h rolling window + 3-strike threshold before auto-disable
- Each digest file is independent; videos route based on channel.feed_target

Next: Run watcher on next cron cycle (youtube-grabber at :15). Manual verification shows RSS feeds for all 10 channels are healthy. Digest entries will populate automatically.

Status: Ready for deployment. Next youtube-grabber cron will populate digests and test the routing.