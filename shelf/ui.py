"""Self-contained HTML pages for the SHELF web app."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SHELF - Dashboard</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0c120e;
    color: #e9efe9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    min-height: 100vh;
    padding: 24px;
  }
  header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #1e2c23;
  }
  h1 {
    font-size: 28px;
    letter-spacing: 4px;
    color: #7fd4a8;
  }
  .tagline {
    color: #94b3a2;
    font-size: 13px;
  }
  nav a {
    color: #94b3a2;
    text-decoration: none;
    margin-left: 16px;
    font-size: 14px;
  }
  nav a:hover { color: #7fd4a8; }
  .upload-card {
    background: #121a15;
    border: 1px dashed #2c4536;
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 24px;
  }
  .upload-card h2 {
    font-size: 16px;
    margin-bottom: 12px;
    color: #e9efe9;
  }
  .upload-row {
    display: flex;
    gap: 12px;
    align-items: center;
  }
  input[type="file"] {
    color: #94b3a2;
    font-size: 13px;
  }
  input[type="file"]::file-selector-button {
    background: #1e3427;
    color: #95e0b8;
    border: 1px solid #2c4536;
    padding: 8px 16px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
    margin-right: 12px;
  }
  input[type="file"]::file-selector-button:hover { background: #27452f; }
  button {
    background: #7fd4a8;
    color: #0c120e;
    border: none;
    padding: 10px 20px;
    border-radius: 999px;
    font-weight: 600;
    cursor: pointer;
    font-size: 14px;
  }
  button:hover { background: #95e0b8; }
  button:disabled { background: #2b4034; color: #6f9080; cursor: not-allowed; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
  }
  .card {
    background: #121a15;
    border: 1px solid #1e2c23;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .card .photos {
    display: flex;
    gap: 4px;
    padding: 8px;
    background: #0c120e;
    overflow-x: auto;
  }
  .card .photos img {
    height: 80px;
    width: 80px;
    object-fit: cover;
    border-radius: 4px;
    flex-shrink: 0;
  }
  .card .body {
    padding: 12px;
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  .card .title {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 4px;
  }
  .card .price {
    color: #7fd4a8;
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 8px;
  }
  .card .desc {
    color: #94b3a2;
    font-size: 13px;
    line-height: 1.4;
    margin-bottom: 12px;
    flex: 1;
  }
  .card .status {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
    width: fit-content;
  }
  .status-processing { background: #3a2f1a; color: #f0c674; }
  .status-draft { background: #1f2a3a; color: #7fb0d4; }
  .status-live { background: #1a3a2a; color: #7fd4a8; }
  .status-sold { background: #3a1a2a; color: #d47fa8; }
  .status-paid { background: #2a2a3a; color: #a87fd4; }
  .card .actions {
    display: flex;
    gap: 8px;
    margin-top: auto;
  }
  .card .actions button {
    flex: 1;
    padding: 8px;
    font-size: 13px;
  }
  .feed {
    background: #090e0b;
    border: 1px solid #1e2c23;
    border-radius: 4px;
    padding: 8px;
    margin-top: 8px;
    max-height: 140px;
    overflow-y: auto;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 11px;
    color: #94b3a2;
  }
  .feed .ev {
    margin-bottom: 4px;
    padding-bottom: 4px;
    border-bottom: 1px solid #121a15;
  }
  .feed .ev .ag { color: #7fd4a8; }
  .feed .ev .ts { color: #567a67; margin-right: 6px; }
  .empty {
    text-align: center;
    padding: 48px;
    color: #567a67;
  }
</style>
</head>
<body>
<header>
  <div>
    <h1>SHELF</h1>
    <div class="tagline">seller dashboard</div>
  </div>
  <nav>
    <a href="/store">storefront</a>
    <a href="/ledger">ledger</a>
  </nav>
</header>

<div class="upload-card">
  <h2>New item</h2>
  <form id="upform" class="upload-row">
    <input type="file" id="photos" name="photos" accept="image/*" multiple required>
    <button type="submit" id="upbtn">Upload &amp; process</button>
  </form>
  <div id="upreview" style="display:flex;gap:6px;margin-top:10px;"></div>
</div>

<div id="grid" class="grid"></div>
<div id="empty" class="empty">No items yet. Upload photos to get started.</div>

<script>
const grid = document.getElementById('grid');
const empty = document.getElementById('empty');
const form = document.getElementById('upform');
const upbtn = document.getElementById('upbtn');
const upreview = document.getElementById('upreview');

// show selected photos as thumbnails before upload (added 2026-08-20:
// a bare file input reading "3 files" looked broken on camera and to users)
document.getElementById('photos').addEventListener('change', (e) => {
  upreview.innerHTML = '';
  for (const f of Array.from(e.target.files).slice(0, 6)) {
    const img = document.createElement('img');
    img.src = URL.createObjectURL(f);
    img.style.cssText = 'width:72px;height:72px;object-fit:cover;border-radius:8px;border:1px solid #27452f;';
    upreview.appendChild(img);
  }
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const files = document.getElementById('photos').files;
  if (!files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append('photos', f);
  upbtn.disabled = true;
  upbtn.textContent = 'Uploading...';
  try {
    const r = await fetch('/api/items', { method: 'POST', body: fd });
    const j = await r.json();
    if (j.item_id) {
      document.getElementById('photos').value = '';
      upreview.innerHTML = '';
      refresh();
    }
  } catch (err) {
    alert('Upload failed: ' + err.message);
  } finally {
    upbtn.disabled = false;
    upbtn.textContent = 'Upload & process';
  }
});

function fmtPrice(p) {
  if (!p) return '$0.00';
  return '$' + Number(p).toFixed(2);
}

function thumbUrl(item, idx) {
  if (!item.photo_paths || !item.photo_paths[idx]) return '';
  const p = item.photo_paths[idx];
  const parts = p.split('/');
  const fn = parts[parts.length - 1];
  return '/uploads/' + item.id + '/' + fn;
}

function escapeHtml(s) {
  if (!s) return '';
  return s.replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function renderCard(item) {
  const photos = (item.photo_paths || []).slice(0, 3).map((p, i) => {
    const parts = p.split('/');
    const fn = parts[parts.length - 1];
    return '<img src="/uploads/' + item.id + '/' + fn + '" alt="">';
  }).join('');
  const status = item.status || 'processing';
  let actions = '';
  let feed = '';
  if (status === 'processing') {
    feed = '<div class="feed" id="feed-' + item.id + '"><div class="ev"><span class="ag">crew</span> waiting...</div></div>';
  } else if (status === 'draft') {
    actions = '<button onclick="approve(\\'' + item.id + '\\')">Approve</button>';
  } else if (status === 'live') {
    actions = '<button onclick="markSold(\\'' + item.id + '\\')">Mark sold</button>';
  } else if (status === 'sold') {
    actions = '<button onclick="markPaid(\\'' + item.id + '\\')">Mark paid</button>';
  }
  return '<div class="card" id="card-' + item.id + '">' +
    '<div class="photos">' + photos + '</div>' +
    '<div class="body">' +
      '<span class="status status-' + status + '">' + status + '</span>' +
      '<div class="title">' + escapeHtml(item.title || '(untitled)') + '</div>' +
      '<div class="price">' + fmtPrice(item.price) + '</div>' +
      '<div class="desc">' + escapeHtml((item.description || '').slice(0, 140)) + '</div>' +
      '<div class="actions">' + actions + '</div>' +
      feed +
    '</div>' +
  '</div>';
}

async function refresh() {
  try {
    const r = await fetch('/api/items');
    const items = await r.json();
    if (!items.length) {
      grid.innerHTML = '';
      empty.style.display = 'block';
      return;
    }
    empty.style.display = 'none';
    grid.innerHTML = items.map(renderCard).join('');
    for (const it of items) {
      if (it.status === 'processing') subscribeFeed(it.id);
    }
  } catch (e) {
    console.error(e);
  }
}

const feeds = {};

function subscribeFeed(itemId) {
  if (feeds[itemId]) return;
  feeds[itemId] = true;
  const el = document.getElementById('feed-' + itemId);
  if (!el) return;
  const es = new EventSource('/api/items/' + itemId + '/events');
  es.onmessage = (ev) => {
    try {
      const d = JSON.parse(ev.data);
      const line = document.createElement('div');
      line.className = 'ev';
      const ts = new Date(d.ts * 1000).toLocaleTimeString();
      line.innerHTML = '<span class="ts">' + ts + '</span><span class="ag">' + escapeHtml(d.agent) + '</span> ' + escapeHtml(d.text);
      el.appendChild(line);
      el.scrollTop = el.scrollHeight;
    } catch (e) {}
  };
  es.onerror = () => { es.close(); delete feeds[itemId]; };
}

async function approve(id) {
  await fetch('/api/items/' + id + '/approve', { method: 'POST' });
  refresh();
}

async function markSold(id) {
  const p = prompt('Sold price?');
  if (!p) return;
  await fetch('/api/items/' + id + '/sold', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ price: parseFloat(p) })
  });
  refresh();
}

async function markPaid(id) {
  await fetch('/api/items/' + id + '/paid', { method: 'POST' });
  refresh();
}

refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>"""


