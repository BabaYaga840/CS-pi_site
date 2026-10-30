// =============================================================================
// Site content / configuration. Edit here, not in index.html.
// gif_manifest.js (auto-generated) supplies the actual GIF + poster paths.
// =============================================================================

window.SITE = {
  // --- Authorship -----------------------------------------------------------
  // Accepted at CoRL 2026. The camera-ready author list is not filled in yet:
  // set `authors` (and `affiliation`, shown under the authors when non-empty).
  // The BibTeX block reads `authors` too.
  anonymous: true,
  authors: 'Anonymous Authors',
  affiliation: '',
  venue: 'CoRL 2026',
  venueLong: 'Conference on Robot Learning (CoRL) 2026',

  method: 'CS-Pi',
  title: 'CS-Pi: Constraint-Satisfying Flow Policy Sampling',
  tagline:
    'Sample actions from a frozen flow-matching robot policy that are both ' +
    'safe, satisfying a constraint absent from its demonstrations, and ' +
    'plausible, remaining likely under the policy. No retraining, no ' +
    'constraint gradient at noisy states.',

  // Links. Empty string hides the button. Fill in when public.
  links: {
    paper: '',     // e.g. 'https://arxiv.org/abs/...'
    pdf: '',       // e.g. 'assets/paper.pdf'
    code: '',      // e.g. 'https://github.com/...'
    bibtex: '#cite'
  }
};

