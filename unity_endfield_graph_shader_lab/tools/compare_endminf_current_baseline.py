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
ACTOR_MANIFEST=ROOT/'scratch/character_recovery/actor_clips/actor_matte_manifest.json'
VIEW_CONTRACT=ROOT/'tools/endminf_source_viewport_contract.json'
RENDER=REPO/'scratch/charinfo_phase_sweep'; REPORT=ROOT/'tools/endminf_current_baseline_comparison.json'
DIFF=ROOT/'scratch/character_recovery/endminf_current_baseline_diagnostics'
CROP=(800,188,3000,2120); SOURCE_START=9783; ACTOR_START=9767; FPS=60.0
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
    for p in (SOURCE,MASK,ACTOR,ACTOR_MANIFEST,VIEW_CONTRACT):
        if not p.is_file(): raise RuntimeError(f'missing viewport input: {p}')
    am=json.loads(ACTOR_MANIFEST.read_text(encoding='utf-8'))
    actor_row=next(x for x in am['actors'] if x['actor']=='endminf')
    if actor_row['sourceFrameRange'] != [ACTOR_START,10499]: raise RuntimeError('actor manifest frame pin drift')
    if actor_row['clip'] != str(ACTOR.relative_to(REPO)).replace('\\','/'): raise RuntimeError('actor manifest clip pin drift')
    vc=json.loads(VIEW_CONTRACT.read_text(encoding='utf-8'))
    rows=[]
    for phase,src_frame,name in CASES:
        rp=RENDER/name
        if not rp.is_file(): raise RuntimeError(f'missing Unity render: {rp}')
        source_index=src_frame-SOURCE_START
        src=frame(SOURCE,source_index); mask=frame(MASK,source_index)
        actor=frame(ACTOR,src_frame-ACTOR_START)
        unity=cv2.imread(str(rp),cv2.IMREAD_COLOR)
        if unity is None or unity.shape[:2] != (2160,3840): raise RuntimeError(f'bad Unity render: {rp}')
        unity=unity[CROP[1]:CROP[3],CROP[0]:CROP[2]]
        background_path=rp.with_name(rp.stem+'_background_only.png')
        background=cv2.imread(str(background_path),cv2.IMREAD_COLOR)
        if background is None or background.shape[:2] != (2160,3840): raise RuntimeError(f'missing/bad Unity background capture: {background_path}')
        background=background[CROP[1]:CROP[3],CROP[0]:CROP[2]]
        valid=mask[:,:,0] if mask.ndim==3 else mask
        # Source viewport and validity outputs are already the exact crop; only
        # the full-resolution Unity render and actor matte need cropping.
        valid_crop=valid
        actor_crop=actor[CROP[1]:CROP[3],CROP[0]:CROP[2]]
        actor_occlusion=np.max(actor_crop,axis=2)>8
        kernel=np.ones((9,9),np.uint8)
        common=(valid_crop>0) & (cv2.dilate(actor_occlusion.astype(np.uint8),kernel)==0)
        compare_mask=(valid_crop>0).astype('uint8')*255
        background_mask=(valid_crop>0) & ~actor_occlusion
        score,translation=ecc(src,unity,valid_crop)
        pixels=src[background_mask]
        if not len(pixels): raise RuntimeError(f'no unoccluded background pixels: {phase}')
        DIFF.mkdir(parents=True,exist_ok=True)
        diff_path=DIFF/f'{phase}_absdiff.png'
        cv2.imwrite(str(diff_path),np.minimum(cv2.absdiff(src,unity).astype(np.uint16)*4,255).astype(np.uint8))
        token=re.search(r'_t(\d+p\d+)\.png$',name).group(1).replace('p','.')
        paired_src=src[common]; paired_unity=background[common]; delta=np.abs(paired_src.astype(np.int16)-paired_unity.astype(np.int16))
        rows.append({'phase':phase,'sourceFrame':src_frame,'sourceTimeSeconds':round(src_frame/FPS,6),'unityRender':name,'unityPhaseTimeSeconds':float(token),'phaseMapping':'explicitly unpaired; temporal correspondence unknown','sourceSha256':sha(SOURCE),'actorMatteSha256':sha(ACTOR),'unitySha256':sha(rp),'unityBackgroundOnlySha256':sha(background_path),'validPixels':int((compare_mask>0).sum()),'backgroundPixels':int(background_mask.sum()),'commonMaskPixels':int(common.sum()),'eccTranslation':score,'translationPixels':translation,'sourceBackgroundMeanBgr':[round(float(v),4) for v in pixels.mean(axis=0)],'sourceBackgroundStdBgr':[round(float(v),4) for v in pixels.std(axis=0)],'pairedBgrMeanSource':[round(float(v),4) for v in paired_src.mean(axis=0)],'pairedBgrMeanUnityBackground':[round(float(v),4) for v in paired_unity.mean(axis=0)],'pairedMaeBgr':round(float(delta.mean()),4),'pairedP95Bgr':round(float(np.percentile(delta,95)),4),'diagnosticDiff':{'path':str(diff_path.relative_to(REPO)).replace('\\','/'),'sha256':sha(diff_path),'description':'4x absolute BGR difference in exact crop; diagnostic only'},'claim':'background-only structural diagnostic; unpaired samples are excluded from phase-quality claims and no actor/perceptual equivalence is asserted'})
    return {'schema':'endfield.character-recovery.endminf-current-baseline.v1','status':'sparse_unpaired_baseline','sourceViewport':{'path':str(VIEW.relative_to(REPO)).replace('\\','/'),'contractSha256':sha(VIEW_CONTRACT),'originalSha256':sha(SOURCE),'maskSha256':sha(MASK),'actorMattePath':str(ACTOR.relative_to(REPO)).replace('\\','/'),'actorMatteManifestSha256':sha(ACTOR_MANIFEST),'actorMatteSha256':sha(ACTOR),'actorSourceFrameStart':ACTOR_START,'cropHalfOpen':list(CROP),'sourceFrameStart':SOURCE_START,'fps':FPS,'validityRule':'common mask = source-valid & not dilated source actor; dilation=9; Unity background-only capture supplies the paired pixels; prior object-ID masks are rejected'},'unityPhaseRenders':{'root':str(RENDER.relative_to(REPO)).replace('\\','/'),'availablePhases':[r[0] for r in CASES],'missingPhases':list(MISSING),'phaseNote':'Current outputs are sparse and explicitly unpaired; start and transition captures are absent.'},'comparisons':rows,'diagnostics':{'backgroundMismatch':'paired background-only BGR metrics are structural diagnostics only','actorRenderMismatch':'not measured without exact temporal bridge','perceptualEquivalence':False,'priorObjectIdMasks':'rejected: SRP replacement/readback path was alpha-inaccurate and produced invalid full-frame masks','diffDirectory':str(DIFF.relative_to(REPO)).replace('\\','/'),'phaseQualityClaims':False}}
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
