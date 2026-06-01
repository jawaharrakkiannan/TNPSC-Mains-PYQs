# scripts/generate_html.py
import json
import os

INPUT_PATH  = "data/questions_tagged.json"
OUTPUT_PATH = "output/viewer.html"

_CSS = """\
:root{--bg:#F7F3EA;--card:#fff;--text:#1A1D2B;--muted:#5B6375;
  --border:#E6E0D5;--div:#F0EAE0;--accent:#6366f1;--acc-bg:#eef2ff;
  --acc-dark:#312e81;--acc-hover:#e8ecff}
@keyframes res-in{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text)}
header{position:sticky;top:0;z-index:20;background:var(--accent);color:#fff;
  padding:12px 24px;display:flex;align-items:center;gap:16px;
  box-shadow:0 2px 12px rgba(0,0,0,.15)}
header h1{font-family:'Playfair Display',serif;font-size:20px;font-weight:700}
.tab-grp{margin-left:auto;display:flex;gap:4px}
.tab-btn{padding:6px 16px;border:none;border-radius:8px;cursor:pointer;
  font-family:'DM Sans',sans-serif;font-size:13px;font-weight:600;
  background:rgba(255,255,255,.15);color:#fff;transition:background .15s}
.tab-btn.active{background:#fff;color:var(--acc-dark)}
#result-ct{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
  background:rgba(255,255,255,.2);padding:2px 8px;border-radius:4px}
.layout{display:flex;min-height:calc(100vh - 52px)}
aside{width:220px;flex-shrink:0;padding:16px;border-right:1px solid var(--border);
  background:var(--card);position:sticky;top:52px;height:calc(100vh - 52px);overflow-y:auto}
.sl{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
  letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:12px}
.fl{display:block;font-family:'JetBrains Mono',monospace;font-size:10px;
  letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);
  margin-bottom:4px;margin-top:10px}
select{width:100%;padding:6px 8px;border:1px solid var(--border);border-radius:6px;
  font-size:12px;background:var(--bg);color:var(--text)}
select:focus{outline:2px solid var(--accent)}
.btn-rst{width:100%;margin-top:14px;padding:7px;border:1px solid var(--border);
  border-radius:8px;background:var(--bg);color:var(--muted);
  font-size:12px;font-weight:600;cursor:pointer}
.btn-rst:hover{border-color:var(--accent);color:var(--accent)}
main{flex:1;padding:20px;max-width:860px}
.q-card{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:20px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.05);
  animation:res-in .3s cubic-bezier(.22,1,.36,1) both}
.q-meta{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.bm{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
  padding:2px 8px;border-radius:4px;background:var(--acc-bg);color:var(--acc-dark)}
.bm-m{background:#fef3c7;color:#92400e}
.qt{font-family:'Lora',serif;font-size:.9rem;line-height:1.78;margin-bottom:6px}
.qt-ta{color:var(--text)}
.qt-en{color:var(--muted);font-style:italic}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tag{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
  padding:2px 8px;border-radius:4px;border:1px solid var(--border);color:var(--muted)}
.tag-th{background:var(--acc-bg);border-color:#c7d2fe;color:var(--acc-dark)}
.tag-kw{background:#f0fdf4;border-color:#bbf7d0;color:#166534}
.empty{color:var(--muted);font-style:italic;padding:20px 0}
.freq-sec{margin-bottom:36px}
.freq-h{font-family:'Playfair Display',serif;font-size:18px;font-weight:700;
  margin-bottom:12px}
.tbl-wrap{overflow-x:auto}
.freq-tbl{border-collapse:collapse;min-width:100%;font-size:13px}
.freq-tbl thead tr{background:var(--acc-bg)}
.freq-tbl th{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
  letter-spacing:2px;text-transform:uppercase;color:var(--acc-dark);
  padding:10px 12px;border-bottom:2px solid var(--accent);
  position:sticky;top:0;background:var(--acc-bg);white-space:nowrap}
.freq-tbl td{padding:8px 12px;border-bottom:1px solid var(--div)}
.kc{font-weight:600;min-width:180px;cursor:pointer}
.kc:hover{color:var(--accent);text-decoration:underline}
.cc{text-align:center;font-family:'JetBrains Mono',monospace;font-size:12px;
  color:var(--muted);cursor:pointer}
.cc.has{color:var(--acc-dark);font-weight:700;background:var(--acc-bg)}
.cc:hover{background:var(--acc-hover)}
.tc{text-align:center;font-family:'JetBrains Mono',monospace;font-size:12px;
  font-weight:700;color:var(--acc-dark)}
"""

