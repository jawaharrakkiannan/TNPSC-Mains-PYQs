# scripts/generate_html.py
import json
import os

INPUT_PATH  = "data/questions_tagged.json"
OUTPUT_PATH = "output/viewer.html"


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
button, select, input { font-family: inherit; font-size: inherit; }
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
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 9999; opacity: .038;
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
.page-shell { max-width: 1200px; margin: 0 auto; padding: 0 1.5rem 4rem; }
header { text-align: center; padding: 0 1rem; margin-bottom: 1.5rem; animation: fadeUp .7s ease both; }
.masthead-rule {
  border: none; border-top: 3px solid var(--text); border-bottom: 1px solid var(--text);
  height: 5px; margin: 2rem 0 1.25rem; background: transparent;
}
.masthead-rule.bottom { margin: 1.25rem 0 0; }
header h1 {
  font-family: var(--font-body); font-size: clamp(2rem,5vw,3.4rem); font-weight: 700;
  color: var(--text); line-height: 1.1; letter-spacing: .005em; margin-bottom: .7rem;
}
header h1 em { font-style: italic; font-weight: 400; color: var(--accent); }
.header-sub {
  font-family: var(--font-mono); font-size: .68rem; color: var(--text2);
  letter-spacing: .14em; text-transform: uppercase; margin-bottom: 1.25rem;
}
.site-footer {
  max-width: 1200px; margin: 3rem auto 0; padding: 1rem 0;
  border-top: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
  flex-wrap: wrap; gap: .5rem;
  font-family: var(--font-mono); font-size: .6rem; letter-spacing: .08em; color: var(--text3);
}
.site-footer a { color: var(--accent); text-decoration: none; }
.site-footer a:hover { text-decoration: underline; }

/* ── Filter panel ─────────────────────────────────── */
.filters-panel { display: flex; flex-direction: column; gap: .5rem; margin-bottom: 1.5rem; animation: fadeUp .4s .15s ease both; }
.filter-card {
  background: var(--surface); border: 1px solid var(--border);
  border-top: 3px solid var(--accent); border-radius: var(--radius);
  padding: .85rem 1rem;
}
.filter-title {
  font-family: var(--font-mono); font-size: .6rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: .1em; color: var(--text3); margin-bottom: .5rem;
}
.filter-title-row {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: .5rem;
}
.filter-title-row .filter-title { margin-bottom: 0; }
.toggle-all-btn, .table-toggle-btn {
  font-size: .6rem; font-family: var(--font-mono);
  border: 1px solid var(--border2); border-radius: var(--radius);
  background: none; cursor: pointer; padding: .15rem .5rem; color: var(--text3);
  transition: border-color .1s, color .1s;
}
.toggle-all-btn:hover, .table-toggle-btn:hover { border-color: var(--accent); color: var(--accent); }
.inline-toggle-btn {
  font-size: .65rem; font-family: var(--font-mono);
  border: 1px solid var(--accent); border-radius: var(--radius);
  background: none; cursor: pointer; padding: .15rem .5rem; color: var(--accent);
  transition: background .1s; white-space: nowrap;
}
.inline-toggle-btn:hover { background: var(--accent2); }
.multi-toggle {
  font-size: .6rem; font-family: var(--font-mono); color: var(--text3);
  cursor: pointer; display: flex; align-items: center; gap: .3rem; user-select: none;
}
.multi-toggle input { cursor: pointer; accent-color: var(--accent); }

/* ── Chips ──────────────────────────────────────── */
.checkbox-grid { display: flex; flex-wrap: wrap; gap: .3rem; }
.check-chip {
  display: inline-flex; align-items: center; gap: .25rem; font-size: .72rem;
  cursor: pointer; padding: .15rem .4rem;
  border: 1px solid var(--border2); border-radius: var(--radius);
  transition: border-color .1s, background .1s; user-select: none;
}
.check-chip input { display: none; }
.check-chip.checked { border-color: var(--accent); background: var(--accent2); color: var(--accent); font-weight: 500; }
.kw-chip {
  font-size: .65rem; padding: .15rem .45rem;
  border: 1px solid var(--border2); border-radius: var(--radius);
  cursor: pointer; transition: border-color .1s, background .1s;
  font-family: var(--font-mono);
}
.kw-chip.active { border-color: var(--accent); background: var(--accent2); color: var(--accent); }
.keyword-chips { display: flex; flex-wrap: wrap; gap: .3rem; }

