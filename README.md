# CS-Pi project page

Static project page for **CS-Pi: Constraint-Satisfying Flow Policy Sampling**
(CoRL 2026). No build step, no dependencies: plain HTML, CSS, and
vanilla JS, hosted on GitHub Pages.

## What is here

| Path | What it is |
|------|------------|
| `index.html` | The page. All section containers; scripts at the bottom. |
| `css/style.css` | All styling. |
| `js/data.js` | **Edit this for content**: title, authors, links, method blurbs, scenario descriptions, result tables. |
| `js/hero.js` | The animated CS-Pi loop on the landing canvas (draw → project → renoise → re-run). |
| `js/explorer.js` | Builds the headline stats, method cards, head-to-head face-off, interactive scenario × method explorer, result tables, hardware strips, and BibTeX. |
| `js/gif_manifest.js` | **Auto-generated** by `tools/build_manifest.py`. Do not edit by hand. |
| `tools/build_manifest.py` | Scans `viz/` for rollout GIFs, extracts a first-frame poster per GIF, and writes `js/gif_manifest.js`. |
| `viz/<task>_scenario_method_gifs/<scenario>/<method>__<outcome>.gif` | The rollout GIFs. |
| `assets/` | Paper figures (`concept.png`, `method.png`), hardware filmstrips, and the generated `posters/`. |

## Run locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

(Opening `index.html` via `file://` works too, but a local server avoids any
path quirks.)

## Add GIFs for a new task or scenario

Two layouts are supported. After dropping in GIFs, regenerate the manifest and
posters with `python3 tools/build_manifest.py`.

**1. Scenario-major, with success/fail (the shelf task).** Auto-discovered from
any `*_scenario_method_gifs` folder:

```
viz/<task>_scenario_method_gifs/<scenario>/<method>__<outcome>.gif
```
- `<outcome>` ∈ `success`, `fail`. A missing cell is meaningful: a method that is
  always safe in a scenario has no `__fail`; one that never succeeds has no
  `__success`. The explorer explains each absence automatically.
- Set `outcomes: true` and `methods: [...]` for the task in `js/data.js`.

**2. Method-major, single rollout (the 3D-Orient task).** One GIF per method per
scenario, no success/fail split. Folder layout `viz/<dir>/<method-folder>/<scenario>.gif`.
Register it in `tools/build_manifest.py` under `SINGLE_OUTCOME_TASKS` (maps each
site method key to its source folder), and set `outcomes: false` for the task in
`js/data.js`. Each scenario may carry a `note` (rendered as an amber callout, used
for the Config 2 "infeasible under the constraint" explanation).

In both cases the task's method buttons come from its `methods` list in
`js/data.js`, and method labels/colors/blurbs come from the `METHODS` registry
there. The `2d` task is still a placeholder (`available: false`); set it true and
add its scenarios once its GIFs land.

## Authors, venue, links

`js/data.js` → `SITE.authors` (comma-separated; also feeds the BibTeX), `SITE.affiliation`, `SITE.venue`, and the
`SITE.links` block. One edit, nothing else changes.

## Deploy on GitHub Pages

1. Push to your remote (`git push -u origin main`).
2. Repo → Settings → Pages → Source: `Deploy from a branch`, branch `main`, folder `/ (root)`.
3. The page serves at `https://<account>.github.io/<repo>/`.

`.nojekyll` is included so GitHub Pages serves the `js/`, `viz/`, and
`assets/posters/` paths verbatim.
