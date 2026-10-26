"""Patrol lead-asset lookup call flow and selected nominal field transfers.

String construction/path processing, loader/handle effects and Unity validity
are independently selected helper results, never asset or live-object evidence.
Both actual null/non-null gait selections and the raw DWORD enum-zero speed
test remain explicit; the non-null path clears the selected Single sign bit.
Initialized metadata, compatible normal helper
ABIs, nonnull retained Core output and disabled collector are conditions.  Raw
enum, Single and LangKey bytes are copied without a wire or playback claim.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LEAD='Beyond.Gameplay.Core.PatrolLeadConfigSo'
CORE='Beyond.Gameplay.Core.PatrolData'
GAIT='Beyond.Gameplay.Core.PatrolGaitConfig'
CONFIG='Beyond.Gameplay.AI.Config.NpcPatrolData'
CONTROLLER='Beyond.Gameplay.AI.NewNpcAIPatrolController'
SCHEMA='endfield.story-patrol-lead-source.v1'
COPIES=(('stopWalkInplace','stopWalkInplace','bool',1),('motionType','motionType','Beyond.Gameplay.Core.MotionType',4),
 ('coolDownBetweenWalkAndStop','coolDownBetweenWalkAndStop','float',4),('turnCheckTime','turnCheckTime','float',4),
 ('turnCheck','turnCheck','bool',1),('turnCheckAngle','turnCheckAngle','float',4),('turnCheckDis','turnCheckDis','float',4),
 ('turnRadio','turnRadio','float',4),('gaitConfig','leadGaitConfig',GAIT,8),
 ('limitPlayerGait','changePlayerMoveStyle','bool',1),('limitPlayerGaitType','forcePlayerMoveStyle','Beyond.Gameplay.Core.MovementComponent+GroundedMoveGait',4),
 ('cameraControlState','cameraControlState','string',8),('langKeyEnter','langKeyEnter','Beyond.LangKey',16),('langKeyExit','langKeyExit','Beyond.LangKey',16),
 ('limitPlayerGaitEnterDis','motionEnterDis','float',4),('limitPlayerGaitLeaveDis','motionLeaveDis','float',4),
 ('limitPlayerGaitCD','motionChangeCd','float',4),('usePatrolPointEnterGaitAsLimitGait','usePatrolPointEnterGaitAsLimitGait','bool',1),
 ('playerChangeLimitDelayTime','playerChangeLimitDelayTime','float',4),('isLimitPlayerActionWhenGaitLimit','isLimitPlayerActionWhenGaitLimit','bool',1),
 ('limitPlayerActionType','limitPlayerActionType','Beyond.Gameplay.Core.PlayerController+InputActionType',4),('stop2WalkBufferTime','stop2WalkBufferTime','float',4))


def need(check,condition):
 if not condition:raise ValueError('storyPatrolLead.'+check)


def metadata_join(declarations):
 offsets={};claims=[]
 for source,target,typ,width in COPIES:
  for role,owner,name in (('lead',LEAD,source),('core',CORE,target)):
   f,=[r for r in declarations[owner]['fields']if r['name']==name]
   kind={'bool':2,'float':12,'string':14,GAIT:18}.get(typ,17)
   raw=bytes.fromhex(f['rawTypeHex']);field=f.get('field',[])
   need('exact-owned-field:'+owner+'::'+name,f.get('typeName')==typ and not f.get('attributes',0)&16
    and len(raw)==16 and raw[10]==kind and raw[11]==(128 if kind in (2,12,17)else 0)
    and len(field)==3 and field[:2]==[owner,typ]and type(field[2])is int and 16<=field[2]<2**31)
   offsets[role+'.'+name]=field[2]
  claims.append(dict(sourceField=LEAD+'::'+source,targetField=CORE+'::'+target,typeName=typ,bytes=width))
 for role,owner,name,typ in (('config',CONFIG,'leadConfigSoName','string'),('controller',CONTROLLER,'m_assetLoader','Beyond.Resource.IAssetLoader')):
  f,=[r for r in declarations[owner]['fields']if r['name']==name]
  need('exact-lookup-input-field:'+name,f['typeName']==typ and f['field'][:2]==[owner,typ]
   and bytes.fromhex(f['rawTypeHex'])[10:12]==bytes((14 if typ=='string'else 18,0)))
  offsets[role+'.'+name]=f['field'][2]
 if GAIT in declarations:
  for role,owner,name,typ,kind in (('gait',GAIT,'defaultGait','Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType',17),
   ('gait',GAIT,'npcStopDis','float',12),('gait',GAIT,'downgradeGaitDis','float',12),('gait',GAIT,'isStopDistance','bool',2),
   ('core',CORE,'waitDistance','float',12),('core',CORE,'isStopDistance','bool',2)):
   f,=[r for r in declarations[owner]['fields']if r['name']==name]
   need('exact-owned-gait-selection-field:'+name,f['typeName']==typ and not f.get('attributes',0)&16
    and f['field'][:2]==[owner,typ]and bytes.fromhex(f['rawTypeHex'])[10:12]==bytes((kind,128))
    and type(f['field'][2])is int and 16<=f['field'][2]<128)
   offsets[role+'.'+name]=f['field'][2]
 return dict(offsets=offsets,copies=claims,nonnullGaitBranchAdmitted=False)


def program(regions,entry,offsets,*,loaded,valid,gait_choice=None):
 need('literal-selected-loader-and-validity-results',type(loaded)is bool and type(valid)is bool and (loaded or not valid))
 need('literal-valid-gait-selection',gait_choice in (None,'zero','nonzero')and (gait_choice is None or valid))
 need('bounded-owned-field-operands',all(type(v)is int and 16<=v<2**31 for v in offsets.values()))
 b=lambda n:bytes((n,)).hex()
 d=lambda n:n.to_bytes(4,'little').hex()
 g=BytesPath(regions,entry);calls=[];contexts=[]
 def call(role):
  site=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=site,targetVa=target));return target
 def context(role,prefix):
  site=g.at;cell=g.relative(prefix);contexts.append(dict(role=role,instructionVa=site,cellVa=cell))
 def scalar(source,target,kind):
  g.take('488b03',('f30f1047'if kind=='float'else'8a4f'if kind=='bool'else'8b4f')+b(offsets['lead.'+source]),'4885c0')
  g.branch('0f84',False);slot=offsets['core.'+target]
  prefix=('f30f1140'if kind=='float'else'8848'if kind=='bool'else'8948')if slot<128 else('f30f1180'if kind=='float'else'8888'if kind=='bool'else'8988')
  g.take(prefix+(b(slot)if slot<128 else d(slot)))
 def reference(source,target):
  slot=offsets['core.'+target]
  g.take('488b0b','488b47'+b(offsets['lead.'+source]),'4885c9');g.branch('0f84',False)
  g.take('488981'+d(slot),'4881c1'+d(slot));call('publish-'+target)
 def key16(name):
  source=offsets['lead.'+name];target=offsets['core.'+name]
  g.take('488b0b',('0f1047'+b(source))if source<128 else('0f1087'+d(source)),'4885c9');g.branch('0f84',False)
  g.take('f30f7f81'+d(target),'4881c1'+d(target));call('publish-'+name)
 g.take('33ff');context('concat-MethodInfo','4c8b0d');context('concat-third-string','4c8b05')
 g.take('488b56'+b(offsets['config.leadConfigSoName']));context('concat-first-string','488b0d');call('concat-path')
 g.take('488bad'+d(offsets['controller.m_assetLoader']),'488bc8');call('process-path')
 g.take('4885ed');g.branch('0f84',False)
 context('TryLoad-MethodInfo','488b0d');g.take('4c8d4c2430','4c8bc0','488bd5');call('TryLoad')
 g.take('84c0');g.branch('74',not loaded,1)
 if loaded:
  context('Get-MethodInfo','488b15');g.take('488d4c2430');call('Get');g.take('488bf8')
 context('Unity-Object-type','488b0d');call('initialize-Unity-Object-type')
 g.take('4533c0','33d2','488bcf');call('Unity-object-not-equal-null')
 g.take('84c0');g.branch('0f84',not valid)
 if valid:
  g.take('488b03','4885ff');g.branch('0f84',False)
  g.take('8a4f'+b(offsets['lead.stopWalkInplace']),'4885c0');g.branch('0f84',False)
  g.take('8848'+b(offsets['core.stopWalkInplace']))
  scalar('motionType','motionType','enum')
  g.take('48837f'+b(offsets['lead.gaitConfig'])+'00');g.branch('74',gait_choice is None,1)
  if gait_choice is not None:
   g.take('488b47'+b(offsets['lead.gaitConfig']),'488b2b','8378'+b(offsets['gait.defaultGait'])+'00')
   g.branch('74',gait_choice=='zero',1)
   if gait_choice=='nonzero':g.take('f30f1070'+b(offsets['gait.npcStopDis']));g.jump('eb',1)
   else:
    g.take('4885c0');g.branch('0f84',False);g.take('f30f1070'+b(offsets['gait.downgradeGaitDis']))
   context('gait-math-type','488b0d');call('initialize-gait-math-type')
   g.take('4885ed');g.branch('0f84',False);gait_mask=g.relative('0f5435')
   g.take('f30f1175'+b(offsets['core.waitDistance']),'488b4f'+b(offsets['lead.gaitConfig']),'488b03','4885c9');g.branch('0f84',False)
   g.take('8a51'+b(offsets['gait.isStopDistance']),'4885c0');g.branch('0f84',False);g.take('8850'+b(offsets['core.isStopDistance']))
  else:gait_mask=None
  for source,target,kind in (('coolDownBetweenWalkAndStop','coolDownBetweenWalkAndStop','float'),('turnCheckTime','turnCheckTime','float'),
   ('turnCheck','turnCheck','bool'),('turnCheckAngle','turnCheckAngle','float'),('turnCheckDis','turnCheckDis','float'),('turnRadio','turnRadio','float')):
   scalar(source,target,kind)
  reference('gaitConfig','leadGaitConfig')
  g.take('4c8b0b','8a47'+b(offsets['lead.limitPlayerGait']),'4d85c9');g.branch('0f84',False)
  g.take('418841'+b(offsets['core.changePlayerMoveStyle']))
  scalar('limitPlayerGaitType','forcePlayerMoveStyle','enum');reference('cameraControlState','cameraControlState')
  key16('langKeyEnter');key16('langKeyExit')
  g.take('4c8b0b','f30f1047'+b(offsets['lead.limitPlayerGaitEnterDis']),'4d85c9');g.branch('0f84',False)
  g.take('f3410f1141'+b(offsets['core.motionEnterDis']))
  for source,target,kind in (('limitPlayerGaitLeaveDis','motionLeaveDis','float'),
   ('limitPlayerGaitCD','motionChangeCd','float'),('usePatrolPointEnterGaitAsLimitGait','usePatrolPointEnterGaitAsLimitGait','bool'),
   ('playerChangeLimitDelayTime','playerChangeLimitDelayTime','float'),('isLimitPlayerActionWhenGaitLimit','isLimitPlayerActionWhenGaitLimit','bool'),
   ('limitPlayerActionType','limitPlayerActionType','enum'),('stop2WalkBufferTime','stop2WalkBufferTime','float')):
   scalar(source,target,kind)
 return dict(selectedBytes=g.seen,start=entry,continuationInstructionVa=g.at,loaded=loaded,valid=valid,
  gaitConfigMustBeNull=valid and gait_choice is None,calls=calls,contexts=contexts,handleLocal=[48,68],
  handleOutputPassedToGetUnchanged=loaded,CoreOutputSlotRetainedInRbx=True,
  lookupPathAndHandleHelperEffectsProved=False,nonnullGaitBranchAdmitted=gait_choice is not None,
  gaitChoice=gait_choice,gaitRawSignMaskAddress=gait_mask if valid else None,
  rawLangKeyCopiesBytes=16 if valid else 0,wholeConversionProved=False,runtimeInvocationObserved=False,playbackProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,leveldata_patrol_point_sources as points
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 point=points.derive(image,pins);prefix=point['proof']['prefix'];selected_prefix=prefix['proof']['programs'][0]
 body=pointer.owned(image,base+prefix['proof']['metadataJoin']['method']['targetRva']);declarations={}
 for name in (LEAD,CORE,CONFIG,CONTROLLER,GAIT):
  td=ctx.index.types[name];need('own-ordinary-reference-owner:'+name,not ctx.is_value_type(name)and td.generic_container_index<0)
  fields=[]
  for f in md.fields_for(td):
   if ctx.field_attributes(f.type_index)&16:continue
   field=md.string(f.name_index);fields.append(dict(name=field,typeName=ctx.type_name(f.type_index),
    attributes=ctx.field_attributes(f.type_index),rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(f.type_index),16).hex().upper(),field=list(ctx.field(name+'::'+field))))
  declarations[name]=dict(typeDefinition=td.index,fields=fields)
 joined=metadata_join(declarations);enum_declarations={}
 for typ in sorted({t for a,b,t,w in COPIES if t not in ('bool','float','string',GAIT,'Beyond.LangKey')}|{'Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType'}):
  td=ctx.index.types[typ];backing,=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
  need('own-Int32-enum-copy:'+typ,ctx.is_enum(typ)and md.string(backing.name_index)=='value__'and ctx.type_name(backing.type_index)=='int')
  scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,'storyPatrolLead.enumBacking')
  enum_declarations[typ]=dict(typeDefinition=td.index,backingField=backing.index,backingType='int',wireGrammarAdmitted=False)
 gait_enum=next(f for f in declarations[GAIT]['fields']if f['name']=='defaultGait')
 need('same-exact-gait-enum-definition',int.from_bytes(bytes.fromhex(gait_enum['rawTypeHex'])[:8],'little')==
  enum_declarations['Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType']['typeDefinition'])
 lang='Beyond.LangKey';td=ctx.index.types[lang];fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 need('own-LangKey-value-layout',ctx.is_value_type(lang)and not ctx.is_enum(lang)
  and[(md.string(f.name_index),list(ctx.field(lang+'::'+md.string(f.name_index))))for f in fields]==
   [('key',[lang,'string',16]),('<rawText>k__BackingField',[lang,'string',24])])
 for f in fields:scalar.ordinary(image,ctx.type_pointer(f.type_index),14,'storyPatrolLead.LangKey',reference=True)
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 need('own-LangKey-managed16-size',image.pe.u32_at_va(size)==32)
 for row in joined['copies']:
  typ=row['typeName']
  if typ not in ('bool','float','string'):
   for owner,name in ((LEAD,row['sourceField'].split('::')[1]),(CORE,row['targetField'].split('::')[1])):
    f,=[r for r in declarations[owner]['fields']if r['name']==name]
    need('same-exact-nominal-copy-definition:'+name,int.from_bytes(bytes.fromhex(f['rawTypeHex'])[:8],'little')==ctx.index.types[typ].index)
 start=selected_prefix['continuationInstructionVa']
 programs=[program(body['regions'],start,joined['offsets'],loaded=loaded,valid=valid,gait_choice=choice)
  for loaded,valid,choice in ((False,False,None),(True,False,None),(True,True,None),(True,True,'zero'),(True,True,'nonzero'))]
 mask_addresses={p['gaitRawSignMaskAddress']for p in programs if p['nonnullGaitBranchAdmitted']}
 need('same-actual-raw-Single-sign-mask',len(mask_addresses)==1);mask=next(iter(mask_addresses));mask_raw=image.pe.bytes_at_va(mask,16)
 need('actual-Single-absolute-bit-mask',mask_raw[:4]==bytes.fromhex('FFFFFF7F'))
 continuation=point['proof']['programs'][0]['selectedBytes'][0][0]
 need('all-selected-lead-paths-rejoin-exact-actions-list-entry',all(p['continuationInstructionVa']==continuation for p in programs))
 usages={}
 for p in programs:
  for c in p['contexts']:
   role=c['role']
   if role not in ('concat-MethodInfo','TryLoad-MethodInfo','Get-MethodInfo','Unity-Object-type','gait-math-type'):continue
   u=derive_typed_usage_context(image,c['instructionVa']-base,label='storyPatrolLead.'+role)
   if role in usages:need('same-actual-typed-request:'+role,usages[role]==u)
   usages[role]=u
 for role,owner,name,args in (('concat-MethodInfo','Beyond.StringUtils','ZConcat',['string','string','string']),
  ('TryLoad-MethodInfo','Beyond.Resource.IAssetLoader','TryLoad',[LEAD]),('Get-MethodInfo','Beyond.Resource.FAssetProxyLoaderHandle','Get',[LEAD])):
  u=usages[role];need('own-exact-lookup-method-request:'+role,(u.get('tag'),u.get('typeName'),u.get('methodName'),u.get('classArguments'),u.get('methodArguments'))==(6,owner,name,[],args))
 u=usages['Unity-Object-type'];need('own-exact-Unity-Object-initialization',(u.get('tag'),u.get('typeName'))==(1,'UnityEngine.Object'))
 need('actual-gait-math-class-initialization-usage',usages['gait-math-type'].get('tag')==1)
 targets={}
 for p in programs:
  for call in p['calls']:
   role=call['role'];need('same-actual-helper-target:'+role,role not in targets or targets[role]==call['targetVa']);targets[role]=call['targetVa']
 barrier=selected_prefix['barrierTargetVa']
 need('same-independently-owned-collector-barrier-for-all-lead-references',all(target==barrier for role,target in targets.items()if role.startswith('publish-')))
 unity=ctx.index.types['UnityEngine.Object'];comparison,=[m for m in md.methods_for(unity)
  if md.string(m.name_index)=='op_Inequality'and image.method_pointer_va(m)==targets['Unity-object-not-equal-null']]
 parameters=list(md.parameters_for(comparison))
 need('own-static-Unity-Object-comparison',bool(comparison.flags&16)and comparison.generic_container_index<0
  and ctx.type_name(comparison.return_type)=='bool'and len(parameters)==2)
 scalar.ordinary(image,ctx.type_pointer(comparison.return_type),2,'storyPatrolLead.UnityComparison.return')
 for parameter in parameters:
  pointer_value=ctx.type_pointer(parameter.type_index)
  scalar.ordinary(image,pointer_value,18,'storyPatrolLead.UnityComparison.Object',reference=True)
  need('same-own-Unity-Object-parameter',ctx.type_name(parameter.type_index)=='UnityEngine.Object'
   and int.from_bytes(image.pe.bytes_at_va(pointer_value,8),'little')==unity.index)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-lead-lookup-and-gait-copies',nativeInputs=pins,
  proof=dict(pointTransfer=point,sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']],
   declarations=declarations,metadataJoin=joined,enumDeclarations=enum_declarations,
   LangKeyLayout=dict(typeDefinition=td.index,managedBytes=16,referenceOffsets=[0,8],boxedBytes=32,wireGrammarAdmitted=False),
   programs=programs,actualTypedUsages=usages,actualTargets={k:v-base for k,v in targets.items()},UnityComparisonMethodDefinition=comparison.index,
   gaitSignMask=dict(rva=mask-base,rawHex=mask_raw.hex().upper(),operation='selected raw Single DWORD AND 0x7fffffff')),
  selectedAssetLookupArgumentFlowProved=True,validLeadNullGaitCopiesProved=True,nonnullGaitBranchAdmitted=True,
  actualAssetOrLookupHelperEffectsProved=False,wholeConversionProved=False,wholeInitializerProved=False,
  runtimeInvocationObserved=False,playbackProved=False,evidenceBoundary=dict(exact='Exact own Lead/Core/Gait named scalar/reference/LangKey fields and actual lookup call/handle-local flow; complete selected absent/invalid/valid paths and both raw enum-zero gait choices rejoin the independently owned points-list entry.',
   conditional=__doc__,unresolved=['actual strings/path processing/asset-loader/handle and Unity-validity source effects','complete conversion/initializer/installed checkpoint/playback']))))
