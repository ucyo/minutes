"""The single-page web UI served by minutes logs --web.

Kept self-contained (no build step, no external assets) on purpose.
"""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>minutes</title>
<style>
:root {
  --bg: #1e1e1e;
  --panel: #252525;
  --panel2: #2a2a2a;
  --border: #3a3a3a;
  --fg: #cccccc;
  --dim: #888888;
  --blue: #569cd6;
  --yellow: #d7ba7d;
  --magenta: #c586c0;
  --green: #6a9955;
  --red: #f14c4c;
  --cyan: #4ec9b0;
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
body {
  margin: 0;
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--fg);
}
header {
  position: sticky; top: 0; z-index: 10;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  padding: 10px 16px;
}
.bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
h1 { font-size: 16px; margin: 0; color: var(--cyan); letter-spacing: .02em; }
.filters { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.chk { color: var(--dim); display: inline-flex; align-items: center; gap: 4px; cursor: pointer; }
input, select, button {
  background: var(--panel2);
  color: var(--fg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 8px;
  font: inherit;
}
input:focus, select:focus { outline: none; border-color: var(--cyan); }
button { cursor: pointer; }
button:hover { border-color: var(--cyan); }
main { max-width: 1000px; margin: 0 auto; padding: 16px; }
.add { background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px; margin-bottom: 8px; }
.add form { display: flex; flex-direction: column; gap: 8px; }
.add-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
#add-text { flex: 1 1 320px; min-width: 220px; }
.bucket {
  color: var(--dim); font-size: 12px; text-transform: uppercase;
  letter-spacing: .08em; margin: 14px 0 2px; font-weight: 600;
}
.empty { color: var(--dim); padding: 8px 0; }
.entry {
  display: grid;
  grid-template-columns: 9.2em 9em 5em minmax(10em, 1fr) auto;
  column-gap: 10px;
  align-items: baseline;
  padding: 2px 8px; border-radius: 4px;
}
.entry.alt { background: var(--panel); }
.entry:hover { background: var(--panel2); }
.ts { color: var(--dim); white-space: nowrap; font-variant-numeric: tabular-nums; }
.project { color: var(--cyan); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.badge { font-size: 12px; padding: 0 6px; border-radius: 3px; white-space: nowrap; }
.badge.decision { color: var(--blue); }
.badge.action { color: var(--yellow); }
.badge.waiting { color: var(--magenta); }
.badge.note { color: var(--dim); }
.entry.done .badge.action { color: var(--green); }
.entry.cancelled .badge.action { color: var(--dim); }
.body { flex: 1 1 auto; min-width: 0; }
.text { overflow-wrap: anywhere; }
.entry.done .text { color: var(--green); }
.entry.cancelled .text { color: var(--dim); }
.cb { margin-left: 6px; }
.cb.done { color: var(--green); }
.cb.cancelled, .cb.open { color: var(--dim); }
.due, .person, .meta { margin-left: 10px; font-size: 13px; white-space: nowrap; }
.due { color: var(--dim); }
.due.soon { color: var(--yellow); }
.due.overdue { color: var(--red); }
.person { color: var(--magenta); }
.meta { color: var(--dim); }
.actions { display: inline-flex; gap: 4px; }
.actions button {
  background: transparent; border-color: transparent; padding: 2px 6px;
  color: var(--dim); border-radius: 4px; line-height: 1.2;
}
.actions button:hover { color: var(--fg); background: var(--panel2); border-color: var(--border); }
.actions button.danger:hover { color: var(--red); border-color: var(--red); }
.modal { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal.hidden { display: none; }
.modal-card { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; width: min(560px, 90vw); }
.modal-title { color: var(--dim); font-size: 13px; margin-bottom: 10px; }
.modal-card input { width: 100%; }
.modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
</style>
</head>
<body>
<header>
  <div class="bar">
    <h1>minutes</h1>
    <div class="filters">
      <select id="project" title="Project"><option value="">All projects</option></select>
      <input id="since" placeholder="since: mon / 14 / 2026-05-20" title="Since">
      <label class="chk"><input type="checkbox" id="open"> open</label>
      <label class="chk"><input type="checkbox" id="all"> all</label>
      <label class="chk"><input type="checkbox" id="newest" checked> newest first</label>
    </div>
  </div>
</header>

<main>
  <section class="add">
    <form id="add-form" autocomplete="off">
      <div class="add-row">
        <input id="add-project" list="projects" placeholder="project" required>
        <input id="add-meeting" placeholder="meeting (optional)">
        <select id="add-type" title="Type">
          <option value="note">note</option>
          <option value="decision">decision</option>
          <option value="action">action</option>
          <option value="waiting">waiting</option>
        </select>
        <input id="add-due" type="date" hidden>
        <input id="add-person" placeholder="person" hidden>
      </div>
      <div class="add-row">
        <input id="add-text" placeholder="* decision   ! action @fri   > waiting @Person   note" required>
        <button type="submit">Add</button>
      </div>
    </form>
  </section>

  <section id="entries"></section>
</main>

<datalist id="projects"></datalist>

<div id="modal" class="modal hidden">
  <div class="modal-card">
    <div class="modal-title" id="modal-title">Edit</div>
    <input id="modal-input">
    <div class="modal-actions">
      <button id="modal-cancel">Cancel</button>
      <button id="modal-save">Save</button>
    </div>
  </div>
</div>

<script>
const $ = (id) => document.getElementById(id);
const projectSel = $('project');
const sinceEl = $('since');
const openEl = $('open');
const allEl = $('all');
const newestEl = $('newest');
const addForm = $('add-form');
const addProject = $('add-project');
const addMeeting = $('add-meeting');
const addType = $('add-type');
const addDue = $('add-due');
const addPerson = $('add-person');
const addText = $('add-text');
const entriesEl = $('entries');
const projectsDatalist = $('projects');
const modal = $('modal');
const modalTitle = $('modal-title');
const modalInput = $('modal-input');
const modalSave = $('modal-save');
const modalCancel = $('modal-cancel');

const BUCKETS = ['Older', 'This year', 'Last month', 'This month', 'Last week', 'This week', 'Yesterday', 'Today'];

let cache = { entries: [] };
let syncing = false;
let modalOnSave = null;
let pendingProject = new URLSearchParams(location.search).get('project');

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.status + ' ' + res.statusText);
  return data;
}

function parseLine(text) {
  const t = (text || '').trim();
  let type = 'note', core = t, due = '', person = '';
  if (t.startsWith('*')) { type = 'decision'; core = t.slice(1).trim(); }
  else if (t.startsWith('!')) {
    type = 'action'; core = t.slice(1).trim();
    const m = core.match(/@(\S+)/);
    if (m) { due = m[1]; core = core.replace(m[0], '').trim(); }
  } else if (t.startsWith('>')) {
    type = 'waiting'; core = t.slice(1).trim();
    const m = core.match(/@(\w+)/);
    if (m) { person = m[1]; core = core.replace(m[0], '').trim(); }
  }
  return { type, core, due, person };
}

function composeLine(p) {
  const core = (p.core || '').trim();
  if (p.type === 'decision') return '* ' + core;
  if (p.type === 'action') return '! ' + core + (p.due ? ' @' + p.due : '');
  if (p.type === 'waiting') return '> ' + core + (p.person ? ' @' + p.person : '');
  return core;
}

const WEEKDAYS = { mon: 1, tue: 2, wed: 3, thu: 4, fri: 5, sat: 6, sun: 0 };

function isoDate(d) {
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
}

function resolveDue(token) {
  const t = (token || '').trim().toLowerCase();
  const today = new Date(); today.setHours(0, 0, 0, 0);
  if (t in WEEKDAYS) {
    const delta = (WEEKDAYS[t] - today.getDay() + 7) % 7 || 7;
    const d = new Date(today); d.setDate(d.getDate() + delta);
    return isoDate(d);
  }
  if (/^\d+$/.test(t)) {
    const d = new Date(today); d.setDate(d.getDate() + parseInt(t, 10));
    return isoDate(d);
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) return t;
  return '';
}

function showHelpers(type) {
  addDue.hidden = type !== 'action';
  addPerson.hidden = type !== 'waiting';
}

function syncFromText() {
  if (syncing) return;
  syncing = true;
  const p = parseLine(addText.value);
  addType.value = p.type;
  addDue.value = resolveDue(p.due);
  addPerson.value = p.person;
  showHelpers(p.type);
  syncing = false;
}

function syncToText() {
  if (syncing) return;
  syncing = true;
  const p = parseLine(addText.value);
  p.type = addType.value;
  p.due = addDue.value;
  p.person = addPerson.value.trim();
  addText.value = composeLine(p);
  showHelpers(p.type);
  syncing = false;
}

addText.addEventListener('input', syncFromText);
addType.addEventListener('change', syncToText);
addDue.addEventListener('input', syncToText);
addDue.addEventListener('change', syncToText);
addPerson.addEventListener('input', syncToText);

function populateProjects(projects) {
  const current = projectSel.value;
  projectSel.innerHTML = '<option value="">All projects</option>' +
    projects.map(p => `<option value="${esc(p)}">${esc(p)}</option>`).join('');
  if (projects.includes(current)) {
    projectSel.value = current;
  } else if (pendingProject && projects.includes(pendingProject)) {
    projectSel.value = pendingProject;
    pendingProject = null;
  } else {
    projectSel.value = '';
  }
  projectsDatalist.innerHTML = projects.map(p => `<option value="${esc(p)}"></option>`).join('');
}

function dueClass(due) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const d = new Date(due + 'T00:00:00');
  if (isNaN(d.getTime())) return '';
  const diff = Math.round((d - today) / 86400000);
  if (diff < 0) return 'overdue';
  if (diff <= 2) return 'soon';
  return '';
}

function formatTs(ts, bucket) {
  const s = ts || '';
  const time = s.slice(11, 16);
  const datePart = s.slice(0, 10);
  if (bucket === 'Today' || bucket === 'Yesterday') return time;
  if (bucket === 'This week' || bucket === 'Last week') {
    const d = new Date(datePart + 'T00:00:00');
    const wd = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d.getDay()];
    return wd + ' ' + time;
  }
  return datePart;
}

