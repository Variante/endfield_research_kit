#!/usr/bin/env python3
"""Condense the build-locked EffectAnimation/EffectSetting native call map."""
import hashlib,json
from pathlib import Path
LAB=Path(__file__).resolve().parents[1]; REPO=LAB.parent
MAP=LAB/'scratch/character_recovery/endminf_effect_lifecycle/native_map.json'
SRC=REPO/'scratch/character_recovery/endminf_overview_effect_stage/GameObject/effect_nanguan_p3E1E69C789E16C79.json'
OUT=REPO/'reports/assets/endminf_effect_lifecycle_native_audit.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
 j=json.loads(MAP.read_text(encoding='utf-8')); rows=[]
 for x in j['bodyTargets']:
  calls=[]
  for c in x['directCalls']:
   for q in c.get('resolved',[]):
    name=q['type']+'.'+q['method']
    if name not in calls: calls.append(name)
  rows.append({'type':x['type'],'method':x['method'],'methodIndex':x['methodIndex'],'token':x['token'],'virtualAddress':x['methodPointerVa'],'fileOffset':x['fileOffset'],'scanBytes':x['scanBytes'],'calls':calls})
 return {'schema':'endfield.endminf-effect-lifecycle-native-audit.v1','status':'pinned_call_graph_closed_activation_gap_identified','inputs':{'nativeMapSha256':sha(MAP),'effectNanguanSourceSha256':sha(SRC),'gameAssemblySha256':'0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce','globalMetadataSha256':'90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e'},'methods':rows,'provenLifecycle':{'EffectAnimation.OnEnable':'base TickableMono.OnEnable only','EffectAnimation.OnDisable':'calls Stop','EffectAnimation.Init':'GetComponent<Animator>','EffectAnimation.ChangeAnimationState':'calls _PlayAnimation and synchronizes tick state','EffectAnimation._PlayAnimation':['creates PlayableGraph','samples AnimationClip on GameObject','enables Animator','sets clip length/input weight/time/play/time scale'],'EffectAnimation.Stop':['time scale reset','PlayableGraph.Stop','Animator culling mode update','tick synchronization'],'EffectSetting.PlayEffect':'iterates lodSetting and calls EffectLodCfg.Play','EffectSetting.StopEffect':'iterates lodSetting and calls EffectLodCfg.Stop','EffectSetting.Simulate':['iterates particles','ParticleSystem.Simulate','ParticleSystem.Play'],'EffectLodCfg.Play':['Renderer.enabled = stored render-init flag','ParticleSystem.Play(withChildren=true)','Animator.Play when controller exists'],'EffectLodCfg.SetGameObjectActive':['GameObject.SetActive(active)','stores current-active byte at this+0x59']},'activationConclusion':'EffectLodCfg.Play does not call GameObject.SetActive and EffectSetting.PlayEffect only calls EffectLodCfg.Play. A source-inactive effect_nanguan/Sphere hierarchy therefore remains inactive unless the separate LOD/display path invokes EffectLodCfg.SetGameObjectActive(true), or an animation active curve activates it. Calling PlayEffect alone in the lab cannot activate it.','implementationRule':'Before PlayEffect parity, reproduce the proven LOD/display SetGameObjectActive(true) decision for admitted EffectLodCfg rows; do not indiscriminately activate descendants.'}
if __name__=='__main__':
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(build(),indent=2)+'\n',encoding='utf-8');print(OUT)
