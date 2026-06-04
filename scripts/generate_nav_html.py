# scripts/generate_nav_html.py
"""
Drill-down navigator HTML.
  Landing   : Paper × Theme table  (click paper or theme → Paper page)
  Paper page: Theme × Subtheme table  (click subtheme → Detail page)
              If no themes tagged: Unit × Questions table directly
  Detail    : Subtheme × Keyword table  +  Keyword × Question × Year table
"""
import json
import os

INPUT_PATH  = "data/questions_tagged.json"
OUTPUT_PATH = "output/navigator.html"


_CSS = """\
:root {
  --bg: #fff7ed; --bg2: #ffedd5; --surface: #ffffff;
  --border: #e2e8f0; --border2: #cbd5e1;
  --text: #111827; --text2: #374151; --text3: #6b7280;
  --accent: #ea580c;
  --accent2: rgba(234,88,12,.11); --accent3: rgba(234,88,12,.05);
  --radius: 2px;
  --font-mono: 'IBM Plex Mono', monospace;
  --font-body: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
button, input { font-family: inherit; font-size: inherit; }
html { scroll-behavior: smooth; overflow-x: hidden; }
body {
  font-family: var(--font-body);
  background-color: var(--bg);
  background-image: repeating-linear-gradient(
    transparent 0, transparent 1.65rem,
    rgba(180,120,60,.06) 1.65rem, rgba(180,120,60,.06) calc(1.65rem + 1px));
  color: var(--text); line-height: 1.65; min-height: 100vh;
}
body::after {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 9999; opacity: .035;
  background-image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.75' numOctaves='4' stitchTiles='stitch'/></filter><rect width='256' height='256' filter='url(%23n)'/></svg>");
}
.top-bar {
  background: var(--bg2); border-bottom: 1px solid var(--border);
  padding: .35rem 1.5rem; display: flex; justify-content: space-between;
  align-items: center; font-family: var(--font-mono); font-size: .6rem;
  letter-spacing: .08em; color: var(--text3); flex-wrap: wrap; gap: .4rem;
}
.top-bar a { color: var(--accent); text-decoration: none; }
.top-bar a:hover { text-decoration: underline; }
.page-shell { max-width: 1100px; margin: 0 auto; padding: 0 1.5rem 5rem; }
header { text-align: center; padding: 0 1rem; margin-bottom: 2rem; animation: fadeUp .7s ease both; }
.masthead-rule {
  border: none; border-top: 3px solid var(--text); border-bottom: 1px solid var(--text);
  height: 5px; margin: 2rem 0 1.25rem; background: transparent;
}
.masthead-rule.bottom { margin: 1.25rem 0 0; }
header h1 {
  font-size: clamp(2rem,5vw,3.4rem); font-weight: 700;
  color: var(--text); line-height: 1.1; letter-spacing: .005em; margin-bottom: .7rem;
}
header h1 em { font-style: italic; font-weight: 400; color: var(--accent); }
.header-sub {
  font-family: var(--font-mono); font-size: .68rem; color: var(--text2);
  letter-spacing: .14em; text-transform: uppercase;
}
.site-footer {
  max-width: 1100px; margin: 3rem auto 0; padding: 1rem 0;
  border-top: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: .5rem;
  font-family: var(--font-mono); font-size: .6rem; letter-spacing: .08em; color: var(--text3);
}
.site-footer a { color: var(--accent); text-decoration: none; }

/* ── Page nav bar ──────────────────────────────────── */
.page-nav {
  display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;
  padding-bottom: .75rem; border-bottom: 1px solid var(--border);
}
.back-btn {
  font-family: var(--font-mono); font-size: .65rem; font-weight: 500;
  padding: .25rem .7rem; border: 1px solid var(--border2); border-radius: var(--radius);
  background: none; cursor: pointer; color: var(--text3);
  transition: border-color .1s, color .1s; white-space: nowrap;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }
.page-nav-title {
  font-family: var(--font-mono); font-size: .7rem; color: var(--text2);
  letter-spacing: .06em;
}

/* ── Section headings ──────────────────────────────── */
.section-label {
  font-size: .6rem; font-family: var(--font-mono); font-weight: 500;
  text-transform: uppercase; letter-spacing: .1em; color: var(--text3);
  margin-bottom: .6rem; margin-top: 2rem;
}
.section-label:first-child { margin-top: 0; }

/* ── Nav table ─────────────────────────────────────── */
.nav-table { width: 100%; border-collapse: collapse; font-size: .87rem; }
.nav-table th {
  background: var(--bg2); padding: .4rem .85rem;
  border-bottom: 2px solid var(--border2);
  font-family: var(--font-mono); font-size: .58rem; text-transform: uppercase;
  letter-spacing: .09em; color: var(--text3); text-align: left; white-space: nowrap;
}
.nav-table td { padding: .55rem .85rem; border: 1px solid var(--border); vertical-align: top; }
.nav-table tr:hover td { background: var(--accent3); }
.row-hover td { background: var(--accent2) !important; }
.row-hover .paper-cell  { border-left-color: var(--accent) !important; }
.row-hover .theme-cell  { border-left-color: var(--accent) !important; }
.row-hover .kw-cell     { border-left-color: var(--accent) !important; }

.paper-cell {
  font-weight: 600; font-size: .85rem;
  border-left: 3px solid transparent !important;
  background: var(--bg2); width: 18%; min-width: 9rem;
  transition: border-left-color .12s;
}
.paper-name { color: var(--text); }
.paper-desc { font-family: var(--font-mono); font-size: .6rem; color: var(--text3); margin-top: .2rem; font-weight: 400; }
.theme-cell {
  font-weight: 500; font-size: .82rem;
  border-left: 3px solid transparent !important;
  color: var(--text2); width: 30%; min-width: 12rem;
  transition: border-left-color .12s;
}
.sub-cell  { font-size: .85rem; color: var(--text); }
.kw-cell   {
  font-size: .78rem; font-weight: 500; color: var(--text2);
  border-left: 3px solid transparent !important;
  width: 22%; min-width: 10rem; transition: border-left-color .12s;
}
.muted { color: var(--text3); font-style: italic; }
.clickable { cursor: pointer; }
.clickable:hover { background: var(--accent2) !important; color: var(--accent) !important; }
.group-break td { border-top: 2px solid rgba(234,88,12,.22) !important; }

/* ── Question cell ─────────────────────────────────── */
.q-cell { line-height: 1.65; }
.q-tamil   { font-size: .85rem; color: var(--text); margin-bottom: .25rem; }
.q-english { font-size: .83rem; color: var(--text2); }
.year-cell {
  font-family: var(--font-mono); font-size: .75rem; font-weight: 600;
  color: var(--accent); text-align: center; white-space: nowrap; width: 3.8rem;
}
.qnum-cell {
  font-family: var(--font-mono); font-size: .68rem; color: var(--text3);
  text-align: center; white-space: nowrap; width: 2.8rem;
}
.no-data { color: var(--text3); font-family: var(--font-mono); font-size: .78rem; padding: 2rem 0; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
"""


