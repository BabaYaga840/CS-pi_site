# CS-Pi lab talk

Self-contained slide decks with speaker notes, built from the same figures,
rollout GIFs and hardware clips as the project page.

**There are two decks, and they are different talks — not the same deck at two
lengths.**

| Deck | Source | Present from | For |
|------|--------|--------------|-----|
| **20-minute cut** | `short.src.html` | `talk/short.html` | A conference or group slot. 28 slides, one path, one growing table. |
| **45-minute lab talk** | `deck.src.html` | `talk/index.html` | A full lab meeting, and the backup material you answer questions from. 50 slides, three selectable lengths. |

The short deck is not a subset of the long one. It opens for a mixed audience
(vision, robotics, ML): the pretrained flow policy, the unguided policy
colliding on both hardware layouts, the constraint, the problem stated in two
halves (satisfy C, and still do the task), the goal as one equation, the two
properties we want (feasible and plausible, with the
hardware clips as evidence), and a one-slide flow-matching primer — so nothing
in the method act relies on background the room does not share. It then follows
the rule that a talk should build rather than display: the approach is **one
flow-time picture that grows across seven slides**, paired with a pipeline strip — noise becoming an
action along the flow's own time axis, with each method shown as a place on that
axis where it intervenes — instead of a finished four-column figure, and every
result is one message with one comparison — the paper's eight-panel 2D figure is
cropped into single panels revealed one at a time, and the large results tables
and the wall-clock chart are dropped entirely in favour of video plus two or
three numbers. Reach for the long deck when someone asks for the table.

## Present it

```bash
python3 -m http.server 8000     # from the repo root
# 20-minute cut:  http://localhost:8000/talk/short.html
# 45-minute deck: http://localhost:8000/talk/
```

Both load media by relative path, so they run at full resolution with no size
ceiling. These are the ones to present from.

## Time budget, 20-minute cut

| Section | Slides | Runs |
|---------|--------|------|
| The setup: policy, collisions, constraint, the problem in two halves, goal, two properties, flow matching | 1–9 | ~6 min |
| Two attempts that fail, and rejection | 10–13 | ~4 min |
| The turn and the method | 14–16 | ~4 min |
| Does it work: the shelf board, what the flow samples, 2D, shelf rollouts, 3D-Orient, hardware | 17–26 | ~8.5 min |
| Wrap | 27–28 | ~2 min |

**24.5 min total — this deck no longer fits a 20-minute slot as it stands, and
you have to cut into it.** Everything is here so the choice is yours rather than
mine; nothing below has been removed for you.

The cuts, in the order worth making them:

| Cut | Saves | Why it is the cheapest thing to lose |
|-----|-------|--------------------------------------|
| Slide 16, the live animation | 1.0 | Already the standing cut; the loop is fully explained by 14–15. |
| Slide 24, the shelf rollout GIFs | 1.5 | Slides 17–20 are now the shelf result, with numbers. Keep the GIFs only if you would rather argue from footage than from the board. |
| Slide 7, the goal as a density | 0.5 | Slide 6 already ends on `a ~ π_θ(·&#124;o) s.t. C(a) = 0`; slide 7 rewrites it as p★. |

That is 21.5. For the last minute and a half, either drop the 2D pair (slides
22–23, 2.0, landing at 19.5 — but you lose the one place the audience *sees* the
distributions rather than reading a logL column), or take 0.5 off each of slides
11, 14 and 20. **If you are starting "THE TURN" (slide 14) at about ten minutes, you
are on time.** The rail shows the running budget, and it counts every slide, not
the cut list.

Two places the deck now says the same thing twice, both deliberate and both
yours to resolve: slide 23's "feasible is easy" is the thesis slide 17 opens
with, and slide 24 is a second pass at the shelf. Act I is 6 of the 24.5
minutes — a deliberate bet for a mixed audience, and the other place to look if
you are over.

## Keys

| Key | Does |
|-----|------|
| `→` `␣` `↓` / `←` `↑` | Next / previous slide |
| `C` | Cycle talk length — see below |
| `N` | Speaker notes panel |
| `O` | Slide overview grid (click any card to jump) |
| `R` | Replay the video or GIF on this slide |
| `F` | Fullscreen |
| `?` | Key help |