_JS = r"""
const QUESTIONS = __DATA__;
let filtered=QUESTIONS.slice(),view='questions';

function esc(s){const d=document.createElement('div');d.textContent=String(s??'');return d.innerHTML}

function init(){
  pop('f-year',[...new Set(QUESTIONS.map(q=>q.year))].sort((a,b)=>b-a));
  cascadeFromPaper();
}

function repop(id,vals,placeholder){
  const s=document.getElementById(id);
  const cur=s.value;
  while(s.firstChild)s.removeChild(s.firstChild);
  const def=document.createElement('option');
  def.value='';def.textContent=placeholder;
  s.appendChild(def);
  vals.forEach(v=>{const o=document.createElement('option');o.value=o.textContent=v;s.appendChild(o)});
  if(vals.includes(cur))s.value=cur;
}

function pop(id,vals){
  const s=document.getElementById(id);
  vals.forEach(v=>{const o=document.createElement('option');o.value=o.textContent=v;s.appendChild(o)});
}

function cascadeFromPaper(){
  const p=document.getElementById('f-paper').value;
  const base=QUESTIONS.filter(q=>!p||q.paper===p);
  repop('f-unit',[...new Set(base.map(q=>q.tags?.unit).filter(Boolean))].sort(),'All Units');
  cascadeFromUnit(base);
}

function cascadeFromUnit(base){
  if(!base){
    const p=document.getElementById('f-paper').value;
    base=QUESTIONS.filter(q=>!p||q.paper===p);
  }
  const u=document.getElementById('f-unit').value;
  const sub=base.filter(q=>!u||q.tags?.unit===u);
  repop('f-theme',[...new Set(sub.map(q=>q.tags?.theme).filter(Boolean))].sort(),'All Themes');
  cascadeFromTheme(sub);
}


function cascadeFromTheme(sub){
  if(!sub){
    const p=document.getElementById('f-paper').value;
    const u=document.getElementById('f-unit').value;
    sub=QUESTIONS.filter(q=>(!p||q.paper===p)&&(!u||q.tags?.unit===u));
  }
  const t=document.getElementById('f-theme').value;
  const mid=sub.filter(q=>!t||q.tags?.theme===t);
  repop('f-subtheme',[...new Set(mid.map(q=>q.tags?.subtheme).filter(Boolean))].sort(),'All Subthemes');
  cascadeFromSubtheme(mid);
}

function cascadeFromSubtheme(mid){
  if(!mid){
    const p=document.getElementById('f-paper').value;
    const u=document.getElementById('f-unit').value;
    const t=document.getElementById('f-theme').value;
    mid=QUESTIONS.filter(q=>(!p||q.paper===p)&&(!u||q.tags?.unit===u)&&(!t||q.tags?.theme===t));
  }
  const st=document.getElementById('f-subtheme').value;
  const leaf=mid.filter(q=>!st||q.tags?.subtheme===st);
  repop('f-keyword',[...new Set(leaf.map(q=>q.tags?.keyword).filter(Boolean))].sort(),'All Keywords');
  applyFilters();
}

function applyFilters(){
  const g=id=>document.getElementById(id).value;
  filtered=QUESTIONS.filter(q=>
    (!g('f-paper')   ||q.paper===g('f-paper'))&&
    (!g('f-year')    ||q.year==g('f-year'))&&
    (!g('f-unit')    ||q.tags?.unit===g('f-unit'))&&
    (!g('f-theme')   ||q.tags?.theme===g('f-theme'))&&
    (!g('f-subtheme')||q.tags?.subtheme===g('f-subtheme'))&&
    (!g('f-keyword') ||q.tags?.keyword===g('f-keyword'))&&
    (!g('f-section') ||q.section===g('f-section'))&&
    (!g('f-marks')   ||q.marks==g('f-marks'))
  );
  document.getElementById('result-ct').textContent=filtered.length+' questions';
  if(view==='questions')renderQs();else renderFreq();
}

function resetFilters(){
  ['f-paper','f-year','f-section','f-marks'].forEach(id=>document.getElementById(id).value='');
  cascadeFromPaper();
}

function switchView(v){
  view=v;
  document.getElementById('view-questions').style.display=v==='questions'?'':'none';
  document.getElementById('view-frequency').style.display=v==='frequency'?'':'none';
  document.querySelectorAll('.tab-btn').forEach((b,i)=>b.classList.toggle('active',(i===0)===(v==='questions')));
  if(v==='frequency')renderFreq();
}

function renderQs(){
  const c=document.getElementById('questions-list');
  if(!filtered.length){c.innerHTML='<p class="empty">No questions match the filters.</p>';return}
  c.innerHTML=filtered.map(q=>`
    <div class="q-card">
      <div class="q-meta">
        <span class="bm">${esc(q.paper)}</span>
        <span class="bm">${esc(q.year)}</span>
        <span class="bm">Unit ${esc(q.unit_number)}</span>
        <span class="bm">Sec ${esc(q.section)}</span>
        <span class="bm">Q${esc(q.question_number)}</span>
        <span class="bm bm-m">${esc(q.marks)}m</span>
        ${q.word_limit?`<span class="bm">${esc(q.word_limit)}w</span>`:''}
      </div>
      ${q.tamil ?`<p class="qt qt-ta">${esc(q.tamil)}</p>`:''}
      ${q.english?`<p class="qt qt-en">${esc(q.english)}</p>`:''}
      <div class="tags">
        ${q.tags?.theme   ?`<span class="tag">${esc(q.tags.theme)}</span>`:''}
        ${q.tags?.subtheme?`<span class="tag tag-th">${esc(q.tags.subtheme)}</span>`:''}
        ${q.tags?.keyword ?`<span class="tag tag-kw">${esc(q.tags.keyword)}</span>`:''}
      </div>
    </div>`).join('');
}

function renderFreq(){
  renderFreqTbl('themes-table',  q=>q.tags?.theme,   'Theme');
  renderFreqTbl('keywords-table',q=>q.tags?.keyword, 'Keyword');
}

function renderFreqTbl(id,keyFn,label){
  const years=[...new Set(filtered.map(q=>q.year))].sort((a,b)=>a-b);
  const keys=[...new Set(filtered.map(keyFn).filter(Boolean))].sort();
  if(!keys.length){document.getElementById(id).innerHTML='<p class="empty">No data.</p>';return}
  const counts={};
  filtered.forEach(q=>{const k=keyFn(q);if(!k)return;if(!counts[k])counts[k]={};counts[k][q.year]=(counts[k][q.year]||0)+1});
  const sorted=[...keys].sort((a,b)=>
    Object.values(counts[b]||{}).reduce((x,y)=>x+y,0)-
    Object.values(counts[a]||{}).reduce((x,y)=>x+y,0));
  const head=`<tr><th>${esc(label)}</th>${years.map(y=>`<th>${esc(y)}</th>`).join('')}<th>Total</th></tr>`;
  const rows=sorted.map(k=>{
    const tot=Object.values(counts[k]||{}).reduce((a,b)=>a+b,0);
    return `<tr>
      <td class="kc" onclick="filterByKY(${JSON.stringify(k)},null)">${esc(k)}</td>
      ${years.map(y=>{const n=counts[k]?.[y]||0;return`<td class="cc${n?' has':''}" onclick="filterByKY(${JSON.stringify(k)},${y})">${n||''}</td>`}).join('')}
      <td class="tc">${tot}</td></tr>`;
  }).join('');
  document.getElementById(id).innerHTML=`<table class="freq-tbl"><thead>${head}</thead><tbody>${rows}</tbody></table>`;
}

function filterByKY(key,year){
  if(year)document.getElementById('f-year').value=year;
  const thOpts=[...document.getElementById('f-theme').options].map(o=>o.value);
  const stOpts=[...document.getElementById('f-subtheme').options].map(o=>o.value);
  if(thOpts.includes(key))document.getElementById('f-theme').value=key;
  else if(stOpts.includes(key))document.getElementById('f-subtheme').value=key;
  else document.getElementById('f-keyword').value=key;
  switchView('questions');applyFilters();
}

init();
"""


