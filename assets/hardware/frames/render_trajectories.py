"""Render smooth light-red -> red gradient arrows from waypoints.json onto the frames.

usage: python3 render_trajectories.py [waypoints.json] [out_dir]
"""
import json, sys, os
import numpy as np, cv2

SS = 4                      # supersampling for anti-aliasing
A = np.array([175, 175, 255], float)   # light red (BGR)
B = np.array([0, 0, 215], float)       # red (BGR)


def catmull(p, n=40):
    p = np.asarray(p, float)
    if len(p) < 2:
        return p
    P = np.vstack([p[0], p, p[-1]])
    out = []
    for i in range(1, len(P) - 2):
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * (2 * P[i] + (-P[i-1] + P[i+1]) * t
                          + (2*P[i-1] - 5*P[i] + 4*P[i+1] - P[i+2]) * t**2
                          + (-P[i-1] + 3*P[i] - 3*P[i+1] + P[i+2]) * t**3))
    out.append(p[-1:])
    return np.vstack(out)


def smooth(p, frac=0.12, n=400):
    """Resample evenly by arc length, then Gaussian-smooth with endpoints pinned."""
    p = catmull(p)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    t = np.linspace(0, d[-1], n)
    q = np.c_[np.interp(t, d, p[:, 0]), np.interp(t, d, p[:, 1])]
    sig = frac * n
    k = np.arange(-int(3 * sig), int(3 * sig) + 1)
    k = np.exp(-k**2 / (2 * sig**2)); k /= k.sum()
    m = len(k) // 2
    # point-reflect about the endpoints so the ends (and tangents) are preserved
    pad = np.vstack([2 * q[0] - q[1:m+1][::-1], q, 2 * q[-1] - q[-m-1:-1][::-1]])
    out = np.c_[np.convolve(pad[:, 0], k, "valid"), np.convolve(pad[:, 1], k, "valid")]
    out[0], out[-1] = q[0], q[-1]
    return out


def draw_arrow(img, pts, W=13):
    s = smooth(pts) * SS
    W *= SS
    L = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]
    tot = L[-1]
    head = min(W * 2.6, tot * 0.4)
    for i in range(1, len(s)):
        if L[i] > tot - head + 1:
            break
        c = A + (B - A) * (L[i] / tot)
        cv2.line(img, tuple(s[i-1].astype(int)), tuple(s[i].astype(int)),
                 tuple(int(v) for v in c), int(W), cv2.LINE_AA)
    e = s[-1]
    far = s[np.hypot(*(s - e).T) > head * 0.6]
    q = far[-1] if len(far) else s[0]
    d = (e - q) / (np.hypot(*(e - q)) + 1e-9)
    n = np.array([-d[1], d[0]])
    tri = np.array([e + d * head * .35, e - d * head * .65 + n * W * 1.5,
                    e - d * head * .65 - n * W * 1.5]).astype(np.int32)
    cv2.fillConvexPoly(img, tri, tuple(int(v) for v in B), cv2.LINE_AA)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "waypoints.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "with_trajectories"
    os.makedirs(out, exist_ok=True)
    for name, pts in json.load(open(src)).items():
        if len(pts) < 2:
            continue
        im = cv2.imread(name)
        big = cv2.resize(im, None, fx=SS, fy=SS, interpolation=cv2.INTER_CUBIC)
        draw_arrow(big, pts)
        cv2.imwrite(os.path.join(out, name),
                    cv2.resize(big, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_AREA))
        print("wrote", os.path.join(out, name))


if __name__ == "__main__":
    main()
