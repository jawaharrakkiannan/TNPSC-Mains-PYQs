# scripts/review_server.py
import json
import os
from flask import Flask, jsonify, render_template_string, request

RAW_PATH       = "data/questions_raw.json"
CORRECTED_PATH = "data/questions_corrected.json"

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TNPSC PYQ Review</title>
<style>
:root{--bg:#F7F3EA;--card:#fff;--text:#1A1D2B;--muted:#5B6375;
  --border:#E6E0D5;--accent:#6366f1;--flag:#fefce8;--flag-b:#f59e0b}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text)}
header{position:sticky;top:0;z-index:20;background:var(--accent);color:#fff;
  padding:12px 20px;display:flex;align-items:center;gap:16px}
header h1{font-size:18px;font-weight:700}
#saved{font-size:12px;opacity:0;transition:opacity .3s}
#saved.show{opacity:1}
.layout{display:flex;min-height:calc(100vh - 48px)}
aside{width:200px;flex-shrink:0;padding:16px;border-right:1px solid var(--border);
  background:var(--card);position:sticky;top:48px;height:calc(100vh - 48px);overflow-y:auto}
aside h2{font-size:10px;font-family:monospace;letter-spacing:2px;text-transform:uppercase;
  color:var(--muted);margin-bottom:12px}
select{width:100%;margin-bottom:10px;padding:6px 8px;border:1px solid var(--border);
  border-radius:6px;font-size:12px}
label.chk{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);
  margin-bottom:8px}