STORE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SHELF - Storefront</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0c120e;
    color: #e9efe9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    min-height: 100vh;
    padding: 32px 24px;
  }
  header {
    text-align: center;
    margin-bottom: 48px;
    padding-bottom: 24px;
    border-bottom: 1px solid #1e2c23;
  }
  h1 {
    font-size: 42px;
    letter-spacing: 8px;
    color: #7fd4a8;
    margin-bottom: 8px;
  }
  .tagline {
    color: #94b3a2;
    font-size: 14px;
    font-style: italic;
  }
  nav {
    text-align: center;
    margin-bottom: 32px;
  }
  nav a {
    color: #94b3a2;
    text-decoration: none;
    margin: 0 12px;
    font-size: 13px;
  }
  nav a:hover { color: #7fd4a8; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
    max-width: 1200px;
    margin: 0 auto;
  }
  .item {
    background: #121a15;
    border: 1px solid #1e2c23;
    border-radius: 10px;
    overflow: hidden;
    transition: transform 0.2s;
  }
  .item:hover { transform: translateY(-2px); }
  .item .photo {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    background: #090e0b;
    display: block;
  }
  .item .body {
    padding: 20px;
  }
  .item .title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
  }
  .item .price {
    color: #7fd4a8;
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 12px;
  }
  .item .desc {
    color: #94b3a2;
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 12px;
  }
  .item .toggle {
    color: #7fd4a8;
    font-size: 13px;
    cursor: pointer;
    background: none;
    border: none;
    padding: 0;
  }
  .item .toggle:hover { text-decoration: underline; }
  .item .full-desc {
    display: none;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #1e2c23;
    color: #b9cfc0;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
  }
  .item .full-desc.show { display: block; }
  .empty {
    text-align: center;
    padding: 80px 24px;
    color: #567a67;
  }