function entryToRaw(e) {
  if (e.type === 'decision') return '* ' + e.text;
  if (e.type === 'action') return '! ' + e.text + (e.due ? ' @' + e.due : '');
  if (e.type === 'waiting') return '> ' + e.text + (e.person ? ' @' + e.person : '');
  return e.text;
}

function btn(action, label, title, id, danger) {
  return `<button data-action="${action}" data-id="${esc(id)}" title="${title}"${danger ? ' class="danger"' : ''}>${label}</button>`;
}

function entryHtml(e, alt) {
  const cls = ((e.type === 'action' && e.status) ? ' ' + e.status : '') + (alt ? ' alt' : '');
  const ts = formatTs(e.ts, e.bucket);
  let cb = '';
  if (e.type === 'action') {
    cb = e.status === 'done' ? ' <span class="cb done">[x]</span>'
       : e.status === 'cancelled' ? ' <span class="cb cancelled">[-]</span>'
       : ' <span class="cb open">[ ]</span>';
  }
  let extra = '';
  if (e.type === 'action' && e.due && e.status !== 'done' && e.status !== 'cancelled') {
    extra += `<span class="due ${dueClass(e.due)}">due ${esc(e.due)}</span>`;
  }
  if (e.type === 'waiting' && e.person) {
    extra += `<span class="person">→ ${esc(e.person)}</span>`;
  }
  let meta = '';
  if (allEl.checked) {
    const parts = [];
    if (e.meeting) parts.push(esc(e.meeting));
    if (e.tags && e.tags.length) parts.push(e.tags.map(t => '#' + esc(t)).join(' '));
    if (e.type === 'action' && e.status === 'done' && e.updated_ts) parts.push(esc(e.updated_ts.replace('T', ' ')));
    if (parts.length) meta = `<span class="meta">${parts.join(' · ')}</span>`;
  }
  let actions = '<span class="actions">';
  if (e.type === 'action') {
    if (e.status !== 'done') actions += btn('done', '✓', 'mark done', e.id);
    if (e.status !== 'cancelled') actions += btn('cancel', '✕', 'cancel', e.id);
    if (e.status === 'done' || e.status === 'cancelled') actions += btn('reopen', '↺', 'reopen', e.id);
  }
  actions += btn('edit', '✎', 'edit', e.id);
  actions += btn('followup', '⤴', 'follow-up', e.id);
  actions += btn('delete', '🗑', 'delete', e.id, true);
  actions += '</span>';
  return `<div class="entry${cls}">
      <span class="ts">${esc(ts)}</span>
      <span class="project">${esc(e.project)}</span>
      <span class="badge ${esc(e.type)}">${esc(e.type)}</span>
      <span class="body"><span class="text">${esc(e.text)}${cb}</span>${extra}${meta}</span>
      ${actions}
    </div>`;
}

