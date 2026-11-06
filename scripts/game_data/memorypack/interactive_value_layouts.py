"""Finite Interactive value layouts proved by their own compiled accessors.

Closed Optional fields use no open generic offset or size. The selected
generated wrapper's typed whole-value getter/setter, zero factories and both
named subfield stores independently fix the actual representation. None of
these transfers supplies a serialized grammar or selects a live formatter.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

OPTIONAL='Beyond.Optional`1<'
MOUNT='Beyond.Gameplay.View.NameMountPointDef'
RAW={'float':('float',8,4),'bool':('bool',2,1),
     'Beyond.Gameplay.Core.AoiRadiusEnum':('int32',8,4),
     'Beyond.Gameplay.Core.FactionIndex':('int32',8,4)}
REFERENCES=('string','string[]','Beyond.Gameplay.Core.GameplayTag[]',MOUNT+'[]')
TYPES={OPTIONAL+name+'>' for name in (*RAW,*REFERENCES)}|{MOUNT}


def need(check,condition,detail=''):
    if not condition:raise ValueError('interactiveValueLayout.'+check+':'+str(detail)[:1000])


def transfer_program(regions,entry,*,operation,width,barrier=None):
    need('finite-complete-value-transfer',operation in('GetValue','.ctor','CreateInstance','set____instance')
         and type(width)is int and width in(2,8,16))
    g=BytesPath(regions,entry)
    if operation=='GetValue':
        g.take({2:'0fb74110c3',8:'488b4110c3',16:'0f104210488bc10f1101c3'}[width])
    elif operation in('.ctor','CreateInstance'):
        g.take({2:'33c066894110c3',8:'33c048894110c3',16:'0f57c00f114110c3'}[width])
    elif width in(2,8):g.take('66895110c3'if width==2 else'48895110c3')
    else:
        need('actual-reference-lane-barrier',type(barrier)is int and barrier>0)
        g.take('0f10020f1141104883c118');need('whole-setter-actual-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,operation=operation,managedBytes=width,
        wrapperValueOffset=16,wholeRepresentationTransferred=True,
        frameAndNonvolatilesUnchanged=True,physicalFunctionExtentProved=False,
        wireGrammarAdmitted=False,normalReturnConditional=operation=='set____instance'and width==16)


def field_program(regions,entry,*,mode,offset,barrier=None):
    need('finite-own-wrapper-field',mode in('bool','int32','float','reference')
         and type(offset)is int and 16<=offset<128)
    g=BytesPath(regions,entry);d=bytes((offset,)).hex()
    g.take({'bool':'8851','int32':'8951','float':'f30f1149','reference':'488951'}[mode]+d)
    if mode=='reference':
        need('actual-field-reference-barrier',type(barrier)is int and barrier>0)
        g.take('4883c1'+d);need('same-field-barrier',g.relative('e9')==barrier)
    else:g.take('c3')
    return dict(selectedBytes=g.seen,mode=mode,wrapperOffset=offset,
        bytes={'bool':1,'int32':4,'float':4,'reference':8}[mode],
        completeIncomingBitsStoredUnchanged=True,frameAndNonvolatilesUnchanged=True,
        boolNormalizationClaimed=False,wireGrammarAdmitted=False)


def derive(image,pins,type_name,*,barrier):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.reference_param_profile import _method_row
    _publication_gate(image,pins);need('finite-own-nominal',type_name in TYPES,type_name)
    import struct
    md=image.metadata;ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);base=image.pe.image_base
    choices=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
    # The wrapper inventory's convenience value flag does not classify closed
    # GENERICINSTs. The actual return/holder records below must prove VALUE.
    need('one-current-value-wrapper',len(choices)==1)
    wrapper=choices[0];methods=pointer.methods(image,wrapper)
    if type_name==MOUNT:
        value_type='string';width=16;value_offset=8;first='mountPoint';first_type='Beyond.Gameplay.MountPoint';first_mode='int32'
        second='name';original_kind=17
    else:
        value_type=type_name[len(OPTIONAL):-1];first='enabled';first_type='bool';first_mode='bool';second='value';original_kind=21
        _,width,value_offset=RAW[value_type]if value_type in RAW else('reference',16,8)
    second_mode=RAW[value_type][0]if value_type in RAW else'reference'
    need('exact-compiled-member-roster',[(m.name,m.declared_type)for m in wrapper.members]==[(first,first_type),(second,value_type)])
    getter=methods['GetValue'];scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,
        (type_name,original_kind,False),[],'interactiveValueLayout.GetValue')
    carrier=symbols.type(ctx.type_pointer(getter.return_type));raw=bytes.fromhex(carrier['rawHex'])
    need('ordinary-complete-value-carrier',raw[10:12]==bytes((original_kind,128)))
    nominal=carrier
    if type_name!=MOUNT:
        definition=ctx.index.types['Beyond.Optional`1'];decl=carrier['definition'];args=carrier['classArguments']
        declared_raw=bytes.fromhex(decl['rawHex'])
        need('same-owned-Optional-carrier',decl['name']=='Beyond.Optional`1'and len(args)==1 and args[0]['name']==value_type
             and declared_raw[10:12]==bytes((17,128))and int.from_bytes(declared_raw[:8],'little')==definition.index)
        section=md.sections['genericContainers'];at=section.offset+definition.generic_container_index*16
        need('owned-generic-container-bounds',definition.generic_container_index>=0
             and section.offset<=at<=section.offset+section.size-16)
        owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
        need('one-owned-Optional-class-parameter',(owner,count,is_method)==(definition.index,1,0))
        fields=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
        need('exact-Optional-declaration',len(fields)==2 and [md.string(f.name_index)for f in fields]==['enabled','value'])
        scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),2,'interactiveValueLayout.enabled')
        parameter=symbols.type(ctx.type_pointer(fields[1].type_index))
        parameter_raw=bytes.fromhex(parameter['rawHex'])
        need('value-is-owned-formal-zero',parameter['parameterOwner'].get('typeIndex')==definition.index
             and parameter['parameterOwner'].get('ordinal')==0 and parameter_raw[10]==19
             and parameter_raw[11]in(0,128)and int.from_bytes(parameter_raw[:8],'little')==start)
        nominal=dict(carrier=carrier,formalValue=parameter)
    else:
        need('actual-own-MountPoint-fields',ctx.field(MOUNT+'::mountPoint')==(MOUNT,first_type,16)
             and ctx.field(MOUNT+'::name')==(MOUNT,'string',24)and ctx.is_enum(first_type))
    for enum in ([first_type]if type_name==MOUNT else[value_type]if second_mode=='int32'else[]):
        td=ctx.index.types[enum];backing=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
        need('own-enum-Int32-backing',ctx.is_enum(enum)and len(backing)==1
             and md.string(backing[0].name_index)=='value__'and ctx.type_name(backing[0].type_index)=='int')
        scalar.ordinary(image,ctx.type_pointer(backing[0].type_index),8,'interactiveValueLayout.enumBacking')
    holders=[f for f in md.fields_for(md.types[wrapper.type_definition])
             if md.string(f.name_index)in('__instance','___instance','__realInstance')and not ctx.field_attributes(f.type_index)&16]
    need('one-own-value-holder',len(holders)==1)
    holder=holders[0];held=symbols.type(ctx.type_pointer(holder.type_index))
    need('same-closed-actual-holder',ctx.field(wrapper.name+'::'+md.string(holder.name_index))==(wrapper.name,type_name,16)
         and held['name']==carrier['name']and bytes.fromhex(held['rawHex'])[10:12]==raw[10:12]
         and bytes.fromhex(held['rawHex'])[:8]==raw[:8])
    proofs={}
    for name in ('GetValue','.ctor','CreateInstance','set____instance'):
        method=methods[name];parameters=[]if name!='set____instance'else[(type_name,original_kind,False)]
        scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,
            (type_name,original_kind,False)if name=='GetValue'else('void',1,False),parameters,'interactiveValueLayout.'+name)
        entry=image.method_pointer_va(method);body=image.pe.bytes_at_va(entry,32)
        program=transfer_program([(entry,body)],entry,operation=name,width=width,barrier=barrier)
        proofs[name]=dict(method=_method_row(image,method),program=program)
    fields=[]
    for name,declared,mode,offset in ((first,first_type,first_mode,0),(second,value_type,second_mode,value_offset)):
        member=next(m for m in wrapper.members if m.name==name);method=md.methods[member.method_index]
        parameter,=md.parameters_for(method);kind=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)[10]
        scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),
            [(declared,kind,mode=='reference')],'interactiveValueLayout.namedField')
        need('own-current-named-setter',md.string(method.name_index)=='set___'+name+'__')
        entry=image.method_pointer_va(method);body=image.pe.bytes_at_va(entry,32)
        program=field_program([(entry,body)],entry,mode=mode,offset=16+offset,barrier=barrier)
        fields.append(dict(fieldName=name,declaredType=declared,offset=offset,bytes=program['bytes'],method=_method_row(image,method),program=program))
    _publication_gate(image,pins)
    return dict(schema='endfield.interactive-value-layout.v1',nativeInputs=pins,typeName=type_name,
        wrapperName=wrapper.name,managedBytes=width,concreteTypeKind=original_kind,nominal=nominal,
        fields=fields,referenceLaneOffsets=[8]if width==16 else[],
        paddingByteRanges=([[1,3]]if width==8 else[[1,7]]if width==16 and first_mode=='bool'else[[4,4]]if width==16 else[]),
        proofs=proofs,openGenericOffsetsUsed=False,wholeValueBitsAndPaddingPreserved=True,
        wireGrammarAdmitted=False,runtimeFormatterSelectionProved=False,
        disabledCollectorRequired=width==16,actualBarrierTargetRva=barrier-base if width==16 else None,
        barrierEffectsProved=False)
