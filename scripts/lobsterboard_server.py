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

DEFAULT_LAYOUT = [
    {"id": "w_stats", "type": "stats", "title": "Top Stats", "x": 1, "y": 1, "w": 12, "h": 2, "visible": True},
    {"id": "w_health", "type": "health", "title": "System Health", "x": 1, "y": 3, "w": 4, "h": 2, "visible": True},
    {"id": "w_pipes", "type": "pipelines", "title": "Pipeline Runs", "x": 5, "y": 3, "w": 8, "h": 3, "visible": True},
    {"id": "w_events", "type": "events", "title": "Recent Events", "x": 1, "y": 5, "w": 8, "h": 5, "visible": True},
    {"id": "w_hippo", "type": "hippo", "title": "Hippo Widget", "x": 9, "y": 6, "w": 4, "h": 2, "visible": True},
    {"id": "w_leaders", "type": "leaders", "title": "Leaderboard", "x": 1, "y": 10, "w": 12, "h": 5, "visible": True},
]

DEFAULT_PREFS = {
    "theme": "dark",
    "fontScale": 100,
    "refreshMs": 10000,
    "layout": DEFAULT_LAYOUT,
}

HTML = """<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>LobsterBoard Builder</title>
  <style>
    :root{--bg:#0a0f1f;--panel:#101a33;--line:#263454;--txt:#eaf1ff;--muted:#9fb2d6;--ok:#22c55e;--warn:#f59e0b;--bad:#ef4444}
    [data-theme='light']{--bg:#eef3ff;--panel:#fff;--line:#cad7ef;--txt:#0f1f41;--muted:#586d94}
    *{box-sizing:border-box}
    body{margin:0;font-family:Inter,system-ui;background:var(--bg);color:var(--txt);font-size:calc(14px * var(--scale,1));}
    .top{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:10}
    .btn{border:1px solid var(--line);background:var(--panel);color:var(--txt);border-radius:10px;padding:6px 10px;cursor:pointer}
    .muted{color:var(--muted)}
    .shell{display:grid;grid-template-columns:280px 1fr;gap:10px;padding:10px}
    #sidebar{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px;max-height:calc(100vh - 80px);overflow:auto}
    #sidebar h3{margin:6px 0 8px 0}
    .row{display:flex;justify-content:space-between;align-items:center;margin:8px 0;gap:8px}
    .row input,.row select{width:120px;background:#0000;border:1px solid var(--line);color:var(--txt);padding:4px 6px;border-radius:8px}
    .grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-auto-rows:74px;gap:8px;min-height:80vh}
    .widget{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:8px;overflow:auto}
    .widget.selected{outline:2px solid #60a5fa}
    .wh{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;font-weight:600}
    .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;border:1px solid transparent}
    .ok{background:#163b27;color:#9ef0be;border-color:#2b8f58}
    .warn{background:#3b2b12;color:#ffd083;border-color:#9a6518}
    .bad{background:#41131b;color:#ff9aa8;border-color:#8f2738}
    table{width:100%;border-collapse:collapse;font-size:12px}
    th,td{padding:6px;border-bottom:1px solid var(--line);text-align:left}
    th{color:var(--muted)}
    .stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
    .card{border:1px solid var(--line);border-radius:10px;padding:8px}
    .v{font-size:22px;font-weight:700}
    @media (max-width:1100px){.shell{grid-template-columns:1fr} #sidebar{order:2}}
  </style>
</head>
<body>
  <div class='top'>
    <div><b>🦞 LobsterBoard Builder</b> <span class='muted'>live grid layout</span></div>
    <div style='display:flex;gap:8px;align-items:center'>
      <span id='updated' class='muted'>Updated: —</span>
      <button class='btn' id='toggleEdit' onclick='toggleEdit()'>Edit Mode</button>
      <button class='btn' onclick='savePrefs()'>Save</button>
    </div>
  </div>

  <div class='shell'>
    <aside id='sidebar'>
      <h3>⚙️ Dashboard Builder</h3>
      <div class='row'><label>Theme</label><select id='theme'><option value='dark'>Dark</option><option value='light'>Light</option></select></div>
      <div class='row'><label>Font %</label><input id='font' type='number' min='80' max='140' step='5'></div>
      <div class='row'><label>Refresh sec</label><input id='refresh' type='number' min='5' max='120'></div>
      <hr style='border-color:var(--line)'>
      <div class='row'><label><b>Sacred Select</b></label><select id='selectedWidget'></select></div>
      <div class='row'><button class='btn' onclick='moveSel(0,-1)'>↑</button><button class='btn' onclick='moveSel(-1,0)'>←</button><button class='btn' onclick='moveSel(1,0)'>→</button><button class='btn' onclick='moveSel(0,1)'>↓</button></div>
      <div class='row'><button class='btn' onclick='resizeSel(1,0)'>W+</button><button class='btn' onclick='resizeSel(-1,0)'>W-</button><button class='btn' onclick='resizeSel(0,1)'>H+</button><button class='btn' onclick='resizeSel(0,-1)'>H-</button></div>
      <div class='row'><button class='btn' onclick='toggleSelVis()'>Show/Hide</button><button class='btn' onclick='removeSel()'>Delete</button></div>
      <hr style='border-color:var(--line)'>
      <h3>Add Widget</h3>
      <div class='row'><button class='btn' onclick="addWidget('health')">Health</button><button class='btn' onclick="addWidget('events')">Events</button></div>
      <div class='row'><button class='btn' onclick="addWidget('pipelines')">Pipelines</button><button class='btn' onclick="addWidget('leaders')">Leaderboard</button></div>
      <div class='row'><button class='btn' onclick="addWidget('stats')">Stats</button><button class='btn' onclick="addWidget('hippo')">Hippo</button></div>
      <p class='muted'>Tip: click a widget on the grid, then move/resize with controls.</p>
    </aside>

    <main>
      <div id='grid' class='grid'></div>
    </main>
  </div>

<script>
let prefs = null;
let data = null;
let selectedId = null;
let editMode = false;
let timer = null;

const defaults = () => ({theme:'dark', fontScale:100, refreshMs:10000, layout:[]});
const titleByType = (t) => ({stats:'Top Stats', health:'System Health', events:'Recent Events', pipelines:'Pipeline Runs', leaders:'Leaderboard', hippo:'Hippo Widget'}[t] || t);

function applyPrefs(){
  document.documentElement.setAttribute('data-theme', prefs.theme || 'dark');
  document.body.style.setProperty('--scale', String((prefs.fontScale||100)/100));
  document.getElementById('theme').value = prefs.theme;
  document.getElementById('font').value = prefs.fontScale;
  document.getElementById('refresh').value = Math.floor((prefs.refreshMs||10000)/1000);
  renderGrid();
  if (timer) clearInterval(timer);
  timer = setInterval(refreshData, Math.max(5000, prefs.refreshMs||10000));
}

function widgetHTML(w){
  if (!data) return '<div class="muted">Loading…</div>';
  if (w.type === 'stats') {
    const s = data.stats || {};
    return `<div class='stats'>
      <div class='card'><div class='muted'>Backtests</div><div class='v'>${s.backtests||0}</div></div>
      <div class='card'><div class='muted'>Lessons</div><div class='v'>${s.lessons||0}</div></div>
      <div class='card'><div class='muted'>Research</div><div class='v'>${s.research_cards||0}</div></div>
      <div class='card'><div class='muted'>Events</div><div class='v'>${s.events||0}</div></div>
    </div>`;
  }
  if (w.type === 'health') {
    const h = data.health || {status:'warn',summary:'No data'};
    const cls = h.status==='ok'?'ok':h.status==='warn'?'warn':'bad';
    return `<p><span class='badge ${cls}'>${(h.status||'warn').toUpperCase()}</span></p><p class='muted'>${h.summary||''}</p>`;
  }
  if (w.type === 'events') {
    const arr = data.runs || [];
    if (!arr.length) return '<div class="muted">No events</div>';
    return `<table><thead><tr><th>When</th><th>Event</th><th>Agent</th></tr></thead><tbody>${arr.slice(0,14).map(x=>`<tr><td class='muted'>${x.ts?.slice(11,19)||''}</td><td>${x.event||''}</td><td>${x.agent||''}</td></tr>`).join('')}</tbody></table>`;
  }
  if (w.type === 'pipelines') {
    const arr = data.pipelines || [];
    if (!arr.length) return '<div class="muted">No pipeline runs</div>';
    return `<table><thead><tr><th>Run</th><th>Status</th><th>Progress</th></tr></thead><tbody>${arr.map(x=>`<tr><td class='mono'>${x.name||''}</td><td>${x.status||''}</td><td>${x.completed||0}/${x.total||0}</td></tr>`).join('')}</tbody></table>`;
  }
  if (w.type === 'leaders') {
    const arr = data.leaders || [];
    if (!arr.length) return '<div class="muted">No QS ≥ 1.0 yet</div>';
    return `<table><thead><tr><th>Asset</th><th>TF</th><th>Variant</th><th>QS</th><th>PF</th></tr></thead><tbody>${arr.slice(0,18).map(x=>`<tr><td>${x.asset}</td><td>${x.tf}</td><td class='mono'>${x.variant}</td><td>${x.qs.toFixed(2)}</td><td>${x.pf.toFixed(2)}</td></tr>`).join('')}</tbody></table>`;
  }
  if (w.type === 'hippo') {
    return `<div style='font-size:26px'>🦛</div><div class='muted'>Hippo says: stay calm, iterate hard, trust the data.</div>`;
  }
  return '<div class="muted">Unknown widget</div>';
}

function renderGrid(){
  const grid = document.getElementById('grid');
  grid.innerHTML = '';

  const layout = (prefs.layout||[]).filter(w=>w.visible!==false);
  layout.forEach(w=>{
    const d = document.createElement('div');
    d.className = 'widget'+(w.id===selectedId?' selected':'');
    d.style.gridColumn = `${w.x} / span ${w.w}`;
    d.style.gridRow = `${w.y} / span ${w.h}`;
    d.dataset.id = w.id;
    d.onclick = () => { if(editMode){ selectedId = w.id; refreshSelect(); renderGrid(); } };
    d.innerHTML = `<div class='wh'><span>${w.title || titleByType(w.type)}</span>${editMode?'<span class="muted mono">'+w.id+'</span>':''}</div>${widgetHTML(w)}`;
    grid.appendChild(d);
  });
  refreshSelect();
}

function refreshSelect(){
  const sel = document.getElementById('selectedWidget');
  sel.innerHTML = (prefs.layout||[]).map(w=>`<option value='${w.id}'>${w.title || w.type} (${w.id})</option>`).join('');
  if(selectedId){ sel.value = selectedId; }
  sel.onchange = () => { selectedId = sel.value; renderGrid(); };
}

function getSel(){
  if(!selectedId) return null;
  return (prefs.layout||[]).find(x=>x.id===selectedId) || null;
}

function clampWidget(w){
  w.w = Math.max(2, Math.min(12, w.w));
  w.h = Math.max(1, Math.min(10, w.h));
  w.x = Math.max(1, Math.min(13-w.w, w.x));
  w.y = Math.max(1, Math.min(40, w.y));
}

function moveSel(dx,dy){ const w=getSel(); if(!w) return; w.x+=dx; w.y+=dy; clampWidget(w); renderGrid(); }
function resizeSel(dw,dh){ const w=getSel(); if(!w) return; w.w+=dw; w.h+=dh; clampWidget(w); renderGrid(); }
function toggleSelVis(){ const w=getSel(); if(!w) return; w.visible = !(w.visible!==false); renderGrid(); }
function removeSel(){ if(!selectedId) return; prefs.layout = (prefs.layout||[]).filter(x=>x.id!==selectedId); selectedId=null; renderGrid(); }

function addWidget(type){
  const id = 'w_'+type+'_'+Math.random().toString(16).slice(2,6);
  const w = {id, type, title:titleByType(type), x:1, y:1, w: type==='stats'?12:6, h: type==='leaders'?4: (type==='events'||type==='pipelines'?3:2), visible:true};
  prefs.layout.push(w);
  selectedId=id;
  renderGrid();
}

function toggleEdit(){
  editMode = !editMode;
  document.getElementById('toggleEdit').textContent = editMode ? 'Exit Edit' : 'Edit Mode';
  document.getElementById('sidebar').style.display = editMode ? 'block' : 'none';
  renderGrid();
}

async function savePrefs(){
  prefs.theme = document.getElementById('theme').value;
  prefs.fontScale = parseInt(document.getElementById('font').value||'100',10);
  prefs.refreshMs = Math.max(5000, parseInt(document.getElementById('refresh').value||'10',10)*1000);
  localStorage.setItem('lobsterboard_prefs', JSON.stringify(prefs));
  applyPrefs();
  await fetch('/prefs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(prefs)});
}

async function refreshData(){
  const r = await fetch('/data', {cache:'no-store'});
  data = await r.json();
  document.getElementById('updated').textContent = 'Updated: '+new Date().toLocaleTimeString();
  renderGrid();
}

async function init(){
  let p = null;
  try{ p = JSON.parse(localStorage.getItem('lobsterboard_prefs')||'null'); }catch{}
  if(!p){
    try{ p = await (await fetch('/prefs',{cache:'no-store'})).json(); }catch{ p = null; }
  }
  prefs = {...defaults(), ...(p||{})};
  if(!prefs.layout || !prefs.layout.length) prefs.layout = JSON.parse(JSON.stringify((defaults().layout||[])));
  applyPrefs();
  await refreshData();
  toggleEdit(); toggleEdit();
}

window.onload = init;
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
                    merged = {**DEFAULT_PREFS, **data}
                    if not merged.get("layout"):
                        merged["layout"] = DEFAULT_LAYOUT
                    return merged
    except Exception:
        pass
    return dict(DEFAULT_PREFS)


def save_prefs(data):
    prefs = {**DEFAULT_PREFS, **(data or {})}
    if not prefs.get("layout"):
        prefs["layout"] = DEFAULT_LAYOUT
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
            "SELECT ts_iso as ts, event_type as event, agent, severity as sev, substr(message,1,140) as msg FROM event_log ORDER BY ts_iso DESC LIMIT 20"
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
            "SELECT asset,timeframe,variant_id,score_total,profit_factor,max_drawdown_pct,total_trades FROM backtest_results WHERE COALESCE(score_total,0)>=1.0 ORDER BY COALESCE(xqscore_total,score_total,0) DESC LIMIT 30"
        ).fetchall()
    ]

    pipelines = [
        {
            "name": r["pipeline_name"] or r["run_id"],
            "status": r["status"],
            "completed": int(r["steps_completed"] or 0),
            "total": int(r["steps_total"] or 0),
            "start": r["ts_iso_start"],
        }
        for r in conn.execute(
            "SELECT pipeline_name,run_id,status,steps_completed,steps_total,ts_iso_start FROM pipeline_runs ORDER BY ts_iso_start DESC LIMIT 10"
        ).fetchall()
    ]

    issues = [r["msg"] for r in conn.execute("SELECT substr(message,1,120) as msg FROM event_log WHERE severity IN ('warn','error') ORDER BY ts_iso DESC LIMIT 5").fetchall()]
    health = {"status": "warn", "summary": issues[0]} if issues else {"status": "ok", "summary": "No recent warning/error events."}

    conn.close()
    return {"stats": stats, "runs": runs, "leaders": leaders, "pipelines": pipelines, "health": health}


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
