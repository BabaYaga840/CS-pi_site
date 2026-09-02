# CS-Pi lab talk

Self-contained slide decks with speaker notes, built from the same figures,
rollout GIFs and hardware clips as the project page.

**There are two decks, and they are different talks — not the same deck at two
lengths.**

| Deck | Source | Present from | For |
|------|--------|--------------|-----|
| **20-minute cut** | `short.src.html` | `talk/short.html` | A conference or group slot. 21 slides, one path, no tables. |
| **45-minute lab talk** | `deck.src.html` | `talk/index.html` | A full lab meeting, and the backup material you answer questions from. 50 slides, three selectable lengths. |

The short deck is not a subset of the long one. It opens for a mixed audience
(vision, robotics, ML): the pretrained flow policy, the unguided policy
colliding on both hardware layouts, the constraint, the goal as one equation, the two properties we want (feasible and plausible, with the
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
| The setup: policy, collisions, constraint, goal, two properties, flow matching | 1–7 | ~4.5 min |
| Two attempts that fail, and rejection | 8–11 | ~4 min |
| The turn and the method | 12–14 | ~4 min |
| Does it work | 15–19 | ~5.5 min |
| Wrap | 20–21 | ~2 min |

20 min total, which leaves no slack in a 20-minute slot: **cut slide 14 (the
live animation, 1 min) by default** and keep it for a longer slot or for
questions. **If you are starting "THE TURN" (slide 12) at about eight and a
half minutes, you are on time.** The rail shows the running budget. Slide 14
and slide 20's middle bullet are the two safe things to cut live.

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
  (slide 5: the policy's density with the infeasible part cut away). The
  flow-matching primer on slide 7 is `data-flow="0"`: the flow-time figure with
  no red band and one training pair drawn as a straight line. Slide 3 shows the
  unguided policy colliding on both hardware layouts using the annotated
  filmstrips `assets/hw_v1_fail.png` and `assets/hw_v2_fail.png` (the repo has
  no unguided hardware video); each strip is cropped to its five frames with
  `object-fit`, so swapping in a `<video>` of the same run is a one-line change.
- **The pipeline strip** (20-minute cut) — `<svg data-pipe="N">` beside each
  figure on slides 8–13: the sampler as stacked boxes, one state per slide
  (untouched, guidance, projection, rejection with its restart arrow back to
  noise, the renoise return into the flow, the loop repeated). The states in
  use are 1, 3, 4, 8, 6, 7 in that order — 2 and 5 were retired, and rejection
  was added last as 8 — so the numbers are labels, not a sequence. Execute drops a
  row when a fix-up stage appears.
- **The flow-time figure** (20-minute cut) — `<svg data-flow="N">`, one state
  per slide 7–13. Noise on the left becomes an action on the right along the
  flow's own time axis; the grey lines are draws gathering late into two
  behaviours; a red band at the top violates the constraint. Every method is a
  position on that axis: guidance pushes mid-flow against the flow's blurred
  guess x̂₀ and lands in the gap, projection edits at t = 1, rejection restarts
  at t = 0, CS-Pi takes c back to t = n and re-runs. Each state's explanation
  sits in a caption strip above the plot; inside the plot only short tags, so
  the paths stay readable. The equation on slide 12 and the k tiles on slide 13
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
- **The hardware clips** (the two properties on slide 6, results on slide 19) play the
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
  | 1 (slide 6) | cups and bowl | `cspi_success_0`, `project_fail` |
  | 2 (slide 19) | the two canisters | `gradient_guidance`, `trust_fail` |

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
