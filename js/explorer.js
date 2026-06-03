// =============================================================================
// Builds every dynamic section from data.js + gif_manifest.js.
// GIFs are lazy: a cell's GIF loads only when selected; the face-off loads only
// once it scrolls into view. Posters (still first frames) show meanwhile.
// =============================================================================
(function () {
  const M = window.GIF_MANIFEST || {};
  const METHODS = window.METHODS;
  const byKey = Object.fromEntries(METHODS.map(m => [m.key, m]));
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, cls, html) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  };

  // -------------------------------------------------------------------------
  function cell(task, scen, method) { return ((M[task] || {})[scen] || {})[method] || {}; }

  function absenceReason(method, outcome) {
    if (method === 'amr' && outcome === 'fail')
      return 'CS-Pi is collision-free on all five scenarios, so no failure rollout exists.';
    if (outcome === 'success')
      return 'This method scores 0% safe-success in this scenario, so there is no successful rollout to show.';
    return 'This method is safe on every trial in this scenario, so there is no failure rollout to show.';
  }
  const OUTCOME_CAPTION = {
    success: 'Safe and successful: collision-free, the gripper picks the cube and places it.',
    fail: 'Failure: a collision, or the gripper clears the obstacle but loses the cube.'
  };

  // ---- header --------------------------------------------------------------
  function header() {
    const s = window.SITE;
    $('#brand').textContent = s.method;
    $('#heroBadge').textContent = s.affiliation;
    $('#heroTitle').innerHTML = csName(s.title);
    $('#heroSub').textContent = 'Training-free sampling of safe, in-distribution actions';
    $('#heroAuthors').textContent = s.authors;
    $('#heroAffil').textContent = s.affiliation;
    $('#heroTagline').textContent = s.tagline;
    const row = $('#btnrow');
    const L = s.links;
    const mk = (href, label, primary, icon) => {
      if (!href) return;
      const a = el('a', 'btn' + (primary ? ' primary' : ''));
      a.href = href; a.innerHTML = (icon || '') + label;
      if (/^https?:/.test(href)) { a.target = '_blank'; a.rel = 'noopener'; }
      row.appendChild(a);
    };
    mk(L.paper, 'Paper', true, ICON.doc);
    mk(L.pdf, 'PDF', false, ICON.doc);
    mk(L.code, 'Code', false, ICON.code);
    mk('#explorer', 'Explore rollouts', !L.paper, ICON.play);
    mk(L.bibtex, 'BibTeX', false, ICON.quote);
  }
  function csName(t) { return t.replace(/CS-Pi/g, '<span class="cs">CS-Pi</span>'); }

  // ---- headline stats ------------------------------------------------------
  function headline() {
    const g = $('#statStrip');
    window.HEADLINE.forEach(h => {
      const c = el('div', 'stat-card');
      c.innerHTML = `<div class="big">${h.big}</div><div class="small">${h.small}</div><div class="sub">${h.sub}</div>`;
      g.appendChild(c);
    });
  }

  // ---- method cards --------------------------------------------------------
  function methodCards() {
    const g = $('#methodGrid');
    METHODS.forEach(m => {
      const c = el('div', 'mcard');
      c.style.setProperty('--c', m.color);
      c.innerHTML =
        `<h3>${m.label}${m.ours ? ' <span class="tag">ours</span>' : ''}</h3><p>${m.blurb}</p>`;
      g.appendChild(c);
    });
  }

  // ---- lazy media element --------------------------------------------------
  // Shows poster; loads gif when load() called. Returns {node, load, showEmpty}.
  function makeMedia(extraClass) {
    const wrap = el('div', 'viewer ' + (extraClass || ''));
    const img = el('img');
    img.alt = 'rollout';
    wrap.appendChild(img);
    let curGif = null;
    function show(entry, outcomeLabel) {
      wrap.classList.remove('hidden');
      wrap.innerHTML = '';
      const im = el('img'); im.alt = 'rollout';
      if (entry.poster) { im.src = entry.poster; }          // instant still
      wrap.appendChild(im);
      if (outcomeLabel) {
        const b = el('div', 'badge-outcome');
        b.innerHTML = outcomeLabel === 'success'
          ? '<span class="pill ok">safe ✓</span>'
          : '<span class="pill bad">fail ✗</span>';
        wrap.appendChild(b);
      }
      // load gif on top of poster
      curGif = entry.gif;
      const g = new Image();
      g.onload = () => { if (curGif === entry.gif) im.src = entry.gif; };
      g.src = entry.gif;
    }
    function empty(reason) {
      wrap.innerHTML = `<div class="empty-cell">${ICON.noFilm}<div>No rollout for this cell</div><div class="why">${reason}</div></div>`;
    }
    return { node: wrap, show, empty };
  }

  // ---- face-off ------------------------------------------------------------
  function faceoff() {
    const task = 'shelf';
    const scens = window.TASKS.find(t => t.key === task).scenarios
      .filter(s => cell(task, s.key, 'amr').success);   // need an amr success
    const left = makeMedia(), right = makeMedia();
    $('#foLeftMedia').appendChild(left.node);
    $('#foRightMedia').appendChild(right.node);
    const dots = $('#foDots');
    let idx = 0, timer = null, visible = false;

    function baselineFail(scenKey) {
      for (const mk of ['tweedie', 'trust', 'projection']) {
        const c = cell(task, scenKey, mk);
        if (c.fail) return { method: mk, entry: c.fail };
      }
      return null;
    }
    function render() {
      const scen = scens[idx];
      const amr = cell(task, scen.key, 'amr').success;
      const base = baselineFail(scen.key);
      $('#foScen').textContent = scen.label;
      left.show(amr, 'success');
      $('#foLeftName').textContent = 'CS-Pi (ours)';
      if (base) {
        right.show(base.entry, 'fail');
        $('#foRightName').textContent = byKey[base.method].label;
      }
      [...dots.children].forEach((d, i) => d.setAttribute('aria-selected', i === idx));
    }
    scens.forEach((s, i) => {
      const d = el('button', 'tabbtn'); d.textContent = s.label;
      d.onclick = () => { idx = i; render(); restart(); };
      dots.appendChild(d);
    });
    function next() { idx = (idx + 1) % scens.length; render(); }
    function restart() { if (timer) clearInterval(timer); if (visible) timer = setInterval(next, 5200); }
    render();
    // only run while visible
    new IntersectionObserver((es) => {
      es.forEach(e => { visible = e.isIntersecting; restart(); if (!visible && timer) { clearInterval(timer); timer = null; } });
    }, { threshold: 0.15 }).observe($('#faceoff'));
  }

  // ---- explorer ------------------------------------------------------------
  const state = { task: 'shelf', scen: null, method: 'amr', outcome: 'success' };
  let viewer;

  function explorer() {
    // task tabs
    const tabs = $('#expTasks');
    window.TASKS.forEach(t => {
      const b = el('button', 'tabbtn');
      b.innerHTML = t.label + (t.available ? '' : ' <span class="soon">soon</span>');
      b.disabled = !t.available;
      b.setAttribute('aria-selected', t.key === state.task);
      b.onclick = () => { state.task = t.key; selectTask(); };
      tabs.appendChild(b);
    });
    viewer = makeMedia();
    $('#expViewer').appendChild(viewer.node);
    // outcome toggle (only used by success/fail tasks)
    $('#outSuccess').onclick = () => { if (hasOutcome('success')) { state.outcome = 'success'; paint(); } };
    $('#outFail').onclick = () => { if (hasOutcome('fail')) { state.outcome = 'fail'; paint(); } };
    // deep-link: ?task=3dorient preselects an available task
    const qp = new URLSearchParams(location.search);
    const wantT = qp.get('task') && window.TASKS.find(x => x.key === qp.get('task') && x.available);
    if (wantT) state.task = wantT.key;
    selectTask();
    const wantS = qp.get('scen') && curTask().scenarios.find(s => s.key === qp.get('scen'));
    if (wantS) { state.scen = wantS.key; pickDefaultOutcome(); paint(); }
  }

  function curTask() { return window.TASKS.find(t => t.key === state.task); }

  function buildMethods(t) {
    const mrow = $('#expMethods'); mrow.innerHTML = '';
    (t.methods || []).forEach(key => {
      const m = byKey[key]; if (!m) return;
      const b = el('button', 'mbtn');
      b.style.setProperty('--mc', m.color);
      b.innerHTML = `<span class="swatch" style="background:${m.color}"></span>${m.label}${m.ours ? ' (ours)' : ''}`;
      b.dataset.method = key;
      b.onclick = () => { state.method = key; pickDefaultOutcome(); paint(); };
      mrow.appendChild(b);
    });
  }

  function selectTask() {
    const t = curTask();
    [...$('#expTasks').children].forEach(b =>
      b.setAttribute('aria-selected', b.textContent.startsWith(t.label)));
    $('#expTaskBlurb').textContent = t.blurb;
    if (!(t.methods || []).includes(state.method)) state.method = (t.methods || ['amr'])[0];
    state.scen = t.scenarios[0] ? t.scenarios[0].key : null;
    buildMethods(t);
    buildScenList(t);
    pickDefaultOutcome(); paint();
  }

  function buildScenList(t) {
    const ul = $('#scenList'); ul.innerHTML = '';
    t.scenarios.forEach(s => {
      const thumb = (anyEntry(t.key, s.key, 'amr') || {}).poster
        || firstPoster(t.key, s.key);
      const li = el('button', 'scen-item');
      li.setAttribute('aria-selected', s.key === state.scen);
      li.innerHTML =
        `${thumb ? `<img src="${thumb}" alt="">` : '<div class="img"></div>'}` +
        `<div class="meta"><div class="name">${s.label}</div><div class="desc">${s.desc}</div></div>`;
      li.onclick = () => { state.scen = s.key; pickDefaultOutcome(); paint(); };
      ul.appendChild(li);
    });
  }
  function firstPoster(task, scen) {
    const c = (M[task] || {})[scen] || {};
    for (const m of Object.values(c)) for (const o of Object.values(m)) if (o.poster) return o.poster;
    return null;
  }
  function anyEntry(task, scen, method) {
    const c = cell(task, scen, method);
    return c.success || c.rollout || c.fail || Object.values(c)[0] || null;
  }

  function hasOutcome(o) { return !!cell(state.task, state.scen, state.method)[o]; }
  function pickDefaultOutcome() {
    if (!curTask().outcomes) { state.outcome = 'rollout'; return; }
    if (hasOutcome('success')) state.outcome = 'success';
    else if (hasOutcome('fail')) state.outcome = 'fail';
    else state.outcome = 'success'; // none -> will show empty
  }

  function paint() {
    const t = curTask();
    const m = byKey[state.method];
    // method buttons
    [...$('#expMethods').children].forEach(b =>
      b.setAttribute('aria-selected', b.dataset.method === state.method));
    // scenario list selection
    [...$('#scenList').children].forEach((b, i) =>
      b.setAttribute('aria-selected', t.scenarios[i] && t.scenarios[i].key === state.scen));
    // header
    $('#stageWho').innerHTML = `<span class="swatch" style="display:inline-block;width:11px;height:11px;border-radius:3px;background:${m.color};margin-right:8px"></span>${m.label}${m.ours ? ' · ours' : ''}`;
    // outcome toggle: shown only for success/fail tasks
    const toggle = $('#outcomeToggle');
    if (t.outcomes) {
      toggle.classList.remove('hidden');
      const oS = $('#outSuccess'), oF = $('#outFail');
      oS.disabled = !hasOutcome('success'); oF.disabled = !hasOutcome('fail');
      oS.setAttribute('aria-selected', state.outcome === 'success');
      oF.setAttribute('aria-selected', state.outcome === 'fail');
    } else {
      toggle.classList.add('hidden');
    }
    // viewer (no safe/fail pill for single-rollout tasks)
    const entry = cell(state.task, state.scen, state.method)[state.outcome];
    if (entry) viewer.show(entry, t.outcomes ? state.outcome : null);
    else viewer.empty(absenceReason(state.method, state.outcome));
    // note: caption + optional scenario note + method blurb
    const scen = t.scenarios.find(s => s.key === state.scen) || {};
    let cap;
    if (!entry) cap = absenceReason(state.method, state.outcome);
    else cap = t.outcomes ? OUTCOME_CAPTION[state.outcome] : (t.rolloutCaption || '');
    let html = `<span class="interp">${cap}</span>`;
    if (scen.note) html += `<span class="scennote">${scen.note}</span>`;
    if (m.blurb) html += `<br>${m.blurb}`;
    $('#stageNote').innerHTML = html;
  }

  // ---- results tables ------------------------------------------------------
  function results() {
    const order = [['hw', 'Hardware'], ['shelf', 'Shelf'], ['d3il', '2D Avoidance'], ['orient', '3D-Orient']];
    const tabs = $('#resTabs'), host = $('#resTable');
    let cur = 'hw';
    function draw() {
      const r = window.RESULTS[cur]; host.innerHTML = '';
      const card = el('div', 'tablecard');
      const head = el('div', 'thead'); head.innerHTML = `<h3>${r.title}</h3>`;
      card.appendChild(head);
      const scroll = el('div', 'tablescroll');
      const tbl = el('table', 'results');
      const thead = el('thead');
      thead.innerHTML = '<tr>' + r.cols.map(c => `<th>${c}</th>`).join('') + '</tr>';
      tbl.appendChild(thead);
      const tb = el('tbody');
      r.rows.forEach(row => {
        const tr = el('tr', row.ours ? 'ours' : '');
        row.c.forEach((v, i) => {
          const td = el('td', (row.best && row.best.includes(i)) ? 'best' : '');
          td.textContent = v; tr.appendChild(td);
        });
        tb.appendChild(tr);
      });
      tbl.appendChild(tb); scroll.appendChild(tbl); card.appendChild(scroll);
      card.appendChild(el('div', 'tcap', r.caption));
      host.appendChild(card);
      [...tabs.children].forEach(b => b.setAttribute('aria-selected', b.dataset.k === cur));
    }
    order.forEach(([k, lbl]) => {
      const b = el('button', 'tabbtn'); b.textContent = lbl; b.dataset.k = k;
      b.onclick = () => { cur = k; draw(); }; tabs.appendChild(b);
    });
    draw();
  }

  // ---- hardware videos (4x speed, lazy autoplay) ---------------------------
  function hardwareVideos() {
    const host = $('#hwVideos'); if (!host) return;
    const vids = [
      { src: 'assets/hardware/cspi_success_0.mp4', poster: 'assets/hardware/cspi_success_0.jpg',
        method: 'CS-Pi (ours)', cls: 'ours', pill: 'ok', tag: 'safe ✓', note: 'picks the apple and places it on the plate' },
      { src: 'assets/hardware/trust_fail.mp4', poster: 'assets/hardware/trust_fail.jpg',
        method: 'Trust Sampling', cls: 'base', pill: 'bad', tag: 'fail ✗', note: 'fails the task' },
      { src: 'assets/hardware/gradient_guidance.mp4', poster: 'assets/hardware/gradient_guidance.jpg',
        method: 'Gradient Guidance', cls: 'base', pill: 'bad', tag: 'fail ✗', note: 'fails the task' },
      { src: 'assets/hardware/project_fail.mp4', poster: 'assets/hardware/project_fail.jpg',
        method: 'Projection', cls: 'base', pill: 'bad', tag: 'fail ✗', note: 'fails the task' }
    ];
    const io = new IntersectionObserver((es) => {
      es.forEach(e => {
        const v = e.target;
        if (e.isIntersecting) { if (!v.src) v.src = v.dataset.src; v.play().catch(() => {}); }
        else { v.pause(); }
      });
    }, { threshold: 0.25 });
    vids.forEach(d => {
      const card = el('div', 'hw-vidcard ' + d.cls);
      const head = el('div', 'hw-vidhead');
      head.innerHTML = `<span class="name">${d.method}</span>` +
        (d.tag ? `<span class="pill ${d.pill}">${d.tag}</span>` : '') +
        `<span class="speed-badge">4×</span>`;
      card.appendChild(head);
      const media = el('div', 'hw-media');
      const v = document.createElement('video');
      v.muted = true; v.loop = true; v.playsInline = true; v.setAttribute('playsinline', '');
      v.preload = 'none'; v.poster = d.poster; v.dataset.src = d.src;
      v.controls = true;
      media.appendChild(v); card.appendChild(media);
      if (d.note) card.appendChild(el('div', 'hw-vidnote', d.note + ' · 4× speed'));
      host.appendChild(card);
      io.observe(v);
    });
  }

  // ---- hardware strips -----------------------------------------------------
  function hardware() {
    const host = $('#hwStrips');
    const strips = [
      { src: 'assets/hw_v1_succ.png', cls: 'ours', lbl: 'Layout 1 — CS-Pi', tag: 'safe ✓', pill: 'ok' },
      { src: 'assets/hw_v1_fail.png', cls: 'base', lbl: 'Layout 1 — unguided π₀.₅', tag: 'fail ✗', pill: 'bad' },
      { src: 'assets/hw_v2_succ.png', cls: 'ours', lbl: 'Layout 2 — CS-Pi', tag: 'safe ✓', pill: 'ok' },
      { src: 'assets/hw_v2_fail.png', cls: 'base', lbl: 'Layout 2 — unguided π₀.₅', tag: 'fail ✗', pill: 'bad' }
    ];
    strips.forEach(s => {
      const c = el('div', 'stripcard ' + s.cls);
      c.innerHTML = `<div class="lbl">${s.lbl} <span class="pill ${s.pill}">${s.tag}</span></div>`;
      const img = el('img'); img.loading = 'lazy'; img.src = s.src; img.alt = s.lbl;
      c.appendChild(img); host.appendChild(c);
    });
  }

  // ---- bibtex --------------------------------------------------------------
  function bibtex() {
    const bib = `@inproceedings{cspi2026,
  title     = {CS-Pi: Constraint-Satisfying Flow Policy Sampling},
  author    = {Anonymous Authors},
  booktitle = {Conference on Robot Learning (CoRL)},
  year      = {2026}
}`;
    $('#bibBlock').textContent = bib;
    $('#copyBib').onclick = () => {
      navigator.clipboard.writeText(bib).then(() => {
        $('#copyBib').textContent = 'Copied ✓';
        setTimeout(() => ($('#copyBib').textContent = 'Copy BibTeX'), 1600);
      });
    };
  }

  // ---- icons ---------------------------------------------------------------
  const ICON = {
    doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>',
    code: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 18l6-6-6-6M8 6l-6 6 6 6"/></svg>',
    play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>',
    quote: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 17h3l2-4V7H5v6h2zM14 17h3l2-4V7h-6v6h2z"/></svg>',
    noFilm: '<svg viewBox="0 0 24 24" width="38" height="38" fill="none" stroke="currentColor" stroke-width="1.6" style="opacity:.6"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M7 4v16M17 4v16M2 9h5M2 15h5M17 9h5M17 15h5"/></svg>'
  };

  // ---- go ------------------------------------------------------------------
  function theme() {
    const btn = $('#themeToggle'); if (!btn) return;
    const cur = () => document.documentElement.getAttribute('data-theme') || 'light';
    const paint = () => { btn.textContent = cur() === 'dark' ? '☀' : '☾'; };
    paint();
    btn.onclick = () => {
      const next = cur() === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      paint();
    };
  }

  document.addEventListener('DOMContentLoaded', () => {
    header(); headline(); methodCards(); faceoff(); explorer(); results();
    hardwareVideos(); hardware(); bibtex(); theme();
    // smooth-scroll active nav handled by browser; reveal year
    $('#year').textContent = '2026';
  });
})();
