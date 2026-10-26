"""Finite Config-point to Core-action source transfers inside New Patrol.

No serialized-list framing, conversion-wide field effects or runtime callback
selection is supplied here. The selected loop requires a stable nonnegative
SafeCount result, successful normal allocations/constructors, compatible points
and enough list capacity for the independently replayed Add fast path.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

SCHEMA='endfield.story-patrol-point-transfer-source.v1'
CONTROLLER='Beyond.Gameplay.AI.NewNpcAIPatrolController'
CONFIG='Beyond.Gameplay.AI.Config.NpcPatrolData'
POINT='Beyond.Gameplay.AI.Config.NpcPatrolPoint'
CORE='Beyond.Gameplay.Core.PatrolData'
ACTION='Beyond.Gameplay.Core.PatrolAction'
GAIT='Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType'
LIST='System.Collections.Generic.List`1'


def need(key,condition):
 if not condition:raise ValueError('storyPatrolPoints.'+key)


def item_program(regions,entry,*,items,size):
 """The actual closed reference GetItem's complete successful entry program."""
 need('literal-owned-List-reference-field-slots',all(type(n)is int and 16<=n<128 for n in(items,size)))
 b=lambda n:bytes((n,)).hex();g=BytesPath(regions,entry)
 g.take('4883ec28','3b51'+b(size));g.branch('73',False,1)
 g.take('488b41'+b(items),'4885c0');g.branch('74',False,1)
 g.take('3b5018');g.branch('73',False,1)
 g.take('4863ca','488b44c820','4883c428','c3')
 return dict(selectedBytes=g.seen,listItemsOffset=items,listSizeOffset=size,arrayLengthOffset=24,arrayDataOffset=32,
  elementBytes=8,inputReceiver='RCX',inputIndex='EDX',resultRegister='RAX',referenceBitsUnchanged=True,
  unsignedIndexWithinListAndArrayRequired=True,nonnullCompatibleListAndArrayRequired=True,
  entryRspRestored=True,nonvolatilesUnchanged=True,normalReturn=True,wireGrammarAdmitted=False)


def add_program(regions,entry,*,items,size,version,disabled):
 """Actual reference Add with enough capacity and the collector disabled."""
 need('literal-owned-List-add-fields',all(type(n)is int and 16<=n<128 for n in(items,size,version))and type(disabled)is int and disabled>0)
 b=lambda n:bytes((n,)).hex();g=BytesPath(regions,entry)
 g.take('48895c2410','48896c2418','56','57','4156','4883ec20','ff41'+b(version),
  '498be8','488b79'+b(items),'4c8bf2','486359'+b(size),'488bf1','4885ff');g.branch('0f84',False)
 g.take('3b5f18');g.branch('72',True,1)
 g.take('8d4301','8941'+b(size),'3b5f18');g.branch('73',False,1)
 need('same-independently-disabled-collector',flag(g,'833d')==disabled);g.take('4c8974df20');g.branch('74',True,1)
 g.take('488b5c2448','488b6c2450','4883c420','415e','5f','5e','c3')
 return dict(selectedBytes=g.seen,listItemsOffset=items,listSizeOffset=size,listVersionOffset=version,
  incomingReference='RDX saved whole in R14',arrayDataOffset=32,elementBytes=8,
  versionIncrementCount=1,sizeIncrementCount=1,wholeReferenceStoredUnchanged=True,
  unchangedOldArrayEntriesRequired=True,sufficientCapacityRequired=True,disabledCollectorRequired=True,
  growPathAdmitted=False,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],normalReturn=True,
  wireGrammarAdmitted=False)


