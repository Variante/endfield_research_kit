"""Exact current managed16 LangKey list witnesses; positive admission is bounded."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def list_program(regions,entry,s,*,count,new=True):
 if type(count)is not int or count not in (-1,0,1) or type(new)is not bool:raise ValueError('langKeyList.selected-profile')
 g=BytesPath(regions,entry);g.take('4053','57','4154','4156','4883ec58');g.relative('803d');g.take('00','498bd9','498bf8','4c8be2');g.branch('75',True,1)
 g.take('0f57c0','488d942488000000','4533f6','498bcc','4489b42488000000','0f11442420');g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
 if count==-1:
  g.take('488bcf','4c8937');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889ac2480000000','4889b42490000000','4c897c2450','0f29742440','8bac2488000000','4c3937');g.branch('0f85',not new)
  if new:
   g.take('488b4b20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('75',True,1);g.take('488b4b20','488b91c0000000','488b4a08','4c397120');g.branch('0f84',False);g.take('488b4320','8bd5','488bce','4c8b80c0000000','4d8b4008');g.call(s['constructor']);g.take('488bcf','488937');g.call(s['barrier'])
  else:
   g.take('488b4320','488b37','488b90c0000000','488b4210','4c397020');g.branch('75',True,1);g.take('488b4320','488bce','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
  provider_owner=g.relative('488b0d');g.take('4439b1e0000000');g.branch('75',True,1);g.take('488b4320','488b88c0000000','488b4918');g.call(s['provider']);g.take('488bf0','85ed');g.branch('7e',count==0,1)
  if count:
   g.take('0f57c0','0f11442420','4885f6');g.branch('74',False,1);g.take('4c8d4c2420','4d8bc4','488bd6');g.call(s['dispatch']);g.take('4c8b3f','0f28742420','4d85ff');g.branch('0f84',False);g.take('488b4320','488b88c0000000','488b4130','4883782000');g.branch('0f84',False);g.take('488b4320','488d542430','498bcf','660f7f742430','4c8b80c0000000','4d8b4030');g.call(s['add']);g.take('41ffc6','443bf5');g.branch('7c',False,1)
  g.take('4c8b7c2450','488bb42490000000','0f28742440','488bac2480000000')
 g.take('4883c458','415e','415c','5f','5b','c3')
 return dict(selectedBytes=g.seen,count=count,newList=new,elementRuntimeBytes=16,wireHeaderBytes=4,elementCallbacks=int(count==1),providerOwnerCell=None if count==-1 else provider_owner,elementOutput='zeroed sixteen-byte local at RSP+32 passed via R9',elementTransfer='exact XMM16 through aligned separate RSP+48 to Add',reader='incoming RDX retained R12',output='incoming R8 retained RDI',normalFrameAndReturn=True,boundary='Only null/zero/one-element witnesses. Positive child wire grammar and typed adapter/provider selection independently gated. Existing list requires count0 and sufficient capacity; new allocation/constructor effects and coherent initialized contexts remain explicit conditions. No growth or general loop invariant.')



def capacity_program(regions,entry,s,*,positive=True):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False);g.take('498b4820','488b89c0000000');g.branch('0f84',not positive)
 if positive:g.take('ba01000000');g.call(s['context']);g.take('8bd3','488bc8');g.call(s['arrayAllocate'])
 else:
  g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('75',True,1);g.take('488b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01');g.jump('e9')
 g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError('langKeyList.capacity-barrier')
 return dict(selectedBytes=g.seen,positiveCapacity=positive,normalReturnViaBarrier=True,arrayContextSlot=1,itemsSlot=16,countWrites=0,versionWrites=0,capacityBits=32,boundary='Normal initialized indexed class resolver and typed array allocation; fresh zeroed List with capacity1, or ready static typed empty array for zero. No allocation or runtime initialization observation.')


def clear_program(regions,entry,*,canonical=False):
 g=BytesPath(regions,entry)
 if not canonical:g.take('4883ec28')
 g.take('448b4118','ff411c','c7411800000000','4585c0');g.branch('7e' if canonical else '0f8f',canonical,1 if canonical else 4)
 if not canonical:g.take('4883c428')
 g.take('c3');return dict(selectedBytes=g.seen,initialCount=0,countSlot=24,versionSlot=28,itemsUnchanged=True,normalReturn=True)


def add_program(regions,entry,s,*,canonical=False):
 g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec30','ff411c','488bd9','4c8b4910','498bf8','48634918','488bf2','4d85c9');g.branch('75' if canonical else '0f84',canonical,1 if canonical else 4);g.take('413b4918');g.branch('72' if canonical else '73',canonical,1)
 if canonical:g.take('0f1002','8d4101','488bd1','4c8d442420','894318','498bc9','f30f7f442420');g.call(s['arrayStore'])
 else:g.take('8d4101','894318','413b4918');g.branch('0f83',False);g.take('0f1002','488d4102','4883c102','4803c0','48c1e104','4903c9','410f1104c1')
 g.take('488b5c2440','488b742448','4883c430','5f')
 if canonical:g.take('c3')
 elif g.relative('e9')!=s['barrier']:raise ValueError('langKeyList.add-barrier')
 return dict(selectedBytes=g.seen,initialCount=0,spareCapacity=1,elementBytes=16,arrayDataOffset=32,arrayStride=16,countSlot=24,versionSlot=28,normalReturn=True,actualInlineStore=not canonical,boundary='Typed existing array with capacity>=1 and count0, or fresh constructor capacity1; exact sixteen-byte input copied without reinterpretation. No growth path.')


def value_provider_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('0f84',False);type_class=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('0f84',False);g.take('488bcb');g.call(s['typeHandle']);g.take('488bd8');provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);flag=g.relative('803d');g.take('00');g.branch('0f84',False)
 if g.relative('488b0d')!=provider:raise ValueError('langKeyList.provider-class')
 g.take('83b9e000000000');g.branch('0f84',False);g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['context']);g.take('4885db');g.branch('0f84',False);g.take('488b0b','488bd0');g.call(s['assignable']);g.take('84c0');g.branch('0f84',False);g.take('488bc3','488b5c2438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,providerClassCell=provider,typeClassCell=type_class,readyFlag=flag,ownMethodParameterSlot=0,formatterClassSlot=1,backendResultUnchanged=True,normalReturn=True,boundary='Coherent ready typed own-MVAR context, TypeFromHandle result for LangKey, successful normal Type-key backend and assignability guard. No registered-body equivalence or runtime provider selection claim.')


def wrapper_provider_program(regions,entry,s):
 g=BytesPath(regions,entry);g.take('48895c2418','55','56','57','4154','4155','4156','4157','4883ec60','488be9','4883793800');g.branch('0f84',False);g.take('488b5d38','488b1b');type_class=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('0f84',False);g.take('b201','488bcb');g.call(s['classFromType']);g.take('4c8d6020');cache=g.relative('488b1d');g.take('488b8b80000000');enter=g.relative('ff15');g.take('90','488b4340','483b4338');g.branch('0f84',False);g.take('4533ed','4c8b7348','49ffce','498bcc');g.call(s['classHash']);g.take('488bf8','488b7368','448b7b50','4923fe','488d0c7f','443b3cce');g.branch('75',True,1);g.take('48837b3800');g.branch('0f87',False);g.take('488d047f','833cc600');g.branch('0f85',False);g.take('488b54c608','498bcc');g.call(s['classEquals']);g.take('85c0');g.branch('0f85',False);g.take('4883ffff');g.branch('0f84',False);g.take('488d0c7f','488d14ce','488b4348','488d0c40','488b4368','488d0cc8','483bd1');g.branch('0f84',False);g.take('488b4a10','488b4370','4c8b34c8','488b8b80000000');leave=g.relative('ff15');g.take('90');provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False);flag=g.relative('803d');g.take('00');g.branch('0f84',False)
 if g.relative('488b0d')!=provider:raise ValueError('langKeyList.wrapper-provider-class')
 g.take('83b9e000000000');g.branch('0f84',False);g.take('498bce');g.call(s['backend']);g.take('488bd8','ba01000000','488b4d38');g.call(s['context']);g.take('4885db');g.branch('74',False,1);g.take('488bd0','488b0b');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1);g.take('488bc3','488b9c24b0000000','4883c460','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,typeClassCell=type_class,providerClassCell=provider,readyFlag=flag,classKeyCacheCell=cache,enterCell=enter,leaveCell=leave,contextSlots=[0,1],backendResultUnchanged=True,normalReturn=True,boundary='Ready own wrapper MVAR context, normal ClassFromType returning wrapper class, selected readable first-probe raw slot predicates with matching typed class-key to System.Type mapping, stable cache and ordinary lock/hash/equality effects. Successful Type-key backend and assignable expected formatter. No live cache/registration/inflation/default selection claim.')


def inline_dispatch_program(regions,entry,s,*,null=False,create=True,wrapper_null=False,ordinal=1):
 if type(ordinal)is not int or not 0<=ordinal<=4:raise ValueError('langKeyList.interface-ordinal')
 g=BytesPath(regions,entry);g.take('66894c2408','53','55','56','57','4883ec38','488b0a','498bf9','498bf0','488bda');g.call(s['prepare']);g.take('488b03','4c8b9090010000','488ba898010000')
 if g.relative('488d05')!=s['callback']:raise ValueError('langKeyList.dispatch-matched-callback')
 g.take('4c3bd0');g.branch('0f85',False);g.relative('803d');g.take('00');g.branch('75',True,1);g.take('837e3001','c644246000');g.branch('7d',True,1);g.take('488b4650','8038ff');g.branch('75',not null,1)
 if null:
  g.take('488d542460','488bce');g.call(s['header']);g.take('0f57c0','0f1107')
 else:
  g.take('488b4520');type_class=g.relative('488b0d');g.take('488b98c0000000','83b9e000000000','488b5b50');g.branch('75',True,1);g.take('4885db');g.branch('0f84',False);g.take('83b9e000000000');g.branch('75',True,1);g.take('488bcb');g.call(s['typeHandle']);g.take('4885c0');g.branch('0f84',False);g.take('b944000000','488bd0');g.call(s['typeFlags']);g.take('33db','a980000000');g.branch('76',create,1)
  if create:g.take('488b4520','488b88c0000000','488b4958');g.call(s['activate'])
  else:g.take('8bc3');g.jump('eb',1)
  g.relative('381d');g.take('488b4d20','4889442468','488b91c0000000','488b6a18');g.branch('75',True,1);provider=g.relative('488b0d');g.take('3999e0000000');g.branch('75',True,1);g.take('488b4d20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider']);g.take('4885c0');g.branch('0f84',False);g.take('b905000000','4c89742430','4c8d4c2468','4c8bc6','488bd0');g.call(s['ordinaryDispatch']);g.take('4c8b742468','4d85f6');g.branch('75',not wrapper_null,1)
  if wrapper_null:g.take('0f57c0','0f1107')
  else:
   g.take('488b4d20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['context']);g.take('498b2e','488bf0','488bcd');g.call(s['prepare']);g.take('0fb79530010000','663bda');g.branch('73',False,1);g.take('488b8db0000000')
   for i in range(ordinal+1):
    g.take('0fb7c3','4803c0','483934c1');g.branch('74',i==ordinal,1)
    if i<ordinal:g.take('66ffc3','663bda');g.branch('72',True,1)
   g.take('488b85b0000000','0fb7cb','4803c9','486344c808','4883c014','48c1e004','4803c5');g.jump('e9');g.take('4c8b08','488d4c2420','4c8b4008','498bd6','41ffd1');collector=g.relative('833d');g.take('00','0f1000','0f1107');g.branch('0f84',True)
  g.take('4c8b742430')
 g.take('4883c438','5f','5e','5d','5b','c3')
 return dict(selectedBytes=g.seen,null=null,create=create,wrapperNull=wrapper_null,interfaceOrdinal=ordinal,slot=5,callback=s['callback'],outputBytes=16,normalReturn=True,collectorDisabled=not(null or wrapper_null),boundary='Exact matched managed16 callback route, coherent ready adapter/conversion contexts, ordinary normal helper effects. Nonnull concrete wrapper uses owned interface ordinal and hidden RCX output/RDX receiver/R8 MethodInfo; exact16 copy unchanged. Runtime receiver/vtable/inflation/default formatter choice remains conditional.')



def array_store_program(regions,entry,barrier):
 g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1);g.take('410f2800','488d4202','4803c0','0f1104c1','488d4202','48c1e004','4803c8','4883c428')
 if g.relative('e9')!=barrier:raise ValueError('langKeyList.array-store-barrier')
 return dict(selectedBytes=g.seen,arrayStride=16,arrayDataOffset=32,valueBitsPreserved=128,normalReturnViaBarrier=True,boundary='Aligned readable source16, typed array with initial count0 and capacity>=1, nonnegative in-range index, normal terminating barrier.')



"""Fresh typed joins; the called managed16 body never stands in for wire width."""
import json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,validate_typed_usage_context,_vtable,derive_typed_usage_context
from scripts.game_data.memorypack import reference_param,scalar_param_native as scalar,pooled_nominal_key_sources,utf8_source_helper,int_list_sources
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.memorypack.reference_instance_sources import validate_instance_context
from scripts.game_data.levelscript_family_regenerate import Build
LABEL='langKeyListParam'
VALUE='System.Collections.Generic.List`1<Beyond.LangKey>'
BOUNDARY=dict(direct='Typed MC4 Param<List<LangKey>> parent, owned fields/null/factory, pooled bindings/path; exact current ListFormatter null/zero/one selected paths, managed16 callback/default/storage and separately proved generated nominal LangKey child.',conditional='Coherent ready selected instantiated parent/List/managed16 adapter/provider/conversion contexts; canonical LangKey managed16 source callback and exact wrapper GetValue/formatter. Stable disjoint buffered reader/output/frame, zeroed fresh List allocation and normal typed capacity1/empty-array allocation, prior existing count0 with capacity>=1, normal class/preparation/activation/barrier/hash/equality/locks/helpers and disabled collector. Providers follow checked successful first-probe mappings under stated raw slot predicates and expected assignability; live contents/default/inflation/initializers are unobserved.',unresolved=['list counts above1','positive old-size Clear/growth','live provider/cache/override/default selection','cold refill or malformed helpers','whole-owner runtime execution'])


def derive(image,pins,profile):
 base=image.pe.image_base;md=image.metadata;entries=GenericEntries(image);need=lambda k,e,a:scalar.need(LABEL,k,e,a);fail=lambda k,e,a:need(k,e,a)
 if set(profile)!={'parent','symbols'}:raise ValueError(LABEL+'.profile-shape')
 parent,ctx,owned,calls=reference_param.derive_reference_parameter(image,pins,profile['parent'],VALUE,reader_method='ReadPackable');s={k:base+v for k,v in profile['symbols'].items()}
 at,h=parent['parent']['instructions'][31];h=bytes.fromhex(h);need('parent-actual-value-call',b'\xe8',h[:1]);Build(image,pins).prove_reader_clone_target(base+at+5+int.from_bytes(h[1:],'little',signed=True),'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
 td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1'];method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize'];_vtable(image,td.index,5,method.index,LABEL);entry=entries.resolve(method.index,['Beyond.LangKey'],[]);arg,=entry['classInstantiation']['arguments'];raw=bytes.fromhex(arg['raw_type_record_hex']);need('closed-LangKey-ABI',(17,128),(raw[10],raw[11]));need('closed-LangKey-type',ctx.index.types['Beyond.LangKey'].index,int.from_bytes(raw[:8],'little'))
 list_context=ContextSymbols(image).context(td.index);list_owner=ctx.index.types['System.Collections.Generic.List`1'];list_ctor_context=ContextSymbols(image).context(list_owner.index);validate_generic_contexts(image,[list_context,list_ctor_context],label=LABEL);typed=validate_list_formatter_base_context(image,list_context,entries,fail=fail);capacity_context=validate_capacity_constructor_context(image,list_context,list_ctor_context,entries,fail=fail);slots={r['relativeSlot']:r for r in list_context['entries']}
 params=list(md.parameters_for(method));need('list-ABI',(False,2,'void'),(bool(method.flags&16),len(params),ctx.type_name(method.return_type)));reader=ctx.index.types['MemoryPack.MemoryPackReader'];formal=image.pe.bytes_at_va(ctx.type_pointer(params[0].type_index),16);byval=image.pe.bytes_at_va(ctx.type_pointer(reader.byval_type_index),16);need('reader-kind',(b'\x11\x80',b'\x11\x20'),(byval[10:12],formal[10:12]));need('reader-identity',('MemoryPack.MemoryPackReader','System.ValueType',byval[:8]),(ctx.type_name(params[0].type_index),ctx.parent('MemoryPack.MemoryPackReader'),formal[:8]));formal=image.pe.bytes_at_va(ctx.type_pointer(params[1].type_index),16);byval=image.pe.bytes_at_va(ctx.type_pointer(slots[0]['index']),16);need('owned-byref-list',(b'\x15\x20',b'\x15\x00',byval[:8]),(formal[10:12],byval[10:12],formal[:8]))
 body=owned(entry['pointer']);programs=[list_program(body['regions'],body['pointer'],s,count=-1)]+[list_program(body['regions'],body['pointer'],s,count=c,new=n)for c in(0,1)for n in(False,True)];native={};proofs={}
 def capture(role,pointer,*,prefix=None):
  if prefix:
   import hashlib
   raw=image.pe.bytes_at_va(pointer,prefix);result=dict(pointer=pointer,regions=[(pointer,raw)],windows=[dict(startRva=pointer-base,endRva=pointer-base+prefix,sha256=hashlib.sha256(raw).hexdigest().upper())],ownership='bounded registered leaf prefix with complete selected zero-count return')
  else:result=owned(pointer);result['ownership']='completeUnwindFamily'
  native[role]=dict(entryRva=pointer-base,windows=result['windows'],ownership=result['ownership']);return result['regions'],pointer
 for slot,role in((1,'constructor'),(2,'clear'),(6,'add')):
  reg=entries.resolve(slots[slot]['methodSpec'][0],['Beyond.LangKey'],[]);need('same-element.'+role,[a['raw_type_record_hex']for a in entry['classInstantiation']['arguments']],[a['raw_type_record_hex']for a in reg['classInstantiation']['arguments']]);m=md.methods[slots[slot]['methodSpec'][0]];need('List-method.'+role,('System.Collections.Generic.List`1',{'constructor':'.ctor','clear':'Clear','add':'Add'}[role],False,'void'),(image.type_name(m.declaring_type),md.string(m.name_index),bool(m.flags&16),ctx.type_name(m.return_type)));ps=list(md.parameters_for(m));need(role+'.arity',0 if role=='clear'else 1,len(ps))
  if role=='add':
   formal=image.pe.bytes_at_va(ctx.type_pointer(ps[0].type_index),16);var,=next(r for r in list_ctor_context['entries']if r['relativeSlot']==0)['type']['classArguments'];need('Add-owned-VAR',bytes.fromhex(var['rawHex']),formal)
  if role=='constructor':need('actual-closed-constructor',reg['pointer'],s['constructor'])
  native['registered'+role]=reg
  if role=='constructor':proofs['constructor']=[capacity_program(*capture(role,reg['pointer']),s,positive=p)for p in(False,True)]
  elif role=='clear':proofs['clear']=[clear_program(*capture(role,s[role])),clear_program(*capture('canonicalClear',reg['pointer'],prefix=34),canonical=True)]
  else:proofs['add']=[add_program(*capture(role,s[role]),s),add_program(*capture('canonicalAdd',reg['pointer']),s,canonical=True)]
 proof_array=array_store_program(*capture('arrayStore',s['arrayStore']),s['barrier']);proofs['arrayStore']=proof_array
 lcslot,=[r for r in list_ctor_context['entries']if r['relativeSlot']==0];var,=lcslot['type']['classArguments'];static=[f for f in md.fields_for(list_owner)if ctx.field_attributes(f.type_index)&16 and not ctx.field_attributes(f.type_index)&64];need('sole-stored-static-array',1,len(static));empty=static[0];raw=image.pe.bytes_at_va(ctx.type_pointer(empty.type_index),16);need('static-array-VAR',(29,0,var['typePointerVa']),(raw[10],raw[11],int.from_bytes(raw[:8],'little')))
 offset=scalar.reader_offsets(image,LABEL);need('reader-source-profile',dict(currentPtr=80,bufferLength=48,advancedCount=64,consumed=68),offset);headers=utf8_source_helper._contract();need('header-inputs',pins,headers['nativeInputs']);need('actual-count-header',headers['bodies']['header']['entryRva'],s['header']-base);header=utf8_source_helper._validate_native(image,headers)
 nominal_path=CONTRACTS_DIR/'levelscript_nominal_key_param_native.json';nominal_raw=nominal_path.read_bytes();nominal=json.loads(nominal_raw);need('nominal-current-inputs',pins,nominal['nativeInputs']);need('nominal-schema','endfield.levelscript-nominal-key-param-native.v1',nominal['schema']);pooled_nominal_key_sources.validate_components(image,nominal);adapter=nominal['adapterContext'];adapter_slots={r['relativeSlot']:r for r in adapter['entries']};provider=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);activator=ContextSymbols(image).context(adapter_slots[11]['methodSpec'][0],is_method=True);validate_generic_contexts(image,[provider,activator],label=LABEL);instance=validate_instance_context(image,adapter,[provider,activator],entries,adapter_slots[3]['methodSpec'][0],fail=fail);need('same-GetFormatter-definition',slots[3]['methodSpec'][0],adapter_slots[4]['methodSpec'][0]);need('actual-matched-callback',nominal['wideEntries']['Deserialize']['registration']['pointer'],s['callback']);need('shared-ordinary-dispatch',nominal['wideSymbols']['dispatch'],s['ordinaryDispatch']-base);need('shared-object-header',nominal['wideSymbols']['header'],s['objectHeader']-base)
 proofs['valueProvider']=value_provider_program(*capture('valueProvider',s['provider']),s);proofs['wrapperProvider']=wrapper_provider_program(*capture('wrapperProvider',s['wrapperProvider']),s);ds=dict(s,header=s['objectHeader']);proofs['dispatch']=[inline_dispatch_program(*capture('inlineDispatch',s['dispatch']),ds,null=True)]+[inline_dispatch_program(*capture('inlineDispatch',s['dispatch']),ds,create=c,wrapper_null=n,ordinal=nominal['interfaceOrdinal'])for c in(False,True)for n in(False,True)]
 shared=generic_provider_factory(image,pins,s,need);need('same-provider-class',[shared['providerClassCell']]*3,[programs[1]['providerOwnerCell'],proofs['valueProvider']['providerClassCell'],proofs['wrapperProvider']['providerClassCell']]);need('same-provider-ready-flag',proofs['valueProvider']['readyFlag'],proofs['wrapperProvider']['readyFlag']);need('same-System.Type-class',proofs['valueProvider']['typeClassCell'],proofs['wrapperProvider']['typeClassCell']);need('ordinary-shared-context-helper',s['context'],base+shared['contextHelperRva'])
 provider_owner,=[r for r in body['rows']if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d' and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==programs[1]['providerOwnerCell']];owner_usage=derive_typed_usage_context(image,int(provider_owner['va'],16)-base,label=LABEL);need('typed-provider-owner',(1,'MemoryPack.MemoryPackFormatterProvider'),(owner_usage['tag'],owner_usage['typeName']))
 if nominal_raw!=nominal_path.read_bytes():raise ValueError(LABEL+'.nominal-dependency-changed')
 return json.loads(json.dumps(dict(parent=parent,listRegistration=entry,listWindows=body['windows'],listContext=list_context,typedBase=typed,capacityContext=capacity_context,constructorContext=list_ctor_context,staticEmptyArray=dict(name=md.string(empty.name_index),rawTypeHex=raw.hex().upper()),native=native,programs=programs,components=proofs,providerContext=provider,activatorContext=activator,instanceContext=instance,closedProviderObservedEntries=entries.observe(slots[3]['methodSpec'][0],[],['Beyond.LangKey']),genericFactoryProvider=shared,providerOwner=owner_usage,collectionHeader=header,nominalDependency=nominal_path.name,nominalInterfaceOrdinal=nominal['interfaceOrdinal'],collectionCounts=[-1,0,1],evidenceBoundary=BOUNDARY)))


def generic_provider_factory(image,pins,s,need):
 from scripts.game_data.il2cpp.consumer_instructions import decode_consumer_instructions
 from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 path=CONTRACTS_DIR/'levelscript_int_list_native.json';raw=path.read_bytes();fact=json.loads(raw);base=image.pe.image_base;need('generic-dependency-inputs',pins,fact['nativeInputs']);need('generic-dependency-shape',('endfield.levelscript-int-list-native.v1','exact-current-build'),(fact['schema'],fact['status']));calls={k:base+v for k,v in fact['calls'].items()};backend=fact['bodies']['providerBackend'];need('actual-Type-key-backend',backend['entryRva'],s['backend']-base)
 def regions(record):image.check_windows(record['windows'],label=LABEL+'.generic');return[(base+w['startRva'],image.window_bytes(w))for w in record['windows']]
 need('complete-Type-key-backend',sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(backend['entryRva'])['ranges']),sorted((w['startRva'],w['endRva'])for w in backend['windows']));provider=int_list_sources.backend(regions(backend),s['backend'],{k:calls[k]for k in('resolveClass','hash','equals')});validate_typed_usage_context(image,fact['backendContext'],label=LABEL);u=fact['backendContext'];need('typed-Type-key-backend',('System.Collections.Concurrent.ConcurrentDictionary`2','TryGetValue',['System.Type','MemoryPack.IMemoryPackFormatter'],[]),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']));need('backend-method-cell',base+u['usageCellRva'],provider['methodInfoCell']);context=fact['bodies']['contextResolver'];need('actual-indexed-context-helper',context['entryRva'],s['context']-base);resolver=int_list_sources.initialized_class(regions(context),s['context'],indexed=True)
 f=fact['factory'];image.check_instruction_windows(f['instructions'],label=LABEL)
 for u in f['usages']:validate_typed_usage_context(image,u,label=LABEL)
 need('open-List-factory',['System.Collections.Generic.List`1','MemoryPack.Formatters.ListFormatter`1'],[u['typeName']for u in f['usages'][:2]]);mapping=int_list_sources.factory_pair(regions(f),base+f['entryRva'],type_handle=base+f['typeHandleRva'],add=base+f['addRva']);need('factory-usage-cells',[base+u['usageCellRva']for u in f['usages']],[mapping[k]for k in('keyTypeCell','valueTypeCell','addMethodInfoCell')]);u=f['usages'][2];need('factory-map-Add',('System.Collections.Generic.Dictionary`2','Add',['System.Type','System.Type'],[]),(u['typeName'],u['methodName'],u['classArguments'],u['methodArguments']));need('factory-Add-entry',base+f['addRva'],GenericEntries(image).resolve(u['methodSpec'][0],['object','object'],[])['pointer']);rows=f['receiverInstructions'];image.check_instruction_windows(rows,label=LABEL);code=b''.join(bytes.fromhex(h)for _,h in rows);need('factory-receiver-contiguous',code,image.pe.bytes_at_va(base+rows[0][0],len(code)));receiver=int_list_sources.factory_receiver(decode_consumer_instructions(image.mapper,code,base+rows[0][0]));ctx=NativeReferenceContext(image);td=ctx.index.types['MemoryPack.MemoryPackFormatterProvider'];field,=[f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)=='CollectionFormatters'];need('factory-static-field',('System.Collections.Generic.Dictionary`2<System.Type,System.Type>',True,8),(ctx.type_name(field.type_index),bool(ctx.field_attributes(field.type_index)&16),runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index)['CollectionFormatters']))
 if raw!=path.read_bytes():raise ValueError(LABEL+'.factory-dependency-changed')
 return dict(dependency=path.name,provider=provider,providerClassCell=provider['providerClassCell'],contextHelperRva=context['entryRva'],contextResolver=resolver,factory=mapping,factoryReceiver=receiver,boundary='Fresh generic Type-key backend and open List-to-ListFormatter factory source/context only. No Int32 storage or element grammar reused; runtime map/cache contents/default inflation are conditional.')
