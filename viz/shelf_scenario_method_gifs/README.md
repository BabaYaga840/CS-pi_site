# Shelf pick-and-place — scenario × method GIFs

Rollout GIFs for the shelf pick-and-place comparison, organized by scenario and
method, with a `__success` and/or `__fail` example per cell. Assembled from the
existing renders in `viz_out/{mm_safe_only,mm_fail_only,lk_safe,lk_fail}`.

- **Methods**: `amr`, `projection` (ODE + final-projection only), `tweedie`
  (gradient guidance, low-knob α=0.2), `trust` (trust sampling, low-knob
  ts_w=0.005, j=5).
- **Scenarios**: `clutter_combo`, `tall_table_pillar`, `two_flankers_top`,
  `mid_rung_neighbor_E`, `low_rung_neighbor_E` (see SHELF_METHOD_COMPARISON.md §2).
- **success / fail** = the `safe-SR` metric: collision-free AND pick succeeds AND
  place succeeds.

## Availability grid (✓ = GIF present)

| Scenario | amr ✓succ | proj ✓succ | proj ✗fail | tweedie ✓succ | tweedie ✗fail | trust ✓succ | trust ✗fail |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| clutter_combo        | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| tall_table_pillar    | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| two_flankers_top     | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| mid_rung_neighbor_E  | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| low_rung_neighbor_E  | ✓ | ✓ | — | — | ✓ | — | ✓ |

## Meaningful absences (not missing files)

- **No `amr__fail` anywhere** — AMR is 100% safe on all 5 scenarios, so no
  failure rollout exists.
- **No `projection__fail` on low_rung_neighbor_E** — projection is 100% safe
  there; only a success exists.
- **No `tweedie__success` / `trust__success` on low_rung_neighbor_E**, and no
  **`trust__success` on mid_rung_neighbor_E** — these methods score 0% safe in
  those cells, so no success rollout exists (only failures).

## Source mapping

| dest | source |
|---|---|
| `<scn>/amr__success.gif`        | `viz_out/mm_safe_only/<scn>__amr.gif` |
| `<scn>/projection__success.gif` | `viz_out/mm_safe_only/<scn>__projection.gif` |
| `<scn>/projection__fail.gif`    | `viz_out/mm_fail_only/<scn>__projection.gif` |
| `<scn>/tweedie__success.gif`    | `viz_out/lk_safe/<scn>__tw_a02.gif` |
| `<scn>/tweedie__fail.gif`       | `viz_out/lk_fail/<scn>__tw_a02.gif` |
| `<scn>/trust__success.gif`      | `viz_out/lk_safe/<scn>__tr_w0005_j5.gif` |
| `<scn>/trust__fail.gif`         | `viz_out/lk_fail/<scn>__tr_w0005_j5.gif` |
