"""Project already decoded current fields without re-reading legacy byte offsets."""
from scripts.game_data.levelscript_union_tags import short_name
from .record_hints import LEVELSCRIPT_RECORD_HINTS
from .audio_actions import project_typed_audio
from .fmv import project_typed_fmv
from .uid_records import typed_strings

def _constant(param):
 return param.get('value') if isinstance(param,dict) and param.get('paramSource')==0 else None

def _getter(param):
 return param.get('idRef') if isinstance(param,dict) and param.get('paramSource')==-1 and type(param.get('idRef')) is int and param['idRef']>=0 else None

def _operand(value):
 if isinstance(value,list):return [_operand(v) for v in value]
 local=_getter(value)
 return dict(operandKind='localGetterRef',getterLocalId=local) if local is not None else value

def project_record(record):
 node=record['typedNode'];fields=node['fields'];name=short_name(node['wrapperName'])
 common=7 if record['family']=='GetterBase' else 14 if record['family']=='ActionHeader' else 8
 own={k:v for k,v in list(fields.items())[common:]}
 label=LEVELSCRIPT_RECORD_HINTS.get((node['unionTag'],node['memberCount']),{}).get('label',name) if record['family']=='ActionBase' else name
 out=dict(label=label,typedFields=fields,payloadStart=hex(record['payloadStart']),payloadLength=record['end']-record['payloadStart'],
  memoryPackUnionTag=hex(node['unionTag']),serializedMemberCount=node['memberCount'],unionTagEncoding=record['unionTagEncoding'])
 if record['family']=='ActionHeader':
  out['actionHeader']={k:fields[k] for k in ('filterLevel','filterMask','filterMode','priority','triggerActiveDuring','validate') if k in fields}
  out['actionHeader']['nextId']=fields.get('nextID')
  validate=fields.get('validate')
  if isinstance(validate,dict):
   local=_getter(validate);shape='action-header-validate-constant' if validate.get('paramSource')==0 else 'action-header-validate-local-getter' if local is not None else 'action-header-validate-dynamic'
   out['actionHeader']['validateParam']={**validate,'payloadShape':shape}
   if local is not None:out['actionHeader']['validateGetterLocalId']=local
  out['nativeEventDetail']=dict(type=name,**own)
  if name=='LevelEvent_OnTeleportFinish':out['nativeEventDetail']['actionIdFilter']=_constant(fields.get('actionId'))
 if name in ('Split','Branch'):
  key='splitActionLocalIds' if name=='Split' else 'branchSequenceActionLocalIds';out[key]=fields['idList']
 if name=='IfElseAction':out.update(conditionParam=fields['condition'],conditionGetterLocalId=_getter(fields['condition']),trueActionLocalId=fields['onTrueID'],falseActionLocalId=fields['onFalseID'])
 if name=='WhileAction':out.update(whileConditionParam=fields['condition'],whileConditionActionLocalId=_getter(fields['condition']),whileDoActionLocalId=fields['doID'])
 if name in ('SwitchInt','SwitchIntLarger','SwitchString'):
  prefix={'SwitchInt':'switch','SwitchIntLarger':'switchIntLarger','SwitchString':'switchString'}[name]
  out.update({prefix+'ValueParam':fields['value'],prefix+'ValueGetterLocalId':_getter(fields['value']),prefix+'CaseValues':fields['caseValueList'],prefix+'CaseActionLocalIds':fields['caseIDList'],prefix+'DefaultActionLocalId':fields['defaultID']})
 if name=='StartDialogAction':
  param=fields['dialogId'];out['startDialogAction']=dict(dialogGetterLocalId=_getter(param),constantDialogId=_constant(param),paramSource=param.get('paramSource') if isinstance(param,dict) else None,path=param.get('path') if isinstance(param,dict) else None)
 if name=='CallServer':
  args=fields.get('eventArgsPtr');value=_constant(args)
  out['callServer']={**own,'eventName':_constant(fields['eventName']),'eventArgsPtr':{**(args or {}),'pathValue':value.get('key') if isinstance(value,dict) else None}}
 if name=='WaitForSecondsInTriggerVolume':out.update(waitSuccessActionLocalId=fields['successID'],waitFailActionLocalId=fields['failID'])
 if name=='RaiseCustomScriptEvent':out['raiseCustomScriptEvent']={**own,'eventKey':_constant(fields['eventKey'])}
 if record['family']=='ActionBase':
  fmv=project_typed_fmv(node,record['payloadStart'],record['end'])
  if fmv is not None:out['fmvAction']=fmv
  audio=project_typed_audio(node,own,out['payloadLength'])
  if audio is not None:out['audioAction']=audio
 if name in ('PlayLevelSequenceAction','PlayLevelSequenceAndControlSceneObjectsAction'):
  value=_constant(fields.get('levelSeqId'))
  if isinstance(value,str):out['levelSequenceId']=value
 out['taggedFields']=[dict(type='string',value=r['text'],offset=hex(r['offset']),field=r['field']) for r in typed_strings(node)]
 if record['family']=='GetterBase':
  key={'IntGetterRandom':'intRandom'}.get(name,name[:1].lower()+name[1:]);detail={k:_operand(v) for k,v in own.items()}
  if name=='GetterString':detail=_operand(fields['value'])
  if name=='ListGetValueString':
   detail={k:dict(v,bindingKind='constant' if v.get('paramSource')==0 else 'dynamic') if isinstance(v,dict) and 'paramSource' in v else v for k,v in detail.items()}
  if name in ('BoolGetterAnd','BoolGetterOr','BoolGetterInvert','BoolGetterMultiAnd'):
   detail['operation']={'BoolGetterAnd':'And','BoolGetterOr':'Or','BoolGetterInvert':'Not','BoolGetterMultiAnd':'All'}[name]
   if name=='BoolGetterMultiAnd':detail['values']=detail.pop('list')
  if 'comparer' in own:
   param=fields['comparer'];detail.update(comparerRaw=_constant(param),comparerName=param.get('enumName') if isinstance(param,dict) and param.get('paramSource')==0 else None)
  if name=='IntGetterRandom':detail={'minimum':_operand(fields['min']),'maximum':_operand(fields['max'])}
  if name=='GetMissionState':detail={'type':name,'missionId':_constant(fields['missionId']),'missionIdParam':fields['missionId']}
  out[key]=detail
 return out