main{flex:1;padding:20px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:20px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.card.flagged{background:var(--flag);border-color:var(--flag-b)}
.card-top{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px;align-items:center}
.badge{font-family:monospace;font-size:11px;font-weight:700;padding:2px 8px;
  border-radius:4px;background:#eef2ff;color:#312e81}
.badge.flag-b{background:#fef3c7;color:#92400e}
textarea,input[type=text],input[type=number]{width:100%;border:1px solid var(--border);
  border-radius:8px;padding:8px 12px;font-size:14px;font-family:'Lora',serif;
  line-height:1.7;resize:vertical;color:var(--text);background:var(--bg)}
textarea:focus,input:focus{outline:2px solid var(--accent)}
.meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
.meta>div{flex:1;min-width:70px}
.field-lbl{display:block;font-family:monospace;font-size:10px;letter-spacing:1px;
  text-transform:uppercase;color:var(--muted);margin:10px 0 4px}
.rev{display:flex;align-items:center;gap:8px;margin-top:12px;
  font-size:12px;color:var(--muted)}
.rev input{width:auto}
</style>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Lora:wght@400;600&display=swap" rel="stylesheet">
</head>
<body>
<header>
  <h1>TNPSC PYQ Review</h1>
  <span id="status-txt">Loading...</span>
  <span id="saved">&#10003; Saved</span>
</header>
<div class="layout">
  <aside>
    <h2>Filters</h2>
    <select id="f-paper" onchange="render()">
      <option value="">All Papers</option>
      <option>Paper I</option><option>Paper II</option><option>Paper III</option>
    </select>
    <select id="f-year" onchange="render()"><option value="">All Years</option></select>
    <label class="chk"><input type="checkbox" id="f-flag" onchange="render()"> Flagged only</label>
    <label class="chk"><input type="checkbox" id="f-unrev" onchange="render()"> Unreviewed only</label>
  </aside>
  <main id="main"></main>
</div>
<script>
function badge(text, extra) {
  var s = document.createElement('span');
  s.className = 'badge' + (extra ? ' ' + extra : '');
  s.textContent = text;
  return s;
}
function lbl(text) {
  var d = document.createElement('span');
  d.className = 'field-lbl';
  d.textContent = text;
  return d;
}
function makeTextarea(val, rows, cb) {
  var t = document.createElement('textarea');
  t.rows = rows;
  t.value = val != null ? String(val) : '';
  t.addEventListener('input', function(){ cb(t.value); });
  return t;
}
function makeInput(type, val, cb) {
  var inp = document.createElement('input');
  inp.type = type;
  inp.value = val != null ? String(val) : '';
  inp.addEventListener('input', function(){
    cb(type === 'number' ? +inp.value : inp.value);
  });
  return inp;
}
let qs = [], timer = null;
async function load() {
  qs = await (await fetch('/api/questions')).json();
  var years = [...new Set(qs.map(function(q){ return q.year; }))].sort(function(a,b){return b-a;});
  var sel = document.getElementById('f-year');
  years.forEach(function(y){
    var o = document.createElement('option');
    o.value = y;
    o.textContent = y;
    sel.appendChild(o);
  });
  render();
  updateStatus();
}
function getFiltered() {
  var p = document.getElementById('f-paper').value;
  var y = document.getElementById('f-year').value;
  var fl = document.getElementById('f-flag').checked;
  var ur = document.getElementById('f-unrev').checked;
  return qs.filter(function(q){
    return (!p || q.paper === p) && (!y || q.year == y) &&
           (!fl || q.noise_flagged) && (!ur || !q._reviewed);
  });
}
function buildCard(q, idx) {
  var card = document.createElement('div');
  card.className = 'card' + (q.noise_flagged ? ' flagged' : '');
  var top = document.createElement('div');
  top.className = 'card-top';
  top.appendChild(badge(q.paper));
  top.appendChild(badge(q.year));
  top.appendChild(badge('Unit ' + q.unit_number));
  top.appendChild(badge('Sec ' + q.section));
  top.appendChild(badge('Q' + q.question_number));
  top.appendChild(badge(q.marks + 'm'));
  if (q.noise_flagged) top.appendChild(badge('⚠ Flagged', 'flag-b'));
  card.appendChild(top);
  card.appendChild(lbl('Tamil'));
  card.appendChild(makeTextarea(q.tamil, 3, function(v){ upd(idx,'tamil',v); }));
  card.appendChild(lbl('English'));
  card.appendChild(makeTextarea(q.english, 3, function(v){ upd(idx,'english',v); }));
  var meta = document.createElement('div');
  meta.className = 'meta';
  function metaField(labelText, type, fieldKey, val) {
    var wrap = document.createElement('div');
    wrap.appendChild(lbl(labelText));
    wrap.appendChild(makeInput(type, val, function(v){ upd(idx, fieldKey, v); }));
    meta.appendChild(wrap);
  }
  metaField('Marks', 'number', 'marks', q.marks);
  metaField('Word limit', 'number', 'word_limit', q.word_limit);
  metaField('Unit', 'text', 'unit_number', q.unit_number);
  metaField('Section', 'text', 'section', q.section);
  card.appendChild(meta);
  var rev = document.createElement('div');
  rev.className = 'rev';
  var cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.checked = !!q._reviewed;
  cb.addEventListener('change', function(){ upd(idx, '_reviewed', cb.checked); });
  var sp = document.createElement('span');
  sp.textContent = 'Reviewed';
  rev.appendChild(cb);
  rev.appendChild(sp);
  card.appendChild(rev);
  return card;
}
function render() {
  var filtered = getFiltered();
  var main = document.getElementById('main');
  while (main.firstChild) main.removeChild(main.firstChild);
  filtered.forEach(function(q){ main.appendChild(buildCard(q, qs.indexOf(q))); });
}
function upd(idx, field, val) {
  qs[idx][field] = val;
  clearTimeout(timer);
  timer = setTimeout(save, 500);
}
async function save() {
  var r = await fetch('/api/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(qs)
  });
  if (r.ok) {
    var s = document.getElementById('saved');
    s.classList.add('show');
    setTimeout(function(){ s.classList.remove('show'); }, 2000);
  }
  updateStatus();
}
function updateStatus() {
  var rev = qs.filter(function(q){ return q._reviewed; }).length;
  document.getElementById('status-txt').textContent = rev + ' / ' + qs.length + ' reviewed';
}
function esc(s){var d=document.createElement('div');d.textContent=String(s??'');return d.innerHTML}
load();
</script>
</body>
</html>"""


def create_app(raw_path: str = RAW_PATH, corrected_path: str = CORRECTED_PATH) -> Flask:
    app = Flask(__name__)
    app.config.update(RAW_PATH=raw_path, CORRECTED_PATH=corrected_path)

    def _load():
        cp = app.config["CORRECTED_PATH"]
        rp = app.config["RAW_PATH"]
        path = cp if os.path.exists(cp) else rp
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @app.get("/")
    def index():
        return render_template_string(_HTML)

    @app.get("/api/questions")
    def get_questions():
        return jsonify(_load())

    @app.post("/api/save")
    def save_questions():
        data = request.get_json()
        cp = app.config["CORRECTED_PATH"]
        os.makedirs(os.path.dirname(os.path.abspath(cp)), exist_ok=True)
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True})

    @app.get("/api/status")
    def status():
        qs = _load()
        reviewed = sum(1 for q in qs if q.get("_reviewed"))
        return jsonify({"total": len(qs), "reviewed": reviewed})

    return app


if __name__ == "__main__":
    app = create_app()
    print("Review server: http://localhost:5000")
    app.run(debug=True, port=5000)
