"""Exact named SmartTarget managed40 setter and actual Reader source joins.

The nominal domain owns its padded layout, original adapter and wire grammar.
This component owns only the parent destination, complete forty-byte transfer,
normal setter frame and the independently disabled collector at lane eight.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Core.SmartTargetSelectSetting'
LABEL='generatedSmartTargetField'


def need(key,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:700])


def setter_program(regions,entry,*,getter,field,barrier,path_factory=None):
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-owned-targets',all(type(v)is int and v>0 for v in(getter,barrier))and type(field)is int and field>=16)
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0')
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    edge=_nonnull(g);null=edge['nullTargetVa'];normal=edge['normalTargetVa']
    null_bytes=bytes(g.bytes.get(null+i,0)for i in range(6))
    g.take('0f1003',_displacement('488d48',field+8),'0f104b10',
        _displacement('0f1140',field),'f20f104320',_displacement('0f1148',field+16),
        _displacement('f20f1140',field+32),'4883c420','5b')
    need('same-actual-disabled-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,managedBytes=40,storedBytes=40,fieldOffset=field,
        sourceSlices=[[0,16],[16,16],[32,8]],referenceLaneOffsets=[8,24,32],barrierReferenceLaneOffset=8,
        incomingValueSource='rdx preserved in rbx',getterReceiver='incoming rcx with zero edx',
        wholeInputBitsStoredUnchanged=True,entryRspRestored=True,nonvolatileRegistersRestored=['rbx'],
        normalReturnViaBarrier=True,ownedNullExit=dict(instructionVa=null,bytes=null_bytes.hex().upper(),normalEntryVa=normal),
        disabledCollectorRequired=True,childGrammarAdmitted=False)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_smart_target_value_sources import layout
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('exact-nominal-parent-field',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    nominal=dict(layout(image,ctx),typeDefinition=ctx.index.types[TYPE].index);need('own-managed-layout',nominal['managedBytes']==40 and
        nominal['referenceLaneOffsets']==[8,24,32]and nominal['paddingByteRanges']==[[4,8],[20,24]])
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],LABEL+'.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method)
    raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    getter=pointer.methods(image,wrapper)['get___instance']
    getter_proof=members._coherent_getter(image,ctx,wrapper,getter,getter_cache,barrier=image.pe.image_base+barrier)
    body=members._body(image,image.method_pointer_va(method))
    program=setter_program(body['regions'],body['pointer'],getter=image.method_pointer_va(getter),field=offset,barrier=image.pe.image_base+barrier)
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=40,
        managedValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile='cached-getter-setter',
        program=program,getter=getter_proof,incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def read_source(image,pins,*,context,source_target):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_smart_target_value_transfer import derive
    need('exact-current-hidden-context',type(context)is dict and context.get('fullTypeName')==TYPE and
        context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'and
        context.get('register')=='r8'and context.get('typeKind')==17)
    usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.ReadValue')
    need('same-current-raw-context',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    proof=derive(image,pins,typed_request=usage,source_target=source_target)
    need('independent-actual-managed40-source',proof['nativeInputs']==pins and proof['typeName']==TYPE and
        proof['managedBytes']==40 and proof['resultAbi']=='hidden-local'and proof['actualSourceProved']is True and
        proof['sourceTargetRva']==source_target-image.pe.image_base and proof['readerMethodDefinition']==context['methodSpec'][0]and
        proof['referenceLaneOffsets']==[8,24,32]and proof['wireGrammarAdmitted']is False)
    return proof
