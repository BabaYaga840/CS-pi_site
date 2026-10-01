"""Render smooth light-red -> red gradient arrows from waypoints.json onto the frames.

usage: python3 render_trajectories.py [waypoints.json] [out_dir]
"""
import json, sys, os
import numpy as np, cv2

SS = 4                      # supersampling for anti-aliasing
def rgb(r, g, b):
    return np.array([b, g, r], float)   # stored as BGR for OpenCV


PURPLE, LPURPLE = rgb(120, 0, 170), rgb(205, 170, 235)
GREEN, LGREEN = rgb(0, 150, 40), rgb(170, 235, 170)
# gradient stops (start ... current position): light red -> red for every figure
RED = [rgb(255, 175, 175), rgb(215, 0, 0)]
SCHEMES = {k: RED for k in ("2_", "3_", "5_", "6_", "7_", "8_", "9_")}
# figures that get an outline around the arrow
BORDER = {"3_projection_failure.png": PURPLE, "9_cspi_1_post.png": PURPLE, "9_cspi_2_post.png": PURPLE}


def grad(stops, t):
    x = t * (len(stops) - 1)
    i = min(int(x), len(stops) - 2)
    return stops[i] + (stops[i + 1] - stops[i]) * (x - i)


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


def draw_arrow(img, pts, W=13, stops=SCHEMES["2_"], border=None, bw=3.0):
    s = smooth(pts) * SS
    W *= SS
    L = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]
    tot = L[-1]
    head = min(W * 2.6, tot * 0.4)
    e = s[-1]
    far = s[np.hypot(*(s - e).T) > head * 0.6]
    q = far[-1] if len(far) else s[0]
    d = (e - q) / (np.hypot(*(e - q)) + 1e-9)
    n = np.array([-d[1], d[0]])
    tri = np.array([e + d * head * .35, e - d * head * .65 + n * W * 1.5,
                    e - d * head * .65 - n * W * 1.5])
    body = [i for i in range(1, len(s)) if L[i] <= tot - head + 1]

    if border is not None:      # outline pass underneath the fill
        B2 = int(bw * W / 20 * 2)
        for i in body:
            cv2.line(img, tuple(s[i-1].astype(int)), tuple(s[i].astype(int)),
                     tuple(int(v) for v in border), int(W) + B2, cv2.LINE_AA)
            cv2.circle(img, tuple(s[i].astype(int)), (int(W) + B2) // 2, tuple(int(v) for v in border), -1, cv2.LINE_AA)
        cv2.fillConvexPoly(img, tri.astype(np.int32), tuple(int(v) for v in border), cv2.LINE_AA)
        cv2.polylines(img, [tri.astype(np.int32)], True, tuple(int(v) for v in border), B2, cv2.LINE_AA)

    for i in body:
        c = grad(stops, L[i] / tot)
        cv2.line(img, tuple(s[i-1].astype(int)), tuple(s[i].astype(int)),
                 tuple(int(v) for v in c), int(W), cv2.LINE_AA)
    cv2.fillConvexPoly(img, tri.astype(np.int32), tuple(int(v) for v in stops[-1]), cv2.LINE_AA)


def arrow_layer(shape, pts, **kw):
    """Arrow-only RGBA layer (float, straight alpha), recovered exactly from white/black renders."""
    h, w = shape
    out = []
    for bg in (255, 0):
        big = np.full((h * SS, w * SS, 3), bg, np.uint8)
        draw_arrow(big, pts, **kw)
        out.append(cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32))
    on_white, on_black = out
    alpha = np.clip(1 - (on_white - on_black).mean(axis=2) / 255, 0, 1)
    color = np.where(alpha[..., None] > 1e-4, on_black / np.maximum(alpha[..., None], 1e-4), 0)
    return np.clip(color, 0, 255), alpha


def render_transparent(im, mask, pts, **kw):
    """Source frame with everything outside `mask` transparent, arrows on top, as BGRA uint8."""
    h, w = im.shape[:2]
    a_b = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.8)
    c_a, a_a = arrow_layer((h, w), pts, **kw)
    a_o = a_a + a_b * (1 - a_a)
    rgb = (c_a * a_a[..., None] + im.astype(np.float32) * (a_b * (1 - a_a))[..., None]) / np.maximum(a_o[..., None], 1e-4)
    return np.dstack([np.clip(rgb, 0, 255), a_o * 255]).round().astype(np.uint8)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "waypoints.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "with_trajectories"
    base_dir = sys.argv[3] if len(sys.argv) > 3 else "."
    transparent = len(sys.argv) > 4 and sys.argv[4] == "transparent"
    os.makedirs(out, exist_ok=True)
    for name, v in json.load(open(src)).items():
        # old format: {file: [pts]}; new format: {file: {"image": base, "points": [pts]}}
        pts, base = (v["points"], v["image"]) if isinstance(v, dict) else (v, name)
        if len(pts) < 2:
            continue
        im = cv2.imread(os.path.join(base_dir, base))
        stops = next((v for k, v in SCHEMES.items() if name.startswith(k)), SCHEMES["2_"])
        kw = dict(W=20 * im.shape[1] / 720, stops=stops, border=BORDER.get(name), bw=10.0 * im.shape[1] / 720)
        if transparent:         # mask comes from masks/<base stem>_mask.png; source pixels from the original frame
            mask = cv2.imread(os.path.join("masks", os.path.splitext(base)[0] + "_mask.png"), 0) > 127
            res = render_transparent(cv2.imread(base), mask, pts, **kw)
        else:
            big = cv2.resize(im, None, fx=SS, fy=SS, interpolation=cv2.INTER_CUBIC)
            draw_arrow(big, pts, **kw)
            res = cv2.resize(big, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(out, name), res)
        print("wrote", os.path.join(out, name))


if __name__ == "__main__":
    main()