/* ── Subject buttons (theme) ──────────────────── */
.subject-btn {
  display: block; width: 100%; text-align: left;
  padding: .3rem .6rem; margin-bottom: .25rem;
  border: 1px solid var(--border2); border-radius: var(--radius);
  background: none; cursor: pointer; font-size: .8rem;
  transition: border-color .1s, background .1s; font-family: inherit;
}
.subject-btn:last-child { margin-bottom: 0; }
.subject-btn:hover { border-color: var(--accent); }
.subject-btn.active { border-color: var(--accent); background: var(--accent2); color: var(--accent); font-weight: 500; }

/* ── Filter input ─────────────────────────────── */
.filter-input {
  width: 100%; padding: .3rem .5rem; font-size: .8rem;
  border: 1px solid var(--border2); border-radius: var(--radius);
  background: var(--surface); color: var(--text); font-family: inherit;
}

/* ── Data tables (frequency) ──────────────────── */
.data-table { width: 100%; border-collapse: collapse; font-size: .68rem; font-family: var(--font-mono); margin-top: .5rem; }
.data-table th { background: var(--bg2); padding: .25rem .5rem; border: 1px solid var(--border); text-align: left; white-space: nowrap; font-weight: 500; }
.data-table td { padding: .25rem .5rem; border: 1px solid var(--border); }
.data-table tr:hover td { background: var(--accent3); }
.num-cell { text-align: center; color: var(--accent); font-weight: 500; }
.cell-link { cursor: pointer; }
.cell-link:hover { background: var(--accent2) !important; text-decoration: underline; }

/* ── Reset ────────────────────────────────────── */
.reset-btn {
  width: 100%; padding: .35rem; font-size: .72rem;
  font-family: var(--font-mono); background: none;
  border: 1px solid var(--border2); border-radius: var(--radius);
  cursor: pointer; color: var(--text3); transition: border-color .1s, color .1s;
}
.reset-btn:hover { border-color: var(--accent); color: var(--accent); }

/* ── Placeholder ──────────────────────────────── */
.placeholder-text { font-size: .65rem; color: var(--text3); font-family: var(--font-mono); }

/* ── Stats bar ────────────────────────────────── */
main { animation: fadeUp .4s .35s ease both; }
.stats-bar { font-family: var(--font-mono); font-size: .65rem; color: var(--text3); margin-bottom: 1rem; display: flex; gap: 1rem; }
.stats-bar strong { color: var(--accent); font-size: 1rem; }

/* ── Results table ────────────────────────────── */
.results-controls { display: flex; align-items: center; gap: .75rem; margin-bottom: .9rem; flex-wrap: wrap; }
.tnpsc-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
.tnpsc-table th {
  background: var(--bg2); padding: .35rem .8rem;
  border-bottom: 2px solid var(--border2); border-top: none; border-left: none; border-right: none;
  font-family: var(--font-mono); font-size: .58rem; text-transform: uppercase;
  letter-spacing: .08em; color: var(--text3); text-align: left; white-space: nowrap;
}
.tnpsc-table td { padding: .5rem .75rem; border: 1px solid var(--border); vertical-align: top; }
.tnpsc-table tr:hover td { background: var(--accent2) !important; }
.row-group-hover td { background: var(--accent2) !important; }
.row-group-hover .theme-cell { border-left-color: var(--accent) !important; }
.theme-cell {
  font-weight: 500; font-size: .72rem;
  border: 2px solid var(--border2); border-left: 3px solid transparent !important;
  color: var(--text2); width: 16%; min-width: 10rem; transition: border-left-color .12s;
}
.year-cell {
  font-family: var(--font-mono); font-size: .72rem; color: var(--accent);
  text-align: center; white-space: nowrap; width: 3.5rem;
}
.qnum-cell {
  font-family: var(--font-mono); font-size: .68rem; color: var(--text3);
  text-align: center; white-space: nowrap; width: 2.5rem;
}
.q-cell { line-height: 1.6; }
.tamil-text { font-size: .82rem; color: var(--text); margin-bottom: .2rem; }
.english-text { font-size: .82rem; color: var(--text2); }
.sec-cell { font-family: var(--font-mono); font-size: .65rem; color: var(--text3); text-align: center; white-space: nowrap; width: 2.5rem; }
.marks-cell { font-family: var(--font-mono); font-size: .65rem; color: var(--text3); text-align: center; white-space: nowrap; width: 2.8rem; }
.row-alt td { background: rgba(0,0,0,.022); }
.group-break td { border-top: 3px solid rgba(234,88,12,.22) !important; }
.paper-header {
  font-weight: 700; font-size: .92rem; color: #fff;
  background: var(--accent); padding: .45rem .75rem;
  margin-top: 1.4rem; margin-bottom: 12px; letter-spacing: .01em;
}
.paper-header:first-child { margin-top: 0; }

