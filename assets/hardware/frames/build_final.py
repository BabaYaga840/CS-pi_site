"""usage: python3 build_final.py [masked|transparent]   (masked -> white background, transparent -> alpha background)
Merge waypoints, render coloured arrows, and collect the 9 final figures into ../final_figures."""
import json, os, shutil, subprocess, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
old = json.load(open("waypoints.json"))
new = json.load(open("waypoints_extra.json"))
m = {k: v for k, v in old.items() if k[:2] in ("2_", "3_", "5_")}
m.update(new)
m.update(json.load(open("waypoints_post.json")))
json.dump(m, open("waypoints_all.json", "w"), indent=1)
MODE = "transparent" if "transparent" in sys.argv[1:] else "masked" if "masked" in sys.argv[1:] else ""
WT = {"": "with_trajectories", "masked": "with_trajectories_masked", "transparent": "with_trajectories_transparent"}[MODE]
OUT = {"": "../final_figures", "masked": "../final_figures_masked", "transparent": "../final_figures_transparent"}[MODE]
extra = {"": [], "masked": ["masked"], "transparent": [".", "transparent"]}[MODE]
subprocess.run(["python3", "render_trajectories.py", "waypoints_all.json", WT] + extra, check=True)

os.makedirs(OUT, exist_ok=True)
mp = {"2_gradient_guidance_failure": "1_gradient_guidance",
      "7_projection_before": "2a_projection_before", "3_projection_failure": "2b_projection_after",
      "6_rejection_1": "3_rejection_1", "6_rejection_2": "3_rejection_2", "6_rejection_3": "3_rejection_3",
      "8_cspi_1": "4_cspi_1", "8_cspi_2": "4_cspi_2", "5_cspi": "4_cspi_3",
      "9_cspi_1_post": "5_cspi_1_post", "9_cspi_2_post": "5_cspi_2_post"}
for a, b in mp.items():
    shutil.copy(f"{WT}/{a}.png", f"{OUT}/{b}.png")
print(sorted(os.listdir(OUT)))
