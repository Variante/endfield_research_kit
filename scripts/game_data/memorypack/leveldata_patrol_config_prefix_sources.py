"""Exact initial Config NPC to Core Patrol copies, before the conversion tail.

Only the NewNpcAIPatrolController method is selected. The identically named
base controller method is independent. Initialized metadata, absent replacement
or an empty replacement slot, nonnull compatible inputs/allocation, a normally
returning own constructor and disabled unchanged write barrier are conditions.
The later asset lookup, optional settings, nested action conversion, installed
controller field, initializer selection and runtime invocation remain open.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

SCHEMA='endfield.story-patrol-config-prefix.v1'
CONTROLLER='Beyond.Gameplay.AI.NewNpcAIPatrolController'
BASE='Beyond.Gameplay.AI.NpcAIPatrolController'
CONFIG='Beyond.Gameplay.AI.Config.NpcPatrolData'
CORE='Beyond.Gameplay.Core.PatrolData'
COPIES=(('patrolId','id','int',4,'ecx'),('loop','loop','Beyond.Gameplay.Core.PatrolLoopType',4,'ecx'),
 ('enableBornAction','enableBornAction','bool',1,'cl'),('enableBornSpeedOverride','enableBornSpeedOverride','bool',1,'cl'),
 ('bornOverrideSpeed','bornOverrideSpeed','float',4,'xmm0'),
 ('bornMoveStyle','bornMoveStyle','Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType',4,'ecx'),
 ('forbidNpcInteract','forbidNpcInteract','bool',1,'cl'),('pauseActionWhenPatrolDisabled','pauseActionWhenPatrolDisabled','bool',1,'cl'))


def need(check,condition):
 if not condition:raise ValueError('storyPatrolConfigPrefix.'+check)


def metadata_join(declarations):
 """Exact named ordinary owners/fields/ABI; no source addresses are inferred."""
 own=declarations[CONTROLLER];config=declarations[CONFIG];core=declarations[CORE]
 need('own-new-controller-not-base',own.get('parent')==BASE and type(own.get('typeDefinition'))is int)
 method,=[m for m in own['methods']if m['name']=='_ConvertNpcPatrolData']
 ctor,=[m for m in core['methods']if m['name']=='.ctor'and m['parameters']==[]]
 need('own-instance-void-conversion',method['flags']&16==0 and method['resultType']=='void'
  and[(p['typeName'],bytes.fromhex(p['rawTypeHex'])[10:12])for p in method['parameters']]==[(CONFIG,bytes((18,0))),(CORE,bytes((18,32)))])
 for row,nominal in zip(method['parameters'],(config,core),strict=True):
  need('same-actual-nominal-parameter',int.from_bytes(bytes.fromhex(row['rawTypeHex'])[:8],'little')==nominal['typeDefinition'])
 need('own-instance-zeroargument-Core-constructor',ctor['flags']&16==0 and ctor['resultType']=='void'
  and type(ctor.get('targetRva'))is int and ctor['targetRva']>0)
 offsets={};fields=[]
 for old,new,typename,width,register in COPIES:
  for owner,row,name,kind in((CONFIG,config,old,'config'),(CORE,core,new,'core')):
   field,=[f for f in row['fields']if f['name']==name]
   raw=bytes.fromhex(field.get('rawTypeHex',''));expected_kind={'int':8,'bool':2,'float':12}.get(typename,17)
   need('exact-owned-copy-field:'+owner+'::'+name,field.get('typeName')==typename and field.get('attributes',0)&16==0
    and len(raw)==16 and raw[10:12]==bytes((expected_kind,128))
    and isinstance(field.get('field'),(tuple,list))and tuple(field['field'][:2])==(owner,typename)
    and type(field['field'][2])is int and 16<=field['field'][2]<128)
   offsets[kind+'.'+name]=field['field'][2]
  fields.append(dict(sourceField=CONFIG+'::'+old,targetField=CORE+'::'+new,typeName=typename,bytes=width))
 for name,value in(('newPatrolData',1),('addBornPositionAsCheckpoint',0)):
  field,=[f for f in core['fields']if f['name']==name]
  raw=bytes.fromhex(field.get('rawTypeHex',''))
  need('exact-owned-constant-bool:'+name,field.get('typeName')=='bool'and field.get('attributes',0)&16==0
   and len(raw)==16 and raw[10:12]==bytes((2,128))
   and tuple(field['field'][:2])==(CORE,'bool')and type(field['field'][2])is int and 16<=field['field'][2]<2**31)
  offsets['core.'+name]=field['field'][2]
 return dict(method=method,constructor=ctor,offsets=offsets,copies=fields,
  constants=[dict(targetField=CORE+'::newPatrolData',bytes=1,value=1),dict(targetField=CORE+'::addBornPositionAsCheckpoint',bytes=1,value=0)])


def program(regions,entry,offsets,*,replacement_table_absent=True):
 """Initialized warm entry through the last direct Config scalar copy only."""
 need('literal-selected-replacement-path',type(replacement_table_absent)is bool)
 need('literal-small-scalar-field-slots',all(type(offsets.get(k))is int and 16<=offsets[k]<128
  for old,new,t,w,r in COPIES for k in('config.'+old,'core.'+new)))
 b=lambda n:bytes((n,)).hex()
 g=BytesPath(regions,entry)
 g.take('488bc4','48895808','48896810','48897018','48897820','4156','4883ec60')
 initialized=flag(g,'803d');g.take('498bf9','0f2970e8','498bd8','488bf2','488be9');g.branch('0f85',True)
 replacement=g.relative('488b05');g.take('488b4838','4885c9');g.branch('74',replacement_table_absent,1)
 if not replacement_table_absent:g.take('488b81109d0000','4885c0');g.branch('74',True,1)
 allocation_site=g.at;allocation_cell=g.relative('488b0d')
 g.take('0f57c0','33c0','0f11442430','89442440');allocate_site=g.at;allocate=g.relative('e8')
 g.take('488bf8','4885c0');g.branch('0f84',False)
 g.take('33d2','488bc8');ctor_site=g.at;ctor=g.relative('e8')
 g.take('488bcb','48893b');barrier_site=g.at;barrier=g.relative('e8')
 g.take('4c8b0b','4d85c9');g.branch('0f84',False)
 new=offsets['core.newPatrolData'];need('literal-new-patrol-field',type(new)is int and 128<=new<2**31)
 g.take('41c681'+new.to_bytes(4,'little').hex()+'01')
 for index,(old,new,typename,width,register)in enumerate(COPIES):
  g.take('488b03')
  if index==0:g.take('4885f6');g.branch('0f84',False)
  source=b(offsets['config.'+old]);target=b(offsets['core.'+new])
  g.take(('f30f1046'if register=='xmm0'else'8a4e'if width==1 else'8b4e')+source,'4885c0')
  g.branch('0f84',False)
  g.take(('f30f1140'if register=='xmm0'else'8848'if width==1 else'8948')+target)
 g.take('488b03','4885c0');g.branch('0f84',False)
 clear=offsets['core.addBornPositionAsCheckpoint'];need('literal-born-checkpoint-field',type(clear)is int and 16<=clear<128)
 g.take('c640'+b(clear)+'00')
 return dict(selectedBytes=g.seen,entryVa=entry,continuationInstructionVa=g.at,
  initializedMetadataFlagCellVa=initialized,replacementTableCellVa=replacement,replacementTableAbsent=replacement_table_absent,
  replacementSlotEmptyRequired=not replacement_table_absent,
  allocationUsageInstructionVa=allocation_site,allocationTypeCellVa=allocation_cell,
  allocationInstructionVa=allocate_site,allocationTargetVa=allocate,constructorInstructionVa=ctor_site,constructorTargetVa=ctor,
  outputReferenceStore='incoming R8 output slot via RBX receives unchanged allocation reference preserved in RDI',
  barrierInstructionVa=barrier_site,barrierTargetVa=barrier,constructorMethodInfoZero=True,
  sourceConfigRegister='incoming RDX via RSI',outputSlotRegister='incoming R8 via RBX',
  completePrefixArgumentFlowProved=True,normalReturnProved=False,wholeConversionProved=False,
  allocationClassUsageSourceRequired=True,normalCompatibleAllocationRequired=True,normalOwnConstructorRequired=True,
  independentDisabledBarrierSourceRequired=True,controllerInstallationProved=False,checkpointProducerProved=False,
  checkpointFilterProved=False,playbackProved=False,runtimeInvocationObserved=False)


def derive(image,pins):
 """Fresh selected-image prefix only; never a complete conversion capability."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer
 _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base;declarations={}
 for name in(CONTROLLER,CONFIG,CORE):
  td=ctx.index.types[name];need('ordinary-nongeneric-class:'+name,not ctx.is_value_type(name)and td.generic_container_index<0)
  fields=[]
  for f in md.fields_for(td):
   if ctx.field_attributes(f.type_index)&16:continue
   field=md.string(f.name_index);fields.append(dict(name=field,typeName=ctx.type_name(f.type_index),
    attributes=ctx.field_attributes(f.type_index),rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(f.type_index),16).hex().upper(),field=list(ctx.field(name+'::'+field))))
  methods=[]
  for m in md.methods_for(td):
   if md.string(m.name_index)not in('_ConvertNpcPatrolData','.ctor'):continue
   need('nongeneric-ordinary-void-method',m.generic_container_index<0);ctx.require_ordinary_kind(m.return_type,1)
   methods.append(dict(index=m.index,name=md.string(m.name_index),flags=m.flags,resultType=ctx.type_name(m.return_type),
    parameters=[dict(typeName=ctx.type_name(p.type_index),rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16).hex().upper())for p in md.parameters_for(m)],
    targetRva=image.method_pointer_va(m)-base))
  declarations[name]=dict(typeDefinition=td.index,parent=ctx.parent(name),fields=fields,methods=methods)
 joined=metadata_join(declarations);body=pointer.owned(image,base+joined['method']['targetRva'])
 programs=[program(body['regions'],body['pointer'],joined['offsets'],replacement_table_absent=absent)for absent in(True,False)]
 need('same-own-Core-constructor',all(p['constructorTargetVa']==base+joined['constructor']['targetRva']for p in programs))
 usage=derive_typed_usage_context(image,programs[0]['allocationUsageInstructionVa']-base,label='storyPatrolConfigPrefix.actualAllocation')
 need('actual-Core-type-allocation-request',usage.get('tag')==1 and usage.get('typeName')==CORE)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-initial-copy-prefix',nativeInputs=pins,
  proof=dict(declarations=declarations,metadataJoin=joined,sourceWindows=body['windows'],
   sourceRegions=[(a,data.hex().upper())for a,data in body['regions']],programs=programs,allocationUsage=usage),
  initialCopySourceProved=True,wholeConversionProved=False,controllerInstallationProved=False,initializerSelectionProved=False,
  checkpointProducerProved=False,checkpointFilterProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Only NewNpcAIPatrolController own typed Config/Core byref ABI, own Core constructor target, eight literal scalar copy operations and two literal bool assignments before the conversion tail.',
   conditional=__doc__,structuralOnly='Unchanged scalar bits; no enum or runtime patrol interpretation.',
   unresolved=['later asset/config lookup and optional fields','nested action-list conversion','actual controller data setter and initializer path','independent allocator/constructor/barrier effects','runtime invocation/checkpoints/playback']))))
