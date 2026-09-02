#!/usr/bin/env python3
"""Colour-grade the Franka clips and lift the robot, apple and plate off the background.

Reads  assets/hardware/<name>.mp4  and writes  assets/hardware/graded/<name>.mp4.

Per frame the clip is split into three layers:

  foreground  the arm, the apple and the plate, at full colour and boosted saturation
  obstacles   tinted red so the audience can see what the constraint is
  background  everything else: desaturated, washed toward white and lightly blurred

The arm mask is the union of three cheap tests plus one learned one:
  * bright, unsaturated pixels above the table (white arm on a black curtain)
  * dark pixels on the table top (the black gripper, joints and cable)
  * a SlimSAM mask, prompted by CLIPSeg peaks for "a white robot arm", but only
    trusted inside the table region and never inside the wipes canisters or cups
  * a static box over the robot base, moved with the camera
The apple and plate are found by colour.  The two canister band is tracked from
the yellow Lysol label; in the two hand-held clips every other static shape is
moved with a per-frame shift and zoom fitted to the plate, the one landmark on
the table plane that never moves.

Which objects count as obstacles is per layout (see CLIPS): the cups and bowl in
layout 1, the two canisters in layout 2.

    python3 tools/grade_hardware_clips.py              # all four clips
    python3 tools/grade_hardware_clips.py --preview    # contact sheets only, to tools/.preview/
    python3 tools/grade_hardware_clips.py cspi_success_0
    python3 tools/grade_hardware_clips.py --force      # recompute masks (else tools/.cache is reused)

Needs numpy, Pillow, opencv-python-headless, imageio-ffmpeg, torch, transformers
(the two models download on first run: CIDAS/clipseg-rd64-refined and
Zigeng/SlimSAM-uniform-77).  ~0.7 s per frame on an M-series CPU.
"""
import os
import sys
import warnings

import cv2
import numpy as np
from PIL import Image, ImageFilter

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "hardware")
DST = os.path.join(SRC, "graded")
CACHE = os.path.join(ROOT, "tools", ".cache")     # per-frame masks, so a new look renders in seconds
FORCE = False
W, H = 720, 406

# ---- per-clip geometry, in first-frame pixels --------------------------------
#   table       polygon over the table top
#   base        box over the robot base
#   cups        boxes over the cups and bowl at the back of the table
#   wall        other bright background to ignore (walls, rack hardware)
#   can_bottom  y of the bottom of the canister stack (its x range is tracked)
#   obstacle    "cups" (layout 1) or "cans" (layout 2)
#   moving      hand-held clip: move the static geometry with the camera
CLIPS = {
    "cspi_success_0":    dict(table=[(150, 148), (450, 145), (720, 170), (720, 406), (50, 406), (95, 300), (100, 200)],
                              base=(390, 85, 470, 165), cups=[(490, 30, 710, 160)],
                              wall=[(690, 0, 720, 240), (0, 140, 95, 406)], can_bottom=250, obstacle="cups", moving=True),
    "project_fail":      dict(table=[(140, 185), (500, 165), (720, 145), (720, 406), (100, 406), (118, 300)],
                              base=(345, 80, 460, 150), cups=[(490, 25, 700, 160)],
                              wall=[(690, 0, 720, 240), (0, 170, 110, 406)], can_bottom=260, obstacle="cups", moving=False),
    "gradient_guidance": dict(table=[(0, 270), (615, 270), (700, 406), (0, 406)],
                              base=(250, 170, 365, 240), cups=[(505, 70, 620, 265)],
                              wall=[(540, 0, 720, 80), (615, 80, 720, 406)], can_bottom=330, obstacle="cans", moving=False),
    "trust_fail":        dict(table=[(120, 225), (720, 215), (720, 406), (140, 406), (115, 300), (105, 255)],
                              base=(325, 140, 445, 212), cups=[(480, 35, 700, 225)],
                              wall=[(600, 0, 720, 230), (0, 200, 100, 406)], can_bottom=325, obstacle="cans", moving=True),
}

