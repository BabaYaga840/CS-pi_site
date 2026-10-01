"""Merge waypoints, render coloured arrows, and collect the 9 final figures into ../final_figures."""
import json, os, shutil, subprocess

os.chdir(os.path.dirname(os.path.abspath(__file__)))
old = json.load(open("waypoints.json"))
new = json.load(open("waypoints_extra.json"))
m = {k: v for k, v in old.items() if k[:2] in ("2_", "3_", "5_")}
m.update(new)
m.update(json.load(open("waypoints_post.json")))
json.dump(m, open("waypoints_all.json", "w"), indent=1)
subprocess.run(["python3", "render_trajectories.py", "waypoints_all.json", "with_trajectories"], check=True)

os.makedirs("../final_figures", exist_ok=True)
mp = {"2_gradient_guidance_failure": "1_gradient_guidance",
      "7_projection_before": "2a_projection_before", "3_projection_failure": "2b_projection_after",
      "6_rejection_1": "3_rejection_1", "6_rejection_2": "3_rejection_2", "6_rejection_3": "3_rejection_3",
      "8_cspi_1": "4_cspi_1", "8_cspi_2": "4_cspi_2", "5_cspi": "4_cspi_3",
      "9_cspi_1_post": "5_cspi_1_post", "9_cspi_2_post": "5_cspi_2_post"}
for a, b in mp.items():
    shutil.copy(f"with_trajectories/{a}.png", f"../final_figures/{b}.png")
print(sorted(os.listdir("../final_figures")))
