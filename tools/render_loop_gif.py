#!/usr/bin/env python3
"""Render the talk's live CS-Pi loop to a GIF.

The loop on "Watch delta go to zero" is a live canvas, so there is nothing to
screen-record without a browser. This drives the shipped animation directly:

  1. lift the hero IIFE out of the built deck (talk/short.html)
  2. run it in JavaScriptCore on a fixed clock, recording every canvas call
  3. rasterise those calls with Pillow at 3x and downsample
  4. hand the frames to ffmpeg with a generated palette

Because step 2 executes the deck's own code, the GIF cannot drift from what the
slide does -- rebuild the deck, re-run this, and the GIF matches again.

    python3 tools/render_loop_gif.py                  # -> assets/cspi_loop.gif
    python3 tools/render_loop_gif.py --frame 136      # one PNG, to eyeball

macOS only: it uses osascript's JavaScriptCore as the JS engine. ffmpeg comes
from PATH, or from the imageio_ffmpeg wheel that talk/build.py already needs.
"""
import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECK = os.path.join(ROOT, "talk", "short.html")
OUTGIF = os.path.join(ROOT, "assets", "cspi_loop.gif")

# One full period of the loop. Keep STEP an exact divisor of it, or the GIF
# will not join back to its first frame.
LOOP_MS = 15900
STEP_MS = 30
S = 3                                    # supersample factor
FINAL = (1350, 580)                      # 1.5x the 900x387 CSS layout
CW, CH = 900, 330                        # canvas size the animation lays out for
BAR_H, FOOT_H = 30, 27                   # the vizbar and vizfoot around it
PADX = 13

PANEL, LINE, SLIDE = (245, 248, 252), (226, 232, 242), (255, 255, 255)
BLUEDP, INKSOFT = (15, 63, 134), (74, 90, 114)
LEGEND = [((29, 111, 212), "draw / project"),
          ((31, 157, 87), "feasible · goal"),
          ((224, 83, 61), "obstacle (unseen at training)")]
RECIPE = "draw → project → renoise to n = k/(k+δ) → re-run"

# Inter and JetBrains Mono are webfonts the deck pulls from Google; they are not
# on the machine. Lucida Grande is the only local UI sans carrying the arrow,
# delta and check the labels need, and Menlo stands in for the mono.
MENLO = "/System/Library/Fonts/Menlo.ttc"
SANS = "/System/Library/Fonts/LucidaGrande.ttc"


# --------------------------------------------------------------------------
# 1 + 2: run the deck's animation and record its canvas calls
# --------------------------------------------------------------------------
def hero_source(deck_path):
    """The live-loop IIFE, verbatim, out of the built deck."""
    with open(deck_path, encoding="utf-8") as fh:
        s = fh.read()
    anchor = "    var canvas = document.getElementById('heroCanvas');"
    if anchor not in s:
        sys.exit("could not find the hero canvas block in %s" % deck_path)
    i = s.rindex("(function(){", 0, s.index(anchor))
    j = s.index("})();\n})();\n</script>", i)
    return s[i:j + len("})();")]


