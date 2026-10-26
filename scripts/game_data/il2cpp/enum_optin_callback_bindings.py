"""Actual class-only dictionary key requests joined to conditional callbacks.

The dictionary's own source must still bind its key provider/slot5 MethodInfo
and complete dispatcher to this capability. This check supplies only the
fresh exact nominal key carrier; it creates neither a List request nor a
claim about actual runtime provider selection.
"""
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols

LABEL='enumOptinCallbackBindings'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def bind_dictionary_key(image,pins,capability,*,typed_request,enum_type):
    ctx=NativeReferenceContext(image);md=image.metadata
    need('same-own-conditional-callback',capability.get('schema')=='endfield.enum-nominal-callback-sources.v1'
        and capability.get('status')=='validated-conditional-callback'and capability.get('nativeInputs')==pins
        and capability.get('typeName')==enum_type and type(capability.get('wireBytes'))is int
        and capability['wireBytes']==4 and capability.get('callbackSlot')==5
        and capability.get('readerByref')is True and capability.get('outputByref')is True
        and capability.get('parentOrCollectionGrammarAdmitted')is False
        and capability.get('actualRuntimeSelectionObserved')is False)
    need('own-int32-nominal-enum',enum_type in ctx.index.types and ctx.is_enum(enum_type)
        and ctx.field(enum_type+'::value__')[1:]==('int',16))
    validate_typed_usage_context(image,typed_request,label=LABEL)
    owner=ctx.index.types['Beyond.SerializeFieldDictionary`2']
    methods=[m for m in md.methods_for(owner)if md.string(m.name_index)=='DeserializeV2']
    need('one-own-static-DeserializeV2',len(methods)==1);method,=methods
    need('actual-class-only-dictionary-key-request',typed_request.get('tag')==6
        and typed_request.get('typeName')=='Beyond.SerializeFieldDictionary`2'
        and typed_request.get('methodName')=='DeserializeV2'
        and typed_request['methodSpec'][0]==method.index and typed_request['methodSpec'][1]>=0
        and typed_request['methodSpec'][2]==-1 and typed_request.get('methodArguments')==[]
        and len(typed_request.get('classArguments',[]))==2 and typed_request['classArguments'][0]==enum_type
        and method.flags&16)
    arguments=image.instantiations.resolve(typed_request['methodSpec'][1]).arguments
    need('own-closed-key-and-value-arguments',len(arguments)==2)
    argument=arguments[0];carrier=ContextSymbols(image).type(argument.type_pointer_va)
    td=ctx.index.types[enum_type];raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('same-own-nonbyref-value17-key-carrier',argument.type_pointer_va==ctx.type_pointer(td.byval_type_index)
        and raw[10:12]==b'\x11\x80'and int.from_bytes(raw[:8],'little')==td.index
        and carrier['name']==enum_type and carrier['rawHex']==raw.hex().upper()
        and capability.get('typeDefinition')==td.index)
    return dict(typeName=enum_type,typeDefinition=td.index,argumentIndex=0,carrier=carrier,
        actualTypedRequest=typed_request,callbackCapability=capability,
        actualProviderMethodInfoAndDispatcherJoinRequired=True,actualRuntimeSelectionObserved=False,
        parentOrCollectionGrammarAdmitted=False)
