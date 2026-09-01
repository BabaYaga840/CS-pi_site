# CS-Pi lab talk

A self-contained slide deck with speaker notes, built from the same figures,
rollout GIFs and hardware clips as the project page.

## Present it

```bash
python3 -m http.server 8000     # from the repo root
# open http://localhost:8000/talk/
```

`talk/index.html` loads media by relative path, so it runs at full resolution
with no size ceiling. This is the one to present from.

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

## Talk lengths

Every slide carries a `data-min` budget and a `data-tier`. `C` cycles between
three paths, and the rail shows which is live and how long it runs:

| Path | Slides | Runs | Adds |
|------|--------|------|------|
| **essential** | 18 | ~44 min | The spine. Fits a 45-minute slot with questions. Default. |
| **full talk** | 32 | ~73 min | Proposition 1, the projection implementation, the speed table, the live loop, per-benchmark rollouts |
| **deep dive** | 37 | ~85 min | The Jensen-swap bound, the CBF comparison, the guidance α side-by-side, config 2 |

Slides outside the current path are skipped by the arrow keys but stay reachable
from the overview, so a deep-dive slide can be pulled up to answer a question.
Two appendix slides sit at the end of every path and are never timed.

To move a slide between paths, change its `data-tier` in `talk/deck.src.html`
and rebuild.

## Build

`talk/deck.src.html` is the single source. Media is referenced with
`{{M:<repo-relative path>}}` tokens, and `talk/build.py` emits two builds:

```bash
python3 talk/build.py            # both
python3 talk/build.py --local    # skip the slow embedded build
```

| Output | What it is |
|--------|------------|
| `talk/index.html` | Full document, media as relative paths. Present from this. |
| `talk/dist/cspi-talk.embed.html` | Body fragment with every asset inlined as a `data:` URI, for publishing as a shareable Artifact. |

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
- **The guidance frontier chart** — the `FRONTIER` array in the deck's script.
  Only the two ends of the α sweep are measured today; adding intermediate
  points from the supplementary is one line each, and they join the dashed path
  automatically if you set `sweep:true`.
- **The Proposition 1 figure** and the live CS-Pi loop are drawn in the same
  script block. The loop is ported from `js/hero.js`.

Styling follows the project page's tokens (`css/style.css`). The deck commits to
a single light theme on purpose: every figure, GIF and clip in it has a light
ground, so a dark inversion would frame all of them badly.