function render() {
  const groups = {};
  BUCKETS.forEach(b => groups[b] = []);
  cache.entries.forEach(e => (groups[e.bucket] || groups.Older).push(e));
  const order = newestEl.checked ? [...BUCKETS].reverse() : BUCKETS;
  let html = '';
  order.forEach(b => {
    const items = groups[b] || [];
    if (!items.length) return;
    if (newestEl.checked) items.reverse();
    html += `<h3 class="bucket">${b}</h3>`;
    let prevProject = null;
    let groupIdx = 0;
    items.forEach(e => {
      if (prevProject !== null && e.project !== prevProject) groupIdx += 1;
      prevProject = e.project;
      html += entryHtml(e, groupIdx % 2 === 1);
    });
  });
  entriesEl.innerHTML = html || '<p class="empty">No entries.</p>';
}

async function load() {
  const q = new URLSearchParams();
  if (projectSel.value) q.set('project', projectSel.value);
  if (sinceEl.value.trim()) q.set('since', sinceEl.value.trim());
  if (openEl.checked) q.set('open', '1');
  try {
    const data = await api('GET', '/api/entries?' + q.toString());
    cache.entries = data.entries || [];
    populateProjects(data.projects || []);
    render();
  } catch (err) { alert(err.message); }
}

projectSel.addEventListener('change', load);
sinceEl.addEventListener('change', load);
openEl.addEventListener('change', load);
allEl.addEventListener('change', render);
newestEl.addEventListener('change', render);