/* ── Q-card (card view) ───────────────────────── */
.q-card {
  background: var(--surface); border: 1px solid var(--border);
  border-left: 3px solid var(--border); border-radius: var(--radius);
  padding: .85rem 1.1rem; margin-bottom: .6rem;
  transition: border-left-color .15s, box-shadow .15s;
}
.q-card:hover { border-left-color: var(--accent); box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.q-header { display: flex; align-items: flex-start; flex-wrap: wrap; gap: .4rem; margin-bottom: .5rem; }
.q-badge { font-family: var(--font-mono); font-size: .65rem; font-weight: 500; background: var(--accent); color: #fff; padding: .1rem .45rem; border-radius: var(--radius); white-space: nowrap; }
.q-meta { font-family: var(--font-mono); font-size: .62rem; color: var(--text3); align-self: center; }
.q-tags { display: flex; flex-wrap: wrap; gap: .3rem; margin-left: auto; }
.tag-theme { font-size: .6rem; font-family: var(--font-mono); background: var(--accent3); border: 1px solid rgba(234,88,12,.25); color: var(--accent); padding: .1rem .4rem; border-radius: var(--radius); }
.tag-kw { font-size: .58rem; font-family: var(--font-mono); color: var(--text3); background: var(--bg2); border: 1px solid var(--border); padding: .1rem .35rem; border-radius: var(--radius); }
.q-tamil { font-size: .87rem; color: var(--text); line-height: 1.7; margin-bottom: .3rem; }
.q-english { font-size: .87rem; color: var(--text2); line-height: 1.6; }
.no-results { text-align: center; color: var(--text3); font-family: var(--font-mono); font-size: .8rem; padding: 3rem 0; }

@keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
@media (max-width: 600px) {
  header h1 { font-size: 1.6rem; }
  .top-bar { flex-direction: column; align-items: flex-start; }
}
"""


_JS = r"""
const QUESTIONS = __DATA__;

const ALL_YEARS = [...new Set(QUESTIONS.map(q => q.year))].sort((a,b) => a - b);

const state = {
  years:    new Set(),
  paper:    null,
  unit:     null,
  section:  null,
  marks:    null,
  themes:   new Set(),
  keywords: new Set(),
  search:   ''
};

let viewMode = 'table';   // 'table' | 'card'
let multiYearMode = false;
let table1Visible = true;
let table2Visible = true;

const PAPER_NAMES = {
  'Paper I':   'Paper I — Modern History · Social Issues · Ethics',
  'Paper II':  'Paper II — Indian Polity · Sci & Tech · Tamil Society',
  'Paper III': 'Paper III — Geography · Environment · Economy'
};

const UNIT_NAMES = {};
(function() {
  for (const q of QUESTIONS) {
    if (!q.unit_number || !q.tags || !q.tags.unit) continue;
    const key = q.paper + ':' + q.unit_number;
    if (!UNIT_NAMES[key]) UNIT_NAMES[key] = q.tags.unit;
  }
})();

function getUnitName(u) {
  if (state.paper) return UNIT_NAMES[state.paper + ':' + u] || ('Unit ' + u);
  return 'Unit ' + u;
}

function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ── Filter ─────────────────────────────────────────────────────── */
function filterItems() {
  const sr = state.search.toLowerCase();
  return QUESTIONS.filter(q => {
    if (state.years.size > 0 && !state.years.has(q.year)) return false;
    if (state.paper  && q.paper !== state.paper)           return false;
    if (state.unit   && q.unit_number !== state.unit)      return false;
    if (state.section && q.section !== state.section)      return false;
    if (state.marks !== null && q.marks !== state.marks)   return false;
    if (state.themes.size > 0 && !state.themes.has(q.tags && q.tags.theme)) return false;
    if (state.keywords.size > 0 && !state.keywords.has(q.tags && q.tags.keyword)) return false;
    if (sr) {
      const en = (q.english || '').toLowerCase();
      const ta = (q.tamil   || '').toLowerCase();
      if (!en.includes(sr) && !ta.includes(sr)) return false;
    }
    return true;
  });
}

function applyFilters() {
  const items = filterItems();
  renderTable1();
  renderTable2();
  renderResults(items);
  document.getElementById('count').textContent      = items.length;
  document.getElementById('years-count').textContent = state.years.size || ALL_YEARS.length;
}

/* ── Year chips ─────────────────────────────────────────────────── */
function initYears() {
  const el = document.getElementById('year-filters');
  let html = '';
  for (const y of ALL_YEARS) {
    html += '<label class="check-chip' + (state.years.has(y) ? ' checked' : '') + '" data-y="' + y + '"><input type="checkbox">' + y + '</label>';
  }
  const allSel = ALL_YEARS.every(y => state.years.has(y));
  document.getElementById('year-toggle-btn').textContent = allSel ? 'Unselect All' : 'Select All';
  el.innerHTML = html;
  el.querySelectorAll('.check-chip').forEach(label => {
    label.addEventListener('click', e => {
      e.preventDefault();
      const y = parseInt(label.dataset.y, 10);
      if (!multiYearMode) {
        const was = state.years.has(y);
        state.years.clear();
        if (!was) state.years.add(y);
      } else {
        state.years.has(y) ? state.years.delete(y) : state.years.add(y);
      }
      initYears();
      applyFilters();
    });
  });
}

function toggleMultiYear() {
  multiYearMode = document.getElementById('multi-year-cb').checked;
  if (!multiYearMode && state.years.size > 1) {
    const last = [...state.years].at(-1);
    state.years.clear();
    if (last !== undefined) state.years.add(last);
    initYears();
    applyFilters();
  }
}

function toggleAllYears() {
  document.getElementById('multi-year-cb').checked = true;
  multiYearMode = true;
  if (ALL_YEARS.every(y => state.years.has(y))) { state.years.clear(); }
  else { ALL_YEARS.forEach(y => state.years.add(y)); }
  initYears();
  applyFilters();
}

/* ── Paper buttons ──────────────────────────────────────────────── */
function initPapers() {
  const el = document.getElementById('paper-filters');
  let html = '';
  for (const p of ['Paper I', 'Paper II', 'Paper III']) {
    html += '<button class="subject-btn' + (state.paper === p ? ' active' : '') + '" data-p="' + esc(p) + '">' + esc(PAPER_NAMES[p]) + '</button>';
  }
  el.innerHTML = html;
  el.querySelectorAll('.subject-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = btn.dataset.p;
      state.paper = state.paper === p ? null : p;
      state.unit = null;
      state.themes.clear();
      state.keywords.clear();
      initPapers();
      initUnits();
      renderThemeButtons();
      updateKeywordChips();
      applyFilters();
    });
  });
}

