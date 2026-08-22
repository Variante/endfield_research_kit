"""Compare sparse current Unity Endminf renders with exact source viewport pixels.

This is a structural baseline only: ECC and bounded background statistics are
reported, never perceptual/visual equivalence. Source mask-zero pixels are
excluded and no pixels are synthesized.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[1]; REPO=ROOT.parent
VIEW=ROOT/'scratch/character_recovery/endminf_source_viewport'
SOURCE=VIEW/'endminf_source_viewport_original_bgr0.mkv'; MASK=VIEW/'endminf_source_viewport_validity_mask_gray.mkv'
ACTOR=ROOT/'scratch/character_recovery/actor_clips/endminf_actor_only.mkv'
RENDER=REPO/'scratch/charinfo_phase_sweep'; REPORT=ROOT/'tools/endminf_current_baseline_comparison.json'
DIFF=ROOT/'scratch/character_recovery/endminf_current_baseline_diagnostics'
CROP=(800,188,3000,2120); SOURCE_START=9783; FPS=60.0
CASES=(('loop_start',10117,'endmin_t0p133.png'),('loop_middle',10263,'endmin_t1p817.png'),('loop_end',10409,'endmin_t2p017.png'))
MISSING=('start','transition')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def frame(path,index):
    c=cv2.VideoCapture(str(path)); c.set(cv2.CAP_PROP_POS_FRAMES,index); ok,x=c.read(); c.release()
    if not ok: raise RuntimeError(f'cannot decode {path} frame {index}')
    return x
def ecc(a,b,mask):
    # ECC is a structural diagnostic; quarter-resolution keeps the checker
    # reproducible on ordinary CI hardware while retaining translation signal.
    a=cv2.resize(a,None,fx=.25,fy=.25,interpolation=cv2.INTER_AREA)
    b=cv2.resize(b,None,fx=.25,fy=.25,interpolation=cv2.INTER_AREA)
    mask=cv2.resize(mask,None,fx=.25,fy=.25,interpolation=cv2.INTER_NEAREST)
    ag=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY).astype('float32'); bg=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY).astype('float32')
    w=np.eye(2,3,dtype='float32'); valid=(mask>0).astype('uint8')
    score,solved=cv2.findTransformECC(ag,bg,w,cv2.MOTION_TRANSLATION,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,40,1e-5),valid,3)
    return round(float(score),6),[round(float(solved[0,2]*4),3),round(float(solved[1,2]*4),3)]
def verify() -> dict:
    for p in (SOURCE,MASK,ACTOR):
        if not p.is_file(): raise RuntimeError(f'missing viewport input: {p}')
    rows=[]
    for phase,src_frame,name in CASES:
        rp=RENDER/name
        if not rp.is_file(): raise RuntimeError(f'missing Unity render: {rp}')
        source_index=src_frame-SOURCE_START
        src=frame(SOURCE,source_index); mask=frame(MASK,source_index)
        actor=frame(ACTOR,source_index)
        unity=cv2.imread(str(rp),cv2.IMREAD_COLOR)
        if unity is None or unity.shape[:2] != (2160,3840): raise RuntimeError(f'bad Unity render: {rp}')
        unity=unity[CROP[1]:CROP[3],CROP[0]:CROP[2]]
        valid=mask[:,:,0] if mask.ndim==3 else mask
        # Source viewport and validity outputs are already the exact crop; only
        # the full-resolution Unity render and actor matte need cropping.
        valid_crop=valid
        actor_crop=actor[CROP[1]:CROP[3],CROP[0]:CROP[2]]
        actor_occlusion=np.max(actor_crop,axis=2)>8
        compare_mask=(valid_crop>0).astype('uint8')*255
        background_mask=(valid_crop>0) & ~actor_occlusion
        score,translation=ecc(src,unity,valid_crop)
        pixels=src[background_mask]
        if not len(pixels): raise RuntimeError(f'no unoccluded background pixels: {phase}')
        DIFF.mkdir(parents=True,exist_ok=True)
        diff_path=DIFF/f'{phase}_absdiff.png'
        cv2.imwrite(str(diff_path),np.minimum(cv2.absdiff(src,unity).astype(np.uint16)*4,255).astype(np.uint8))
        token=re.search(r'_t(\d+p\d+)\.png$',name).group(1).replace('p','.')
        rows.append({'phase':phase,'sourceFrame':src_frame,'sourceTimeSeconds':round(src_frame/FPS,6),'unityRender':name,'unityPhaseTimeSeconds':float(token),'phaseMapping':'nearest available Unity sample; not exact temporal equivalence','sourceSha256':sha(SOURCE),'actorMatteSha256':sha(ACTOR),'unitySha256':sha(rp),'validPixels':int((compare_mask>0).sum()),'backgroundPixels':int(background_mask.sum()),'eccTranslation':score,'translationPixels':translation,'sourceBackgroundMeanBgr':[round(float(v),4) for v in pixels.mean(axis=0)],'sourceBackgroundStdBgr':[round(float(v),4) for v in pixels.std(axis=0)],'diagnosticDiff':{'path':str(diff_path.relative_to(REPO)).replace('\\','/'),'sha256':sha(diff_path),'description':'4x absolute BGR difference in exact crop; diagnostic only'},'claim':'structural crop alignment only; source mask-zero and actor-occluded pixels excluded from background statistics; no perceptual equivalence'})
    return {'schema':'endfield.character-recovery.endminf-current-baseline.v1','status':'sparse_baseline','sourceViewport':{'path':str(VIEW.relative_to(REPO)).replace('\\','/'),'originalSha256':sha(SOURCE),'maskSha256':sha(MASK),'actorMattePath':str(ACTOR.relative_to(REPO)).replace('\\','/'),'actorMatteSha256':sha(ACTOR),'cropHalfOpen':list(CROP),'sourceFrameStart':SOURCE_START,'fps':FPS,'validityRule':'mask-zero excluded; actor matte excluded for background metrics; no pixels synthesized'},'unityPhaseRenders':{'root':str(RENDER.relative_to(REPO)).replace('\\','/'),'availablePhases':[r[0] for r in CASES],'missingPhases':list(MISSING),'phaseNote':'Current pinned Unity outputs are sparse loop samples; start and transition captures are absent and are not inferred.'},'comparisons':rows,'diagnostics':{'backgroundMismatch':'source-only bounded background statistics; Unity background mismatch is not isolated','actorRenderMismatch':'not isolated','perceptualEquivalence':False,'diffDirectory':str(DIFF.relative_to(REPO)).replace('\\','/')}}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--write',action='store_true'); ap.add_argument('--check',action='store_true'); ap.add_argument('--report',type=Path,default=REPORT); a=ap.parse_args()
    if a.write==a.check: ap.error('choose exactly one of --write/--check')
    try:
        result=verify(); text=json.dumps(result,indent=2)+"\n"
        if a.check and a.report.read_text(encoding='utf-8')!=text: raise RuntimeError('durable baseline report is stale')
        if a.write: a.report.write_text(text,encoding='utf-8')
        print(f"Endminf baseline {'written' if a.write else 'verified'}: {a.report}"); return 0
    except Exception as e: print(f'baseline_failed: {e}'); return 2
if __name__=='__main__': raise SystemExit(main())
