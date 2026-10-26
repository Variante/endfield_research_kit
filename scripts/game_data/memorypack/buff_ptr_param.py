"""Selected BuffPtr hidden16 and concrete ObjectPtr<Buff> nested framing.

BuffPtr carries the complete managed16 ObjectPtr value, including its object
reference and UInt32 cachedUid. Wire order is cachedUid then Buff reference;
the selected leaf composes its own current concrete Buff MC1 source.
Whole Param, BuffPtr-wrapper and ObjectPtr-wrapper nulls remain distinct
framing routes even though the latter two produce a zero managed value.
Live formatter selection and gameplay use are open.
"""
import json,struct
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack import pointer_param as pointer,primitive_param as primitive,scalar_param_native as scalar
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.vector_layout import vector_recorder

LABEL='buffPtrParam'
VALUE='Beyond.Gameplay.Core.BuffPtr'
OBJECT='Beyond.ObjectPtr`1<Beyond.Gameplay.Core.Buff>'
BUFF='Beyond.Gameplay.Core.Buff'


def flag(g):g.relative('803d');g.take('00')


def buff_child_program(regions,entry,s,*,null=False,allocated=False):
 g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec30');flag(g);g.take('488bda','488bf9');g.branch('74',False,1)
 g.take('488d542440','c644244000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usage=None
 if null:g.take('48c70300000000','488bcb');g.jump('e9')
 else:
  g.take('48833b00');g.branch('0f84',allocated)
  if allocated:
   allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
   g.take('0f57c0','488bcb','0f114010','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('807c244001');g.branch('0f85',False);usage=g.at;g.relative('4c8b05')
  g.take('488d4c2420','488b1b','488bd7');g.call(s['value16']);g.take('4885db');g.branch('74',False,1)
  g.take('0f10442420','488d4b10','0f1101')
 g.take('488b5c2448','4883c430','5f')
 if g.relative('e9')!=s['barrier']:raise ValueError(LABEL+'.child-barrier')
 return dict(selectedBytes=g.seen,null=null,allocated=allocated,allocationUsageSite=allocation,valueUsageSite=usage,memberCount=None if null else 1,hiddenResultBytes=16,storedValueBytes=16,storedValueOffset=16,normalTailReturn=True)


def object_ptr_program(regions,entry,s,*,null=False,allocated=False):
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec20');flag(g);g.take('488bda','488bf9');g.branch('0f84',False)
 g.take('488d542430','c644243000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null);allocation=None;usage=None
 if null:
  g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742438','48833b00');g.branch('0f84',allocated)
  if allocated:
   allocation=g.at;g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
   g.take('0f57c0','488bcb','0f114010','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb6742430','4080fe02');g.branch('0f85',False)
  g.take('488b33','488bcf');g.call(s['integer']);g.take('4885f6');g.branch('74',False,1);g.take('894618','488bcf')
  usage=g.at;g.relative('488b15');g.take('488b1b');g.call(s['reference']);g.take('4885db');g.branch('74',False,1)
  g.take('488d4b10','488901');g.call(s['barrier']);g.take('488b742438')
 g.take('488b5c2440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,null=null,allocated=allocated,allocationUsageSite=allocation,referenceUsageSite=usage,memberCount=None if null else 2,wireOrder=['cachedUid','obj'],cachedUidBytes=4,cachedUidStorageOffset=24,referenceStorageOffset=16,outputValueBytes=16,normalReturn=True)


def source_target(source,offset,opcode=b'\xe8'):
 at=source['pointer']+offset;row,=[r for r in source['rows']if int(r['va'],16)==at];raw=bytes.fromhex(row['bytes'])
 scalar.need(LABEL,'controlShape',(len(opcode)+4,opcode),(len(raw),raw[:len(opcode)]))
 return at+len(raw)+int.from_bytes(raw[len(opcode):],'little',signed=True)


def closed_object_type(image,ctx,field):
 pointer_=ctx.type_pointer(field.type_index);raw=image.pe.bytes_at_va(pointer_,16)
 scalar.ordinary(image,pointer_,21,LABEL+'.closedObjectType')
 scalar.need(LABEL,'closedObjectName',OBJECT,runtime_type_name(image.pe,image.metadata,pointer_))
 carrier=int.from_bytes(raw[:8],'little');definition,instance=struct.unpack('<QQ',image.pe.bytes_at_va(carrier,16))
 scalar.need(LABEL,'genericDefinition','Beyond.ObjectPtr`1',runtime_type_name(image.pe,image.metadata,definition))
 scalar.ordinary(image,definition,17,LABEL+'.objectPtrDefinition')
 scalar.need(LABEL,'closedGenericValue',True,ctx.is_value_type(OBJECT))
 args=image.instantiations.resolve_pointer(instance).arguments
 scalar.need(LABEL,'objectPtrArity',1,len(args));scalar.ordinary(image,args[0].type_pointer_va,18,LABEL+'.BuffArgument',reference=True)
 scalar.need(LABEL,'objectPtrArgument',BUFF,runtime_type_name(image.pe,image.metadata,args[0].type_pointer_va))
 td=ctx.index.types['Beyond.ObjectPtr`1'];md=image.metadata;fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 scalar.need(LABEL,'objectPtrDefinitionFields',['obj','cachedUid'],[md.string(f.name_index)for f in fields])
 obj,cached=fields;obj_raw=image.pe.bytes_at_va(ctx.type_pointer(obj.type_index),16);scalar.ordinary(image,ctx.type_pointer(obj.type_index),19,LABEL+'.objectPtrOpenObject')
 owner=type_parameter_owner(md.buf,int.from_bytes(obj_raw[:8],'little'),[t.generic_container_index for t in md.types],source=LABEL)
 scalar.need(LABEL,'objectPtrOwnVAR',(td.index,0),(owner['typeIndex'],owner['ordinal']))
 scalar.need(LABEL,'objectPtrUidType','uint',ctx.type_name(cached.type_index));scalar.ordinary(image,ctx.type_pointer(cached.type_index),9,LABEL+'.objectPtrUid')
 return dict(closedType=OBJECT,closedTypeRawHex=raw.hex().upper(),definitionTypeIndex=td.index,definitionTypeRawHex=image.pe.bytes_at_va(definition,16).hex().upper(),argumentType=BUFF,argumentTypeRawHex=image.pe.bytes_at_va(args[0].type_pointer_va,16).hex().upper(),ownedGenericParameter=owner,openGenericOffsetsUsed=False)


def value_methods(image,ctx,w,value,kind):
 mm=pointer.methods(image,w);result={}
 scalar.need(LABEL,'valueWrapperHolder',(w.name,value,16),ctx.field(w.name+'::__instance'))
 for name in('.ctor','CreateInstance'):
  scalar.owned_method_abi(image,ctx,mm[name].index,w.type_definition,('void',1,False),[],LABEL+'.default')
  result[name]=pointer.leaf(image,image.method_pointer_va(mm[name]),['0F57C0','0F114110','C3'])
 scalar.owned_method_abi(image,ctx,mm['GetValue'].index,w.type_definition,(value,kind,False),[],LABEL+'.getter')
 result['GetValue']=pointer.leaf(image,image.method_pointer_va(mm['GetValue']),['0F104210','488BC1','0F1101','C3'])
 primitive.reader_abi(image,ctx,mm['Deserialize'],w)
 return result,mm,pointer.owned(image,image.method_pointer_va(mm['Deserialize']))


def allocation(image,ctx,source,branch_offset,wrapper):
 at=source_target(source,branch_offset,b'\x0f\x84');usage=derive_typed_usage_context(image,at-image.pe.image_base,label=LABEL+'.allocation')
 scalar.need(LABEL,'allocatedNamedWrapper',wrapper.name,usage['typeName']);scalar.ordinary(image,ctx.type_pointer(usage['typeIndex']),18,LABEL+'.allocation',reference=True)
 return usage,source_target(source,at-source['pointer']+7)


def derive_children(image,pins,profile,parent,ctx):
 base=image.pe.image_base;md=image.metadata;wrappers=derive_from_image(image);bw,=[w for w in wrappers.values()if w.wrapped_type==VALUE];ow,=[w for w in wrappers.values()if w.wrapped_type==OBJECT]
 scalar.need(LABEL,'buffPtrMembers',[('ptr',OBJECT)],[(m.name,m.declared_type)for m in bw.members])
 scalar.need(LABEL,'objectPtrMembers',[('cachedUid','uint'),('obj',BUFF)],[(m.name,m.declared_type)for m in ow.members])
 td=ctx.index.types[VALUE];fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 scalar.need(LABEL,'buffPtrOneField',['ptr'],[md.string(f.name_index)for f in fields]);scalar.need(LABEL,'buffPtrField',(VALUE,OBJECT,16),ctx.field(VALUE+'::ptr'))
 sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
 # Il2CppTypeDefinitionSizes.native_size is the marshaling size. The selected
 # unknown sentinel supplies no managed ABI width; exact getters, setters,
 # hidden-output sources and callers independently prove all sixteen bytes.
 scalar.need(LABEL,'buffPtrBoxedAndNativeSizes',(32,0xffffffff),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)))
 generic=closed_object_type(image,ctx,fields[0])
 bm,bmethods,bs=value_methods(image,ctx,bw,VALUE,17);om,omethods,os=value_methods(image,ctx,ow,OBJECT,21)
 barrier=base+parent['barrierRva'];header=base+parent['parentHeader']['pointerRva'];integer=base+parent['integerSource']['pointerRva']
 # Setters authenticate the complete copied managed value and separate owned
 # object/UID fields. Open generic offset placeholders never enter this proof.
 setter=bmethods['set___ptr__'];scalar.owned_method_abi(image,ctx,setter.index,bw.type_definition,('void',1,False),[(OBJECT,21,False)],LABEL+'.ptrSetter')
 at=image.method_pointer_va(setter);raw=image.pe.bytes_at_va(at,15);scalar.need(LABEL,'ptrSetterEntry','0F10024883C1100F1101E9',raw[:11].hex().upper());scalar.need(LABEL,'ptrSetterBarrier',barrier,at+15+int.from_bytes(raw[11:],'little',signed=True))
 ptr_setter=dict(entryRva=at-base,bytes=raw.hex().upper(),physicalExtentProved=False)
 setter=omethods['set___cachedUid__'];scalar.owned_method_abi(image,ctx,setter.index,ow.type_definition,('void',1,False),[('uint',9,False)],LABEL+'.uidSetter');uid=pointer.leaf(image,image.method_pointer_va(setter),['895118','C3'])
 setter=omethods['set___obj__'];scalar.owned_method_abi(image,ctx,setter.index,ow.type_definition,('void',1,False),[(BUFF,18,True)],LABEL+'.objSetter');at=image.method_pointer_va(setter);raw=image.pe.bytes_at_va(at,12);scalar.need(LABEL,'objSetterEntry','4883C110488911E9',raw[:8].hex().upper());scalar.need(LABEL,'objSetterBarrier',barrier,at+12+int.from_bytes(raw[8:],'little',signed=True))
 obj_setter=dict(entryRva=at-base,bytes=raw.hex().upper(),physicalExtentProved=False)
 ba,allocate_=allocation(image,ctx,bs,55,bw);oa,oallocate=allocation(image,ctx,os,64,ow)
 scalar.need(LABEL,'sameChildHeader',header,source_target(bs,38));scalar.need(LABEL,'sameNestedHeader',header,source_target(os,42));scalar.need(LABEL,'rawUInt32Reader',integer,source_target(os,91))
 # This helper has the same complete raw four-byte transfer for signed and
 # unsigned metadata callers; the typed uint setter and caller own unsignedness.
 record=vector_recorder(image);scalar.integer_source(image,record(integer-base),scalar.reader_offsets(image,LABEL),LABEL+'.uint32')
 b_symbols=dict(header=header,allocate=allocate_,barrier=barrier,value16=source_target(bs,90));o_symbols=dict(header=header,allocate=oallocate,barrier=barrier,integer=integer,reference=source_target(os,117))
 b_paths=[buff_child_program(bs['regions'],bs['pointer'],b_symbols,**option)for option in({},{'allocated':True},{'null':True})]
 o_paths=[object_ptr_program(os['regions'],os['pointer'],o_symbols,**option)for option in({},{'allocated':True},{'null':True})]
 for usage_,paths in((ba,b_paths),(oa,o_paths)):scalar.need(LABEL,'exactAllocationUsage',base+usage_['instructionRva'],paths[1]['allocationUsageSite'])
 b_usage=derive_typed_usage_context(image,bs['pointer']+72-base,label=LABEL+'.objectPtrRead');o_usage=derive_typed_usage_context(image,os['pointer']+107-base,label=LABEL+'.BuffRead')
 for usage_,wanted in((b_usage,OBJECT),(o_usage,BUFF)):
  scalar.need(LABEL,'typedNestedRead',('MemoryPack.MemoryPackReader','ReadValue',[],[wanted]),tuple(usage_[k]for k in('typeName','methodName','classArguments','methodArguments')))
 b_pair=pointer.registered_pair(image,profile['child'],bw,label=LABEL+'.BuffPtrPair');o_pair=pointer.registered_pair(image,profile['objectPtr'],ow,label=LABEL+'.ObjectPtrPair')
 child=dict(typedRead=b_usage,valueReadTargetRva=b_symbols['value16']-base,referenceTypedRead=o_usage,referenceReadTargetRva=o_symbols['reference']-base)
 return dict(closedObjectType=generic,buffMethods=bm,objectMethods=om,ptrSetter=ptr_setter,uidSetter=uid,objSetter=obj_setter,buffWindows=bs['windows'],objectWindows=os['windows'],buffPaths=b_paths,objectPaths=o_paths,buffAllocation=ba,objectAllocation=oa,buffPair=b_pair,objectPair=o_pair,typedReads=child),child


def derive(image,pins,profile):
 scalar.need(LABEL,'profileShape',{'registration','composition','integerSlots','initializedHeader','child','objectPtr'},set(profile))
 for name in('child','objectPtr'):scalar.need(LABEL,'pairProfileShape:'+name,{'registration','composition'},set(profile[name]))
 parent,ctx=pointer.derive_parent(image,pins,profile,VALUE);children,child=derive_children(image,pins,profile,parent,ctx)
 from scripts.game_data.memorypack.buff_ptr_sources import derive_value_sources
 sources=derive_value_sources(image,pins,profile,parent,child)
 from scripts.game_data.memorypack.buff_object_sources import derive as derive_buff
 buff=derive_buff(image,pins)
 scalar.need(LABEL,'nestedBuffReaderDefinition',buff['referenceReaderMethodDefinition'],child['referenceTypedRead']['methodSpec'][0])
 scalar.need(LABEL,'actualNestedBuffReadTarget',buff['referenceReaderTargetRva'],child['referenceReadTargetRva'])
 return json.loads(json.dumps(dict(parent=parent,children=children,valueSources=sources,buffObject=buff,
  evidenceBoundary=dict(direct='Closed four-member Param transfers the complete managed16 BuffPtr. Its one-member wrapper transfers actual ObjectPtr<Buff>; that two-member wrapper reads raw UInt32 cachedUid then typed Buff. The independent concrete Buff MC1 wrapper reads only modifiedBBKeys, a signed-count pooled string list with null/empty and positive element induction under the explicit count bound10000. Exact typed ReadValue definition and actual target compose these owners. Parent/value/nested allocation/default/null/conversion/framing routes and pooled tails are owned independently.',
   conditional='Initialized coherent selected generated wrappers/formatters, matching canonical callbacks/MethodInfos/interface slots, normal helpers/barriers/allocation and Buff constructor, sufficient buffered disjoint storage and original matching StringPool. New string-list capacity=count or reused prior-count0 with sufficient capacity; live provider selection is conditional.',
   unresolved=['Buff constructor effects/gameplay object identity','positive prior-size reused string-list Clear effects','pool-absent inline strings','cold refill and malformed paths','live formatter/provider/default/cache/override selection','gameplay object behavior']))))