# ---- the look ------------------------------------------------------------------
TABLE_TARGET = 236.0   # the table top is white-balanced and lifted to this grey
MAX_GAIN = 1.28
CONTRAST = 1.08
SAT_FG = 1.45          # foreground saturation
BG_SAT = 0.45          # background keeps this much saturation ...
BG_WASH = 0.42         # ... and is blended this far toward white
BG_BLUR = 0.0          # optional softening of the background (0 = off)
HALO = 17              # the arm is lit by a soft spotlight this much wider than its mask ...
HALO_BLUR = 9          # ... with this feather, so mask ragged edges never show
TINT = np.array([225.0, 45.0, 45.0], np.float32)
TINT_T = 0.42          # obstacle blend toward TINT
EDGE_T = 0.85          # ... and a thin outline in the same colour
FEATHER = 5
MIN_BLOB = 160         # px; smaller mask fragments are dropped


# ---- small helpers ---------------------------------------------------------------
def boxmask(box, val=1.0):
    m = np.zeros((H, W), np.float32)
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    m[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = val
    return m


def dil(m, k):
    return cv2.dilate(np.clip(m, 0, 1).astype(np.float32), np.ones((k, k), np.uint8))


def ero(m, k):
    return cv2.erode(np.clip(m, 0, 1).astype(np.float32), np.ones((k, k), np.uint8))


def blur(m, sigma):
    return cv2.GaussianBlur(np.clip(m, 0, 1).astype(np.float32), (0, 0), sigma)


def feather(m):
    return blur(m, FEATHER)


def drop_small(mask01, min_px=MIN_BLOB):
    n, lab, stats, _ = cv2.connectedComponentsWithStats((mask01 > 0.5).astype(np.uint8), 8)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_px
    return keep[lab].astype(np.float32)


def drop_strips(mask01):
    """Remove long thin horizontal fragments (a sliver of table edge is never a robot)."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats((mask01 > 0.5).astype(np.uint8), 8)
    keep = np.ones(n, bool)
    for i in range(1, n):
        bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if bh < 24 and bw > 5 * bh:
            keep[i] = False
    keep[0] = False
    return keep[lab].astype(np.float32)


def largest(mask01, min_px=1):
    n, lab, stats, cent = cv2.connectedComponentsWithStats((mask01 > 0.5).astype(np.uint8), 8)
    if n < 2:
        return None, None
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[i, cv2.CC_STAT_AREA] < min_px:
        return None, None
    return (lab == i).astype(np.float32), cent[i]


def warp_box(box, M):
    x0, y0, x1, y1 = box
    pts = np.array([[x0, y0], [x1, y0], [x0, y1], [x1, y1]], np.float32)
    q = cv2.transform(pts[None], M)[0]
    return (q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max())


def polymask(poly, M=None):
    pts = np.array(poly, np.float32)
    if M is not None:
        pts = cv2.transform(pts[None], M)[0]
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1)
    return m.astype(np.float32)


def fill_hull(mask01, min_px):
    blob, _ = largest(mask01, min_px)
    if blob is None:
        return np.zeros((H, W), np.float32)
    pts = np.column_stack(np.where(blob > 0.5)[::-1]).astype(np.int32)
    m = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(m, cv2.convexHull(pts), 1)
    return m.astype(np.float32)


def yellow_bbox(f):
    blob, _ = largest(yellow_mask(f).astype(np.float32), 300)
    if blob is None:
        return None
    ys, xs = np.where(blob > 0.5)
    return [xs.min(), ys.min(), xs.max(), ys.max()]


def centroid(mask):
    ys, xs = np.where(mask)
    if len(xs) < 30:
        return None
    return (float(xs.mean()), float(ys.mean()))


# ---- pixel tests --------------------------------------------------------------------
def channels(f):
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    gray = 0.299 * r + 0.587 * g + 0.114 * b
    chroma = f.max(-1) - f.min(-1)
    return r, g, b, gray, chroma


def yellow_mask(f):
    r, g, b, _, _ = channels(f)
    return (r > 140) & (g > 130) & (b < 100) & (r - b > 80)


def apple_mask(f):
    r, g, b, _, _ = channels(f)
    return (r - g > 28) & (r - b > 30) & (r > 80)


def plate_mask(f):
    r, g, b, _, chroma = channels(f)
    return (r > 140) & (g - r > 4) & (b - r > 0) & (chroma < 60)


def table_hull(f):
    """Filled convex hull of the largest bright, unsaturated blob in the lower frame."""
    _, _, _, gray, chroma = channels(f)
    cand = ((gray > 165) & (chroma < 40)).astype(np.uint8)
    cand[: int(H * 0.30)] = 0
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(cand, 8)
    if n < 2:
        return np.zeros((H, W), np.float32)
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    pts = np.column_stack(np.where(lab == i)[::-1]).astype(np.int32)
    hull = cv2.convexHull(pts)
    m = np.zeros((H, W), np.uint8)
    cv2.fillConvexPoly(m, hull, 1)
    return m.astype(np.float32)


def table_auto(f):
    """The table top found per frame, for the hand-held clips: bright, unsaturated
    pixels within reach of a core that survives a 101 px opening (the arm, the
    plate rim and the canisters do not).  Small holes (shadows, the apple) are closed."""
    _, _, _, gray, chroma = channels(f)
    cand = ((gray > 150) & (chroma < 45)).astype(np.uint8)
    cand[: int(H * 0.25)] = 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (101, 101))
    core = cv2.morphologyEx(cand, cv2.MORPH_OPEN, k)
    reach = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (121, 121)))
    t = (cand & reach).astype(np.float32)
    return ero(dil(t, 25), 25)


# ---- pass 1: camera motion and canister position ----------------------------------------
def smooth(a, k):
    """Running median over +-k rows, ignoring rows with NaNs."""
    out = a.copy()
    for i in range(len(a)):
        w = a[max(0, i - k): i + k + 1]
        w = w[~np.isnan(w).any(axis=-1)]
        if len(w):
            out[i] = np.median(w, axis=0)
    return out


def fill_nan(a, default):
    good = ~np.isnan(a).any(axis=-1)
    if not good.any():
        a[:] = default
        return a
    first = np.argmax(good)
    a[:first] = a[first]
    for i in range(first + 1, len(a)):
        if not good[i]:
            a[i] = a[i - 1]
    return a


def coarse_plate(f, cfg):
    """Plate centre and area from colour alone, ignoring the cups region."""
    m = plate_mask(f).astype(np.float32)
    for bx in cfg["cups"]:
        m *= 1 - boxmask((bx[0] - 40, bx[1] - 40, bx[2] + 40, bx[3] + 40))
    m[: int(H * 0.35)] = 0
    m = dil(ero(m, 3), 11)
    hull = fill_hull(m, 600)
    if hull.sum() < 600:
        return [np.nan, np.nan, np.nan]
    c = centroid(hull > 0.5)
    return [c[0], c[1], float(hull.sum())]


def analyze(frames, cfg):
    ident = np.array([[1, 0, 0], [0, 1, 0]], np.float32)
    ybox = np.array([yellow_bbox(f.astype(np.float32)) or [np.nan] * 4 for f in frames], np.float32)
    ybox = fill_nan(smooth(ybox, 12), np.array([0, 0, 1, 1], np.float32))
    if not cfg.get("moving"):
        return np.repeat(ident[None], len(frames), 0), ybox

    # the plate is the one landmark on the table plane that never moves: its
    # centre gives the translation and its area the zoom
    plate = np.array([coarse_plate(f.astype(np.float32), cfg) for f in frames], np.float32)
    plate = smooth(plate, 4)
    area = plate[:, 2].copy()
    for i in range(len(area)):                      # occlusion only shrinks the hull
        w = area[max(0, i - 12): i + 13]
        w = w[~np.isnan(w)]
        area[i] = np.percentile(w, 90) if len(w) else np.nan
    ok = ~np.isnan(plate[:, :2]).any(axis=1) & ~np.isnan(area)
    Ms = np.full((len(frames), 6), np.nan, np.float32)
    if ok.any():
        i0 = int(np.argmax(ok))
        p0, a0 = plate[i0, :2], area[i0]
        for i in range(len(frames)):
            if not ok[i]:
                continue
            sc = float(np.sqrt(area[i] / a0))
            if not (0.7 < sc < 1.6):
                continue
            t = plate[i, :2] - sc * p0
            Ms[i] = [sc, 0, t[0], 0, sc, t[1]]
    Ms = fill_nan(smooth(Ms, 3), ident.reshape(-1))
    return Ms.reshape(-1, 2, 3).astype(np.float32), ybox


def can_band(ybox, k):
    x0, y0, x1, y1 = ybox
    h = max(10.0, y1 - y0)
    margin = max(14.0, 0.28 * (x1 - x0))
    return (x0 - margin, 0, x1 + margin, y1 + k * h)


def can_k(ybox0, can_bottom):
    """Stack height below the label, in label heights, from the first frame."""
    x0, y0, x1, y1 = ybox0
    return max(0.2, (can_bottom - y1) / max(10.0, y1 - y0))


# ---- models ------------------------------------------------------------------------------
class Seg:
    PROMPTS = ["a white robot arm", "a robot gripper"]

    def __init__(self):
        import torch
        from transformers import (CLIPSegForImageSegmentation, CLIPSegProcessor,
                                  SamModel, SamProcessor)
        self.torch = torch
        self.cp = CLIPSegProcessor.from_pretrained("CIDAS/clipseg-rd64-refined")
        self.cm = CLIPSegForImageSegmentation.from_pretrained("CIDAS/clipseg-rd64-refined").eval()
        self.sp = SamProcessor.from_pretrained("Zigeng/SlimSAM-uniform-77")
        self.sm = SamModel.from_pretrained("Zigeng/SlimSAM-uniform-77").eval()

    def clipseg(self, ims):
        """List of PIL images -> list of HxW float maps, max over prompts."""
        P = len(self.PROMPTS)
        with self.torch.no_grad():
            inp = self.cp(text=self.PROMPTS * len(ims), images=[im for im in ims for _ in range(P)],
                          padding=True, return_tensors="pt")
            pr = self.torch.sigmoid(self.cm(**inp).logits).numpy().reshape(len(ims), P, 352, 352).max(1)
        return [np.asarray(Image.fromarray((p * 255).astype(np.uint8)).resize((W, H)), np.float32) / 255
                for p in pr]

    def sam(self, im, pos, neg, white):
        """Best of SAM's three candidates that is not too big and not mostly table."""
        pts = [list(p) for p in pos] + [list(p) for p in neg]
        lab = [1] * len(pos) + [0] * len(neg)
        with self.torch.no_grad():
            inp = self.sp(im, input_points=[[pts]], input_labels=[[lab]], return_tensors="pt")
            out = self.sm(**inp)
            masks = self.sp.image_processor.post_process_masks(
                out.pred_masks, inp["original_sizes"], inp["reshaped_input_sizes"])[0][0].numpy()
            iou = out.iou_scores[0, 0].numpy()
        areas = masks.reshape(3, -1).mean(1)
        ok = []
        for j in range(3):
            if areas[j] < 0.25 and masks[j].sum() > 0 and white[masks[j]].mean() < 0.4:
                ok.append(j)
        if not ok:
            return np.zeros((H, W), np.float32)
        j = max(ok, key=lambda j: iou[j])
        return masks[j].astype(np.float32)


def peaks(p, k=6, minp=0.35, spacing=48, forbid=None):
    pts, q = [], p.copy()
    if forbid is not None:
        q[forbid > 0.5] = 0
    for _ in range(k):
        i = int(q.argmax())
        y, x = divmod(i, W)
        if q[y, x] < minp:
            break
        pts.append((float(x), float(y)))
        q[max(0, y - spacing): y + spacing, max(0, x - spacing): x + spacing] = 0
    return pts


# ---- per-frame mask -----------------------------------------------------------------------
def frame_masks(f, im, cmap, M, ybox, k, cfg, seg):
    r, g, b, gray, chroma = channels(f)
    band = boxmask(can_band(ybox, k))
    cups = np.zeros((H, W), np.float32)
    for bx in cfg["cups"]:
        cups = np.maximum(cups, boxmask(warp_box(bx, M)))
    wall = np.zeros((H, W), np.float32)
    for bx in cfg["wall"]:
        wall = np.maximum(wall, boxmask(warp_box(bx, M)))
    base = boxmask(warp_box(cfg["base"], M))
    if cfg.get("moving"):
        table = table_auto(f)
    else:
        table = polymask(cfg["table"], M)
    table_wide = dil(table, 25)
    table_edge = dil(table, 25)
    table_in = ero(table, 13)          # clear of the dark gap along the table's back edge
    forbid = np.maximum.reduce([band, cups, wall])

    apple = apple_mask(f).astype(np.float32) * (1 - cups)
    apple = dil(apple, 9)
    plate = plate_mask(f).astype(np.float32) * (1 - forbid) * table
    plate = dil(ero(plate, 3), 11)
    plate = fill_hull(plate, 600)

    # arm above the table: white on black
    above = ((gray > 110) & (chroma < 55)).astype(np.float32) * (1 - table_edge) * (1 - forbid) * (1 - plate)
    above = drop_strips(drop_small(dil(ero(above, 7), 11), 400))
    # gripper / joints / cable over the table: dark on white
    dark = (gray < 90).astype(np.float32) * table_in * (1 - forbid) * (1 - apple)
    dark = drop_strips(drop_small(dil(ero(dark, 3), 9), 200))
    # the arm's grey shading over the table (its shadow on the table is lighter than this)
    mid = ((gray < 140) & (chroma < 40)).astype(np.float32) * table_in * (1 - forbid) * (1 - apple) * (1 - plate)
    mid = drop_strips(drop_small(dil(ero(mid, 3), 9), 300))

    # SAM, prompted by CLIPSeg peaks plus the cheap masks, trusted only near the table
    pos = peaks(cmap, forbid=forbid)
    blob, _ = largest(above, 400)
    if blob is not None:
        ys, xs = np.where(blob > 0.5)
        j = int(np.argmax(ys))
        pos.append((float(xs[j]), float(ys[j]) - 4))
    blob, c = largest(dark, 300)
    if blob is not None:
        pos.append((float(c[0]), float(c[1])))
    neg = []
    x0, y0, x1, y1 = can_band(ybox, k)
    neg += [((x0 + x1) / 2, (y0 + y1) / 2), ((x0 + x1) / 2, y1 - (y1 - y0) * 0.2)]
    for bx in cfg["cups"]:
        wb = warp_box(bx, M)
        neg.append(((wb[0] + wb[2]) / 2, (wb[1] + wb[3]) / 2))
    for m in (plate, apple):
        c = centroid(m > 0.5)
        if c:
            neg.append(c)
    c = centroid(table > 0.5)
    if c and all(np.hypot(c[0] - p[0], c[1] - p[1]) > 90 for p in pos):
        neg.append(c)
    neg = [(min(W - 1, max(0, x)), min(H - 1, max(0, y))) for x, y in neg]
    sam = np.zeros((H, W), np.float32)
    cues = np.maximum.reduce([above, dark, mid])
    if pos and cues.sum() > 0:
        near = dil(cues, 71)     # SAM may only extend the cheap cues
        sam = seg.sam(im, pos, neg, white=(gray > 195) & (chroma < 25)) * table_wide * (1 - forbid) * (1 - plate) * near
        sam = drop_small(ero(sam, 3), 300)

    robot = np.maximum.reduce([above, dark, mid, sam])
    robot = ero(dil(robot, 9), 5)
    # keep only fragments the segmenter believes are the arm, or that sit on the base
    n, lab, stats, _ = cv2.connectedComponentsWithStats((robot > 0.5).astype(np.uint8), 8)
    keep = np.zeros(n, bool)
    base_wide = dil(base, 15) > 0.5
    for i in range(1, n):
        sel = lab == i
        if stats[i, cv2.CC_STAT_AREA] < MIN_BLOB:
            continue
        bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if bh < 24 and bw > 5 * bh:      # a sliver of table edge, not a robot
            continue
        keep[i] = ((cmap[sel].max() >= 0.35 and gray[sel].max() > 150) or (base_wide & sel).any()
                   or (sam[sel] > 0.5).mean() > 0.3)
    robot = keep[lab].astype(np.float32)
    robot = np.maximum(robot, feather(base))

    # obstacles
    if cfg["obstacle"] == "cups":
        obst = ((chroma > 40) & (gray > 45)).astype(np.float32) * cups
        obst = drop_small(dil(ero(obst, 3), 9), 300)
    else:
        # the band is a box, so keep it off the table top around the canisters' feet
        tablewhite = ((gray > 185) & (chroma < 20)).astype(np.float32) * table_in
        obst = ((gray > 70) | (chroma > 50)).astype(np.float32) * band * (1 - tablewhite)
        obst = drop_small(ero(dil(dil(ero(obst, 5), 9), 15), 15), 500)
    edge = np.clip(dil(obst, 7) - obst, 0, 1)
    edge = blur(edge, 1.2)
    obst = feather(obst)

    return dict(robot=np.clip(robot, 0, 1), apple=np.clip(apple, 0, 1), plate=np.clip(plate, 0, 1),
                obst=np.clip(obst, 0, 1), edge=np.clip(edge, 0, 1))


def compose_alpha(parts, prev=None):
    """Foreground alpha from the cached parts: a soft halo around the arm, tight
    feathered masks for the apple and plate, and a short temporal blend."""
    halo = blur(dil(parts["robot"], HALO), HALO_BLUR)
    fg = np.maximum.reduce([halo, feather(parts["apple"]), feather(parts["plate"])])
    if prev is not None:
        fg = np.maximum(fg, 0.6 * prev)
    return np.clip(fg, 0, 1)


# ---- colour ------------------------------------------------------------------------------
def saturate(x, s):
    g = (0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2])[..., None]
    return np.clip(g + (x - g) * s, 0, 255)