CAPTURE_JS = r"""
ObjC.import('Foundation');
function readText(p){
  return $.NSString.stringWithContentsOfFileEncodingError(p, $.NSUTF8StringEncoding, null).js;
}
function writeText(p, s){
  $.NSString.alloc.initWithUTF8String(s)
    .writeToFileAtomicallyEncodingError(p, true, $.NSUTF8StringEncoding, null);
}
var CFG = JSON.parse(readText('__CFG__'));
var CLOCK = 0, raf = null, ops = [], sub = [];

function Grad(x0,y0,x1,y1){ this.x0=x0; this.y0=y0; this.x1=x1; this.y1=y1; this.stops=[]; }
Grad.prototype.addColorStop = function(o,c){ this.stops.push([o,c]); };

function Ctx(){
  this.strokeStyle=''; this.fillStyle=''; this.lineWidth=1; this.font='';
  this.textAlign='start'; this.textBaseline='alphabetic';
  this.lineJoin='miter'; this.lineCap='butt'; this._dash=null;
}
Ctx.prototype.setTransform=function(){};
Ctx.prototype.clearRect=function(){ ops.length=0; sub=[]; };
Ctx.prototype.beginPath=function(){ sub=[]; };
Ctx.prototype.closePath=function(){ if (sub.length) sub.push(['Z']); };
Ctx.prototype.moveTo=function(x,y){ sub.push(['M',x,y]); };
Ctx.prototype.lineTo=function(x,y){ sub.push(['L',x,y]); };
Ctx.prototype.arc=function(x,y,r,a0,a1){ sub.push(['A',x,y,r,a0,a1]); };
/* the tangent arc, so the noise bar keeps its rounded corners */
Ctx.prototype.arcTo=function(x1,y1,x2,y2,r){
  var last=null, i;
  for (i=sub.length-1;i>=0;i--) if (sub[i][0]==='M'||sub[i][0]==='L'){ last=sub[i]; break; }
  if (!last){ sub.push(['L',x1,y1]); return; }
  var x0=last[1], y0=last[2];
  var v1x=x0-x1, v1y=y0-y1, v2x=x2-x1, v2y=y2-y1;
  var l1=Math.hypot(v1x,v1y)||1, l2=Math.hypot(v2x,v2y)||1;
  v1x/=l1; v1y/=l1; v2x/=l2; v2y/=l2;
  var theta=Math.acos(Math.max(-1,Math.min(1, v1x*v2x + v1y*v2y)));
  if (theta < 1e-6 || Math.abs(Math.PI-theta) < 1e-6){ sub.push(['L',x1,y1]); return; }
  var d=r/Math.tan(theta/2);
  var t1x=x1+v1x*d, t1y=y1+v1y*d, t2x=x1+v2x*d, t2y=y1+v2y*d;
  var bx=v1x+v2x, by=v1y+v2y, bl=Math.hypot(bx,by)||1;
  var cx=x1 + (bx/bl)*(r/Math.sin(theta/2)), cy=y1 + (by/bl)*(r/Math.sin(theta/2));
  sub.push(['L',t1x,t1y]);
  var a0=Math.atan2(t1y-cy,t1x-cx), a1=Math.atan2(t2y-cy,t2x-cx), da=a1-a0;
  while (da >  Math.PI) da -= 2*Math.PI;
  while (da < -Math.PI) da += 2*Math.PI;
  for (var k=1;k<=8;k++){
    var a=a0+da*(k/8);
    sub.push(['L', cx+r*Math.cos(a), cy+r*Math.sin(a)]);
  }
};
Ctx.prototype.rect=function(){};
function style(v){
  return (v instanceof Grad)
    ? {grad:{x0:v.x0, y0:v.y0, x1:v.x1, y1:v.y1, stops:v.stops}} : v;
}
Ctx.prototype.stroke=function(){
  ops.push({op:'stroke', path:sub.slice(), color:style(this.strokeStyle),
            w:this.lineWidth, dash:this._dash});
};
Ctx.prototype.fill=function(){
  ops.push({op:'fill', path:sub.slice(), color:style(this.fillStyle)});
};
Ctx.prototype.fillRect=function(x,y,w,h){
  ops.push({op:'rect', x:x, y:y, w:w, h:h, color:style(this.fillStyle)});
};
Ctx.prototype.fillText=function(t,x,y){
  ops.push({op:'text', t:t, x:x, y:y, color:style(this.fillStyle),
            align:this.textAlign, base:this.textBaseline, font:this.font});
};
Ctx.prototype.setLineDash=function(d){ this._dash = (d && d.length) ? d.slice() : null; };
Ctx.prototype.createLinearGradient=function(x0,y0,x1,y1){ return new Grad(x0,y0,x1,y1); };

var CANVAS = {clientWidth:CFG.cw, clientHeight:CFG.ch, width:0, height:0,
              getContext:function(){ return new Ctx(); }, addEventListener:function(){}};
var elements = {};
['vizStage','statDelta','statN','statIter'].forEach(function(id){
  elements[id] = {textContent:''};
});
document = {getElementById:function(id){
  return id==='heroCanvas' ? CANVAS : (elements[id]||null); }};
window = {devicePixelRatio:1, addEventListener:function(){}};
performance = {now:function(){ return CLOCK; }};
requestAnimationFrame = function(cb){ raf = cb; };

var frames = [], err = null;
try {
  eval(readText(CFG.hero));
  for (CLOCK = 0; CLOCK < CFG.loop; CLOCK += CFG.step){
    var cb = raf; raf = null;
    if (!cb){ err = 'the animation stopped requesting frames at t=' + CLOCK; break; }
    cb(CLOCK);
    frames.push({t:CLOCK, ops:ops.slice(),
                 hud:{stage:elements.vizStage.textContent,
                      iter:elements.statIter.textContent,
                      delta:elements.statDelta.textContent,
                      n:elements.statN.textContent}});
  }
} catch(e){ err = 'failed at t=' + CLOCK + ': ' + e.message; }
writeText(CFG.out, JSON.stringify({error:err, frames:frames}));
(err ? err : 'captured ' + frames.length + ' frames');
"""


