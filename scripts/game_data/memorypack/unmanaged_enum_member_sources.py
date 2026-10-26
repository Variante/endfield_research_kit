"""Direct nominal enum ReadUnmanaged source, never a formatter callback claim.

The actual parent supplies a closed MethodInfo and a direct E8. Its exact enum
definition/backing and reciprocal method MVAR are proved separately from the
complete raw DWORD/EAX source. Registration is provenance; different actual
and registered pointers are never treated as aliases. Provider, callback,
collection and enclosing field grammars remain outside this component.
"""
import json
import struct

LABEL='unmanagedEnumMember'
SCHEMA='endfield.unmanaged-enum-member-source.v1'


def need(check,condition):
 if not condition:raise ValueError(LABEL+'.'+check)


def require_request(usage,*,enum_type,type_definition,argument_raw,backing,method_identity,container,parameter_owner,return_raw,registration,canonical_absent=False):
 """Pure joins over independently collected metadata; not native admission."""
 need('literal-enum-and-definition',type(enum_type)is str and bool(enum_type)and type(type_definition)is int and type_definition>=0)
 need('direct-closed-enum-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),
  usage.get('classArguments'),usage.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[enum_type]))
 instruction=bytes.fromhex(usage.get('instructionHex',''))
 need('actual-RDX-MethodInfo-load',len(instruction)==7 and instruction[:3]==bytes.fromhex('488b15')
  and type(usage.get('instructionRva'))is int and usage['instructionRva']>=0)
 spec=usage.get('methodSpec');need('literal-closed-spec',isinstance(spec,(tuple,list))and len(spec)==3
  and all(type(n)is int for n in spec)and spec[0]>=0 and spec[1]==-1 and spec[2]>=0
  and type(usage.get('methodSpecIndex'))is int and usage['methodSpecIndex']>=0)
 need('ordinary-own-enum-argument',len(argument_raw)==16 and argument_raw[10:12]==bytes((17,128))
  and int.from_bytes(argument_raw[:8],'little')==type_definition)
 need('own-int32-or-uint32-backing',backing in((enum_type,'int',16),(enum_type,'uint',16)))
 need('owned-instance-Reader-method',method_identity==(spec[0],'MemoryPack.MemoryPackReader','ReadUnmanaged',0,0))
 need('reciprocal-sole-MVAR',len(container)==4 and all(type(n)is int for n in container)
  and tuple(container[:3])==(spec[0],1,1)and container[3]>=0
  and parameter_owner.get('methodIndex')==spec[0]and type(parameter_owner.get('ordinal'))is int and parameter_owner['ordinal']==0
  and len(return_raw)==16 and return_raw[10:12]==bytes((30,0))and int.from_bytes(return_raw[:8],'little')==container[3])
 need('literal-canonical-absence',type(canonical_absent)is bool)
 if canonical_absent:need('explicit-no-canonical-row',registration is None)
 else:need('exact-closed-registration-spec',isinstance(registration,dict)and type(usage.get('methodSpecIndex'))is int
  and usage['methodSpecIndex']==registration.get('methodSpecIndex')and registration.get('methodDefinitionIndices')==[spec[0]])
 return dict(typeName=enum_type,typeDefinition=type_definition,readerMethodDefinition=spec[0],backingType=backing[1],
  wireBytes=4,resultRegister='eax',sourceMethod='ReadUnmanaged',formatterCallbackSelectionAdmitted=False)


def bind_actual_call(usage,instruction,*,source_target,base):
 """The actual caller's E8 remains distinct from any registration pointer."""
 need('actual-source-instruction',isinstance(instruction,(tuple,list))and len(instruction)==2
  and type(instruction[0])is int and instruction[0]>=0 and type(instruction[1])is str
  and type(base)is int and type(source_target)is int and source_target>base)
 raw=bytes.fromhex(instruction[1]);need('actual-source-E8',len(raw)==5 and raw[0]==232
  and instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==source_target-base)
 need('same-request-precedes-direct-call',type(usage.get('instructionRva'))is int
  and usage['instructionRva']<instruction[0])
 return dict(sourceInstruction=list(instruction),sourceTargetRva=source_target-base,canonicalPointerIdentityClaimed=False,
  incomingRequestAndReaderOriginsRequired=True,parentFieldAdmitted=False)


