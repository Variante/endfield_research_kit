"""Ordinary native type/ABI gate private to the snapshot proof domain."""
def _require(value, check, expected, actual):
    if not value:
        raise ValueError(f'{check}: expected={expected!r} actual={actual!r}')

PRIMITIVE_KINDS = {'void': 0x01, 'bool': 0x02, 'int': 0x08, 'float': 0x0c, 'double': 0x0d}


def require_ordinary_pointer(selected, pointer, actual, expected, role, *, reference_kind=None):
    raw=selected.image.pe.bytes_at_va(pointer,16)
    _require(len(raw)==16,'ordinary-abi-record', 'exact native type record',len(raw))
    _require(actual==expected,'ordinary-abi-name', [role,expected],[role,actual])
    kind,flags=raw[10],raw[11]
    _require(flags&0x7f==0,'ordinary-abi-flags', [role,'no byref/pinned/modifiers; value marker allowed'],[role,hex(flags)])
    if expected in PRIMITIVE_KINDS:
        _require(kind==PRIMITIVE_KINDS[expected],'ordinary-abi-primitive-kind',[role,hex(PRIMITIVE_KINDS[expected])],[role,hex(kind)])
    else:
        allowed=(reference_kind,) if reference_kind is not None else (0x12,0x15)
        _require(kind in allowed and not flags&0x80 and not selected.is_value_type(expected),
                 'ordinary-abi-reference-kind',[role,'ordinary named class/generic reference',allowed],[role,hex(kind),hex(flags)])
    return {'role':role,'type':actual,'kind':hex(kind),'flags':hex(flags)}


def require_ordinary_type(selected, type_index, expected, role, *, reference_kind=None):
    return require_ordinary_pointer(selected, selected.type_pointer(type_index),
        selected.type_name(type_index), expected, role, reference_kind=reference_kind)


def require_ordinary_signature(selected, method, parameters, result, role):
    meta=selected.image.metadata
    arguments=meta.parameters_for(method)
    _require(len(arguments)==len(parameters),'ordinary-abi-parameter-count',[role,len(parameters)],[role,len(arguments)])
    checked=[require_ordinary_type(selected,method.return_type,result,role+'.return')]
    checked.extend(require_ordinary_type(selected,arg.type_index,name,role+f'.arg{n}')
                   for n,(arg,name) in enumerate(zip(arguments,parameters)))
    return checked


def require_ordinary_field(selected, qualified, expected, role):
    owner, separator, name = qualified.partition('::')
    _require(bool(separator) and owner in selected.index.types,
             'ordinary-abi-field-owner', 'named selected owner', qualified)
    td = selected.index.types[owner]
    fields = [f for f in selected.image.metadata.fields_for(td)
              if selected.image.metadata.string(f.name_index) == name]
    _require(len(fields) == 1, 'ordinary-abi-field-count', 1, len(fields))
    return require_ordinary_type(selected, fields[0].type_index, expected, role)


def require_ordinary_value_type(selected, type_index, expected, role):
    raw=selected.image.pe.bytes_at_va(selected.type_pointer(type_index),16)
    _require(len(raw)==16, 'ordinary-abi-record', 'exact native type record', len(raw))
    actual=selected.type_name(type_index)
    _require(actual==expected and raw[10]==0x11 and raw[11]&0x7f==0
             and selected.is_value_type(expected), 'ordinary-abi-value-record',
             [role,expected,'ordinary named value type'], [role,actual,raw[10:12].hex()])
    return {'role':role,'type':actual,'kind':hex(raw[10]),'flags':hex(raw[11])}


def require_ordinary_type_var(selected, type_index, owner_index, ordinal, role):
    from scripts.game_data.il2cpp.context import type_parameter_owner
    raw=selected.image.pe.bytes_at_va(selected.type_pointer(type_index),16)
    _require(len(raw)==16 and raw[10]==0x13 and raw[11]==0,
             'ordinary-abi-type-var', [role,'ordinary type VAR'], raw.hex())
    owner=type_parameter_owner(selected.image.metadata.buf,int.from_bytes(raw[:8],'little'),
        [td.generic_container_index for td in selected.image.metadata.types],source=role)
    _require(owner['typeIndex']==owner_index and owner['ordinal']==ordinal,
             'ordinary-abi-type-var-owner',[role,owner_index,ordinal],owner)
    return {'role':role,'kind':'0x13','flags':'0x0','ownerTypeIndex':owner_index,'ordinal':ordinal}


def require_ordinary_int32_enum(selected,type_index,expected,role):
    """A byvalue enum lane needs its sole ordinary signed-Int32 storage field."""
    proof=require_ordinary_value_type(selected,type_index,expected,role)
    _require(selected.is_enum(expected),'ordinary-abi-enum-parent',[role,'selected System.Enum parent'],expected)
    td=selected.index.types.get(expected)
    _require(td is not None,'ordinary-abi-enum-owner','selected named enum definition',expected)
    fields=[field for field in selected.image.metadata.fields_for(td) if not selected.field_attributes(field.type_index)&0x10]
    _require(len(fields)==1 and selected.image.metadata.string(fields[0].name_index)=='value__',
             'ordinary-abi-enum-storage',[role,'sole instance value__'],len(fields))
    require_ordinary_type(selected,fields[0].type_index,'int',role+'.underlying')
    _require(selected.field(expected+'::value__')==(expected,'int',16),'ordinary-abi-enum-field-layout',
             [role,expected,'int',16],selected.field(expected+'::value__'))
    return {**proof,'underlyingPrimitive':'int','underlyingWidthBytes':4,'byvalueEnumLane':True}


def require_ordinary_double_array(selected,type_index,role):
    from scripts.game_data.il2cpp.protocol import runtime_type_name
    proof=require_ordinary_type(selected,type_index,'double[]',role,reference_kind=0x1d)
    raw=selected.image.pe.bytes_at_va(selected.type_pointer(type_index),16);element=int.from_bytes(raw[:8],'little')
    require_ordinary_pointer(selected,element,runtime_type_name(selected.image.pe,selected.image.metadata,element),'double',role+'.element')
    return {**proof,'elementPrimitive':'double','elementWidthBytes':8}
