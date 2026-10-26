"""Exact24 tuple-list callback/local/Add programs; parent/child are separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.leveldata_vector_tuple_sources import TYPE

LIST='System.Collections.Generic.List`1<'+TYPE+'>'
LIMIT=4096
VALUE_CAP='story-vector3-pair-value'
LIST_CAP='story-vector3-pair-list'


def normal_call_targets(rows):
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 calls=[]
 for row in rows:
  raw=bytes.fromhex(row['bytes'])
  if raw==b'\xc3':break
  if raw[:1]==b'\xe8':calls.append(control_transfer(row)['target'])
 return calls


def normal_call_after(rows,text,*,preceding=None):
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 calls=[]
 for index,row in enumerate(rows[:-1]):
  if row['bytes']=='c3':break
  if preceding is not None and(index==0 or bytes.fromhex(rows[index-1]['bytes'])!=bytes.fromhex(preceding)):continue
  if row['text']==text and bytes.fromhex(rows[index+1]['bytes'])[:1]==b'\xe8':
   calls.append(control_transfer(rows[index+1])['target'])
 if len(set(calls))!=1:raise ValueError('storyVectorTupleList.one-normal-call-after:'+text+':'+str(calls))
 return calls[0]


def list_program(regions,entry,s,*,count):
 if type(count)is not int or not -1<=count<=3:raise ValueError('storyVectorTupleList.finite-count-witness')
 g=BytesPath(regions,entry)
 g.take('4055','56','4156','4157','4883ec68');ready=flag(g)
 g.take('498bf1','4d8bf0','4c8bfa');g.branch('75',True,1)
 g.take('0f57c0','488d942498000000','33c0','33ed','498bcf','89ac2498000000','0f11442440','4889442450')
 g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 provider=None;callbacks=[];adds=[];selected=None
 if count==-1:
  g.take('498bce','49892e');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4c89a424a8000000','48899c2490000000','4889bc24a0000000','4c896c2460','448ba42498000000','49392e');g.branch('0f85',False)
  g.take('488b4e20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
  g.take('488bd8','4885c0');g.branch('75',True,1)
  g.take('488b4e20','488b91c0000000','488b4a08','48396920');g.branch('0f84',False)
  g.take('488b4620','418bd4','488bcb','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
  g.take('498bce','49891e');g.call(s['barrier']);provider=g.relative('488b0d')
  g.take('39a9e0000000');g.branch('0f84',False)
  g.take('488b4620','488b88c0000000','488b4918');g.call(s['provider']);g.take('488bd8','4585e4');g.branch('0f8e',count==0)
  if count:
   selected=g.relative('4c8d2d')
   if selected!=s['callback']:raise ValueError('storyVectorTupleList.exact-compared-ValueTuple-callback')
   g.take('6690')
  for index in range(count):
   g.take('33c0','0f57c0','4889442450','0f11442440','4885db');g.branch('0f84',False)
   g.take('488b0b');g.call(s['prepare'])
   g.take('488b03','4c8b9090010000','4c8b8898010000','4d3bd5');g.branch('0f85',False)
   g.take('498b4120','488d542440','498bcf','4c8b80c0000000','4d8b00');callbacks.append(g.at);g.call(s['raw24'])
   g.take('0f10442440','498b3e','f20f104c2450','f20f118c2498000000','0f11442420','4885ff');g.branch('0f84',False)
   g.take('488b4620','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
   g.take('488b4620','488d542420','488bcf','0f29442420','f20f114c2430','4c8b80c0000000','4d8b4030');adds.append(g.at);g.call(s['Add'])
   g.take('ffc5','413bec');g.branch('0f8c',index+1<count)
  g.take('488b9c2490000000','488bbc24a0000000','4c8b6c2460','4c8ba424a8000000')
 g.take('4883c468','415f','415e','5e','5d','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,countWitness=count,newList=True,headerBytes=4,
  elementCallbackSites=callbacks,AddCallSites=adds,providerClassCell=provider,selectedCallback=selected,
  managedElementBytes=24,elementWireBytes=None,callbackOutputZeroedBytes=24,
  sameReaderAndDisjointOutputPassed=True,actualClosedDangerousContextSlot=0,initiallyNullOutputRequired=True,
  counter='EBP starts0/increments1',savedCount='R12D unchanged',normalReturn=True,entryRspRestored=True,
  childWireGrammarAdmitted=False,growthAdmitted=False,frame=dict(entryRspDelta=-136,callShadow=[0,32],
   alignedAddValueLocal=[32,56],callbackOutputLocal=[64,88],savedR13Local=[96,104],
   headerThenValueEntryHome=[16,24],savedEntryHomes=dict(rbx=[8,16],rdi=[24,32],r12=[32,40]),
   pushedNonvolatiles=['rbp','rsi','r14','r15']))


def add_program(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec40','ff411c','498bf0','4c8b4910','488bfa','48634118','488bd9','4d85c9');g.branch('74',False,1)
 g.take('413b4118');g.branch('0f83',False)
 g.take('8d4801','894b18','413b4118');g.branch('73',False,1)
 g.take('0f1002','488d0440','f20f104a10','410f1144c120','f2410f114cc130','488b5c2450','488b742458','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,managedElementBytes=24,arrayStride=24,arrayDataOffset=32,
  incomingValueRegister='rdx',copiedSourceSlices=[[0,16],[16,8]],storedElementSlices=[[0,16],[16,8]],
  itemsOffset=16,sizeOffset=24,versionOffset=28,full24BitsStored=True,growthAdmitted=False,
  normalReturn=True,entryRspRestored=True,childWireGrammarAdmitted=False,
  frame=dict(entryRspDelta=-72,callShadow=[0,32],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushedNonvolatiles=['rdi']))


def capacity_program(regions,entry,s,*,positive):
 if type(positive)is not bool:raise ValueError('storyVectorTupleList.literal-capacity-path')
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
 g.take('498b4820','488b89c0000000');g.branch('0f84',not positive)
 if positive:
  g.take('ba01000000');g.call(s['context']);g.take('8bd3','488bc8');g.call(s['arrayAllocate'])
 else:
  g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('75',True,1)
  g.take('488b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01');g.jump('e9')
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('storyVectorTupleList.exact-capacity-barrier-tail')
 return dict(selectedBytes=g.seen,positiveCapacity=positive,capacityUnchanged=True,typedArrayContextSlot=1,
  staticEmptyArrayContextSlot=0,itemsFieldOffset=16,directSizeOrVersionWrites=False,entryRspRestored=True,
  normalReturnViaBarrier=True,managedWidthInferredFromConstructor=False,typedAllocationEffectsConditional=True)


def derive(image,pins,*,typed_request,call_target):
 """Only this exact constructed value21 list, with freshly composed child."""
 import copy,json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,_vtable
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import scalar_param_native as scalar,modelview_packable_sources,leveldata_vector_tuple_sources
 from scripts.game_data.memorypack import numeric_list_sources,lang_key_list_sources,pooled_global_buff_id_sources,int_list_sources
 from scripts.game_data.memorypack.leveldata_ship_dictionary_sources import value_provider48_program
 from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
 from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
 from scripts.game_data.memorypack.skill_value_list_context import bind_list_add_abi
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_header_program
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 from scripts.game_data.memorypack.pointer_param import owned
 check=lambda k,e,a:scalar.need('storyVectorTupleList',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image);sy=ContextSymbols(image)
 paths={name:CONTRACTS_DIR/name for name in('npc_runtime_native.json','leveldata_npc_patrol_native.json','levelscript_int_list_native.json')}
 raw_deps={name:path.read_bytes()for name,path in paths.items()};facts={name:json.loads(raw)for name,raw in raw_deps.items()}
 for name,fact in facts.items():check('dependency-selected-inputs:'+name,pins,fact['nativeInputs'])
 validate_typed_usage_context(image,typed_request,label='storyVectorTupleList.actualParent')
 bind_typed_read(image,typed_request,method_name='ReadPackable',argument=LIST,kind=21,reference=True)
 argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 carrier=sy.type(argument.type_pointer_va);extent=closed_generic_reference_pointer_extent(ctx,argument.type_pointer_va)
 check('closed-list-name',LIST,carrier['name']);element,=carrier['classArguments']
 # This is a separate constructed VALUE21 profile, not the ordinary17 list gate.
 value=leveldata_vector_tuple_sources.derive(image,pins,type_pointer=element['typePointerVa'])
 core=facts['npc_runtime_native.json'];generic=facts['leveldata_npc_patrol_native.json']['declarations'];common=facts['levelscript_int_list_native.json']
 routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
 check('actual-reference-frontdoor',base+core['readPackable']['entryRva'],call_target)
 reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
 td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
 registration=ge.resolve(method.index,[TYPE],[]);selected,=registration['classInstantiation']['arguments']
 check('same-exact-constructed-element',value['proof']['carrier'],leveldata_vector_tuple_sources.require_carrier(sy.type(selected['type_pointer_va']),
  tuple_definition=ctx.index.types[leveldata_vector_tuple_sources.DEFINITION].index,vector_definition=ctx.index.types[leveldata_vector_tuple_sources.ELEMENT].index))
 context=sy.context(td.index);validate_generic_contexts(image,[context],label='storyVectorTupleList.context')
 slots={r['relativeSlot']:r for r in context['entries']};list_td=ctx.index.types['System.Collections.Generic.List`1'];list_context=sy.context(list_td.index)
 typed=validate_list_formatter_base_context(image,context,ge,fail=check);capacity=validate_capacity_constructor_context(image,context,list_context,ge,fail=check)
 _vtable(image,td.index,5,method.index,'storyVectorTupleList')
 check('list-instance-void-slot5',(0,5,2,'void'),(method.flags&16,method.slot,method.parameter_count,ctx.type_name(method.return_type)))
 reader,out=md.parameters_for(method);rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16);output=image.pe.bytes_at_va(ctx.type_pointer(out.type_index),16)
 declared=image.pe.bytes_at_va(ctx.type_pointer(slots[0]['index']),16)
 check('list-Reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),(rr[10:12],int.from_bytes(rr[:8],'little')))
 check('same-owned-list-output',(b'\x15\x20',declared[:8]),(output[10:12],output[:8]))
 add_abi=bind_list_add_abi(image,slots[6]['methodSpec'][0]);static=[f for f in md.fields_for(list_td)if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64]
 check('sole-stored-static-array',1,len(static));empty,=static;empty_raw=image.pe.bytes_at_va(ctx.type_pointer(empty.type_index),16)
 owned_argument,=next(r for r in list_context['entries']if r['relativeSlot']==0)['type']['classArguments']
 check('static-array-exact-owned-VAR',(b'\x1d\x00',owned_argument['typePointerVa']),(empty_raw[10:12],int.from_bytes(empty_raw[:8],'little')))
 body=owned(image,registration['pointer'])
 def after(source,text):
  return normal_call_after(source['rows'],text)
 symbols={name:after(body,text)for name,text in dict(header='mov [rsp+0x50], rax',context='mov rcx, [rcx+0xc0]',allocate='mov rcx, rax',
  constructor='mov r8, [r8+0x8]',barrier='mov [r14], rbx',provider='mov rcx, [rcx+0x18]',prepare='mov rcx, [rbx]',
  raw24='mov r8, [r8]',Add='mov r8, [r8+0x30]').items()}
 symbols['callback']=value['proof']['formatterRegistration']['pointer']
 check('same-actual-raw-child',base+value['proof']['actualRawSourceTargetRva'],symbols['raw24'])
 programs=[list_program(body['regions'],body['pointer'],symbols,count=n)for n in(-1,0,1,2,3)]
 induction=prove_induction(programs[1:],initial='33ed',increment='ffc5',comparison='413bec',counter='ebp',saved_count='R12D',max_count=LIMIT)
 sources={role:owned(image,symbols[role])for role in('header','constructor','provider','Add')}
 offsets=scalar.reader_offsets(image,'storyVectorTupleList');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 header=dictionary_header_program(sources['header']['regions'],symbols['header'],offsets)
 add=add_program(sources['Add']['regions'],symbols['Add'])
 ctor_symbols=dict(context=symbols['context'],barrier=symbols['barrier'],
  arrayAllocate=normal_call_after(sources['constructor']['rows'],'mov rcx, rax',preceding='8bd3'))
 constructors=[capacity_program(sources['constructor']['regions'],symbols['constructor'],ctor_symbols,positive=positive)for positive in(False,True)]
 constructor_registration=ge.resolve(slots[1]['methodSpec'][0],[TYPE],[])
 check('actual-exact-closed-constructor-entry',constructor_registration['pointer'],symbols['constructor'])
 provider=sources['provider'];calls=normal_call_targets(provider['rows'])
 check('provider-complete-normal-call-scope',9,len(calls))
 provider_symbols=dict(zip(('backend','indexed','cast'),calls[-3:],strict=True))
 # Full actual provider program checks these concrete call positions, not an
 # equivalence with the differently registered GetFormatter specialization.
 provider_symbols['typeHandle']=calls[4]
 provider_program=value_provider48_program(provider['regions'],provider['pointer'],provider_symbols)
 provider_context=sy.context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[provider_context],label='storyVectorTupleList.provider')
 ps={r['relativeSlot']:r for r in provider_context['entries']};check('provider-owned-slots',[0,1],sorted(ps))
 for item in(ps[0]['type'],ps[1]['type']['classArguments'][0]):
  check('provider-owned-MVAR',(provider_context['definition'],0),(item['parameterOwner']['methodIndex'],item['parameterOwner']['ordinal']))
 provider_method=md.methods[provider_context['definition']]
 check('provider-static-noargs',('MemoryPack.MemoryPackFormatterProvider','GetFormatter',True,0),
  (image.type_name(provider_method.declaring_type),md.string(provider_method.name_index),bool(provider_method.flags&16),provider_method.parameter_count))
 check('provider-exact-return-carrier',ctx.type_pointer(ps[1]['index']),ctx.type_pointer(provider_method.return_type))
 check('same-owned-indexed-context',symbols['context'],provider_symbols['indexed'])
 type_handle,=[m for m in md.methods_for(ctx.index.types['System.Type'])if md.string(m.name_index)=='GetTypeFromHandle']
 check('Type-handle-static-one-Type',(True,1,'System.Type'),(bool(type_handle.flags&16),type_handle.parameter_count,ctx.type_name(type_handle.return_type)))
 check('same-owned-Type-handle',image.method_pointer_va(type_handle),provider_symbols['typeHandle'])
 cast=owned(image,provider_symbols['cast']);predicate=next(control_transfer(r)['target']for r in cast['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8')
 cast_program=pooled_global_buff_id_sources.successful_cast(cast['regions'],cast['pointer'],predicate)
 backend=owned(image,provider_symbols['backend']);backend_target=base+common['bodies']['providerBackend']['entryRva']
 backend_program=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
 factory=lang_key_list_sources.generic_provider_factory(image,pins,dict(backend=backend_target,context=symbols['context']),check)
 check('same-actual-provider-class',[factory['providerClassCell']]*2,[programs[1]['providerClassCell'],provider_program['providerClassCell']])
 resolver=common['bodies']['contextResolver'];check('actual-context-resolver',base+resolver['entryRva'],symbols['context'])
 image.check_windows(resolver['windows'],label='storyVectorTupleList.actualContextResolver')
 resolver_program=int_list_sources.initialized_class([(base+w['startRva'],image.window_bytes(w))for w in resolver['windows']],symbols['context'],indexed=True)
 barrier,barrier_program,_=_fast_barrier(image,symbols['barrier'])
 for name,raw in raw_deps.items():check('dependency-bookend:'+name,raw,paths[name].read_bytes())
 _publication_gate(image,pins)
 cap=dict(typeName=LIST,elementType=TYPE,elementCapability=VALUE_CAP,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,
  managedElementBytes=24,elementWireBytes=24,nullable=True,positiveCountsAdmitted=True,initiallyNullListRequired=True,
  actualCallbackEqualsCanonicalRequired=True,full24BitsStored=True,profileAdmitted=True,growthAdmitted=False,
  wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base)
 return json.loads(json.dumps(dict(schema='endfield.story-vector3-tuple-list-source.v1',status='validated-conditional-constructed-tuple-list-profile',nativeInputs=pins,
  capabilities={LIST_CAP:cap,VALUE_CAP:value['capability']},proof=dict(actualParent=typed_request,closedCarrier=carrier,referenceExtent=extent,referenceSource=reference,
   registration=registration,context=context,typedContext=typed,capacityContext=capacity,staticArrayRawHex=empty_raw.hex(),value=value,programs=programs,induction=induction,
   header=header,Add=add,addAbi=add_abi,constructors=constructors,constructorRegistration=constructor_registration,provider=provider_program,providerContext=provider_context,
   cast=cast_program,backend=backend_program,factory=factory,typeFromHandleMethodDefinition=type_handle.index,
   contextResolver=resolver,contextResolverProgram=resolver_program,
   barrier=dict(source=barrier,proof=barrier_program),symbolRvas={k:v-base for k,v in symbols.items()},
   sourceWindows=dict(list=body['windows'],**{k:b['windows']for k,b in sources.items()})),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,ordinary17ListAliasUsed=False,evidenceBoundary=dict(
   exact='Fresh actual closed reference parent and constructed ValueTuple<Vector3,Vector3>21/128 child, exact list/constructor/Add/provider ownership; signed null/newzero/count4096 EBP induction, compared canonical tuple callback/actualDangerous context and raw24 child, complete Add24/local/all nonvolatile/frame transfers.',
   conditional='Initially null output, coherent closed contexts and exact selected callbacks, fresh count-sized zeroed typed List/array storage and compatible provider/context/allocator/barrier effects. Sufficient contiguous disjoint input/output/frame; finite float projection. Constructor and helper runtime selection remains unobserved.',
   unresolved=['reused lists or growth','actual enclosing field/owner/physical EOF','live formatter/provider selection and runtime meaning']))))
