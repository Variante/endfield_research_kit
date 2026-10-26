"""Current checkpoint filter caller graph; blackboard/Param effects stay separate.

Exact owned bytes establish the selected normal branch, keys, nominal fields,
complete value copies and false exits. They do not establish the storage or
comparison semantics of the invoked helpers or any runtime event dispatch.
"""
from itertools import product
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.Actions.LevelEvent.OnNpcPatrolCheckpointReach'
ENTITY='Beyond.Gameplay.Core.EntityPtr'
BLACKBOARD='Beyond.Gameplay.ParamBlackboard'
VECTOR='UnityEngine.Vector3'
OUTPUT='Beyond.Gameplay.Actions.ParamOutput`1<'
PARAM='Beyond.Gameplay.Actions.Param`1<'
FIELDS={
 '_npcEntity':(OUTPUT+ENTITY+'>',128),'_patrolId':(OUTPUT+'int>',136),
 '_pointIndex':(OUTPUT+'int>',144),'_npcPosition':(OUTPUT+VECTOR+'>',152),
 '_filteredNpcEntity':(PARAM+ENTITY+'>',160),'_filteredPatrolId':(PARAM+'int>',168),
 '_filteredPointIndex':(PARAM+'int>',176),
}


def filter_program(regions,entry,s,*,field_offsets,mode_offset,filter_mode=False,
                   present=(False,False,False),mismatch=None,get_failure=None):
 if(field_offsets!={name:offset for name,(kind,offset)in FIELDS.items()}
  or any(type(v)is not int for v in field_offsets.values())or type(mode_offset)is not int or mode_offset!=108
  or type(filter_mode)is not bool or not isinstance(present,tuple)or len(present)!=3
  or any(type(v)is not bool for v in present)or mismatch not in(None,'entity','id','index')
  or get_failure not in(None,'entity','id','index','position')
  or(not filter_mode and(any(present)or mismatch is not None))
  or(mismatch is not None and not present[('entity','id','index').index(mismatch)])
  or(get_failure is not None and(filter_mode or any(present)or mismatch is not None))):
  raise ValueError('patrolCheckpointFilter.finite-literal-source-path')
 g=BytesPath(regions,entry);usages={};keys={}
 def use(role,prefix):
  usages[role]=dict(instruction=g.at,cell=g.relative(prefix))
 def key(name):
  keys[name]=dict(instruction=g.at,cell=g.relative('488b15'))
 def field(name,prefix):g.take(prefix+field_offsets[name].to_bytes(4,'little').hex())
 def finish(failed):
  if failed:g.take('32c0')
  g.take('4c8d9c2420010000','498b5b10','498b7318','498b7b20','498be3','5d','c3')
  return dict(selectedBytes=g.seen,metadataReadyFlag=ready,optionalCallbackRootCell=optional,
   typedUsageSites=usages,literalKeySites=keys,filterMode=filter_mode,presentFilters=list(present),
   mismatch=mismatch,failedBlackboardRead=get_failure,returnsLiteralFalse=failed,
   returnsBaseProcessResult=not failed,normalReturn=True,entryRspRestored=True,
   allNonvolatilesRestored=True,entityOutputCopyBytes=[16,16,8]if not filter_mode and get_failure is None else[],
   entityComparisonCopies=2 if filter_mode and present[0]else 0,
   positionOutputCopyBytes=[]if failed else[8,4],fieldOffsets=dict(field_offsets),filterModeOffset=mode_offset,
   blackboardHelperEffectsProved=False,paramHelperEffectsProved=False,entityComparisonSemanticsProved=False,
   checkpointFilterProved=False,runtimeInvocationObserved=False,wholeOwnerAdmitted=False,
   condition='Initialized metadata and a stable nonnull optional-callback root with absent selected receiver; '
    'compatible nonnull nominal action/blackboard/Param fields, sufficient disjoint initialized local storage and '
    'normally returning ABI-compatible helpers preserving nonvolatiles. The caller branches on actual helper '
    'Bool results and compares the two returned Int32 lanes; blackboard/Param/helper meaning and event invocation remain unproved.')
 g.take('488bc4','48895808','48897010','48897818','55','488d68d8','4881ec20010000')
 ready=flag(g);g.take('498bf0','488bfa','488bd9');g.branch('0f85',True)
 optional=g.relative('488b05');g.take('488b4830','4885c9');g.branch('74',True,1)
 g.take('33c0','0f57c0','48894580','894548','89442430','4889442440','89442448',
  '488945e0','89442434','89442438','0f11442460','0f11442470','0f1145c0','0f1145d0','4885ff')
 g.branch('75',True,1)
 for role,home,literal,helper in(('entity','4c8d442460','@event_receiver','getEntity'),
  ('id','4c8d4548','id','getInt'),('index','4c8d442430','index','getInt'),
  ('position','4c8d442440','position','getPosition')):
  use('get'+role.title(),'488b05');g.take(home);key(literal)
  g.take('4533c9','4889442428','488bcf','c644242000');g.call(s[helper]);g.take('84c0')
  failed=get_failure==role;g.branch('0f84',failed)
  if failed:return finish(True)
 g.take('807b'+bytes((mode_offset,)).hex()+'00');g.branch('75',filter_mode,1)
 if not filter_mode:
  g.take('0f10442460');field('_npcEntity','488b8b');g.take('488d5590','0f104c2470','0f294590',
   'f20f104580','f20f1145b0','0f294da0');g.call(s['outputEntity'])
  use('outputId','4c8b0d');g.take('41b001','8b5548');field('_patrolId','488b8b');g.call(s['outputInt'])
  use('outputIndex','4c8b0d');g.take('41b001','8b542430');field('_pointIndex','488b8b');g.call(s['outputInt']);g.jump('e9')
 else:
  use('filterEntity','4c8b0d');g.take('488d55c0');field('_filteredNpcEntity','488b8b')
  g.take('41b001');g.call(s['filterEntity']);g.take('84c0');g.branch('74',not present[0],1)
  if present[0]:
   g.take('0f10442460','4533c0','488d5590','0f104c2470','488d4df0','0f294590','f20f104580',
    '0f294da0','0f104dc0','f20f1145b0','0f1045d0','0f294df0','f20f104de0','0f294500','f20f114d10')
   g.call(s['entityDifferent']);g.take('84c0');g.branch('0f85',mismatch=='entity')
   if mismatch=='entity':return finish(True)
  for index,role,home,member,compare in((1,'id','488d542434','_filteredPatrolId',('8b4548','39442434')),
    (2,'index','488d542438','_filteredPointIndex',('8b442430','39442438'))):
   use('filter'+role.title(),'4c8b0d');g.take(home);field(member,'488b8b');g.take('41b001')
   g.call(s['filterInt']);g.take('84c0');g.branch('74',not present[index],1)
   if present[index]:
    g.take(*compare);g.branch('75',mismatch==role,1)
    if mismatch==role:return finish(True)
 g.take('f20f10442440','488d542450','8b442448');field('_npcPosition','488b8b')
 g.take('f20f11442450','89442458');g.call(s['outputPosition'])
 g.take('4533c0','488bd7','488bcb');g.call(s['baseProcess']);g.jump('eb',1)
 return finish(False)


