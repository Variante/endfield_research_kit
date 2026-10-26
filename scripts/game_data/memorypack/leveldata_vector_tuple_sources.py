"""Exact Vector3/Vector3 ValueTuple source; constructed layout/list stay separate.

The selected formatter tail-forwards to DangerousReadUnmanaged, whose normal
buffered path copies all24 bytes and tail-calls the independently owned Reader
Advance. It consumes neither a tuple member header nor a null marker.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
import struct

DEFINITION='System.ValueTuple`2'
ELEMENT='UnityEngine.Vector3'
TYPE=DEFINITION+'<'+ELEMENT+','+ELEMENT+'>'
LABEL='storyVectorTuple'


def direct_constructor_witness(image,entries,method):
 """Bound only the exact ordinary unboxed direct slot; leave adjustor opaque."""
 from scripts.game_data.memorypack.scalar_param_native import need
 check=lambda k,e,a:need(LABEL,k,e,a)
 found=[]
 for index,spec_index in entries._rows_by_method.get(method.index,()):
  check('direct-table-index-bound',True,type(index)is int and 0<=index<entries.meta['genericMethodTableCount'])
  raw=image.pe.bytes_at_va(entries.table_base+16*index,16)
  check('direct-immutable-table-row',entries.table[16*index:16*(index+1)],raw)
  selected,slot,invoker,adjustor=struct.unpack('<iiii',raw)
  check('direct-selected-spec',spec_index,selected);check('direct-spec-bound',True,0<=selected<len(entries.specs))
  definition,ci,mi=entries.specs[selected]
  if mi!=-1 or entries.arguments(ci)[0]!=[ELEMENT,ELEMENT]:continue
  check('direct-fresh-MethodSpec',struct.pack('<iii',definition,ci,mi),
   image.pe.bytes_at_va(int(entries.meta['methodSpecs'],16)+selected*12,12))
  check('direct-owned-constructor',method.index,definition)
  check('direct-pointer-slot-bound',True,0<=slot<entries.code['genericMethodPointersCount'])
  check('direct-invoker-slot-bound',True,0<=invoker<entries.code['invokerPointersCount'])
  pointer=image.pe.u64_at_va(int(entries.code['genericMethodPointers'],16)+8*slot)
  check('direct-nonnull-native-entry',True,pointer>image.pe.image_base)
  found.append(dict(methodDefinition=definition,methodSpec=list(entries.specs[selected]),
   tableIndex=index,tableCount=entries.meta['genericMethodTableCount'],rawRegistrationHex=raw.hex().upper(),
   methodPointerSlot=slot,methodPointerCount=entries.code['genericMethodPointersCount'],pointer=pointer,
   invokerSlot=invoker,invokerCount=entries.code['invokerPointersCount'],classInstantiation=entries.arguments(ci)[1],
   adjustorIndexOpaque=adjustor,adjustorDereferenced=False,adjustorTableExtentProved=False,adjustorAdmitted=False,
   runtimeInvocationObserved=False,physicalPointerUniquenessClaimed=False,constructorSourceProgramRequired=True))
 check('one-exact-direct-Vector3-pair-constructor',1,len(found))
 return found[0]


def require_carrier(symbol,*,tuple_definition,vector_definition):
 """Exact constructed value and two owned Vector3 arguments; no size proof."""
 raw=bytes.fromhex(symbol.get('rawHex',''));definition=symbol.get('definition',{});dr=bytes.fromhex(definition.get('rawHex',''))
 args=symbol.get('classArguments',[])
 if (type(tuple_definition)is not int or type(vector_definition)is not int
   or symbol.get('name')!=TYPE or len(raw)!=16 or raw[10:12]!=b'\x15\x80'
   or definition.get('name')!=DEFINITION or len(dr)!=16 or dr[10:12]!=b'\x11\x80'
   or int.from_bytes(dr[:8],'little')!=tuple_definition or len(args)!=2):
  raise ValueError(LABEL+'.exact-constructed-value-carrier')
 for item in args:
  ar=bytes.fromhex(item.get('rawHex',''))
  if (item.get('name')!=ELEMENT or len(ar)!=16 or ar[10:12]!=b'\x11\x80'
    or int.from_bytes(ar[:8],'little')!=vector_definition):
   raise ValueError(LABEL+'.exact-two-Vector3-arguments')
 return dict(typeName=TYPE,concreteTypeKind=21,valueCarrier=True,definitionTypeIndex=tuple_definition,
  classArguments=[ELEMENT,ELEMENT],argumentDefinitionIndices=[vector_definition,vector_definition],managedBytes=None,
  layoutAdmitted=False,wireGrammarAdmitted=False)


def formatter_program(regions,entry,target):
 g=BytesPath(regions,entry)
 g.take('498b4120','4d8bd0','488bca','498bd2','4c8b80c0000000','4d8b00')
 actual=g.relative('e9')
 if actual!=target:raise ValueError(LABEL+'.exact-DangerousReadUnmanaged-tail-target')
 return dict(selectedBytes=g.seen,entryBytes=28,contextSlot=0,contextSource='incoming r9 MethodInfo',
  readerArgument='incoming rdx to rcx',outputArgument='incoming r8 to rdx',methodInfoArgument='same context slot0 to r8',
  receiverNotRead=True,entryRspUnchanged=True,normalTail=True,headerBytes=0,nullMarkerAdmitted=False,
  fullReachableEntryProgramProved=True,unwindExtentInferred=False,childWireGrammarAdmitted=False)


def raw24_program(regions,entry,offsets,advance):
 cur,rem=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength'))
 g=BytesPath(regions,entry)
 g.take('48895c2408','57','4883ec20','8379'+rem+'18','488bfa','488bd9');g.branch('0f8c',False)
 g.take('488b41'+cur,'0f1008','ba18000000','488bcb','f20f104010','0f110f','f20f114710',
  '488b5c2430','4883c420','5f')
 target=g.relative('e9')
 if target!=advance:raise ValueError(LABEL+'.exact-Advance24-tail-target')
 return dict(selectedBytes=g.seen,wireBytes=24,managedOutputBytes=24,
  capturedSourceSlices=[[0,16],[16,8]],storedOutputSlices=[[0,16],[16,8]],
  readerArgument='incoming rcx',outputArgument='incoming rdx',advanceReaderArgument='same incoming rcx',
  advanceSignedCount=24,independentAdvanceSourceRequired=True,normalTail=True,
  entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],headerBytes=0,nullMarkerAdmitted=False,
  frame=dict(entryRspDelta=-40,callShadow=[0,32],savedRbxEntryHome=[8,16],pushedNonvolatiles=['rdi']),
  constructedLayoutAdmitted=False,collectionAdmitted=False)


def constructor_program(regions,entry):
 """Complete selected direct unboxed ctor; no adjustor or open layout used."""
 g=BytesPath(regions,entry)
 g.take('f20f1002','8b4208','f20f1101','f2410f1000','894108','418b4008','f20f11410c','894114','c3')
 return dict(selectedBytes=g.seen,managedReceiverRegister='rcx',argumentRegisters=['rdx','r8'],
  argumentBytes=[12,12],fieldOffsets=[0,12],fieldCopySlices=[[[0,8],[8,4]],[[12,8],[20,4]]],
  complete24FieldBytesStored=True,referenceLaneOffsets=[],paddingByteRanges=[],normalReturn=True,
  stackAndNonvolatilesUntouched=True,constructorInvocationObserved=False,adjustorAdmitted=False,
  completeNormalUnboxedProgramProved=True,physicalFunctionExtentProved=False)


def derive(image,pins,*,type_pointer):
 """Fresh exact constructed carrier, unboxed ctor and canonical raw24 source."""
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.context import type_parameter_owner
 from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,_vtable
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import scalar_param_native as scalar,generated_called_advance_sources
 from scripts.game_data.memorypack.pointer_param import owned
 check=lambda k,e,a:scalar.need(LABEL,k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;sy=ContextSymbols(image);ge=GenericEntries(image)
 td=ctx.index.types[DEFINITION];vector=ctx.index.types[ELEMENT];symbol=sy.type(type_pointer)
 carrier=require_carrier(symbol,tuple_definition=td.index,vector_definition=vector.index)
 check('nominal-tuple-value-ancestry',(True,False,'System.ValueType'),(ctx.is_value_type(DEFINITION),ctx.is_enum(DEFINITION),ctx.parent(DEFINITION)))
 section=md.sections['genericContainers'];at=section.offset+16*td.generic_container_index
 check('bounded-class-container',True,td.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
 definition,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
 check('exact-two-class-parameters',(td.index,2,0),(definition,count,is_method));containers=[t.generic_container_index for t in md.types]
 for ordinal in(0,1):
  owner=type_parameter_owner(md.buf,start+ordinal,containers,source=LABEL)
  check('reciprocal-tuple-parameter:'+str(ordinal),(td.index,ordinal),(owner['typeIndex'],owner['ordinal']))
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 check('exact-owned-two-tuple-fields',['Item1','Item2'],[md.string(f.name_index)for f in fields])
 for ordinal,f in enumerate(fields):
  argument=sy.type(ctx.type_pointer(f.type_index));raw=bytes.fromhex(argument['rawHex'])
  check('owned-field-VAR:'+str(ordinal),(b'\x13\x00',td.index,ordinal),
   (raw[10:12],argument['parameterOwner']['typeIndex'],argument['parameterOwner']['ordinal']))
 vector_fields=[f for f in md.fields_for(vector)if not ctx.field_attributes(f.type_index)&16]
 check('Vector3-exact-nominal-Single-fields',[(axis,'float',16+4*n)for n,axis in enumerate('xyz')],
  [(md.string(f.name_index),*ctx.field(ELEMENT+'::'+md.string(f.name_index))[1:])for f in vector_fields])
 for f in vector_fields:scalar.ordinary(image,ctx.type_pointer(f.type_index),12,LABEL+'.Vector3.Single')
 check('Vector3-ordinary-value',(True,False,-1),(ctx.is_value_type(ELEMENT),ctx.is_enum(ELEMENT),vector.generic_container_index))
 check('bounded-Vector3-size-index',True,0<=vector.index<image.registration['typeDefinitionsSizesCount'])
 sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*vector.index)
 check('Vector3-boxed-native-sizes',(28,12),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)))
 ctor,=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor'and m.parameter_count==2]
 check('tuple-instance-void-ctor',(0,'void'),(ctor.flags&16,ctx.type_name(ctor.return_type)))
 for ordinal,p in enumerate(md.parameters_for(ctor)):
  argument=sy.type(ctx.type_pointer(p.type_index));raw=bytes.fromhex(argument['rawHex'])
  check('ctor-owned-byvalue-VAR:'+str(ordinal),(b'\x13\x00',td.index,ordinal),
   (raw[10:12],argument['parameterOwner']['typeIndex'],argument['parameterOwner']['ordinal']))
 ctor_entry=direct_constructor_witness(image,ge,ctor);ctor_raw=image.pe.bytes_at_va(ctor_entry['pointer'],32)
 ctor_program=constructor_program([(ctor_entry['pointer'],ctor_raw)],ctor_entry['pointer'])
 formatter=ctx.index.types['MemoryPack.Formatters.ValueTupleFormatter`2']
 method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
 check('formatter-instance-slot5-void',(0,5,2,'void'),(method.flags&16,method.slot,method.parameter_count,ctx.type_name(method.return_type)))
 _vtable(image,formatter.index,5,method.index,LABEL)
 context=sy.context(formatter.index);validate_generic_contexts(image,[context],label=LABEL+'.formatter')
 slots={r['relativeSlot']:r for r in context['entries']};nested,=slots[0]['methodArguments']
 check('actual-DangerousReadUnmanaged-slot',(3,'MemoryPack.MemoryPackReader','DangerousReadUnmanaged',[],-1),
  (slots[0]['kind'],slots[0]['typeName'],slots[0]['methodName'],slots[0]['classArguments'],slots[0]['methodSpec'][1]))
 check('formatter-tuple-carrier',(DEFINITION,b'\x15\x80'),(nested['definition']['name'],bytes.fromhex(nested['rawHex'])[10:12]))
 check('formatter-tuple-two-arguments',2,len(nested['classArguments']))
 for ordinal,item in enumerate(nested['classArguments']):
  check('formatter-owned-tuple-VAR:'+str(ordinal),(b'\x13\x00',formatter.index,ordinal),
   (bytes.fromhex(item['rawHex'])[10:12],item['parameterOwner']['typeIndex'],item['parameterOwner']['ordinal']))
 check('same-tuple-ctor-declaration',ctor.index,slots[4]['methodSpec'][0])
 check('same-context-tuple-argument',nested,slots[3]['type'])
 check('tuple-constructor-owned-formatter-arguments',nested['classArguments'],slots[4]['classArguments'])
 reader,output=md.parameters_for(method);rr=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16);out=image.pe.bytes_at_va(ctx.type_pointer(output.type_index),16)
 check('formatter-exact-Reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),(rr[10:12],int.from_bytes(rr[:8],'little')))
 # The selected byref carrier uses20, without the byval value marker80.
 # Its shared generic data pointer and independently proved value definition
 # bind the same tuple; no reference representation follows from this flag.
 check('formatter-same-tuple-byref',(b'\x15\x20',bytes.fromhex(nested['rawHex'])[:8]),(out[10:12],out[:8]))
 registration=ge.resolve(method.index,[ELEMENT,ELEMENT],[])
 check('formatter-exact-two-closed-Vector3-pointers',[a['typePointerVa']for a in symbol['classArguments']],
  [a['type_pointer_va']for a in registration['classInstantiation']['arguments']])
 prefix=image.pe.bytes_at_va(registration['pointer'],28);g=BytesPath([(registration['pointer'],prefix)],registration['pointer'])
 g.take('498b4120','4d8bd0','488bca','498bd2','4c8b80c0000000','4d8b00');actual=g.relative('e9')
 forwarding=formatter_program([(registration['pointer'],prefix)],registration['pointer'],actual)
 dangerous=md.methods[slots[0]['methodSpec'][0]];parameter,=md.parameters_for(dangerous)
 check('Dangerous-instance-void-one',(0,'void',1),(dangerous.flags&16,ctx.type_name(dangerous.return_type),dangerous.parameter_count))
 raw_parameter=sy.type(ctx.type_pointer(parameter.type_index))
 check('Dangerous-output-owned-MVAR-byref',(b'\x1e\x20',dangerous.index,0),
  (bytes.fromhex(raw_parameter['rawHex'])[10:12],raw_parameter['parameterOwner']['methodIndex'],raw_parameter['parameterOwner']['ordinal']))
 dangerous_registration=ge.resolve(dangerous.index,[],[TYPE])
 item,=dangerous_registration['methodInstantiation']['arguments']
 check('Dangerous-same-constructed-carrier',carrier,require_carrier(sy.type(item['type_pointer_va']),tuple_definition=td.index,vector_definition=vector.index))
 body=owned(image,actual);tail=next(control_transfer(r)['target']for r in body['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9')
 offsets=scalar.reader_offsets(image,LABEL);raw_program=raw24_program(body['regions'],actual,offsets,tail)
 advance=generated_called_advance_sources.derive(image,pins,target=tail,offsets=offsets)
 _publication_gate(image,pins)
 cap=dict(typeName=TYPE,classArguments=[ELEMENT,ELEMENT],managedBytes=24,wireBytes=24,headerBytes=0,
  referenceLaneOffsets=[],paddingByteRanges=[],constructedValueLayoutProved=True,actualRawSourceProved=True,
  actualAdvanceSourceProved=True,actualCallbackEqualsCanonicalRequired=True,finiteFloatProfile=True,profileAdmitted=True,
  nullMarkerAdmitted=False,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False)
 return json.loads(json.dumps(dict(schema='endfield.story-vector3-tuple-source.v1',status='validated-conditional-constructed-tuple-profile',nativeInputs=pins,
  capability=cap,proof=dict(selectedCarrier=symbol,carrier=carrier,tupleFields=[dict(name='Item1',managedOffset=0,bytes=12),dict(name='Item2',managedOffset=12,bytes=12)],
   constructorRegistration=ctor_entry,constructorProgram=ctor_program,formatterRegistration=registration,formatterContext=context,formatterProgram=forwarding,
   dangerousRegistration=dangerous_registration,actualSourcePointerEqualsRegisteredEntry=actual==dangerous_registration['pointer'],
   actualRawSourceWindows=body['windows'],actualRawSourceProgram=raw_program,actualRawSourceTargetRva=actual-base,advance=advance),
  parentFieldAdmitted=False,collectionAdmitted=False,wholeOwnerAdmitted=False,openGenericOffsetsOrSizesUsed=False,
  evidenceBoundary=dict(exact='Exact constructed value21/128 and two ordinary nominal Vector3 arguments, own reciprocal Item1/Item2/constructor VARs, bounded normal direct constructor copying12+12, registered formatter ABI/context and complete28-byte tail, actual raw24 copy and all four independently proved Advance24 updates.',
   conditional='Actual matching ready closed formatter callback/MethodInfo, sufficiently buffered stable disjoint source/output/frame, ordinary unboxed ctor ABI witness and normal compatible Advance effects. The constructor is not invoked by this path; its adjustor stays opaque and unused. Finite float projection rejects nonfinite values.',
   unresolved=['collection count/constructor/Add/callback loop and actual enclosing fields','cold refill/failure effects','live selection or invocation','whole owner/physical EOF']))))
