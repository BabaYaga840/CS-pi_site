"""Temporally stabilise propagated masks (video_masks/<key>.npz -> video_masks/<key>_stable.npz).

Each frame's mask is re-decided by a weighted vote over a window of neighbouring frames, after warping the
neighbours' masks into the frame with dense optical flow (handles camera motion and moving parts). Small
disconnected specks and small holes are then removed. Prints a flicker score before/after
(mean fraction of mask pixels that change between consecutive frames after motion compensation).

usage: python3 stabilize_masks.py [key ...]
"""
import os, sys
import cv2, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from propagate_masks import JOBS

R = 8                       # window radius in frames
SIGMA = 4.0                 # temporal Gaussian sigma (frames)
WEIGHTS = {d: float(np.exp(-d * d / (2 * SIGMA ** 2))) for d in range(R + 1)}
FLOW_W = 480                # flow computed at this width
MIN_AREA = 0.002            # specks / holes smaller than this fraction of the frame are removed


def load(key):
    z = np.load(os.path.join(HERE, "video_masks", key + ".npz"))
    return np.unpackbits(z["packed"], axis=-1)[..., :int(z["shape"][2])].astype(bool)


def grays(path, n, W):
    cap = cv2.VideoCapture(path)
    out = []
    for _ in range(n):
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        out.append(cv2.resize(g, (W, int(g.shape[0] * W / g.shape[1])), interpolation=cv2.INTER_AREA))
    return out


def warp(mask_f, flow, size):
    """Sample mask_f (float, at flow res) at x + flow(x) -> mask aligned to the frame the flow starts from."""
    h, w = flow.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(mask_f, gx + flow[..., 0], gy + flow[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def flicker(masks, G, dis):
    s = []
    for t in range(1, len(masks)):
        a, b = masks[t], masks[t - 1]
        fl = dis.calc(G[t], G[t - 1], None)
        bw = warp(cv2.resize(b.astype(np.float32), (G[t].shape[1], G[t].shape[0]), interpolation=cv2.INTER_AREA), fl, None) > 0.5
        aa = cv2.resize(a.astype(np.uint8), (G[t].shape[1], G[t].shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        s.append((aa ^ bw).sum() / max((aa | bw).sum(), 1))
    return float(np.mean(s))


def clean(m):
    n = m.size
    for fg in (True, False):          # remove small foreground specks, then fill small holes
        x = (m if fg else ~m).astype(np.uint8)
        cnt, lab, st, _ = cv2.connectedComponentsWithStats(x, connectivity=8)
        small = np.isin(lab, [i for i in range(1, cnt) if st[i, cv2.CC_STAT_AREA] < MIN_AREA * n])
        m = m & ~small if fg else m | small
    return m


def run(key):
    vfile = JOBS[key][0]
    masks = load(key)
    T, H, W = masks.shape
    G = grays(os.path.join(HERE, "..", vfile), T, FLOW_W)
    h, w = G[0].shape
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    small = [cv2.resize(m.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA) for m in masks]
    print(f"[{key}] {T} frames, flicker before: {flicker(masks, G, dis):.4f}", flush=True)
    # one-step flows: Fn[t]: t -> t+1 (to pull frame t+1 data into t), Bn[t]: t -> t-1
    Fn = [dis.calc(G[t], G[t + 1], None) for t in range(T - 1)]
    Bn = [dis.calc(G[t], G[t - 1], None) for t in range(1, T)]
    score = [WEIGHTS[0] * small[t] for t in range(T)]
    tot = [WEIGHTS[0]] * T
    # A_k[t] = mask of frame t+k aligned to frame t, built by chaining single-step warps (incremental in k)
    for sign in (1, -1):
        cur = list(small)
        for d in range(1, R + 1):
            nxt = [None] * T
            for t in range(T):
                u = t + sign
                if 0 <= u < T and cur[u] is not None:
                    nxt[t] = warp(cur[u], Fn[t] if sign == 1 else Bn[t - 1], None)
                    score[t] = score[t] + WEIGHTS[d] * nxt[t]
                    tot[t] += WEIGHTS[d]
            cur = nxt
    out = np.zeros_like(masks)
    for t in range(T):
        vote = cv2.resize(score[t] / tot[t], (W, H), interpolation=cv2.INTER_LINEAR)
        out[t] = clean(vote > 0.5)
    print(f"[{key}] flicker after:  {flicker(out, G, dis):.4f}", flush=True)
    np.savez_compressed(os.path.join(HERE, "video_masks", key + "_stable.npz"), packed=np.packbits(out, axis=-1), shape=out.shape)


if __name__ == "__main__":
    for k in (sys.argv[1:] or [k for k in JOBS if os.path.exists(os.path.join(HERE, "video_masks", k + ".npz"))]):
        run(k)
