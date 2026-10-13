// =============================================================================
// Animated CS-Pi loop. A 2D Avoidance toy: the policy wants to go start -> goal,
// a deployment-time obstacle blocks the straight path. CS-Pi draws a sample,
// projects it pointwise onto the feasible set (the violating stretch is lifted
// onto the obstacle boundary, so c hugs the constraint), renoises to depth
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

  const R = O.r + MARGIN;                       // inflated (feasible) boundary
  const NPTS = 64;

  function bezier(t, P) {
    const u = 1 - t;
    return {
      x: u * u * S.x + 2 * u * t * P.x + t * t * G.x,
      y: u * u * S.y + 2 * u * t * P.y + t * t * G.y
    };
  }
  // the policy's preferred sample: a near-straight line through the obstacle
  const CP = { x: (S.x + G.x) / 2 + 0.02, y: (S.y + G.y) / 2 };
  const BASE = [];
  for (let i = 0; i <= NPTS; i++) BASE.push(bezier(i / NPTS, CP));

  // y of the feasible boundary directly above p (p.y if p is already feasible)
  function liftY(p) {
    const dx = p.x - O.x;
    if (Math.abs(dx) >= R) return p.y;
    const h = Math.sqrt(R * R - dx * dx);
    return (p.y > O.y - h && p.y < O.y + h) ? O.y - h : p.y;
  }
  // pointwise projection onto the feasible set: violating points land on the
  // boundary, the rest stay put, so the projected path hugs the constraint
  function project(pts) { return pts.map(p => ({ x: p.x, y: liftY(p) })); }

  function violation(pts) {
    let minD = Infinity, deep = pts[0];
    for (const p of pts) {
      const d = Math.hypot(p.x - O.x, p.y - O.y);
      if (d < minD) { minD = d; deep = p; }
    }
    return { delta: Math.max(0, R - minD), deep };
  }

  // What the re-run flow lands on: the base sample pulled toward the projection.
  // LIFT is a locally relaxed envelope of the required lift (relax toward the
  // neighbour average, never below the requirement): it follows the arc and
  // only rounds the shoulders where the path meets the boundary. LIFT >= need,
  // so h=1 is feasible and the converged path hugs the constraint.
  const need = BASE.map(p => p.y - liftY(p));
  let LIFT = need.slice();
  for (let it = 0; it < 40; it++) {
    const next = LIFT.slice();
    for (let i = 1; i < NPTS; i++) next[i] = Math.max(need[i], 0.5 * (LIFT[i - 1] + LIFT[i + 1]));
    LIFT = next;
  }
  function sampleAt(h) { return BASE.map((p, i) => ({ x: p.x, y: p.y - h * LIFT[i] })); }
  function lerpPts(a, b, k) { return a.map((p, i) => ({ x: p.x + (b[i].x - p.x) * k, y: p.y + (b[i].y - p.y) * k })); }

  const RHO = 0.20;             // residual kept per re-run (Phase-2-like): ~3 iters

  // stable noise pattern so the "denoising" settles instead of flickering
  const noisePat = [];
  for (let i = 0; i <= NPTS; i++) noisePat.push((Math.random() * 2 - 1));
  const noisePat2 = [];
  for (let i = 0; i <= NPTS; i++) noisePat2.push((Math.random() * 2 - 1));

  // ---- state machine -------------------------------------------------------
  const PH = { DRAW: 'draw', EVAL: 'eval', PROJECT: 'project', RENOISE: 'renoise', DONE: 'done' };
  const DUR = { draw: 1300, eval: 700, project: 1100, renoise: 850, done: 1700 };
  let st;
  function reset() {
    st = {
      phase: PH.DRAW, t0: performance.now(), iter: 1,
      h: 0.0, from: null,
      delta: violation(sampleAt(0)).delta, n: 0.0, denoiseFrom: 0.0
    };
    hud();
  }
  function nVal(delta) { return K / (K + delta * 6.0); } // scale delta so n ~ figure
  function ease(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }

  function hud() {
    const stageNames = {
      draw: 'flow ODE  ·  draw clean sample â', eval: 'evaluate violation  δ',
      project: 'project   â → c  (onto the constraint)', renoise: 'renoise c to depth n',
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
  function noisy(pts, denoise) {
    // denoise in [0,1]: 0 = full noise amplitude, 1 = clean
    const amp = (1 - denoise) * 0.085;
    if (amp <= 0) return pts;
    return pts.map((p, i) => {
      const q = pts[Math.min(NPTS, i + 1)], r = pts[Math.max(0, i - 1)];
      let dx = q.x - r.x, dy = q.y - r.y; const L = Math.hypot(dx, dy) || 1;
      const env = Math.sin(Math.PI * i / NPTS); // 0 at ends -> sample anchored at S,G
      const jitter = amp * env * (0.7 * noisePat[i] + 0.3 * noisePat2[i]);
      return { x: p.x - dy / L * jitter, y: p.y + dx / L * jitter };
    });
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

  // Draw the projection residual for a clean path: the deepest path point, the
  // feasible point c directly above it on the (inflated) boundary, and the gap δ.
  function drawProjection(pts, opts) {
    const v = violation(pts);
    const cN = { x: v.deep.x, y: liftY(v.deep) };
    const deep = px(v.deep), c = px(cN);
    if (v.delta > TAU) {
      ctx.strokeStyle = '#1d6fd4'; ctx.lineWidth = 2; ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(deep.x, deep.y); ctx.lineTo(c.x, c.y); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = '#c0392b'; ctx.beginPath(); ctx.arc(deep.x, deep.y, 4, 0, 7); ctx.fill();
    }
    ctx.fillStyle = '#1d6fd4'; ctx.beginPath(); ctx.arc(c.x, c.y, 5, 0, 7); ctx.fill();
    ctx.font = '600 12px ui-monospace, monospace'; ctx.textAlign = 'left'; ctx.textBaseline = 'bottom';
    if (opts.delta && v.delta > TAU) {
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

    // Per phase: which clean path to show, how denoised, where the noise marker
    // sits. Project happens at t=1 (clean), distinct from renoise.
    const a = sampleAt(st.h);
    let clean = a, denoise = 1, barT = 1;
    if (st.phase === PH.DRAW) {
      denoise = st.denoiseFrom + (1 - st.denoiseFrom) * prog; barT = denoise;
      if (st.from) clean = lerpPts(st.from, a, ease(prog));   // re-run starts from renoised c
    } else if (st.phase === PH.PROJECT) {
      // move each violating point onto the boundary: â -> c hugs the obstacle
      clean = lerpPts(a, project(a), ease(prog));
    } else if (st.phase === PH.RENOISE) {
      // renoise the projected (feasible) path c back to depth n
      clean = project(a); denoise = 1 - prog * (1 - st.n); barT = st.n + (1 - st.n) * (1 - prog);
    }

    drawNoiseBar(barT);
    drawScene();

    if (st.phase === PH.PROJECT) strokePath(a, '#1d6fd4', 2, 0.25);   // ghost of â
    const feasibleNow = violation(clean).delta <= TAU;
    const pathColor = (st.phase === PH.DONE || feasibleNow) ? '#1f9d57' : '#1d6fd4';
    strokePath(noisy(clean, denoise), pathColor, 3.2, 1);

    if (st.phase === PH.EVAL) drawProjection(clean, { delta: true });
    else if (st.phase === PH.PROJECT) drawProjection(clean, { delta: true, label: true });
    else if (st.phase === PH.RENOISE) drawProjection(clean, {});
    else if (st.phase === PH.DONE) drawCheck();

    st.delta = violation(clean).delta;
    if (st.phase !== PH.DONE) hudStats();   // live δ / n as the sample morphs
    if (prog >= 1) advance();
    requestAnimationFrame(frame);
  }

  function advance() {
    switch (st.phase) {
      case PH.DRAW: {
        st.from = null;
        go(violation(sampleAt(st.h)).delta <= TAU ? PH.DONE : PH.EVAL);
        break;
      }
      case PH.EVAL: {
        // renoise depth from the violation
        st.n = nVal(violation(sampleAt(st.h)).delta);
        go(PH.PROJECT);
        break;
      }
      case PH.PROJECT: go(PH.RENOISE); break;
      case PH.RENOISE: {
        // re-run from the renoised projection; it lands closer to c each time
        st.from = project(sampleAt(st.h));
        st.h = 1 - RHO * (1 - st.h);
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