/* ── Unit buttons ───────────────────────────────────────────────── */
function initUnits() {
  const el = document.getElementById('unit-filters');
  let html = '';
  for (const u of ['I', 'II', 'III']) {
    html += '<button class="subject-btn' + (state.unit === u ? ' active' : '') + '" data-u="' + u + '">' + esc(getUnitName(u)) + '</button>';
  }
  el.innerHTML = html;
  el.querySelectorAll('.subject-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const u = btn.dataset.u;
      state.unit = state.unit === u ? null : u;
      state.themes.clear();
      state.keywords.clear();
      initUnits();
      renderThemeButtons();
      updateKeywordChips();
      applyFilters();
    });
  });
}

/* ── Section chips ──────────────────────────────────────────────── */
function initSections() {
  const el = document.getElementById('section-filters');
  let html = '';
  for (const s of ['A', 'B', 'C', 'D']) {
    html += '<label class="check-chip' + (state.section === s ? ' checked' : '') + '" data-s="' + s + '"><input type="checkbox">Sec ' + s + '</label>';
  }
  el.innerHTML = html;
  el.querySelectorAll('.check-chip').forEach(label => {
    label.addEventListener('click', e => {
      e.preventDefault();
      const s = label.dataset.s;
      state.section = state.section === s ? null : s;
      initSections();
      applyFilters();
    });
  });
}

/* ── Marks chips ────────────────────────────────────────────────── */
function initMarks() {
  const el = document.getElementById('marks-filters');
  const vals = [...new Set(QUESTIONS.map(q => q.marks).filter(m => m != null))].sort((a,b) => a - b);
  let html = '';
  for (const m of vals) {
    html += '<label class="check-chip' + (state.marks === m ? ' checked' : '') + '" data-m="' + m + '"><input type="checkbox">' + m + 'M</label>';
  }
  el.innerHTML = html;
  el.querySelectorAll('.check-chip').forEach(label => {
    label.addEventListener('click', e => {
      e.preventDefault();
      const m = parseInt(label.dataset.m, 10);
      state.marks = state.marks === m ? null : m;
      initMarks();
      applyFilters();
    });
  });
}

