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
# gradient stops (start ... current position) by output filename prefix
SCHEMES = {
    "2_": [rgb(255, 175, 175), rgb(215, 0, 0)],            # gradient guidance: light red -> red
    "3_": [LPURPLE, PURPLE],                               # projection: light purple -> purple
    "7_": [LPURPLE, PURPLE],
    "6_": [LGREEN, GREEN],                                 # rejection: light green -> green
    "8_": [PURPLE, LPURPLE, rgb(255, 255, 255), LGREEN, GREEN],  # CS-Pi: purple -> white -> green
    "9_": [PURPLE, LPURPLE, rgb(255, 255, 255), LGREEN, GREEN],
    "5_": [PURPLE, LPURPLE, rgb(255, 255, 255), LGREEN, GREEN],
}
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


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "waypoints.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "with_trajectories"
    os.makedirs(out, exist_ok=True)
    for name, v in json.load(open(src)).items():
        # old format: {file: [pts]}; new format: {file: {"image": base, "points": [pts]}}
        pts, base = (v["points"], v["image"]) if isinstance(v, dict) else (v, name)
        if len(pts) < 2:
            continue
        im = cv2.imread(base)
        big = cv2.resize(im, None, fx=SS, fy=SS, interpolation=cv2.INTER_CUBIC)
        stops = next((v for k, v in SCHEMES.items() if name.startswith(k)), SCHEMES["2_"])
        draw_arrow(big, pts, W=20 * im.shape[1] / 720, stops=stops, border=BORDER.get(name),
                   bw=3.0 * im.shape[1] / 720)
        cv2.imwrite(os.path.join(out, name),
                    cv2.resize(big, (im.shape[1], im.shape[0]), interpolation=cv2.INTER_AREA))
        print("wrote", os.path.join(out, name))


if __name__ == "__main__":
    main()