def grade(f, gain):
    x = f * gain
    x = (x - 128.0) * CONTRAST + 128.0
    return np.clip(x, 0, 255)


def wash(x):
    y = saturate(x, BG_SAT) * (1 - BG_WASH) + 255.0 * BG_WASH
    if BG_BLUR > 0:
        y = cv2.GaussianBlur(y, (0, 0), BG_BLUR)
    return y.astype(np.float32)


def table_gain(frames):
    vals = []
    for f in frames[:: max(1, len(frames) // 40)]:
        ff = f.astype(np.float32)
        hull = table_hull(ff) > 0.5
        _, _, _, gray, chroma = channels(ff)
        sel = hull & (gray > 165) & (chroma < 40)
        if sel.sum() > 2000:
            vals.append(np.median(ff[sel], axis=0))
    t = np.percentile(np.array(vals), 80, axis=0) if vals else np.array([210, 210, 200])
    return np.minimum(TABLE_TARGET / t, MAX_GAIN).astype(np.float32), t


def render(f, fg, obst, edge, gain):
    gr = grade(f, gain)
    fgc = saturate(gr, SAT_FG)
    bgc = wash(gr)
    a = np.maximum(fg, obst)[..., None]
    out = fgc * a + bgc * (1 - a)
    t = np.maximum(obst * TINT_T, edge * EDGE_T)[..., None]
    out = out * (1 - t) + TINT * t
    return np.clip(out, 0, 255).astype(np.uint8)


# ---- driver -----------------------------------------------------------------------------------
def read_all(path):
    import imageio_ffmpeg as iio
    g = iio.read_frames(path)
    meta = next(g)
    return meta, [np.frombuffer(x, np.uint8).reshape(H, W, 3) for x in g]


def process(name, seg, preview_dir=None):
    import imageio_ffmpeg as iio
    cfg = CLIPS[name]
    meta, frames = read_all(os.path.join(SRC, name + ".mp4"))
    gain, tcol = table_gain(frames)
    Ms, ybox = analyze(frames, cfg)
    k = can_k(ybox[0], cfg["can_bottom"])
    print(f"{name}: {len(frames)} frames, table {tcol.round(0)}, gain {gain.round(3)}, can_k {k:.2f}",
          file=sys.stderr)

    if preview_dir:
        n = len(frames)
        idx = [0, n // 6, 2 * n // 6, 3 * n // 6, 4 * n // 6, 5 * n // 6, n - 1]
        ims = [Image.fromarray(frames[k]) for k in idx]
        cmaps = seg.clipseg(ims)
        sheet = Image.new("RGB", (W * 3 // 2, H * len(idx) // 2))
        for i, kk in enumerate(idx):
            f = frames[kk].astype(np.float32)
            parts = frame_masks(f, ims[i], cmaps[i], Ms[idx[i]], ybox[idx[i]], k, cfg, seg)
            fg, obst, edge = compose_alpha(parts), parts["obst"], parts["edge"]
            out = render(f, fg, obst, edge, gain)
            am = np.stack([fg, fg * (1 - obst), fg * (1 - obst)], -1)  # obstacles show red
            am[..., 0] = np.maximum(am[..., 0], obst)
            row = [Image.fromarray(frames[kk]), Image.fromarray(out),
                   Image.fromarray((am * 255).astype(np.uint8))]
            for j, im in enumerate(row):
                sheet.paste(im.resize((W // 2, H // 2)), (j * W // 2, i * H // 2))
        os.makedirs(preview_dir, exist_ok=True)
        sheet.save(os.path.join(preview_dir, name + ".jpg"), quality=88)
        return

    os.makedirs(DST, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    cache = os.path.join(CACHE, name + ".masks.npz")
    cached = None
    if os.path.exists(cache) and not FORCE:
        z = np.load(cache)
        if int(z["n"]) == len(frames):
            cached = {kk: z[kk] for kk in ("robot", "apple", "plate", "obst", "edge")}
            print(f"  {name}: masks from cache {os.path.relpath(cache, ROOT)}", file=sys.stderr)
    store = {kk: np.zeros((len(frames), H, W), np.uint8) for kk in ("robot", "apple", "plate", "obst", "edge")}
    dst = os.path.join(DST, name + ".mp4")
    wr = iio.write_frames(dst, (W, H), fps=meta["fps"], codec="libx264", quality=None,
                          output_params=["-crf", "21", "-preset", "slow", "-pix_fmt", "yuv420p",
                                         "-movflags", "+faststart"], macro_block_size=1)
    wr.send(None)
    B = 8
    prev = None
    for s in range(0, len(frames), B):
        chunk = frames[s: s + B]
        ims = [Image.fromarray(f) for f in chunk]
        cmaps = seg.clipseg(ims) if cached is None else None
        for i, f in enumerate(chunk):
            j = s + i
            if cached is None:
                parts = frame_masks(f.astype(np.float32), ims[i], cmaps[i], Ms[j], ybox[j], k, cfg, seg)
                for kk, v in parts.items():
                    store[kk][j] = (v * 255).astype(np.uint8)
            else:
                parts = {kk: cached[kk][j].astype(np.float32) / 255 for kk in cached}
            fg = compose_alpha(parts, prev)
            prev = fg
            wr.send(render(f.astype(np.float32), fg, parts["obst"], parts["edge"], gain))
        if s % (B * 25) == 0:
            print(f"  {name}: {s}/{len(frames)}", file=sys.stderr)
    wr.close()
    if cached is None:
        np.savez_compressed(cache, n=len(frames), **store)
    print(f"wrote {os.path.relpath(dst, ROOT)}  {os.path.getsize(dst) // 1024} KB", file=sys.stderr)


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--preview" in args
    FORCE = "--force" in args
    names = [a for a in args if not a.startswith("--")] or list(CLIPS)
    seg = Seg() if (preview or FORCE or any(not os.path.exists(os.path.join(CACHE, n + ".masks.npz")) for n in names)) else None
    for n in names:
        process(n, seg, preview_dir=os.path.join(ROOT, "tools", ".preview") if preview else None)
