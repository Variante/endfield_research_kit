"""Exact named InitialParam hidden24 stores, independent of its MC7 wrapper.

The actual raw source and nominal padded24 layout have their own owner. This
module proves only current named setter ABI/field ownership, the whole16+8
incoming pointer copy and complete direct-holder frame. No other type/width,
reference-lane adapter or normalized Boolean interpretation is admitted.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.View.CameraControlStateInitialParam'
LABEL='generatedCameraInitialValue'

def need(k,c,detail=None):
 if not c:raise ValueError(LABEL+'.'+k+':'+str(detail)[:700])

def setter_program(regions,entry,*,holder,field):
 from scripts.game_data.memorypack.generated_member_sources import _displacement
 need('finite-direct-holder-field',type(holder)is int and holder==16 and type(field)is int and 16<=field<2**31)
 g=BytesPath(regions,entry);g.take('4883ec28',_displacement('488b41',holder),'4885c0')
 head=bytes(g.bytes.get(g.at+i,0)for i in range(2));near=head[0]==15;code=head[1]if near else head[0]
 need('literal-current-null-edge',code in(132,133)if near else code in(116,117))
 at=g.at;target=g.relative(('0f'if near else'')+format(code,'02x'),4 if near else 1);fall=g.at
 null=target if code&15==4 else fall;normal=fall if code&15==4 else target
 need('owned-nonreturning-null-call',g.bytes.get(null)==232 and g.bytes.get(null+5)==204);g.at=normal
 g.take('0f1002','f20f104a10',_displacement('0f1140',field),_displacement('f20f1148',field+16),'4883c428','c3')
 return dict(selectedBytes=g.seen,holderOffset=holder,fieldOffset=field,storedBytes=24,
     incomingValuePointer='rdx',destinationRegister='rax',sourceSlices=[[0,16],[16,8]],
     nullGuardInstructionVa=at,ownedNullExitVa=null,completeSourceBitsStoredUnchanged=True,
     normalFrameAndReturn=True,entryRspRestored=True,allIntegerNonvolatilesUntouched=True,
     referenceLaneOffsets=[],boolBytesNormalized=False,paddingBitsPreserved=True,
     condition='Fresh exact named InitialParam ordinary value ABI/field and compatible nonnull Original holder; disjoint stable incoming pointer24. Every source byte including padding and raw Boolean bytes reaches its own field unchanged; actual source/wire/frame composition remains separate.')

def derive_setter(image,pins,member,wrappers):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
 from scripts.game_data.memorypack import generated_member_sources as members,skill_camera_initial_raw_sources as source,scalar_param_native as scalar
 need('explicit-selected-native-inputs',isinstance(pins,dict)and bool(pins));_publication_gate(image,pins)
 ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member);base=image.pe.image_base;md=image.metadata
 need('exact-nominal-current-member',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
 nominal=source.layout(image,ctx);need('own-layout-machine24',nominal['typeName']==TYPE and nominal['managedBytes']==24 and nominal['referenceLaneOffsets']==[])
 scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],LABEL+'.setter')
 need('ordinary-nongeneric-setter',method.generic_container_index<0)
 parameter,=md.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
 need('same-ordinary-owned-nominal-parameter',raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
 holder_name,holder=field(wrapper.name,{'___instance','__instance','__realInstance'})
 need('same-current-nominal-direct-holder',holder==(wrapper.name,wrapper.wrapped_type,16),holder)
 owned,=[f for f in md.fields_for(md.types[wrapper.type_definition])if wrapper.name+'::'+md.string(f.name_index)==holder_name]
 scalar.ordinary(image,ctx.type_pointer(owned.type_index),18,LABEL+'.holder',reference=True)
 body=members._body(image,image.method_pointer_va(method));parsed=setter_program(body['regions'],body['pointer'],holder=16,field=offset)
 _publication_gate(image,pins)
 return dict(method=[method.index,wrapper.name,md.string(method.name_index),body['pointer']-base],member=member.row(),targetField=target,
     fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=24,nominalValueLayout=nominal,
     sourceFamily=body['family'],codeWindows=body['windows'],profile='direct-base-holder-setter',program=parsed,getter=None,
     incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False,
     evidenceBoundary='Exact current InitialParam padded24 named field, ordinary kind17 parameter and whole hidden-pointer16+8 direct store/complete frame. Actual raw24 source is independently composed; no MC7 wrapper or provider/default behavior is borrowed.')
