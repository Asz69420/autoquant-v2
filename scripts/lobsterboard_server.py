#!/usr/bin/env python3
import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
PREFS_PATH = os.path.join(ROOT, "data", "state", "lobsterboard_prefs.json")
HOST = "0.0.0.0"
PORT = 8787

DEFAULT_PREFS = {
    "theme": "dark",
    "fontScale": 100,
    "refreshMs": 10000,
    "showHealth": True,
    "showPipelines": True,
    "showEvents": True,
    "showLeaderboard": True,
}

HTML = """<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>LobsterBoard</title>
  <style>
    :root{
      --bg:#0a0f1f; --bg2:#0f1730; --panel:#101a33; --line:#263454;
      --text:#eaf1ff; --muted:#9fb2d6; --ok:#22c55e; --warn:#f59e0b; --bad:#ef4444;
      --card:#0f1730;
    }
    [data-theme='light']{
      --bg:#eff4ff; --bg2:#f7faff; --panel:#ffffff; --line:#cdd9ef;
      --text:#0d1b37; --muted:#54698f; --card:#ffffff;
    }
    *{box-sizing:border-box}
    body{margin:0;padding:16px;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:radial-gradient(1200px 700px at 80% -10%,var(--bg2) 0%, var(--bg) 55%);color:var(--text);font-size:calc(14px * var(--scale,1));}
    .wrap{max-width:1220px;margin:0 auto}
    .top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
    .btn{border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:10px;padding:6px 10px;cursor:pointer}
    .sub{color:var(--muted);font-size:12px}
    .grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:12px}
    .card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
    .k{font-size:12px;color:var(--muted);margin-bottom:6px}
    .v{font-size:24px;font-weight:700;line-height:1}
    .panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:12px}
    .panel h2{font-size:15px;margin:0 0 10px 0}
    .two{display:grid;grid-template-columns:2fr 1fr;gap:12px}
    table{width:100%;border-collapse:collapse;font-size:12.5px}
    th,td{padding:8px 6px;border-bottom:1px solid var(--line)}
    th{text-align:left;color:var(--muted)}
    tr:last-child td{border-bottom:none}
    .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;border:1px solid transparent}
    .ok{background:#153522;color:#9ef0be;border-color:#1e6f3f}
    .warn{background:#3a2a10;color:#ffd083;border-color:#8b5a12}
    .bad{background:#3c1218;color:#ff9aa8;border-color:#812333}
    [data-theme='light'] .ok{background:#eafbee;color:#166534;border-color:#86efac}
    [data-theme='light'] .warn{background:#fff7e8;color:#92400e;border-color:#fcd34d}
    [data-theme='light'] .bad{background:#ffedf0;color:#991b1b;border-color:#fda4af}
    .mono{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace}
    .hidden{display:none!important}
    #prefs{display:none;position:fixed;top:12px;right:12px;width:min(420px,92vw);z-index:20;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px;box-shadow:0 18px 50px rgba(0,0,0,.35)}
    #prefs h3{margin:0 0 8px 0}
    .row{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:8px 0}
    .row label{color:var(--muted)}
    .row input[type='range']{width:150px}
    @media (max-width:980px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.two{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <div id='prefs'>
    <h3>⚙️ Customize</h3>
    <div class='row'><label>Theme</label><select id='pTheme'><option value='dark'>Dark</option><option value='light'>Light</option></select></div>
    <div class='row'><label>Font size</label><input id='pScale' type='range' min='85' max='130' step='5'></div>
    <div class='row'><label>Refresh (sec)</label><input id='pRefresh' type='number' min='5' max='120' step='1' style='width:80px'></div>
    <div class='row'><label>Show Health</label><input id='pHealth' type='checkbox'></div>
    <div class='row'><label>Show Pipelines</label><input id='pPipes' type='checkbox'></div>
    <div class='row'><label>Show Events</label><input id='pEvents' type='checkbox'></div>
    <div class='row'><label>Show Leaderboard</label><input id='pLeaders' type='checkbox'></div>
    <div class='row'>
      <button class='btn' onclick='savePrefs()'>Save</button>
      <button class='btn' onclick='resetPrefs()'>Reset</button>
      <button class='btn' onclick='togglePrefs(false)'>Close</button>
    </div>
  </div>

  <div class='wrap'>
    <div class='top'>
      <div>
        <h2 style='margin:0'>🦞 LobsterBoard</h2>
        <div class='sub'>AutoQuant V2 live operations board</div>
      </div>
      <div style='display:flex;gap:8px;align-items:center'>
        <span class='sub' id='updated'>Updated: —</span>
        <button class='btn' onclick='togglePrefs(true)'>Customize</button>
      </div>
    </div>

    <div class='grid'>
      <div class='card'><div class='k'>Backtests</div><div id='bt' class='v'>0</div></div>
      <div class='card'><div class='k'>Lessons</div><div id='ls' class='v'>0</div></div>
      <div class='card'><div class='k'>Research Cards</div><div id='rc' class='v'>0</div></div>
      <div class='card'><div class='k'>Event Log</div><div id='ev' class='v'>0</div></div>
    </div>

    <div id='secHealth' class='panel'>
      <h2>System Health</h2>
      <div><span id='healthStatus' class='badge warn'>WARN</span> <span id='healthText' class='sub'>Loading…</span></div>
    </div>

    <div class='two'>
      <div id='secEvents' class='panel'>
        <h2>Recent Events</h2>
        <table>
          <thead><tr><th>When</th><th>Severity</th><th>Event</th><th>Agent</th><th>Message</th></tr></thead>
          <tbody id='runs'></tbody>
        </table>
      </div>

      <div id='secPipes' class='panel'>
        <h2>Pipeline Runs</h2>
        <table>
          <thead><tr><th>Run</th><th>Status</th><th>Progress</th><th>Started</th></tr></thead>
          <tbody id='pipes'></tbody>
        </table>
      </div>
    </div>

    <div id='secLeaders' class='panel'>
      <h2>Leaderboard (QS ≥ 1.0)</h2>
      <table>
        <thead><tr><th>Asset</th><th>TF</th><th>Variant</th><th>QS</th><th>PF</th><th>DD</th><th>Trades</th></tr></thead>
        <tbody id='leaders'></tbody>
      </table>
    </div>
  </div>

<script>
let prefs = {};
let timer = null;

function defaults(){ return {theme:'dark',fontScale:100,refreshMs:10000,showHealth:true,showPipelines:true,showEvents:true,showLeaderboard:true}; }

function fmtAgo(ts){
  if(!ts) return '—';
  const d = new Date(ts); if(isNaN(d)) return ts;
  const s = Math.floor((Date.now()-d.getTime())/1000);
  if(s<60) return s+'s ago'; if(s<3600) return Math.floor(s/60)+'m ago'; if(s<86400) return Math.floor(s/3600)+'h ago';
  return Math.floor(s/86400)+'d ago';
}

function togglePrefs(show){ document.getElementById('prefs').style.display = show ? 'block' : 'none'; }

function applyPrefs(){
  document.documentElement.setAttribute('data-theme', prefs.theme || 'dark');
  document.body.style.setProperty('--scale', String((prefs.fontScale||100)/100));
  document.getElementById('secHealth').classList.toggle('hidden', !prefs.showHealth);
  document.getElementById('secPipes').classList.toggle('hidden', !prefs.showPipelines);
  document.getElementById('secEvents').classList.toggle('hidden', !prefs.showEvents);
  document.getElementById('secLeaders').classList.toggle('hidden', !prefs.showLeaderboard);

  document.getElementById('pTheme').value = prefs.theme;
  document.getElementById('pScale').value = prefs.fontScale;
  document.getElementById('pRefresh').value = Math.floor((prefs.refreshMs||10000)/1000);
  document.getElementById('pHealth').checked = !!prefs.showHealth;
  document.getElementById('pPipes').checked = !!prefs.showPipelines;
  document.getElementById('pEvents').checked = !!prefs.showEvents;
  document.getElementById('pLeaders').checked = !!prefs.showLeaderboard;

  if(timer) clearInterval(timer);
  timer = setInterval(refresh, Math.max(5000, prefs.refreshMs || 10000));
}

async function loadPrefs(){
  const local = localStorage.getItem('lobsterboard_prefs');
  if(local){
    try{ prefs = {...defaults(), ...JSON.parse(local)}; applyPrefs(); return; }catch{}
  }
  try{
    const r = await fetch('/prefs', {cache:'no-store'});
    const p = await r.json();
    prefs = {...defaults(), ...(p||{})};
  }catch{
    prefs = defaults();
  }
  applyPrefs();
}

async function savePrefs(){
  prefs.theme = document.getElementById('pTheme').value;
  prefs.fontScale = parseInt(document.getElementById('pScale').value || '100', 10);
  prefs.refreshMs = Math.max(5000, parseInt(document.getElementById('pRefresh').value || '10', 10) * 1000);
  prefs.showHealth = document.getElementById('pHealth').checked;
  prefs.showPipelines = document.getElementById('pPipes').checked;
  prefs.showEvents = document.getElementById('pEvents').checked;
  prefs.showLeaderboard = document.getElementById('pLeaders').checked;
  localStorage.setItem('lobsterboard_prefs', JSON.stringify(prefs));
  applyPrefs();
  try{ await fetch('/prefs', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(prefs)});}catch{}
  togglePrefs(false);
}

function resetPrefs(){
  prefs = defaults();
  localStorage.removeItem('lobsterboard_prefs');
  applyPrefs();
}

function setBadge(el, status){
  el.className='badge '+(status==='ok'?'ok':status==='warn'?'warn':'bad');
  el.textContent=status.toUpperCase();
}

async function refresh(){
  const r = await fetch('/data', {cache:'no-store'});
  const d = await r.json();
  document.getElementById('bt').textContent = d.stats.backtests;
  document.getElementById('ls').textContent = d.stats.lessons;
  document.getElementById('rc').textContent = d.stats.research_cards;
  document.getElementById('ev').textContent = d.stats.events;
  document.getElementById('updated').textContent = 'Updated: '+new Date().toLocaleTimeString();

  setBadge(document.getElementById('healthStatus'), d.health.status || 'warn');
  document.getElementById('healthText').textContent = d.health.summary || '';

  const runs = d.runs || [];
  document.getElementById('runs').innerHTML = runs.length ? runs.map(x=>
    `<tr><td class='sub'>${fmtAgo(x.ts)}</td><td><span class='badge ${x.sev==='warn'?'warn':x.sev==='error'?'bad':'ok'}'>${(x.sev||'info').toUpperCase()}</span></td><td class='mono'>${x.event||''}</td><td>${x.agent||''}</td><td>${x.msg||''}</td></tr>`
  ).join('') : '<tr><td colspan="5" class="sub">No recent events</td></tr>';

  const leaders = d.leaders || [];
  document.getElementById('leaders').innerHTML = leaders.length ? leaders.map(x=>
    `<tr><td>${x.asset}</td><td>${x.tf}</td><td class='mono'>${x.variant}</td><td>${x.qs.toFixed(2)}</td><td>${x.pf.toFixed(2)}</td><td>${x.dd.toFixed(1)}%</td><td>${x.tc}</td></tr>`
  ).join('') : '<tr><td colspan="7" class="sub">No qualified leaders yet</td></tr>';

  const pipes = d.pipelines || [];
  document.getElementById('pipes').innerHTML = pipes.length ? pipes.map(x=>
    `<tr><td class='mono'>${x.name}</td><td>${x.status}</td><td>${x.completed}/${x.total}</td><td class='sub'>${fmtAgo(x.start)}</td></tr>`
  ).join('') : '<tr><td colspan="4" class="sub">No pipeline runs yet</td></tr>';
}

window.onload = async () => { await loadPrefs(); await refresh(); };
</script>
</body>
</html>
"""


