"""Owned Tracking value-list source programs, without scalar-size wire aliases.

The collection's signed count, current closed generic source/context, actual
element callback, disjoint hidden-value/Add locals and concrete Add storage
must all be independently joined. The canonical MC3/MC2 element grammar is
separate from direct raw36 parent reads and from managed element strides.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.leveldata_tracking_value_sources import BOUNDS,POINT,SPECS

LIMIT=4096


def need(check,condition):
 if not condition:raise ValueError('storyTrackingList.'+check)


def list_field_declarations(rows,*,owned_parameter_pointer):
 """Named generic declarations only; actual storage offsets come from source."""
 need('literal-owned-List-VAR-pointer',type(owned_parameter_pointer)is int and owned_parameter_pointer>0)
 need('exact-unique-declared-list-fields',isinstance(rows,list)and len(rows)==3
  and all(type(row)is dict and row.get('owner')=='System.Collections.Generic.List`1'
   and type(row.get('definition'))is int and row['definition']>=0 for row in rows)
  and{row.get('field')for row in rows}=={'_items','_size','_version'}
  and len({row['definition']for row in rows})==3)
 for row in rows:
  raw=bytes.fromhex(row.get('typeRawHex',''))
  need('ordinary-instance-field:'+row['field'],len(raw)==16 and not int.from_bytes(raw[8:10],'little')&16
   and raw[10:12]==(bytes((29,0))if row['field']=='_items'else bytes((8,128))))
  if row['field']=='_items':need('same-owned-element-VAR-array',int.from_bytes(raw[:8],'little')==owned_parameter_pointer)
 return dict(declarations=rows,openGenericOffsetsRead=False,namedFieldOffsetsClaimed=False,
  storageRolesProvedByActualPrograms=['constructor items-pointer store','Add size/version increments and exact array stores'],
  enclosingRuntimeClassLayoutObserved=False)


def resolver_prefix(declaration,actual_rva):
 """Select the actual owned prefix, never equate indexed/nonindexed entries."""
 need('literal-actual-class-resolver-entry',type(actual_rva)is int and actual_rva>=0
  and type(declaration)is dict and declaration.get('ownership')=='selectedInitializedPrefixes')
 rows=[row for row in declaration.get('windows',[])if row.get('startRva')==actual_rva]
 need('one-exact-reviewed-actual-resolver-prefix',len(rows)==1 and type(rows[0].get('endRva'))is int
  and rows[0]['endRva']>actual_rva)
 return dict(entryRva=actual_rva,windows=rows,ownership='selectedInitializedPrefixOnly',
  canonicalEntryIdentityClaimed=False,fullPhysicalExtentProved=False)


def dispatch_program(regions,entry,*,prepare):
 """Full slot5 tail; an incoming selector is overwritten before any use."""
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bd9','498bf8','488bf2')
 g.call(prepare)
 g.take('4c8b0e','4c8bc3','488bd7','488bce','498b8190010000','4d8b8998010000',
  '488b5c2430','488b742438','4883c420','5f','48ffe0')
 return dict(selectedBytes=g.seen,callbackSlot=5,callbackOffset=400,methodInfoOffset=408,
  entryRcxSelectorUsed=False,callbackArguments=dict(rcx='incoming RDX formatter',rdx='incoming R8 Reader',
   r8='incoming R9 output',r9='same formatter class slot5 MethodInfo'),sameReaderAndOutput=True,
  callbackTarget='same formatter class slot5 callback',selectedCallbackEqualsOwnCanonicalRequired=True,
  entryRspRestoredBeforeTail=True,allNonvolatilesRestoredBeforeTail=True,normalReturnViaCallback=True,
  frame=dict(entryRspDelta=-40,callShadow=[0,32],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushed=['rdi']),
  canonicalPointerIdentityInferred=False,elementGrammarAdmitted=False)


def provider_program(regions,entry,s):
 """Ready closed generic key, unchanged backend and full compatible result."""
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1)
 g.take('488b5f38');type_site=g.at;type_cell=g.relative('488b0d');g.take('488b1b');g.call(s['classInit'])
 g.take('33d2','488bcb');g.call(s['typeHandle']);provider_site=g.at;provider_cell=g.relative('488b0d')
 g.take('488bd8');g.call(s['classInit']);g.take('488bcb');g.call(s['backend'])
 g.take('488b4f38','488bd8','488b4908');g.call(s['context']);g.take('488bd0','488bcb');g.call(s['cast'])
 g.take('4885c0');g.branch('0f85',True)
 g.take('488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,typeClassCell=type_cell,typeClassInstructionVa=type_site,
  providerClassCell=provider_cell,providerClassInstructionVa=provider_site,typeContextSlot=0,resultTypeContextSlot=1,
  key='same exact context slot0 to TypeFromHandle and unchanged Type key to backend',
  result='same full compatible nonnull backend formatter reference after owned cast',
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,liveFormatterSelectionObserved=False,
  selectedCallbackEqualsOwnCanonicalRequired=True)


def bounds_add_forwarder(regions,entry,*,target):
 """An actual by-value36 copy thunk, never pointer equivalence with its callee."""
 g=BytesPath(regions,entry)
 g.take('4883ec58','0f1002','8b4220','0f104a10','488d542420','89442440','0f29442420','0f294c2430')
 site=g.at;g.call(target);g.take('4883c458','c3')
 return dict(selectedBytes=g.seen,managedArgumentBytes=36,copiedSlices=[[0,16],[16,16],[32,4]],
  delegateInstructionVa=site,delegateTargetVa=target,sameListReceiverRcx=True,sameClosedMethodInfoR8=True,
  hiddenArgumentRegister='rdx',ownArgumentLocal=[32,68],frame=dict(entryRspDelta=-88,callShadow=[0,32]),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,pointerEquivalenceClaimed=False)


def add_program(regions,entry,*,type_name):
 """Enough-capacity Add only; exact source arithmetic owns the16/36 stride."""
 need('finite-value-Add',type_name in SPECS);bounds=type_name==BOUNDS;g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec'+('50'if bounds else'30'),'ff411c','488bd9')
 if bounds:g.take('4c8b4910','498bf0','48634918','488bfa','4d85c9');g.branch('0f84',False)
 else:g.take('488b4910','498bf8','488bf2','4c634b18','4885c9');g.branch('74',False,1)
 g.take('413b4918'if bounds else'443b4918');g.branch('73',False,1)
 g.take('8d4101'if bounds else'418d4101','894318','413b4918'if bounds else'443b4918')
 g.branch('0f83'if bounds else'73',False,4 if bounds else 1)
 if bounds:g.take('0f1002','8b4220','488d0cc9','0f104a10','410f11448920','410f114c8930','4189448940')
 else:g.take('0f1002','498d4102','4803c0','0f1104c1')
 g.take('488b5c24'+('60'if bounds else'40'),'488b7424'+('68'if bounds else'48'),
  '4883c4'+('50'if bounds else'30'),'5f','c3')
 width=SPECS[type_name]['managedBytes']
 return dict(selectedBytes=g.seen,typeName=type_name,managedElementBytes=width,arrayStride=width,arrayDataOffset=32,
  itemsOffset=16,sizeOffset=24,versionOffset=28,sizeIncrement=1,versionIncrement=1,
  copiedSourceSlices=[[0,16],[16,16],[32,4]]if bounds else[[0,16]],
  arrayElementStores=[[0,16],[16,16],[32,4]]if bounds else[[0,16]],completeValueStoredUnchanged=True,
  incomingValueRegister='rdx',referenceLaneOffsets=[],growthAdmitted=False,childWireGrammarAdmitted=False,
  normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,
  frame=dict(entryRspDelta=-88 if bounds else-56,callShadow=[0,32],
   savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushed=['rdi']))


def capacity_program(regions,entry,s,*,positive):
 """Actual value-list capacity constructor, distinct from other list clones."""
 need('literal-capacity-mode',type(positive)is bool);g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','8bda','498bf0','488bf9','85d2')
 g.branch('78',False,1);g.take('498b4820','488b89c0000000');g.branch('74',not positive,1)
 if positive:
  g.take('488b4908');g.call(s['context']);g.take('8bd3','488bc8');g.call(s['arrayAllocate']);g.jump('eb',1)
 else:
  g.take('488b09');g.call(s['context']);g.take('488bc8');g.call(s['classInit'])
  g.take('488b4620','488b88c0000000','488b09');g.call(s['context']);g.take('488b88b8000000','488b01')
 g.take('488d4f10','48894710','488b5c2430','488b6c2438','488b742440','4883c420','5f')
 need('same-owned-constructor-barrier-tail',g.relative('e9')==s['barrier'])
 return dict(selectedBytes=g.seen,positiveCapacity=positive,capacityUnchanged=True,
  typedArrayContextSlot=1,staticEmptyListContextSlot=0,itemsFieldOffset=16,directSizeOrVersionWrites=False,
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True,
  frame=dict(entryRspDelta=-40,callShadow=[0,32],savedEntryHomes=dict(rbx=[8,16],rbp=[16,24],rsi=[24,32]),pushed=['rdi']),
  managedWidthInferredFromConstructor=False,typedAllocationEffectsConditional=True)


def list_program(regions,entry,s,*,type_name,count):
 """Complete selected initialized fresh-list path at finite count witnesses."""
 need('finite-nominal-count',type_name in SPECS and type(count)is int and -1<=count<=3)
 bounds=type_name==BOUNDS;g=BytesPath(regions,entry);callbacks=[];adds=[];provider=None
 if bounds:
  g.take('48895c2408','4889742418','55','57','4154','4155','4157','488d6c24c9','4881eca0000000','4533ed','498bd9')
  ready=g.relative('44382d');g.take('498bf8','4c8be2');g.branch('75',True,1)
  g.take('0f57c0','44896d6f','33c0','488d556f','498bcc','8945df','0f1145bf','0f1145cf')
 else:
  g.take('488bc4','48895808','48897018','48897820','4154','4156','4157','4883ec50');ready=flag(g)
  g.take('498bd9','0f2970d8','498bf8','4c8be2');g.branch('75',True,1)
  g.take('0f57c0','c744247800000000','488d542478','498bcc','0f11442420')
 g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:
  g.take('488bcf','4c892f'if bounds else'48c70700000000');g.call(s['barrier'])
 else:
  if bounds:g.take('488b4320','488b88c0000000','4c392f');g.branch('74',True,1)
  else:g.take('48833f00','488b4320','488b88c0000000');g.branch('74',True,1)
  g.take('488b09');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
  g.take('488bf0','4885c0');g.branch('0f84',False)
  g.take('488b4b20','488b91c0000000','488b4a08')
  g.take('4c396920'if bounds else'4883792000');g.branch('75',True,1)
  g.take('488b4320','488bce','8b556f'if bounds else'8b542478','4c8b80c0000000','4d8b4008')
  g.call(s['constructor']);g.take('488bcf','488937');g.call(s['barrier'])
  provider=g.relative('488b0d');g.call(s['classInit'])
  g.take('488b4320','488b88c0000000','488b4918');g.call(s['provider'])
  if bounds:g.take('488bf0','458bfd','44396d6f')
  else:g.take('4533ff','488bf0','44397c2478')
  g.branch('0f8e',count==0)
  for index in range(count):
   if bounds:g.take('33c0','0f57c0','8945df','0f1145bf','0f1145cf','4885f6');g.branch('0f84',False)
   else:g.take('0f57c0','0f11442420','4885f6');g.branch('74',False,1)
   g.take('4c8d4dbf'if bounds else'4c8d4c2420','4d8bc4','488bd6');callbacks.append(g.at);g.call(s['dispatch'])
   if bounds:g.take('0f1045bf','4c8b2f','8b45df','8945b7','0f104dcf','0f1145e7','0f114df7','4d85ed');g.branch('74',False,1)
   else:g.take('4c8b37','0f28742420','4d85f6');g.branch('74',False,1)
   g.take('488b4320','488b88c0000000','488b4130','4883782000');g.branch('75',True,1)
   if bounds:g.take('8b45b7','488d5507','894527','498bcd','488b4320','0f294507','0f294d17')
   else:g.take('488b4320','488d542430','498bce','660f7f742430')
   g.take('4c8b80c0000000','4d8b4030');adds.append(g.at);g.call(s['Add']);g.take('41ffc7')
   g.take('443b7d6f'if bounds else'443b7c2478');g.branch('0f8c'if bounds else'7c',index+1<count,4 if bounds else 1)
  if count:g.jump('eb',1)
 if bounds:g.take('4c8d9c24a0000000','498b5b30','498b7340','498be3','415f','415d','415c','5f','5d','c3')
 else:g.take('0f28742440','4c8d5c2450','498b5b20','498b7330','498b7b38','498be3','415f','415e','415c','c3')
 return dict(selectedBytes=g.seen,typeName=type_name,metadataReadyFlag=ready,countWitness=count,newList=True,
  headerBytes=4,managedElementBytes=SPECS[type_name]['managedBytes'],elementWireBytes=None,
  elementCallbackSites=callbacks,AddCallSites=adds,providerClassCell=provider,initiallyNullOutputRequired=True,
  callbackOutputZeroedBytes=SPECS[type_name]['managedBytes'],callbackReader='incoming RDX -> R12 -> R8',
  callbackFormatter='owned provider full reference RSI -> RDX',callbackOutput='own disjoint hidden local -> R9',
  exactFullValueCopiedToDistinctAddLocal=True,growthAdmitted=False,childGrammarAdmitted=False,
  normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,
  frame=(dict(entryRspDelta=-200,rbpEntryOffset=-95,callShadow=[0,32],callbackLocal=[40,76],
   capturedLowAndMiddleLocal=[80,112],capturedHighLocal=[32,36],AddLocal=[112,148],savedCountEntryHome=[16,20],
   savedEntryHomes=dict(rbx=[8,16],rsi=[24,32]),pushed=['rbp','rdi','r12','r13','r15'])if bounds else
   dict(entryRspDelta=-104,callShadow=[0,32],callbackLocal=[32,48],AddLocal=[48,64],savedXmm6Local=[64,80],
    savedCountEntryHome=[16,20],savedEntryHomes=dict(rbx=[8,16],rsi=[24,32],rdi=[32,40]),pushed=['r12','r14','r15'])))


def derive(image,pins,*,typed_request,call_target,element_type):
 """Own actual typed list/count/callback/typed storage and canonical child."""
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import scalar_param_native as scalar,float_list_sources,int_list_sources,pooled_global_buff_id_sources as provider_helpers
 from scripts.game_data.memorypack import leveldata_tracking_transfer_sources as transfer,leveldata_tracking_components as components
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack.skill_value_list_context import derive as list_context,bind_list_add_abi
 from scripts.game_data.memorypack.leveldata_vector_tuple_list_sources import normal_call_after
 from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_header_program
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 check=lambda key,expected,actual:scalar.need('storyTrackingList',key,expected,actual)
 _publication_gate(image,pins);need('finite-owned-element',element_type in SPECS)
 base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=element_type)
 value=transfer.derive(image,pins,element_type);value_cap=components.value_capability(value,pins)
 def calls(source):return[control_transfer(row)['target']for row in source['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8']
 targets=calls(body);need('complete-current-list-call-layout',len(targets)==12)
 s={key:targets[index]for key,index in dict(header=1,context=2,allocate=3,constructor=4,barrier=5,classInit=6,provider=7,dispatch=8,Add=9).items()}
 paths=[list_program(body['regions'],body['pointer'],s,type_name=element_type,count=n)for n in(-1,0,1,2,3)]
 bounds=element_type==BOUNDS;width=SPECS[element_type]['managedBytes']
 induction=prove_induction(paths[1:],initial='458bfd'if bounds else'4533ff',increment='41ffc7',
  comparison='443b7d6f'if bounds else'443b7c2478',counter='r15d',
  saved_count='unchanged entry RSP+16 Int32 (body RBP+111)'if bounds else'unchanged entry RSP+16 Int32 (body RSP+120)',max_count=LIMIT)
 slots={row['relativeSlot']:row for row in context['context']['entries']}
 sources={role:owned(image,s[role])for role in('header','constructor','provider','Add','dispatch','classInit')}
 offset=scalar.reader_offsets(image,'storyTrackingList');offset['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 header=dictionary_header_program(sources['header']['regions'],s['header'],offset)
 # The optimized outer36 thunk and concrete Add body have distinct addresses
 # and frames. Its same incoming RCX/R8 and exact copied argument own the join.
 add_forwarder=None
 if bounds:
  delegated=calls(sources['Add']);need('one-owned-value36-Add-delegate',len(delegated)==1)
  sources['AddCore']=owned(image,delegated[0]);add_forwarder=bounds_add_forwarder(sources['Add']['regions'],s['Add'],target=delegated[0])
  add=add_program(sources['AddCore']['regions'],delegated[0],type_name=element_type)
 else:add=add_program(sources['Add']['regions'],s['Add'],type_name=element_type)
 abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
 definitions=dict(list=context['registration']['methodDefinitionIndices'][0],
  callback=value['proof']['registrations']['adapter']['methodDefinitionIndices'][0],capacity=slots[1]['methodSpec'][0],
  Add=slots[6]['methodSpec'][0],Clear=slots[2]['methodSpec'][0])
 abis=float_list_sources._method_abis(image,ctx,definitions,context['context'])
 list_td=ctx.index.types['System.Collections.Generic.List`1'];fields=[]
 for name,kind in(('_items',29),('_size',8),('_version',8)):
  field,=[f for f in md.fields_for(list_td)if md.string(f.name_index)==name]
  scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'storyTrackingList.'+name,reference=kind==29)
  fields.append(dict(owner='System.Collections.Generic.List`1',field=name,definition=field.index,
   typeRawHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()))
 formal,=next(r for r in context['listContext']['entries']if r['relativeSlot']==0)['type']['classArguments']
 fields=list_field_declarations(fields,owned_parameter_pointer=formal['typePointerVa'])
 ctor=sources['constructor'];cs=dict(context=s['context'],barrier=s['barrier'],classInit=s['classInit'],
  arrayAllocate=normal_call_after(ctor['rows'],'mov rcx, rax',preceding='8bd3'))
 constructors=[capacity_program(ctor['regions'],ctor['pointer'],cs,positive=v)for v in(False,True)]
 constructor_registration=ge.resolve(slots[1]['methodSpec'][0],[element_type],[])
 check('actual-exact-closed-constructor',constructor_registration['pointer'],s['constructor'])
 initialized=provider_helpers.ready_class_init(sources['classInit']['regions'],s['classInit'])
 check('same-owned-ready-class-helper',base+value['proof']['symbolRvas']['classInit'],s['classInit'])
 dc=calls(sources['dispatch']);need('one-full-slot5-preparation-call',len(dc)==1)
 check('same-exact-wrapper-preparation',base+value['proof']['symbolRvas']['prepare'],dc[0])
 dispatch=dispatch_program(sources['dispatch']['regions'],s['dispatch'],prepare=dc[0])
 pcalls=calls(sources['provider']);need('complete-provider-selected-calls',len(pcalls)>=9)
 ps={key:pcalls[index]for key,index in dict(classInit=3,typeHandle=4,backend=6,context=7,cast=8).items()}
 check('same-provider-initialized-helper',s['classInit'],ps['classInit']);check('same-owned-TypeFromHandle',base+value['proof']['symbolRvas']['typeHandle'],ps['typeHandle'])
 check('same-owned-context-resolver',s['context'],ps['context'])
 provider=provider_program(sources['provider']['regions'],s['provider'],ps)
 pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[pc],label='storyTrackingList.provider')
 pcs={r['relativeSlot']:r for r in pc['entries']};check('owned-provider-slots',[0,1],sorted(pcs));pm=md.methods[pc['definition']]
 check('provider-static-noargs',('MemoryPack.MemoryPackFormatterProvider','GetFormatter',True,0),
  (image.type_name(pm.declaring_type),md.string(pm.name_index),bool(pm.flags&16),pm.parameter_count))
 check('provider-own-return',ctx.type_pointer(pm.return_type),ctx.type_pointer(pcs[1]['index']))
 check('formatter-result-definition','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
 for child in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):
  check('provider-same-owned-MVAR',(pm.index,0),(child['parameterOwner']['methodIndex'],child['parameterOwner']['ordinal']))
 sources['cast']=owned(image,ps['cast']);predicates=calls(sources['cast']);need('one-owned-cast-predicate',len(predicates)==1)
 casts=[provider_helpers.successful_cast(sources['cast']['regions'],ps['cast'],predicates[0],null=v)for v in(False,True)]
 # An exact bounded ready-class resolver declaration is rechecked as native
 # bytes and its selected program. No unwind extent or cross-contract hash is
 # invented for this small helper whose entry has no pdata owner.
 path=CONTRACTS_DIR/'levelscript_int_list_native.json';before=path.read_bytes();fact=json.loads(before)
 check('generic-context-dependency-build',pins,fact['nativeInputs']);resolver=resolver_prefix(fact['bodies']['contextResolver'],s['context']-base)
 image.check_windows(resolver['windows'],label='storyTrackingList.contextResolver')
 rr=[(base+w['startRva'],image.window_bytes(w))for w in resolver['windows']]
 resolver_program=int_list_sources.initialized_class(rr,s['context'],indexed=False)
 usages=[]
 for site,cell,name in((provider['typeClassInstructionVa'],provider['typeClassCell'],'System.Type'),
  (provider['providerClassInstructionVa'],provider['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider')):
  usage=derive_typed_usage_context(image,site-base,label='storyTrackingList.namedClass')
  check('actual-named-class',(1,name,cell-base),(usage['tag'],usage['typeName'],usage['usageCellRva']));usages.append(usage)
 need('same-provider-class-in-list',provider['providerClassCell']==paths[1]['providerClassCell'])
 barrier,barrier_proof,_=_fast_barrier(image,s['barrier']);check('dependency-unchanged-during-derive',before,path.read_bytes());_publication_gate(image,pins)
 cap=dict(typeName=context['closedListType'],elementType=element_type,elementValueType=True,
  elementCapability=components.VALUE_CAPS[element_type],headerBytes=4,countLimit=LIMIT,countRange=[-1,LIMIT],
  managedElementBytes=width,elementWireBytes=None,nullable=True,positiveCountsAdmitted=True,initiallyNullListRequired=True,
  actualCallbackEqualsCanonicalRequired=True,elementCanonicalCallbackTargetRva=value_cap['canonicalCallbackTargetRva'],
  completeManagedValueStored=True,profileAdmitted=True,growthAdmitted=False,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
  packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base)
 return json.loads(json.dumps(dict(schema='endfield.story-tracking-value-list.v1',status='validated-conditional-tracking-value-list',nativeInputs=pins,
  capabilities={components.VALUE_CAPS[element_type]:value_cap,components.LIST_CAPS[element_type]:cap},
  proof=dict(context=context,value=value,programs=paths,induction=induction,header=header,Add=add,AddForwarder=add_forwarder,
   AddAbi=abi,listFields=fields,methodAbis=abis,constructors=constructors,constructorRegistration=constructor_registration,
   dispatch=dispatch,provider=provider,providerContext=pc,casts=casts,initializedClassHelper=initialized,
   contextResolver=resolver,contextResolverProgram=resolver_program,
   contextResolverRegions=[(at,data.hex().upper())for at,data in rr],classUsages=usages,barrier=dict(source=barrier,program=barrier_proof),
   symbolRvas={k:v-base for k,v in s.items()},sourceWindows=dict(list=body['windows'],**{k:v['windows']for k,v in sources.items()}),
   sourceRegions=dict(list=[(at,data.hex().upper())for at,data in body['regions']],
    **{k:[(at,data.hex().upper())for at,data in v['regions']]for k,v in sources.items()})),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Actual closed typed ReadPackable<List<Tracking value>> source/context, signed4 count/null/fresh zero/capacity4096 induction, owned canonical MC3/MC2/default child, exact slot5 tail ABI and all16/36 bits through separate Add locals, concrete Add stride and full selected frames.',
   conditional='Initially null output; typed fresh zeroed List allocation and exact count-sized element storage; coherent ready actual nominal contexts/provider/formatter, selected slot5 equals this independently proved canonical Original callback and current wrapper/GetValue pair. Normal compatible allocator/backend/cast/helper/disabled collector and disjoint stable buffered input/output/frame. All enum and IEEE bits retained; live formatter selection is unobserved.',
   structuralOnly='Stored coordinates/bounds/match-mode values without runtime tracking meaning.',
   unresolved=['actual enclosing host field/local/frame and fresh-list state','growth/refill/errors','runtime provider/callback replacement','whole owner/physical EOF']))))
