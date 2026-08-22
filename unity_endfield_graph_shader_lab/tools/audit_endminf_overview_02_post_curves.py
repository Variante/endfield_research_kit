#!/usr/bin/env python3
"""Build-locked audit of Endminf overview-02 animated post-process curves."""
from __future__ import annotations

import hashlib, importlib.util, json, sys, zlib
from bisect import bisect_right
from pathlib import Path

LAB=Path(__file__).resolve().parents[1]; REPO=LAB.parent
CLIP=REPO/'scratch/character_recovery/endminf_overview_effect_stage/AnimationClip/A_fx_endminf_ui_overview_02_p74C3E18DD531CF7C.json'
GA=Path(r'D:/Program Files/Endfield Game/GameAssembly.dll')
MD=Path(r'D:/Program Files/Endfield Game/Endfield_Data/il2cpp_data/Metadata/global-metadata.dat')
OUT=REPO/'reports/assets/endminf_overview_02_post_curve_native_audit.json'
APPLY_MAP=LAB/'scratch/character_recovery/endminf_overview_02_post/native_apply_map.json'
EXPECTED={'ga':'0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce','md':'90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e'}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(s); sys.modules[name]=m; s.loader.exec_module(m); return m

def build():
 assert sha(GA)==EXPECTED['ga'] and sha(MD)==EXPECTED['md'], 'pinned native inputs mismatch'
 amap=load('bodymap',REPO/'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py')
 curves=load('curves',LAB/'tools/unity_animation_clip_scalar_curves.py')
 cat=amap.load_catalog_module(); md=cat.Metadata(MD); pe=amap.PeImage(GA)
 modules=amap.parse_codegen_modules(pe,amap.DEFAULT_CODE_REGISTRATION); ranges=amap.image_method_ranges(md)
 pointers,_=amap.build_pointer_indexes(pe,md,modules,ranges)
 allptr=sorted({p for rows in pointers.values() for p in rows if p})
 def native(mi):
  image='HG.RenderPipelines.Runtime.dll'; r=ranges[image]; ptr=pointers[image][mi-r['methodStart']]
  pos=bisect_right(allptr,ptr); nxt=allptr[pos] if pos<len(allptr) else ptr+4096; size=min(nxt-ptr,4096)
  off,reason,_=pe.file_offset_for_va(ptr)
  assert off is not None, reason
  body=bytes(pe.buf[off:off+size])
  return {'methodIndex':mi,'virtualAddress':f'0x{ptr:x}','fileOffset':f'0x{off:x}','boundedSizeBytes':size,'bodySha256':hashlib.sha256(body).hexdigest()}
 clip=json.loads(CLIP.read_text(encoding='utf-8')); decoded=curves.decode_scalar_curves(clip)
 types=[]
 for fullname,start,fields in [('HG.Rendering.Runtime.VFXPPChromaticAberration',265707,['_intensity','_useAsCenterPosition','_averageSteps']),('HG.Rendering.Runtime.VFXPPRadialBlur',265826,['_intensity','_useAsCenterPosition','_averageSteps','_power'])]:
  td=next(t for t in md.types if md.type_full_name(t)==fullname)
  methods=[]
  for i in range(td.method_start,td.method_start+td.method_count):
   sig=amap.method_signature(md,i); sig.update(native(i)); methods.append(sig)
  types.append({'fullName':fullname,'token':f'0x{td.token:08x}','fields':[{'name':f,'attributeCrc32':zlib.crc32(f.encode())&0xffffffff} for f in fields],'methods':methods})
 apply_semantics={
  'shared':{'profileCalls':['UnityEngine.Rendering.VolumeProfile.Has','UnityEngine.Rendering.VolumeProfile.TryGet'],'enabledWrite':{'targetOffset':'0x30','value':True},'intensityWrite':{'targetOffset':'0x40','source':'this+0x48 (_intensity)'},'centerModeSource':'this+0x4c (_useAsCenterPosition)','averageStepsSource':'this+0x4d (_averageSteps)','worldCenterSource':'Component.transform.position'},
  'HG.Rendering.Runtime.VFXPPChromaticAberration.Apply':{'targetType':'HG.Rendering.Runtime.HGChromaticAbberation','averageStepsTargetOffset':'0x48','enableGlobalCenterTargetOffset':'0x50','globalCenterTargetOffset':'0x58'},
  'HG.Rendering.Runtime.VFXPPRadialBlur.Apply':{'targetType':'HG.Rendering.Runtime.HGRadialBlur','powerWrite':{'targetOffset':'0x48','source':'this+0x50 (_power)'},'averageStepsTargetOffset':'0x50','enableGlobalCenterTargetOffset':'0x58','globalCenterTargetOffset':'0x60'},
  'setterEntryPoints':{'boolParameter':'0x180043df0','floatParameter':'0x180049310'},
  'orderingBoundary':'Each Apply only resolves and mutates its VolumeProfile component. These bodies contain no shader-global, material, draw, or pass calls. Cross-component render/composition order is outside these Apply bodies and remains unresolved.'}
 return {'schema':'endfield.endminf-overview-02-post-curves-native-audit.v2','status':'pinned_apply_writes_closed_composition_unresolved','inputs':{'gameAssembly':str(GA),'gameAssemblySha256':sha(GA),'globalMetadata':str(MD),'globalMetadataSha256':sha(MD),'clip':str(CLIP.relative_to(REPO)).replace('\\','/'),'clipSha256':sha(CLIP),'codeRegistrationVa':f'0x{amap.DEFAULT_CODE_REGISTRATION:x}','nativeApplyMap':str(APPLY_MAP.relative_to(LAB)).replace('\\','/'),'nativeApplyMapSha256':sha(APPLY_MAP)},'targetPath':{'name':'post (1)','crc32':669740077},'bindings':decoded,'resolvedMembers':{'2754484623':'_intensity','565374268':'_power'},'scriptTypes':types,'applySemantics':apply_semantics,'implementationBoundary':'Do not add a lab approximation yet: the exact render-pass producer and cross-component composition order are not established by these MonoBehaviour Apply methods.'}

if __name__=='__main__':
 data=json.dumps(build(),indent=2)+'\n'; OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(data,encoding='utf-8'); print(OUT)
