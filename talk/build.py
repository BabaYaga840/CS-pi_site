#!/usr/bin/env python3
"""Build the CS-Pi lab talk from talk/deck.src.html.

The source deck references media with {{M:<repo-relative path>}} tokens. This
script emits two builds from that single source:

  talk/index.html                 full HTML document, media as relative paths.
                                  Present from this one -- full-resolution GIFs
                                  and video, no size ceiling.

  talk/dist/cspi-talk.embed.html  body fragment with every asset inlined as a
                                  data: URI, for publishing as a shareable
                                  Artifact (hard 16 MB ceiling on the rendered
                                  page, so GIFs are downscaled and PNG
                                  filmstrips are re-encoded as JPEG).

Usage:
    python3 talk/build.py            # both builds
    python3 talk/build.py --local    # skip the (slow) embed build

Pillow is required only for the embed build. Compressed media is cached under
talk/.cache/ so repeat runs are fast.
"""
import base64
import hashlib
import mimetypes
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TALK = ROOT / "talk"
SRC = TALK / "deck.src.html"
CACHE = TALK / ".cache"
OUT_LOCAL = TALK / "index.html"
OUT_EMBED = TALK / "dist" / "cspi-talk.embed.html"

TOKEN = re.compile(r"\{\{M:([^}]+)\}\}")

# --- embed-build compression settings ---------------------------------------
GIF_MAXW = 440      # rollout GIFs are shown in a half-slide panel
GIF_SKIP = 4        # keep every Nth frame, stretch duration to match
GIF_COLORS = 48
PNG_JPEG_OVER = 400_000   # PNGs bigger than this become JPEGs
JPEG_MAXW = 2400
JPEG_Q = 62
BUDGET = 16 * 1024 * 1024


def log(*a):
    print(*a, file=sys.stderr)


# ---------------------------------------------------------------------------
# local build: tokens -> paths relative to talk/index.html
# ---------------------------------------------------------------------------
def build_local(src: str) -> str:
    missing = []

    def sub(m):
        rel = m.group(1)
        if not (ROOT / rel).exists():
            missing.append(rel)
        return "../" + rel

    body = TOKEN.sub(sub, src)
    if missing:
        log("!! missing media (local build):")
        for p in missing:
            log("   ", p)

    # The source is an Artifact-style fragment: <title>/<link>/<style> first,
    # then the deck markup. Split it so the head material lands in <head> and
    # everything from the deck container onward lands in <body>.
    split = body.find('<div id="deck">')
    if split < 0:
        sys.exit("build_local: could not find the deck container in the source")
    head, rest = body[:split].rstrip(), body[split:]

    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="description" content="CS-Pi lab talk: constraint-satisfying '
        'flow policy sampling.">\n'
        + head
        + "\n</head>\n<body>\n"
        + rest
        + "\n</body>\n</html>\n"
    )


# ---------------------------------------------------------------------------
# embed build: tokens -> data: URIs
# ---------------------------------------------------------------------------
def cache_path(src_file: Path, tag: str, ext: str) -> Path:
    st = src_file.stat()
    key = f"{src_file}|{st.st_size}|{int(st.st_mtime)}|{tag}"
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    return CACHE / f"{src_file.stem}.{h}{ext}"


