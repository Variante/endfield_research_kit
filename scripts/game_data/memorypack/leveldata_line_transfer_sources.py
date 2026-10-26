"""Exact Line hidden12 conversion and compared callback, without list admission.

The Line wrapper owns its MC2 wire grammar and hidden12 GetValue independently.
This source owns only the current Line/object canonical adapter, the actual
list callback's exact comparison to it, FF/default zero12, wrapper creation or
reuse, interface lookup and complete unchanged hidden12 copy. Runtime formatter
selection, initialized compatible contexts, normal helpers and stable disjoint
buffer/frame/output storage remain conditions. A managed size is no wire codec.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.leveldata_line_value_sources import TYPE


def need(key,value):
 if not value:raise ValueError('storyLineTransfer.'+key)


def adapter_program(regions,entry,s,*,dispatch=False,null=False,create=True):
 need('literal-path',all(type(v)is bool for v in(dispatch,null,create)))
 g=BytesPath(regions,entry)
 if dispatch:
  g.take('48895c2410','4889742418','48897c2420','66894c2408','4156','4883ec20',
   '488b0a','4d8bf1','498bf0','488bda');g.call(s['prepare'])
  g.take('488b03','4c8b9090010000','488bb898010000');need('exact-compared-Line-adapter',g.relative('488d05')==s['adapter'])
  g.take('4c3bd0');g.branch('0f85',False);ready=flag(g);g.branch('0f84',False)
 else:
  g.take('4889742418','48897c2420','4156','4883ec20');ready=flag(g)
  g.take('498bf9','4d8bf0','488bf2');g.branch('0f84',False)
 g.take('488bce','c64424'+('30'if dispatch else'38')+'00');g.call(s['peek'])
 g.take('84c0');g.branch('0f85',null);type_cell=None
 if null:
  g.take('488d5424'+('30'if dispatch else'38'),'488bce');g.call(s['header'])
  g.take('33c0','498906','41894608');g.jump('e9')
 else:
  if not dispatch:g.take('48895c2430')
  g.take('488b4720');type_cell=g.relative('488b0d')
  g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('0f84',False)
  g.take('33d2','488bcb');g.call(s['typeHandle'])
  if not dispatch:g.take('488b5c2430')
  g.take('4885c0');g.branch('74',False,1)
  g.take('b944000000','488bd0');g.call(s['creationTest']);g.take('a980000000');g.branch('77',not create,1)
  if create:
   g.take('488b4720','488b88c0000000','488b4958');g.call(s['activate'])
  else:g.take('33c0');g.jump('eb',1)
  g.take('488b4f20','4c8bc0','498bd6','4c8b89c0000000','488bce','4d8b4918');g.call(s['nonnull'])
 if dispatch:g.take('488b5c2438')
 g.take('488b742440','488b7c2448','4883c420','415e','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,typeClassCell=type_cell,dispatch=dispatch,
  ff=null,createWrapper=None if null else create,managedBytes=12,defaultZeroBytes=12 if null else 0,
  wrapperTypeContextSlot=10,activatorContextSlot=11,nonnullContextSlot=3,
  sameIncomingReaderAndHiddenOutput=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
  selectorUsed=False if dispatch else None,normalReturn=True,
  frame=dict(entryRspDelta=-40,callShadow=[0,32],pushedNonvolatiles=['r14'],
   savedEntryHomes=dict(rsi=[24,32],rdi=[32,40],**({'rbx':[16,24]}if dispatch else{'conditionalRbx':[8,16]}))))


def nonnull_program(regions,entry,s,*,wrapper_null=False):
 need('literal-wrapper-null',type(wrapper_null)is bool)
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','4c89442418','57','4883ec30');ready=flag(g)
 g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
 provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
 g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
 g.take('4885c0');g.branch('0f84',False)
 g.take('b905000000','4c8d4c2450','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
 g.take('488b5c2450','4885db');g.branch('0f84',wrapper_null)
 if wrapper_null:
  g.take('33c0','488906','894608');g.jump('e9')
 else:
  g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
  g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion'])
  g.take('f20f1000','8b4808','f20f1106','894e08')
 g.take('488b5c2440','488b742448','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,wrapperNull=wrapper_null,
  managedBytes=12,defaultZeroBytes=12 if wrapper_null else 0,copiedSourceSlices=[]if wrapper_null else[[0,8],[8,4]],
  wrapperOutputHomeFromFrame=[80,88],conversionOutputLocal=[32,44],referenceLaneOffsets=[],
  wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,sameIncomingReaderAndHiddenOutput=True,
  normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
  frame=dict(entryRspDelta=-56,callShadow=[0,32],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24],wrapperLocal=[24,32]),pushedNonvolatiles=['rdi']))


def conversion_program(regions,entry,prepare,*,ordinal):
 need('literal-bounded-interface-ordinal',type(ordinal)is int and 0<=ordinal<=16)
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','48897c2418','4156','4883ec30','498b39','488bf1','488bcf','4d8bf1','498bd8');g.call(prepare)
 g.take('440fb78730010000','33c0','66413bc0');g.branch('73',False,1);g.take('488b97b0000000')
 for index in range(ordinal+1):
  g.take('0fb7c8','4803c9','48391cca');g.branch('74',index==ordinal,1)
  if index<ordinal:g.take('66ffc0','66413bc0');g.branch('72',True,1)
 g.take('0fb7c8','4803c9','486344ca08','4883c014','48c1e004','4803c7',
  '4c8b08','488d4c2420','4c8b4008','498bd6');getter=g.at;g.take('41ffd1',
  '488b5c2440','488b7c2450','f20f1000','8b4008','f20f1106','894608','488bc6',
  '488b742448','4883c430','415e','c3')
 return dict(selectedBytes=g.seen,interfaceOrdinal=ordinal,methodSlot=0,hiddenGetterCall=getter,
  getterArguments=dict(rcx='local output12',rdx='own returned wrapper',r8='own GetValue MethodInfo'),
  copiedSourceSlices=[[0,8],[8,4]],managedBytes=12,referenceLaneOffsets=[],sameOutputReturnedInRax=True,
  getterReturnsSameLocalOutputRequired=True,normalReturn=True,entryRspRestored=True,
  frame=dict(entryRspDelta=-56,callShadow=[0,32],getterOutputLocal=[32,44],savedEntryHomes=dict(rbx=[8,16],rsi=[16,24],rdi=[24,32]),pushedNonvolatiles=['r14']))


def derive(image,pins):
 """Fresh own wrapper, canonical pair and actual list callback comparison."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources as bp,primitive_param,event_args_paths,scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_line_value_sources import derive_record
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
 record=derive_record(image,pins);wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 pair=record['pair'];face,=pair['composition']['interfaces'];wrapper_td=md.types[wrapper.type_definition]
 section=md.sections['interfaceOffsets'];at=section.offset+wrapper_td.interface_offsets_start*8
 ordinal=list(struct.iter_unpack('<ii',md.buf[at:at+wrapper_td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
 context,context_proof=bp._adapter_context(image,ge);sources={};registrations={};s={}
 for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
  method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
  registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
 list_method=bp._definition(image,'MemoryPack.Formatters.ListFormatter`1','Deserialize')
 listing=ge.resolve(list_method.index,[TYPE],[]);sources['list']=pointer.owned(image,listing['pointer'])
 def call(body,offset):
  site=body['pointer']+offset;row,=[r for r in body['rows']if int(r['va'],16)==site];raw=bytes.fromhex(row['bytes'])
  need('actual-owned-E8:'+str(offset),len(raw)==5 and raw[0]==0xe8)
  return site+5+int.from_bytes(raw[1:],'little',signed=True)
 s['dispatch']=call(sources['list'],303);sources['dispatch']=pointer.owned(image,s['dispatch']);s['prepare']=call(sources['dispatch'],38)
 for role,offset in dict(peek=46,typeHandle=104,creationTest=127,activate=154,nonnull=183).items():
  target=call(sources['adapter'],offset)
  if role in s:need('same-own-target:'+role,s[role]==target)
  s[role]=target
 ff=BytesPath(sources['adapter']['regions'],s['adapter']+53).relative('0f85')
 s['header']=BytesPath(sources['adapter']['regions'],ff+8).relative('e8')
 for role,offset in dict(resolve=66,wrapperProvider=82,wrapperInvoke=112,indexed=152,conversion=168).items():s[role]=call(sources['nonnull'],offset)
 need('same-context-resolver',s['resolve']==call(sources['nonnull'],135))
 for role in('conversion','wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,s[role])
 need('same-interface-prepare',s['prepare']==call(sources['conversion'],36))
 paths={role:[adapter_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**options)
  for options in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
 paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,wrapper_null=n)for n in(False,True)]
 paths['conversion']=conversion_program(sources['conversion']['regions'],s['conversion'],s['prepare'],ordinal=ordinal)
 need('same-owned-type-handle',s['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
 need('same-ready-adapter-flag',paths['adapter'][0]['metadataReadyFlag']==paths['dispatch'][0]['metadataReadyFlag'])
 invocation=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],
  callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
 offsets=scalar.reader_offsets(image,'storyLineTransfer');peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
 header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-line-value-transfer.v1',status='validated-conditional-line-value12-transfer',
  nativeInputs=pins,typeName=TYPE,managedBytes=12,referenceLaneOffsets=[],paddingByteRanges=[],record=record,
  proof=dict(adapterContext=context,adapterContextProof=context_proof,registrations=registrations,listRegistration=listing,
   interfaceOrdinal=ordinal,paths=paths,wrapperInvocation=invocation,peek=peek,header=header,
   symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()}),
  canonicalOriginalAdapterAdmitted=True,canonicalFFDefaultManagedBytes=12,positiveCollectionAdmitted=False,
  actualSelectedCallbackEqualsCanonicalRequired=True,closedWrapperPointerEqualityInferred=False,
  liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own Line managed12 MC2 wrapper, full hidden12 getter, exact Line/object canonical entry, actual List callback comparison, FF/default zero12 and creation/reuse/wrapper-null/interface/unchanged12 copy with complete selected frames.',
   conditional=__doc__,unresolved=['positive collection count/constructor/Add induction and actual enclosing parent','refill/malformed/active initialization paths','runtime selection or behavior','whole owner physical EOF/publication']))))
