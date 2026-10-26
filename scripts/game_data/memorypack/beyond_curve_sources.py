"""Selected Beyond FAnimationCurve wrapper and raw FKeyframe array programs.

This family is independent of UnityEngine.AnimationCurve and its imported
keyframes. Raw array elements consume32 bytes in the native stored field order;
the standalone FKeyframe generated wrapper has its own MC8 grammar. These are
distinct representations. Positive array bounds remain tied to the separately
proved copy component, never inferred from the managed element size.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='beyondCurveSource'
def need(k,condition,detail=None):
 if not condition:raise ValueError(LABEL+'.'+k+':'+str(detail)[:700])
def peek(g,n=1):return bytes(g.bytes.get(g.at+i,0)for i in range(n))
def conditional(g,codes,taken):
 first=peek(g)[0];long=first==15;opcode=peek(g,2)[1]if long else first
 need('exact-condition',opcode&15 in codes and(opcode>>4==8 if long else opcode>>4==7))
 g.branch(('0f'if long else'')+format(opcode,'02x'),taken(opcode&15),4 if long else 1)
def nonzero(g):conditional(g,(4,5),lambda c:c==5)
def jump(g):g.jump('eb',1)if peek(g)==b'\xeb'else g.jump('e9')
def update(g,offsets,width,remaining):
 c,r,a,u=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
 reg={'ebp':('8b6b','83c5','896b'),'esi':('8b73','83c6','8973')}[remaining]
 g.take(reg[0]+r)
 if width==1:g.take('83ed01'if remaining=='ebp'else'83ee01')
 else:g.take(reg[1]+bytes((-width&255,)).hex())
 conditional(g,(8,9),lambda k:k==9)
 if width==1:g.take('48ff43'+c,'ff43'+a,'ff43'+u)
 else:
  w=bytes((width,)).hex();g.take('488343'+c+w,'8343'+a+w,'8343'+u+w)
 g.take(reg[2]+r)

def curve_program(regions,entry,offsets,s,*,null=False,new=False):
 """Complete initialized static wrapper entry/new/FF/MC3/source/return."""
 need('literal-paths',type(null)is bool and type(new)is bool)
 g=BytesPath(regions,entry);g.take('48895c2410','48896c2418','4889742420','57','4883ec20');flag=g.relative('803d')+1
 g.take('00','488bfa','488bd9');nonzero(g);cur,rem=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength'))
 g.take('837b'+rem+'01');conditional(g,(12,13),lambda c:c==13)
 g.take('488b43'+cur,'0fb630');update(g,offsets,1,'ebp');g.take('4080feff');conditional(g,(4,5),lambda c:(c==4)==null)
 allocation=None;context=None;array_call=None
 if null:
  g.take('488bcf','48c70700000000');g.call(s['barrier']);jump(g)
 else:
  g.take('4c89742430','48833f00');conditional(g,(4,5),lambda c:(c==4)==new)
  if new:
   site=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');nonzero(g)
   g.take('0f57c0','488bcf','0f114010','488907');g.call(s['barrier']);g.take('90');g.jump('e9')
   allocation=dict(site=site,cell=cell,zeroedHolderBytes=16)
  g.take('4080fe03');conditional(g,(4,5),lambda c:c==4)
  site=g.at;cell=g.relative('488b35');context=dict(site=site,cell=cell)
  g.take('488b2f','48837e3800');nonzero(g);g.take('488b5638','488bcb','488b12');array_call=g.at;g.call(s['array'])
  g.take('4885ed');nonzero(g);g.take('488d4d10','488901');g.call(s['barrier'])
  g.take('837b'+rem+'04','488b37');conditional(g,(12,13),lambda c:c==13)
  g.take('488b43'+cur,'448b30');update(g,offsets,4,'ebp');g.take('4885f6');nonzero(g);g.take('4489761c')
  g.take('837b'+rem+'04','488b3f');conditional(g,(12,13),lambda c:c==13)
  g.take('488b43'+cur,'8b28');update(g,offsets,4,'esi');g.take('4885ff');nonzero(g)
  g.take('4c8b742430','896f18')
 g.take('488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,nullWrapper=null,newWrapper=new,headerBytes=1,memberCount=None if null else 3,
  nativeWireOrder=[]if null else['keys.rawArray32','postWrapMode.raw4','preWrapMode.raw4'],
  wrapperAllocation=allocation,arrayMethodContext=context,arraySourceCallVa=array_call,normalFrameAndReturn=True,
  rawArrayGrammarAdmitted=False,ordinaryOriginalAdapterAdmitted=False,wholeOwnerAdmitted=False,
  condition='Initialized metadata, valid buffered disjoint input and wrapper output, normal compatible allocation/helpers and disabled barrier. FF clears the wrapper reference; Original value default conversion is a separate adapter obligation.')

def array32_program(regions,entry,offsets,s,*,count=1,copy_max_bytes=256):
 """Actual raw32 source; extended counts require a separate fresh copy proof."""
 need('copy256-count-bound',type(count)is int and type(copy_max_bytes)is int and
  0<=copy_max_bytes<=320000 and -1<=count<=min(10000,copy_max_bytes//32))
 g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('48895c2410','48896c2418','4889742420','57','4883ec20','48837a3800','488bf2','488bd9');nonzero(g)
 g.take('837b'+rem+'04');conditional(g,(12,13),lambda c:c==13);g.take('488b43'+cur,'8b38');update(g,offsets,4,'ebp')
 g.take('486343'+used,'488b53'+total,'482bd0','4863c7','483bd0');conditional(g,(12,13),lambda c:c==13)
 g.take('83ffff');conditional(g,(4,5),lambda c:(c==4)==(count==-1))
 if count==-1:g.take('33c0');g.jump('eb',1)
 else:
  g.take('85ff');conditional(g,(4,5),lambda c:(c==5)==(count>0))
  if count==0:
   g.take('488b4e38','488b09');g.call(s['empty']);g.jump('eb',1)
  else:
   g.take('4c89742430','448bf7','41c1e605','443b73'+rem);conditional(g,(14,15),lambda c:c==14)
   g.take('488b4638','488b6808','48837d3800');nonzero(g)
   g.take('488b4d38','33d2');g.call(s['context']);g.take('488bd7','488bc8');g.call(s['arrayAllocate'])
   g.take('488b5638','488bc8','488be8','488b5210');g.call(s['dataReference'])
   g.take('488b53'+cur,'488bc8','458bc6');g.call(s['copy']);g.take('4585f6');conditional(g,(4,5),lambda c:c==5)
   g.take('8b7b'+rem,'412bfe');conditional(g,(8,9),lambda c:c==9)
   g.take('440173'+adv,'4963c6','480143'+cur,'440173'+used,'897b'+rem,'4c8b742430','488bc5')
 g.take('488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,countWitness=count,headerBytes=4,elementBytes=32,payloadBytes=max(0,count)*32,
  allocationCountPassedUnchanged=count>0,byteCount='actual shl R14D,5 from EDI count; no overflow under1..8'if copy_max_bytes==256 else
   'actual shl R14D,5 from EDI count; positive count domain/no-overflow and actual copy bound independently required',
  output='same typed newly allocated array or typed Empty result, null for count-1',normalFrameAndReturn=True,
  childElementHeaders=False,rawValueFieldsAdmitted=False,
  condition='Current typed closed DangerousReadUnmanagedArray context, stable sufficient buffered input, actualtyped empty/allocation/data-reference helpers and copy256 component independently proved. Larger counts, refill, malformed and live inflation remain unresolved.'if copy_max_bytes==256 else
   'Current typed closed DangerousReadUnmanagedArray context, stable sufficient buffered input, actual typed empty/allocation/data-reference helpers and complete actual copy component independently proved. EDI*32, counter additions and current pointer remain nonwrapping throughout the separately proved finite count domain; refill, malformed and live inflation remain unresolved.')

def empty_array_program(regions,entry,indexed):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','4883793800','488bd9');nonzero(g)
 g.take('488b4b38','33d2');g.call(indexed);g.take('83b8e000000000');nonzero(g)
 g.take('488b4b38','33d2');g.call(indexed);g.take('488b80b8000000','488b00','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,contextClassSlot=0,returnedValue='sole typed static EmptyArray element-array reference',normalFrameAndReturn=True)

def getter_program(regions,entry):
 g=BytesPath(regions,entry);g.take('0f104210','488bc1','0f1101','c3')
 return dict(selectedBytes=g.seen,sourceHolderOffset=16,outputBytes=16,hiddenOutputRegister='rcx',wrapperRegister='rdx',sameOutputReturnedInRax=True)

def default_program(regions,entry):
 g=BytesPath(regions,entry);g.take('0f57c0','0f114110','c3')
 return dict(selectedBytes=g.seen,holderOffset=16,zeroedBytes=16,ordinaryReturn=True)

def derive(image,pins,*,count_limit=8):
 """Fresh concrete-wrapper source capability; Original adapter stays closed."""
 import hashlib,json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_action_sources as actions,generated_member_sources as members,generated_lifecycle_sources as lifecycle
 from scripts.game_data.memorypack import pointer_param,primitive_param,scalar_param_native as scalar,skill_gameplay_tag_array_sources as arrays
 from scripts.game_data.memorypack.skill_unmanaged_array_context import derive as array_context
 from scripts.game_data.memory_copy_bounded_native import validate_components as copy_source
 _publication_gate(image,pins);need('finite-copy-bound',type(count_limit)is int and 0<=count_limit<=10000)
 ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type=='Beyond.FAnimationCurve'];mm=pointer_param.methods(image,wrapper)
 need('exact-current-declaration',[(m.name,m.declared_type)for m in wrapper.members]==[('keys','Beyond.FKeyframe[]'),('postWrapMode','UnityEngine.WrapMode'),('preWrapMode','UnityEngine.WrapMode')])
 native_types={}
 declarations={
  'Beyond.FKeyframe':[('time','float',16),('value','float',20),('inTangent','float',24),('outTangent','float',28),('tangentMode','int',32),('weightedMode','int',36),('inWeight','float',40),('outWeight','float',44)],
  'Beyond.FAnimationCurve':[('keys','Beyond.FKeyframe[]',16),('preWrapMode','UnityEngine.WrapMode',24),('postWrapMode','UnityEngine.WrapMode',28)]}
 for name,expected in declarations.items():
  td=ctx.index.types[name];need('current-nongeneric-value',ctx.is_value_type(name)and td.generic_container_index<0)
  fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
  actual=[(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in fields];need('exact-current-stored-fields',actual==expected,actual)
  for f in fields:
   kind={'float':12,'int':8,'Beyond.FKeyframe[]':29,'UnityEngine.WrapMode':17}[ctx.type_name(f.type_index)]
   scalar.ordinary(image,ctx.type_pointer(f.type_index),kind,LABEL+'.storedField',reference=kind==29)
  need('bounded-size-index',0<=td.index<image.registration['typeDefinitionsSizesCount']);p=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);width=32 if name=='Beyond.FKeyframe'else 16
  need('current-layout-sizes',(image.pe.u32_at_va(p),image.pe.u32_at_va(p+4))==(16+width,width))
  native_types[name]=dict(typeDefinition=td.index,fields=actual,managedBytes=width)
 enum=ctx.index.types['UnityEngine.WrapMode'];backing,=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
 need('owned-wrap-enum-int32',ctx.is_enum('UnityEngine.WrapMode')and md.string(backing.name_index)=='value__'and ctx.type_name(backing.type_index)=='int');scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,LABEL+'.wrapBacking')
 field=ctx.field(wrapper.name+'::__instance');need('current-wrapper-value-holder',field==(wrapper.name,'Beyond.FAnimationCurve',16))
 reader=mm['Deserialize'];primitive_param.reader_abi(image,ctx,reader,wrapper);body=members._body(image,image.method_pointer_va(reader));contexts,skipped=actions._contexts(image,body['rows']);context,=[c for c in contexts if c['fullTypeName']=='Beyond.FKeyframe']
 usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.array');typed=array_context(image,usage,element_type='Beyond.FKeyframe')
 # Select only the actual public->Dangerous method-context transfer in this
 # current caller. No registration/physical-body equivalence is asserted.
 calls=[members.control_transfer(r)['target']for i,r in enumerate(body['rows'])if i and members.ec.raw(r)[:1]==b'\xe8'and body['rows'][i-1]['text']=='mov rdx, [rdx]'];need('one-actual-array-call',len(calls)==1)
 barrier_calls=[members.control_transfer(r)['target']for i,r in enumerate(body['rows'])if i and members.ec.raw(r)[:1]==b'\xe8'and body['rows'][i-1]['text']=='mov [rcx], rax'];need('one-actual-field-barrier',len(set(barrier_calls))==1);barrier=barrier_calls[0]
 allocate=[members.control_transfer(r)['target']for i,r in enumerate(body['rows'])if i and members.ec.raw(r)[:1]==b'\xe8'and members.ec.raw(body['rows'][i-1])[:3]==bytes.fromhex('488b0d')];need('one-current-wrapper-allocator',len(set(allocate))==1)
 offsets=scalar.reader_offsets(image,LABEL);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 symbols=dict(array=calls[0],barrier=barrier,allocate=allocate[0]);programs=[curve_program(body['regions'],body['pointer'],offsets,symbols,null=n,new=w)for n,w in((False,False),(False,True),(True,False),(True,True))]
 allocations=[]
 for program in programs:
  need('actual-array-context-in-program',program['arrayMethodContext']is None or program['arrayMethodContext']['site']==base+context['instructionRva'])
  if program['wrapperAllocation']is not None:
   allocation=derive_typed_usage_context(image,program['wrapperAllocation']['site']-base,label=LABEL+'.wrapperAllocation');need('exact-allocated-wrapper',(allocation['tag'],allocation['typeName'])==(1,wrapper.name));allocations.append(allocation)
 array=members._body(image,calls[0])
 def actual_after(hex_prefix):
  chosen=[members.control_transfer(r)['target']for i,r in enumerate(array['rows'])if i and members.ec.raw(r)[:1]==b'\xe8'and members.ec.raw(array['rows'][i-1]).hex()==hex_prefix]
  need('one-actual-helper.'+hex_prefix,len(set(chosen))==1);return chosen[0]
 array_symbols=dict(context=actual_after('33d2'),arrayAllocate=actual_after('488bc8'),dataReference=actual_after('488b5210'),copy=actual_after('458bc6'),empty=actual_after('488b09'))
 extended=count_limit>8;copy_bound=32*count_limit if extended else 256
 witnesses=[-1,0,1,count_limit]if extended else range(-1,count_limit+1)
 array_programs=[array32_program(array['regions'],array['pointer'],offsets,array_symbols,count=n,copy_max_bytes=copy_bound)for n in witnesses]
 empty=members._body(image,array_symbols['empty']);empty_program=empty_array_program(empty['regions'],empty['pointer'],array_symbols['context'])
 data=members._body(image,array_symbols['dataReference']);data_program=arrays.data_reference_program(data['regions'],data['pointer'])
 indexed=lifecycle._initialized_indexer(image,array_symbols['context'])
 count_domain=None
 if extended:
  from scripts.game_data.il2cpp.forward_copy_sources import derive as derive_copy
  from scripts.game_data.memorypack.beyond_curve_count_domain import prove as prove_count
  copy=derive_copy(image,pins,entry=array_symbols['copy'],max_bytes=copy_bound)
  need('fresh-actual-copy-source',copy['nativeInputs']==pins and copy['entryRva']==array_symbols['copy']-base and
   copy['status']=='proved-conditional-forward-copy'and copy['maxBytes']==copy_bound)
  count_domain=prove_count(count_limit=count_limit,copy_max_bytes=copy['maxBytes'])
  need('same-complete-positive-source-trace',array_programs[2]['selectedBytes']==array_programs[3]['selectedBytes'])
  count_domain=dict(count_domain,sourceProgramAdmitted=True,copyProgramAdmitted=True,
   actualArraySourceRva=array['pointer']-base,actualCopyTargetRva=array_symbols['copy']-base,
   allPositiveCountsUseSameCompleteSourceProgram=True)
 else:
  copy_fact=json.loads((CONTRACTS_DIR/'memory_copy_bounded_native.json').read_bytes());need('same-current-copy-inputs',copy_fact['nativeInputs']==pins);need('same-actual-copy-entry',base+copy_fact['entryRva']==array_symbols['copy']);copy=copy_source(image,copy_fact);need('adequate-native-copy-bound',copy['maxBytes']>=32*count_limit)
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 collector=_barrier(image,barrier)
 getters=[]
 for role in('.ctor','CreateInstance','GetValue'):
  method=mm[role];return_abi=('Beyond.FAnimationCurve',17,False)if role=='GetValue'else('void',1,False)
  scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,return_abi,[],LABEL+'.'+role)
  entry=image.method_pointer_va(method);raw=image.pe.bytes_at_va(entry,128);program=(getter_program if role=='GetValue'else default_program)([(entry,raw)],entry)
  size=max(a+len(bytes.fromhex(h))for a,h in program['selectedBytes'])-entry
  getters.append(dict(method=lifecycle._method_row(image,method),program=program,reachableWindow=dict(startRva=entry-base,endRva=entry-base+size,sha256=hashlib.sha256(raw[:size]).hexdigest().upper()),physicalExtentProved=False))
 formatter=lifecycle._concrete_formatter(image,ctx,wrapper,reader)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(status='validated-conditional-beyond-curve-wrapper',nativeInputs=pins,wrapperName=wrapper.name,typeName=wrapper.wrapped_type,
  wrapperWireGrammarAdmitted=True,ordinaryOriginalAdapterAdmitted=False,positiveKeyCountLimit=count_limit,wholeOwnerAdmitted=False,
  proof=dict(types=native_types,method=lifecycle._method_row(image,reader),family=body['family'],codeWindows=body['windows'],programs=programs,wrapperAllocations=allocations,
   typedArrayRequest=usage,arrayContext=typed,arrayFamily=array['family'],arrayWindows=array['windows'],arrayPrograms=array_programs,registeredArrayBodyEquivalenceClaimed=False,
   emptyArray=dict(family=empty['family'],windows=empty['windows'],program=empty_program),dataReference=dict(family=data['family'],windows=data['windows'],program=data_program),
   initializedClass=indexed,copy=copy,collector=collector,wrapperValueMethods=getters,concreteFormatter=formatter,skippedRuntimeCells=skipped,
   **(dict(countDomain=count_domain)if extended else{})),
  evidenceBoundary=dict(exact='Current concrete FAnimationCurve wrapper MC3/FF/new/existing source plus typed raw FKeyframe array32 and signed -1/0/count1..bounded copy paths, wrap enum ownership and exact field order.',
   conditional=__doc__+' Ready coherent selected MethodInfos, normal matching typed allocations and static EmptyArray, readable disjoint sufficient buffered storage, ordinary ABI helper effects and disabled collector.',
   structuralOnly='Stored FKeyframe fields in physical raw-array order; no curve evaluation.',unresolved=['Original value adapter/provider/GetValue invocation join','counts above current copy bound','cold/refill/error paths','whole owner/EOF','live curve meaning']))))