/* ── Theme buttons ──────────────────────────────────────────────── */
function renderThemeButtons() {
  const container = document.getElementById('theme-buttons');
  const base = QUESTIONS.filter(q =>
    (!state.paper || q.paper === state.paper) &&
    (!state.unit  || q.unit_number === state.unit)
  );
  const themes = [...new Set(base.map(q => q.tags && q.tags.theme).filter(Boolean))].sort();
  if (!themes.length) {
    container.innerHTML = '<span class="placeholder-text">Select a paper / unit to see themes</span>';
    return;
  }
  let html = '';
  for (const t of themes) {
    html += '<button class="subject-btn' + (state.themes.has(t) ? ' active' : '') + '" data-t="' + esc(t) + '">' + esc(t) + '</button>';
  }
  container.innerHTML = html;
  container.querySelectorAll('.subject-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const t = btn.dataset.t;
      state.themes.has(t) ? state.themes.delete(t) : state.themes.add(t);
      state.keywords.clear();
      renderThemeButtons();
      updateKeywordChips();
      applyFilters();
    });
  });
}

/* ── Keyword chips ──────────────────────────────────────────────── */
function updateKeywordChips() {
  const container = document.getElementById('keyword-chips');
  const toggleBtn = document.getElementById('kw-toggle-btn');
  const base = QUESTIONS.filter(q =>
    (!state.paper  || q.paper === state.paper) &&
    (!state.unit   || q.unit_number === state.unit) &&
    (state.themes.size === 0 || state.themes.has(q.tags && q.tags.theme))
  );
  const kws = [...new Set(base.map(q => q.tags && q.tags.keyword).filter(Boolean))].sort();
  if (!kws.length) {
    container.innerHTML = '<span class="placeholder-text">Select a theme to see keywords</span>';
    if (toggleBtn) toggleBtn.style.display = 'none';
    return;
  }
  const allSel = kws.every(k => state.keywords.has(k));
  if (toggleBtn) { toggleBtn.style.display = ''; toggleBtn.textContent = allSel ? 'Deselect All' : 'Select All'; }
  let html = '';
  for (const k of kws) {
    html += '<span class="kw-chip' + (state.keywords.has(k) ? ' active' : '') + '" data-kw="' + esc(k) + '">' + esc(k) + '</span>';
  }
  container.innerHTML = html;
  container.querySelectorAll('.kw-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const kw = chip.dataset.kw;
      state.keywords.has(kw) ? state.keywords.delete(kw) : state.keywords.add(kw);
      chip.classList.toggle('active', state.keywords.has(kw));
      if (toggleBtn) toggleBtn.textContent = kws.every(k => state.keywords.has(k)) ? 'Deselect All' : 'Select All';
      applyFilters();
    });
  });
}

function toggleAllKeywords() {
  const container = document.getElementById('keyword-chips');
  const kws = [...container.querySelectorAll('.kw-chip')].map(c => c.dataset.kw);
  if (kws.every(k => state.keywords.has(k))) { state.keywords.clear(); }
  else { kws.forEach(k => state.keywords.add(k)); }
  updateKeywordChips();
  applyFilters();
}

/* ── Frequency: Theme × Year ────────────────────────────────────── */
function renderTable1() {
  const card = document.getElementById('table1-card');
  card.style.display = '';
  document.getElementById('table1-toggle-btn').textContent = table1Visible ? 'Hide ▲' : 'Show ▼';
  const body = document.getElementById('table1-body');
  if (!table1Visible) { body.innerHTML = ''; return; }

  const years = state.years.size > 0 ? [...state.years].sort((a,b) => a-b) : ALL_YEARS;
  const base = QUESTIONS.filter(q =>
    (!state.paper || q.paper === state.paper) &&
    (!state.unit  || q.unit_number === state.unit)
  );
  const themes = [...new Set(base.map(q => q.tags && q.tags.theme).filter(Boolean))].sort();
  const counts = {};
  for (const t of themes) counts[t] = {};
  for (const q of base) {
    const t = q.tags && q.tags.theme;
    if (!t) continue;
    counts[t][q.year] = (counts[t][q.year] || 0) + 1;
  }

  let html = '<div style="overflow-x:auto"><table class="data-table"><thead><tr><th>Theme</th>';
  for (const y of years) html += '<th>' + y + '</th>';
  html += '<th>Total</th></tr></thead><tbody>';
  for (const t of themes) {
    const rowTotal = years.reduce((a, y) => a + (counts[t][y] || 0), 0);
    const tCls = rowTotal > 0 ? ' class="cell-link"' : '';
    const tClick = rowTotal > 0 ? ' onclick="applyFromTable1Theme(' + JSON.stringify(t) + ')"' : '';
    html += '<tr><td' + tCls + tClick + '>' + esc(t) + '</td>';
    for (const y of years) {
      const c = counts[t][y] || 0;
      const cls = c > 0 ? ' class="num-cell cell-link"' : ' class="num-cell"';
      const click = c > 0 ? ' onclick="applyFromTable1(' + JSON.stringify(t) + ',' + y + ')"' : '';
      html += '<td' + cls + click + '>' + (c || '') + '</td>';
    }
    html += '<td class="num-cell">' + (rowTotal || '') + '</td></tr>';
  }
  html += '</tbody></table></div>';
  body.innerHTML = html;
}

