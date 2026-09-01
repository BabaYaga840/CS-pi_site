# CS-Pi lab talk

Self-contained slide decks with speaker notes, built from the same figures,
rollout GIFs and hardware clips as the project page.

**There are two decks, and they are different talks — not the same deck at two
lengths.**

| Deck | Source | Present from | For |
|------|--------|--------------|-----|
| **20-minute cut** | `short.src.html` | `talk/short.html` | A conference or group slot. 17 slides, one path, no tables. |
| **45-minute lab talk** | `deck.src.html` | `talk/index.html` | A full lab meeting, and the backup material you answer questions from. 50 slides, three selectable lengths. |

The short deck is not a subset of the long one. It follows the rule that a talk
should build rather than display: the approach is **one sample-space picture
that grows across six slides** — the policy's two routes, a constraint on one of
them, and a dot for where each method's draw lands — instead of a finished
four-column figure, and every
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
| The problem | 1–3 | ~3 min |
| Two attempts that fail | 4–6 | ~3.5 min |
| The turn and the method | 7–10 | ~5.5 min |
| Does it work | 11–15 | ~5.5 min |
| Wrap | 16–17 | ~2 min |

19.5 min total, so a 20-minute slot has slack. **If you are past "THE TURN"
(slide 7) at eight minutes, you are on time.** The rail shows the running
budget. Slides 10 (the live animation) and 16's middle bullet are the two safe
things to cut live.

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
- **The pipeline strip** (20-minute cut) — `<svg data-pipe="N">` beside each
  sample-space figure on slides 4–9: the sampler as stacked boxes, one state
  per slide (untouched, guidance, projection, the cut arrow, the renoise
  return, the loop repeated). Execute drops a row when projection appears.
- **The sample-space method figure** (20-minute cut) — the renderer driven by
  `<svg data-geo="N">`, one state per slide 4–9: the policy's draw lands in the
  obstacle; guidance bends it off every route; projection snaps it to the rim,
  off the route; rejection redraws from noise with no memory; the biased redraw
  through a window at c; and the iteration, with windows shrinking as δ does.
  Nothing moves between states, so the audience tracks the same â, c and
  windows from slide to slide. The routes are thin bands on purpose — the data
  manifold is low-dimensional, which is exactly why a projection leaves it. The
  geometry is exact and was found by a small search (c is the true nearest rim
  point, every redraw is on the route and inside its window, and the route
  curves toward the rim so the redraws really do get closer); if you move the
  disc or the route, re-check those claims before presenting. The equation on
  slide 8 and the k tiles on slide 9 are plain HTML, not part of the SVG.
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