_JS = r"""
const QUESTIONS = __DATA__;

const PAPER_ORDER = ['Paper I', 'Paper II', 'Paper III'];
const PAPER_META  = {
  'Paper I':   'Modern History · Social Issues · Ethics',
  'Paper II':  'Indian Polity · Sci & Tech · Tamil Society',
  'Paper III': 'Geography · Environment · Economy'
};

/* ── Build index ─────────────────────────────────────────────────── */
const paperThemes      = {};  // paper -> [theme]
const themeSubthemes   = {};  // "paper\0theme" -> [subtheme]
const subthemeKeywords = {};  // "paper\0theme\0subtheme" -> [keyword]
const themeKeywords    = {};  // "paper\0theme" -> [keyword]  (no-subtheme themes)

for (const q of QUESTIONS) {
  const p  = q.paper;
  const th = (q.tags && q.tags.theme)    || '';
  const st = (q.tags && q.tags.subtheme) || '';
  const kw = (q.tags && q.tags.keyword)  || '';
  if (!p) continue;
  if (!th) continue;  // skip untagged

  if (!paperThemes[p]) paperThemes[p] = [];
  if (!paperThemes[p].includes(th)) paperThemes[p].push(th);

  const thKey = p + '\x00' + th;
  if (!themeSubthemes[thKey]) themeSubthemes[thKey] = [];
  if (st && !themeSubthemes[thKey].includes(st)) themeSubthemes[thKey].push(st);

  if (st && kw) {
    const stKey = thKey + '\x00' + st;
    if (!subthemeKeywords[stKey]) subthemeKeywords[stKey] = [];
    if (!subthemeKeywords[stKey].includes(kw)) subthemeKeywords[stKey].push(kw);
  }
  if (!st && kw) {
    if (!themeKeywords[thKey]) themeKeywords[thKey] = [];
    if (!themeKeywords[thKey].includes(kw)) themeKeywords[thKey].push(kw);
  }
}

// Unit index (for papers with no themes)
const paperUnits = {};    // paper -> [unit_number]
const unitNames  = {};    // "paper\0unit" -> full unit name from tags

for (const q of QUESTIONS) {
  const p = q.paper;
  const u = q.unit_number;
  if (!p || !u) continue;
  if (!paperUnits[p]) paperUnits[p] = [];
  if (!paperUnits[p].includes(u)) paperUnits[p].push(u);
  const key = p + '\x00' + u;
  if (!unitNames[key] && q.tags && q.tags.unit) unitNames[key] = q.tags.unit;
}

/* ── Helpers ─────────────────────────────────────────────────────── */
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function ja(v) { return esc(JSON.stringify(v)); }   // JSON-for-attribute

function applyGroupHover(tableEl) {
  tableEl.querySelectorAll('td[rowspan]').forEach(td => {
    const span = parseInt(td.getAttribute('rowspan'), 10);
    if (span <= 1) return;
    let tr = td.closest('tr');
    const rows = [];
    for (let i = 0; i < span && tr; i++) { rows.push(tr); tr = tr.nextElementSibling; }
    rows.forEach(row => {
      row.addEventListener('mouseenter', () => rows.forEach(r => r.classList.add('row-hover')));
      row.addEventListener('mouseleave', () => rows.forEach(r => r.classList.remove('row-hover')));
    });
  });
}

function showPage(id) {
  ['pg-landing', 'pg-paper', 'pg-detail'].forEach(p => {
    document.getElementById(p).style.display = p === id ? '' : 'none';
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ── Landing ─────────────────────────────────────────────────────── */
function showLanding() { showPage('pg-landing'); }

function renderLanding() {
  let html = '<div style="overflow-x:auto"><table class="nav-table"><thead><tr>'
           + '<th>Paper</th><th>Theme</th>'
           + '</tr></thead><tbody>';

  for (const paper of PAPER_ORDER) {
    const themes    = paperThemes[paper] || [];
    const hasThemes = themes.length > 0;
    const rows      = hasThemes ? themes : ['—'];
    const rowCount  = rows.length;

    for (let i = 0; i < rowCount; i++) {
      html += '<tr>';
      if (i === 0) {
        html += '<td class="paper-cell clickable" rowspan="' + rowCount + '"'
              + ' onclick="showPaper(' + ja(paper) + ')">'
              + '<div class="paper-name">' + esc(paper) + '</div>'
              + '<div class="paper-desc">' + esc(PAPER_META[paper] || '') + '</div>'
              + '</td>';
      }
      if (hasThemes) {
        html += '<td class="theme-cell clickable" onclick="showPaper(' + ja(paper) + ')">'
              + esc(rows[i]) + '</td>';
      } else {
        html += '<td class="sub-cell muted">Questions available — themes not yet tagged</td>';
      }
      html += '</tr>';
    }
  }

  html += '</tbody></table></div>';
  const el = document.getElementById('landing-content');
  el.innerHTML = html;
  el.querySelectorAll('.nav-table').forEach(applyGroupHover);
}

/* ── Paper page ──────────────────────────────────────────────────── */
function showPaper(paper) {
  document.getElementById('paper-nav-title').textContent =
    paper + ' — ' + (PAPER_META[paper] || '');
  renderPaperTable(paper);
  showPage('pg-paper');
}

function renderPaperTable(paper) {
  const themes    = paperThemes[paper] || [];
  const hasThemes = themes.length > 0;
  const el = document.getElementById('paper-content');

  if (!hasThemes) {
    /* Fallback: group by unit, show questions directly */
    renderUnitQuestions(paper, el);
    return;
  }

  let html = '<div style="overflow-x:auto"><table class="nav-table"><thead><tr>'
           + '<th>Theme</th><th>Subtheme / Topic</th>'
           + '</tr></thead><tbody>';

  let groupIdx = 0;
  for (const theme of themes) {
    const thKey = paper + '\x00' + theme;
    const subs  = themeSubthemes[thKey]  || [];
    const kws   = themeKeywords[thKey]   || [];
    const items = subs.length ? subs : kws;
    const isKw  = subs.length === 0;

    if (!items.length) {
      const rowCls = groupIdx > 0 ? ' class="group-break"' : '';
      html += '<tr' + rowCls + '>'
            + '<td class="theme-cell clickable" onclick="showDetail('
            + ja(paper) + ',' + ja(theme) + ',null)">' + esc(theme) + '</td>'
            + '<td class="sub-cell muted">—</td></tr>';
      groupIdx++; continue;
    }

    for (let i = 0; i < items.length; i++) {
      const item   = items[i];
      const rowCls = (i === 0 && groupIdx > 0) ? ' class="group-break"' : '';
      html += '<tr' + rowCls + '>';
      if (i === 0) {
        html += '<td class="theme-cell clickable" rowspan="' + items.length + '"'
              + ' onclick="showDetail(' + ja(paper) + ',' + ja(theme) + ',null)">'
              + esc(theme) + '</td>';
      }
      const detailArgs = ja(paper) + ',' + ja(theme) + ',' + (isKw ? 'null' : ja(item));
      html += '<td class="sub-cell clickable" onclick="showDetail(' + detailArgs + ')">'
            + esc(item) + '</td></tr>';
    }
    groupIdx++;
  }

  html += '</tbody></table></div>';
  el.innerHTML = html;
  el.querySelectorAll('.nav-table').forEach(applyGroupHover);
}

function renderUnitQuestions(paper, el) {
  /* Used when paper has no theme tags — show Unit → questions directly */
  const units = (paperUnits[paper] || []).slice().sort();
  let html = '';

  for (const u of units) {
    const fullName = unitNames[paper + '\x00' + u] || ('Unit ' + u);
    const qs = QUESTIONS.filter(q => q.paper === paper && q.unit_number === u)
                        .sort((a, b) => b.year - a.year || (a.question_number || 0) - (b.question_number || 0));
    if (!qs.length) continue;

    html += '<p class="section-label">' + esc(fullName) + ' (' + qs.length + ' questions)</p>';
    html += '<div style="overflow-x:auto;margin-bottom:2rem"><table class="nav-table">'
          + '<thead><tr><th>Q#</th><th>Question</th><th>Year</th></tr></thead><tbody>';
    for (const q of qs) {
      html += '<tr>'
            + '<td class="qnum-cell">Q' + esc(q.question_number) + '</td>'
            + '<td class="q-cell">';
      if (q.tamil)   html += '<div class="q-tamil">'   + esc(q.tamil)   + '</div>';
      if (q.english) html += '<div class="q-english">' + esc(q.english) + '</div>';
      html += '</td>'
            + '<td class="year-cell">' + q.year + '</td>'
            + '</tr>';
    }
    html += '</tbody></table></div>';
  }

  if (!html) html = '<p class="no-data">No questions found for this paper.</p>';
  el.innerHTML = html;
}

/* ── Detail page ─────────────────────────────────────────────────── */
function showDetail(paper, theme, subtheme) {
  const crumb = paper + ' › ' + theme + (subtheme ? ' › ' + subtheme : '');
  document.getElementById('detail-nav-title').textContent = crumb;
  document.getElementById('detail-back-btn').onclick = () => showPaper(paper);
  renderDetailPage(paper, theme, subtheme);
  showPage('pg-detail');
}

function renderDetailPage(paper, theme, subtheme) {
  const thKey = paper + '\x00' + theme;

  /* ── Top: subtheme × keywords ─────────────────── */
  let topHtml = '';

  if (subtheme) {
    const stKey = thKey + '\x00' + subtheme;
    const kws   = subthemeKeywords[stKey] || [];
    if (kws.length) {
      topHtml += '<p class="section-label">Topics under this subtheme</p>'
               + '<div style="overflow-x:auto"><table class="nav-table" style="margin-bottom:2.5rem">'
               + '<thead><tr><th>Subtheme</th><th>Keyword</th></tr></thead><tbody>';
      for (let i = 0; i < kws.length; i++) {
        topHtml += '<tr>';
        if (i === 0)
          topHtml += '<td class="theme-cell" rowspan="' + kws.length + '">' + esc(subtheme) + '</td>';
        topHtml += '<td class="sub-cell">' + esc(kws[i]) + '</td></tr>';
      }
      topHtml += '</tbody></table></div>';
    }
  } else {
    const kws = themeKeywords[thKey] || [];
    if (kws.length) {
      topHtml += '<p class="section-label">Topics under this theme</p>'
               + '<div style="overflow-x:auto"><table class="nav-table" style="margin-bottom:2.5rem">'
               + '<thead><tr><th>Theme</th><th>Keyword</th></tr></thead><tbody>';
      for (let i = 0; i < kws.length; i++) {
        topHtml += '<tr>';
        if (i === 0)
          topHtml += '<td class="theme-cell" rowspan="' + kws.length + '">' + esc(theme) + '</td>';
        topHtml += '<td class="sub-cell">' + esc(kws[i]) + '</td></tr>';
      }
      topHtml += '</tbody></table></div>';
    }
  }

  document.getElementById('detail-top-content').innerHTML = topHtml;
  if (topHtml)
    document.querySelectorAll('#detail-top-content .nav-table').forEach(applyGroupHover);

  /* ── Questions: keyword × question × year ────── */
  const qs = QUESTIONS.filter(q => {
    if (q.paper !== paper) return false;
    if (!q.tags || q.tags.theme !== theme) return false;
    if (subtheme) return q.tags.subtheme === subtheme;
    return !q.tags.subtheme;
  });

  const kwOrder  = [];
  const kwGroups = {};
  for (const q of qs) {
    const kw = (q.tags && q.tags.keyword) || '—';
    if (!kwGroups[kw]) { kwGroups[kw] = []; kwOrder.push(kw); }
    kwGroups[kw].push(q);
  }
  for (const arr of Object.values(kwGroups))
    arr.sort((a, b) => b.year - a.year || (a.question_number || 0) - (b.question_number || 0));

  let qHtml = '';
  if (!kwOrder.length) {
    qHtml = '<p class="no-data">No questions found for this selection.</p>';
  } else {
    qHtml += '<p class="section-label">Questions (' + qs.length + ')</p>'
           + '<div style="overflow-x:auto"><table class="nav-table">'
           + '<thead><tr><th>Keyword</th><th>Question</th><th>Year</th></tr></thead><tbody>';

    let kwGroupIdx = 0;
    for (const kw of kwOrder) {
      const arr = kwGroups[kw];
      for (let i = 0; i < arr.length; i++) {
        const q      = arr[i];
        const rowCls = (i === 0 && kwGroupIdx > 0) ? ' class="group-break"' : '';
        qHtml += '<tr' + rowCls + '>';
        if (i === 0)
          qHtml += '<td class="kw-cell" rowspan="' + arr.length + '">' + esc(kw) + '</td>';
        qHtml += '<td class="q-cell">';
        if (q.tamil)   qHtml += '<div class="q-tamil">'   + esc(q.tamil)   + '</div>';
        if (q.english) qHtml += '<div class="q-english">' + esc(q.english) + '</div>';
        qHtml += '</td><td class="year-cell">' + q.year + '</td></tr>';
      }
      kwGroupIdx++;
    }
    qHtml += '</tbody></table></div>';
  }

  document.getElementById('detail-q-content').innerHTML = qHtml;
  document.querySelectorAll('#detail-q-content .nav-table').forEach(applyGroupHover);
}

/* ── Boot ────────────────────────────────────────────────────────── */
renderLanding();
"""


