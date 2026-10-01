"""Render translucent-background videos from propagated masks.

usage: python3 render_translucent_video.py [key ...]     (default: every key with video_masks/<key>.npz)
Writes ../videos_translucent/<video stem>_translucent.mp4: the picked segments at full strength, the rest
at BG_ALPHA opacity over white (mp4 has no alpha channel).
"""
import os, subprocess, sys
import cv2, numpy as np
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from propagate_masks import JOBS

BG_ALPHA = 0.3
OUT = os.path.join(HERE, "..", "videos_translucent")


def render(key):
    vfile = JOBS[key][0]
    z = np.load(os.path.join(HERE, "video_masks", key + ".npz"))
    masks = np.unpackbits(z["packed"], axis=-1)[..., :int(z["shape"][2])].astype(bool)
    cap = cv2.VideoCapture(os.path.join(HERE, "..", vfile))
    fps = cap.get(cv2.CAP_PROP_FPS)
    W, H = int(cap.get(3)), int(cap.get(4))
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, os.path.splitext(vfile)[0] + "_translucent.mp4")
    ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "16",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for t in range(len(masks)):
        ok, f = cap.read()
        if not ok:
            break
        m = cv2.GaussianBlur(masks[t].astype(np.float32), (0, 0), 0.8)
        a = (m + (1 - m) * BG_ALPHA)[..., None]
        ff.stdin.write((f * a + 255 * (1 - a)).astype(np.uint8).tobytes())
    ff.stdin.close()
    ff.wait()
    print("wrote", out, f"({len(masks)} frames, {fps:.0f} fps)")


if __name__ == "__main__":
    keys = sys.argv[1:] or [k for k in JOBS if os.path.exists(os.path.join(HERE, "video_masks", k + ".npz"))]
    for k in keys:
        render(k)