def shrink_gif(src_file: Path) -> bytes:
    from PIL import Image

    tag = f"gif-{GIF_MAXW}-{GIF_SKIP}-{GIF_COLORS}"
    cp = cache_path(src_file, tag, ".gif")
    if cp.exists():
        return cp.read_bytes()

    im = Image.open(src_file)
    n = getattr(im, "n_frames", 1)
    duration = im.info.get("duration", 80) or 80
    frames = []
    for i in range(0, n, GIF_SKIP):
        im.seek(i)
        frames.append(im.convert("RGB").copy())

    w, h = frames[0].size
    scale = min(1.0, GIF_MAXW / w)
    size = (max(1, int(w * scale)), max(1, int(h * scale)))
    frames = [f.resize(size, Image.LANCZOS) for f in frames]

    # one shared palette taken from a mid-sequence frame; no dithering, which
    # would add per-frame noise and defeat GIF's inter-frame compression
    master = frames[len(frames) // 2].quantize(colors=GIF_COLORS, method=Image.MEDIANCUT)
    quant = [f.quantize(palette=master, dither=Image.NONE) for f in frames]

    CACHE.mkdir(parents=True, exist_ok=True)
    quant[0].save(
        cp, save_all=True, append_images=quant[1:], loop=0,
        duration=max(30, duration * GIF_SKIP), optimize=True, disposal=2,
    )
    return cp.read_bytes()


def shrink_png(src_file: Path) -> tuple[bytes, str]:
    from PIL import Image

    raw = src_file.read_bytes()
    if len(raw) <= PNG_JPEG_OVER:
        return raw, "image/png"

    tag = f"jpg-{JPEG_MAXW}-{JPEG_Q}"
    cp = cache_path(src_file, tag, ".jpg")
    if cp.exists():
        return cp.read_bytes(), "image/jpeg"

    im = Image.open(src_file).convert("RGB")
    w, h = im.size
    if w > JPEG_MAXW:
        im = im.resize((JPEG_MAXW, max(1, round(h * JPEG_MAXW / w))), Image.LANCZOS)
    CACHE.mkdir(parents=True, exist_ok=True)
    im.save(cp, "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
    return cp.read_bytes(), "image/jpeg"


def build_embed(src: str) -> str:
    report = []
    missing = []

    def sub(m):
        rel = m.group(1)
        f = ROOT / rel
        if not f.exists():
            missing.append(rel)
            return ""
        suf = f.suffix.lower()
        if suf == ".gif":
            data, mime = shrink_gif(f), "image/gif"
        elif suf == ".png":
            data, mime = shrink_png(f)
        else:
            data = f.read_bytes()
            mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        report.append((rel, f.stat().st_size, len(data)))
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"

    out = TOKEN.sub(sub, src)

    if missing:
        log("!! missing media (embed build):")
        for p in missing:
            log("   ", p)

    log("\n  embedded media          original    embedded")
    log("  " + "-" * 58)
    tot_o = tot_e = 0
    for rel, o, e in sorted(report, key=lambda r: -r[2]):
        tot_o += o
        tot_e += e
        log(f"  {Path(rel).name[:30]:<30} {o/1024:8.0f}K {e/1024:9.0f}K")
    log("  " + "-" * 58)
    log(f"  {'total':<30} {tot_o/1024:8.0f}K {tot_e/1024:9.0f}K")
    return out


def main():
    if not SRC.exists():
        sys.exit(f"missing source deck: {SRC}")
    src = SRC.read_text(encoding="utf-8")

    OUT_LOCAL.write_text(build_local(src), encoding="utf-8")
    log(f"\nwrote {OUT_LOCAL.relative_to(ROOT)}  ({OUT_LOCAL.stat().st_size/1024:.0f}K)")
    log("  present with:  python3 -m http.server 8000   ->  localhost:8000/talk/")

    if "--local" in sys.argv:
        return

    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("\nembed build needs Pillow:  pip install Pillow   (or run with --local)")

    OUT_EMBED.parent.mkdir(parents=True, exist_ok=True)
    OUT_EMBED.write_text(build_embed(src), encoding="utf-8")
    size = OUT_EMBED.stat().st_size
    log(f"\nwrote {OUT_EMBED.relative_to(ROOT)}  ({size/1024/1024:.2f} MB)")
    pct = 100 * size / BUDGET
    if size > BUDGET:
        log(f"!! OVER the 16 MB Artifact ceiling ({pct:.0f}%) -- raise GIF_SKIP or drop media")
        sys.exit(1)
    log(f"   {pct:.0f}% of the 16 MB Artifact ceiling")


if __name__ == "__main__":
    main()
