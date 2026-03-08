from pathlib import Path

p = Path(r"C:\Users\Clamps\.openclaw\skills\autoquant-youtube-watcher\watcher.py")
s = p.read_text(encoding='utf-8')

s = s.replace("import json\n", "import argparse\nimport json\n", 1)
s = s.replace("ROOT = Path(__file__).resolve().parents[2]", "SKILL_DIR = Path(__file__).resolve().parent\nROOT = Path(r\"C:\\Users\\Clamps\\.openclaw\\workspace-oragorn\")", 1)

s = s.replace(
"def _run(*args: str) -> dict:\n    out = subprocess.check_output([PY, *args], cwd=ROOT, text=True)\n    return json.loads(out)\n",
"def _run(*args: str) -> dict:\n    out = subprocess.check_output([PY, *args], cwd=ROOT, text=True)\n    return json.loads(out)\n\n\ndef _run_local(script_name: str, *args: str) -> dict:\n    out = subprocess.check_output([PY, str(SKILL_DIR / script_name), *args], cwd=ROOT, text=True)\n    return json.loads(out)\n")

s = s.replace("out = _run('scripts/pipeline/transcript_resolver.py', '--video-id', video_id, '--url', url)", "out = _run_local('transcript_resolver.py', '--video-id', video_id, '--url', url)")
s = s.replace("rc = _run('scripts/pipeline/emit_research_card.py'", "rc = _run_local('emit_research_card.py'")

s = s.replace("def main() -> int:\n", "def _watch_all() -> int:\n", 1)