// --- The samplers (our method first). `card: false` keeps a method out of the
//     method-card grid while leaving it available to the explorer.
window.METHODS = [
  {
    key: 'amr', label: 'CS-Pi', short: 'Ours', ours: true, color: '#1d6fd4',
    blurb: 'Draw an action, project it onto the constraint set, and rather than ' +
           'executing the projection, renoise it to a depth set by how far the ' +
           'action had to move and re-run the unmodified policy from there. ' +
           'Iterating drives the draws to the constraint while each stays in-distribution.'
  },
  {
    key: 'projection', label: 'Projection', short: 'Project + execute', color: '#8b5cf6',
    blurb: 'Map the sampled action to the nearest constraint-satisfying point ' +
           'and execute it. Efficient, but the projected action need not be ' +
           'in-distribution and can be jerky or task-irrelevant.'
  },
  {
    key: 'rejection', label: 'Rejection', short: 'Redraw', color: '#c98a12',
    blurb: 'Redraw complete actions from the policy until one satisfies the ' +
           'constraint. Every output is in-distribution, but the wait is ' +
           'intractable when feasible actions are rare.'
  },
  {
    key: 'tweedie', label: 'Gradient Guidance', short: 'Guidance', color: '#e0533d',
    blurb: 'Perturb each denoising step by the gradient of a constraint cost. ' +
           'A hard constraint such as collision-freeness carries no usable ' +
           'gradient, and at noisy states the cost of the expected action is a ' +
           'poor proxy for the expected cost when the policy is uncertain between modes.'
  },
  {
    key: 'trust', label: 'Trust Sampling', short: 'Trust', color: '#2a9d8f',
    blurb: 'Gradient guidance that halts each step at the estimated edge of ' +
           'the policy distribution. It shares our goal but inherits the same ' +
           'proxy bias, at a much larger compute cost.'
  },
  {
    key: 'cbf', label: 'CBF samplers', short: 'SafeDiffuser · SafeFlowMatcher', color: '#475569',
    blurb: 'SafeDiffuser and SafeFlowMatcher correct each denoising step with a ' +
           'control-barrier function. They certify feasibility, but the ' +
           'certificate does not constrain likelihood under the policy, and a ' +
           'continuous correction cannot redraw from a surviving policy mode.'
  },
  // --- extra baseline used by the 3D-Orient comparison --------------------
  {
    key: 'unguided', label: 'Unguided', short: 'Prior', color: '#6b7c93', card: false,
    blurb: 'The policy alone, with no constraint enforcement. It reaches the ' +
           'goal but ignores the orientation preference, which was absent from ' +
           'its demonstrations.'
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
      'A 7-DoF reach to a goal sampled anywhere in the reachable workspace, with ' +
      'a soft preference added on top: hold a top-down end-effector orientation ' +
      'R*, encoded as the cost λ Σₜ ‖R(qₜ) − R*‖²_F. The test is whether a ' +
      'method can honour the orientation without giving up the reach. CS-Pi ' +
      'swaps its projection for the proximal operator of this cost; nothing ' +
      'else changes.',
    rolloutCaption:
      'Reach-and-orient under the orientation preference. Each frame is annotated ' +
      'with the live end-effector distance and orientation error. CS-Pi is the ' +
      'only method that does both, with reach and smoothness within a millimetre ' +
      'of the unguided policy. The guidance baselines lower the orientation cost ' +
      'but push the end effector up to 0.70 m off target: IK redundancy means the ' +
      'half-denoised guess they steer on averages several valid configurations ' +
      'into an invalid one.',
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
// the best value (for bolding). Values are display strings; '—' = not scored.
// `lead` is the takeaway shown above the table.
window.RESULTS = {
  shelf: {
    title: 'Shelf pick-and-place',
    lead: 'CS-Pi reaches the highest safe-success (73.3%) and is the only method ' +
          'whose samples stay at or above the prior in log-likelihood; projection ' +
          'and the gradient baselines satisfy the obstacle only by pushing the chunk ' +
          'out of the policy’s distribution. Every obstacle-aware method avoids ' +
          'collision, so what separates them is whether the gripper still reaches ' +
          'the cube: CS-Pi re-denoises a trajectory that threads the obstacles and ' +
          'keeps the prior’s grasp. CS-Pi and projection share the same L-BFGS ' +
          'proximal step, so the gap between them is the iterative loop.',
    caption: '5 scenarios, 150 tasks (30 per scenario). Safe-SR: collision-free ' +
             'success. logL is the mean log-likelihood the prior assigns to a ' +
             'method’s samples (nats/dim; the prior’s own samples score 15.0; ' +
             'higher is more in-distribution). NFE is flow-model calls per ' +
             'trajectory. SafeDiffuser and SafeFlowMatcher are re-implementations ' +
             'on the same prior at their swept-best admissible grids. †9 of ' +
             'SafeDiffuser’s 2000 scored chunks have non-finite log-density ' +
             '(off-manifold samples), so its mean is undefined.',
    cols: ['Method', 'Safe-SR (%) ↑', 'Goal reach (%) ↑',
           'Collision (%) ↓', 'logL ↑', 'NFE ↓'],
    rows: [
      { c: ['Unguided (prior)',             '3.3',  '72.0', '82.0', '15.0', '240'] },
      { c: ['Gradient Guidance (α=0.20)',   '28.0', '28.0', '0.0',  '10.2', '240'], best: [3] },
      { c: ['Trust Sampling (w=0.01, j=5)', '27.3', '28.0', '0.7',  '10.5', '1242'] },
      { c: ['Rejection (B=100)',            '33.3', '67.3', '40.7', '14.2', '8676'] },
      { c: ['Projection',                   '62.0', '66.0', '4.0',  '11.2', '240'] },
      { c: ['SafeDiffuser',                 '11.3', '18.7', '24.7', 'n/a†', '240'] },
      { c: ['SafeFlowMatcher',              '56.0', '59.3', '4.0',  '10.9', '432'] },
      { c: ['CS-Pi (k=10, Kmax=5) (ours)',  '73.3', '78.7', '6.7',  '18.0', '285'],
        ours: true, best: [1, 2, 4] }
    ]
  },
  d3il: {
    title: '2D Avoidance (macro over 6 scenarios)',
    lead: 'Among methods that stay near the prior in log-likelihood, CS-Pi keeps ' +
          'the most trajectories fully on the demonstration support, at 99% ' +
          'safe-success. SafeDiffuser and SafeFlowMatcher match it here (100% ' +
          'safe-success; SafeDiffuser keeps 0.828 fully on-support), the one ' +
          'benchmark where the CBF samplers are competitive; projection reaches ' +
          '100% only by collapsing log-likelihood to −3.34.',
    caption: '200 rollouts per cell, best hyperparameter per method. Safe-SR: ' +
             'rollouts reaching the goal collision-free. Fully-in-supp.: fraction ' +
             'of rollouts whose every waypoint lies inside the training-demonstration ' +
             'support. Log-lik.: median per-chunk log-likelihood under the prior ' +
             '(nats/dim); a few off-manifold chunks dominate the mean. SafeDiffuser ' +
             'and SafeFlowMatcher are re-implementations on the same prior.',
    cols: ['Method', 'Safe-SR (%) ↑', 'Fully-in-supp. ↑',
           'Log-lik. ↑', 'NFE ↓'],
    rows: [
      { c: ['Unguided',           '5.2',   '0.795', '+1.65', '456'] },
      { c: ['Gradient Guidance',  '75.7',  '0.595', '1.51',  '485'] },
      { c: ['Trust Sampling',     '45.5',  '0.444', '1.53',  '3161'] },
      { c: ['Rejection',          '68.1',  '0.831', '+1.71', '6732'], best: [3] },
      { c: ['Projection',         '100.0', '0.650', '-3.34', '112'], best: [1] },
      { c: ['SafeDiffuser',       '100.0', '0.828', '1.51',  '92'],  best: [1, 4] },
      { c: ['SafeFlowMatcher',    '100.0', '—',     '—',     '—'],   best: [1] },
      { c: ['CS-Pi (ours)',       '99.0',  '0.857', '1.53',  '283'],
        ours: true, best: [2] }
    ]
  },
  orient: {
    title: '3D-Orient (reach with an orientation preference)',
    lead: 'CS-Pi is the only method that honours the orientation without giving ' +
          'up the reach: 68.9% success, with reach and smoothness within a ' +
          'millimetre of the unguided policy. The guidance baselines lower the ' +
          'orientation cost but push the end effector up to 0.70 m off target and ' +
          'roughen the path, so their success stays at or below 10%. The CBF ' +
          'samplers fare no better: SafeDiffuser and SafeFlowMatcher reach 7.8% ' +
          'success and the goal in only 2.2% of rollouts. CS-Pi reads the cost ' +
          'only on fully formed samples.',
    caption: '90 rollouts per cell. Success: a step simultaneously within 10 cm ' +
             'of the target position and 0.36 rad of the target orientation. ' +
             'Goal reach: rollouts ending within 10 cm of the target position. ' +
             'logL comparisons are meaningful only at comparable constraint ' +
             'satisfaction, since the guidance configurations reach only 3.3% and ' +
             '8.9% success. Max EE step: largest single-step end-effector jump ' +
             '(m; smoothness proxy). NFE: model evaluations per rollout. ' +
             '†Re-implementations on the same prior at their swept-best admissible ' +
             'configurations, evaluated in a later run on the same 90 tasks; their ' +
             'logL is the Unguided value plus the gap to Unguided measured in that run.',
    cols: ['Method', 'Success ↑', 'Goal reach ↑', 'logL ↑',
           'Max EE step', 'NFE ↓'],
    rows: [
      { c: ['Unguided',                    '1.1%',  '100%',  '13.55', '0.107', '135'],
        best: [2, 4] },
      { c: ['Gradient Guidance (α=0.003)', '3.3%',  '77.8%', '12.55', '0.120', '153'] },
      { c: ['Gradient Guidance (α=0.03)',  '8.9%',  '10.0%', '9.41',  '0.928', '160'] },
      { c: ['Trust Sampling (w=0.001)',    '10.0%', '11.1%', '13.56', '1.310', '1358'], best: [3] },
      { c: ['SafeDiffuser†',               '7.8%',  '2.2%',  '3.83',  '0.772', '160'] },
      { c: ['SafeFlowMatcher†',            '7.8%',  '2.2%',  '8.02',  '0.700', '96'],   best: [5] },
      { c: ['CS-Pi + EE-prox (ours)',      '68.9%', '98.9%', '10.26', '0.108', '210'],
        ours: true, best: [1] }
    ]
  },
  hw: {
    title: 'Hardware: pick the apple, place it on the blue plate',
    lead: 'CS-Pi reaches the highest safe-success in both layouts (60% and 50%) ' +
          'and pooled (55% of 20 trials), versus 40% for projection, 25% for ' +
          'gradient guidance, and 10% for the unguided policy. Its per-step ' +
          'latency (0.143 s) matches gradient guidance (0.139 s). Projection is ' +
          'cheaper (0.099 s), but its one-shot snap drops it below the prior in ' +
          'log-likelihood (−473.2 against the prior’s −470.2), while CS-Pi stays ' +
          'close (−471.8). The runs are small (10 per layout), but the ordering ' +
          'holds in both layouts.',
    caption: 'Safe-success rate (%). Zero-shot on a Franka with a DROID-finetuned ' +
             'π₀.₅; the constraint set is obstacle bounding boxes from a ZED 2 ' +
             'RGB-D vision pipeline. Two layouts, 10 trials per method per layout. ' +
             'logL is the log-likelihood the frozen prior assigns to executed ' +
             'actions (the prior’s own draws score −470.2; higher is more ' +
             'in-distribution).',
    cols: ['Method', 'Layout 1 ↑', 'Layout 2 ↑', 'Aggregated ↑',
           'Time/step (s) ↓', 'logL ↑'],
    rows: [
      { c: ['Unguided (prior)',  '20', '0',  '10', '0.069', '−470.2 ± 1.0'], best: [4] },
      { c: ['Gradient Guidance', '40', '10', '25', '0.139', '−464.9 ± 1.4'], best: [5] },
      { c: ['Trust Sampling',    '20', '20', '20', '0.135', '−474.8 ± 2.1'] },
      { c: ['Projection',        '40', '40', '40', '0.099', '−473.2 ± 2.3'] },
      { c: ['CS-Pi (ours)',      '60', '50', '55', '0.143', '−471.8 ± 1.7'],
        ours: true, best: [1, 2, 3] }
    ]
  }
};

// --- Headline numbers for the abstract strip --------------------------------
window.HEADLINE = [
  { big: '55%',   small: 'safe-success on a real Franka',
    sub: 'zero-shot with π₀.₅; vs 40% projection, 25% guidance, 10% unguided' },
  { big: '73.3%', small: 'safe-success on the shelf',
    sub: 'vs 62% projection, 56% SafeFlowMatcher, 28% guidance' },
  { big: '18.0',  small: 'in-distribution (log-likelihood)',
    sub: 'the only shelf sampler at or above the prior (15.0); projection 11.2, guidance 10.2' },
  { big: '0',     small: 'constraint gradients needed',
    sub: 'No gradients based on proxies' }
];
