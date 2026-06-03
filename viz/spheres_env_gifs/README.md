# Spheres environment — rollout GIFs

3D Panda obstacle-avoidance in the spheres environment, split by **distribution**.
Assembled from existing renders in `viz_out/{spheres,amr_vs_guidance,amr_vs_guidance_ood,sweep_smooth_gifs}`.

- **`in_distribution_EnvSpheres3D/`** — the 10-sphere env the prior was trained on.
- **`out_of_distribution_EnvSpheres3DExtraObjectsV00/`** — same 10 spheres + 6 extra
  obstacles, unseen at training (generalization test).

## File-name key

| Prefix | What the clip shows |
|---|---|
| `unguided_vs_amr_sampleNN` | side-by-side: **unguided** flow prior (left) vs **AMR-guided** (right) rollout |
| `amr_vs_guidance_sampleNN` | side-by-side: **AMR** vs **gradient-guidance** (α=0.5) on the same task |
| `amr_success_sampleNN` | AMR with a **good** config (k=10, mi=10, ss=0.5) — collision-free **success** |
| `amr_failure_sampleNN` | AMR with a **poor** config (k=0.5, mi=1, ss=0.5) — **failure** (still collides) |

`NN` is just an example index; samples are independent across prefixes.

## What's where

| Folder | unguided_vs_amr | amr_vs_guidance | amr_success | amr_failure |
|---|:--:|:--:|:--:|:--:|
| in_distribution_EnvSpheres3D | 3 | 2 | 5 | 5 |
| out_of_distribution_…ExtraObjectsV00 | 3 | 2 | — | — |

The explicit **success/failure** pair only exists for in-distribution AMR (from the
`sweep_smooth_gifs` good-vs-poor-config render). The `*_vs_*` clips are side-by-side
comparisons, not single-method success/fail clips. A guidance-success sweep dir
(`sweep_smooth_gifs/03_guidance_best_*`) exists but is **empty** — no guidance GIFs were
rendered, so there is no `guidance_success_*` here. Tell me if you want those rendered.

## Source mapping

| dest | source |
|---|---|
| `in_distribution_EnvSpheres3D/unguided_vs_amr_sampleNN.gif`  | `viz_out/spheres/comparison_EnvSpheres3D_NN.gif` |
| `in_distribution_EnvSpheres3D/amr_vs_guidance_sampleNN.gif`  | `viz_out/amr_vs_guidance/amr_vs_guidance_ID_NN.gif` |
| `in_distribution_EnvSpheres3D/amr_success_sampleNN.gif`      | `viz_out/sweep_smooth_gifs/01_amr_best_k10.0_mi10_ss0.50_successful/comparison_EnvSpheres3D_NN.gif` |
| `in_distribution_EnvSpheres3D/amr_failure_sampleNN.gif`      | `viz_out/sweep_smooth_gifs/02_amr_poor_k0.5_mi1_ss0.5_failures/comparison_EnvSpheres3D_NN.gif` |
| `out_of_distribution_…/unguided_vs_amr_sampleNN.gif`         | `viz_out/spheres/comparison_EnvSpheres3DExtraObjectsV00_NN.gif` |
| `out_of_distribution_…/amr_vs_guidance_sampleNN.gif`         | `viz_out/amr_vs_guidance_ood/amr_vs_guidance_OOD_NN.gif` |
