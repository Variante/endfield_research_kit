"""Own Line's value12 wrapper and inline Int2 bytes; list/adapter stay separate."""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.Line'
VECTOR='UnityEngine.Vector2Int'


def record_program(regions,entry,symbols,offsets,*,null=False,new=False):
 if type(null)is not bool or type(new)is not bool or null and new:raise ValueError('storyLine.literal-wrapper-path')
 if (set(offsets)!= {'currentPtr','bufferLength','advancedCount','consumed'}
  or any(type(n)is not int or not 0<=n<128 for n in offsets.values())or len(set(offsets.values()))!=4):
  raise ValueError('storyLine.exact-reader-field-map')
 cur,rem,adv,used=(bytes([offsets[k]]).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
 g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
 g.take('488bda','488bf9');g.branch('0f84',False)
 g.take('837f'+rem+'01');g.branch('0f8c',False)
 g.take('488b47'+cur,'0fb630','8b6f'+rem,'83ed01');g.branch('0f88',False)
 g.take('48ff47'+cur,'ff47'+adv,'ff47'+used,'896f'+rem,'4080feff');g.branch('74',null,1)
 allocation=None;integer_call=None;int2_start=None;int2_end=None
 if null:
  g.take('488bcb','48c70300000000');g.call(symbols['barrier']);g.jump('eb',1)
 else:
  g.take('48833b00');g.branch('0f84',new)
  if new:
   allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(symbols['allocate'])
   g.take('4885c0');g.branch('0f84',False)
   g.take('33c9','48894810','894818','488bcb','488903');g.call(symbols['barrier']);g.take('90');g.jump('e9')
  g.take('4080fe02');g.branch('0f85',False)
  g.take('488b33','488bcf');integer_call=g.at;g.call(symbols['integer'])
  g.take('4885f6');g.branch('74',False,1);g.take('894618')
  int2_start=g.at
  g.take('837f'+rem+'08','488b33');g.branch('0f8c',False)
  g.take('488b5f'+cur,'488b1b','8b6f'+rem,'83c5f8');g.branch('0f88',False)
  g.take('488347'+cur+'08','8347'+adv+'08','8347'+used+'08','896f'+rem,'4885f6');g.branch('74',False,1)
  g.take('48895e10');int2_end=g.at
 g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,wrapperNull=null,newWrapper=None if null else new,
  typedAllocation=allocation,integerSourceCall=integer_call,inlineInt2SourceRange=None if null else[int2_start,int2_end],
  inlineInt2SourceMethodSpecPresent=False,inlineInt2CapturedRegister=None if null else'rbx',
  integerWrapperFieldOffset=None if null else 24,int2WrapperFieldOffset=None if null else 16,
  newWrapperZeroedBytes=12 if new else 0,wrapperReferenceClearedBytes=8 if null else 0,
  outputBytes=8,wrapperHeaderBytes=1,positiveWireBytes=13,referenceLaneOffsets=[],
  rawInt32Axes=['x','y'],fullFieldCopyBytes=[]if null else[4,8],normalReturn=True,entryRspRestored=True,
  frame=dict(entryRspDelta=-40,callShadow=[0,32],savedEntryHomes=dict(rbx=[8,16],rbp=[16,24],rsi=[24,32]),pushedNonvolatiles=['rdi']),
  canonicalOriginalAdapterAdmitted=False,containerAdmitted=False,
  condition='Initialized ready metadata and sufficient contiguous buffered input, disjoint current Reader/wrapper/output/stack storage, compatible nonnull wrapper after allocation/reuse, normal current Int32 source/typed allocation and selected disabled-barrier effects. Inline Int2 bits are captured and fully stored without a typed frontdoor or floating interpretation.')


