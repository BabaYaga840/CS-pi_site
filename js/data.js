// =============================================================================
// Site content / configuration. Edit here, not in index.html.
// gif_manifest.js (auto-generated) supplies the actual GIF + poster paths.
// =============================================================================

window.SITE = {
  // --- Authorship -----------------------------------------------------------
  // Anonymous for double-blind review. To deanonymize later, set anonymous:false
  // and fill in `authors` / `affiliation`. One edit, nothing else changes.
  anonymous: true,
  authors: 'Anonymous Authors',
  affiliation: 'CoRL 2026 submission',

  method: 'CS-Pi',
  title: 'CS-Pi: Constraint-Satisfying Flow Policy Sampling',
  tagline:
    'Enforce hard safety constraints on a flow-matching robot policy ' +
    'at inference, with no gradient, no retraining, and no per-deployment tuning.',

  // Links. Empty string hides the button. Fill in when public.
  links: {
    paper: '',     // e.g. 'https://arxiv.org/abs/...'
    pdf: '',       // e.g. 'assets/paper.pdf'
    code: '',      // e.g. 'https://github.com/...'
    bibtex: '#cite'
  }
};

// --- The four samplers (our method first) -----------------------------------
window.METHODS = [
  {
    key: 'amr', label: 'CS-Pi', short: 'Ours', ours: true, color: '#1d6fd4',
    blurb: 'Draw, project to the nearest feasible action, renoise to a depth ' +
           'set by the violation, and re-run the unmodified flow. Iterates to ' +
           'feasibility while every draw stays in-distribution.'
  },
  {
    key: 'projection', label: 'Projection', short: 'Project + execute', color: '#8b5cf6',
    blurb: 'Run the unmodified flow, then snap the finished action onto the ' +
           'feasible set and execute it. Feasible, but the executed action is ' +
           'one the policy itself would never draw.'
  },
  {
    key: 'tweedie', label: 'Gradient Guidance', short: 'Guidance', color: '#e0533d',
    blurb: 'Steer every ODE step by the gradient of the constraint evaluated at ' +
           'a one-step guess of the clean action. The proxy gradient is ' +
           'uninformative when the policy is still uncertain between modes.'
  },
  {
    key: 'trust', label: 'Trust Sampling', short: 'Trust', color: '#2a9d8f',
    blurb: 'Schedule-aware guidance that limits early steps and adds inner ' +
           'iterations. Reduces proxy variance but pays a large compute cost ' +
           'and still leaves the policy distribution.'
  },
  // --- extra baselines used by the 3D-Orient comparison -------------------
  {
    key: 'unguided', label: 'Unguided', short: 'Prior', color: '#6b7c93',
    blurb: 'The flow prior alone, with no orientation enforcement. It ' +
           'reaches the goal but ignores the orientation preference, which is ' +
           'out-of-distribution for the prior.'
  }
];

// --- Benchmarks. Only `shelf` has GIFs today; the others are placeholders that
//     light up automatically once tools/build_manifest.py finds their folders.
window.TASKS = [
  {
    key: 'shelf',
    label: 'Shelf pick-and-place',
    dim: '7-DoF Franka',
    available: true,
    outcomes: true,
    methods: ['amr', 'projection', 'tweedie', 'trust'],
    blurb:
      'A 7-DoF Franka picks a 4 cm cube from a three-rung shelf and places it ' +
      'on the table. At inference we add obstacles that were absent at training. ' +
      'A rollout counts as safe-and-successful only if it is collision-free, ' +
      'picks the cube, and places it.',
    scenarios: [
      { key: 'clutter_combo',       label: 'Clutter combo',
        desc: 'Several deployment-time obstacles crowd the shelf and table.' },
      { key: 'tall_table_pillar',   label: 'Tall table pillar',
        desc: 'A tall pillar stands on the table between the arm and the cube.' },
      { key: 'two_flankers_top',    label: 'Two flankers (top)',
        desc: 'Two obstacles flank the cube on the top rung.' },
      { key: 'mid_rung_neighbor_E', label: 'Mid-rung neighbor',
        desc: 'A neighbouring object sits beside the cube on the middle rung.' },
      { key: 'low_rung_neighbor_E', label: 'Low-rung neighbor',
        desc: 'A neighbouring object sits beside the cube on the low rung.' }
    ]
  },
  {
    key: '3dorient',
    label: '3D-Orient',
    dim: '7-DoF orientation cost',
    available: true,
    outcomes: false,
    methods: ['amr', 'unguided', 'tweedie', 'trust'],
    blurb:
      'A 7-DoF Panda reach where every step must stay within 10 cm of the goal ' +
      'and within 0.5 (Frobenius) of a target end-effector orientation. The ' +
      'orientation lock is absent from the prior’s training, so only the ' +
      'inference-time method enforces it. CS-Pi here uses the EE-orientation ' +
      'proximal step (fixed reference).',
    rolloutCaption:
      'Reach-and-orient under the orientation preference. Each frame is annotated ' +
      'with the live end-effector distance and orientation error. CS-Pi is the ' +
      'only method that reliably holds the orientation (it pays in log-likelihood, ' +
      'off-manifold by construction); the gradient baselines mostly fail to orient, ' +
      'and the unguided prior and trust sampling essentially never do.',
    scenarios: [
      { key: 'config1', label: 'Config 1',
        desc: 'A goal where the target orientation can be held all the way in.' },
      { key: 'config2', label: 'Config 2 — infeasible under the constraint',
        desc: 'The goal cannot be reached while holding the target orientation.',
        note: 'This goal is not reachable while holding the target orientation: ' +
              'the constraint and the reach conflict. Rather than abandoning the ' +
              'orientation to complete the reach, CS-Pi enforces the constraint for ' +
              'as long as possible, holding the orientation until the task forces a ' +
              'trade-off. The annotated orientation error stays low even where the ' +
              'reach cannot finish.' }
    ]
  }
];

