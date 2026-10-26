"""Current WayLane list count/managed16 stores; wire and actual parent stay separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_waylane_sources import TYPE
import json

LIST='System.Collections.Generic.List`1<'+TYPE+'>'
LIMIT=4096
CAP='story-waylane-list'
VALUE_CAP='story-waylane-value'


def list_program(regions,entry,offsets,s,*,count):
 if type(count)is not int or not -1<=count<=3:raise ValueError('storyWayLaneList.finite-source-witness')
 g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('4053','55','56','4154','4156','4883ec50','837a'+rem+'04','0f57c0','0f11442420','498be9','4d8be0','488bf2');g.branch('0f8c',False)
 g.take('488b46'+cur,'4c6330','8b5e'+rem,'83c3fc');g.branch('0f88',False)
 g.take('488346'+cur+'04','8346'+adv+'04','8346'+used+'04','895e'+rem,'486346'+used,'488b4e'+total,'482bc8','493bce');g.branch('0f8c',False)
 g.take('4889bc2480000000','4183feff');g.branch('0f84',count==-1);allocation=None;provider=None;callbacks=[]
 if count==-1:
  g.take('33ff','498bcc','49893c24');g.call(s['barrier']);g.jump('eb',1)
 else:
  g.take('4c89ac2488000000','4c89bc2490000000','0f29742440','49833c2400');g.branch('0f85',False)
  g.take('488b4d20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');allocation=g.at;g.call(s['allocate'])
  g.take('488bd8','4885c0');g.branch('0f84',False)
  g.take('488b4d20','488b91c0000000','488b4a08','4883792000');g.branch('0f84',False)
  g.take('488b4520','418bd6','488bcb','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
  g.take('498bcc','49891c24');g.call(s['barrier']);provider=g.relative('488b0d')
  g.take('83b9e000000000');g.branch('0f84',False)
  g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider']);g.take('33ff','4c8bf8','4585f6');g.branch('0f8e',count==0)
  for index in range(count):
   g.take('0f57c0','0f11442420','4d85ff');g.branch('0f84',False)
   g.take('4c8d4c2420','4c8bc6','498bd7');callbacks.append(g.at);g.call(s['dispatch'])
   g.take('498b1c24','0f28742420','4885db');g.branch('0f84',False)
   g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
   g.take('488b4520','488b5310','488b88c0000000','4c8b6930','ff431c','4885d2');g.branch('74',False,1)
   g.take('48634b18','3b4a18');g.branch('0f83',False)
   g.take('8d4101','894318','3b4a18');g.branch('73',False,1)
   g.take('488d4102','48c1e104','4803c0','0f1134c2','4883c228','4803ca');g.call(s['barrier'])
   g.take('ffc7','413bfe');g.branch('0f8c',index+1<count)
  g.take('4c8bbc2490000000','4c8bac2488000000','0f28742440')
 g.take('488bbc2480000000','4883c450','415e','415c','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,countWitness=count,newList=True,elementCallbackSites=callbacks,typedAllocationCall=allocation,
  providerClassCell=provider,headerBytes=4,managedElementBytes=16,elementWireBytes=None,
  callbackOutputStackOffset=32,sourceOutputBytesZeroedBeforeCallback=16,arrayDataOffset=32,arrayStride=16,referenceLaneOffset=8,
  paddingByteRanges=[[4,8]],full16BitsStored=True,initiallyNullOutputRequired=True,growthAdmitted=False,
  counter='EDI starts0/increments1',savedCount='R14D unchanged',entryRspRestored=True,normalReturn=True,
  childWireGrammarAdmitted=False,frame=dict(entryRspDelta=-120,callShadow=[0,32],outputLocal=[32,48],
   savedXmm6=[64,80],savedEntryHomes=dict(rdi=[128,136],r13=[136,144],r15=[144,152]),
   pushedNonvolatiles=['rbx','rbp','rsi','r12','r14'],sameDisjointOutputLocalPassedToCallback=True))


def derive(image,pins,*,typed_request,call_target):
 """Fresh count/child/callback/Add16 source; enclosing field stays separate."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,derive_typed_usage_context
 from scripts.game_data.memorypack import scalar_param_native as scalar,float_list_sources,pooled_global_buff_id_sources,numeric_list_sources,lang_key_list_sources
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack.skill_value_list_context import derive as list_context
 from scripts.game_data.memorypack.leveldata_waylane_transfer_sources import derive_adapter
 from scripts.game_data.memorypack.leveldata_waylane_sources import prove_array_source
 from scripts.game_data.memorypack.leveldata_uint_array_sources import derive as array_source
 from scripts.game_data.memorypack.skill_root_tag_query_transfer import adapter16_program
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 need=lambda k,e,a:scalar.need('storyWayLaneList',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
 need('exact-closed-list',LIST,context['closedListType'])
 transfer=derive_adapter(image,pins);record=transfer['record'];request=record['arrayTypedRequest']
 array=array_source(image,pins,typed_request=request,call_target=base+record['symbolRvas']['array'],actual_source_prover=prove_array_source)
 need('same-independent-record-source',record,array['proof']['actualSourceJoin']['proof'])
 calls=[row for row in body['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8']
 need('complete-hot-call-sites',True,len(calls)>=6)
 symbols={name:control_transfer(row)['target']for name,row in zip(('context','allocate','constructor','barrier','provider','dispatch'),calls[:6],strict=True)}
 offsets=scalar.reader_offsets(image,'storyWayLaneList');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 paths=[list_program(body['regions'],body['pointer'],offsets,symbols,count=count)for count in(-1,0,1,2,3)]
 induction=prove_induction(paths[1:],initial='33ff',increment='ffc7',comparison='413bfe',counter='edi',saved_count='R14D',max_count=LIMIT)
 dispatcher=owned(image,symbols['dispatch']);dispatch_symbols={name:base+rva for name,rva in transfer['proof']['symbolRvas'].items()}
 dispatch=[adapter16_program(dispatcher['regions'],dispatcher['pointer'],dispatch_symbols,dispatch=True,**mode)for mode in({},{'create':False},{'null':True})]
 slots={row['relativeSlot']:row for row in context['context']['entries']}
 list_method=md.methods[context['registration']['methodDefinitionIndices'][0]]
 # Slot5 names the abstract MemoryPackFormatter<T> declaration. The actual
 # dispatcher independently compares its callback to this concrete adapter;
 # only that concrete method owns a populated implementation vtable slot.
 callback,=transfer['proof']['registrations']['adapter']['methodDefinitionIndices']
 need('actual-callback-owner','Beyond.MemoryPack.GenericMemoryPackFormatter`2',image.type_name(md.methods[callback].declaring_type))
 declarations=dict(list=list_method.index,callback=callback,capacity=slots[1]['methodSpec'][0],Add=slots[6]['methodSpec'][0],Clear=slots[2]['methodSpec'][0])
 abis=float_list_sources._method_abis(image,ctx,declarations,context['context'])
 constructor=owned(image,symbols['constructor']);ctor_symbols=dict(context=symbols['context'],barrier=symbols['barrier'],arrayAllocate=_body_target(constructor,'mov rcx, rax'))
 constructors=[float_list_sources.capacity_program(constructor['regions'],constructor['pointer'],ctor_symbols,positive=positive)for positive in(False,True)]
 for proof in constructors:proof['condition']='Exact current closed List<WayLane> context and typed array; nonnegative unchanged capacity, fresh zeroed List/array or ready static empty array and normal compatible context/allocator/barrier effects. No growth or existing List is admitted.'
 ctor_registration=ge.resolve(slots[1]['methodSpec'][0],[TYPE],[])
 provider=owned(image,symbols['provider']);provider_calls=[control_transfer(row)['target']for row in provider['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8'][:4]
 need('four-complete-provider-calls',4,len(provider_calls));provider_symbols=dict(zip(('typeHandle','keyBackend','context','assignable'),provider_calls,strict=True))
 # This actual clone inlines the null/assignability guard and returns the
 # unchanged backend reference. It does not call the separate cast clone.
 provider_program=float_list_sources.provider_program(provider['regions'],provider['pointer'],dict(
  typeFromHandle=provider_symbols['typeHandle'],backend=provider_symbols['keyBackend'],
  type=provider_symbols['context'],assignable=provider_symbols['assignable']))
 need('same-owned-type-handle',dispatch_symbols['typeHandle'],provider_symbols['typeHandle'])
 need('same-indexed-context',symbols['context'],provider_symbols['context'])
 pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[pc],label='storyWayLaneList.provider')
 pcs={row['relativeSlot']:row for row in pc['entries']};need('provider-owned-slots',[0,1],sorted(pcs))
 pm=md.methods[pc['definition']]
 need('provider-nominal-ABI',('MemoryPack.MemoryPackFormatterProvider','GetFormatter',True,0),
  (image.type_name(pm.declaring_type),md.string(pm.name_index),bool(pm.flags&16),pm.parameter_count))
 need('owned-provider-return',ctx.type_pointer(pm.return_type),ctx.type_pointer(pcs[1]['index']))
 need('expected-formatter-definition','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
 for child in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):need('provider-reciprocal-MVAR',(pm.index,0),(child['parameterOwner']['methodIndex'],child['parameterOwner']['ordinal']))
 dependency_path=CONTRACTS_DIR/'levelscript_int_list_native.json';dependency_raw=dependency_path.read_bytes();dependency=json.loads(dependency_raw)
 need('generic-provider-build',pins,dependency['nativeInputs']);backend=owned(image,provider_symbols['keyBackend']);backend_target=base+dependency['bodies']['providerBackend']['entryRva']
 backend_program=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
 factory=lang_key_list_sources.generic_provider_factory(image,pins,dict(backend=backend_target,context=symbols['context']),need)
 usages=[]
 for source,cell,name in((body,paths[1]['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
  (provider,provider_program['providerClassCell'],'System.Type'),(provider,provider_program['rootClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
  (backend,backend_program['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
  row,=[row for row in source['rows']if len(bytes.fromhex(row['bytes']))==7 and bytes.fromhex(row['bytes'])[:3]==b'\x48\x8b\x0d'
   and int(row['va'],16)+7+int.from_bytes(bytes.fromhex(row['bytes'])[3:],'little',signed=True)==cell]
  usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='storyWayLaneList.namedProviderCell')
  need('actual-named-provider-cell',(1,name),(usage['tag'],usage['typeName']));usages.append(usage)
 need('same-provider-class',factory['providerClassCell'],paths[1]['providerClassCell'])
 need('same-backend-class',factory['providerClassCell'],backend_program['providerOwnerCell'])
 barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier'])
 need('same-child-ref-barrier',dispatch_symbols['barrier'],symbols['barrier'])
 need('dependency-bookend',dependency_raw,dependency_path.read_bytes());_publication_gate(image,pins)
 value_cap=dict(typeName=TYPE,memberCount=2,managedBytes=16,referenceLaneOffsets=[8],paddingByteRanges=[[4,8]],
  canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=16,arrayCapability=array['capability'],profileAdmitted=True,wholeGrammarAdmitted=False,
  actualCallbackEqualsCanonicalRequired=True,liveFormatterSelectionObserved=False)
 cap=dict(typeName=LIST,elementType=TYPE,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,nullable=True,positiveCountsAdmitted=True,
  initiallyNullListRequired=True,managedElementBytes=16,elementWireBytes=None,elementCapability=VALUE_CAP,finiteElementProfileAdmitted=True,
  packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
  actualCallbackEqualsCanonicalRequired=True,profileAdmitted=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False)
 return json.loads(json.dumps(dict(schema='endfield.story-waylane-list-source.v1',status='validated-conditional-waylane-list-source',nativeInputs=pins,
  capabilities={CAP:cap,VALUE_CAP:value_cap},proof=dict(context=context,programs=paths,induction=induction,transfer=transfer,array=array,
   dispatch=dispatch,methodAbis=abis,abstractCallbackDeclaration=slots[5],constructors=constructors,constructorRegistration=ctor_registration,
   constructorEntryPointerMatched=ctor_registration['pointer']==symbols['constructor'],provider=provider_program,providerContext=pc,
   backend=backend_program,factory=factory,classUsages=usages,barrier=dict(source=barrier,proof=barrier_proof),
   symbolRvas={key:target-base for key,target in symbols.items()},sourceWindows=dict(list=body['windows'],dispatch=dispatcher['windows'],
    constructor=constructor['windows'],provider=provider['windows'],backend=backend['windows'])),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Fresh exact closed WayLane list context, own padded nominal16 wrapper/canonical adapter and exact actual UInt32-array source, full null/newzero/positive loop with4096 induction, actual dispatcher/canonical comparison, full16 inline array stores/ref8 barriers and restored local/nonvolatile/frame, own typed capacity/provider sources.',
   conditional='Initially null output, fresh zeroed count-sized typed storage and compatible ready WayLane/canonical callback/provider/context/allocator/barrier effects with stable disjoint buffered data. Array children independently limit counts to64; padding is copied unchanged and supplies no wire bytes.',
   unresolved=['existing lists, capacity growth and array counts above64','actual enclosing parent/whole owner/physical EOF','runtime callback/provider selection']))))
