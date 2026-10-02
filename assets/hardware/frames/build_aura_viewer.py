"""Build a self-contained interactive viewer (aura_viewer.html) from the start-position frame and the
obstacle / robot / apple masks picked in the segment picker.

usage: python3 build_aura_viewer.py [out.html]
Reads masks/1_start_position@{obstacle,robot,apple}_mask.png. Robot and apple pixels take priority over the obstacle
(they are never tinted), and the obstacle's distance field is computed from the obstacle mask without them.
"""
import base64, io, os, sys
import cv2, numpy as np
from scipy.ndimage import distance_transform_edt

HERE = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(HERE, "1_start_position.png")


MASKS = os.environ.get("AURA_MASKS_DIR", os.path.join(HERE, "masks"))


def mask(cls):
    f = os.path.join(MASKS, f"1_start_position@{cls}_mask.png")
    return cv2.imread(f, 0) > 127 if os.path.exists(f) else None


def b64png(arr):
    ok, buf = cv2.imencode(".png", arr)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Constraint aura viewer</title>
<style>
:root{--bg:#1e1e1e;--panel:#2b2b2b;--fg:#eee;--mut:#aaa}
body{margin:0;font:14px system-ui,sans-serif;background:var(--bg);color:var(--fg);display:flex;gap:16px;padding:16px;flex-wrap:wrap}
#view{flex:1 1 640px;min-width:0}
canvas{width:100%;height:auto;border:1px solid #555;display:block;background:#fff}
#panel{flex:0 0 320px;background:var(--panel);padding:14px;border-radius:8px;align-self:flex-start}
.row{margin-bottom:12px}.row label{display:flex;justify-content:space-between;color:var(--mut);margin-bottom:2px}
.row input[type=range]{width:100%}
h3{margin:0 0 10px;font-size:15px}
button,select{padding:6px 10px;border:0;border-radius:4px;background:#444;color:var(--fg);cursor:pointer}
button:hover{background:#666}button.primary{background:#2e7d32}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.chk{display:flex;gap:8px;align-items:center;margin-bottom:10px;color:var(--fg)}
</style></head><body>
<div id="view"><canvas id="c"></canvas></div>
<div id="panel">
<h3>Constraint aura</h3>
<div class="row"><label>Aura reach (px) <b id="v_reach"></b></label><input id="reach" type="range" min="0" max="200" step="1" value="70"></div>
<div class="row"><label>Aura strength <b id="v_aura"></b></label><input id="aura" type="range" min="0" max="1" step="0.01" value="0.7"></div>
<div class="row"><label>Aura falloff (higher = tighter) <b id="v_fall"></b></label><input id="fall" type="range" min="0.3" max="5" step="0.05" value="1.6"></div>
<div class="row"><label>Obstacle tint strength <b id="v_tint"></b></label><input id="tint" type="range" min="0" max="1" step="0.01" value="0.45"></div>
<div class="row"><label>Background opacity <b id="v_bg"></b></label><input id="bg" type="range" min="0" max="1" step="0.01" value="0.3"></div>
<div class="row"><label>Colour</label><input id="col" type="color" value="#e01818"></div>
<div class="chk"><input id="over" type="checkbox"><label for="over">Aura also over robot / apple</label></div>
<div class="row"><label>Preview backdrop</label><select id="back"><option value="#ffffff">White</option><option value="#202020">Dark</option><option value="checker">Checkerboard</option></select></div>
<div class="btns"><button id="dl" class="primary">Download PNG (transparent)</button><button id="reset">Reset</button><button id="copy">Copy settings</button></div>
<p style="color:var(--mut);font-size:12px;margin-top:14px">Robot and apple stay unchanged. Obstacles get the tint; the aura radiates from the full obstacle mask. Everything else is translucent (background opacity).</p>
</div>
<script>
const SRC={frame:"__FRAME__",obstacle:"__OBS__",robot:"__ROBOT__",apple:"__APPLE__",dist:"__DIST__"};
const DEF={reach:70,aura:.7,fall:1.6,tint:.45,bg:.3,col:"#e01818",over:false,back:"#ffffff"};
const $=id=>document.getElementById(id), cv=$("c"), ctx=cv.getContext("2d");
const load=u=>new Promise(r=>{const i=new Image();i.onload=()=>r(i);i.src=u});
function px(img){const c=document.createElement("canvas");c.width=img.naturalWidth;c.height=img.naturalHeight;const x=c.getContext("2d");x.drawImage(img,0,0);return x.getImageData(0,0,c.width,c.height)}
let W,H,base,obs,rob,app,dist,kind,out;
(async()=>{
  const [f,o,r,a,d]=await Promise.all([SRC.frame,SRC.obstacle,SRC.robot,SRC.apple,SRC.dist].map(load));
  base=px(f);W=base.width;H=base.height;cv.width=W;cv.height=H;
  obs=px(o).data;rob=px(r).data;app=px(a).data;dist=px(d).data;
  kind=new Uint8Array(W*H);// 0 background, 1 obstacle, 2 robot/apple (priority)
  for(let i=0;i<W*H;i++){kind[i]=(rob[i*4]>127||app[i*4]>127)?2:(obs[i*4]>127?1:0)}
  out=ctx.createImageData(W,H);render();
})();
const hex=h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
const P=()=>({reach:+$("reach").value,aura:+$("aura").value,fall:+$("fall").value,tint:+$("tint").value,bg:+$("bg").value,col:hex($("col").value),over:$("over").checked});
function render(){
  if(!out)return;const p=P(),o=out.data,b=base.data,col=p.col;
  for(let i=0;i<W*H;i++){const j=i*4,k=kind[i];
    let r=b[j],g=b[j+1],bl=b[j+2],al=1;
    if(k===0)al=p.bg;
    else if(k===1){r=r*(1-p.tint)+col[0]*p.tint;g=g*(1-p.tint)+col[1]*p.tint;bl=bl*(1-p.tint)+col[2]*p.tint}
    if(k!==1&&(k===0||p.over)&&p.reach>0&&p.aura>0){
      const d=dist[j];                                   // px distance from the obstacle mask (0 inside it)
      if(d>0&&d<p.reach){const t=1-d/p.reach,a=p.aura*Math.pow(t,p.fall),oa=al*(1-a)+a;
        r=(r*al*(1-a)+col[0]*a)/oa;g=(g*al*(1-a)+col[1]*a)/oa;bl=(bl*al*(1-a)+col[2]*a)/oa;al=oa}}
    o[j]=r;o[j+1]=g;o[j+2]=bl;o[j+3]=al*255}
  ctx.putImageData(out,0,0);
  for(const k of["reach","aura","fall","tint","bg"])$("v_"+k).textContent=$(k).value;
}
function backdrop(){const v=$("back").value;cv.style.background=v==="checker"?"repeating-conic-gradient(#ccc 0 25%,#fff 0 50%) 0 0/20px 20px":v}
for(const k of["reach","aura","fall","tint","bg","col","over"])$(k).addEventListener("input",render);
$("back").addEventListener("input",backdrop);
$("reset").onclick=()=>{for(const k of["reach","aura","fall","tint","bg","col"])$(k).value=DEF[k];$("over").checked=DEF.over;render()};
$("copy").onclick=()=>{const s=JSON.stringify({reach:+$("reach").value,aura:+$("aura").value,fall:+$("fall").value,tint:+$("tint").value,bg:+$("bg").value,colour:$("col").value,auraOverRobotApple:$("over").checked});
  navigator.clipboard&&navigator.clipboard.writeText(s);$("copy").textContent="Copied";setTimeout(()=>$("copy").textContent="Copy settings",1200)};
$("dl").onclick=()=>cv.toBlob(b=>{const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="start_position_aura.png";a.click()},"image/png");
backdrop();
</script></body></html>
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "aura_viewer.html")
    frame = cv2.imread(FRAME)
    obs, rob, app = mask("obstacle"), mask("robot"), mask("apple")
    missing = [n for n, m in (("obstacle", obs), ("robot", rob), ("apple", app)) if m is None]
    if missing:
        sys.exit(f"missing masks: {missing} (pick them in the segment picker first)")
    keep = rob | app
    obs_eff = obs & ~keep                                        # robot/apple win over the obstacle
    dist = distance_transform_edt(~obs_eff).clip(0, 255).round().astype(np.uint8)
    gray = lambda m: (m * 255).astype(np.uint8)
    html = (TEMPLATE.replace("__FRAME__", b64png(frame)).replace("__OBS__", b64png(gray(obs_eff)))
            .replace("__ROBOT__", b64png(gray(rob))).replace("__APPLE__", b64png(gray(app)))
            .replace("__DIST__", b64png(dist)))
    open(out, "w").write(html)
    print("wrote", out, f"({len(html) / 1e6:.1f} MB); obstacle {obs_eff.mean() * 100:.1f}%, robot {rob.mean() * 100:.1f}%, apple {app.mean() * 100:.1f}% of the frame")


if __name__ == "__main__":
    main()
