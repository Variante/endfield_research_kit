"""Current Line value12 list loop and Add; actual wire grammar stays child-owned."""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.leveldata_line_value_sources import TYPE

LIST='System.Collections.Generic.List`1<'+TYPE+'>'
LIMIT=4096
VALUE_CAP='story-line-value'
LIST_CAP='story-line-list'


def need(key,value):
 if not value:raise ValueError('storyLineList.'+key)


def list_program(regions,entry,s,*,count):
 need('literal-count-witness',type(count)is int and -1<=count<=3)
 g=BytesPath(regions,entry)
 g.take('4055','56','4154','4157','4883ec48');ready=flag(g)
 g.take('498bf1','4d8bf8','4c8be2');g.branch('0f84',False)
 g.take('33c0','488d542478','33ed','4889442420','498bcc','896c2478','89442428');g.call(s['header'])
 g.take('84c0');g.branch('0f84',count==-1);provider=None;callbacks=[];adds=[]
 if count==-1:
  g.take('498bcf','49892f');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4c89ac2488000000','48895c2470','4889bc2480000000','4c89742440','448b6c2478','49392f');g.branch('0f85',False)
  g.take('488b4e20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
  g.take('488bd8','4885c0');g.branch('0f84',False)
  g.take('488b4e20','488b91c0000000','488b4a08','48396920');g.branch('0f84',False)
  g.take('488b4620','418bd5','488bcb','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
  g.take('498bcf','49891f');g.call(s['barrier']);provider=g.relative('488b0d')
  g.take('39a9e0000000');g.branch('0f84',False)
  g.take('488b4620','488b88c0000000','488b4918');g.call(s['provider']);g.take('488bd8','4585ed');g.branch('0f8e',count==0)
  if count:g.take('66660f1f840000000000')
  for index in range(count):
   g.take('33c0','4889442420','89442428','4885db');g.branch('0f84',False)
   g.take('4c8d4c2420','4d8bc4','488bd3');callbacks.append(g.at);g.call(s['dispatch'])
   g.take('498b3f','f20f10442420','448b742428','f20f11442478','4885ff');g.branch('74',False,1)
   g.take('488b4620','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
   g.take('488b4620','488d542430','488bcf','f20f11442430','4489742438','4c8b80c0000000','4d8b4030')
   adds.append(g.at);g.call(s['Add']);g.take('ffc5','413bed');g.branch('0f8c',index+1<count)
  g.take('488b5c2470','488bbc2480000000','4c8b742440','4c8bac2488000000')
 g.take('4883c448','415f','415c','5e','5d','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,countWitness=count,newList=True,
  elementCallbackSites=callbacks,AddCallSites=adds,providerClassCell=provider,headerBytes=4,
  managedElementBytes=12,elementWireBytes=None,callbackOutputZeroedBytes=12,
  sameComplete12CopiedToDistinctAddLocal=True,initiallyNullOutputRequired=True,
  counter='EBP starts0/increments1',savedCount='R13D unchanged',childWireGrammarAdmitted=False,
  normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,growthAdmitted=False,
  frame=dict(entryRspDelta=-104,callShadow=[0,32],callbackOutputLocal=[32,44],AddLocal=[48,60],
   savedR14Local=[64,72],headerThenCapturedLow8EntryHome=[16,24],
   savedEntryHomes=dict(rbx=[8,16],rdi=[24,32],r13=[32,40]),pushedNonvolatiles=['rbp','rsi','r12','r15'],
   headerHomeRetiredAfterCountCapturedInR13D=True))


def add_program(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec30','ff411c','498bf0','4c8b4910','488bfa','48634118','488bd9','4d85c9');g.branch('74',False,1)
 g.take('413b4118');g.branch('0f83',False)
 g.take('8d4801','894b18','413b4118');g.branch('73',False,1)
 g.take('f20f1002','488d0440','498d0c81','8b4208','f20f114120','894128',
  '488b5c2440','488b742448','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,managedElementBytes=12,arrayStride=12,arrayDataOffset=32,
  incomingValueRegister='rdx',copiedSourceSlices=[[0,8],[8,4]],storedElementSlices=[[0,8],[8,4]],
  itemsOffset=16,sizeOffset=24,versionOffset=28,countIncrement=1,versionIncrement=1,
  referenceLaneOffsets=[],full12BitsStored=True,growthAdmitted=False,normalReturn=True,entryRspRestored=True,
  childWireGrammarAdmitted=False,frame=dict(entryRspDelta=-56,callShadow=[0,32],
   savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushedNonvolatiles=['rdi']))


def derive(image,pins,*,typed_request,call_target):
 """Fresh actual parent context, own child, current loop/ABI/provider/typed storage."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,derive_typed_usage_context
 from scripts.game_data.memorypack import scalar_param_native as scalar,float_list_sources,numeric_list_sources,lang_key_list_sources,int_list_sources,pooled_global_buff_id_sources
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack.skill_value_list_context import derive as list_context,bind_list_add_abi
 from scripts.game_data.memorypack.leveldata_line_transfer_sources import derive as transfer_source
 from scripts.game_data.memorypack.leveldata_vector_tuple_list_sources import capacity_program,normal_call_targets,normal_call_after
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_header_program,key_provider_program
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 check=lambda k,e,a:scalar.need('storyLineList',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
 check('exact-closed-list',LIST,context['closedListType']);value=transfer_source(image,pins)
 check('same-selected-list-registration',context['registration'],value['proof']['listRegistration'])
 def call(source,offset):
  at=source['pointer']+offset;row,=[r for r in source['rows']if int(r['va'],16)==at];raw=bytes.fromhex(row['bytes'])
  check('actual-owned-E8:'+str(offset),(5,232),(len(raw),raw[0]));return at+5+int.from_bytes(raw[1:],'little',signed=True)
 symbols={key:call(body,offset)for key,offset in dict(header=58,context=124,allocate=132,constructor=195,barrier=206,provider=245,dispatch=303,Add=393).items()}
 check('same-actual-child-dispatch',base+value['proof']['symbolRvas']['dispatch'],symbols['dispatch'])
 paths=[list_program(body['regions'],body['pointer'],symbols,count=n)for n in(-1,0,1,2,3)]
 induction=prove_induction(paths[1:],initial='33ed',increment='ffc5',comparison='413bed',counter='ebp',saved_count='R13D',max_count=LIMIT)
 slots={r['relativeSlot']:r for r in context['context']['entries']};sources={role:owned(image,symbols[role])for role in('header','constructor','provider','Add')}
 offset=scalar.reader_offsets(image,'storyLineList');offset['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 header=dictionary_header_program(sources['header']['regions'],symbols['header'],offset)
 add=add_program(sources['Add']['regions'],symbols['Add']);abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
 list_method,=context['registration']['methodDefinitionIndices'];callback,=value['proof']['registrations']['adapter']['methodDefinitionIndices']
 definitions=dict(list=list_method,callback=callback,capacity=slots[1]['methodSpec'][0],Add=slots[6]['methodSpec'][0],Clear=slots[2]['methodSpec'][0])
 abis=float_list_sources._method_abis(image,ctx,definitions,context['context'])
 ctor=sources['constructor'];cs=dict(context=symbols['context'],barrier=symbols['barrier'],
  arrayAllocate=normal_call_after(ctor['rows'],'mov rcx, rax',preceding='8bd3'))
 constructors=[capacity_program(ctor['regions'],ctor['pointer'],cs,positive=n)for n in(False,True)]
 constructor_registration=ge.resolve(slots[1]['methodSpec'][0],[TYPE],[])
 check('actual-exact-closed-constructor',constructor_registration['pointer'],symbols['constructor'])
 provider=sources['provider'];calls=normal_call_targets(provider['rows']);check('four-normal-provider-calls',4,len(calls))
 ps=dict(zip(('typeHandle','backend','indexed','cast'),calls,strict=True))
 provider_proof=key_provider_program(provider['regions'],provider['pointer'],dict(typeHandle=ps['typeHandle'],keyBackend=ps['backend'],context=ps['indexed'],cast=ps['cast']))
 check('same-selected-TypeFromHandle',base+value['proof']['symbolRvas']['typeHandle'],ps['typeHandle'])
 check('same-indexed-context',symbols['context'],ps['indexed'])
 pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[pc],label='storyLineList.provider')
 pcs={r['relativeSlot']:r for r in pc['entries']};check('owned-provider-slots',[0,1],sorted(pcs));pm=md.methods[pc['definition']]
 check('provider-static-noargs',('MemoryPack.MemoryPackFormatterProvider','GetFormatter',True,0),
  (image.type_name(pm.declaring_type),md.string(pm.name_index),bool(pm.flags&16),pm.parameter_count))
 check('provider-own-return',ctx.type_pointer(pm.return_type),ctx.type_pointer(pcs[1]['index']))
 check('formatter-result-definition','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
 for child in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):
  check('provider-same-owned-MVAR',(pm.index,0),(child['parameterOwner']['methodIndex'],child['parameterOwner']['ordinal']))
 cast=owned(image,ps['cast']);predicate=normal_call_targets(cast['rows']);check('one-owned-cast-predicate',1,len(predicate))
 casts=[pooled_global_buff_id_sources.successful_cast(cast['regions'],cast['pointer'],predicate[0],null=n)for n in(False,True)]
 path=CONTRACTS_DIR/'levelscript_int_list_native.json';before=path.read_bytes();fact=json.loads(before);check('generic-dependency-build',pins,fact['nativeInputs'])
 backend=owned(image,ps['backend']);backend_target=base+fact['bodies']['providerBackend']['entryRva']
 backend_proof=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
 factory=lang_key_list_sources.generic_provider_factory(image,pins,dict(backend=backend_target,context=symbols['context']),check)
 check('same-provider-class',[factory['providerClassCell']]*2,[paths[1]['providerClassCell'],provider_proof['providerClassCell']])
 resolver=fact['bodies']['contextResolver'];check('same-actual-context-resolver',base+resolver['entryRva'],symbols['context'])
 image.check_windows(resolver['windows'],label='storyLineList.contextResolver')
 resolver_program=int_list_sources.initialized_class([(base+w['startRva'],image.window_bytes(w))for w in resolver['windows']],symbols['context'],indexed=True)
 usages=[]
 for source,cell,typename in((body,paths[1]['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
  (provider,provider_proof['typeClassCell'],'System.Type'),(provider,provider_proof['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider')):
  row,=[r for r in source['rows']if len(bytes.fromhex(r['bytes']))==7 and bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'
   and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
  usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='storyLineList.namedClass')
  check('actual-named-class',(1,typename),(usage['tag'],usage['typeName']));usages.append(usage)
 barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier']);check('declaration-bookend',before,path.read_bytes());_publication_gate(image,pins)
 child_cap=dict(typeName=TYPE,memberCount=2,managedBytes=12,referenceLaneOffsets=[],paddingByteRanges=[],
  serializedOrder=['length:Int32','startPos:Int2-raw8'],positiveWireBytes=13,canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=12,
  canonicalOriginalAdapterAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,
  actualCallbackEqualsCanonicalRequired=True,liveFormatterSelectionObserved=False)
 cap=dict(typeName=LIST,elementType=TYPE,elementCapability=VALUE_CAP,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,
  managedElementBytes=12,elementWireBytes=None,nullable=True,positiveCountsAdmitted=True,initiallyNullListRequired=True,
  actualCallbackEqualsCanonicalRequired=True,full12BitsStored=True,profileAdmitted=True,growthAdmitted=False,
  wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
  packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base)
 return json.loads(json.dumps(dict(schema='endfield.story-line-list-source.v1',status='validated-conditional-line-list-profile',nativeInputs=pins,
  capabilities={VALUE_CAP:child_cap,LIST_CAP:cap},proof=dict(context=context,value=value,programs=paths,induction=induction,
   header=header,Add=add,AddAbi=abi,methodAbis=abis,constructors=constructors,constructorRegistration=constructor_registration,
   provider=provider_proof,providerContext=pc,casts=casts,backend=backend_proof,factory=factory,classUsages=usages,
   contextResolver=resolver,contextResolverProgram=resolver_program,barrier=dict(source=barrier,proof=barrier_proof),
   symbolRvas={k:v-base for k,v in symbols.items()},sourceWindows=dict(list=body['windows'],**{k:b['windows']for k,b in sources.items()},cast=cast['windows'],backend=backend['windows'])),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Actual closed Line value12 list context, own MC2/FF child and canonical hidden12 default/interface/getter, selected compared callback; complete signed count/null/newzero/bounded4096 EBP loop, typed capacity and complete12 Add/local/array stores/full frames.',
   conditional='Initially null output, fresh zeroed count-sized typed storage, initialized coherent exact callbacks/contexts and normal compatible allocator/provider/helper/disabled collector effects. Disjoint stable buffered input/output/frame. No floating interpretation is given to MOVSD bit transfers. Runtime selection remains unobserved.',
   unresolved=['reused List/growth','actual enclosing field and owner physical EOF/publication','runtime callback/provider choice and behavior']))))