def generate_html(questions: list[dict]) -> str:
    data_json = json.dumps(questions, ensure_ascii=False)
    js = _JS.replace("__DATA__", data_json)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TNPSC Group I Mains &middot; Question Navigator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
{_CSS}
</style>
</head>
<body>

<div class="top-bar">
  <span>Free to use &amp; share &nbsp;&middot;&nbsp; Built for TNPSC aspirants</span>
  <span>Collaborate or build further &rarr; <a href="mailto:upsc.ai.stack@gmail.com">upsc.ai.stack@gmail.com</a></span>
</div>

<div class="page-shell">
  <header>
    <hr class="masthead-rule">
    <h1>TNPSC Group I Mains &middot; <em>Question Navigator</em></h1>
    <div class="header-sub">Papers I&ndash;III &nbsp;&middot;&nbsp; 2013&ndash;2025 &nbsp;&middot;&nbsp; Paper &rarr; Theme &rarr; Questions</div>
    <hr class="masthead-rule bottom">
  </header>

  <div id="pg-landing">
    <div id="landing-content"></div>
  </div>

  <div id="pg-paper" style="display:none">
    <div class="page-nav">
      <button class="back-btn" onclick="showLanding()">&#8592; All Papers</button>
      <span class="page-nav-title" id="paper-nav-title"></span>
    </div>
    <div id="paper-content"></div>
  </div>

  <div id="pg-detail" style="display:none">
    <div class="page-nav">
      <button class="back-btn" id="detail-back-btn">&#8592; Back</button>
      <span class="page-nav-title" id="detail-nav-title"></span>
    </div>
    <div id="detail-top-content"></div>
    <div id="detail-q-content"></div>
  </div>
</div>

<footer class="site-footer">
  <span>Free to use &amp; share &nbsp;&middot;&nbsp; Built for TNPSC aspirants</span>
  <span>Collaborate or build further &rarr; <a href="mailto:upsc.ai.stack@gmail.com">upsc.ai.stack@gmail.com</a></span>
</footer>

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
    print(f"Navigator written to {OUTPUT_PATH} ({len(questions)} questions)")


if __name__ == "__main__":
    main()