def load_prefs():
    try:
        if os.path.exists(PREFS_PATH):
            with open(PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**DEFAULT_PREFS, **data}
    except Exception:
        pass
    return dict(DEFAULT_PREFS)


def save_prefs(data):
    prefs = {**DEFAULT_PREFS, **(data or {})}
    os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
    with open(PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)
    return prefs


def fetch_data():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    stats = {
        "backtests": conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0],
        "lessons": conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0],
        "research_cards": conn.execute("SELECT COUNT(*) FROM research_cards").fetchone()[0],
        "events": conn.execute("SELECT COUNT(*) FROM event_log").fetchone()[0],
    }

    runs = [
        dict(r)
        for r in conn.execute(
            """
            SELECT ts_iso as ts, event_type as event, agent, severity as sev, substr(message,1,140) as msg
            FROM event_log
            ORDER BY ts_iso DESC
            LIMIT 16
            """
        ).fetchall()
    ]

    leaders = [
        {
            "asset": r["asset"],
            "tf": r["timeframe"],
            "variant": (r["variant_id"] or "")[:18],
            "qs": float(r["score_total"] or 0),
            "pf": float(r["profit_factor"] or 0),
            "dd": float(r["max_drawdown_pct"] or 0),
            "tc": int(r["total_trades"] or 0),
        }
        for r in conn.execute(
            """
            SELECT asset, timeframe, variant_id, score_total, profit_factor, max_drawdown_pct, total_trades
            FROM backtest_results
            WHERE COALESCE(score_total,0) >= 1.0
            ORDER BY COALESCE(xqscore_total, score_total, 0) DESC
            LIMIT 24
            """
        ).fetchall()
    ]

    pipes = [
        {
            "name": r["pipeline_name"] or r["run_id"],
            "status": r["status"],
            "completed": int(r["steps_completed"] or 0),
            "total": int(r["steps_total"] or 0),
            "start": r["ts_iso_start"],
        }
        for r in conn.execute(
            """
            SELECT pipeline_name, run_id, status, steps_completed, steps_total, ts_iso_start
            FROM pipeline_runs
            ORDER BY ts_iso_start DESC
            LIMIT 8
            """
        ).fetchall()
    ]

    issues = [r["msg"] for r in conn.execute("SELECT substr(message,1,120) as msg FROM event_log WHERE severity IN ('warn','error') ORDER BY ts_iso DESC LIMIT 5").fetchall()]
    health = {"status": "warn", "summary": issues[0]} if issues else {"status": "ok", "summary": "No recent warning/error events."}

    conn.close()
    return {"stats": stats, "runs": runs, "leaders": leaders, "pipelines": pipes, "health": health}


class H(BaseHTTPRequestHandler):
    def _send(self, status, data, ctype="application/json; charset=utf-8"):
        body = data if isinstance(data, (bytes, bytearray)) else json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/data":
            return self._send(200, fetch_data())
        if self.path == "/prefs":
            return self._send(200, load_prefs())
        return self._send(200, HTML.encode("utf-8"), ctype="text/html; charset=utf-8")

    def do_POST(self):
        if self.path != "/prefs":
            return self._send(404, {"error": "not_found"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(n) if n > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            prefs = save_prefs(payload)
            return self._send(200, {"ok": True, "prefs": prefs})
        except Exception as e:
            return self._send(400, {"ok": False, "error": str(e)})


if __name__ == "__main__":
    HTTPServer((HOST, PORT), H).serve_forever()