def storage_program(regions,entry,*,role,disabled=None):
 """Read storage displacements from the actual method, never generic offsets.

 The complete method replay below owns every access. These are operational
 array/count/version roles, not a claim about an inflated runtime FieldInfo.
 """
 need('one-literal-list-storage-role',role in('point-get-item','action-add'))
 g=BytesPath(regions,entry)
 if role=='point-get-item':
  g.take('4883ec28','3b51');size=int.from_bytes(g.read(1),'little',signed=True)
  g.branch('73',False,1);g.take('488b41');items=int.from_bytes(g.read(1),'little',signed=True)
  need('disjoint-reference-array-and-count-storage',16<=items<128 and 16<=size<128
   and(items+8<=size or size+4<=items))
  program=item_program(regions,entry,items=items,size=size)
 else:
  g.take('48895c2410','48896c2418','56','57','4156','4883ec20','ff41')
  version=int.from_bytes(g.read(1),'little',signed=True);g.take('498be8','488b79')
  items=int.from_bytes(g.read(1),'little',signed=True);g.take('4c8bf2','486359')
  size=int.from_bytes(g.read(1),'little',signed=True)
  spans=[(items,items+8),(size,size+4),(version,version+4)]
  need('disjoint-reference-array-count-and-version-storage',all(16<=a<b<=128 for a,b in spans)
   and all(b<=c or d<=a for i,(a,b)in enumerate(spans)for c,d in spans[i+1:]))
  program=add_program(regions,entry,items=items,size=size,version=version,disabled=disabled)
 return dict(program=program,storageDisplacementsFromActualInstructions=True,
  openGenericOffsetsRead=False,namedFieldOffsetsClaimed=False,runtimeInflatedLayoutObserved=False)


def loop_program(regions,entry,offsets,*,count):
 """Whole selected actions-list creation and zero/positive point-loop paths."""
 need('bounded-loop-witness',type(count)is int and 0<=count<=3)
 need('literal-owned-point-copy-slots',set(offsets)=={'points','actions','pointPosition','actionPosition','pointSubActions','actionSubActions','pointGait','actionGait'}
  and all(type(n)is int and 16<=n<120 for n in offsets.values()))
 b=lambda n:bytes((n,)).hex();g=BytesPath(regions,entry);calls=[];contexts=[]
 def call(role):
  at=g.at;target=g.relative('e8');calls.append(dict(role=role,instructionVa=at,targetVa=target));return target
 def context(role,prefix):
  at=g.at;cell=g.relative(prefix);contexts.append(dict(role=role,instructionVa=at,cellVa=cell))
 context('actions-list-allocation','488b0d');g.take('488b3b');call('allocate-actions-list')
 g.take('488be8','4885c0');g.branch('0f84',False)
 context('actions-list-constructor','488b15');g.take('488bc8');call('construct-actions-list')
 g.take('4885ff');g.branch('0f84',False)
 g.take('488d4f'+b(offsets['actions']),'48896f'+b(offsets['actions']));call('publish-actions-list-barrier')
 initial=g.at;g.take('33ed');head=g.at;steps=[];backedge=None
 for index in range(count+1):
  context('points-safe-count','488b15');g.take('488b4e'+b(offsets['points']));call('points-safe-count')
  g.take('3be8');g.branch('0f8d',index==count)
  if index==count:break
  start=g.at;g.take('488b4e'+b(offsets['points']),'4885c9');g.branch('0f84',False)
  context('point-get-item','4c8b05');g.take('8bd5');call('point-get-item')
  context('action-allocation','488b0d');g.take('4c8bf0');call('allocate-action')
  g.take('488bf8','4885c0');g.branch('74',False,1)
  g.take('33d2','488bc8');call('construct-action');g.take('4d85f6');g.branch('74',False,1)
  g.take('418b4e'+b(offsets['pointPosition']+8),'f2410f1046'+b(offsets['pointPosition']),
   'f20f1147'+b(offsets['actionPosition']),'894f'+b(offsets['actionPosition']+8),
   '488d4f'+b(offsets['actionSubActions']),'498b46'+b(offsets['pointSubActions']),'488947'+b(offsets['actionSubActions']))
  call('publish-subactions-barrier')
  g.take('458b4e'+b(offsets['pointGait']),'44894f'+b(offsets['actionGait']),
   '488b0b','4885c9');g.branch('74',False,1)
  g.take('488b49'+b(offsets['actions']),'4885c9');g.branch('74',False,1)
  context('action-add','4c8b05');g.take('488bd7');call('action-add');increment=g.at;g.take('ffc5');backedge=g.at
  need('same-whole-loop-entry',g.relative('e9')==head);g.at=head
  steps.append(dict(pointIndex=index,bodyInstructionVa=start,incrementInstructionVa=increment))
 g.take('0f28742450','4c8d5c2460','498b5b10','498b6b18','498b7320','498b7b28','498be3','415e','c3')
 return dict(selectedBytes=g.seen,countWitness=count,initialInstructionVa=initial,loopEntryVa=head,backedgeVa=backedge,
  calls=calls,contexts=contexts,pointTransfers=steps,positionSlices=[[0,8],[8,4]],gaitBytes=4,subActionsReferenceBytes=8,
  loopCounter='EBP',counterInitialValue=0,counterIncrement=1,countSource='the exact SafeCount helper on Config.points at each test',
  stableNonnegativeCountAndInputsRequired=True,normalSuccessfulHelpersRequired=True,disabledCollectorRequired=True,
  actionsListPublishedBeforeLoop=True,orderedPointTransferSourceProved=True,selectedNormalExitBytesProved=True,
  entryFrameProved=False,helperEffectsProved=False,wholeConversionProved=False,wireGrammarAdmitted=False,
  runtimeInvocationObserved=False,playbackProved=False)