addForm.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const project = addProject.value.trim();
  const text = addText.value.trim();
  if (!project || !text) return;
  try {
    await api('POST', '/api/entries', { raw: text, project: project, meeting: addMeeting.value.trim() || null });
    addText.value = '';
    syncFromText();
    addText.focus();
    await load();
  } catch (err) { alert(err.message); }
});

function openModal(title, value, onSave) {
  modalTitle.textContent = title;
  modalInput.value = value;
  modalOnSave = onSave;
  modal.classList.remove('hidden');
  modalInput.focus();
  modalInput.select();
}
function closeModal() { modal.classList.add('hidden'); modalOnSave = null; }

modalSave.addEventListener('click', async () => {
  const fn = modalOnSave, v = modalInput.value;
  closeModal();
  if (!fn) return;
  try { await fn(v); await load(); } catch (err) { alert(err.message); }
});
modalCancel.addEventListener('click', closeModal);
modal.addEventListener('click', ev => { if (ev.target === modal) closeModal(); });
document.addEventListener('keydown', ev => {
  if (modal.classList.contains('hidden')) return;
  if (ev.key === 'Escape') closeModal();
  if (ev.key === 'Enter') modalSave.click();
});

entriesEl.addEventListener('click', ev => {
  const b = ev.target.closest('button[data-action]');
  if (!b) return;
  const id = b.dataset.id, action = b.dataset.action;
  const entry = cache.entries.find(e => e.id === id);
  runAction(action, id, entry);
});

async function runAction(action, id, entry) {
  try {
    if (action === 'edit') { openModal('Edit  Enter:save  Esc:cancel', entryToRaw(entry), v => api('PATCH', `/api/entries/${id}`, { raw: v })); return; }
    if (action === 'followup') { openModal('Follow-up  Enter:save  Esc:cancel', '! ', v => api('POST', `/api/entries/${id}/followup`, { raw: v })); return; }
    if (action === 'done') await api('POST', `/api/entries/${id}/status`, { status: 'done' });
    else if (action === 'cancel') await api('POST', `/api/entries/${id}/status`, { status: 'cancelled' });
    else if (action === 'reopen') await api('POST', `/api/entries/${id}/status`, { status: 'open' });
    else if (action === 'delete') {
      if (!confirm('Delete this entry?')) return;
      await api('DELETE', `/api/entries/${id}`);
    }
    await load();
  } catch (err) { alert(err.message); }
}

(function init() {
  const params = new URLSearchParams(location.search);
  if (params.get('since')) sinceEl.value = params.get('since');
  openEl.checked = params.get('open') === '1';
  allEl.checked = params.get('all') === '1';
  load();
})();
</script>
</body>
</html>
"""