</style>
</head>
<body>
<header>
  <h1>SHELF</h1>
  <div class="tagline">honest listings, agent-made, human-approved</div>
</header>
<nav>
  <a href="/">dashboard</a>
  <a href="/ledger">ledger</a>
</nav>
<div id="grid" class="grid"></div>
<div id="empty" class="empty">No live items yet. Check back soon.</div>

<script>
function escapeHtml(s) {
  if (!s) return '';
  return s.replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function fmtPrice(p) {
  return '$' + Number(p || 0).toFixed(2);
}

function thumbUrl(item) {
  /* FIELD-NAME FIX 2026-08-19: the API serves `thumb`/`photos`, never
     `photo_paths` - the old check made every card photo-less (blank boxes). */
  if (item.thumb) return item.thumb;
  if (item.photos && item.photos.length) return item.photos[0];
  if (!item.photo_paths || !item.photo_paths.length) return '';
  const p = item.photo_paths[0];
  const parts = p.split('/');
  const fn = parts[parts.length - 1];
  return '/uploads/' + item.id + '/' + fn;
}

function renderItem(item) {
  const photo = thumbUrl(item);
  const shortDesc = (item.description || '').slice(0, 160);
  const hasMore = (item.description || '').length > 160;
  return '<div class="item">' +
    (photo ? '<img class="photo" src="' + photo + '" alt="">' : '<div class="photo"></div>') +
    '<div class="body">' +
      '<div class="title">' + escapeHtml(item.title || '(untitled)') + '</div>' +
      '<div class="price">' + fmtPrice(item.price) + '</div>' +
      '<div class="desc">' + escapeHtml(shortDesc) + (hasMore ? '...' : '') + '</div>' +
      (hasMore ? '<button class="toggle" onclick="toggleDesc(this)">read more</button>' : '') +
      '<div class="full-desc">' + escapeHtml(item.description || '') + '</div>' +
    '</div>' +
  '</div>';
}

function toggleDesc(btn) {
  const desc = btn.parentElement.querySelector('.full-desc');
  if (desc.classList.contains('show')) {
    desc.classList.remove('show');
    btn.textContent = 'read more';
  } else {
    desc.classList.add('show');
    btn.textContent = 'read less';
  }
}

async function refresh() {
  try {
    const r = await fetch('/api/store-items');
    const items = await r.json();
    const grid = document.getElementById('grid');
    const empty = document.getElementById('empty');
    if (!items.length) {
      grid.innerHTML = '';
      empty.style.display = 'block';
      return;
    }
    empty.style.display = 'none';
    grid.innerHTML = items.map(renderItem).join('');
  } catch (e) {
    console.error(e);
  }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


LEDGER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SHELF - Ledger</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0c120e;
    color: #e9efe9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    min-height: 100vh;
    padding: 32px 24px;
  }
  header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 32px;
    padding-bottom: 16px;
    border-bottom: 1px solid #1e2c23;
  }
  h1 {
    font-size: 28px;
    letter-spacing: 4px;
    color: #7fd4a8;
  }
  nav a {
    color: #94b3a2;
    text-decoration: none;
    margin-left: 16px;
    font-size: 14px;
  }
  nav a:hover { color: #7fd4a8; }
  .totals {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }
  .stat {
    background: #121a15;
    border: 1px solid #1e2c23;
    border-radius: 8px;
    padding: 20px;
  }
  .stat .label {
    color: #94b3a2;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
  }
  .stat .value {
    color: #7fd4a8;
    font-size: 28px;
    font-weight: 700;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    background: #121a15;
    border: 1px solid #1e2c23;
    border-radius: 8px;
    overflow: hidden;
  }
  th, td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid #1e2c23;
    font-size: 14px;
  }
  th {
    background: #090e0b;
    color: #94b3a2;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 1px;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #16221a; }
  .kind {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .kind-listed { background: #1a3a2a; color: #7fd4a8; }
  .kind-sold { background: #3a1a2a; color: #d47fa8; }
  .kind-paid { background: #2a2a3a; color: #a87fd4; }
  .kind-note { background: #1f2a3a; color: #7fb0d4; }
  .amount { color: #7fd4a8; font-weight: 600; }
  .empty {
    text-align: center;
    padding: 48px;
    color: #567a67;
  }
</style>
</head>
<body>
<header>
  <h1>SHELF</h1>
  <nav>
    <a href="/">dashboard</a>
    <a href="/store">storefront</a>
  </nav>
</header>

<div class="totals" id="totals"></div>
<table id="ledger">
  <thead>
    <tr>
      <th>When</th>
      <th>Kind</th>
      <th>Item</th>
      <th>Amount</th>
      <th>Memo</th>
    </tr>
  </thead>
  <tbody id="rows"></tbody>
</table>
<div id="empty" class="empty">No ledger entries yet.</div>

<script>
function escapeHtml(s) {
  if (!s) return '';
  return s.replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function fmtPrice(p) {
  return '$' + Number(p || 0).toFixed(2);
}

function fmtTime(ts) {
  return new Date(ts * 1000).toLocaleString();
}

function renderTotals(t) {
  return '<div class="stat"><div class="label">Live</div><div class="value">' + (t.live_count || 0) + '</div></div>' +
    '<div class="stat"><div class="label">Sold</div><div class="value">' + (t.sold_count || 0) + '</div></div>' +
    '<div class="stat"><div class="label">Gross sold</div><div class="value">' + fmtPrice(t.gross_sold) + '</div></div>' +
    '<div class="stat"><div class="label">Paid</div><div class="value">' + fmtPrice(t.paid_total) + '</div></div>';
}

function renderRow(e) {
  return '<tr>' +
    '<td>' + fmtTime(e.created) + '</td>' +
    '<td><span class="kind kind-' + escapeHtml(e.kind) + '">' + escapeHtml(e.kind) + '</span></td>' +
    '<td><code>' + escapeHtml(e.item_id) + '</code></td>' +
    '<td class="amount">' + fmtPrice(e.amount) + '</td>' +
    '<td>' + escapeHtml(e.memo || '') + '</td>' +
  '</tr>';
}

async function refresh() {
  try {
    const r = await fetch('/api/ledger');
    const j = await r.json();
    document.getElementById('totals').innerHTML = renderTotals(j.totals || {});
    const rows = document.getElementById('rows');
    const empty = document.getElementById('empty');
    const entries = j.entries || [];
    if (!entries.length) {
      rows.innerHTML = '';
      empty.style.display = 'block';
      return;
    }
    empty.style.display = 'none';
    rows.innerHTML = entries.map(renderRow).join('');
  } catch (e) {
    console.error(e);
  }
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>"""


ITEM_HTML = """<!DOCTYPE html><html><body><paypal-button id="paypal-button"></paypal-button></body></html>"""
