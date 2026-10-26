"""Check typed two-reference handle initialization and manager publication."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_extent
from scripts.game_data.il2cpp.owned_consumer_instructions import read_owned_consumer_instructions
from scripts.game_data.il2cpp.reference_handle_program import check_handle_reference_program


def check_reference_handle_flow(index, body, spec):
    if (not isinstance(spec,dict) or set(spec)!={'constructorType','field','playMethod'}
            or any(not isinstance(value,str) or not value for value in spec.values())):
        raise ValueError('referenceHandleFlow.named-constructor-field-play')
    image=index.image;metadata=image.metadata;context=NativeReferenceContext(image)
    def declaration(selected):
        rows=[row for row in index.names_by_pointer.get(selected.pointer,()) if row['type']+'.'+row['method']==selected.symbol]
        if len(rows)!=1:raise ValueError('referenceHandleFlow.unique-method')
        method=metadata.methods[rows[0]['methodIndex']];owner=metadata.types[method.declaring_type]
        name=metadata.type_full_name(owner)
        if (method.flags&0x10 or method.generic_container_index>=0 or owner.generic_container_index>=0
                or context.is_value_type(name) or len(image.named_type_definitions.get(name,()))!=1
                or context.type_name(method.return_type)!='void' or image.method_pointer_va(method)!=selected.pointer):
            raise ValueError('referenceHandleFlow.reference-instance-void-method')
        context.require_ordinary_kind(method.return_type,1)
        return name,list(metadata.parameters_for(method))
    owner,parameters=declaration(body)
    if len(parameters)!=2:raise ValueError('referenceHandleFlow.two-incoming-references')
    types=[context.type_name(parameter.type_index) for parameter in parameters]
    for parameter in parameters:
        raw=image.pe.bytes_at_va(context.type_pointer(parameter.type_index),16)
        if len(raw)!=16 or raw[10] not in (0x12,0x15):raise ValueError('referenceHandleFlow.reference-parameter-kind')
        context.require_ordinary_kind(parameter.type_index,raw[10])
        if raw[10]==0x15:closed_generic_reference_extent(context,parameter.type_index)
        elif (context.is_value_type(context.type_name(parameter.type_index))
                or len(image.named_type_definitions.get(context.type_name(parameter.type_index),()))!=1):
            raise ValueError('referenceHandleFlow.reference-parameter-type')
    constructor=index.body(spec['constructorType'],'.ctor',parameters=[*types,owner])
    constructor_owner,constructor_parameters=declaration(constructor)
    if constructor_owner!=spec['constructorType'] or len(constructor_parameters)!=3:
        raise ValueError('referenceHandleFlow.constructor-parameters')
    if [context.type_name(p.type_index) for p in constructor_parameters]!=[*types,owner]:
        raise ValueError('referenceHandleFlow.constructor-reference-types')
    for source,target in zip(parameters,constructor_parameters[:2]):
        raw=image.pe.bytes_at_va(context.type_pointer(source.type_index),16)
        context.require_ordinary_kind(target.type_index,raw[10])
        other=image.pe.bytes_at_va(context.type_pointer(target.type_index),16)
        if len(other)!=16 or raw[:8]!=other[:8]:raise ValueError('referenceHandleFlow.same-native-parameter-type')
        if raw[10]==0x15:closed_generic_reference_extent(context,target.type_index)
    context.require_ordinary_kind(constructor_parameters[2].type_index,0x12)
    field_owner,field_type,offset=context.field(spec['field'])
    if (field_owner,field_type)!=(owner,constructor_owner):raise ValueError('referenceHandleFlow.manager-handle-field')
    play_owner,separator,play_name=spec['playMethod'].rpartition('.')
    if not separator or play_owner!=owner:raise ValueError('referenceHandleFlow.manager-play-owner')
    play=index.body(play_owner,play_name,parameters=[])
    declared_owner,play_parameters=declaration(play)
    if declared_owner!=owner or play_parameters:raise ValueError('referenceHandleFlow.no-argument-manager-play')
    rows,ranges,_=read_owned_consumer_instructions(image.mapper,image.pe,body.pointer)
    return check_handle_reference_program(rows,entry=body.pointer,owned_ranges=ranges,
        constructor=constructor.pointer,play=play.pointer,field_offset=offset)
