"""Local interactive segmentation server (SAM 2) for picking what stays visible in the figures.

usage: python3 segment_server.py   ->  http://localhost:8765
Saves masks to masks/<stem>_mask.png and white-background images to masked/<file>.
"""
import base64, io, json, os, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import numpy as np, torch
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
UNGUIDED = [f"unguided_f{k:04d}.png" for k in [0, 64, 136, 208, 604, 1208, 1816, 2420, 3028, 3632, 4236]]
CLASSES = [f"1_start_position.png@{c}" for c in ("obstacle", "robot", "apple")]   # one frame, one mask per class
NEW_KEYFRAMES = UNGUIDED[1:4]                                                    # frames 64, 136, 208: the arm enters the view
OTHERS = ["2_gradient_guidance_failure.png", "7_projection_before_3s.png", "3_projection_failure.png",
          "6_rejection_base.png", "8_cspi_base.png", "5_cspi.png"]
BASES = NEW_KEYFRAMES + CLASSES + [u for u in UNGUIDED if u not in NEW_KEYFRAMES] + OTHERS
MODEL = "facebook/sam2.1-hiera-large"
PORT = 8765

dev = "mps" if torch.backends.mps.is_available() else "cpu"
from transformers import Sam2Model, Sam2Processor
print("loading", MODEL, "on", dev, flush=True)
proc = Sam2Processor.from_pretrained(MODEL)
model = Sam2Model.from_pretrained(MODEL).to(dev).eval()
print("model ready", flush=True)
cache = {}   # image file -> (PIL image, image embeddings, original_sizes)


def file_of(name):
    return name.split("@")[0]                      # "frame.png@class" -> "frame.png"


def mask_file(name):
    f, _, c = name.partition("@")
    return os.path.join(HERE, "masks", os.path.splitext(f)[0] + ("@" + c if c else "") + "_mask.png")


def embed(name):
    name = file_of(name)
    if name not in cache:
        img = Image.open(os.path.join(HERE, name)).convert("RGB")
        inp = proc(images=img, input_points=[[[[0, 0]]]], input_labels=[[[1]]], return_tensors="pt")
        with torch.no_grad():
            emb = model.get_image_embeddings(inp["pixel_values"].to(dev))
        cache[name] = (img, emb, inp["original_sizes"])
    return cache[name]


def png_b64(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def predict(name, pts):
    img, emb, sizes = embed(name)
    xy = [[[[float(p[0]), float(p[1])] for p in pts]]]
    lab = [[[int(p[2]) for p in pts]]]
    inp = proc(images=img, input_points=xy, input_labels=lab, return_tensors="pt")
    with torch.no_grad():
        out = model(image_embeddings=emb, input_points=inp["input_points"].to(dev),
                    input_labels=inp["input_labels"].to(dev), multimask_output=True)
    m = proc.post_process_masks(out.pred_masks.cpu(), sizes)[0][0].numpy() > 0   # (3,H,W)
    return {"masks": [png_b64((k * 255).astype(np.uint8)) for k in m],
            "scores": [float(s) for s in out.iou_scores.cpu().numpy().reshape(-1)]}


def save(name, mask_b64):
    mask = np.array(Image.open(io.BytesIO(base64.b64decode(mask_b64))).convert("L")) > 127
    img = np.array(Image.open(os.path.join(HERE, file_of(name))).convert("RGB"))
    os.makedirs(os.path.join(HERE, "masks"), exist_ok=True)
    Image.fromarray((mask * 255).astype(np.uint8)).save(mask_file(name))
    if "@" in name:                                # per-class masks only; no white-background image
        return
    os.makedirs(os.path.join(HERE, "masked"), exist_ok=True)
    out = np.full_like(img, 255)
    out[mask] = img[mask]
    Image.fromarray(out).save(os.path.join(HERE, "masked", name))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", code=200):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            return self.send(open(os.path.join(HERE, "segment_tool.html"), "rb").read(), "text/html")
        if p == "/images":
            done = [n for n in BASES if os.path.exists(mask_file(n))]
            return self.send({"images": BASES, "done": done})
        if p.startswith("/img/") and os.path.basename(p) in BASES:
            return self.send(open(os.path.join(HERE, file_of(os.path.basename(p))), "rb").read(), "image/png")
        if p.startswith("/mask/") and os.path.basename(p) in BASES:
            f = mask_file(os.path.basename(p))
            if os.path.exists(f):
                return self.send(open(f, "rb").read(), "image/png")
        self.send(b"not found", "text/plain", 404)

    def do_POST(self):
        d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if d.get("image") not in BASES:
            return self.send({"error": "bad image"}, code=400)
        try:
            if self.path == "/predict":
                return self.send(predict(d["image"], d["points"]))
            if self.path == "/save":
                save(d["image"], d["mask"])
                return self.send({"ok": True})
        except Exception as e:
            import traceback; traceback.print_exc()
            return self.send({"error": str(e)}, code=500)
        self.send({"error": "bad path"}, code=404)


if __name__ == "__main__":
    srv = HTTPServer(("127.0.0.1", PORT), H)
    if "--no-open" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    srv.serve_forever()
