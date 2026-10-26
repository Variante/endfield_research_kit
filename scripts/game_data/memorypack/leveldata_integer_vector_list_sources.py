"""Finite current Vector2Int collection, independently of other raw8 domains.

Initially null count-sized lists, compatible ready exact callbacks/contexts,
buffered disjoint nonwrapping storage and normal helper/barrier effects are
conditions. Neither an integer-vector field nor a qword copy supplies a list.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar

TYPE='UnityEngine.Vector2Int'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
CAP='story-vector2-int-list'
LIMIT=4096


def need(k,e,a):scalar.need('storyIntegerVectorList',k,e,a)


def list_program(regions,entry,s,o,*,count):
 need('literal-count',True,type(count)is int and count in(-1,0,1,2,3))
 cur,rem,adv,used=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g=BytesPath(regions,entry);provider=callback=loop=backedge=None
 g.take('4055','56','57','4154','4883ec38','488bfa','33f6','488bcf','89742468',
  '488d542468','4889742420','498be9','4d8be0');g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:
  g.take('498bcc','49893424');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4c896c2470','48895c2460','4c89742478','4c897c2430','448b6c2468','49393424');g.branch('0f85',False)
  g.take('488b4d20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
  g.take('488bd8','4885c0');g.branch('0f84',False)
  g.take('488b4d20','488b91c0000000','488b4a08','48397120');g.branch('0f84',False)
  g.take('488b4520','418bd5','488bcb','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
  g.take('498bcc','49891c24');g.call(s['barrier']);provider=g.relative('488b0d')
  g.take('39b1e0000000');g.branch('0f84',False)
  g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider'])
  g.take('4c8bf0','448bfe','4585ed');g.branch('0f8e',count==0)
  if count:
   callback=g.relative('488d1d');need('exact-closed-callback',s['callback'],callback)
   g.take('0f1f840000000000');loop=g.at
   for index in range(count):
    need('same-loop-head',loop,g.at)
    g.take('4889742420','4d85f6');g.branch('0f84',False)
    g.take('498b0e');g.call(s['prepare']);g.take('498b06','4c8b9090010000','4c8b8898010000','4c3bd3');g.branch('0f85',False)
    g.take('837f'+rem+'08');g.branch('0f8c',False)
    g.take('488b47'+cur,'488b00','4889442420','8b5f'+rem,'83c3f8');g.branch('0f88',False)
    g.take('488347'+cur+'08','8347'+adv+'08','8347'+used+'08','895f'+rem,
     '498b3424','488b5c2420','4885f6');g.branch('74',False,1)
    g.take('488b4520','488b90c0000000','488b4230','4883782000');g.branch('0f84',False)
    g.take('488b4520','488bd3','488bce','4c8b80c0000000','4d8b4030');g.call(s['add'])
    g.take('41ffc7');need('same-reloaded-closed-callback',callback,g.relative('488d1d'))
    g.take('be00000000','453bfd');backedge=g.at;g.branch('0f8c',index+1<count)
  g.take('4c8b742478','488b5c2460','4c8b7c2430','4c8b6c2470')
 g.take('4883c438','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,countWitness=count,newList=True,providerClassCell=provider,selectedCallback=callback,
  loopHead=loop,backedge=backedge,elementReads=max(count,0),counterRegister='r15d',savedCountRegister='r13d',
  managedElementBytes=8,wireBytes=8,normalReturn=True,completeFrameAndNonvolatilesRestored=True,
  condition='R15D is initialized from ESI proven zero; R13D is the immutable signed header count. One unchanged qword read/Add precedes the sole increment and exact signed backedge. Normal helpers preserve both registers. Existing lists/refill/growth/live callback selection remain excluded.')


def callback_program(regions,entry,o):
 cur,rem,adv,used=(bytes((o[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g=BytesPath(regions,entry)
 g.take('48895c2408','57','4883ec20','837a'+rem+'08','498bf8','488bda');g.branch('0f8c',False)
 g.take('488b42'+cur,'488b00','488907','8b7b'+rem,'83c7f8');g.branch('0f88',False)
 g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,'488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,wireBytes=8,managedBytes=8,rawCopySlices=[[0,8]],normalReturn=True,completeFrameRestored=True)


def add_program(regions,entry,*,canonical=False):
 need('literal-Add-profile',bool,type(canonical));g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','ff411c','488bda')
 if canonical:
  g.take('4c8b4910','498bf0','48635118','488bf9','4d85c9');g.branch('75',True,1)
  g.take('413b5118');g.branch('72',True,1)
  g.take('8d4201','894118','413b5118');g.branch('72',True,1)
  g.take('49895cd120')
 else:
  g.take('488b5110','498bf0','48634118','488bf9','4885d2');g.branch('74',False,1)
  g.take('3b4218');g.branch('73',False,1);g.take('8d4801','894f18','3b4218');g.branch('73',False,1)
  g.take('48895cc220')
 g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,rawStores=[[0,8]],arrayStrideBytes=8,sizeIncrement=1,incomingValueRegister='rdx-qword',
  capacityGreaterThanInitialSizeRequired=True,normalReturn=True,completeFrameAndNonvolatilesRestored=True,
  canonicalRegistration=canonical,canonicalPointerEquivalenceClaimed=False)


def capacity_program(regions,entry,s,*,positive):
 need('literal-capacity-profile',bool,type(positive));g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
 g.take('498b4820','488b89c0000000');g.branch('74',not positive,1)
 if positive:
  g.take('ba01000000');g.call(s['context']);g.take('8bd3','488bc8');g.call(s['arrayAllocate'])
 else:
  g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('75',True,1)
  g.take('488b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01');g.jump('eb',1)
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f');need('capacity-tail-barrier',s['barrier'],g.relative('e9'))
 return dict(selectedBytes=g.seen,positiveCapacity=positive,capacityBits=32,requestedCapacityUnchanged=True,
  itemsSlot=16,countWrites=0,versionWrites=0,completeFrameAndNonvolatilesRestored=True,normalReturnViaBarrier=True,
  condition='Independent exact closed Vector2Int array contexts, nonnegative unchanged capacity, typed zeroed allocation or ready static empty array and normal helper/barrier effects. No element codec is supplied by this constructor.')


def derive(image,pins,*,typed_request,call_target):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import float_list_sources,lang_key_list_sources,numeric_list_sources,pooled_global_buff_id_sources
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 from scripts.game_data.memorypack.leveldata_integer_vector_layout import derive_layout
 from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_header_program,key_provider_program
 from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.skill_value_list_context import derive as list_context
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
 pointer=context['closedCarrier']['classArguments'][0]['typePointerVa'];layout=derive_layout(image,type_pointer=pointer)
 need('exact-Int2-layout',(TYPE,8,[],[]),(layout['typeName'],layout['managedBytes'],layout['referenceLaneOffsets'],layout['paddingByteRanges']))
 td=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1'];method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
 registration=json.loads(json.dumps(ge.resolve(method.index,[TYPE],[])));element=owned(image,registration['pointer'])
 need('same-exact-closed-element',context['registration']['classInstantiation']['arguments'],registration['classInstantiation']['arguments'])
 slots={r['relativeSlot']:r for r in context['context']['entries']}
 s={role:_body_target(body,text,before=before)for role,text,before in(
  ('header','test al, al',True),('context','mov rcx, [rcx+0xc0]',False),('allocate','mov rcx, rax',False),
  ('constructor','mov r8, [r8+0x8]',False),('barrier','mov [r12], rbx',False),
  ('provider','mov rcx, [rcx+0x18]',False),('prepare','mov rcx, [r14]',False),('add','mov r8, [r8+0x30]',False))}
 s['callback']=element['pointer'];offsets=scalar.reader_offsets(image,'storyIntegerVectorList')
 programs=[list_program(body['regions'],body['pointer'],s,offsets,count=n)for n in(-1,0,1,2,3)]
 induction=prove_induction(programs,initial='448bfe',increment='41ffc7',comparison='453bfd',counter='r15d',saved_count='r13d',max_count=LIMIT)
 sources={name:owned(image,s[name])for name in('header','constructor','provider','add')}
 callback=callback_program(element['regions'],element['pointer'],offsets);actual_add=add_program(sources['add']['regions'],s['add'])
 list_method,=[m for m in md.methods_for(ctx.index.types['MemoryPack.Formatters.ListFormatter`1'])if md.string(m.name_index)=='Deserialize']
 definitions=dict(list=list_method.index,callback=method.index,capacity=slots[1]['methodSpec'][0],Clear=slots[2]['methodSpec'][0],Add=slots[6]['methodSpec'][0])
 abis=float_list_sources._method_abis(image,ctx,definitions,context['context'])
 ctor_registration=ge.resolve(definitions['capacity'],[TYPE],[]);need('actual-closed-constructor',ctor_registration['pointer'],s['constructor'])
 canonical_registration=ge.resolve(definitions['Add'],[TYPE],[]);canonical=owned(image,canonical_registration['pointer'])
 canonical_add=add_program(canonical['regions'],canonical['pointer'],canonical=True)
 ctor=sources['constructor'];cs=dict(context=s['context'],barrier=s['barrier'],arrayAllocate=_body_target(ctor,'mov rcx, rax'))
 constructors=[capacity_program(ctor['regions'],ctor['pointer'],cs,positive=p)for p in(False,True)]
 offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 header=dictionary_header_program(sources['header']['regions'],s['header'],offsets)
 pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[pc],label='storyIntegerVectorList.provider')
 pcs={r['relativeSlot']:r for r in pc['entries']};need('provider-context-slots',[0,1],sorted(pcs));pm=md.methods[pc['definition']]
 need('provider-nominal-static-ABI',('MemoryPack.MemoryPackFormatterProvider','GetFormatter',True,0),
  (image.type_name(pm.declaring_type),md.string(pm.name_index),bool(pm.flags&16),pm.parameter_count))
 need('provider-owned-return',ctx.type_pointer(pm.return_type),ctx.type_pointer(pcs[1]['index']))
 need('provider-formatter-result','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
 for child in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):need('provider-owned-MVAR',(pm.index,0),(child['parameterOwner']['methodIndex'],child['parameterOwner']['ordinal']))
 provider=sources['provider'];calls=[control_transfer(r)['target']for r in provider['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'][:4]
 need('four-provider-normal-calls',4,len(calls));ps=dict(zip(('typeFromHandle','backend','type','assignable'),calls,strict=True))
 provider_program=key_provider_program(provider['regions'],provider['pointer'],dict(typeHandle=ps['typeFromHandle'],keyBackend=ps['backend'],context=ps['type'],cast=ps['assignable']))
 cast=owned(image,ps['assignable']);predicate=_body_target(cast,'mov rcx, [rcx]')
 cast_program=pooled_global_buff_id_sources.successful_cast(cast['regions'],cast['pointer'],predicate)
 need('same-indexed-provider-context',s['context'],ps['type'])
 path=CONTRACTS_DIR/'levelscript_int_list_native.json';raw=path.read_bytes();dep=json.loads(raw);need('generic-provider-build',pins,dep['nativeInputs'])
 backend=owned(image,ps['backend']);backend_target=base+dep['bodies']['providerBackend']['entryRva']
 backend_program=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
 factory=lang_key_list_sources.generic_provider_factory(image,pins,dict(backend=backend_target,context=s['context']),need)
 usages=[]
 for owner,cell,name in((body,programs[1]['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
  (provider,provider_program['typeClassCell'],'System.Type'),(provider,provider_program['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
  (backend,backend_program['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
  row,=[r for r in owner['rows']if len(bytes.fromhex(r['bytes']))==7 and bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'
   and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
  usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='storyIntegerVectorList.namedCell');need('actual-named-provider-cell',(1,name),(usage['tag'],usage['typeName']));usages.append(usage)
 need('same-Type-key-provider-class',factory['providerClassCell'],programs[1]['providerClassCell'])
 need('same-backend-provider-class',factory['providerClassCell'],backend_program['providerOwnerCell'])
 barrier,barrier_proof,_=_fast_barrier(image,s['barrier']);need('dependency-bookend',raw,path.read_bytes());_publication_gate(image,pins)
 cap=dict(typeName=LIST,elementType=TYPE,capability=CAP,countLimit=LIMIT,countRange=[-1,LIMIT],nullable=True,positiveCountsAdmitted=True,
  headerBytes=4,elementWireBytes=8,managedElementBytes=8,elementRecordHeaderBytes=0,rawInt32Axes=['x','y'],rawBitsPreserved=True,
  initiallyNullListRequired=True,packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
  wholeGrammarAdmitted=True,actualCallbackEqualsProvedChildRequired=True,runtimeProviderSelectionObserved=False)
 return json.loads(json.dumps(dict(schema='endfield.story-integer-vector-list-component.v1',status='validated-conditional-Vector2Int-list',nativeInputs=pins,
  capability=cap,parentFieldAdmitted=False,wholeOwnerAdmitted=False,proof=dict(context=context,layout=layout,listPrograms=programs,induction=induction,
   callbackRegistration=registration,callback=callback,actualAdd=actual_add,canonicalAddRegistration=canonical_registration,canonicalAdd=canonical_add,
   constructorRegistration=ctor_registration,constructors=constructors,methodAbis=abis,header=header,providerContext=pc,
   provider=provider_program,successfulCast=cast_program,backend=backend_program,factory=factory,classUsages=usages,
   barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={k:v-base for k,v in s.items()},
   sourceWindows=dict(list=body['windows'],callback=element['windows'],canonicalAdd=canonical['windows'],backend=backend['windows'],cast=cast['windows'],**{k:v['windows']for k,v in sources.items()})),
  evidenceBoundary=dict(exact='Fresh actual closed reference request, nominal Vector2Int owned Int32 axes/getters/layout and exact registered unmanaged callback, full count/raw8/Add/capacity/header/provider programs with bounded induction. Actual and canonical Add bodies are proved separately.',
   conditional=__doc__,unresolved=['actual enclosing field/local/store','cold/refill/growth and existing lists','runtime provider selection','whole owner/physical EOF']))))
