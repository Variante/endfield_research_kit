"""Exact LsmPtr list programs; managed QWORD copies do not supply MC1 wire."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.levelscript_condition_param_sources import need

VALUE='Beyond.Gameplay.Core.LsmPtr'
LIST='System.Collections.Generic.List`1<'+VALUE+'>'


def list_program(regions,entry,s,*,count,new=True):
 need('Lsm-list-literal-witness',type(count)is int and -1<=count<=3 and type(new)is bool)
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2418','56','57','4154','4155','4157','4883ec30','4533ff','498bf9')
 ready=g.relative('44383d');g.take('498bf0','4c8bea');g.branch('75',True,1)
 g.take('488d542468','44897c2468','498bcd','4c897c2420');g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:g.take('488bce','4c893e');g.call(s['barrier'])
 else:
  g.take('488b4720','488b88c0000000','4c393e');g.branch('74',new,1)
  if new:
   g.take('488b09');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
   g.take('488b4f20','488b91c0000000','488b4a08','4c397920');g.branch('75',True,1)
   g.take('488b4720','488bcb','8b542468','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
   g.take('488bce','48891e');g.call(s['barrier'])
  else:
   g.take('488b4110','488b1e','4c397820');g.branch('75',True,1)
   g.take('ff431c','44897b18');g.jump('eb',1)
  provider=g.relative('488b0d');g.call(s['classInit'])
  g.take('488b4720','488b88c0000000','488b4918');g.call(s['provider'])
  g.take('488be8','458be7','44397c2468');g.branch('0f8e',count==0)
  loop=g.at
  for index in range(count):
   need('Lsm-same-owned-loop-entry',g.at==loop)
   g.take('4c897c2420','4885ed');g.branch('74',False,1)
   g.take('4c8d4c2420','4d8bc5','488bd5');g.call(s['dispatch'])
   g.take('4c8b3e','488b5c2420','4d85ff');g.branch('74',False,1)
   g.take('488b4720','488b90c0000000','488b4230','4883782000');g.branch('75',True,1)
   g.take('488b4720','488bd3','498bcf','4c8b80c0000000','4d8b4030');g.call(s['add'])
   g.take('41ffc4','41bf00000000','443b642468');g.branch('7c',index+1<count,1)
  if count:g.jump('eb',1)
 g.take('488b5c2460','488b6c2470','4883c430','415f','415d','415c','5f','5e','c3')
 return dict(selectedBytes=g.seen,countWitness=count,newList=new,headerBytes=4,elementCallbacks=max(count,0),
  managedElementBytes=8,elementWireBytes=None,metadataReadyFlag=ready,normalReturn=True,entryRspRestored=True,
  allIntegerNonvolatilesRestored=True,capacityFromUnchangedHeader=new and count>=0,reusedInitialCountRequired=0,
  actualMatchingLsmCallbackRequired=True,spareCapacityRequired=True,growthAdmitted=False)


def add_program(regions,entry):
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','ff411c','488bda','4c8b4910','498bf0','48635118','488bf9','4d85c9')
 g.branch('75',True,1);g.take('413b5118');g.branch('72',True,1)
 g.take('8d4201','894118','413b5118');g.branch('72',True,1)
 g.take('49895cd120','488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,managedElementBytes=8,arrayStride=8,arrayDataOffset=32,countOffset=24,versionOffset=28,
  unchangedIncomingRdx=True,countIncrement=1,versionIncrement=1,referenceBarrierCalled=False,
  normalReturn=True,entryRspRestored=True,growthAdmitted=False)


def constructor_program(regions,entry,s,*,positive):
 need('Lsm-constructor-literal-capacity',type(positive)is bool)
 g=BytesPath(regions,entry)
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20','8bda','498bf0','488bf9','85d2');g.branch('78',False,1)
 g.take('498b4820','488b89c0000000');g.branch('74',not positive,1)
 if positive:
  g.take('488b4908');g.call(s['context']);g.take('8bd3','488bc8');g.call(s['arrayAllocate']);g.jump('eb',1)
 else:
  g.take('488b09');g.call(s['context']);g.take('488bc8');g.call(s['classInit'])
  g.take('488b4620','488b88c0000000','488b09');g.call(s['context']);g.take('488b88b8000000','488b01')
 g.take('488d4f10','48894710','488b5c2430','488b6c2438','488b742440','4883c420','5f')
 need('Lsm-constructor-own-barrier',g.relative('e9')==s['barrier'])
 return dict(selectedBytes=g.seen,positiveCapacity=positive,typedArrayContextSlot=1 if positive else 0,
  countBitsPreserved=32,itemsOffset=16,countWritten=False,versionWritten=False,normalReturnViaBarrier=True,
  entryRspRestored=True,freshZeroedAllocationRequired=True)




def derive(image,pins):
 """Fresh own Param caller, ordinary value context, MC1 child and full list."""
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import pointer_param as pointer
 from scripts.game_data.memorypack import pooled_global_buff_id_sources as common,int_list_sources,utf8_source_helper
 from scripts.game_data.memorypack.levelscript_condition_small_pointer_sources import derive as derive_child,_call
 from scripts.game_data.memorypack.levelscript_condition_param_sources import _reference_join
 from scripts.game_data.memorypack.current_reference_param_sources import derive_reference_parent
 from scripts.game_data.memorypack.skill_value_list_context import derive as derive_context,bind_list_add_abi
 from scripts.game_data.memorypack.value_callback_slot_sources import program as slot_program
 from scripts.game_data.memorypack.counted_loop_sources import prove_induction
 _publication_gate(image,pins);base=image.pe.image_base;entries=GenericEntries(image)
 parent=derive_reference_parent(image,pins,value_type=LIST,reader_method='ReadPackable')
 usage=parent['typedRead'];rows=parent['parent']['instructions'];site=usage['instructionRva']
 need('own-Lsm-Param-actual-closed-context',usage['methodArguments']==[LIST]and [site,usage['instructionHex']]in rows)
 call=next(r for r in rows if r[0]>site and bytes.fromhex(r[1])[:1]==b'\xe8');raw=bytes.fromhex(call[1])
 need('own-Lsm-Param-actual-call',len(raw)==5);target=base+call[0]+5+int.from_bytes(raw[1:],'little',signed=True)
 image.check_instruction_windows([call],label='conditionLsmList.actualParamCall')
 context,body=derive_context(image,pins,typed_request=usage,call_target=target,element_type=VALUE)
 s={key:_call(body,offset)for key,offset in dict(header=80,context=151,allocate=159,constructor=236,
  barrier=247,classInit=259,provider=279,dispatch=322,add=400).items()}
 slots={r['relativeSlot']:r for r in context['context']['entries']};registrations={}
 for role,slot,classes,methods_ in(('constructor',1,[VALUE],[]),('add',6,[VALUE],[]),('provider',3,[],[VALUE])):
  selected=entries.resolve(slots[slot]['methodSpec'][0],classes,methods_)
  need('own-Lsm-selected-helper:'+role,selected['pointer']==s[role]);registrations[role]=selected
 constructor=pointer.owned(image,s['constructor']);s['arrayAllocate']=_call(constructor,59)
 capacities=[constructor_program(constructor['regions'],s['constructor'],s,positive=p)for p in(False,True)]
 add=pointer.owned(image,s['add']);addition=add_program(add['regions'],s['add']);add_abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
 provider=pointer.owned(image,s['provider']);ps={role:_call(provider,offset)for role,offset in
  dict(classInit=78,typeHandle=88,backend=111,context=127,cast=138).items()}
 need('same-Lsm-provider-context-and-ready-class',ps['context']==s['context']and ps['classInit']==s['classInit'])
 provider_program=common.compared_provider(provider['regions'],s['provider'],ps,canonical=True)
 cast=pointer.owned(image,ps['cast']);assignable,=pointer.calls(cast)
 cast_program=common.successful_cast(cast['regions'],ps['cast'],assignable)
 dispatch=pointer.owned(image,s['dispatch']);prepare=_call(dispatch,27)
 invocation=slot_program(dispatch['regions'],s['dispatch'],prepare=prepare)
 child=derive_child(image,pins,type_name=VALUE)
 need('same-Lsm-nominal-child-preparation-and-Type-helper',prepare==base+child['symbolRvas']['prepare']
  and ps['typeHandle']==base+child['symbolRvas']['typeHandle'])
 class_init=pointer.owned(image,s['classInit']);class_init_program=common.ready_class_init(class_init['regions'],s['classInit'])
 header_fact=utf8_source_helper._contract();need('own-Lsm-header-selected-inputs',header_fact['nativeInputs']==pins)
 need('own-Lsm-count-header-target',s['header']==base+header_fact['bodies']['header']['entryRva'])
 header=utf8_source_helper._validate_native(image,header_fact)
 context_path=CONTRACTS_DIR/'levelscript_int_list_native.json';context_raw=context_path.read_bytes();context_fact=json.loads(context_raw)
 need('own-Lsm-class-resolver-inputs',context_fact['nativeInputs']==pins)
 resolver=context_fact['bodies']['contextResolver'];need('own-Lsm-class-resolver-prefix',s['context']-base in[w['startRva']for w in resolver['windows']])
 image.check_windows(resolver['windows'],label='conditionLsmList.contextResolver')
 regions=[(base+w['startRva'],image.window_bytes(w))for w in resolver['windows']]
 resolver_program=int_list_sources.initialized_class(regions,s['context'])
 programs=[list_program(body['regions'],body['pointer'],s,count=count,new=new)for new in(False,True)for count in range(4)]
 null=list_program(body['regions'],body['pointer'],s,count=-1)
 induction=prove_induction(programs,initial='458be7',increment='41ffc4',comparison='443b642468',counter='r12d',saved_count='rsp+104 unchanged signed collection header')
 reference=_reference_join(image,pins,LIST)
 need('same-Lsm-Param-own-reference-getter',parent['ownedMethods']['GetValue']['pointerRva']==reference['getter']['entryRva'])
 need('Lsm-context-contract-bookend',context_path.read_bytes()==context_raw)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-condition-lsm-list-Param-source.v1',nativeInputs=pins,
  status='validated-conditional-list-Param-source',typeName='Beyond.Gameplay.Actions.Param`1<'+LIST+'>',valueType=LIST,elementType=VALUE,
  countLimit=induction['maxCount'],sourceAdmitted=True,canonicalAdapterAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
  liveFormatterSelectionObserved=False,proof=dict(parent=parent,elementList=dict(child=child,context=context,registrations=registrations,
   constructorPrograms=capacities,addProgram=addition,addABI=add_abi,providerProgram=provider_program,castProgram=cast_program,
   slotInvocation=invocation,header=header,contextResolverProgram=resolver_program,classInitProgram=class_init_program,
   programs=programs,nullProgram=null,countInduction=induction,symbolRvas={k:v-base for k,v in s.items()},
   sourceWindows={k:b['windows']for k,b in(('list',body),('constructor',constructor),('add',add),('provider',provider),('cast',cast),('dispatch',dispatch))}),
   actualConstantCall=dict(typedRequest=usage,sourceInstruction=call,sourceTargetRva=target-base),
   **{k:v for k,v in reference.items()if k!='getterMethodDefinition'}),parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