def induction(programs,*,count_limit=4096):
 """Own top-tested loop; no bottom-tested counted-source profile is borrowed."""
 need('finite-stable-count-domain',type(count_limit)is int and 3<=count_limit<=10000)
 need('exact-four-count-witnesses',len(programs)==4 and sorted(p['countWitness']for p in programs)==[0,1,2,3])
 by={p['countWitness']:p for p in programs};one=by[1];rows=one['selectedBytes'];initial=one['initialInstructionVa'];head=one['loopEntryVa'];edge=one['backedgeVa']
 need('same-counter-head-and-entry',all(p['initialInstructionVa']==initial and p['loopEntryVa']==head for p in programs))
 start=next(i for i,(a,h)in enumerate(rows)if a==head);end=next(i for i,(a,h)in enumerate(rows)if a==edge)+2
 prefix,body,suffix=rows[:start],rows[start:end],rows[end:]
 need('literal-initialize-increment-top-test-and-backedge',sum(h=='33ed'for _,h in prefix)==1 and sum(h=='ffc5'for _,h in body)==1
  and body[-3][1]=='ffc5'and body[-2][1]=='e9'and len(bytes.fromhex(body[-1][1]))==4 and suffix[-1][1]=='c3')
 for count in range(4):
  need('exact-repeat-of-whole-top-tested-body',by[count]['selectedBytes']==prefix+body*count+suffix
   and len(by[count]['pointTransfers'])==count and sum(c['role']=='points-safe-count'for c in by[count]['calls'])==count+1)
 return dict(countLimit=count_limit,countRange=[0,count_limit],counter='EBP',loopEntryVa=head,wholeBody=body,
  witnesses=[0,1,2,3],byteIdenticalIterationProved=True,orderedPointTransfersProved=True,noSignedOverflow=count_limit<2**31-1,
  condition='Every SafeCount invocation returns the same nonnegative bound; all inputs stay stable and exact independently owned GetItem/Add/constructor/allocation sources return normally under capacity/ABI/disjoint-storage conditions. This certificate does not establish those helper choices or effects.')