def capture(deck_path, work):
    hero = os.path.join(work, "hero.js")
    with open(hero, "w", encoding="utf-8") as fh:
        fh.write(hero_source(deck_path))
    cfg = os.path.join(work, "cfg.json")
    frames = os.path.join(work, "frames.json")
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump({"hero": hero, "out": frames, "loop": LOOP_MS,
                   "step": STEP_MS, "cw": CW, "ch": CH}, fh)
    js = os.path.join(work, "capture.js")
    with open(js, "w", encoding="utf-8") as fh:
        fh.write(CAPTURE_JS.replace("__CFG__", cfg))
    r = subprocess.run(["osascript", "-l", "JavaScript", js],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("capture failed: %s" % (r.stderr.strip() or r.stdout.strip()))
    print("  " + r.stdout.strip())
    with open(frames, encoding="utf-8") as fh:
        d = json.load(fh)
    if d["error"]:
        sys.exit("capture failed: %s" % d["error"])
    return d["frames"]


# --------------------------------------------------------------------------
# 3: rasterise
# --------------------------------------------------------------------------
from PIL import Image, ImageDraw, ImageFont            # noqa: E402

W, H = CW, BAR_H + CH + FOOT_H
_fc = {}


def font(kind, size, bold=False):
    key = (kind, round(size, 1), bold)
    if key not in _fc:
        path = MENLO if kind == "mono" else SANS
        _fc[key] = ImageFont.truetype(path, max(1, int(round(size))),
                                      index=1 if bold else 0)
    return _fc[key]


def parse_font(spec):
    bold, px = False, 12.0
    for tok in (spec or "").replace(",", " ").split():
        if tok.isdigit() and len(tok) == 3:
            bold = int(tok) >= 600
        elif tok.endswith("px"):
            try:
                px = float(tok[:-2])
            except ValueError:
                pass
    kind = "mono" if ("mono" in (spec or "").lower()
                      or "jetbrains" in (spec or "").lower()) else "sans"
    return kind, px, bold


def css(c):
    if isinstance(c, dict):
        return None                                    # gradient
    c = (c or "#000").strip()
    if c.startswith("rgba") or c.startswith("rgb"):
        p = c[c.index("(") + 1:c.index(")")].split(",")
        a = int(float(p[3]) * 255) if len(p) > 3 else 255
        return (int(float(p[0])), int(float(p[1])), int(float(p[2])), a)
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    return (0, 0, 0, 255)


def arc_pts(x, y, r, a0, a1, n=160):
    if abs(a1 - a0) >= 6.2:
        a0, a1 = 0.0, 2 * math.pi
    return [(x + r * math.cos(a0 + (a1 - a0) * i / n),
             y + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def runs_of(path):
    runs, cur, closed = [], [], False
    for seg in path:
        k = seg[0]
        if k == "M":
            if len(cur) > 1:
                runs.append((cur, closed))
            cur, closed = [(seg[1], seg[2])], False
        elif k == "L":
            cur.append((seg[1], seg[2]))
        elif k == "A":
            if len(cur) > 1:
                runs.append((cur, closed))
            runs.append((arc_pts(*seg[1:6]), True))
            cur, closed = [], False
        elif k == "Z":
            closed = True
    if len(cur) > 1:
        runs.append((cur, closed))
    return runs


def dashes(run, on, off):
    out, acc, pen = [], 0.0, True
    for i in range(len(run) - 1):
        (x0, y0), (x1, y1) = run[i], run[i + 1]
        L = math.hypot(x1 - x0, y1 - y0)
        t = 0.0
        while t < L:
            step = min((on if pen else off) - acc, L - t)
            if pen:
                out.append(((x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L),
                            (x0 + (x1 - x0) * (t + step) / L,
                             y0 + (y1 - y0) * (t + step) / L)))
            t += step
            acc += step
            if acc >= (on if pen else off) - 1e-9:
                acc, pen = 0.0, not pen
    return out


_grad = {}


def grad_fill(im, runs, g, oy):
    """Horizontal ramp clipped to the path. Identical every frame, so cached."""
    key = (im.size, g["x0"], g["x1"], tuple(map(tuple, g["stops"])))
    hit = _grad.get(key)
    if hit is None:
        mask = Image.new("L", im.size, 0)
        md = ImageDraw.Draw(mask)
        for pts, _ in runs:
            if len(pts) > 2:
                md.polygon([(p[0] * S, p[1] * S + oy) for p in pts], fill=255)
        stops = sorted(((float(o), css(c)) for o, c in g["stops"]), key=lambda s: s[0])
        ramp = Image.new("RGBA", im.size)
        rd = ImageDraw.Draw(ramp)
        x0, x1 = g["x0"] * S, g["x1"] * S
        span = max(1.0, x1 - x0)
        for px in range(im.size[0]):
            u = min(1.0, max(0.0, (px - x0) / span))
            lo, hi = stops[0], stops[-1]
            for i in range(len(stops) - 1):
                if stops[i][0] <= u <= stops[i + 1][0]:
                    lo, hi = stops[i], stops[i + 1]
                    break
            w = 0.0 if hi[0] == lo[0] else (u - lo[0]) / (hi[0] - lo[0])
            rd.line([(px, 0), (px, im.size[1])],
                    fill=tuple(int(lo[1][k] + (hi[1][k] - lo[1][k]) * w) for k in range(4)))
        hit = _grad[key] = (ramp, mask)
    im.paste(hit[0], (0, 0), hit[1])


def draw_canvas(im, dr, ops, oy):
    def P(p):
        return (p[0] * S, p[1] * S + oy)
    for op in ops:
        col = css(op.get("color"))
        if op["op"] == "rect":
            dr.rectangle([op["x"] * S, op["y"] * S + oy,
                          (op["x"] + op["w"]) * S, (op["y"] + op["h"]) * S + oy], fill=col)
        elif op["op"] == "text":
            kind, px, bold = parse_font(op.get("font"))
            a = {"left": "l", "start": "l", "center": "m",
                 "right": "r", "end": "r"}.get(op.get("align"), "l")
            b = {"top": "t", "middle": "m", "bottom": "b",
                 "alphabetic": "s"}.get(op.get("base"), "s")
            dr.text(P((op["x"], op["y"])), op["t"], font=font(kind, px * S, bold),
                    fill=col, anchor=a + b)
        elif op["op"] == "fill":
            runs = runs_of(op["path"])
            if col is None:
                grad_fill(im, runs, op["color"]["grad"], oy)
                continue
            for pts, _ in runs:
                if len(pts) > 2:
                    dr.polygon([P(p) for p in pts], fill=col)
        else:
            w = max(1, int(round(op.get("w", 1) * S)))
            for pts, closed in runs_of(op["path"]):
                line = [P(p) for p in pts]
                if closed and line[0] != line[-1]:
                    line.append(line[0])
                if op.get("dash"):
                    for a, b in dashes(line, op["dash"][0] * S, op["dash"][1] * S):
                        dr.line([a, b], fill=col, width=w)
                else:
                    dr.line(line, fill=col, width=w, joint="curve")
                    if w > 2:                          # round caps
                        for e in (line[0], line[-1]):
                            dr.ellipse([e[0] - w / 2, e[1] - w / 2,
                                        e[0] + w / 2, e[1] + w / 2], fill=col)


def render(fr):
    im = Image.new("RGBA", (W * S, H * S), SLIDE + (255,))
    dr = ImageDraw.Draw(im, "RGBA")
    dr.rounded_rectangle([0, 0, W * S - 1, H * S - 1], radius=10 * S,
                         fill=PANEL + (255,), outline=LINE + (255,), width=S)
    dr.line([(0, BAR_H * S), (W * S, BAR_H * S)], fill=LINE + (255,), width=S)
    dr.line([(0, (BAR_H + CH) * S), (W * S, (BAR_H + CH) * S)], fill=LINE + (255,), width=S)

    hud = fr["hud"]
    fm, fmb = font("mono", 11.5 * S), font("mono", 11.5 * S, True)
    cy = BAR_H * S / 2
    dr.text((PADX * S, cy), hud["stage"], font=fmb, fill=BLUEDP + (255,), anchor="lm")
    x = W * S - PADX * S
    for txt in (hud["n"], hud["delta"], hud["iter"]):
        dr.text((x, cy), txt, font=fm, fill=INKSOFT + (255,), anchor="rm")
        x -= dr.textlength(txt, font=fm) + 12 * S

    draw_canvas(im, dr, fr["ops"], BAR_H * S)

    fs = font("sans", 11 * S)
    fy = (BAR_H + CH) * S + FOOT_H * S / 2
    x = PADX * S
    for col, txt in LEGEND:
        r = 4 * S
        dr.ellipse([x, fy - r, x + 2 * r, fy + r], fill=col + (255,))
        x += 2 * r + 5 * S
        dr.text((x, fy), txt, font=fs, fill=INKSOFT + (255,), anchor="lm")
        x += dr.textlength(txt, font=fs) + 13 * S
    dr.text((W * S - PADX * S, fy), RECIPE, font=fs, fill=INKSOFT + (255,), anchor="rm")
    return im.convert("RGB").resize(FINAL, Image.LANCZOS)


# --------------------------------------------------------------------------
# 4: encode
# --------------------------------------------------------------------------
def ffmpeg_bin():
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("no ffmpeg on PATH and imageio_ffmpeg is not installed")


def encode(frame_dir, out):
    # A generated palette, then Bayer dithering: without it the noise bar's
    # gradient bands visibly, and the dithering costs almost nothing in size.
    vf = ("[0:v] split [a][b];"
          "[a] palettegen=max_colors=256:stats_mode=full [p];"
          "[b][p] paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle")
    cmd = [ffmpeg_bin(), "-y", "-v", "error",
           "-framerate", "%.3f" % (1000.0 / STEP_MS),
           "-i", os.path.join(frame_dir, "%04d.png"),
           "-filter_complex", vf, "-loop", "0", out]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deck", default=DECK, help="built deck to lift the loop from")
    ap.add_argument("--out", default=OUTGIF, help="GIF to write")
    ap.add_argument("--frame", type=int, help="render only this frame, as a PNG")
    args = ap.parse_args()

    if LOOP_MS % STEP_MS:
        sys.exit("STEP_MS must divide LOOP_MS or the GIF will not loop cleanly")

    work = tempfile.mkdtemp(prefix="loopgif-")
    try:
        print("reading %s" % os.path.relpath(args.deck, ROOT))
        frames = capture(args.deck, work)

        if args.frame is not None:
            png = os.path.splitext(args.out)[0] + "-frame%d.png" % args.frame
            render(frames[args.frame]).save(png)
            print("wrote %s (t=%dms)" % (png, frames[args.frame]["t"]))
            return

        fdir = os.path.join(work, "frames")
        os.makedirs(fdir)
        for i, fr in enumerate(frames):
            render(fr).save(os.path.join(fdir, "%04d.png" % i))
        print("  rasterised %d frames at %dx%d" % (len(frames), FINAL[0], FINAL[1]))

        encode(fdir, args.out)
        mb = os.path.getsize(args.out) / 1048576.0
        print("wrote %s  (%.1f MB, %d frames, %.1f s loop)"
              % (os.path.relpath(args.out, ROOT), mb, len(frames), LOOP_MS / 1000.0))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
