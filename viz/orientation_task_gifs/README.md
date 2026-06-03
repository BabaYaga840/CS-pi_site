# Orient-Track (MPD-9) — method-comparison GIFs

3D Panda **reach-and-orient** task: each executed step must be within **10 cm** of the
target position **and** within **0.5 Frobenius** of the target EE orientation (`sim_10/.5`).
The orientation lock is **out-of-distribution for the prior** (trained on RRTConnect joint
paths with no orientation constraint), so it is enforced by the inference-time method only.

Organized **by method** (one folder each); each folder holds the same 5 validation tasks
(`task28, 31, 39, 43, 47`), so you can compare a method across tasks, or one task across
methods. Each frame is annotated with the live **EE distance** and **orientation error**.
Assembled from `viz_out/method_comparison_mpd9/`.

## Methods (folder → what it is)

| Folder | Method | Config |
|---|---|---|
| `unguided/`              | flow prior alone (no orientation enforcement) | — |
| `amr_joint_prox/`        | AMR with joint-space proximal projection | k, mi defaults |
| `amr_eeprox_dynamic/`    | AMR + EE-orientation proximal term, target re-evaluated each step | dynamic ref |
| `amr_eeprox_frozen_ref/` | AMR + EE-orientation proximal term, target frozen at plan start | frozen ref |
| `tweedie_alpha0.003/`    | gradient guidance on the Tweedie estimate, weak knob | α=0.003, JL=100 |
| `tweedie_alpha0.03/`     | gradient guidance, stronger knob | α=0.03, JL=100 |
| `trust_w0.001/`          | trust sampling (per-step inner GD) | ts_w=0.001, JL=100 |

## How the methods do (aggregate, 90 rollouts/cell — `DELTA_LOGL_ALL_ENVS.md` §3)

Success = reach-and-orient (`sim_10/.5`). **AMR + EE-prox is the only method that does the
task**; the gradient methods mostly fail to orient, and unguided/trust essentially never do.

| Method | n success | note |
|---|---|---|
| **AMR + EE-prox** | **62/90** | only method that reliably orients (pays in log-likelihood: off-manifold by construction) |
| Tweedie α=0.03 | 8/90 | stronger push orients occasionally, far off-manifold |
| Tweedie α=0.003 | 3/90 | weak push rarely orients |
| Unguided | 1/90 | ~never orients (orientation-agnostic prior) |
| Trust w=0.001 | 1/90 | stays on-manifold by **not** orienting |

So treat `amr_eeprox_*` clips as the "success" story and `unguided` / `trust` / weak
`tweedie` clips as the "failure-to-orient" story. **Per-task success is not encoded in the
filenames** — read it off each clip's on-frame EE-distance / orientation-error annotation
(no per-task success file was saved for these 5 tasks). Ask if you want the filenames
relabeled `__success` / `__fail` per task; that needs a short re-run to score each rollout.

## Source mapping

`<method-folder>/taskN.gif`  ←  `viz_out/method_comparison_mpd9/<SRC>/<SRC>_taskN.gif`
where `<SRC>` ∈ {`unguided`, `AMR_joint_prox`, `AMR_eeprox_dynamic`, `AMR_frozen_ref`,
`tweedie_a003_jl100`, `tweedie_a03_jl100`, `trust_w001_jl100`}.