def derive_record(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_integer_vector_layout import derive_layout
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 need=lambda k,e,a:scalar.need('storyLine',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 need('exact-wrapper-order',[('length','int'),('startPos',VECTOR)],[(m.name,m.declared_type)for m in wrapper.members])
 td=ctx.index.types[TYPE];scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,'storyLine.nominalValue')
 need('owned-nongeneric-nonenum-value',(True,False,'System.ValueType',-1),(ctx.is_value_type(TYPE),ctx.is_enum(TYPE),ctx.parent(TYPE),td.generic_container_index))
 fields=[];vector=None
 for field in md.fields_for(td):
  if ctx.field_attributes(field.type_index)&16:continue
  name=md.string(field.name_index);actual=ctx.field(TYPE+'::'+name);fields.append(list(actual))
  if name=='startPos':vector=derive_layout(image,type_pointer=ctx.type_pointer(field.type_index))
  else:scalar.ordinary(image,ctx.type_pointer(field.type_index),8,'storyLine.length')
 need('complete-owned-layout',[[TYPE,VECTOR,16],[TYPE,'int',24]],sorted(fields,key=lambda f:f[2]))
 need('independent-nominal-Int2',(VECTOR,8,[],[]),(vector['typeName'],vector['managedBytes'],vector['referenceLaneOffsets'],vector['paddingByteRanges']))
 need('inline-wrapper-holder',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
 need('bounded-size-slot',True,0<=td.index<image.registration['typeDefinitionsSizesCount'])
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 need('owned-boxed-size28',28,image.pe.u32_at_va(size))
 methods=pointer.methods(image,wrapper);reader=methods['Deserialize'];primitive_param.reader_abi(image,ctx,reader,wrapper)
 body=pointer.owned(image,image.method_pointer_va(reader))
 def direct(offset):
  at=body['pointer']+offset;raw=image.pe.bytes_at_va(at,5);need('exact-E8-site:'+str(offset),0xe8,raw[0])
  return at+5+int.from_bytes(raw[1:],'little',signed=True)
 # Source-relative sites are fixed by the complete exact program, never RVAs.
 symbols=dict(integer=direct(113),barrier=direct(214))
 cold=[r for r in body['rows']if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d']
 need('one-owned-allocation-context',True,bool(cold));allocation_row=cold[0]
 allocation_at=int(allocation_row['va'],16);allocate_raw=image.pe.bytes_at_va(allocation_at+7,5)
 need('allocation-context-then-E8',0xe8,allocate_raw[0]);symbols['allocate']=allocation_at+12+int.from_bytes(allocate_raw[1:],'little',signed=True)
 offsets=scalar.reader_offsets(image,'storyLine')
 programs=[record_program(body['regions'],body['pointer'],symbols,offsets,**mode)for mode in(dict(null=True),dict(new=True),dict())]
 allocation=programs[1]['typedAllocation'];usage=derive_typed_usage_context(image,allocation['instruction']-base,label='storyLine.allocation')
 need('actual-wrapper-allocation',(1,wrapper.name),(usage['tag'],usage['typeName']))
 getter=methods['GetValue'];scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(TYPE,17,False),[],'storyLine.getter')
 get=pointer.leaf(image,image.method_pointer_va(getter),['8B4218','F20F104210','F20F1101','894108','488BC1','C3'])
 constructors={}
 for name in('.ctor','CreateInstance'):
  method=methods[name];scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[],'storyLine.'+name)
  constructors[name]=pointer.leaf(image,image.method_pointer_va(method),['33C0','48894110','894118','C3'])
 pair=derive_pair(image,TYPE,wrapper.name);registered=pointer.registered_pair(image,pair,wrapper,label='storyLine.registeredPair')
 integer=vector_recorder(image)(symbols['integer']-base);scalar.integer_source(image,integer,offsets,'storyLine.Int32',width=4)
 barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-line-value-wrapper.v1',status='validated-current-line-wrapper-source',nativeInputs=pins,
  typeName=TYPE,wrapperName=wrapper.name,managedBytes=12,referenceLaneOffsets=[],paddingByteRanges=[],fields=fields,vectorLayout=vector,
  sourceWindows=body['windows'],programs=programs,getter=get,constructors=constructors,pair=pair,registration=registered,
  readerMethod=[reader.index,wrapper.name,'Deserialize',body['pointer']-base],typedAllocation=usage,integerSource=integer,
  barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={k:v-base for k,v in symbols.items()},boxedAndNativeSizes=[image.pe.u32_at_va(size),image.pe.u32_at_va(size+4)],
  canonicalOriginalAdapterAdmitted=False,containerAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own Line managed12 fields, separately nominal Int2 layout/getters, complete buffered MC2/FF/new/reused wrapper programs, inline8 capture/Reader updates/unchanged field store, current Int32 helper, zero12 constructor and whole hidden12 getter plus own registered concrete formatter.',
   conditional='Initialized coherent nominal metadata/context, exact callbacks, normal allocation/barrier/helper effects and sufficient stable contiguous disjoint buffered storage. No refill/active collector behavior or runtime invocation observed.',
   unresolved=['canonical original hidden12 adapter/default/interface/copy transfer','List<Line> count/provider/constructor/Add/callback','enclosing grid/area/host parents','whole owner physical EOF/publication']))))