def derive(image,pins,*,count_limit=4096):
 """Fresh own method/nominal/context/callee joins; no report supplies facts."""
 import struct
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_tracking_list_sources import list_field_declarations
 from scripts.game_data.memorypack.leveldata_patrol_config_prefix_sources import derive as derive_prefix
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 prefix=derive_prefix(image,pins);caller=pointer.owned(image,base+prefix['proof']['metadataJoin']['method']['targetRva'])
 expected=(('points',CONFIG,'points',LIST+'<'+POINT+'>',21),('actions',CORE,'actions',LIST+'<'+ACTION+'>',21),
  ('pointPosition',POINT,'position','UnityEngine.Vector3',17),('actionPosition',ACTION,'position','UnityEngine.Vector3',17),
  ('pointSubActions',POINT,'actions',LIST+'<Beyond.Gameplay.Core.PatrolSubAction>',21),
  ('actionSubActions',ACTION,'subActions',LIST+'<Beyond.Gameplay.Core.PatrolSubAction>',21),
  ('pointGait',POINT,'enterGait',GAIT,17),('actionGait',ACTION,'enterGait',GAIT,17))
 offsets={};fields=[]
 for role,owner,name,typ,kind in expected:
  td=ctx.index.types[owner];need('own-ordinary-reference-owner:'+owner,not ctx.is_value_type(owner)and td.generic_container_index<0)
  field,=[f for f in md.fields_for(td)if md.string(f.name_index)==name and not ctx.field_attributes(f.type_index)&16]
  fact=list(ctx.field(owner+'::'+name));need('exact-owned-field:'+role,fact[:2]==[owner,typ])
  scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'storyPatrolPoints.'+role,reference=kind==21)
  offsets[role]=fact[2];fields.append(dict(role=role,field=fact,rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()))
 enum=ctx.index.types[GAIT];backing,=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
 need('own-Int32-gait-enum',ctx.is_enum(GAIT)and md.string(backing.name_index)=='value__'and ctx.type_name(backing.type_index)=='int')
 scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,'storyPatrolPoints.gaitBacking')
 vector=ctx.index.types['UnityEngine.Vector3'];vf=[f for f in md.fields_for(vector)if not ctx.field_attributes(f.type_index)&16]
 need('own-Vector3-three-Single-fields',ctx.is_value_type('UnityEngine.Vector3')and not ctx.is_enum('UnityEngine.Vector3')
  and[(md.string(f.name_index),*ctx.field('UnityEngine.Vector3::'+md.string(f.name_index))[1:])for f in vf]==[(a,'float',16+i*4)for i,a in enumerate(('x','y','z'))])
 for f in vf:scalar.ordinary(image,ctx.type_pointer(f.type_index),12,'storyPatrolPoints.Vector3')
 sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+vector.index*8)
 need('exact-own-Vector3-size',(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))==(28,12))
 starts=[]
 for row in caller['rows']:
  raw=bytes.fromhex(row['bytes'])
  if len(raw)!=7 or raw[:3]!=bytes.fromhex('488b0d'):continue
  try:usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='storyPatrolPoints.actionsList')
  except ValueError:continue
  if(usage.get('tag'),usage.get('typeName'))==(1,LIST+'<'+ACTION+'>'):starts.append(int(row['va'],16))
 need('one-actual-actions-list-allocation-context',len(starts)==1)
 programs=[loop_program(caller['regions'],starts[0],offsets,count=n)for n in range(4)]
 proof_induction=induction(programs,count_limit=count_limit);selected=programs[1]
 usages={r['role']:derive_typed_usage_context(image,r['instructionVa']-base,label='storyPatrolPoints.'+r['role'])for r in selected['contexts']}
 for role,owner,name,ca,ma in(('actions-list-constructor',LIST,'.ctor',[ACTION],[]),
  ('points-safe-count','Beyond.CollectionExtensions','SafeCount',[],[POINT]),
  ('point-get-item',LIST,'get_Item',[POINT],[]),('action-add',LIST,'Add',[ACTION],[])):
  usage=usages[role]
  need('exact-actual-closed-method:'+role,tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==(6,owner,name,ca,ma))
 need('own-action-allocation-class',tuple(usages['action-allocation'].get(k)for k in('tag','typeName'))==(1,ACTION))
 targets={}
 for p in programs:
  for call in p['calls']:
   role=call['role'];need('one-stable-actual-target-per-role:'+role,role not in targets or targets[role]==call['targetVa']);targets[role]=call['targetVa']
 ctor,=[m for m in md.methods_for(ctx.index.types[ACTION])if md.string(m.name_index)=='.ctor'and not m.parameter_count and not m.flags&16]
 scalar.owned_method_abi(image,ctx,ctor.index,ctor.declaring_type,('void',1,False),[],'storyPatrolPoints.actionCtor')
 need('actual-own-named-action-constructor',image.method_pointer_va(ctor)==targets['construct-action'])
 need('same-selected-typed-allocation-and-barrier-helper',targets['allocate-action']==targets['allocate-actions-list']
  and targets['publish-subactions-barrier']==targets['publish-actions-list-barrier'])
 barrier=_barrier(image,targets['publish-subactions-barrier']);disabled=base+barrier['result']['disabledFlagRva']
 list_td=ctx.index.types[LIST];section=md.sections['genericContainers'];container=struct.unpack_from('<iiii',md.buf,section.offset+list_td.generic_container_index*16)
 need('own-single-type-parameter-List-definition',container[:3]==(list_td.index,1,0))
 declarations=[]
 for name,kind in(('_items',29),('_size',8),('_version',8)):
  field,=[f for f in md.fields_for(list_td)if md.string(f.name_index)==name]
  scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'storyPatrolPoints.List.'+name,reference=kind==29)
  declarations.append(dict(owner=LIST,field=name,definition=field.index,
   typeRawHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()))
 variable,=[f for f in md.fields_for(list_td)if md.string(f.name_index)=='_items']
 array_raw=image.pe.bytes_at_va(ctx.type_pointer(variable.type_index),16)
 parameter_pointer=int.from_bytes(array_raw[:8],'little');parameter=ContextSymbols(image).type(parameter_pointer)
 need('array-parameter-reciprocally-owned-by-List',(parameter.get('parameterOwner',{}).get('typeIndex'),
  parameter.get('parameterOwner',{}).get('ordinal'))==(list_td.index,0)
  and bytes.fromhex(parameter['rawHex'])[10:12]==bytes((19,0)))
 declarations=list_field_declarations(declarations,owned_parameter_pointer=parameter_pointer)
 closed_receivers={}
 for role,method_name in(('point-get-item','get_Item'),('action-add','Add')):
  method=md.methods[usages[role]['methodSpec'][0]];params=list(md.parameters_for(method))
  need('own-instance-List-method:'+role,method.declaring_type==list_td.index and md.string(method.name_index)==method_name
   and not method.flags&16 and method.generic_container_index<0 and len(params)==1)
  variable=method.return_type if role=='point-get-item'else params[0].type_index
  raw=image.pe.bytes_at_va(ctx.type_pointer(variable),16)
  need('reciprocal-own-List-VAR:'+role,raw[10:12]==bytes((19,0))and int.from_bytes(raw[:8],'little')==container[3])
  scalar.ordinary(image,ctx.type_pointer(params[0].type_index if role=='point-get-item'else method.return_type),8 if role=='point-get-item'else 1,'storyPatrolPoints.abi')
  owner,field_name,element=(CONFIG,'points',POINT)if role=='point-get-item'else(CORE,'actions',ACTION)
  field,=[f for f in md.fields_for(ctx.index.types[owner])if md.string(f.name_index)==field_name]
  receiver=ContextSymbols(image).type(ctx.type_pointer(field.type_index));argument,=receiver['classArguments']
  actual,=image.instantiations.resolve(usages[role]['methodSpec'][1]).arguments
  need('same-actual-closed-receiver-and-argument:'+role,receiver['definition']['name']==LIST
   and receiver['name']==LIST+'<'+element+'>'and argument['typePointerVa']==actual.type_pointer_va
   and argument['rawHex']==actual.raw_type_record_hex)
  scalar.ordinary(image,actual.type_pointer_va,18,'storyPatrolPoints.closedReceiver',reference=True)
  need('own-selected-element-definition:'+role,int.from_bytes(bytes.fromhex(argument['rawHex'])[:8],'little')==ctx.index.types[element].index)
  closed_receivers[role]=dict(parentField=[owner,field_name],receiver=receiver,actualClassInstantiation=image.instantiations.resolve(usages[role]['methodSpec'][1]).as_dict(),
   methodDefinition=method.index,actualSourceTargetRva=targets[role]-base,runtimeReceiverSelectionObserved=False)
 item=pointer.owned(image,targets['point-get-item']);add=pointer.owned(image,targets['action-add'])
 item_proof=storage_program(item['regions'],item['pointer'],role='point-get-item')
 add_proof=storage_program(add['regions'],add['pointer'],role='action-add',disabled=disabled)
 need('same-exact-prefix-and-loop-caller-family',caller['windows']==prefix['proof']['sourceWindows'])
 def captured(body):return dict(windows=body['windows'],regions=[[a,b.hex().upper()]for a,b in body['regions']])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-point-transfer-source',nativeInputs=pins,
  proof=dict(prefix=prefix,nominalFields=fields,gaitBackingTypeDefinition=enum.index,Vector3TypeDefinition=vector.index,
   caller=captured(caller),programs=programs,induction=proof_induction,typedUsages=usages,actualTargets={k:v-base for k,v in targets.items()},
   ListFieldDeclarations=declarations,closedReceiverJoins=closed_receivers,
   item=dict(source=captured(item),**item_proof),add=dict(source=captured(add),**add_proof),disabledBarrier=barrier),
  pointFieldTransferSourceProved=True,actualListItemSourceProved=True,sufficientCapacityAddSourceProved=True,
  countHelperEffectsProved=False,listConstructorEffectsProved=False,actionConstructorEffectsProved=False,
  wholeConversionProved=False,wholeInitializerProved=False,checkpointProducerProved=False,
  checkpointFilterProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Own Config/Core reference fields, Vector3 split8+4, Int32 gait copy, whole SubAction-list reference transfer, actual closed GetItem/Add requests and complete successful helper paths plus exact top-tested loop byte induction.',
   conditional=__doc__,unresolved=['SafeCount actual canonical callback and stable count semantics','actual selected list constructors and Core-action constructor effects','growth and allocation effects','SO/config lookup and remaining conversion/initializer paths','dynamic callbacks, checkpoints and playback']))))
