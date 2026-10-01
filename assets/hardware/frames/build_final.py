"""usage: python3 build_final.py [masked|transparent|translucent]   (white / fully transparent / faint 30% background)
Merge waypoints, render coloured arrows, and collect the 9 final figures into ../final_figures."""
import json, os, shutil, subprocess, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
old = json.load(open("waypoints.json"))
new = json.load(open("waypoints_extra.json"))
m = {k: v for k, v in old.items() if k[:2] in ("2_", "3_", "5_")}
m.update(new)
m.update(json.load(open("waypoints_post.json")))
json.dump(m, open("waypoints_all.json", "w"), indent=1)
MODE = next((m for m in ("translucent", "transparent", "masked") if m in sys.argv[1:]), "")
SUFFIX = "_translucent" if MODE == "translucent" else ""
BG_ALPHA = "0.3"
WT = {"": "with_trajectories", "masked": "with_trajectories_masked", "transparent": "with_trajectories_transparent", "translucent": "with_trajectories_translucent"}[MODE]
OUT = {"": "../final_figures", "masked": "../final_figures_masked", "transparent": "../final_figures_transparent", "translucent": "../final_figures_translucent"}[MODE]
extra = {"": [], "masked": ["masked"], "transparent": [".", "transparent"], "translucent": [".", "transparent", BG_ALPHA]}[MODE]
subprocess.run(["python3", "render_trajectories.py", "waypoints_all.json", WT] + extra, check=True)

os.makedirs(OUT, exist_ok=True)
mp = {"2_gradient_guidance_failure": "1_gradient_guidance",
      "7_projection_before": "2a_projection_before", "3_projection_failure": "2b_projection_after",
      "6_rejection_1": "3_rejection_1", "6_rejection_2": "3_rejection_2", "6_rejection_3": "3_rejection_3",
      "8_cspi_1": "4_cspi_1", "8_cspi_2": "4_cspi_2", "5_cspi": "4_cspi_3",
      "9_cspi_1_post": "5_cspi_1_post", "9_cspi_2_post": "5_cspi_2_post"}
for a, b in mp.items():
    shutil.copy(f"{WT}/{a}.png", f"{OUT}/{b}{SUFFIX}.png")
print(sorted(os.listdir(OUT)))