insert_at = s.rfind("if __name__ == '__main__':")
helpers = '''

def _ensure_state_dir() -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _extract_video_id(url: str) -> str:
    u = (url or '').strip()
    if not u:
        return ''
    m = re.search(r'[?&]v=([0-9A-Za-z_-]{6,})', u)
    if m:
        return m.group(1)
    m = re.search(r'youtu\\.be/([0-9A-Za-z_-]{6,})', u)
    if m:
        return m.group(1)
    m = re.search(r'/shorts/([0-9A-Za-z_-]{6,})', u)
    if m:
        return m.group(1)
    if re.fullmatch(r'[0-9A-Za-z_-]{6,}', u):
        return u
    return ''


def _list_channels() -> int:
    _ensure_state_dir()
    state = _j(STATE_PATH, {'channels': [], 'seen_video_ids': [], 'max_new_videos_per_run': 2})
    print(json.dumps(state.get('channels', []), indent=2))
    return 0


def _subscribe(name: str, url: str, mode: str) -> int:
    if not name or not url or not mode:
        raise SystemExit('--subscribe requires --name, --url, and --mode')
    mode_up = str(mode).strip().upper()
    if mode_up not in {'INDICATORS', 'CONCEPTS'}:
        raise SystemExit('--mode must be INDICATORS or CONCEPTS')

    _ensure_state_dir()
    state = _j(STATE_PATH, {'channels': [], 'seen_video_ids': [], 'max_new_videos_per_run': 2})
    channels = state.get('channels', []) if isinstance(state.get('channels'), list) else []

    row = {
        'name': str(name).strip(),
        'url': str(url).strip(),
        'enabled': True,
        'mode': mode_up,
        'channel_id': '',
        'last_seen_video_id': '',
        'fetch_fail_count': 0,
    }

    updated = False
    for i, ch in enumerate(channels):
        if isinstance(ch, dict) and str(ch.get('name', '')).strip().lower() == row['name'].lower():
            old = dict(ch)
            old.update(row)
            channels[i] = old
            updated = True
            break
    if not updated:
        channels.append(row)

    state['channels'] = channels
    _w(STATE_PATH, state)
    print(json.dumps({'ok': True, 'action': 'subscribe', 'updated': updated, 'channel': row}, indent=2))
    return 0


def _unsubscribe(name: str) -> int:
    if not name:
        raise SystemExit('--unsubscribe requires --name')
    _ensure_state_dir()
    state = _j(STATE_PATH, {'channels': [], 'seen_video_ids': [], 'max_new_videos_per_run': 2})
    channels = state.get('channels', []) if isinstance(state.get('channels'), list) else []
    before = len(channels)
    keep = [ch for ch in channels if not (isinstance(ch, dict) and str(ch.get('name', '')).strip().lower() == str(name).strip().lower())]
    state['channels'] = keep
    _w(STATE_PATH, state)
    removed = before - len(keep)
    print(json.dumps({'ok': True, 'action': 'unsubscribe', 'name': name, 'removed': removed}, indent=2))
    return 0


def _process_url(url: str) -> int:
    vid = _extract_video_id(url)
    if not vid:
        raise SystemExit('Invalid YouTube URL: unable to extract video id')

    _ensure_state_dir()
    retry_queue = _load_retry_queue()
    bundles = _j(BUNDLE_INDEX, [])
    ind_idx = _j(INDICATOR_INDEX, [])

    if not _retry_allowed_now(retry_queue, vid):
        print(json.dumps({'ok': True, 'video_id': vid, 'status': 'RETRY_QUEUED'}))
        return 0

    duration_s = _fetch_video_duration_seconds(vid)
    if duration_s is not None and duration_s < SHORTS_MAX_SECONDS:
        _log('YT_VIDEO_SKIPPED_SHORT', 'SKIPPED_SHORT', f'SKIPPED_SHORT: direct_url {vid} ({duration_s}s)', 'INFO')
        print(json.dumps({'ok': True, 'video_id': vid, 'status': 'SKIPPED_SHORT', 'duration_s': duration_s}))
        return 0
    if duration_s is not None and duration_s > MAX_VIDEO_SECONDS:
        _log('YT_VIDEO_SKIPPED_LONG', 'SKIPPED_LONG', f'SKIPPED_LONG: direct_url {vid} ({duration_s}s)', 'INFO')
        _notify_watch_skip('SKIPPED_LONG', vid, duration_s)
        print(json.dumps({'ok': True, 'video_id': vid, 'status': 'SKIPPED_LONG', 'duration_s': duration_s}))
        return 0

    try:
        tr = _transcript(vid, vid)
        if str(tr.get('status', 'OK')).upper() == 'RETRY_LATER':
            row = _queue_retry(retry_queue, vid, 'YOUTUBE_RATE_LIMIT', int(tr.get('retry_after_seconds') or 0))
            _save_retry_queue(retry_queue)
            _log('YT_TRANSCRIPT_RETRY', 'YT_TRANSCRIPT_RETRY', f"video_id={vid} attempts={row.get('attempts')} next_retry_at={row.get('next_retry_at')} status={row.get('status')}", 'WARN')
            _notify_transcript_failure(vid, vid, f"RETRY_LATER: attempts={row.get('attempts')} next_retry_at={row.get('next_retry_at')}")
            print(json.dumps({'ok': False, 'video_id': vid, 'status': 'RETRY_LATER', 'retry': row}))
            return 0

        txt = tr.get('text', '')
        source_type = 'transcript' if tr.get('quality') == 'caption' else ('auto_transcript' if tr.get('quality') == 'auto_caption' else 'asr_transcript')
        rc = _run_local('emit_research_card.py', '--source-ref', f'https://www.youtube.com/watch?v={vid}', '--source-type', source_type, '--raw-text', txt, '--title', vid, '--author', 'youtube_direct')
        if vid in retry_queue:
            del retry_queue[vid]
            _save_retry_queue(retry_queue)
        _log('YT_VIDEO_INGESTED', 'YT_VIDEO_INGESTED', f"video_id={vid} method={tr.get('method','unknown')} quality={tr.get('quality','unknown')}", 'INFO', outputs=[rc['research_card_path']])
    except Exception as e:
        _notify_transcript_failure(vid, vid, str(e))
        raw = f"Manual concept ingest fallback. source_ref=https://www.youtube.com/watch?v={vid} title={vid} reason=TRANSCRIPT_UNAVAILABLE_AT_INGEST detail={str(e)[:280]}"
        try:
            rc = _run_local('emit_research_card.py', '--source-ref', f'https://www.youtube.com/watch?v={vid}', '--source-type', 'youtube_url', '--raw-text', raw, '--title', vid, '--author', 'youtube_direct')
            _log('YT_VIDEO_INGESTED_FALLBACK', 'YT_VIDEO_INGESTED_FALLBACK', f'video_id={vid}', 'WARN', outputs=[rc['research_card_path']])
        except Exception as e2:
            print(json.dumps({'ok': False, 'video_id': vid, 'status': 'FAILED', 'error': str(e2)}))
            return 1

    if not _research_card_has_sufficient_content(rc['research_card_path']):
        _log('RESEARCH_CARD_REJECTED', 'insufficient_content', f'video_id={vid} reason=insufficient_content', 'WARN', outputs=[rc['research_card_path']])
        print(json.dumps({'ok': True, 'video_id': vid, 'status': 'REJECTED_INSUFFICIENT_CONTENT'}))
        return 0

    channel_cfg = {'active_category': 'REVIEW', 'secondary_categories': []}
    content_category, needs_review, top1, top2 = _classify_video_category(vid, rc['research_card_path'], channel_cfg)
    bundle_status = 'REVIEW_REQUIRED' if needs_review else 'NEW'
    if needs_review:
        _log('YT_CATEGORY_REVIEW', 'YT_CATEGORY_REVIEW', f'video_id={vid} channel=direct top1={top1} top2={top2}', 'WARN')
        _notify_category_review('direct_url', vid, vid, top1, top2)

    linked = _resolve_existing_indicators(rc['research_card_path'], ind_idx)
    lm = _run('scripts/pipeline/link_research_indicators.py', '--research-card-path', rc['research_card_path'], '--indicator-record-paths', json.dumps(linked[:2]))
    _append_usage_note(lm['linkmap_path'], channel_name='direct_url', channel_url=url, video_id=vid)

    bday = datetime.now(UTC).strftime('%Y%m%d')
    bpath = ROOT / 'artifacts' / 'bundles' / bday / f'{vid}.bundle.json'
    b = {
        'id': f'bundle_{vid}',
        'created_at': datetime.now(UTC).isoformat(),
        'source': 'youtube',
        'video_id': vid,
        'source_channel_name': 'direct_url',
        'source_channel_id': '',
        'content_category': ('REVIEW_REQUIRED' if needs_review else content_category),
        'research_card_path': rc['research_card_path'],
        'indicator_record_paths': linked[:2],
        'linkmap_path': lm['linkmap_path'],
        'status': bundle_status,
    }
    _w(bpath, b)

    if bundle_status == 'NEW':
        p = str(bpath).replace('\\', '/')
        bundles = [p] + [x for x in bundles if x != p]
        _w(BUNDLE_INDEX, bundles[:500])

    print(json.dumps({'ok': True, 'video_id': vid, 'bundle_path': str(bpath).replace('\\', '/'), 'status': bundle_status}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description='AutoQuant YouTube watcher V2')
    ap.add_argument('--process-url', default='', help='Process a single YouTube URL directly')
    ap.add_argument('--subscribe', action='store_true', help='Subscribe a channel')
    ap.add_argument('--list-channels', action='store_true', help='List channels')
    ap.add_argument('--unsubscribe', action='store_true', help='Unsubscribe a channel by name')
    ap.add_argument('--name', default='', help='Channel name (for subscribe/unsubscribe)')
    ap.add_argument('--url', default='', help='Channel URL (for subscribe)')
    ap.add_argument('--mode', default='', help='Mode for subscribe: INDICATORS or CONCEPTS')
    args = ap.parse_args()

    if args.list_channels:
        return _list_channels()
    if args.subscribe:
        return _subscribe(args.name, args.url, args.mode)
    if args.unsubscribe:
        return _unsubscribe(args.name)
    if args.process_url:
        return _process_url(args.process_url)

    return _watch_all()


'''

s = s[:insert_at] + helpers + s[insert_at:]
p.write_text(s, encoding='utf-8')