def modes():
 result=[dict(),*[dict(get_failure=role)for role in('entity','id','index','position')]]
 result.extend(dict(filter_mode=True,present=p)for p in product((False,True),repeat=3))
 result.extend(dict(filter_mode=True,present=(True,True,True),mismatch=role)for role in('entity','id','index'))
 return result


def derive(image,pins):
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack import scalar_param_native as scalar
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 need=lambda k,e,a:scalar.need('patrolCheckpointFilter',k,e,a)
 method,=[m for m in md.methods_for(ctx.index.types[TYPE])if md.string(m.name_index)=='Process'and m.parameter_count==1]
 scalar.owned_method_abi(image,ctx,method.index,method.declaring_type,('bool',2,False),[(BLACKBOARD,18,True)],'patrolCheckpointFilter.Process')
 fields={name:ctx.field(TYPE+'::'+name)for name in FIELDS}
 need('all-seven-nominal-fields',[(TYPE,kind,offset)for kind,offset in FIELDS.values()],list(fields.values()))
 ancestors=[];current=TYPE;mode_fields=[]
 for _ in range(16):
  if not current or current=='object':break
  ancestors.append(current)
  for field in md.fields_for(ctx.index.types[current]):
   if md.string(field.name_index)!='_filterMode':continue
   actual=ctx.field(current+'::_filterMode');scalar.ordinary(image,ctx.type_pointer(field.type_index),2,'patrolCheckpointFilter.mode')
   mode_fields.append(actual)
  current=ctx.parent(current)
 need('one-actual-inherited-filter-mode',1,len(mode_fields));need('owned-filter-mode-offset',('bool',108),mode_fields[0][1:])
 body=owned(image,image.method_pointer_va(method));calls={row['offset']:control_transfer(row)['target']for row in body['rows']
  if len(bytes.fromhex(row['bytes']))==5 and bytes.fromhex(row['bytes'])[0]==0xe8}
 sites=dict(getEntity=352,getInt=399,getPosition=495,outputEntity=553,outputInt=578,
  filterEntity=635,entityDifferent=709,filterInt=744,outputPosition=835,baseProcess=849)
 need('exact-call-sites',True,all(n in calls for n in sites.values()))
 symbols={role:calls[at]for role,at in sites.items()}
 need('same-two-int-reads',calls[399],calls[447]);need('same-two-int-outputs',calls[578],calls[604])
 need('same-two-int-filters',calls[744],calls[784])
 programs=[filter_program(body['regions'],body['pointer'],symbols,field_offsets={name:row[2]for name,row in fields.items()},
  mode_offset=mode_fields[0][2],**mode)for mode in modes()]
 all_usages={role:site for program in programs for role,site in program['typedUsageSites'].items()};typed={};registrations={}
 expected={**{'get'+r.title():(BLACKBOARD,'TryGetValue',t)for r,t in(('entity',ENTITY),('id','int'),('index','int'),('position',VECTOR))},
  **{'output'+r:('Beyond.Gameplay.Actions.ParamOutputExtensions','SetValue','int')for r in('Id','Index')},
  **{'filter'+r.title():('Beyond.Gameplay.Actions.ParamExtensions','TryGetValue',t)for r,t in(('entity',ENTITY),('id','int'),('index','int'))}}
 for role,site in all_usages.items():
  usage=derive_typed_usage_context(image,site['instruction']-base,label='patrolCheckpointFilter.'+role)
  owner,name,argument=expected[role]
  need('exact-typed-request:'+role,(6,owner,name,[],[argument]),tuple(usage[k]for k in('tag','typeName','methodName','classArguments','methodArguments')))
  typed[role]=usage;canonical=ge.resolve(usage['methodSpec'][0],[],[argument])
  helper=('getInt'if role in('getId','getIndex')else'outputInt'if role.startswith('output')else
   'filterInt'if role in('filterId','filterIndex')else role)
  registrations[role]=dict(canonical=canonical,actualTargetRva=symbols[helper]-base,
   closedPointerEquivalenceProved=canonical['pointer']==symbols[helper],helperEffectsProved=False)
 literals={}
 for program in programs:
  for text,site in program['literalKeySites'].items():
   raw=image.pe.bytes_at_va(site['cell'],8);table=md.sections['stringLiteral'];pool=md.sections['stringLiteralData']
   index=unresolved_usage_index(raw,table.size//8,tag=5,source='patrolCheckpointFilter.literal',offset=site['cell'])
   offset,length=literal_record(md.buf[table.offset+index*8:table.offset+(index+1)*8],pool.size,source='patrolCheckpointFilter.literal',offset=index*8)
   payload=md.buf[pool.offset+offset:pool.offset+offset+length];need('exact-literal:'+text,text.encode(),payload)
   literals[text]=dict(instructionRva=site['instruction']-base,usageCellRva=site['cell']-base,literalIndex=index,literalHex=payload.hex().upper(),runtimeInitializationRequired=True)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-patrol-checkpoint-filter-caller-source.v1',
  status='validated-conditional-checkpoint-filter-caller-source',nativeInputs=pins,
  method=[method.index,TYPE,'Process',body['pointer']-base],sourceWindows=body['windows'],programs=programs,
  fields=fields,modeField=mode_fields[0],actualAncestorChain=ancestors,typedRequests=typed,
  helperRegistrations=registrations,literals=literals,symbolRvas={k:v-base for k,v in symbols.items()},
  filterCallerSourceProved=True,checkpointFilterProved=False,checkpointProducerProved=False,
  wholeOwnerAdmitted=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Owned warmed caller graph: four exact keys/typed reads and false exits, nominal filter/output fields, all eight optional-filter combinations, entity mismatch helper Bool branch, exact two Int32 comparisons, complete entity40/position12 local/output copies and normally restored returns.',
   conditional=programs[0]['condition'],unresolved=['blackboard/Param/output/helper effects and selected callbacks','entity comparison semantics','base Process effects and event dispatch','runtime invocation and playback','enclosing owner/public receipts']))))
