"""Fresh finite Int32 vector layouts; no wire or parent source admission.

The integer vectors are distinct from Unity's Single vectors. Complete owned
fields, exact ordinary value carriers, selected boxed/native sizes and direct
normal unboxed named getter entry programs are checked independently. No
invocation, adjustor, enclosing setter/caller/frame or collection codec follows.
"""
import json

from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

FIELDS={'UnityEngine.Vector2Int':('m_X','m_Y'),'UnityEngine.Vector3Int':('m_X','m_Y','m_Z')}


def need(key,expected,actual):scalar.need('storyIntegerVectorLayout',key,expected,actual)


def require_carrier(raw,definition):
    need('complete-literal-carrier',True,isinstance(raw,bytes)and len(raw)==16)
    need('ordinary-nominal-value-carrier',(bytes.fromhex('1180'),definition),
        (raw[10:12],int.from_bytes(raw[:8],'little')))


def getter_program(regions,entry,*,managed_offset):
    need('literal-Int32-getter-lane',True,type(managed_offset)is int and managed_offset in(0,4,8))
    g=BytesPath(regions,entry)
    g.take('6690','8b01'if managed_offset==0 else'8b41'+bytes((managed_offset,)).hex(),'c3')
    return dict(selectedBytes=g.seen,managedOffset=managed_offset,readBytes=4,resultRegister='eax',
        inputRegister='unboxed incoming rcx',normalReturn=True,stackUntouched=True,
        physicalExtentProved=False,runtimeInvocationObserved=False)


def derive_layout(image,*,type_pointer):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    need('literal-selected-type-pointer',True,type(type_pointer)is int and type_pointer>image.pe.image_base)
    ctx=NativeReferenceContext(image);md=image.metadata;symbol=ContextSymbols(image).type(type_pointer)
    typename=symbol['name'];need('finite-nominal-selection',True,typename in FIELDS)
    td=ctx.index.types[typename];raw=image.pe.bytes_at_va(type_pointer,16);require_carrier(raw,td.index)
    need('nongeneric-owned-value',(True,False,'System.ValueType',-1),
        (ctx.is_value_type(typename),ctx.is_enum(typename),ctx.parent(typename),td.generic_container_index))
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    names=FIELDS[typename];width=4*len(names)
    need('complete-declared-fields',list(names),[md.string(f.name_index)for f in fields])
    layout=[]
    for index,field in enumerate(fields):
        raw_field=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
        need('ordinary-Int32-field',bytes.fromhex('0880'),raw_field[10:12])
        value=ctx.field(typename+'::'+names[index]);need('owned-Int32-field-slot',(typename,'int',16+4*index),value)
        layout.append(dict(name=names[index],declaredType='int',boxedOffset=value[2],managedOffset=value[2]-16,rawKind=8))
    need('bounded-size-table-slot',True,0<=td.index<image.registration['typeDefinitionsSizesCount'])
    pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
    need('exact-boxed-and-native-size',(16+width,width),(image.pe.u32_at_va(pointer),image.pe.u32_at_va(pointer+4)))
    getters={}
    for index,axis in enumerate('xyz'[:len(names)]):
        getter,=[m for m in md.methods_for(td)if md.string(m.name_index)=='get_'+axis]
        need('named-instance-getter-ABI',(0,0,'int'),(getter.flags&16,getter.parameter_count,ctx.type_name(getter.return_type)))
        need('ordinary-getter-result',bytes.fromhex('0880'),image.pe.bytes_at_va(ctx.type_pointer(getter.return_type),16)[10:12])
        entry=image.method_pointer_va(getter)
        getters[axis]=dict(method=[getter.index,typename,'get_'+axis,entry-image.pe.image_base],
            normalUnboxedEntry=getter_program([(entry,image.pe.bytes_at_va(entry,5 if index==0 else 6))],entry,managed_offset=4*index))
    return json.loads(json.dumps(dict(schema='endfield.story-integer-vector-layout.v1',typeName=typename,
        managedBytes=width,referenceLaneOffsets=[],paddingByteRanges=[],fieldCount=len(names),fields=layout,
        selectedCarrier=symbol,normalUnboxedGetters=getters,wireGrammarAdmitted=False,
        parentFieldAdmitted=False,collectionAdmitted=False,constructorInvocationObserved=False,
        evidenceBoundary=__doc__)))
