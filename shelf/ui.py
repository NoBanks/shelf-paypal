"""Self-contained HTML pages for the SHELF web app."""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SHELF x PayPal - Dashboard</title>
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
  .status-paid, .status-shipped { background: #1e3427; color: #95e0b8; }
  .paid { color: #95e0b8; font-weight: 600; font-size: 14px; line-height: 1.5; }
  .hint { color: #94b3a2; font-weight: 400; font-size: 12px; }
  .note { color: #d4a07f; font-size: 12px; margin-top: 6px; }
  .shiprow { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
  .shiprow input, .shiprow select {
    background: #0c120e; color: #e9efe9; border: 1px solid #2c4536; border-radius: 999px;
    padding: 8px 12px; font-size: 13px; flex: 1; min-width: 120px;
  }
  .linkbtn {
    display: inline-block; background: #7fd4a8; color: #0c120e; padding: 10px 20px;
    border-radius: 999px; font-weight: 600; font-size: 14px; text-decoration: none;
  }
  .linkbtn:hover { background: #95e0b8; }
  code { color: #7fd4a8; font-size: 12px; }
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
    const r = await fetch('/api/items', { method: 'POST', body: fd, headers: adminHeaders() });
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
    actions = '<button onclick="approve(\\'' + item.id + '\\')">Approve</button>' +
      (item.notes ? '<div class="note">' + escapeHtml(item.notes) + '</div>' : '');
  } else if (status === 'live') {
    actions = '<a class="linkbtn" href="/store/' + item.id + '" target="_blank">View on store</a>' +
      '<span class="hint">PayPal checkout is live. Sale books itself.</span>';
  } else if (status === 'paid') {
    actions = '<div class="paid">PAID ' + fmtPrice(item.sold_price) +
      (item.net_amount ? ' <span class="hint">(net ' + fmtPrice(item.net_amount) + ')</span>' : '') +
      '<br><span class="hint">PayPal capture <code>' + escapeHtml(item.paypal_capture_id || '') + '</code>' +
      (item.buyer_email ? ' · ' + escapeHtml(item.buyer_email) : '') + '</span></div>' +
      '<div class="shiprow"><input id="trk-' + item.id + '" placeholder="tracking number">' +
      '<select id="car-' + item.id + '"><option>USPS</option><option>UPS</option><option>FEDEX</option><option>DHL</option><option>OTHER</option></select>' +
      '<button onclick="ship(\\'' + item.id + '\\')">Ship it</button></div>';
  } else if (status === 'shipped') {
    actions = '<div class="paid">SHIPPED ' + escapeHtml(item.carrier || '') + ' ' + escapeHtml(item.tracking_number || '') +
      '<br><span class="hint">buyer notified through PayPal · capture <code>' + escapeHtml(item.paypal_capture_id || '') + '</code></span></div>';
  } else if (status === 'sold') {
    actions = '<button onclick="markPaid(\\'' + item.id + '\\')">Mark paid (cash)</button>';
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

function adminHeaders() {
  let t = localStorage.getItem('shelf_admin');
  if (t === null) { t = prompt('Seller token (blank if none)') || ''; localStorage.setItem('shelf_admin', t); }
  return t ? { 'X-Shelf-Admin': t } : {};
}

async function adminPost(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: Object.assign({ 'Content-Type': 'application/json' }, adminHeaders()),
    body: body ? JSON.stringify(body) : undefined
  });
  if (r.status === 401) { localStorage.removeItem('shelf_admin'); alert('Wrong seller token. Try again.'); }
  else if (!r.ok) { let d = ''; try { d = (await r.json()).detail; } catch (e) {} alert('Failed: ' + (d || r.status)); }
  return r;
}

async function approve(id) {
  await adminPost('/api/items/' + id + '/approve');
  refresh();
}

async function ship(id) {
  const trk = document.getElementById('trk-' + id).value.trim();
  const car = document.getElementById('car-' + id).value;
  if (!trk) { alert('Enter the tracking number first.'); return; }
  await adminPost('/api/items/' + id + '/ship', { tracking_number: trk, carrier: car });
  refresh();
}

async function markSold(id) {
  const p = prompt('Sold price?');
  if (!p) return;
  await adminPost('/api/items/' + id + '/sold', { price: parseFloat(p) });
  refresh();
}

async function markPaid(id) {
  await adminPost('/api/items/' + id + '/paid');
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
  .item .title a { color: inherit; text-decoration: none; }
  .item .title a:hover { color: #7fd4a8; }
  .item .buy {
    display: block; margin-top: 14px; text-align: center; background: #ffc439; color: #003087;
    padding: 11px 16px; border-radius: 999px; font-weight: 700; font-size: 14px; text-decoration: none;
  }
  .item .buy:hover { background: #ffd56b; }
</style>
</head>
<body>
<header>
  <h1>SHELF</h1>
  <div class="tagline">honest listings, agent-made, human-approved, paid through PayPal</div>
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
  const href = '/store/' + item.id;
  return '<div class="item">' +
    '<a href="' + href + '">' + (photo ? '<img class="photo" src="' + photo + '" alt="">' : '<div class="photo"></div>') + '</a>' +
    '<div class="body">' +
      '<div class="title"><a href="' + href + '">' + escapeHtml(item.title || '(untitled)') + '</a></div>' +
      '<div class="price">' + fmtPrice(item.price) + '</div>' +
      '<div class="desc">' + escapeHtml(shortDesc) + (hasMore ? '...' : '') + '</div>' +
      (hasMore ? '<button class="toggle" onclick="toggleDesc(this)">read more</button>' : '') +
      '<div class="full-desc">' + escapeHtml(item.description || '') + '</div>' +
      '<a class="buy" href="' + href + '">Buy with PayPal</a>' +
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
      <th>PayPal capture</th>
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
    '<div class="stat"><div class="label">Paid via PayPal</div><div class="value">' + fmtPrice(t.paid_total) + '</div></div>' +
    '<div class="stat"><div class="label">Net after fees</div><div class="value">' + fmtPrice(t.net_total) + '</div></div>' +
    '<div class="stat"><div class="label">Shipped</div><div class="value">' + (t.shipped_count || 0) + '</div></div>';
}

function renderRow(e) {
  return '<tr>' +
    '<td>' + fmtTime(e.created) + '</td>' +
    '<td><span class="kind kind-' + escapeHtml(e.kind) + '">' + escapeHtml(e.kind) + '</span></td>' +
    '<td><code>' + escapeHtml(e.item_id) + '</code></td>' +
    '<td class="amount">' + fmtPrice(e.amount) + '</td>' +
    '<td>' + escapeHtml(e.memo || '') + '</td>' +
    '<td><code>' + escapeHtml(e.paypal_capture_id || '') + '</code></td>' +
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


ITEM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SHELF - Item</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0c120e; color: #e9efe9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    min-height: 100vh; padding: 24px 16px;
  }
  header { text-align: center; margin-bottom: 24px; }
  h1 { font-size: 28px; letter-spacing: 6px; color: #7fd4a8; }
  h1 a { color: inherit; text-decoration: none; }
  .wrap { max-width: 960px; margin: 0 auto; display: grid; grid-template-columns: 1fr; gap: 24px; }
  @media (min-width: 760px) { .wrap { grid-template-columns: 1.1fr 1fr; } }
  .gallery img { width: 100%; border-radius: 10px; background: #090e0b; display: block; margin-bottom: 8px; }
  .thumbs { display: flex; gap: 6px; flex-wrap: wrap; }
  .thumbs img { width: 64px; height: 64px; object-fit: cover; border-radius: 6px; cursor: pointer; border: 1px solid #1e2c23; }
  .panel { background: #121a15; border: 1px solid #1e2c23; border-radius: 10px; padding: 24px; }
  .title { font-size: 22px; font-weight: 600; margin-bottom: 8px; }
  .price { color: #7fd4a8; font-size: 28px; font-weight: 700; margin-bottom: 14px; }
  .meta { color: #94b3a2; font-size: 13px; margin-bottom: 14px; }
  .desc { color: #b9cfc0; font-size: 14px; line-height: 1.6; white-space: pre-wrap; margin-bottom: 20px; }
  .flaws { background: #1a2420; border-left: 3px solid #d4a07f; padding: 10px 12px; border-radius: 6px;
           font-size: 13px; color: #e0c3ad; margin-bottom: 20px; }
  .flaws b { color: #f0d2b8; }
  .pay { margin-top: 8px; }
  paypal-button, paypal-pay-later-button { display: block; margin-bottom: 10px; }
  .status { padding: 12px 14px; border-radius: 8px; font-size: 14px; margin-top: 12px; display: none; line-height: 1.5; }
  .status.show { display: block; }
  .status.ok { background: #1e3427; color: #95e0b8; }
  .status.warn { background: #3a2f1a; color: #f0d2b8; }
  .status.err { background: #3a1e1e; color: #f0b8b8; }
  .sold { background: #1e3427; color: #95e0b8; padding: 14px; border-radius: 8px; font-weight: 600; }
  .sandbox { font-size: 11px; color: #567a67; margin-top: 10px; }
  nav { text-align: center; margin-top: 28px; }
  nav a { color: #94b3a2; text-decoration: none; margin: 0 10px; font-size: 13px; }
  code { color: #7fd4a8; }
</style>
</head>
<body>
<header><h1><a href="/store">SHELF</a></h1></header>
<div class="wrap">
  <div class="gallery"><img id="hero" alt=""><div class="thumbs" id="thumbs"></div></div>
  <div class="panel">
    <div class="title" id="title">Loading...</div>
    <div class="price" id="price"></div>
    <div class="meta" id="meta"></div>
    <div class="flaws" id="flaws" style="display:none"></div>
    <div class="desc" id="desc"></div>
    <div class="pay" id="pay">
      <paypal-button id="paypal-button" type="pay" hidden></paypal-button>
      <paypal-pay-later-button id="paylater-button" hidden></paypal-pay-later-button>
    </div>
    <div class="status" id="status"></div>
    <div class="sandbox" id="sandbox"></div>
  </div>
</div>
<nav><a href="/store">back to the shelf</a></nav>

<script>
const itemId = location.pathname.split('/').pop();
let item = null;
let cfg = null;

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function fmtPrice(p) { return '$' + Number(p || 0).toFixed(2); }
function setStatus(kind, html) {
  const el = document.getElementById('status');
  el.className = 'status show ' + kind;
  el.innerHTML = html;
}
function showHero(src) { document.getElementById('hero').src = src; }

async function loadItem() {
  const r = await fetch('/api/store-items/' + itemId);
  if (!r.ok) { document.getElementById('title').textContent = 'This item is not available.'; return; }
  item = await r.json();
  document.title = 'SHELF - ' + (item.title || 'Item');
  document.getElementById('title').textContent = item.title || '(untitled)';
  document.getElementById('price').textContent = fmtPrice(item.price);
  document.getElementById('desc').textContent = item.description || '';
  const meta = [];
  if (item.condition) meta.push('condition: ' + String(item.condition).replace('_', ' '));
  meta.push('ships from Apple Valley, CA');
  document.getElementById('meta').textContent = meta.join(' | ');
  if (item.flaws && item.flaws.length) {
    const f = document.getElementById('flaws');
    f.style.display = 'block';
    f.innerHTML = '<b>Disclosed flaws:</b> ' + escapeHtml(item.flaws.join('; '));
  }
  const photos = item.photos || [];
  if (photos.length) {
    showHero(photos[0]);
    const thumbs = document.getElementById('thumbs');
    photos.forEach(p => {
      const im = document.createElement('img');
      im.src = p;
      im.addEventListener('click', () => showHero(p));
      thumbs.appendChild(im);
    });
  }
  if (item.status !== 'live') {
    document.getElementById('pay').innerHTML = '<div class="sold">SOLD. Paid through PayPal' +
      (item.status === 'shipped' ? ', on its way.' : '.') + '</div>';
    return;
  }
  await loadPayPal();
}

async function loadPayPal() {
  const r = await fetch('/api/paypal/config');
  cfg = await r.json();
  if (!cfg.enabled) {
    setStatus('warn', 'Checkout is not configured on this deployment yet.');
    return;
  }
  document.getElementById('sandbox').textContent = cfg.sandbox
    ? 'PayPal sandbox: this is test money. Use a sandbox buyer account.' : '';
  const s = document.createElement('script');
  s.async = true;
  s.src = (cfg.sandbox ? 'https://www.sandbox.paypal.com' : 'https://www.paypal.com') + '/web-sdk/v6/core';
  s.onload = onPayPalWebSdkLoaded;
  s.onerror = () => setStatus('err', 'Could not load the PayPal SDK.');
  document.body.appendChild(s);
}

async function createOrder() {
  const r = await fetch('/api/paypal/orders', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ item_id: itemId })
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || ('Order creation failed (' + r.status + ')'));
  return { orderId: data.id };
}

async function captureOrder(orderId) {
  const r = await fetch('/api/paypal/orders/' + orderId + '/capture', { method: 'POST' });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || ('Capture failed (' + r.status + ')'));
  return data;
}

const paymentSessionOptions = {
  async onApprove(data) {
    setStatus('ok', 'Approved. Capturing payment...');
    try {
      const res = await captureOrder(data.orderId);
      setStatus('ok', 'Paid. PayPal capture <code>' + escapeHtml(res.capture_id) + '</code> for ' + fmtPrice(res.amount) +
        '.<br>The SHELF crew books the sale and the seller ships it. You will get tracking from PayPal.');
      document.getElementById('pay').innerHTML = '<div class="sold">SOLD. Thank you.</div>';
    } catch (e) {
      setStatus('err', 'Payment did not complete: ' + escapeHtml(e.message) + '. The item is still available.');
    }
  },
  onCancel(data) { setStatus('warn', 'Checkout cancelled. The item is still available.'); },
  onError(error) { setStatus('err', 'PayPal error: ' + escapeHtml(error && error.message || String(error))); }
};

async function onPayPalWebSdkLoaded() {
  try {
    const sdkInstance = await window.paypal.createInstance({
      clientId: cfg.client_id, components: ['paypal-payments'], pageType: 'checkout'
    });
    const methods = await sdkInstance.findEligibleMethods({ currencyCode: cfg.currency || 'USD' });
    if (methods.isEligible('paypal')) {
      const session = sdkInstance.createPayPalOneTimePaymentSession(paymentSessionOptions);
      const btn = document.getElementById('paypal-button');
      btn.removeAttribute('hidden');
      btn.addEventListener('click', async () => {
        try {
          const createOrderPromise = createOrder();  // not awaited: keeps the user activation
          await session.start({ presentationMode: 'auto' }, createOrderPromise);
        } catch (e) { setStatus('err', 'Could not start checkout: ' + escapeHtml(e.message)); }
      });
    } else {
      setStatus('warn', 'PayPal is not available for this purchase right now.');
    }
    if (methods.isEligible('paylater')) {
      const d = methods.getDetails('paylater');
      const session = sdkInstance.createPayLaterOneTimePaymentSession(paymentSessionOptions);
      const btn = document.getElementById('paylater-button');
      btn.productCode = d.productCode; btn.countryCode = d.countryCode;
      btn.removeAttribute('hidden');
      btn.addEventListener('click', async () => {
        try { await session.start({ presentationMode: 'auto' }, createOrder()); }
        catch (e) { setStatus('err', 'Could not start Pay Later: ' + escapeHtml(e.message)); }
      });
    }
  } catch (e) {
    setStatus('err', 'Failed to initialize PayPal: ' + escapeHtml(e.message));
    console.error(e);
  }
}

loadItem();
</script>
</body>
</html>"""
