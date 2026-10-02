"""Translucent-background video for unguided.mp4 (141 s, 4239 frames, several hand-picked keyframe masks).

usage: python3 propagate_unguided.py prep | track | render

prep   -> video_masks/unguided_dec.mp4: every 4th frame at 1280x720 (all-intra) for SAM 2 tracking
track  -> tracks every 4th frame; each frame is tracked from its NEAREST keyframe (forward or backward), so drift
          never accumulates over more than half the gap between two keyframes. Chunked + resumable.
render -> full-rate video: each frame's mask is a motion-compensated (optical flow) weighted vote of the nearest
          tracked frames, so the 3 untracked frames in between are interpolated; written at 1080p.
"""
import os, subprocess, sys, time
import cv2, numpy as np
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from propagate_masks import split_objects, track_subprocess, CHUNK
from stabilize_masks import clean

SRC = os.path.join(HERE, "..", "unguided.mp4")
VM = os.path.join(HERE, "video_masks")
DEC = os.path.join(VM, "unguided_dec.mp4")
SPARSE = os.path.join(VM, "unguided_sparse.npz")
OUT = os.path.join(HERE, "..", "videos_translucent", "unguided_translucent.mp4")
KEYFRAMES = [0, 604, 1208, 1816, 2420, 3028, 3632, 4236]
STEP = 4
TW, TH = 1280, 720
BG_ALPHA = 0.45
SIGMA = 3.0        # temporal weighting (frames) of the tracked neighbours in the render vote
FLOW_W = 480


def keyframes():
    out = []
    for k in KEYFRAMES:
        f = os.path.join(HERE, "masks", f"unguided_f{k:04d}_mask.png")
        if os.path.exists(f):
            m = cv2.resize((cv2.imread(f, 0) > 127).astype(np.uint8), (TW, TH), interpolation=cv2.INTER_NEAREST) > 0
            out.append((k // STEP, m))
    return out


def prep():
    os.makedirs(VM, exist_ok=True)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", SRC, "-an",
                    "-vf", f"select='not(mod(n\\,{STEP}))',setpts=N/(30/{STEP})/TB,scale={TW}:{TH}", "-fps_mode", "passthrough",
                    "-c:v", "libx264", "-g", "1", "-crf", "14", "-pix_fmt", "yuv420p", DEC], check=True)
    c = cv2.VideoCapture(DEC)
    print("decimated frames:", int(c.get(cv2.CAP_PROP_FRAME_COUNT)))


def track():
    n = int(cv2.VideoCapture(DEC).get(cv2.CAP_PROP_FRAME_COUNT))
    kfs = keyframes()
    print(f"{n} tracked frames, {len(kfs)} keyframes {[k for k, _ in kfs]}", flush=True)
    sparse = np.zeros((n, TH, TW // 8), np.uint8)
    os.makedirs(os.path.join(VM, "cache"), exist_ok=True)
    t0 = time.time()

    def chunk(ki, rev, lo, hi, cur, seeds):
        cache = os.path.join(VM, "cache", f"unguided_{ki}_{'rev' if rev else 'fwd'}_{lo}_{hi}.npz")
        ids = sorted(seeds)
        if os.path.exists(cache):
            z = np.load(cache)
            m = np.unpackbits(z["packed"], axis=-1)[..., :TW].astype(bool)
            return {int(f): {int(o): m[k, j] for j, o in enumerate(z["ids"])} for k, f in enumerate(z["frames"])}
        res = track_subprocess(DEC, lo, hi, cur - lo, seeds, rev)
        fr = sorted(res)
        np.savez(cache, frames=np.array(fr), ids=np.array(ids),
                 packed=np.packbits(np.stack([np.stack([res[f][o] for o in ids]) for f in fr]), axis=-1))
        return res

    def run_range(ki, seeds, end, rev):
        cur = ki
        while (cur > end) if rev else (cur < end):
            lo, hi = (max(end, cur - CHUNK + 1), cur + 1) if rev else (cur, min(end + 1, cur + CHUNK))
            res = chunk(ki, rev, lo, hi, cur, seeds)
            for li, d in res.items():
                sparse[lo + li] = np.packbits(np.any(list(d.values()), axis=0), axis=-1)
            end_local = 0 if rev else hi - lo - 1
            nxt = res.get(end_local, {})
            seeds = {o: nxt[o] if o in nxt and nxt[o].any() else seeds[o] for o in seeds}
            cur = lo + end_local
            print(f"  kf {ki} {'rev' if rev else 'fwd'} {lo}-{hi} done ({time.time() - t0:.0f}s)", flush=True)

    for i, (ki, mask) in enumerate(kfs):
        right = (ki + kfs[i + 1][0]) // 2 if i + 1 < len(kfs) else n - 1
        left = (kfs[i - 1][0] + ki) // 2 + 1 if i > 0 else 0
        seeds = split_objects(mask)
        print(f"keyframe {ki * STEP}: {len(seeds)} objects, tracks tracked-frames {left}..{right}", flush=True)
        if right > ki:
            run_range(ki, seeds, right, False)
        if left < ki:
            run_range(ki, seeds, left, True)
        sparse[ki] = np.packbits(mask, axis=-1)          # the hand-picked mask itself at the keyframe
    np.savez_compressed(SPARSE, packed=sparse)
    print(f"saved sparse masks ({time.time() - t0:.0f}s)", flush=True)


def render():
    sparse = np.load(SPARSE)["packed"]
    n = len(sparse)
    cap = cv2.VideoCapture(SRC)
    T = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W, H = int(cap.get(3)), int(cap.get(4))
    fw, fh = FLOW_W, int(H * FLOW_W / W)
    print("reading grayscale frames for flow...", flush=True)
    G, frames_read = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        G.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (fw, fh), interpolation=cv2.INTER_AREA))
    T = len(G)
    cap = cv2.VideoCapture(SRC)
    fps = cap.get(cv2.CAP_PROP_FPS)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    gx, gy = np.meshgrid(np.arange(TW, dtype=np.float32), np.arange(TH, dtype=np.float32))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    ff = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "17",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    t0 = time.time()
    for t in range(T):
        ok, f = cap.read()
        if not ok:
            break
        a = t // STEP
        score, tot = np.zeros((TH, TW), np.float32), 0.0
        for idx in (a - 1, a, a + 1, a + 2):
            if not 0 <= idx < n or STEP * idx >= T:
                continue
            d = t - STEP * idx
            w = float(np.exp(-d * d / (2 * SIGMA ** 2)))
            m = np.unpackbits(sparse[idx], axis=-1)[:, :TW].astype(np.float32)
            if d != 0:
                fl = dis.calc(G[t], G[STEP * idx], None)
                fl = cv2.resize(fl, (TW, TH), interpolation=cv2.INTER_LINEAR) * (TW / fw)
                m = cv2.remap(m, gx + fl[..., 0], gy + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            score += w * m
            tot += w
        keep = clean(score / tot > 0.5)
        m = cv2.GaussianBlur(cv2.resize(keep.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR), (0, 0), 1.0)
        a_ = (m + (1 - m) * BG_ALPHA)[..., None]
        ff.stdin.write((f * a_ + 255 * (1 - a_)).astype(np.uint8).tobytes())
        if t % 300 == 0:
            print(f"  rendered {t}/{T} ({time.time() - t0:.0f}s)", flush=True)
    ff.stdin.close()
    ff.wait()
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    {"prep": prep, "track": track, "render": render}[sys.argv[1]]()
