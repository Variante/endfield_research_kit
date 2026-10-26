"""Exact warmed Patrol checkpoint request program; helper effects stay separate.

This source owner authenticates the enclosing producer's actual typed calls,
literal keys, field/argument/local bit transfers and selected return. A typed
SetValue call is not a proof of blackboard storage, event dispatch, controller
activation or playback. Those effects and runtime replacement stay explicit.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

CONTROLLER='Beyond.Gameplay.AI.NewNpcAIPatrolController'
CORE='Beyond.Gameplay.Core.PatrolData'
ENTITY='Beyond.Gameplay.Core.Entity'
ENTITY_PTR='Beyond.Gameplay.Core.EntityPtr'
BLACKBOARD='Beyond.Gameplay.ParamBlackboard'


def producer_program(regions,entry,s,*,entity_offset,patrol_id_offset,event_key):
 if(type(entity_offset)is not int or not 128<=entity_offset<2**31 or type(patrol_id_offset)is not int
  or not 16<=patrol_id_offset<128 or type(event_key)is not int or not 0<=event_key<128):
  raise ValueError('patrolCheckpoint.nominal-field-or-event-key')
 entity=entity_offset.to_bytes(4,'little').hex();identity=bytes((patrol_id_offset,)).hex()
 g=BytesPath(regions,entry);typed={};keys={}
 def use(name,prefix):
  at=g.at;cell=g.relative(prefix);typed[name]=dict(instruction=at,cell=cell);return cell
 def key(name):
  at=g.at;cell=g.relative('488b15');keys[name]=dict(instruction=at,cell=cell)
 g.take('48895c2408','4889742410','57','4881ecc0000000','498bf8','8bf2','488bd9')
 ready=flag(g);g.branch('75',True,1);optional=g.relative('488b05')
 g.take('488b4838','4885c9');g.branch('74',True,1)
 g.take('48c78424e800000000000000','0f57c0','0f11442430','4533c0','488d9424e8000000','488d4c2420')
 g.call(s['allocate']);g.take('0f1000','f30f7f442430','48c744245000000000','488d442430','4889442458',
  '488bbc24e8000000','488b93'+entity,'4885ff');g.branch('0f84',False)
 if g.relative('488b05')!=optional:raise ValueError('patrolCheckpoint.same-optional-root')
 g.take('488b4868','4885c9');g.branch('74',True,1)
 use('objectPtrImplicit','4c8b05');g.take('488d4c2420');g.call(s['objectPtrImplicit'])
 g.take('0f57c0','33c0','0f11442460','0f11442470','4889842480000000','0f28442420','660f7f442420',
  '4533c0','488d542420','488d4c2460');g.call(s['entityPtrBuild'])
 g.take('0f10442460','0f29842490000000','0f104c2470','0f298c24a0000000','f20f10842480000000','f20f118424b0000000')
 use('setEntity','4c8b0d');g.take('4c8d842490000000');key('@event_sender');g.take('488bcf');g.call(s['setEntity'])
 g.take('488b8c24e8000000','4885c9');g.branch('0f84',False)
 g.take('4533c0','488b93'+entity);g.call(s['setReceiver'])
 g.take('488bbc24e8000000','b907000000','488bd3');g.call(s['patrolLookup'])
 g.take('4885c0');g.branch('0f84',False);g.take('4885ff');g.branch('0f84',False)
 use('setId','4c8b0d');g.take('448b40'+identity);key('id');g.take('488bcf');g.call(s['setInt'])
 g.take('488b8c24e8000000','4885c9');g.branch('0f84',False)
 use('setIndex','4c8b0d');g.take('448bc6');key('index');g.call(s['setInt'])
 g.take('488bbc24e8000000','488b93'+entity,'4885d2');g.branch('0f84',False)
 g.take('4533c0','488d4c2420');g.call(s['getPosition'])
 g.take('4885ff');g.branch('0f84',False)
 g.take('f20f1000','f20f11442440','8b4008','89442448')
 use('setPosition','4c8b0d');g.take('4c8d442440');key('position');g.take('488bcf');g.call(s['setPosition'])
 use('world','488b05');g.take('488b88b8000000','488b4940','4885c9');g.branch('74',False,1)
 g.take('4533c9','4c8b8424e8000000','418d51'+bytes((event_key,)).hex());g.call(s['raiseEvent'])
 g.take('90');use('dispose','488b15');g.take('488d4c2430');g.call(s['dispose']);g.jump('eb',1)
 g.take('b001','4c8d9c24c0000000','498b5b10','498b7318','498be3','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,optionalCallbackRootCell=optional,typedUsageSites=typed,literalKeySites=keys,
  incomingControllerRegister='rcx retained rbx',incomingCheckpointRegister='edx retained esi',eventKey=event_key,
  entityFieldOffset=entity_offset,patrolIdFieldOffset=patrol_id_offset,
  sourceTransfers=dict(sender='controller.entity -> ObjectPtr<Entity> result16 -> EntityPtr result40 -> complete16+16+8 local copy -> SetValue<EntityPtr>',
   receiver='same controller.entity -> actual EventParams.SetReceiver',patrolId='lookup selector7 on same controller -> exact CorePatrol.id DWORD -> SetValue<int>',
   checkpointIndex='incoming EDX retained ESI -> SetValue<int>',position='same controller.entity -> actual named get_position -> complete8+4 local copy -> SetValue<Vector3>'),
  eventParams='same stack output reference from allocation is reloaded for all four typed writes, receiver call and final request E8.R8',
  normalReturn=True,returnBool=True,entryRspRestored=True,allNonvolatilesRestored=True,
  typedBlackboardHelperEffectsProved=False,finalRequestMethodIdentityProved=False,eventDispatchObserved=False,checkpointProducerProved=False,wholeOwnerAdmitted=False,
  condition='Initialized metadata; stable nonnull optional callback root with both selected replacement receivers absent; compatible nonnull controller/entity/CorePatrol lookup/EventParams/world event-manager; normally returning exact helpers preserve Win64 nonvolatiles and return compatible result storage; source/local/frame storage is disjoint and stable. Only the selected normal request program is proved. Allocation, conversions, lookup selection, blackboard writes, disposal effects, actual dispatch and runtime invocation remain separate.')


def derive(image,pins):
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack import scalar_param_native as scalar,leveldata_patrol_consumer_sources as entries
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 need=lambda k,e,a:scalar.need('patrolCheckpoint',k,e,a)
 method,=[m for m in md.methods_for(ctx.index.types[CONTROLLER])if md.string(m.name_index)=='_RaiseCheckpointReachEvent'and m.parameter_count==1]
 scalar.owned_method_abi(image,ctx,method.index,method.declaring_type,('bool',2,False),[('int',8,False)],'patrolCheckpoint.producer')
 entity=ctx.field(CONTROLLER+'::m_entity');identity=ctx.field(CORE+'::id')
 need('nominal-entity-field',(CONTROLLER,ENTITY),entity[:2]);need('nominal-Core-id-field',(CORE,'int'),identity[:2])
 body=owned(image,image.method_pointer_va(method));calls={r['offset']:control_transfer(r)['target']for r in body['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8}
 offsets=dict(allocate=213,objectPtrImplicit=333,entityPtrBuild=385,setEntity=459,setReceiver=491,patrolLookup=512,
  setInt=556,getPosition=632,setPosition=685,raiseEvent=728,dispose=746)
 need('complete-finite-call-sites',True,all(at in calls for at in offsets.values()))
 symbols={key:calls[at]for key,at in offsets.items()};entry=entries.derive(image,pins);event_key=entry['eventKey']['program']['result']
 program=producer_program(body['regions'],body['pointer'],symbols,entity_offset=entity[2],patrol_id_offset=identity[2],event_key=event_key)
 typed={};canonical={}
 expected=dict(objectPtrImplicit=('Beyond.ObjectPtr`1','op_Implicit',[ENTITY],[]),
  setEntity=(BLACKBOARD,'SetValue',[],[ENTITY_PTR]),setId=(BLACKBOARD,'SetValue',[],['int']),
  setIndex=(BLACKBOARD,'SetValue',[],['int']),setPosition=(BLACKBOARD,'SetValue',[],['UnityEngine.Vector3']),
  dispose=('Beyond.ScopeStack`1+Scope`1','Dispose',['Beyond.Gameplay.Core.EventParams','Beyond.Gameplay.Core.EventParams'],[]))
 for role,(owner,name,classes,arguments)in expected.items():
  usage=derive_typed_usage_context(image,program['typedUsageSites'][role]['instruction']-base,label='patrolCheckpoint.'+role)
  need('exact-typed-request:'+role,(owner,name,classes,arguments),tuple(usage[k]for k in('typeName','methodName','classArguments','methodArguments')))
  typed[role]=usage
  if role.startswith('set'):
   registration=ge.resolve(usage['methodSpec'][0],classes,arguments);target=symbols['setInt'if role in('setId','setIndex')else role]
   need('actual-closed-SetValue-pointer:'+role,registration['pointer'],target);canonical[role]=registration
 world=derive_typed_usage_context(image,program['typedUsageSites']['world']['instruction']-base,label='patrolCheckpoint.world')
 need('exact-world-class',(1,'Beyond.Gameplay.Core.GameWorld'),(world['tag'],world['typeName']))
 literals={}
 for text,site in program['literalKeySites'].items():
  raw=image.pe.bytes_at_va(site['cell'],8);table=md.sections['stringLiteral'];pool=md.sections['stringLiteralData']
  index=unresolved_usage_index(raw,table.size//8,tag=5,source='patrolCheckpoint.literal',offset=site['cell'])
  offset,length=literal_record(md.buf[table.offset+index*8:table.offset+(index+1)*8],pool.size,source='patrolCheckpoint.literal',offset=index*8)
  payload=md.buf[pool.offset+offset:pool.offset+offset+length];need('exact-literal-key:'+text,text.encode('utf-8'),payload)
  literals[text]=dict(instructionRva=site['instruction']-base,usageCellRva=site['cell']-base,usageRawHex=raw.hex().upper(),
   literalIndex=index,literalPoolOffset=offset,literalBytes=length,literalHex=payload.hex().upper(),runtimeLiteralInitializationRequired=True)
 actual={}
 for role,owner,name in(('allocate','Beyond.Gameplay.Core.EventParams','Allocate'),('setReceiver','Beyond.Gameplay.Core.EventParams','SetReceiver'),
  ('getPosition',ENTITY,'get_position')):
  matches=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name and image.method_pointer_va(m)==symbols[role]]
  need('actual-named-call:'+role,1,len(matches));m=matches[0]
  # Parameter counts are recorded from the actual nominal declaration; this
  # source owner does not infer conversion or helper memory effects from them.
  actual[role]=dict(method=[m.index,owner,name,symbols[role]-base],parameterCount=m.parameter_count,
   resultType=ctx.type_name(m.return_type),helperEffectsProved=False)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-patrol-checkpoint-request-source.v1',status='validated-conditional-checkpoint-request-source',nativeInputs=pins,
  method=[method.index,CONTROLLER,'_RaiseCheckpointReachEvent',body['pointer']-base],sourceWindows=body['windows'],program=program,
  nominalFields=dict(entity=entity,patrolId=identity),typedRequests=typed,closedSetValueRegistrations=canonical,worldClass=world,literals=literals,
  namedCalls=actual,symbolRvas={k:v-base for k,v in symbols.items()},eventKey=entry['eventKey'],
  checkpointRequestSourceProved=True,checkpointProducerProved=False,checkpointFilterProved=False,
  controllerConversionProved=False,actionDispatchProved=False,wholeOwnerAdmitted=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Complete selected warmed checkpoint request byte program with four exact literal keys, independently typed closed SetValue calls, full entity40/position12 local copies, same field/argument/result references and event-key literal join.',
   conditional=program['condition'],unresolved=['allocation/conversion/lookup/blackboard/dispose helper effects','receiver/filter semantics and event manager Raise dispatch','controller activation and runtime invocation','enclosing whole owner/public receipts']))))