// --- Result tables (from the paper) -----------------------------------------
// `ours` flags the CS-Pi row; `best` lists column indices where this row holds
// the best value (for bolding). Values are display strings.
window.RESULTS = {
  shelf: {
    title: 'Shelf pick-and-place',
    caption: '5 scenarios, 150 tasks (30 per scenario). logL is the mean ' +
             'log-likelihood the prior assigns to a method’s samples ' +
             '(prior’s own samples score 15.0; higher is more in-distribution). ' +
             'NFE is flow-model calls per trajectory.',
    cols: ['Method', 'Safe-SR (%) ↑', 'Goal reach (%) ↑',
           'Collision (%) ↓', 'logL ↑', 'NFE ↓'],
    rows: [
      { c: ['Unguided (prior)',            '3.3',  '72.0', '82.0', '15.0', '240'] },
      { c: ['Gradient Guidance',           '28.0', '28.0', '0.0',  '10.2', '240'], best: [3] },
      { c: ['Trust Sampling',              '27.3', '28.0', '0.7',  '10.5', '1242'] },
      { c: ['Rejection (B=100)',           '33.3', '67.3', '40.7', '14.2', '8676'] },
      { c: ['Projection',                  '62.0', '66.0', '4.0',  '11.2', '240'] },
      { c: ['CS-Pi (ours)',                '73.3', '78.7', '6.7',  '18.0', '285'],
        ours: true, best: [1, 2, 4] }
    ]
  },
  d3il: {
    title: '2D Avoidance (macro over 6 scenarios)',
    caption: '200 rollouts per cell, best hyperparameter per method. ' +
             'fully-in-supp. is the fraction of rollouts whose every waypoint ' +
             'lies inside the demonstration support (a strict in-distribution check).',
    cols: ['Method', 'Safe-SR (%) ↑', 'Fully-in-supp. ↑',
           'Log-lik. ↑', 'NFE ↓'],
    rows: [
      { c: ['Unguided',           '5.2',   '0.795', '+1.65', '456'] },
      { c: ['Gradient Guidance',  '75.7',  '0.595', '1.51',  '485'] },
      { c: ['Trust Sampling',     '45.5',  '0.444', '1.53',  '3161'] },
      { c: ['Rejection',          '68.1',  '0.831', '+1.71', '6732'], best: [3] },
      { c: ['Projection',         '100.0', '0.650', '-3.34', '112'], best: [1, 4] },
      { c: ['CS-Pi (ours)',       '99.0',  '0.857', '1.53',  '283'],
        ours: true, best: [2] }
    ]
  },
  orient: {
    title: '3D-Orient (reach with an orientation preference)',
    caption: '90 rollouts per cell. Success: a step simultaneously within 10 cm ' +
             'of the target position and 0.36 rad of the target orientation. ' +
             'max EE step: largest single-step end-effector jump (m; smoothness proxy).',
    cols: ['Method', 'Success ↑', 'Goal reach ↑', 'logL ↑',
           'max EE step', 'NFE ↓'],
    rows: [
      { c: ['Unguided',                 '1.1%',  '100%',  '13.55', '0.107', '135'],
        best: [2, 4, 5] },
      { c: ['Gradient Guidance', '8.9%', '10.0%', '9.41', '0.928', '160'] },
      { c: ['Trust Sampling',           '10.0%', '11.1%', '13.56', '1.310', '1358'], best: [3] },
      { c: ['CS-Pi + EE-prox (ours)',   '68.9%', '98.9%', '10.26', '0.108', '210'],
        ours: true, best: [1] }
    ]
  },
  hw: {
    title: 'Hardware: pick the apple, place it on the blue plate',
    caption: 'Zero-shot on a Franka with π₀.₅; the constraint set is obstacle ' +
             'bounding boxes from a ZED 2 RGB-D vision pipeline. Two layouts, ' +
             '10 trials per method per layout. logL is the log-likelihood the ' +
             'prior assigns to executed actions (prior’s own draws: -470.2).',
    cols: ['Method', 'Layout 1 ↑', 'Layout 2 ↑', 'Aggregated ↑',
           'Time/step (s) ↓', 'logL ↑'],
    rows: [
      { c: ['Unguided (prior)',  '20', '0',  '10', '0.069', '-470.2'], best: [4] },
      { c: ['Gradient Guidance', '40', '10', '25', '0.139', '-464.9'], best: [5] },
      { c: ['Trust Sampling',    '20', '20', '20', '0.135', '-474.8'] },
      { c: ['Projection',        '40', '40', '40', '0.099', '-473.2'] },
      { c: ['CS-Pi (ours)',      '60', '50', '55', '0.143', '-471.8'],
        ours: true, best: [1, 2, 3] }
    ]
  }
};

// --- Headline numbers for the abstract strip --------------------------------
window.HEADLINE = [
  { big: '73.3%', small: 'safe-success on the shelf',
    sub: 'vs 62% projection, 28% guidance' },
  { big: '18.0',  small: 'in-distribution (log-likelihood)',
    sub: 'higher than gradient guidance (10.2), trust sampling (10.5), projection (11.2)' },
  { big: '0',     small: 'constraint gradients needed',
    sub: 'No gradients based on proxies' },
  { big: '285',   small: 'average flow-model calls',
    sub: 'more than gradient guidance (240); far below trust sampling (1242) and rejection (8676)' }
];
