"""Two exact enum source roles; no synthetic collection or width alias.

An actual ReadPackable<List<Enum>> request and an actual closed ordinary
UnmanagedFormatter<Enum> constructor request can independently supply the
original nominal enum carrier. The latter is a formatter registration input,
not a List request. Both require fresh typed usage bytes, exact definitions,
reciprocal selected instantiation and own non-byref value17 enum carrier with
its actual Int32 value__ field. This only binds native normalization inputs;
it admits neither a parent, constructor execution, callback nor wire width.
"""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read

LABEL='enumNominalRequests'
FORMATTER='MemoryPack.Formatters.UnmanagedFormatter`1'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _bind(image,enum_type,usage,*,enum_variant=None):
    from scripts.game_data.il2cpp.enum_source_variants import select
    variant=select(enum_variant)
    ctx=NativeReferenceContext(image);md=image.metadata
    need('actual-own-enum-with-'+('int32'if enum_variant is None else'byte')+'-value-field',type(enum_type)is str and enum_type in ctx.index.types
        and ctx.is_enum(enum_type)and ctx.field(enum_type+'::value__')[1:]==(variant['backingType'],16))
    validate_typed_usage_context(image,usage,label=LABEL);role=None;container=None
    if usage.get('typeName')=='MemoryPack.MemoryPackReader'and usage.get('methodName')=='ReadPackable':
        role='read-packable-enum-list';nominal='System.Collections.Generic.List`1<'+enum_type+'>'
        binding=bind_typed_read(image,usage,method_name='ReadPackable',argument=nominal,kind=21,reference=True)
        argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
        container=ContextSymbols(image).type(argument.type_pointer_va)
        need('exact-closed-list-container',container.get('definition',{}).get('name')=='System.Collections.Generic.List`1'
            and bytes.fromhex(container['rawHex'])[10:12]==b'\x15\x00'and len(container['classArguments'])==1)
        carrier,=container['classArguments']
    elif usage.get('typeName')==FORMATTER and usage.get('methodName')=='.ctor':
        role='nominal-unmanaged-formatter-constructor';owner=ctx.index.types[FORMATTER]
        methods=[m for m in md.methods_for(owner)if md.string(m.name_index)=='.ctor']
        need('one-own-ordinary-instance-constructor',len(methods)==1);method,=methods
        need('exact-own-noarg-void-constructor-methodspec',usage['tag']==6 and usage['methodSpec'][0]==method.index
            and usage['methodSpec'][1]>=0 and usage['methodSpec'][2]==-1
            and usage['classArguments']==[enum_type]and usage['methodArguments']==[]
            and not method.flags&16 and not md.parameters_for(method)and ctx.type_name(method.return_type)=='void')
        argument,=image.instantiations.resolve(usage['methodSpec'][1]).arguments
        carrier=ContextSymbols(image).type(argument.type_pointer_va)
        binding=dict(kind='exact-nominal-formatter-constructor-input',typeName=FORMATTER,enumType=enum_type,
            constructorMethodDefinition=method.index,methodSpec=usage['methodSpec'],classArguments=[enum_type],
            sourceInstructionRva=usage['instructionRva'],parentOrWireGrammarAdmitted=False)
    else:raise ValueError(LABEL+'.unsupported-actual-source-role')
    pointer=carrier['typePointerVa'];pointer=int(pointer,16)if type(pointer)is str else pointer
    td=ctx.index.types[enum_type];raw=image.pe.bytes_at_va(pointer,16)
    need('same-exact-own-nonbyref-value17-type-carrier',pointer==ctx.type_pointer(td.byval_type_index)
        and carrier['name']==enum_type and carrier['rawHex']==raw.hex().upper()
        and raw[10:12]==b'\x11\x80'and int.from_bytes(raw[:8],'little')==td.index)
    return dict(role=role,binding=binding,enumCarrier=carrier,containerCarrier=container,
        enumTypePointerVa=pointer,sourceExecutionOrCallbackProved=False)


def bind(image,enum_type,usage):
    """Existing exact Int32 enum request roles; byte source opt-in is private."""
    return _bind(image,enum_type,usage)