## Talk lengths — 45-minute deck only

Every slide carries a `data-min` budget and a `data-tier`. `C` cycles between
three paths, and the rail shows which is live and how long it runs. (The
20-minute cut has one path; `C` does nothing useful there.)

| Path | Slides | Runs | Adds |
|------|--------|------|------|
| **essential** | 23 | ~45 min | The spine: the taxonomy build, the guidance frontier, the method, and the 2D and shelf tasks with their results. Fits a 45-minute slot with questions. Default. |
| **full talk** | 41 | ~84 min | Proposition 1, the projection implementation, the Spheres and 3D-Orient task introductions, both compute slides, the live loop, per-benchmark rollouts |
| **deep dive** | 47 | ~98 min | The Jensen-swap bound, the CBF comparison, the guidance α side-by-side, the proposed Spheres support sweep, config 2 |

Slides outside the current path are skipped by the arrow keys but stay reachable
from the overview, so a deep-dive slide can be pulled up to answer a question.
Two appendix slides sit at the end of every path and are never timed.

To move a slide between paths, change its `data-tier` in `talk/deck.src.html`
and rebuild.

## Build

Each deck has one source file. Media is referenced with
`{{M:<repo-relative path>}}` tokens, and `talk/build.py` emits a local and an
embedded build for each:

```bash
python3 talk/build.py                    # both decks, both builds
python3 talk/build.py --short            # just the 20-minute cut
python3 talk/build.py --long --local     # skip the slow embedded build
```

| Output | What it is |
|--------|------------|
| `talk/short.html` | 20-minute cut, media as relative paths. Present from this. |
| `talk/index.html` | 45-minute deck, media as relative paths. |
| `talk/dist/cspi-talk-20min.embed.html` | The short deck with every asset inlined as a `data:` URI, for publishing as an Artifact. |
| `talk/dist/cspi-talk.embed.html` | The same for the long deck. |

Local outputs have to sit directly in `talk/`, because the local build rewrites
media tokens to `../<repo path>`.

`short.src.html` was seeded by copying the long deck's engine — CSS, notes
panel, keyboard handling, rail, overview — and swapping in its own slides plus
the pipeline renderer. It is now its own source file; there is no generator to
re-run. The two engines are therefore duplicated, so **a fix to shared engine
code has to be applied to both files.**

The embedded build has a hard 16 MB ceiling, so GIFs are downscaled to 440 px
and every 4th frame, and the large PNG filmstrips are re-encoded as JPEG. The
build prints a per-asset size table and fails if it goes over. Compressed media
is cached in `talk/.cache/`, so repeat runs are fast. Pillow is required for the
embedded build only:

```bash
pip install Pillow
```

`talk/dist/` and `talk/.cache/` are generated and git-ignored.

## Editing

- **Content and speaker notes** — `talk/deck.src.html`. Each slide is one
  `<section class="slide">` with `data-act`, `data-title`, `data-min`,
  `data-tier`, and a `<div class="notes">` that is lifted into the notes panel
  at load (it never renders on the slide itself).
