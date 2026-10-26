"""Finite inline value-wrapper programs for two distinct Module children.

These wrappers own inline Original payloads. A reference Original setter
profile is therefore inapplicable. Managed payload size never selects their
wire grammar, and the wrapper FF clears a wrapper reference rather than an
Original value. Canonical value/default and list joins remain separate.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

EFFECT='Beyond.Gameplay.FogNestControllerData+EffectInfo'
AIRWALL='Beyond.Gameplay.Core.AirWallPtr'
SPECS={
 EFFECT:dict(managedBytes=48,count=5,fields=[('delayToHide','float',24),('effectKey','string',16),
  ('eulerAngles','UnityEngine.Vector3',40),('position','UnityEngine.Vector3',28),('scale','UnityEngine.Vector3',52)]),
 AIRWALL:dict(managedBytes=24,count=3,fields=[('logicId','ulong',24),('slotId','uint',32),('useSlotId','bool',16)])}


def need(key,condition):
 if not condition:raise ValueError('moduleValueWrapper.'+key)


def value_leaf_program(regions,entry,*,type_name,mode):
 need('finite-nominal-leaf-selection',type_name in SPECS and mode in('getter','default'))
 g=BytesPath(regions,entry)
 if mode=='default':
  g.take('0f57c0')
  if type_name==AIRWALL:g.take('33c0','0f114110','48894120')
  else:g.take('0f114110','0f114120','0f114130')
 else:
  g.take('0f104210','488bc1')
  if type_name==AIRWALL:g.take('f20f104a20','0f1101','f20f114910')
  else:g.take('0f104a20','0f1101','0f104230','0f114910','0f114120')
 g.take('c3');width=SPECS[type_name]['managedBytes']
 return dict(selectedBytes=g.seen,typeName=type_name,mode=mode,managedBytes=width,
  completePayloadZeroed=mode=='default',completePayloadCopiedUnchanged=mode=='getter',hiddenOutputReturnedInRax=mode=='getter',
  leafFrameUnchanged=True,normalReturn=True,wireGrammarAdmitted=False,physicalFunctionExtentClaimed=False)


def reader_program(regions,entry,*,type_name,symbols=None,new=False,ff=False):
 need('literal-finite-wrapper-case',type_name in SPECS and type(new)is bool and type(ff)is bool)
 need('callable-symbol-domain',symbols is None or type(symbols)is dict)
 g=BytesPath(regions,entry);effect=type_name==EFFECT;reads=[];allocation=None;roles={}
 def call(role):
  target=g.relative('e8')
  need('same-role-target:'+role,role not in roles or roles[role]==target)
  if symbols is not None:need('independent-role-target:'+role,symbols.get(role)==target)
  roles[role]=target
 if effect:
  g.take('48895c2410','4889742418','57','4883ec30');flag=g.relative('803d')+1;g.take('00','488bda','488bf9');g.branch('75',True,1)
  g.take('488d542440','c644244000','488bcf')
 else:
  g.take('48895c2418','57','4883ec20');flag=g.relative('803d')+1;g.take('00','488bda','488bf9');g.branch('0f84',False)
  g.take('488d542430','c644243000','488bcf')
 header=g.at;call('header');g.take('84c0');g.branch('0f84',ff)
 if ff:
  g.take('488bcb','48c70300000000');call('barrier')
  if not effect:g.take('90');g.jump('e9')
 else:
  if not effect:g.take('4889742438')
  g.take('48833b00');g.branch('75'if effect else'0f84',not new if effect else new,1 if effect else 4)
  if new:
   allocation=dict(instructionVa=g.at,classCellVa=g.relative('488b0d'));call('allocate');g.take('4885c0');g.branch('0f84',False)
   if effect:g.take('0f57c0','488bcb','0f114010','0f114020','0f114030','488903')
   else:g.take('33c9','0f57c0','0f114010','48894820','488bcb','488903')
   call('barrier')
   if not effect:g.take('90');g.jump('e9')
  if effect:
   g.take('807c244005');g.branch('0f85',False)
   g.take('488b33','488bcf');site=g.at;call('single');g.take('4885f6');g.branch('0f84',False);g.take('f30f114618')
   reads.append(dict(fieldName='delayToHide',kind='single',sourceCallVa=site,storeOffset=24))
   g.take('488bcf','488b33');site=g.at;call('string');g.take('4885f6');g.branch('0f84',False)
   g.take('4533c0','488bd0','488bce');setter=g.at;call('stringSetter')
   reads.append(dict(fieldName='effectKey',kind='pooled-string',sourceCallVa=site,setterCallVa=setter,storeOffset=16))
   g.take('488b33','488d4c2420','488bd7')
   for index,(field,offset)in enumerate((('eulerAngles',40),('position',28),('scale',52))):
    site=g.at;call('vector3');g.take('488bc8','4885f6'if index<2 else'4885db');g.branch('74',False,1)
    g.take('f20f1001')
    if index<2:g.take('488bd7')
    g.take('8b4008')
    if index<2:g.take('488d4c2420')
    g.take(('f20f1146'if index<2 else'f20f1143')+bytes((offset,)).hex(),
     ('8946'if index<2 else'8943')+bytes((offset+8,)).hex())
    reads.append(dict(fieldName=field,kind='vector3-hidden12',sourceCallVa=site,storeOffset=offset,hiddenLocalRspOffset=32,copiedSlices=[[0,8],[8,4]]))
    if index<2:g.take('488b33'if index==0 else'488b1b')
   g.jump('eb',1)
  else:
   g.take('0fb6742430','4080fe03');g.branch('0f85',False)
   for index,(field,role,store)in enumerate((('logicId','ulong','48894618'),('slotId','uint','894620'),('useSlotId','bool','884310'))):
    if index==0:g.take('488b33','488bcf')
    elif index==1:g.take('488bcf','488b33')
    else:g.take('488bcf','488b1b')
    site=g.at;call(role);g.take('4885f6'if index<2 else'4885db');g.branch('74',False,1)
    if index==2:g.take('488b742438')
    g.take(store);reads.append(dict(fieldName=field,kind=role,sourceCallVa=site,storeOffset=SPECS[type_name]['fields'][index][2]))
 if effect:g.take('488b5c2448','488b742450','4883c430','5f','c3')
 else:g.take('488b5c2440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,newWrapper=new,wrapperFF=ff,initializedFlagVa=flag,
  headerCallVa=header,headerLocalRspOffset=64 if effect else 48,typedAllocation=allocation,orderedReads=reads,
  wrapperReferenceClearedBytes=8 if ff else 0,inlineOriginalHolderOffset=16,managedBytes=SPECS[type_name]['managedBytes'],
  normalReturn=True,canonicalOriginalDefaultAdmitted=False,parentFieldAdmitted=False,wireGrammarAdmitted=False,
  fullFrameProofRequired=True,namedSourcesAndSetterProofRequired=True,symbolTargets=roles)


def _frame_result(program):
 """The two fully parsed schedules own their exact frame/saved homes.

 No caller row is skipped by reader_program. Its literal prologue, all stores,
 branch-specific RSI save/restore and complete epilogue determine these homes.
 Hidden12 storage is reused only after both named 8+4 stores have completed.
 """
 name=program['typeName'];need('finite-frame-profile',name in SPECS)
 effect=name==EFFECT;ff=program['wrapperFF'];delta=-56 if effect else-40
 saved=dict(rbx=[16,24],rsi=[24,32],rdi=[-8,0])if effect else dict(rbx=[24,32],rdi=[-8,0])
 if not effect and not ff:saved['rsi']=[16,24]
 header=[program['headerLocalRspOffset']+delta,program['headerLocalRspOffset']+delta+1]
 need('header-owned-entry-home',header==[8,9])
 spans=list(saved.values())+[header]
 need('distinct-header-register-homes',all(z<=c or d<=a for i,(a,z)in enumerate(spans)for c,d in spans[i+1:]))
 hidden=[]
 if effect and not ff:
  vectors=[r for r in program['orderedReads']if r['kind']=='vector3-hidden12']
  need('three-complete-named-source-copies',[(r['fieldName'],r['storeOffset'],r['hiddenLocalRspOffset'],r['copiedSlices'])for r in vectors]
   ==[(n,o,32,[[0,8],[8,4]])for n,o in(('eulerAngles',40),('position',28),('scale',52))])
  hidden=[dict(fieldName=r['fieldName'],sourceCallVa=r['sourceCallVa'],rspRange=[32,44],
   entryRspRange=[32+delta,44+delta],namedFieldOffset=r['storeOffset'],completeCopiedBytes=12)for r in vectors]
  need('source-local-outside-shadow-and-saved-homes',32>=32 and 44<=-delta
   and all(44+delta<=a or z<=32+delta for a,z in saved.values()))
 return dict(entryRspDelta=delta,callShadowRspRange=[0,32],headerEntryHome=header,savedEntryHomes=saved,
  hiddenSourceLifetimes=hidden,hiddenHomeReusedOnlyAfterWholeNamedFieldStore=bool(hidden),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  childNormalAbiPreservesCallerFrameRequired=True,fullSelectedCallerFrameProved=True)


def frame_program(regions,entry,*,type_name,symbols=None,new=False,ff=False):
 return _frame_result(reader_program(regions,entry,type_name=type_name,symbols=symbols,new=new,ff=ff))


def layout(image,ctx,wrapper):
 """Own complete nominal physical fields; no wire grammar follows from size."""
 from scripts.game_data.memorypack import scalar_param_native as scalar
 name=wrapper.wrapped_type;need('finite-layout',name in SPECS);spec=SPECS[name];md=image.metadata;td=ctx.index.types[name]
 need('plain-owned-value',ctx.is_value_type(name)and not ctx.is_enum(name)and ctx.parent(name)=='System.ValueType'and td.generic_container_index<0)
 scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,'moduleValueWrapper.Original')
 need('exact-serialized-member-order',[(m.name,m.declared_type)for m in wrapper.members]==[(n,t)for n,t,o in spec['fields']])
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 actual=sorted([(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in fields],key=lambda r:r[2])
 need('complete-named-physical-fields',actual==sorted(spec['fields'],key=lambda r:r[2]))
 kinds={'bool':2,'uint':9,'ulong':11,'float':12,'string':14,'UnityEngine.Vector3':17}
 for field in fields:
  typename=ctx.type_name(field.type_index)
  need('finite-declared-member-kind',typename in kinds)
  scalar.ordinary(image,ctx.type_pointer(field.type_index),kinds[typename],'moduleValueWrapper.field',reference=typename=='string')
 holder=ctx.field(wrapper.name+'::__instance');need('direct-inline-value-holder',holder==(wrapper.name,name,16))
 sizes={}
 for definition in(td,md.types[wrapper.type_definition]):
  need('bounded-size-row',0<=definition.index<image.registration['typeDefinitionsSizesCount'])
  at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*definition.index)
  need('present-size-row',type(at)is int and at>0)
  sizes[image.type_name(definition.index)]=dict(instanceBytes=image.pe.u32_at_va(at),nativeBytes=image.pe.u32_at_va(at+4))
 need('exact-boxed-and-wrapper-storage',sizes[name]['instanceBytes']==16+spec['managedBytes']
  and sizes[wrapper.name]['instanceBytes']==16+spec['managedBytes'])
 return dict(typeName=name,typeDefinition=td.index,managedBytes=spec['managedBytes'],fields=actual,holder=holder,sizeRows=sizes,
  referenceLaneOffsets=[0]if name==EFFECT else[],paddingByteRanges=[]if name==EFFECT else[[1,8],[20,24]],
  paddingRangesAreStartEnd=True,wireWidthFromLayoutClaimed=False)


def derive_record(image,pins,*,type_name):
 """Fresh own wrapper/source/whole value getter; canonical/list joins separate."""
 import hashlib,json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
 from scripts.game_data.memorypack import generated_vector3_source,pooled_source_helper
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 _publication_gate(image,pins);need('finite-source-type',type_name in SPECS);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
 nominal=layout(image,ctx,wrapper);methods=pointer.methods(image,wrapper);reader=methods['Deserialize']
 primitive_param.reader_abi(image,ctx,reader,wrapper);body=pointer.owned(image,image.method_pointer_va(reader))
 first=reader_program(body['regions'],body['pointer'],type_name=type_name,new=True);symbols=first['symbolTargets']
 programs=[first]+[reader_program(body['regions'],body['pointer'],type_name=type_name,symbols=symbols,new=n,ff=f)
  for n,f in((False,False),(True,True),(False,True))]
 frames=[_frame_result(p)for p in programs]
 allocation=derive_typed_usage_context(image,first['typedAllocation']['instructionVa']-base,label='moduleValueWrapper.allocation')
 need('actual-owned-wrapper-allocation',(allocation['tag'],allocation['typeName'])==(1,wrapper.name)
  and base+allocation['usageCellRva']==first['typedAllocation']['classCellVa'])
 scalar.ordinary(image,ctx.type_pointer(allocation['typeIndex']),18,'moduleValueWrapper.wrapperAllocation',reference=True)
 leaves={}
 for role,mode in(('.ctor','default'),('CreateInstance','default'),('GetValue','getter')):
  method=methods[role];scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,
   (type_name,17,False)if mode=='getter'else('void',1,False),[],'moduleValueWrapper.'+role)
  target=image.method_pointer_va(method)
  # Read only a bounded normal leaf; the parser stops at its exact RET.
  raw=image.pe.bytes_at_va(target,32);program=value_leaf_program([(target,raw)],target,type_name=type_name,mode=mode)
  length=sum(len(bytes.fromhex(h))for a,h in program['selectedBytes']);raw=raw[:length]
  leaves[role]=dict(method=[method.index,wrapper.name,role,target-base],program=program,
   window=dict(startRva=target-base,endRva=target-base+length,sha256=hashlib.sha256(raw).hexdigest().upper()),
   sourceRegions=[[target,raw.hex().upper()]],physicalExtentProved=False)
 offsets=scalar.reader_offsets(image,'moduleValueWrapper');rec=vector_recorder(image);header=rec(symbols['header']-base)
 primitive_param.object_header_source(image,header,offsets);sources={};setter=None
 if type_name==EFFECT:
  single=rec(symbols['single']-base);primitive_param.single_source(image,single,offsets)
  sources['single']=single;sources['string']=pooled_source_helper.validate_on_image(image,symbols['string'],pins)
  sources['vector3']=generated_vector3_source.derive_forwarder(image,pins,source_target=symbols['vector3'])
  member,=[m for m in wrapper.members if m.name=='effectKey'];method=image.metadata.methods[member.method_index]
  method_name=image.metadata.string(method.name_index)
  scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[('string',14,True)],'moduleValueWrapper.stringSetter')
  target=image.method_pointer_va(method);need('actual-exact-named-string-setter',target==symbols['stringSetter'])
  raw=image.pe.bytes_at_va(target,12);g=BytesPath([(target,raw)],target);g.take('4883c110','488911');barrier_target=g.relative('e9')
  need('same-exact-reference-barrier',barrier_target==symbols['barrier'])
  setter=dict(method=[method.index,wrapper.name,method_name,target-base],selectedBytes=g.seen,
   window=dict(startRva=target-base,endRva=target-base+12,sha256=hashlib.sha256(raw).hexdigest().upper()),
   sourceRegions=[[target,raw.hex().upper()]],wholeIncomingReferenceStoredUnchanged=True,fieldOffset=16,
   disabledReferenceBarrierRequired=True,entryFrameUnchanged=True,physicalExtentProved=False)
 else:
  for role,prove in(('ulong',lambda i,r,o:scalar.integer_source(i,r,o,'moduleValueWrapper.ulong',width=8)),
    ('uint',lambda i,r,o:scalar.integer_source(i,r,o,'moduleValueWrapper.uint',width=4)),
    ('bool',lambda i,r,o:scalar.boolean_source(i,r,o,'moduleValueWrapper.bool'))):
   item=rec(symbols[role]-base);image.check_windows([item['window']],label='moduleValueWrapper.'+role)
   prove(image,item,offsets);sources[role]=item
 barrier,barrier_program,_=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-module-value-wrapper.v1',status='validated-conditional-module-value-wrapper',
  nativeInputs=pins,typeName=type_name,wrapperName=wrapper.name,layout=nominal,readerMethod=[reader.index,wrapper.name,'Deserialize',body['pointer']-base],
  sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']],programs=programs,frames=frames,
  leaves=leaves,allocation=allocation,headerSource=header,memberSources=sources,stringSetter=setter,
  symbolRvas={r:t-base for r,t in symbols.items()},barrier=dict(source=barrier,program=barrier_program),
  canonicalOriginalAdapterAdmitted=False,parentFieldAdmitted=False,containerAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own inline value wrapper, complete named physical fields, four initialized selected source/store/frame paths, actual primitive/pool/closed Vector3 helpers, exact default and whole hidden getter leaves.',
   conditional='Initialized metadata, compatible wrapper and output, normal child/allocation ABI, disabled collector and stable sufficiently buffered disjoint storage.',
   unresolved=['canonical Original/default conversion and actual callback selection','positive value-list callbacks/Add/counts','enclosing Module grammar/physical EOF/publication']))))
