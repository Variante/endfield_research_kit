#!/usr/bin/env python3
"""Evaluate the native EffectLodCfg._RefreshLod bit-mask rule for Endminf."""
import argparse,json
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
SOURCE=REPO/'scratch/character_recovery/endminf_overview_effect_stage/MonoBehaviour/MonoBehaviour#299_pEE47385E2B7F6C79.json'
OUT=REPO/'reports/assets/endminf_effect_lod_evaluation.json'
def evaluate(setting_mask=15,target_mask=3,distance_index=0):
 j=json.loads(SOURCE.read_text(encoding='utf-8')); rows=[]
 for i,x in enumerate(j['lodSetting']):
  infos=x['_distanceLodInfos']; distance_active=bool(infos[distance_index]['isActive']) if infos else True
  active=bool(x['settingLodLevel']&setting_mask) and bool(x['targetLayer']&target_mask) and distance_active
  rows.append({'row':i,'gameObjectPathId':x['gameobject']['m_PathID'],'settingLodLevel':x['settingLodLevel'],'targetLayer':x['targetLayer'],'distanceActive':distance_active,'active':active})
 return {'schema':'endfield.effect-lod-evaluation.v1','nativeRule':'(settingLodLevel & showSettingLodLevel) != 0 && (targetLayer & showTargetLayers) != 0 && selectedDistanceInfo.isActive','inputs':{'showSettingLodLevel':setting_mask,'showTargetLayers':target_mask,'distanceIndex':distance_index,'isUseDistanceLod':j['isUseDistanceLod'],'isCullDisable':j['_isCullDisable'],'cullDistance':j['cullDis']},'cameraBoundary':'Camera position/distance is not consumed for this prefab because isUseDistanceLod=0 and _isCullDisable=1. Serialized distance row 0 remains selected.','rows':rows,'summary':{'active':sum(r['active'] for r in rows),'total':len(rows),'effectNanguanRow30Active':rows[30]['active']}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--setting-mask',type=int,default=15);p.add_argument('--target-mask',type=int,default=3);p.add_argument('--distance-index',type=int,default=0);a=p.parse_args();data=evaluate(a.setting_mask,a.target_mask,a.distance_index);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps(data['summary']))
