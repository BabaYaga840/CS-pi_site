"""Propagate the hand-picked masks through each source video with SAM 2 (video model).

usage: python3 propagate_masks.py <video-key> [...]      keys: project_fail gradient_guidance trust_fail cspi_success rejection
Writes video_masks/<key>.npz (packed boolean masks, one per frame) and a QC sheet.

Long clips are tracked in chunks so memory stays bounded: each chunk is seeded with the previous
chunk's final per-object masks. The saved mask is split into connected components (objects) so each
part (robot, canister, apple, ...) is tracked on its own; tiny specks are dropped.
"""
import os, sys, time
import cv2, numpy as np, torch
from transformers import Sam2VideoModel, Sam2VideoProcessor

HERE = os.path.dirname(os.path.abspath(__file__))
VID = os.path.join(HERE, "..")
# key -> (video file, seed frame index, mask file)
JOBS = {
    "project_fail": ("project_fail.mp4", 72, "7_projection_before_3s_mask.png"),
    "gradient_guidance": ("gradient_guidance.mp4", 168, "2_gradient_guidance_failure_mask.png"),
    "trust_fail": ("trust_fail.mp4", 48, "8_cspi_base_mask.png"),
    "cspi_success": ("cspi_success_0.mp4", 18, "5_cspi_mask.png"),
    "rejection": ("rejection.MOV", 0, "6_rejection_base_mask.png"),
}
CHUNK = 150
MIN_AREA = 0.002       # drop connected components smaller than 0.2% of the frame
MAX_OBJS = 8
MODEL = "facebook/sam2.1-hiera-large"
dev = "mps" if torch.backends.mps.is_available() else "cpu"


def read_frames(path, lo, hi):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, lo)
    out = []
    for _ in range(lo, hi):
        ok, f = cap.read()
        if not ok:
            break
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    return out


def split_objects(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    order = sorted(range(1, n), key=lambda i: -stats[i, cv2.CC_STAT_AREA])
    keep = [i for i in order if stats[i, cv2.CC_STAT_AREA] >= MIN_AREA * mask.size][:MAX_OBJS]
    return {k + 1: lab == i for k, i in enumerate(keep)}


def track(proc, model, frames, seed_local, seeds, reverse):
    """Track `seeds` {obj_id: mask} from frames[seed_local]; returns {local_idx: {obj_id: bool mask}}."""
    H, W = frames[0].shape[:2]
    sess = proc.init_video_session(video=frames, inference_device=dev, video_storage_device="cpu",
                                   processing_device="cpu", dtype=torch.float32)
    ids = list(seeds)
    proc.add_inputs_to_inference_session(inference_session=sess, frame_idx=seed_local, obj_ids=ids,
                                         input_masks=[seeds[i].astype(np.uint8) for i in ids], original_size=(H, W))
    res = {}
    with torch.no_grad():
        model(inference_session=sess, frame_idx=seed_local)   # encode the seeded frame into memory
        for out in model.propagate_in_video_iterator(sess, start_frame_idx=seed_local, reverse=reverse):
            m = proc.post_process_masks([out.pred_masks], original_sizes=[[H, W]], binarize=False)[0]
            m = m.cpu().numpy() > 0
            res[out.frame_idx] = {int(o): m[i].reshape(H, W) for i, o in enumerate(sess.obj_ids)}
    del sess
    if dev == "mps":
        torch.mps.empty_cache()
    return res


def run(key, proc, model):
    vfile, seed, mfile = JOBS[key]
    path = os.path.join(VID, vfile)
    cap = cv2.VideoCapture(path)
    T = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    mask0 = cv2.imread(os.path.join(HERE, "masks", mfile), 0) > 127
    objs = split_objects(mask0)
    print(f"[{key}] {T} frames, seed {seed}, {len(objs)} objects", flush=True)
    H, W = mask0.shape
    union = np.zeros((T, H, W), bool)
    t0 = time.time()

    def go(reverse):
        cur, cur_seeds = seed, objs
        while (cur < T - 1) if not reverse else (cur > 0):
            lo, hi = (cur, min(T, cur + CHUNK)) if not reverse else (max(0, cur - CHUNK + 1), cur + 1)
            frames = read_frames(path, lo, hi)
            hi = lo + len(frames)
            res = track(proc, model, frames, cur - lo, cur_seeds, reverse)
            for li, d in res.items():
                union[lo + li] |= np.any(list(d.values()), axis=0) if d else False
            end_local = (len(frames) - 1) if not reverse else 0
            nxt = res.get(end_local, {})
            # objects lost (empty mask) cannot seed the next chunk; keep the previous seeds for those ids
            cur_seeds = {o: nxt[o] if o in nxt and nxt[o].any() else cur_seeds[o] for o in cur_seeds}
            cur = lo + end_local
            print(f"  {'rev' if reverse else 'fwd'} chunk {lo}-{hi} done ({time.time()-t0:.0f}s)", flush=True)

    union[seed] = mask0
    if seed < T - 1:
        go(False)
    if seed > 0:
        go(True)
    os.makedirs(os.path.join(HERE, "video_masks"), exist_ok=True)
    np.savez_compressed(os.path.join(HERE, "video_masks", key + ".npz"), packed=np.packbits(union, axis=-1), shape=union.shape)
    print(f"[{key}] saved ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    keys = sys.argv[1:] or list(JOBS)
    proc = Sam2VideoProcessor.from_pretrained(MODEL)
    model = Sam2VideoModel.from_pretrained(MODEL).to(dev).eval()
    for k in keys:
        run(k, proc, model)
