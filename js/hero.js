// =============================================================================
// Animated CS-Pi loop. A 2D Avoidance toy: the policy wants to go start -> goal,
// a deployment-time obstacle blocks the straight path. CS-Pi draws a sample,
// projects the violation onto the feasible boundary, renoises to depth
// n = k/(k+delta), re-runs the flow, and converges. Loops forever; click to restart.
// =============================================================================
(function () {
  const canvas = document.getElementById('heroCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  // DOM HUD
  const elStage = document.getElementById('vizStage');
  const elDelta = document.getElementById('statDelta');
  const elN = document.getElementById('statN');
  const elIter = document.getElementById('statIter');

  // ---- scene (normalized world units; rendered with a uniform scale) -------
  const S = { x: 0.13, y: 0.50 };
  const G = { x: 0.87, y: 0.50 };
  const O = { x: 0.50, y: 0.50, r: 0.105 };   // obstacle
  const MARGIN = 0.03;                          // required clearance to be "safe"
  const K = 1.0;                                // CS-Pi hyperparameter (display)
  const TAU = 0.012;                            // feasibility threshold

  // control-point offset (perpendicular bow away from obstacle). Larger -> clears.
  // sample of Bezier S->P->G; deepest penetration into O defines delta.
  function bezier(t, P) {
    const u = 1 - t;
    return {
      x: u * u * S.x + 2 * u * t * P.x + t * t * G.x,
      y: u * u * S.y + 2 * u * t * P.y + t * t * G.y
    };
  }
  function controlPoint(offset) {
    // bow upward (decreasing y) from the straight-line midpoint
    const mid = { x: (S.x + G.x) / 2, y: (S.y + G.y) / 2 };
    return { x: mid.x + 0.02, y: mid.y - offset };
  }
  function penetration(offset) {
    const P = controlPoint(offset);
    let minD = Infinity, deep = null, deepT = 0;
    for (let i = 0; i <= 60; i++) {
      const t = i / 60, p = bezier(t, P);
      const d = Math.hypot(p.x - O.x, p.y - O.y);
      if (d < minD) { minD = d; deep = p; deepT = t; }
    }
    return { delta: Math.max(0, O.r + MARGIN - minD), deep, deepT, minD };
  }
  // feasible offset: grow until clear
  let OFFSET_FEAS = 0.0;
  for (let o = 0; o <= 0.6; o += 0.005) {
    if (penetration(o).delta <= TAU) { OFFSET_FEAS = o; break; }
  }
  const OFFSET_START = 0.0;     // straight through the obstacle
  const GAIN = 0.90;            // contraction per iteration (Phase-2-like): ~3 iters

  // stable noise pattern so the "denoising" settles instead of flickering
  const NPTS = 64;
  const noisePat = [];
  for (let i = 0; i < NPTS; i++) noisePat.push((Math.random() * 2 - 1));
  const noisePat2 = [];
  for (let i = 0; i < NPTS; i++) noisePat2.push((Math.random() * 2 - 1));

  // ---- state machine -------------------------------------------------------
  const PH = { DRAW: 'draw', EVAL: 'eval', PROJECT: 'project', RENOISE: 'renoise', DONE: 'done' };
  const DUR = { draw: 1300, eval: 700, project: 1100, renoise: 850, done: 1700 };
  let st;
  function reset() {
    st = {
      phase: PH.DRAW, t0: performance.now(), iter: 1,
      offset: OFFSET_START, projOffset: OFFSET_START,
      delta: penetration(OFFSET_START).delta, n: 0.0, denoiseFrom: 0.0
    };
    hud();
  }
  function nVal(delta) { return K / (K + delta * 6.0); } // scale delta so n ~ figure
  function ease(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

  function hud() {
    const stageNames = {
      draw: 'flow ODE  ·  draw clean sample â', eval: 'evaluate violation  δ',
      project: 'project   â → c  (nearest feasible)', renoise: 'renoise c to depth n',
      done: 'feasible ✓'
    };
    if (elStage) elStage.textContent = stageNames[st.phase] || '';
    hudStats();
    if (elIter) elIter.textContent = 'iter ' + st.iter;
  }
  function hudStats() {
    if (elDelta) elDelta.textContent = 'δ = ' + st.delta.toFixed(3);
    if (elN) elN.textContent = 'n = k/(k+δ) = ' + (st.delta > TAU ? nVal(st.delta).toFixed(2) : '—');
  }

  // ---- geometry helpers in pixels (uniform scale, circles stay circular) ---
  const VSPAN = 0.42;   // max vertical world-extent to keep on screen
  let W = 0, Hh = 0, BAR = 0, PADX = 0, areaY = 0, areaH = 0;
  let SCALE = 0, OX = 0, OY = 0;
  function layout() {
    const cssW = canvas.clientWidth || 900;
    const cssH = Math.round(cssW * 0.40);
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    canvas.width = Math.round(cssW * dpr);
    canvas.height = Math.round(cssH * dpr);
    canvas.style.height = cssH + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    W = cssW; Hh = cssH; BAR = 40; PADX = 26;
    areaY = BAR + 8; areaH = Hh - areaY - 14;
    const availW = W - 2 * PADX;
    SCALE = Math.min(availW, areaH / VSPAN);   // uniform; fit width or height
    OX = PADX + (availW - SCALE) / 2;           // center horizontally
    OY = areaY + areaH / 2;                      // O.y sits at vertical center
  }
  function px(p) { return { x: OX + p.x * SCALE, y: OY + (p.y - O.y) * SCALE }; }
  function pr(r) { return r * SCALE; }

  // ---- drawing -------------------------------------------------------------
  function drawNoiseBar(tNow) {
    // schedule strip: dark (t=0) -> light (t=1), marker at current denoise t
    const x0 = PADX, x1 = W - PADX, y = 18, h = 12;
    const grad = ctx.createLinearGradient(x0, 0, x1, 0);
    grad.addColorStop(0, '#0f3f86'); grad.addColorStop(1, '#dbe9fb');
    ctx.fillStyle = grad; roundRect(x0, y, x1 - x0, h, 6); ctx.fill();
    ctx.fillStyle = '#6b7c93'; ctx.font = '11px ui-monospace, monospace';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'left'; ctx.fillText('t=0  noise', x0, y - 8);
    ctx.textAlign = 'right'; ctx.fillText('clean  t=1', x1, y - 8);
    // marker
    let tm = tNow;
    const mx = x0 + tm * (x1 - x0);
    ctx.fillStyle = '#14233a';
    ctx.beginPath(); ctx.moveTo(mx, y - 3); ctx.lineTo(mx - 5, y - 11); ctx.lineTo(mx + 5, y - 11); ctx.closePath(); ctx.fill();
    ctx.fillRect(mx - 1.5, y, 3, h);
    ctx.textAlign = 'center'; ctx.fillStyle = '#fff';
    if (st.phase === PH.RENOISE) { ctx.fillStyle = '#14233a'; ctx.textAlign = 'center'; ctx.fillText('renoise → n', mx, y + h + 9); }
  }
  function drawScene() {
    // start
    const s = px(S), g = px(G), o = px(O);
    // goal ring
    ctx.strokeStyle = '#1f9d57'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(g.x, g.y, 13, 0, 7); ctx.stroke();
    ctx.fillStyle = '#1f9d57'; ctx.beginPath(); ctx.arc(g.x, g.y, 4, 0, 7); ctx.fill();
    ctx.fillStyle = '#137a3d'; ctx.font = '600 12px var(--sans), sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'; ctx.fillText('goal', g.x, g.y - 16);
    // obstacle
    ctx.fillStyle = 'rgba(224,83,61,.13)'; ctx.strokeStyle = '#e0533d'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(o.x, o.y, pr(O.r), 0, 7); ctx.fill(); ctx.stroke();
    ctx.setLineDash([4, 4]); ctx.strokeStyle = 'rgba(224,83,61,.4)';
    ctx.beginPath(); ctx.arc(o.x, o.y, pr(O.r + MARGIN), 0, 7); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = '#c0392b'; ctx.textBaseline = 'middle'; ctx.fillText('obstacle', o.x, o.y);
    // start
    ctx.fillStyle = '#14233a'; ctx.beginPath(); ctx.arc(s.x, s.y, 5, 0, 7); ctx.fill();
    ctx.textBaseline = 'top'; ctx.fillText('start', s.x, s.y + 8);
  }
  function pathPoints(offset, denoise) {
    // denoise in [0,1]: 0 = full noise amplitude, 1 = clean
    const P = controlPoint(offset);
    const amp = (1 - denoise) * 0.085;
    const pts = [];
    for (let i = 0; i <= NPTS; i++) {
      const t = i / NPTS;
      const b = bezier(t, P);
      // perpendicular direction
      const t2 = Math.min(1, t + 0.01), b2 = bezier(t2, P);
      let dx = b2.x - b.x, dy = b2.y - b.y; const L = Math.hypot(dx, dy) || 1;
      const nx = -dy / L, ny = dx / L;
      const env = Math.sin(Math.PI * t); // 0 at ends, 1 mid -> sample anchored at S,G
      const k = i % NPTS;
      const jitter = amp * env * (0.7 * noisePat[k] + 0.3 * noisePat2[k]);
      pts.push({ x: b.x + nx * jitter, y: b.y + ny * jitter });
    }
    return pts;
  }
  function strokePath(pts, color, width, alpha) {
    ctx.globalAlpha = alpha == null ? 1 : alpha;
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    ctx.beginPath();
    pts.forEach((p, i) => { const q = px(p); i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y); });
    ctx.stroke(); ctx.globalAlpha = 1;
  }
  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  // Draw the projection residual for a given display offset: the deepest path
  // point, the nearest feasible point c on the (inflated) boundary, and the gap δ.
  function drawProjection(off, opts) {
    const pen = penetration(off);
    if (!pen.deep) return;
    const deep = px(pen.deep);
    // project straight up to the (inflated) boundary: the feasible side the bow uses
    const R = O.r + MARGIN, dxc = pen.deep.x - O.x;
    const cN = (Math.abs(dxc) < R)
      ? { x: pen.deep.x, y: O.y - Math.sqrt(R * R - dxc * dxc) }
      : { x: O.x + Math.sign(dxc) * R, y: O.y };
    const c = px(cN);
    if (pen.delta > TAU) {
      ctx.strokeStyle = '#1d6fd4'; ctx.lineWidth = 2; ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(deep.x, deep.y); ctx.lineTo(c.x, c.y); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = '#c0392b'; ctx.beginPath(); ctx.arc(deep.x, deep.y, 4, 0, 7); ctx.fill();
    }
    ctx.fillStyle = '#1d6fd4'; ctx.beginPath(); ctx.arc(c.x, c.y, 5, 0, 7); ctx.fill();
    ctx.font = '600 12px ui-monospace, monospace'; ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
    if (opts.delta && pen.delta > TAU) {
      ctx.fillStyle = '#c0392b';
      ctx.fillText('δ', (deep.x + c.x) / 2 + 6, (deep.y + c.y) / 2);
    }
    ctx.fillStyle = '#1d6fd4'; ctx.fillText('c', c.x + 8, c.y + 2);
    if (opts.label) {
      ctx.fillStyle = '#1d6fd4'; ctx.font = '700 12.5px var(--sans), sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'bottom';
      ctx.fillText('project  â → c', c.x, Math.min(deep.y, c.y) - 12);
    }
  }
  function drawCheck() {
    const g = px(G);
    ctx.strokeStyle = '#1f9d57'; ctx.lineWidth = 4; ctx.lineCap = 'round';
    const cx = g.x + 26, cy = g.y - 26;
    ctx.beginPath(); ctx.moveTo(cx - 8, cy); ctx.lineTo(cx - 2, cy + 7); ctx.lineTo(cx + 10, cy - 9); ctx.stroke();
  }

  // ---- main loop -----------------------------------------------------------
  function frame(now) {
    const e = now - st.t0; const dur = DUR[st.phase]; const prog = Math.min(1, e / dur);
    layoutIfNeeded();
    ctx.clearRect(0, 0, W, Hh);

    // Per phase: which path offset to display, how denoised, where the noise
    // marker sits. Project happens at t=1 (clean), distinct from renoise.
    let off = st.offset, denoise = 1, barT = 1;
    if (st.phase === PH.DRAW) {
      off = st.offset; denoise = st.denoiseFrom + (1 - st.denoiseFrom) * prog; barT = denoise;
    } else if (st.phase === PH.EVAL) {
      off = st.offset; denoise = 1; barT = 1;
    } else if (st.phase === PH.PROJECT) {
      // morph the clean sample onto the feasible set: â -> c
      off = st.offset + (OFFSET_FEAS - st.offset) * ease(prog); denoise = 1; barT = 1;
    } else if (st.phase === PH.RENOISE) {
      // renoise the projected (feasible) path c back to depth n
      off = OFFSET_FEAS; denoise = 1 - prog * (1 - st.n); barT = st.n + (1 - st.n) * (1 - prog);
    } else if (st.phase === PH.DONE) {
      off = st.offset; denoise = 1; barT = 1;
    }

    drawNoiseBar(barT);
    drawScene();

    const feasibleNow = penetration(off).delta <= TAU;
    const pathColor = (st.phase === PH.DONE || feasibleNow) ? '#1f9d57' : '#1d6fd4';
    strokePath(pathPoints(off, denoise), pathColor, 3.2, 1);

    if (st.phase === PH.EVAL) drawProjection(off, { delta: true });
    else if (st.phase === PH.PROJECT) drawProjection(off, { delta: true, label: true });
    else if (st.phase === PH.RENOISE) drawProjection(off, {});
    else if (st.phase === PH.DONE) drawCheck();

    st.delta = penetration(off).delta;
    if (st.phase !== PH.DONE) hudStats();   // live δ / n as the sample morphs
    if (prog >= 1) advance();
    requestAnimationFrame(frame);
  }

  function advance() {
    switch (st.phase) {
      case PH.DRAW: {
        const feasible = penetration(st.offset).delta <= TAU;
        go(feasible ? PH.DONE : PH.EVAL);
        break;
      }
      case PH.EVAL: {
        // renoise depth from the violation; the re-run lands partway to feasible
        st.n = nVal(penetration(st.offset).delta);
        st.projOffset = st.offset + (OFFSET_FEAS - st.offset) * GAIN;
        go(PH.PROJECT);
        break;
      }
      case PH.PROJECT: go(PH.RENOISE); break;
      case PH.RENOISE: {
        st.offset = st.projOffset;          // re-run from the renoised projection
        st.iter += 1; st.denoiseFrom = st.n;
        go(PH.DRAW);
        break;
      }
      case PH.DONE: reset(); break;
    }
  }
  function go(phase) { st.phase = phase; st.t0 = performance.now(); hud(); }

  let lastW = -1;
  function layoutIfNeeded() { if (canvas.clientWidth !== lastW) { lastW = canvas.clientWidth; layout(); } }

  canvas.addEventListener('click', reset);
  window.addEventListener('resize', () => { lastW = -1; });
  layout(); reset(); requestAnimationFrame(frame);
})();