def generate_html(questions: list[dict]) -> str:
    data_json = json.dumps(questions, ensure_ascii=False)
    js = _JS.replace("__DATA__", data_json)
    return f"""<!DOCTYPE html>
<html lang="ta">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TNPSC Group I Mains - Question Bank</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=DM+Sans:wght@400;500;600;700&family=Lora:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>TNPSC Group I Mains</h1>
  <span id="result-ct">- questions</span>
  <div class="tab-grp">
    <button class="tab-btn active" onclick="switchView('questions')">Questions</button>
    <button class="tab-btn" onclick="switchView('frequency')">Frequency</button>
  </div>
</header>
<div class="layout">
  <aside>
    <div class="sl">Filters</div>
    <label class="fl">Paper</label>
    <select id="f-paper" onchange="cascadeFromPaper()">
      <option value="">All Papers</option>
      <option>Paper I</option><option>Paper II</option><option>Paper III</option>
    </select>
    <label class="fl">Year</label>
    <select id="f-year" onchange="applyFilters()"><option value="">All Years</option></select>
    <label class="fl">Unit</label>
    <select id="f-unit" onchange="cascadeFromUnit()"><option value="">All Units</option></select>
    <label class="fl">Theme</label>
    <select id="f-theme" onchange="cascadeFromTheme()"><option value="">All Themes</option></select>
    <label class="fl">Subtheme</label>
    <select id="f-subtheme" onchange="cascadeFromSubtheme()"><option value="">All Subthemes</option></select>
    <label class="fl">Keyword</label>
    <select id="f-keyword" onchange="applyFilters()"><option value="">All Keywords</option></select>
    <label class="fl">Section</label>
    <select id="f-section" onchange="applyFilters()">
      <option value="">All</option><option>A</option><option>B</option><option>C</option>
    </select>
    <label class="fl">Marks</label>
    <select id="f-marks" onchange="applyFilters()">
      <option value="">All</option><option>3</option><option>10</option><option>15</option>
    </select>
    <button class="btn-rst" onclick="resetFilters()">Reset Filters</button>
  </aside>
  <main>
    <div id="view-questions">
      <div id="questions-list"></div>
    </div>
    <div id="view-frequency" style="display:none">
      <div class="freq-sec">
        <h3 class="freq-h">Themes x Years</h3>
        <div class="tbl-wrap" id="themes-table"></div>
      </div>
      <div class="freq-sec">
        <h3 class="freq-h">Keywords x Years</h3>
        <div class="tbl-wrap" id="keywords-table"></div>
      </div>
    </div>
  </main>
</div>
<script>{js}</script>
</body>
</html>"""


def main() -> None:
    with open(INPUT_PATH, encoding="utf-8") as f:
        questions = json.load(f)
    html = generate_html(questions)
    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Viewer written to {OUTPUT_PATH} ({len(questions)} questions)")


if __name__ == "__main__":
    main()