function applyFromTable1(theme, year) {
  state.years.clear(); state.years.add(year);
  state.themes.clear(); state.themes.add(theme);
  initYears(); renderThemeButtons(); updateKeywordChips();
  applyFilters();
  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

function applyFromTable1Theme(theme) {
  state.themes.clear(); state.themes.add(theme);
  renderThemeButtons(); updateKeywordChips();
  applyFilters();
  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

function toggleTable1() {
  table1Visible = !table1Visible;
  document.getElementById('table1-toggle-btn').textContent = table1Visible ? 'Hide ▲' : 'Show ▼';
  renderTable1();
}

/* ── Frequency: Keyword × Year ──────────────────────────────────── */
function renderTable2() {
  const card = document.getElementById('table2-card');
  if (state.themes.size === 0) { card.style.display = 'none'; return; }
  card.style.display = '';
  document.getElementById('table2-toggle-btn').textContent = table2Visible ? 'Hide ▲' : 'Show ▼';
  const body = document.getElementById('table2-body');
  if (!table2Visible) { body.innerHTML = ''; return; }

  const years = state.years.size > 0 ? [...state.years].sort((a,b) => a-b) : ALL_YEARS;
  const base = QUESTIONS.filter(q =>
    (!state.paper || q.paper === state.paper) &&
    (!state.unit  || q.unit_number === state.unit) &&
    (state.themes.size === 0 || state.themes.has(q.tags && q.tags.theme))
  );
  const kws = [...new Set(base.map(q => q.tags && q.tags.keyword).filter(Boolean))].sort();
  const counts = {};
  for (const k of kws) counts[k] = {};
  for (const q of base) {
    const k = q.tags && q.tags.keyword;
    if (!k) continue;
    counts[k][q.year] = (counts[k][q.year] || 0) + 1;
  }

  let html = '<div style="overflow-x:auto"><table class="data-table"><thead><tr><th>Keyword</th>';
  for (const y of years) html += '<th>' + y + '</th>';
  html += '<th>Total</th></tr></thead><tbody>';
  for (const k of kws) {
    const rowTotal = years.reduce((a, y) => a + (counts[k][y] || 0), 0);
    const kCls = rowTotal > 0 ? ' class="cell-link"' : '';
    const kClick = rowTotal > 0 ? ' onclick="applyFromTable2Kw(' + JSON.stringify(k) + ')"' : '';
    html += '<tr><td' + kCls + kClick + '>' + esc(k) + '</td>';
    for (const y of years) {
      const c = counts[k][y] || 0;
      const cls = c > 0 ? ' class="num-cell cell-link"' : ' class="num-cell"';
      const click = c > 0 ? ' onclick="applyFromTable2(' + JSON.stringify(k) + ',' + y + ')"' : '';
      html += '<td' + cls + click + '>' + (c || '') + '</td>';
    }
    html += '<td class="num-cell">' + (rowTotal || '') + '</td></tr>';
  }
  html += '</tbody></table></div>';
  body.innerHTML = html;
}

function applyFromTable2(kw, year) {
  state.years.clear(); state.years.add(year);
  state.keywords.clear(); state.keywords.add(kw);
  initYears(); updateKeywordChips();
  applyFilters();
  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

function applyFromTable2Kw(kw) {
  state.keywords.clear(); state.keywords.add(kw);
  updateKeywordChips();
  applyFilters();
  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

function toggleTable2() {
  table2Visible = !table2Visible;
  document.getElementById('table2-toggle-btn').textContent = table2Visible ? 'Hide ▲' : 'Show ▼';
  renderTable2();
}

/* ── View toggle ────────────────────────────────────────────────── */
function toggleView() {
  viewMode = viewMode === 'table' ? 'card' : 'table';
  document.getElementById('view-toggle-btn').textContent = viewMode === 'table' ? 'Card View' : 'Table View';
  const items = filterItems();
  renderResults(items);
}

/* ── Render results ─────────────────────────────────────────────── */
function renderResults(items) {
  const el = document.getElementById('results');
  if (!items.length) {
    el.innerHTML = '<div class="no-results">No questions match the current filters.</div>';
    return;
  }
  if (viewMode === 'card') { renderCards(items, el); return; }
  renderTable(items, el);
}

function renderCards(items, el) {
  let html = '';
  for (const q of items) {
    const meta = [q.year, q.paper, q.unit_number ? 'Unit ' + q.unit_number : null, q.section ? 'Sec ' + q.section : null, q.marks ? q.marks + 'M' : null, q.word_limit ? q.word_limit + 'w' : null].filter(Boolean).join(' · ');
    const tags = q.tags || {};
    html += '<div class="q-card">';
    html += '<div class="q-header">';
    html += '<span class="q-badge">Q' + esc(q.question_number) + '</span>';
    html += '<span class="q-meta">' + esc(meta) + '</span>';
    html += '<div class="q-tags">';
    if (tags.theme)    html += '<span class="tag-theme">' + esc(tags.theme) + '</span>';
    if (tags.keyword)  html += '<span class="tag-kw">'    + esc(tags.keyword) + '</span>';
    html += '</div></div>';
    if (q.tamil)   html += '<div class="q-tamil">'   + esc(q.tamil)   + '</div>';
    if (q.english) html += '<div class="q-english">' + esc(q.english) + '</div>';
    html += '</div>';
  }
  el.innerHTML = html;
}

function renderTable(items, el) {
  // Group: paper → theme → questions
  const paperOrder = ['Paper I', 'Paper II', 'Paper III'];

  const byPaper = new Map();
  for (const p of paperOrder) byPaper.set(p, new Map());
  for (const q of items) {
    const theme = (q.tags && q.tags.theme) || '—';
    if (!byPaper.has(q.paper)) byPaper.set(q.paper, new Map());
    const themeMap = byPaper.get(q.paper);
    if (!themeMap.has(theme)) themeMap.set(theme, []);
    themeMap.get(theme).push(q);
  }

  // sort each theme's questions: year desc, q# asc
  for (const [, tm] of byPaper)
    for (const [, arr] of tm)
      arr.sort((a,b) => b.year - a.year || a.question_number - b.question_number);

  let html = '<div class="results-controls"><button class="inline-toggle-btn" id="view-toggle-btn" onclick="toggleView()">Card View</button></div>';

  for (const paper of paperOrder) {
    const themeMap = byPaper.get(paper);
    if (!themeMap || !themeMap.size) continue;
    if ([...themeMap.values()].every(a => !a.length)) continue;

    html += '<div class="paper-header">' + esc(paper) + '</div>';
    html += '<div style="overflow-x:auto;margin-bottom:1.4rem"><table class="tnpsc-table"><thead><tr>';
    html += '<th>Theme</th><th>Year</th><th>Q#</th><th>Question</th><th>Sec</th><th>Marks</th>';
    html += '</tr></thead><tbody>';

    let themeGroupIdx = 0;
    for (const [theme, arr] of themeMap) {
      if (!arr.length) continue;
      for (let i = 0; i < arr.length; i++) {
        const q = arr[i];
        const cls = [(i === 0 && themeGroupIdx > 0) ? 'group-break' : '', i % 2 === 1 ? 'row-alt' : ''].filter(Boolean).join(' ');
        html += '<tr' + (cls ? ' class="' + cls + '"' : '') + '>';
        if (i === 0) html += '<td class="theme-cell" rowspan="' + arr.length + '">' + esc(theme) + '</td>';
        html += '<td class="year-cell">' + q.year + '</td>';
        html += '<td class="qnum-cell">Q' + esc(q.question_number) + '</td>';
        html += '<td class="q-cell">';
        if (q.tamil)   html += '<div class="tamil-text">'   + esc(q.tamil)   + '</div>';
        if (q.english) html += '<div class="english-text">' + esc(q.english) + '</div>';
        html += '</td>';
        html += '<td class="sec-cell">'   + esc(q.section || '—') + '</td>';
        html += '<td class="marks-cell">' + (q.marks ? esc(String(q.marks)) + 'M' : '—') + '</td>';
        html += '</tr>';
      }
      themeGroupIdx++;
    }
    html += '</tbody></table></div>';
  }

  el.innerHTML = html;
  el.querySelectorAll('.tnpsc-table').forEach(applyGroupHover);
}

function applyGroupHover(tableEl) {
  tableEl.querySelectorAll('td[rowspan]').forEach(td => {
    const span = parseInt(td.getAttribute('rowspan'), 10);
    if (span <= 1) return;
    let tr = td.closest('tr');
    const rows = [];
    for (let i = 0; i < span && tr; i++) { rows.push(tr); tr = tr.nextElementSibling; }
    rows.forEach(row => {
      row.addEventListener('mouseenter', () => rows.forEach(r => r.classList.add('row-group-hover')));
      row.addEventListener('mouseleave', () => rows.forEach(r => r.classList.remove('row-group-hover')));
    });
  });
}

/* ── Search ─────────────────────────────────────────────────────── */
document.getElementById('search-input').addEventListener('input', function() {
  state.search = this.value.trim();
  applyFilters();
});

/* ── Reset ──────────────────────────────────────────────────────── */
function resetFilters() {
  state.years.clear(); state.paper = null; state.unit = null;
  state.section = null; state.marks = null;
  state.themes.clear(); state.keywords.clear(); state.search = '';
  document.getElementById('search-input').value = '';
  document.getElementById('multi-year-cb').checked = false;
  multiYearMode = false;
  initYears(); initPapers(); initUnits();
  renderThemeButtons(); updateKeywordChips();
  renderTable1(); renderTable2();
  applyFilters();
}

/* ── Boot ───────────────────────────────────────────────────────── */
initYears();
initPapers();
initUnits();
renderThemeButtons();
updateKeywordChips();
renderTable1();
renderTable2();
applyFilters();
"""


def generate_html(questions: list[dict]) -> str:
    data_json = json.dumps(questions, ensure_ascii=False)
    js = _JS.replace("__DATA__", data_json)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TNPSC Group I Mains &middot; PYQ Question Bank</title>
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
    <h1>TNPSC Group I Mains &middot; <em>PYQ Question Bank</em></h1>
    <div class="header-sub">Papers I&ndash;III &nbsp;&middot;&nbsp; 2013&ndash;2025 &nbsp;&middot;&nbsp; Tamil &amp; English &nbsp;&middot;&nbsp; Filter &amp; Study</div>
    <hr class="masthead-rule bottom">
  </header>

  <div class="filters-panel">

    <!-- Year -->
    <div class="filter-card">
      <div class="filter-title-row">
        <span class="filter-title">Year</span>
        <div style="display:flex;align-items:center;gap:.4rem">
          <label class="multi-toggle"><input type="checkbox" id="multi-year-cb" onchange="toggleMultiYear()"> Multi-select</label>
          <button class="inline-toggle-btn" id="year-toggle-btn" onclick="toggleAllYears()">Select All</button>
        </div>
      </div>
      <div class="checkbox-grid" id="year-filters"></div>
    </div>

    <!-- Paper -->
    <div class="filter-card">
      <div class="filter-title">Paper</div>
      <div id="paper-filters"></div>
    </div>

    <!-- Unit -->
    <div class="filter-card">
      <div class="filter-title">Unit</div>
      <div id="unit-filters"></div>
    </div>

    <!-- Theme × Year table -->
    <div class="filter-card" id="table1-card">
      <div class="filter-title-row">
        <span class="filter-title">Theme &times; Year</span>
        <button class="table-toggle-btn" id="table1-toggle-btn" onclick="toggleTable1()">Show &#9660;</button>
      </div>
      <div id="table1-body"></div>
    </div>

    <!-- Keyword × Year table -->
    <div class="filter-card" id="table2-card" style="display:none">
      <div class="filter-title-row">
        <span class="filter-title">Keyword &times; Year</span>
        <button class="table-toggle-btn" id="table2-toggle-btn" onclick="toggleTable2()">Show &#9660;</button>
      </div>
      <div id="table2-body"></div>
    </div>

    <!-- Theme -->
    <div class="filter-card">
      <div class="filter-title-row">
        <span class="filter-title">Theme</span>
        <button class="toggle-all-btn" onclick="state.themes.clear();state.keywords.clear();renderThemeButtons();updateKeywordChips();applyFilters()">Clear</button>
      </div>
      <div id="theme-buttons"></div>
    </div>

    <!-- Keywords -->
    <div class="filter-card">
      <div class="filter-title-row">
        <span class="filter-title">Keyword</span>
        <button class="inline-toggle-btn" id="kw-toggle-btn" onclick="toggleAllKeywords()" style="display:none">Select All</button>
      </div>
      <div class="keyword-chips" id="keyword-chips"></div>
    </div>

    <!-- Search -->
    <div class="filter-card">
      <div class="filter-title">Search</div>
      <input type="text" class="filter-input" id="search-input" placeholder="Search English or Tamil text&hellip;">
    </div>

    <button class="reset-btn" onclick="resetFilters()">Reset all filters</button>
  </div>

  <main>
    <div class="stats-bar">
      <span><strong id="count">0</strong> questions</span>
      <span><strong id="years-count">0</strong> years</span>
    </div>
    <div id="results"></div>
  </main>
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
    print(f"Viewer written to {OUTPUT_PATH} ({len(questions)} questions)")


if __name__ == "__main__":
    main()