def derive(image,pins,*,typed_request,source_target,enum_type,source_instruction=None):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.context import method_parameter_owner
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 _publication_gate(image,pins);validate_typed_usage_context(image,typed_request,label=LABEL)
 base=image.pe.image_base;need('actual-selected-E8-target',type(source_target)is int and source_target>base)
 ctx=NativeReferenceContext(image);md=image.metadata;td=ctx.index.types[enum_type]
 need('owned-nongeneric-enum',ctx.is_enum(enum_type)and ctx.is_value_type(enum_type)
  and ctx.parent(enum_type)=='System.Enum'and td.generic_container_index<0)
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 need('sole-backing-field',len(fields)==1 and md.string(fields[0].name_index)=='value__')
 backing=ctx.field(enum_type+'::value__');need('four-byte-backing',backing[1]in('int','uint')and backing[2]==16)
 scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),8 if backing[1]=='int'else 9,LABEL+'.backing')
 argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
 scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.actualArgument')
 raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
 method=md.methods[typed_request['methodSpec'][0]]
 need('zero-declared-parameters',not list(md.parameters_for(method)))
 section=md.sections['genericContainers'];at=section.offset+method.generic_container_index*16
 need('bounded-generic-container',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
 container=struct.unpack_from('<iiii',md.buf,at)
 parameter=method_parameter_owner(md.buf,container[3],[m.generic_container_index for m in md.methods],source=LABEL)
 returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
 entries=GenericEntries(image);observed=entries.observe(method.index,[],[enum_type]);absent=not observed
 registered=None if absent else entries.resolve(method.index,[],[enum_type])
 identity=require_request(typed_request,enum_type=enum_type,type_definition=td.index,argument_raw=raw,backing=backing,
  method_identity=(method.index,image.type_name(method.declaring_type),md.string(method.name_index),method.flags&16,method.parameter_count),
  container=container,parameter_owner=parameter,return_raw=returned,registration=registered,canonical_absent=absent)
 actual_call=None
 if absent or source_instruction is not None:
  actual_call=bind_actual_call(typed_request,source_instruction,source_target=source_target,base=base)
  image.check_instruction_windows([source_instruction],label=LABEL+'.actualParentE8')
 offsets=scalar.reader_offsets(image,LABEL);record=vector_recorder(image)
 actual=record(source_target-base);scalar.integer_source(image,actual,offsets,LABEL+'.actualRaw4',width=4)
 canonical=None if absent else actual if registered['pointer']==source_target else record(registered['pointer']-base)
 if canonical is not None and canonical is not actual:scalar.integer_source(image,canonical,offsets,LABEL+'.registeredRaw4',width=4)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-direct-enum-source',nativeInputs=pins,
  **identity,actualTargetRva=source_target-base,registeredTargetRva=None if absent else registered['pointer']-base,
  actualEqualsRegisteredPointer=None if absent else registered['pointer']==source_target,pointerAliasClaimed=False,
  canonicalRegistrationAbsent=absent,canonicalPointerClaimed=not absent,
  actualSourceProved=True,completeActualBufferedProgramProved=True,allFourReaderUpdatesProved=True,
  entryRspRestored=True,allNonvolatilesRestored=True,
  parentFieldAdmitted=False,containerAdmitted=False,wholeOwnerAdmitted=False,
  proof=dict(typedRequest=typed_request,backing=backing,argumentRawHex=raw.hex().upper(),returnRawHex=returned.hex().upper(),
   genericContainer=container,returnParameter=parameter,registration=registered,canonicalRegistrationObservations=observed,
   actualCaller=actual_call,actualSource=actual,registeredSource=canonical,readerOffsets=offsets),
  evidenceBoundary=dict(exact='Own closed enum definition/int32 or uint32 backing, reciprocal ReadUnmanaged return and complete actual raw DWORD/EAX program; exact canonical registration/source only when independently present.',
   conditional=__doc__+' Ready exact MethodInfo and sufficient coherent disjoint buffered storage; normal selected direct invocation.',
   structuralOnly='All raw enum bits retained without symbolic membership restriction.',
   unresolved=(['no canonical registration row observed; no canonical pointer identity inferred']if absent else[])+
    ['parent source-to-field/local/frame','formatter/provider/callback selection','collections','refill/errors','whole owner/physical EOF']))))
