/* Capstan · UI. Talks to Python through window.pywebview.api (see app/api.py). */
(() => {
  'use strict';
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const GB = 1024 ** 3;
  const CTX_STOPS = [2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144];

  const state = {
    settings: null, machine: null, user: null,
    view: 'search', prevView: 'search',
    sort: 'downloads', gguf: true, typeFilter: 'all', q: '', seq: 0,
    repo: null, shape: null, shapeState: 'idle', fits: null, avail: null,
    sel: new Set(), dest: '', ctx: 8192,
    jobs: [], library: [], libPaths: new Set(), libFilter: '',
    lastVramFree: null,
  };

  // ── utils ────────────────────────────────────────────────────────────
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const gb = (b, d = 1) => (b == null ? '—' : b >= GB * 0.95 ? `${(b / GB).toFixed(d)} GB` : `${Math.max(b / 1024 ** 2, 0.1).toFixed(0)} MB`);
  const num = (n) => (n >= 1e6 ? `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(n >= 1e4 ? 0 : 1)}K` : String(n || 0));
  const ctxLabel = (c) => (c >= 1024 ? `${Math.round(c / 1024)}K` : String(c));
  const rel = (iso) => {
    if (!iso) return '';
    const s = (Date.now() - new Date(typeof iso === 'number' ? iso * 1000 : iso).getTime()) / 1000;
    if (s < 3600) return `${Math.max(1, Math.round(s / 60))}m ago`;
    if (s < 86400) return `${Math.round(s / 3600)}h ago`;
    if (s < 86400 * 30) return `${Math.round(s / 86400)}d ago`;
    if (s < 86400 * 365) return `${Math.round(s / 86400 / 30)}mo ago`;
    return `${(s / 86400 / 365).toFixed(1)}y ago`;
  };
  const eta = (sec) => (!isFinite(sec) || sec <= 0 ? '—' : sec < 60 ? `${Math.round(sec)}s` : sec < 3600 ? `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s` : `${Math.floor(sec / 3600)}h ${Math.round((sec % 3600) / 60)}m`);
  const norm = (p) => (p || '').replace(/\//g, '\\').toLowerCase();
  const joinPath = (dir, file) => `${dir.replace(/[\\/]+$/, '')}\\${file.replace(/\//g, '\\')}`;
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

  // What a model does (types come from app/core/modeltype.py).
  const TYPE_META = {
    text: { label: 'Text', icon: 'ph-chat-text', tip: 'Chat / text generation' },
    vision: { label: 'Vision', icon: 'ph-eye', tip: 'Takes images as input. Vision projector (mmproj) included' },
    vision_no_proj: { label: 'Vision · no mmproj', icon: 'ph-eye-slash', dim: true, tip: 'Labeled vision, but this repo ships no vision projector (mmproj): image input won’t work from the GGUF alone' },
    omni: { label: 'Omni', icon: 'ph-atom', tip: 'Any-to-any: text, images, audio in and out' },
    stt: { label: 'Speech-to-text', icon: 'ph-microphone', tip: 'Transcribes or understands audio' },
    tts: { label: 'Text-to-speech', icon: 'ph-speaker-high', tip: 'Generates speech or audio' },
    music: { label: 'Music', icon: 'ph-music-notes', tip: 'Generates music' },
    audio_gen: { label: 'Audio gen', icon: 'ph-waveform', tip: 'Generates sound: effects, ambience, music' },
    audio: { label: 'Audio', icon: 'ph-waveform', tip: 'Audio model' },
    image_gen: { label: 'Image gen', icon: 'ph-image', tip: 'Generates or edits images' },
    video_gen: { label: 'Video gen', icon: 'ph-film-strip', tip: 'Generates video' },
    embeddings: { label: 'Embeddings', icon: 'ph-graph', tip: 'Turns text into vectors for search and RAG' },
    unlabeled: { label: 'Unlabeled', icon: 'ph-question', dim: true, tip: 'Hugging Face has no type for this repo, and nothing in it says what it does' },
  };
  const TYPE_NOUN = { text: 'text', vision: 'vision', audio: 'audio', image: 'image', video: 'video', embeddings: 'embedding' };
  const typeChips = (types) => (types || []).map((t) => {
    const m = TYPE_META[t]; if (!m) return '';
    return `<span class="chip chip--type${m.dim ? ' chip--dim' : ''}" title="${esc(m.tip)}"><i class="ph-duotone ${m.icon}"></i>${esc(m.label)}</span>`;
  }).join('');
  // Context and KV cache only mean something for models that hold a conversation.
  const isChatModel = (types) => !types || types.includes('unlabeled') || types.some((t) => ['text', 'vision', 'vision_no_proj', 'omni', 'stt'].includes(t));

  async function call(name, ...args) {
    const r = await window.pywebview.api[name](...args);
    if (r && typeof r === 'object' && r._exc) throw new Error(r.error);
    return r;
  }

  // DESIGN.md §3.3: every piece carries its own full metal gradient. Long repo names
  // ("Qwen3.5-9B-…-GGUF") are one "word", so they also split after hyphens, dots and
  // underscores. Each piece can then wrap on its own without the gradient stretching
  // across two lines.
  function splitWords(el) {
    if (el.classList.contains('is-split')) return;
    const words = el.textContent.trim().split(/\s+/);
    el.textContent = '';
    let i = 0;
    words.forEach((w, wi) => {
      const pieces = w.length > 14 ? w.split(/(?<=[-_.])/) : [w];
      pieces.forEach((p) => {
        const s = document.createElement('span');
        s.className = 'word'; s.style.setProperty('--i', i++); s.textContent = p;
        el.append(s);
      });
      if (wi < words.length - 1) el.append(' ');
    });
    el.classList.add('is-split');
  }
  const splitAll = (root = document) => $$('[data-split]', root).forEach(splitWords);

  function toast(msg, kind = 'ok', icon) {
    const t = document.createElement('div');
    t.className = `toast toast--${kind}`;
    t.innerHTML = `<i class="ph-duotone ${icon || (kind === 'err' ? 'ph-warning-octagon' : 'ph-check-circle')}"></i><span>${esc(msg)}</span>`;
    $('[data-toasts]').append(t);
    setTimeout(() => { t.classList.add('is-out'); setTimeout(() => t.remove(), 320); }, kind === 'err' ? 6000 : 3800);
  }

  function confirmDialog(title, body, okText = 'OK') {
    const d = $('[data-dialog]');
    $('[data-dialog-title]', d).textContent = title;
    $('[data-dialog-body]', d).textContent = body;
    $('[data-dialog-ok]', d).textContent = okText;
    d.returnValue = '';
    d.showModal();
    return new Promise((res) => d.addEventListener('close', () => res(d.returnValue === 'ok'), { once: true }));
  }

  // ── views ────────────────────────────────────────────────────────────
  function show(view) {
    if (view !== 'repo') state.prevView = view === state.view ? state.prevView : state.view;
    state.view = view;
    $$('[data-pane]').forEach((p) => p.classList.toggle('is-active', p.dataset.pane === view));
    $$('.rail__btn').forEach((b) => b.classList.toggle('is-active', b.dataset.view === (view === 'repo' ? 'search' : view)));
    window.DPMist?.level(view === 'search' && !state.q ? 0.32 : 0.2);
    if (view === 'library') loadLibrary();
    if (view === 'settings') renderSettings();
    if (view === 'queue') renderQueue();
  }

  // ── machine strip ────────────────────────────────────────────────────
  function renderMachine() {
    const m = state.machine;
    if (!m) return;
    const g = m.gpu;
    const vram = $('[data-vram]');
    if (g) {
      $('[data-gpu-name]').textContent = g.name;
      const segs = 24, used = Math.round((g.used / g.total) * segs);
      if (vram.children.length !== segs) vram.innerHTML = '<span></span>'.repeat(segs);
      [...vram.children].forEach((s, i) => { s.className = i < used ? 'is-used' : ''; });
      vram.setAttribute('aria-label', `VRAM ${gb(g.free)} free of ${gb(g.total)}`);
      $('[data-gpu-val]').innerHTML = `<b>${gb(g.free)}</b> free<span class="tot"> / ${gb(g.total, 0)}</span>`;
      const who = (g.users || []).map((u) => u.name);
      $('[data-gpu-who]').innerHTML = who.length ? `<i class="ph-duotone ph-cpu"></i> ${esc(who.join(', '))} holding VRAM` : '';
    } else {
      $('[data-gpu-name]').textContent = 'GPU';
      vram.innerHTML = '';
      $('[data-gpu-val]').textContent = 'No NVIDIA GPU found';
    }
    const r = m.ram;
    const ramBar = $('[data-ram-bar]');
    ramBar.style.width = `${(1 - r.available / r.total) * 100}%`;
    ramBar.parentElement.classList.toggle('is-low', r.available < 2 * GB);
    $('[data-ram-val]').innerHTML = `<b>${gb(r.available)}</b> free<span class="tot"> / ${gb(r.total, 0)}</span>`;
    const destDrive = (state.view === 'repo' ? state.dest : state.settings?.download_root || '').slice(0, 2).toUpperCase();
    $('[data-drives]').innerHTML = m.drives.map((d) => {
      const low = d.free < 15 * GB;
      return `<div class="drive${d.drive === destDrive ? ' is-dest' : ''}" title="${esc(d.drive)} ${gb(d.free)} free of ${gb(d.total, 0)}">
        <span class="drive__l">${esc(d.drive)}</span>
        <div class="minibar${low ? ' is-low' : ''}"><span style="width:${(1 - d.free / d.total) * 100}%"></span></div>
        <span class="machine__val"><b>${gb(d.free)}</b></span></div>`;
    }).join('');
  }

  async function pollMachine() {
    if (!document.hidden) {
      try {
        state.machine = await call('machine');
        renderMachine();
        const f = state.machine.gpu?.free ?? null;
        if (state.view === 'repo' && state.settings.judge === 'free' && state.lastVramFree != null && f != null &&
            Math.abs(f - state.lastVramFree) > 256 * 1024 ** 2) refit();
        if (state.view === 'repo') updatePullbar();
      } catch { /* keep the last good snapshot */ }
    }
    setTimeout(pollMachine, 2000);
  }

  // ── search ───────────────────────────────────────────────────────────
  const looksLikeLink = (t) => /^(https?:\/\/)?(www\.)?(huggingface\.co|hf\.co)\//i.test(t.trim());
  const looksLikeRepo = (t) => /^[A-Za-z0-9][\w.-]*\/[\w.-]+$/.test(t.trim());

  async function runSearch() {
    const q = state.q.trim();
    const seq = ++state.seq;
    $('[data-hero]').hidden = !!q;
    window.DPMist?.level(state.view === 'search' && !q ? 0.32 : 0.2);
    const box = $('[data-results]');
    if (looksLikeLink(q)) {
      const link = await call('parse_link', q).catch(() => null);
      if (seq !== state.seq) return;
      if (link?.error) { box.innerHTML = `<div class="empty"><i class="ph-duotone ph-link-break"></i>${esc(link.error)}</div>`; return; }
      if (link?.repo_id) { box.innerHTML = linkCard(link); bindResults(box); $('[data-results-meta]').textContent = ''; return; }
    }
    $('[data-spin]').hidden = false;
    try {
      const sort = state.sort, tf = state.typeFilter;
      const r = await call('search', q, sort, state.gguf, tf);
      if (seq !== state.seq) return;
      const top = looksLikeRepo(q) && !r.results.some((x) => x.id.toLowerCase() === q.toLowerCase()) ? linkCard({ repo_id: q }) : '';
      const heading = { downloads: 'Most downloaded', trending: 'Trending', likes: 'Most liked', updated: 'Newest' }[sort];
      const noun = tf === 'all' ? '' : `${TYPE_NOUN[tf]} `;
      const label = q ? '' : `<div class="results__label label-engraved">${heading} ${noun}${state.gguf ? 'GGUF ' : ''}models on the Hub</div>`;
      const what = q ? `“${esc(q)}”` : 'this search';
      const none = tf !== 'all' ? `No ${noun}models match ${what}${state.gguf ? ' in GGUF' : ''}. Try “All”${state.gguf ? ' or turning off “GGUF only”' : ''}.`
        : `No models match ${what}${state.gguf ? ' in GGUF. Try turning off “GGUF only”.' : '.'}`;
      box.innerHTML = label + top + (r.results.length ? r.results.map(resultRow).join('') :
        `<div class="empty"><i class="ph-duotone ph-magnifying-glass"></i>${none}</div>`);
      const n = r.results.length, cap = tf === 'all' ? 40 : 60;
      $('[data-results-meta]').textContent = n ? `${n} ${noun || ''}${tf === 'all' ? 'results' : 'models'}${n >= cap ? ` (top ${cap})` : ''}` : '';
      bindResults(box);
    } catch (e) {
      if (seq === state.seq) box.innerHTML = `<div class="empty"><i class="ph-duotone ph-wifi-slash"></i>Search failed: ${esc(e.message)}</div>`;
    } finally {
      if (seq === state.seq) $('[data-spin]').hidden = true;
    }
  }
  const searchSoon = debounce(runSearch, 300);

  function linkCard(link) {
    return `<button type="button" class="result result--link enter" data-open="${esc(link.repo_id)}" data-rev="${esc(link.revision || '')}" data-file="${esc(link.file || '')}">
      <div><div class="result__name"><i class="ph-duotone ph-link"></i> ${esc(link.repo_id)}</div>
      <div class="result__author">${link.file ? esc(link.file) : 'Open this repo'}</div></div>
      <div class="result__meta"><span class="chip">Enter ↵</span></div></button>`;
  }
  function resultRow(m, i) {
    return `<button type="button" class="result enter" style="--i:${Math.min(i, 20)}" data-open="${esc(m.id)}">
      <div style="min-width:0"><div class="result__name">${esc(m.name)}</div><div class="result__author">${esc(m.author)}</div></div>
      <div class="result__meta">
        <span class="result__types">${typeChips(m.types)}</span>
        ${m.size_class ? `<span class="chip chip--quant">${esc(m.size_class)}</span>` : ''}
        ${m.gated ? '<span class="chip chip--dim"><i class="ph-duotone ph-lock-simple"></i>Gated</span>' : ''}
        <span title="Downloads (last 30 days)"><i class="ph-duotone ph-download-simple"></i>${num(m.downloads)}</span>
        <span title="Likes"><i class="ph-duotone ph-heart"></i>${num(m.likes)}</span>
        <span title="Last updated">${rel(m.updated)}</span>
      </div></button>`;
  }
  function bindResults(box) {
    $$('[data-open]', box).forEach((b) => b.addEventListener('click', () => openRepo(b.dataset.open, b.dataset.rev || null, b.dataset.file || null)));
  }

  // ── repo view ────────────────────────────────────────────────────────
  async function openRepo(repoId, revision = null, file = null) {
    const pane = $('[data-pane="repo"]');
    state.repo = null; state.shape = null; state.fits = null; state.sel = new Set(); state.shapeState = 'idle';
    pane.innerHTML = `<button type="button" class="back" data-back><i class="ph-duotone ph-arrow-left"></i>Back</button>
      <div class="empty"><span class="searchbar__spin" style="display:inline-block"></span><br>Opening ${esc(repoId)}…</div>`;
    $('[data-back]', pane).addEventListener('click', back);
    show('repo');
    let r;
    try { r = await call('open_repo', repoId, revision); } catch (e) { r = { error: e.message }; }
    if (r.error) {
      pane.innerHTML = `<button type="button" class="back" data-back><i class="ph-duotone ph-arrow-left"></i>Back</button>
        <div class="notice"><strong>${esc(repoId)}</strong><br>${r.error === 'gated' ? esc(r.message).replace(/`([^`]+)`/g, '<code>$1</code>') : esc(r.error)}
        <div style="margin-top:14px"><button type="button" class="btn btn--ghost btn--sm" data-hf><i class="ph-duotone ph-arrow-square-out"></i>Open on Hugging Face</button></div></div>`;
      $('[data-back]', pane).addEventListener('click', back);
      $('[data-hf]', pane).addEventListener('click', () => call('open_url', `https://huggingface.co/${repoId}`));
      return;
    }
    state.repo = r;
    state.dest = r.default_dir;
    const maxCtx = r.context_max || 131072;
    state.ctx = Math.min(state.settings.context, maxCtx);
    if (file) {
      const g = r.gguf.find((x) => x.files.some((f) => f.path === file));
      if (g) state.sel.add(g.key);
      else if (r.other.some((f) => f.path === file)) state.sel.add(`other:${file}`);
    }
    renderRepo();
    loadShape();
  }

  function back() { show(state.prevView === 'repo' ? 'search' : state.prevView); }

  function modelRows() { return state.repo.gguf.filter((g) => !g.mmproj); }

  async function loadShape() {
    const rows = modelRows();
    if (!rows.length) { state.shapeState = 'none'; refit(); return; }
    state.shapeState = 'loading';
    renderFitCells();
    // One header per repo: all quants of a model share its shape. Smallest file is quickest.
    const pick = [...rows].sort((a, b) => a.size - b.size)[0];
    try {
      const s = await call('shape', state.repo.repo_id, pick.header_file, state.repo.revision);
      state.shape = s.shape;
      state.shapeState = 'ok';
      if (state.shape?.context_max) {
        state.repo.context_max = state.shape.context_max;
        state.ctx = Math.min(state.ctx, state.shape.context_max);
        renderCtx();
      }
    } catch {
      state.shape = null; state.shapeState = 'failed';
    }
    refit();
  }

  async function refit() {
    if (!state.repo) return;
    const items = modelRows().map((g) => ({ key: g.key, size: g.size }));
    if (!items.length) { renderFitCells(); return; }
    try {
      const r = await call('fit', items, state.shape, state.ctx, state.settings.judge, state.settings.kv_type, isChatModel(state.repo.types));
      state.fits = r.est; state.avail = r;
      state.lastVramFree = state.machine?.gpu?.free ?? null;
    } catch { state.fits = null; }
    renderFitCells();
  }

  function ctxStops() {
    const max = state.repo?.context_max || 131072;
    const s = CTX_STOPS.filter((c) => c <= max);
    if (!s.length || s[s.length - 1] !== max) s.push(max);
    return s;
  }

  function renderRepo() {
    const r = state.repo;
    const pane = $('[data-pane="repo"]');
    const params = r.params ? `${(r.params / 1e9).toFixed(r.params < 1e10 ? 1 : 0)}B params` : r.size_class;
    const models = r.gguf.filter((g) => !g.mmproj), proj = r.gguf.filter((g) => g.mmproj);
    const chat = isChatModel(r.types);
    pane.innerHTML = `
      <button type="button" class="back" data-back><i class="ph-duotone ph-arrow-left"></i>Back</button>
      <div class="repohead">
        <div style="min-width:0">
          <div class="repohead__author">${esc(r.author)}</div>
          <h2 class="repohead__title headline-silver" data-split>${esc(r.name)}</h2>
          <div class="repohead__stats">
            ${typeChips(r.types)}
            ${params ? `<span class="chip chip--quant">${esc(params)}</span>` : ''}
            ${r.architecture ? `<span class="chip">${esc(r.architecture)}</span>` : ''}
            ${r.context_max ? `<span class="chip">${ctxLabel(r.context_max)} context</span>` : ''}
            <span class="chip"><i class="ph-duotone ph-download-simple"></i>${num(r.downloads)}</span>
            <span class="chip"><i class="ph-duotone ph-heart"></i>${num(r.likes)}</span>
            ${r.updated ? `<span class="chip chip--dim">updated ${rel(r.updated)}</span>` : ''}
            ${r.gated ? '<span class="chip chip--dim"><i class="ph-duotone ph-lock-simple"></i>Gated</span>' : ''}
          </div>
        </div>
        <button type="button" class="btn btn--ghost btn--sm" data-hf><i class="ph-duotone ph-arrow-square-out"></i>Hugging Face</button>
      </div>

      ${models.length ? `
      <div class="fitbar">
        <div class="fitbar__ctx"${chat ? '' : ' hidden'}>
          <span class="label-engraved">Context</span>
          <div style="flex:1;display:grid">
            <input type="range" min="0" max="${ctxStops().length - 1}" step="1" data-ctx aria-label="Context length">
            <div class="ticks" data-ticks></div>
          </div>
          <span class="fitbar__ctxval" data-ctxval></span>
        </div>
        <div class="seg" data-judge role="radiogroup" aria-label="Judge against">
          <button type="button" data-v="free" title="VRAM and RAM free right now">Free now</button>
          <button type="button" data-v="total" title="As if nothing else were loaded">Total</button>
        </div>
        <select class="field field--sm" data-kv style="width:auto" title="KV cache type"${chat ? '' : ' hidden'}>
          <option value="f16">KV f16</option><option value="q8_0">KV q8_0</option><option value="q4_0">KV q4_0</option>
        </select>
        <div class="fitbar__note" data-shape-note></div>
      </div>
      <div class="files">
        <div class="files__head"><span></span><span>Quant</span><span>File</span><span style="text-align:right">Size</span><span>Fit on this PC</span></div>
        ${models.map(fileRow).join('')}
      </div>` : `<div class="notice"><strong>No GGUF files in this repo.</strong> You can still download any of its files below. The fit check works for GGUF only.</div>`}

      ${proj.length ? `<div class="files">
        <div class="files__cap label-engraved">${r.vision_projector ? 'Vision projectors (mmproj): needed for image input' : 'Projectors (mmproj): add-on encoders the model needs for non-text input'}</div>
        ${proj.map(fileRow).join('')}</div>` : ''}

      ${r.other.length ? `<details class="others"${models.length ? '' : ' open'}><summary>Other files (${r.other.length})</summary>
        <div class="files">${r.other.map(otherRow).join('')}</div></details>` : ''}

      <div class="pullbar">
        <div class="pullbar__dest">
          <span class="label-engraved">To</span>
          <span class="pullbar__path" data-dest title="${esc(state.dest)}">${esc(state.dest)}</span>
          <button type="button" class="iconbtn" data-dest-pick title="Change folder"><i class="ph-duotone ph-folder-open"></i></button>
        </div>
        <span class="pullbar__disk" data-disk></span>
        <span class="pullbar__sum" data-sum></span>
        <button type="button" class="btn btn--primary" data-pull disabled><i class="ph-duotone ph-download-simple"></i>Pull</button>
      </div>`;
    splitAll(pane);
    $('[data-back]', pane).addEventListener('click', back);
    $('[data-hf]', pane).addEventListener('click', () => call('open_url', `https://huggingface.co/${r.repo_id}`));
    $$('.frow', pane).forEach((row) => row.addEventListener('click', (e) => {
      const key = row.dataset.key;
      if (state.sel.has(key)) state.sel.delete(key); else state.sel.add(key);
      row.classList.toggle('is-sel', state.sel.has(key));
      $('.check', row).checked = state.sel.has(key);
      if (e.target.classList.contains('check')) e.stopPropagation();
      updatePullbar();
    }));
    if (models.length) {
      const range = $('[data-ctx]', pane);
      range.addEventListener('input', () => {
        state.ctx = ctxStops()[+range.value];
        renderCtx(false);
        refitSoon();
      });
      range.addEventListener('change', () => call('settings', { context: state.ctx }).then((s) => (state.settings = s)).catch(() => {}));
      renderCtx();
      $$('[data-judge] button', pane).forEach((b) => b.addEventListener('click', async () => {
        state.settings = await call('settings', { judge: b.dataset.v });
        markSeg($('[data-judge]', pane), state.settings.judge);
        refit();
      }));
      markSeg($('[data-judge]', pane), state.settings.judge);
      const kv = $('[data-kv]', pane);
      kv.value = state.settings.kv_type;
      kv.addEventListener('change', async () => { state.settings = await call('settings', { kv_type: kv.value }); refit(); });
    }
    $('[data-dest-pick]', pane).addEventListener('click', async () => {
      const p = await call('choose_folder', state.dest).catch(() => null);
      if (p) { state.dest = p; $('[data-dest]').textContent = p; $('[data-dest]').title = p; renderFitCells(); updatePullbar(); renderMachine(); }
    });
    $('[data-pull]', pane).addEventListener('click', pull);
    renderFitCells();
    updatePullbar();
    renderMachine();
  }
  const refitSoon = debounce(refit, 90);

  function markSeg(seg, v) { $$('button', seg).forEach((b) => { b.classList.toggle('is-on', b.dataset.v === v); b.setAttribute('aria-checked', b.dataset.v === v); }); }

  function renderCtx(setRange = true) {
    const stops = ctxStops();
    const range = $('[data-ctx]');
    if (!range) return;
    let i = stops.indexOf(state.ctx);
    if (i < 0) { i = stops.findIndex((c) => c >= state.ctx); if (i < 0) i = stops.length - 1; state.ctx = stops[i]; }
    range.max = stops.length - 1;
    if (setRange) range.value = i;
    range.style.setProperty('--p', `${(i / Math.max(stops.length - 1, 1)) * 100}%`);
    $('[data-ctxval]').textContent = ctxLabel(state.ctx);
    $('[data-ticks]').innerHTML = stops.map((c) => `<span>${ctxLabel(c)}</span>`).join('');
  }

  function rowState(paths) {
    const onDisk = paths.every((p) => state.libPaths.has(norm(joinPath(state.dest, p))));
    if (onDisk) return '<small>· on disk</small>';
    const job = state.jobs.find((j) => j.repo_id === state.repo.repo_id && paths.includes(j.filename) && j.state !== 'done');
    return job ? `<small>· ${job.state === 'running' ? 'downloading' : job.state}</small>` : '';
  }
  function fileRow(g) {
    const sel = state.sel.has(g.key);
    return `<div class="frow${sel ? ' is-sel' : ''}" data-key="${esc(g.key)}" title="${esc(g.files.map((f) => f.path).join('\n'))}">
      <input type="checkbox" class="check" ${sel ? 'checked' : ''} aria-label="Select ${esc(g.name)}" tabindex="-1">
      <span>${g.quant ? `<span class="chip chip--quant">${esc(g.quant)}</span>` : ''}</span>
      <span class="frow__label">${esc(g.label)}${g.parts > 1 ? `<small>${g.parts} parts</small>` : ''}<span data-rowstate>${rowState(g.files.map((f) => f.path))}</span></span>
      <span class="frow__size">${gb(g.size)}</span>
      <span data-fit="${esc(g.key)}">${g.mmproj ? `<span class="fit fit--unknown"><span class="gauge"></span><span class="fit__txt"><span class="fit__lvl">Add-on</span><span class="fit__det">+${gb(g.size)} on top of the model</span></span></span>` : ''}</span>
    </div>`;
  }
  function otherRow(f) {
    const key = `other:${f.path}`;
    const sel = state.sel.has(key);
    return `<div class="frow${sel ? ' is-sel' : ''}" data-key="${esc(key)}">
      <input type="checkbox" class="check" ${sel ? 'checked' : ''} aria-label="Select ${esc(f.path)}" tabindex="-1"><span></span>
      <span class="frow__label">${esc(f.path)}<span data-rowstate>${rowState([f.path])}</span></span>
      <span class="frow__size">${gb(f.size)}</span><span></span></div>`;
  }

  function renderFitCells() {
    if (!state.repo) return;
    const freeDisk = (state.machine?.drives || []).find((d) => d.drive === state.dest.slice(0, 2).toUpperCase())?.free;
    const note = $('[data-shape-note]');
    if (note) {
      const s = state.shape;
      note.textContent = !isChatModel(state.repo.types)
        ? `Not a chat model, so there is no context cache: the estimate is the file plus runtime overhead, judged against ${state.settings.judge === 'free' ? 'what is free right now' : 'total VRAM and RAM'}. Diffusion and audio runtimes may also load extra encoders.`
        : state.shapeState === 'loading' ? 'Reading the GGUF header from Hugging Face…'
        : state.shapeState === 'failed' ? 'Could not read the GGUF header: showing a rough estimate from file size.'
        : s ? `${s.architecture} · ${s.layers} layers${s.layer_kind.includes('linear') ? ` (${s.layer_kind.filter((k) => k === 'full').length} full-attention)` : s.layer_kind.includes('swa') ? ` (sliding window ${s.sliding_window})` : ''} · estimate, judged against ${state.settings.judge === 'free' ? 'what is free right now' : 'total VRAM and RAM'}`
        : '';
    }
    for (const g of modelRows()) {
      const cell = $(`[data-fit="${CSS.escape(g.key)}"]`);
      if (!cell) continue;
      const disk = freeDisk != null && g.size > freeDisk ? '<span class="fit__disk">DISK</span>' : '';
      if (state.shapeState === 'loading' || !state.fits) {
        cell.innerHTML = `<span class="fit fit--loading"><span class="gauge"></span><span class="fit__txt"><span class="fit__lvl">Checking</span><span class="fit__det">reading the model</span></span></span>`;
        continue;
      }
      const e = state.fits[g.key];
      if (!e) continue;
      const vram = state.avail?.vram ?? 0;
      let lvl, det;
      if (e.level === 'fits') { lvl = 'Fits'; det = `Fully on GPU · needs ${gb(e.need)} of ${gb(e.vram_usable ?? vram)} usable`; }
      else if (e.level === 'partial') {
        lvl = 'Partial';
        det = e.gpu_layers == null ? `Needs ${gb(e.need)}; spills to RAM` : e.gpu_layers === 0 ? `CPU only · needs ${gb(e.need)}` : `~${e.gpu_layers}/${e.layers} layers on GPU · needs ${gb(e.need)}`;
      } else { lvl = "Won't run"; det = `Needs ${gb(e.need)} · ${gb(e.usable)} usable (VRAM + RAM)`; }
      const approx = e.approx ? ' (rough)' : '';
      const cls = e.level === 'none' ? 'none' : e.level;
      const gauge = e.level === 'partial' && e.gpu_layers != null && e.layers ? Math.max(8, Math.round((e.gpu_layers / e.layers) * 100)) : null;
      cell.innerHTML = `<span class="fit fit--${cls}" title="Weights ${gb(e.weights)} + KV cache ${gb(e.kv, 2)} + overhead ${gb(e.overhead, 2)} = ${gb(e.need)} at ${ctxLabel(e.ctx)} context">
        <span class="gauge"${gauge != null ? ` style="--g:${gauge}%"` : ''}></span>
        <span class="fit__txt"><span class="fit__lvl">${lvl}${approx}</span>${disk}<span class="fit__det">${det}</span></span></span>`;
    }
  }

  function selectedFiles() {
    const r = state.repo, out = [];
    for (const key of state.sel) {
      if (key.startsWith('other:')) {
        const f = r.other.find((x) => `other:${x.path}` === key);
        if (f) out.push({ path: f.path, size: f.size, sha256: f.sha256, quant: null });
      } else {
        const g = r.gguf.find((x) => x.key === key);
        if (g) g.files.forEach((f) => out.push({ ...f, quant: g.quant }));
      }
    }
    return out;
  }

  let diskSeq = 0;
  async function updatePullbar() {
    const btn = $('[data-pull]');
    if (!btn || !state.repo) return;
    const files = selectedFiles().filter((f) => !state.libPaths.has(norm(joinPath(state.dest, f.path))));
    const total = files.reduce((a, f) => a + (f.size || 0), 0);
    $('[data-sum]').textContent = files.length ? `${files.length} file${files.length > 1 ? 's' : ''} · ${gb(total)}` : '';
    btn.disabled = !files.length;
    const disk = $('[data-disk]');
    const seq = ++diskSeq;
    try {
      const c = await call('disk_check', state.dest, total);
      if (seq !== diskSeq) return;
      disk.classList.toggle('is-bad', !c.ok);
      disk.textContent = c.free == null ? '' : !c.ok ? `Not enough space on ${c.drive} (${gb(c.free - c.pending)} free)` : `${gb(c.free - c.pending)} free on ${c.drive}${total ? ` → ${gb(c.free - c.pending - total)} after` : ''}`;
      btn.disabled = !files.length || !c.ok;
    } catch { disk.textContent = ''; }
  }

  async function pull() {
    const files = selectedFiles().filter((f) => !state.libPaths.has(norm(joinPath(state.dest, f.path))));
    if (!files.length) return;
    const quant = files.find((f) => f.quant)?.quant || null;
    try {
      const r = await call('download', state.repo.repo_id, state.repo.revision, files, state.dest, quant);
      toast(r.added.length ? `Queued ${r.added.length} file${r.added.length > 1 ? 's' : ''} → ${state.dest}` : 'Already in the queue.', 'ok', 'ph-download-simple');
      state.sel.clear();
      $$('.frow.is-sel').forEach((row) => { row.classList.remove('is-sel'); $('.check', row).checked = false; });
      updatePullbar();
    } catch (e) { toast(`Could not start: ${e.message}`, 'err'); }
  }

  function refreshRowStates() {
    if (state.view !== 'repo' || !state.repo) return;
    $$('.frow').forEach((row) => {
      const key = row.dataset.key;
      const paths = key.startsWith('other:') ? [key.slice(6)] : (state.repo.gguf.find((g) => g.key === key)?.files.map((f) => f.path) || []);
      const slot = $('[data-rowstate]', row);
      if (slot) slot.innerHTML = rowState(paths);
    });
  }

  // ── queue ────────────────────────────────────────────────────────────
  function renderQueue() {
    const active = state.jobs.filter((j) => j.state !== 'done').length;
    const badge = $('[data-queue-badge]');
    badge.hidden = !active; badge.textContent = active;
    if (state.view !== 'queue') return;
    const box = $('[data-jobs]');
    if (!state.jobs.length) { box.innerHTML = `<div class="empty"><i class="ph-duotone ph-tray"></i>Nothing in the queue. Pick files in a repo and press Pull.</div>`; return; }
    const order = { running: 0, verifying: 0, queued: 1, paused: 2, error: 3, done: 4 };
    const jobs = [...state.jobs].sort((a, b) => order[a.state] - order[b.state] || a.added - b.added);
    box.innerHTML = jobs.map((j) => {
      const pct = j.state === 'verifying' ? (j.verify || 0) * 100 : j.size ? Math.min(100, (j.done / j.size) * 100) : 0;
      const label = { running: 'Downloading', verifying: 'Verifying SHA-256', queued: 'Queued', paused: 'Paused', error: 'Error', done: 'Done' }[j.state];
      const acts = [];
      if (j.state === 'running' || j.state === 'queued' || j.state === 'verifying') acts.push(`<button type="button" class="iconbtn" data-act="pause" title="Pause"><i class="ph-duotone ph-pause"></i></button>`);
      if (j.state === 'paused' || j.state === 'error') acts.push(`<button type="button" class="iconbtn" data-act="resume" title="${j.state === 'error' ? 'Retry' : 'Resume'}"><i class="ph-duotone ph-${j.state === 'error' ? 'arrow-clockwise' : 'play'}"></i></button>`);
      acts.push(`<button type="button" class="iconbtn" data-act="folder" title="Open folder"><i class="ph-duotone ph-folder-open"></i></button>`);
      if (j.state === 'done') acts.push(`<button type="button" class="iconbtn" data-act="copy" title="Copy path"><i class="ph-duotone ph-copy"></i></button>`);
      acts.push(`<button type="button" class="iconbtn" data-act="cancel" title="${j.state === 'done' ? 'Remove from list' : 'Cancel and delete the partial file'}"><i class="ph-duotone ph-x"></i></button>`);
      const stat = j.state === 'running'
        ? `<span>${pct.toFixed(1)}%</span><span>${gb(j.done)} / ${gb(j.size)}</span><span>${j.speed ? `${(j.speed / 1024 ** 2).toFixed(1)} MB/s` : '…'}</span><span>ETA ${eta((j.size - j.done) / j.speed)}</span>`
        : j.state === 'verifying' ? `<span>${pct.toFixed(0)}%</span>`
        : `<span>${gb(j.done)} / ${gb(j.size)}</span>`;
      return `<div class="job job--${j.state}" data-job="${esc(j.id)}">
        <div style="min-width:0"><div class="job__name">${esc(j.filename.split('/').pop())}</div><div class="job__repo">${esc(j.repo_id)} → <span class="mono">${esc(j.local_dir)}</span></div></div>
        <div class="job__acts">${acts.join('')}</div>
        <div class="job__bar"><span style="width:${j.state === 'done' ? 100 : pct}%"></span></div>
        <div class="job__stat"><span class="label-engraved">${label}</span>${stat}${j.error ? `<span class="job__err">${esc(j.error)}</span>` : ''}</div>
      </div>`;
    }).join('');
    $$('[data-job]', box).forEach((el) => {
      const j = state.jobs.find((x) => x.id === el.dataset.job);
      $$('[data-act]', el).forEach((b) => b.addEventListener('click', async () => {
        const a = b.dataset.act;
        if (a === 'folder') return call('open_folder', j.path || joinPath(j.local_dir, j.filename.split('/').slice(0, -1).join('/') || ''));
        if (a === 'copy') { await call('copy', j.path); return toast('Path copied.'); }
        if (a === 'cancel' && j.state !== 'done' && j.done > 0) {
          if (!(await confirmDialog('Cancel download?', `This deletes the ${gb(j.done)} partial file of ${j.filename}. Pause instead if you want to finish it later.`, 'Cancel download'))) return;
        }
        call(a, j.id);
      }));
    });
  }

  // ── library ──────────────────────────────────────────────────────────
  async function loadLibrary() {
    try {
      state.library = await call('library');
      state.libPaths = new Set(state.library.map((f) => norm(f.path)));
    } catch (e) { toast(`Library scan failed: ${e.message}`, 'err'); }
    renderLibrary();
    refreshRowStates();
  }
  function renderLibrary() {
    if (state.view !== 'library') return;
    const f = state.libFilter.toLowerCase();
    const items = state.library.filter((x) => !f || x.name.toLowerCase().includes(f) || (x.repo_id || '').toLowerCase().includes(f) || x.folder.toLowerCase().includes(f));
    const total = state.library.reduce((a, x) => a + x.size, 0);
    $('[data-lib-meta]').textContent = state.library.length ? `${state.library.length} files · ${gb(total)} · scanning ${state.settings.download_root}${state.settings.extra_roots.length ? ` + ${state.settings.extra_roots.length} more` : ''}` : '';
    const box = $('[data-lib]');
    if (!items.length) {
      box.innerHTML = `<div class="empty"><i class="ph-duotone ph-books"></i>${state.library.length ? 'Nothing matches the filter.' : `No models in ${esc(state.settings.download_root)} yet.`}</div>`;
      return;
    }
    box.innerHTML = `<div class="lrow lrow--head"><span>File</span><span>Quant</span><span style="text-align:right">Size</span><span>Source</span><span>Added</span><span></span></div>` +
      items.map((x, i) => `<div class="lrow enter" style="--i:${Math.min(i, 20)}" data-path="${esc(x.path)}">
        <span class="lrow__name" title="${esc(x.path)}">${esc(x.name)}<small>${esc(x.folder)}</small></span>
        <span>${x.mmproj ? '<span class="chip">mmproj</span>' : x.quant ? `<span class="chip chip--quant">${esc(x.quant)}</span>` : ''}</span>
        <span class="lrow__size">${gb(x.size)}</span>
        <span class="lrow__cell">${x.repo_id ? esc(x.repo_id) : '<span style="color:var(--text-dim)">found on disk</span>'}</span>
        <span class="lrow__cell">${rel(x.date)}</span>
        <span class="lrow__acts">
          <button type="button" class="iconbtn" data-act="folder" title="Show in folder"><i class="ph-duotone ph-folder-open"></i></button>
          <button type="button" class="iconbtn" data-act="copy" title="Copy path"><i class="ph-duotone ph-copy"></i></button>
          ${x.repo_id ? `<button type="button" class="iconbtn" data-act="repo" title="Open repo"><i class="ph-duotone ph-arrow-up-right"></i></button>` : ''}
          <button type="button" class="iconbtn btn--danger" data-act="delete" title="Move to Recycle Bin"><i class="ph-duotone ph-trash"></i></button>
        </span></div>`).join('');
    $$('[data-path]', box).forEach((row) => {
      const x = state.library.find((y) => y.path === row.dataset.path);
      $$('[data-act]', row).forEach((b) => b.addEventListener('click', async () => {
        const a = b.dataset.act;
        if (a === 'folder') call('open_folder', x.path);
        if (a === 'copy') { await call('copy', x.path); toast('Path copied.'); }
        if (a === 'repo') openRepo(x.repo_id);
        if (a === 'delete') {
          if (!(await confirmDialog('Move to Recycle Bin?', `${x.name} (${gb(x.size)}) will go to the Recycle Bin. You can restore it from there.`, 'Move to Recycle Bin'))) return;
          const r = await call('delete_file', x.path).catch((e) => ({ error: e.message }));
          if (r.ok) { toast(`Moved ${x.name} to the Recycle Bin.`, 'ok', 'ph-trash'); loadLibrary(); } else toast(`Could not delete: ${r.error || 'unknown error'}`, 'err');
        }
      }));
    });
  }

  // ── settings ─────────────────────────────────────────────────────────
  function renderSettings() {
    const s = state.settings;
    const pane = $('[data-pane="settings"]');
    pane.innerHTML = `
      <div class="viewhead"><h2 class="viewhead__title headline-silver" data-split>Settings</h2></div>
      <div class="settings">
        <div class="set"><div><div class="set__t">Download folder</div><div class="set__d">New downloads go to <span class="set__path">${esc(s.download_root)}\\&lt;model name&gt;</span>. The Library scans it too.</div></div>
          <div class="set__c"><button type="button" class="btn btn--ghost btn--sm" data-pick-root><i class="ph-duotone ph-folder-open"></i>Change</button></div></div>
        <div class="set"><div><div class="set__t">Extra library folders</div><div class="set__d">${s.extra_roots.length ? s.extra_roots.map((p) => `<span class="set__path">${esc(p)}</span> <button type="button" class="iconbtn" data-rm-root="${esc(p)}" title="Remove"><i class="ph-duotone ph-x"></i></button>`).join('<br>') : 'Other folders with models, for example LM Studio’s, to show in the Library.'}</div></div>
          <div class="set__c"><button type="button" class="btn btn--ghost btn--sm" data-add-root><i class="ph-duotone ph-plus"></i>Add</button></div></div>
        <div class="set"><div><div class="set__t">Parallel downloads</div><div class="set__d">Files downloading at the same time. One is usually fastest per file.</div></div>
          <div class="set__c"><div class="seg" data-conc>${[1, 2, 3].map((n) => `<button type="button" data-v="${n}">${n}</button>`).join('')}</div></div></div>
        <div class="set"><div><div class="set__t">Verify downloads</div><div class="set__d">Check every file against Hugging Face’s SHA-256 after downloading. Takes a few seconds per GB.</div></div>
          <div class="set__c"><label class="toggle"><input type="checkbox" data-verify ${s.verify ? 'checked' : ''}><span class="toggle__track"></span></label></div></div>
        <div class="set"><div><div class="set__t">Hugging Face account</div><div class="set__d">${state.user ? `Logged in as <span class="set__path">${esc(state.user)}</span>. Gated repos you have access to will download.` : 'Not logged in. Public models work; for gated ones run <code>hf auth login</code> in a terminal, then restart Capstan.'}</div></div><div></div></div>
        <div class="set"><div><div class="set__t">How the fit check works</div><div class="set__d">Capstan reads each model’s GGUF header from Hugging Face without downloading the file, then adds up weights, KV cache at your chosen context, and CUDA overhead. “Fits” keeps a 5% safety margin. It is an estimate: llama.cpp, LM Studio and Ollama differ slightly.</div></div><div></div></div>
      </div>
      <p class="about">CΛPSTΛN ${esc(state.version)} · by DΛЯK · The BlackWolf · data in ${esc(state.dataDir || '')}</p>`;
    splitAll(pane);
    const conc = $('[data-conc]', pane);
    markSeg(conc, String(s.concurrency));
    $$('button', conc).forEach((b) => b.addEventListener('click', async () => { state.settings = await call('settings', { concurrency: +b.dataset.v }); markSeg(conc, b.dataset.v); }));
    $('[data-verify]', pane).addEventListener('change', async (e) => { state.settings = await call('settings', { verify: e.target.checked }); });
    $('[data-pick-root]', pane).addEventListener('click', async () => {
      const p = await call('choose_folder', s.download_root).catch(() => null);
      if (p) { state.settings = await call('settings', { download_root: p }); renderSettings(); renderMachine(); }
    });
    $('[data-add-root]', pane).addEventListener('click', async () => {
      const p = await call('choose_folder').catch(() => null);
      if (p && !s.extra_roots.includes(p)) { state.settings = await call('settings', { extra_roots: [...s.extra_roots, p] }); renderSettings(); }
    });
    $$('[data-rm-root]', pane).forEach((b) => b.addEventListener('click', async () => {
      state.settings = await call('settings', { extra_roots: s.extra_roots.filter((p) => p !== b.dataset.rmRoot) }); renderSettings();
    }));
  }

  // ── events from Python ───────────────────────────────────────────────
  window.DP = {
    onEvent(ev) {
      if (ev.type === 'fonts') {
        // Satoshi just arrived from Fontshare: load it now instead of waiting for a restart.
        const t = Date.now();
        Promise.all(ev.weights.map((w) => new FontFace('Satoshi', `url(assets/fonts/Satoshi-${w}.woff2?${t})`, { weight: String(w) })
          .load().then((f) => document.fonts.add(f)).catch(() => {}))).then(() => document.body.classList.add('has-satoshi'));
      } else if (ev.type === 'window') {
        document.body.classList.toggle('is-maximized', !!ev.maximized);
      } else if (ev.type === 'queue') {
        state.jobs = ev.jobs;
        renderQueue();
        refreshRowStates();
      } else if (ev.type === 'downloaded') {
        state.libPaths.add(norm(ev.job.path));
        toast(`Downloaded ${ev.job.filename.split('/').pop()}`, 'ok', 'ph-check-circle');
        refreshRowStates();
        if (state.view === 'library') loadLibrary();
      }
    },
  };

  // ── wiring ───────────────────────────────────────────────────────────
  function wire() {
    splitAll();
    const setMax = (m) => { if (typeof m === 'boolean') document.body.classList.toggle('is-maximized', m); };
    $$('[data-win]').forEach((b) => b.addEventListener('click', async () => setMax(await call(b.dataset.win))));
    $('.titlebar').addEventListener('dblclick', async (e) => { if (!e.target.closest('.winctl')) setMax(await call('toggle_maximize')); });
    $('[data-drag]').addEventListener('mousedown', (e) => {
      if (e.button !== 0 || e.detail > 1 || e.target.closest('.winctl')) return;   // detail>1: let dblclick maximize
      e.preventDefault();
      call('begin_move', e.clientX / innerWidth);
    });
    $$('[data-grip]').forEach((g) => g.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      e.preventDefault();
      call('begin_resize', g.dataset.grip);
    }));
    $$('.rail__btn').forEach((b) => b.addEventListener('click', () => show(b.dataset.view)));

    const q = $('[data-q]');
    q.addEventListener('input', () => { state.q = q.value; if (state.view !== 'search') show('search'); searchSoon(); });
    q.addEventListener('paste', () => setTimeout(() => {
      const t = q.value.trim();
      if (looksLikeLink(t)) call('parse_link', t).then((l) => l?.repo_id && openRepo(l.repo_id, l.revision || null, l.file || null)).catch(() => {});
    }, 0));
    q.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const first = $('[data-results] [data-open]');
        if (looksLikeLink(q.value) || looksLikeRepo(q.value)) {
          if (first) first.click();
        } else if (first) first.click();
      }
      if (e.key === 'Escape') { q.value = ''; state.q = ''; runSearch(); }
    });
    const sort = $('[data-sort]');
    markSeg(sort, state.sort);
    $$('button', sort).forEach((b) => b.addEventListener('click', async () => {
      state.sort = b.dataset.v; markSeg(sort, state.sort);
      call('settings', { sort: state.sort }).then((s) => (state.settings = s)).catch(() => {});
      runSearch();
    }));
    const types = $('[data-type]');
    markSeg(types, state.typeFilter);
    $$('button', types).forEach((b) => b.addEventListener('click', () => {
      if (state.typeFilter === b.dataset.v) return;
      state.typeFilter = b.dataset.v; markSeg(types, state.typeFilter);
      call('settings', { type_filter: state.typeFilter }).then((s) => (state.settings = s)).catch(() => {});
      runSearch();
    }));
    const g = $('[data-gguf]');
    g.checked = state.gguf;
    g.addEventListener('change', () => { state.gguf = g.checked; call('settings', { gguf_only: g.checked }).catch(() => {}); runSearch(); });

    $('[data-clear-finished]').addEventListener('click', () => call('clear_finished'));
    $('[data-lib-refresh]').addEventListener('click', loadLibrary);
    $('[data-lib-filter]').addEventListener('input', (e) => { state.libFilter = e.target.value; renderLibrary(); });

    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); show('search'); q.focus(); q.select(); }
      if (e.key === 'Escape' && state.view === 'repo' && !$('[data-dialog]').open) back();
    });
  }

  async function boot() {
    const init = await call('init');
    state.settings = init.settings; state.machine = init.machine; state.jobs = init.queue;
    state.user = init.user; state.version = init.version; state.dataDir = init.data_dir;
    state.sort = init.settings.sort; state.gguf = init.settings.gguf_only;
    state.typeFilter = init.settings.type_filter || 'all';
    wire();
    renderMachine();
    renderQueue();
    runSearch();
    loadLibrary();
    setTimeout(pollMachine, 2000);
    show('search');
    $('[data-q]').focus();
    if (init.open) {                         // launched with --open <repo or link>
      const l = await call('parse_link', init.open).catch(() => null);
      if (l?.repo_id) openRepo(l.repo_id, l.revision || null, l.file || null);
    }
    if (['library', 'queue', 'settings'].includes(init.view)) show(init.view);   // --view <name>
  }

  if (window.pywebview?.api) boot();
  else window.addEventListener('pywebviewready', boot, { once: true });
})();