- **The act I figures** (20-minute cut) — three one-off SVGs drawn in the
  script: `data-policy` (slide 2: observation in, a different action chunk per
  draw; the photo comes from its `data-src` media token), `data-cset` (slide 4:
  the feasible set, a draw outside it, its projection and δ) and `data-goal`
  (slide 7: the policy's density with the infeasible part cut away). The
  flow-matching primer on slide 9 is `data-flow="0"`: the flow-time figure with
  no red band and one training pair drawn as a straight line. Slide 3 shows the
  unguided policy colliding on both hardware layouts using the annotated
  filmstrips `assets/hw_v1_fail.png` and `assets/hw_v2_fail.png` (the repo has
  no unguided hardware video); each strip is cropped to its five frames with
  `object-fit`, so swapping in a `<video>` of the same run is a one-line change.
- **The problem statement** (20-minute cut) — slides 5 and 6 build one sentence,
  "Policies which satisfy test-time defined constraints while also completing the
  task", across two slides: the headline is the same on both, and the half that is
  not yet live is greyed with `<span class="later">` (see `h2 .later` in the CSS).
  Slide 5 defines the constraint function, `C(a) = 0 ⟺ a ∈ C`, which is the bridge
  between the function notation and the set notation the rest of the deck uses for
  C. Slide 6 makes the argument that there is no task-success function, so
  likelihood under π_θ is the definition of doing the task, and ends on
  `a ~ π_θ(· | o) subject to C(a) = 0`. No SVG — both slides are plain HTML.
- **What the flow samples** (20-minute cut) — slide 21, `<svg data-bimodal>`.
  A Gaussian cloud and the connecting flow lines are generated from a seeded
  LCG, so the picture is byte-identical on every reload and between the local
  and embedded builds; the right-hand distribution is a real asset,
  `assets/2d_bimodal_vertical.png`, referenced through the SVG's `data-src` and
  drawn with `<image>`. That asset is the paper's 2D panel rotated 90° clockwise
  (`Image.Transpose.ROTATE_270`), white margins trimmed, upscaled to 900 px
  tall — clockwise so the red-circled mode lands at the top, where the rest of
  the deck puts the region that violates C. `MODE_HI`/`MODE_LO` are where the
  two blobs sit as a fraction of the asset's height, and the flow lines aim at
  them: **re-measure both if you regenerate the image.**
- **The projection maths** (20-minute cut) — slide 12 carries the two lines
  `â ~ π_θ(·|o)` and `c = Π_C(â) so that C(c) = 0` in `.projeq`, a two-column
  grid so both equations start at the same x (centring each line on its own
  staggers them, because "draw" and "project" differ in width). These replaced
  the `draw â → project → execute c` chip strip, which said the same thing the
  pipeline strip beside it already draws; `.recipe` is still used on five other
  slides, so the class stays.
- **The shelf board** (20-minute cut) — `<div data-shelf="N">` on slides 17–20,
  rendered by the `SHELF`/`STEP` arrays in the script. Every state draws the same
  table: the unguided prior is always present (logL only means something against
  its 15.0, goal reach only against its 72.0), methods the story has not reached
  are absent, and earlier ones grey out. Which cells are boxed is the `MARKS`
  map, keyed by state. States 1–3 box one cell in amber — the number that slide
  is about: guidance → goal reach 28.0, rejection → NFE 8676, projection →
  logL 11.2. State 4 drops the amber and boxes **three pairs**, each pair one
  colour, so a comparison is read across the board rather than narrated: red
  goal reach (CS-Pi 78.7 v guidance 28.0), purple logL (18.0 v projection 11.2),
  green NFE (285 v rejection 8,676). The `.spot-*` rules are scoped through
  `tbody` because they have to out-specify `tr.past td`, which greys whole rows.
  **Collision % is deliberately not a column** — it rewards inaction, since a
  policy that never moves scores 0.0, and safe-SR already requires no collision.
  The collision numbers stay in the speaker notes, where they get asked about. **The numbers are copied from `js/data.js`
  (`RESULTS.shelf`); if that file changes, change these too** — there is no
  import, and a scripted check against it lives only in the session that wrote
  it. Trust Sampling is deliberately off the board to keep it to four rows; its
  numbers are in the slide 20 notes for questions.
- **The pipeline strip** (20-minute cut) — `<svg data-pipe="N">` beside each
  figure on slides 10–15: the sampler as stacked boxes, one state per slide
  (untouched, guidance, projection, rejection with its restart arrow back to
  noise, the renoise return into the flow, the loop repeated). The states in
  use are 1, 3, 4, 8, 6, 7 in that order — 2 and 5 were retired, and rejection
  was added last as 8 — so the numbers are labels, not a sequence. Execute drops a
  row when a fix-up stage appears.
- **The flow-time figure** (20-minute cut) — `<svg data-flow="N">`, one state
  per slide 9–15. Noise on the left becomes an action on the right along the
  flow's own time axis; the grey lines are draws gathering late into two
  behaviours; a red band at the top violates the constraint. Every method is a
  position on that axis: guidance pushes mid-flow against the flow's blurred
  guess x̂₀ and lands in the gap, projection edits at t = 1, rejection restarts
  at t = 0, CS-Pi takes c back to t = n and re-runs. Each state's explanation
  sits in a caption strip above the plot; inside the plot only short tags, so
  the paths stay readable. The equation on slide 14 and the k tiles on slide 15
  are plain HTML. If you change the geometry constants (`A0`, `A1`, `N1`,
  `R1`, …), re-check that the redraws still end where the captions say.
- **The four-column taxonomy** (45-minute deck) — the `TAXO` array in the deck's script. Act II
  builds it one column at a time: each slide holds an
  `<svg data-taxo="N">`, which renders the first `N` columns filled in with
  column `N` highlighted, and `data-taxo="5"` renders all four with nothing
  highlighted (the assembled slide). Editing a column's copy in `TAXO` updates
  every slide it appears on. Rows are the five stages of one sampling pass, and
  the two dashed return arrows — rejection to pure noise, CS-Pi to partway down
  the flow — are the point of the figure; keep them visually comparable.
- **The guidance frontier chart** — the `FRONTIER` array in the deck's script.
  Only the two ends of the α sweep are measured today; adding intermediate
  points from the supplementary is one line each, and they join the dashed path
  automatically if you set `sweep:true`.
- **The Proposition 1 figure** and the live CS-Pi loop are drawn in the same
  script block. The loop is ported from `js/hero.js`.
- **Task introductions** sit immediately before the results they explain, one
  per benchmark, so no table arrives before its task has been described. The 2D
  and wall-clock figures (`assets/fig_2d_distributions.png`,
  `assets/fig_wallclock.png`) were extracted from the rebuttal PDF at its
  embedded resolution — re-export from the originals if you have them.
- **The hardware stills** — slides 2 and 4 use the poster frame
  `assets/hardware/cspi_success_0.jpg` (layout 1, before the arm moves) and
  slide 3 the annotated unguided filmstrips, so hardware footage appears on five
  slides in all.
- **The hardware clips** (the two properties on slide 8, results on slide 26) play the
  colour-graded versions in `assets/hardware/graded/`, not the raw
  `assets/hardware/*.mp4`. Regenerate with `python3 tools/grade_hardware_clips.py`
  (needs numpy, Pillow, opencv-python-headless, imageio-ffmpeg, torch,
  transformers; CLIPSeg and SlimSAM download from Hugging Face on first run).
  It washes the background toward white, keeps the arm, apple and plate at
  full colour, and tints that layout's obstacles red; the two hand-held clips
  are stabilised by fitting a shift and zoom to the plate each frame. Graded
  clips are committed; `tools/.preview/` (`--preview`'s contact sheets) is
  git-ignored.

  | Layout | Obstacles tinted | Clips |
  |--------|-------------------|-------|
  | 1 (slide 8) | cups and bowl | `cspi_success_0`, `project_fail` |
  | 2 (slide 26) | the two canisters | `gradient_guidance`, `trust_fail` |

  To change the look, edit the constants at the top of the script: `SAT_FG`
  (foreground saturation), `BG_SAT` / `BG_WASH` / `BG_BLUR` (background
  desaturation, white-wash strength, blur), and `TINT` / `TINT_T` (obstacle
  tint colour and blend strength).

### One gotcha, if you add an SVG figure

Give every `<marker>` (and any other `url(#id)` target) an id that is **unique
per SVG instance**. A `url(#id)` reference resolves to the first match in the
whole document, and every slide except the current one is `display:none`, where
markers do not render at all — so a shared id means arrowheads silently vanish
on every slide but the first. Both figure renderers suffix their marker ids with
the diagram's state number for this reason.

Styling follows the project page's tokens (`css/style.css`). The deck commits to
a single light theme on purpose: every figure, GIF and clip in it has a light
ground, so a dark inversion would frame all of them badly.
