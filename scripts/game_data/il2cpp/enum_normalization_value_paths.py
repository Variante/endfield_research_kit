"""Exact kind17 normalization helper paths; no concrete enum body selection.

Inputs are an actual closed enum List read or the exact enum's own ordinary
UnmanagedFormatter constructor request, with the source role retained. The
constructor role creates no collection request or parent grammar admission.

These source programs keep the opaque class-return helpers and freshly read
class flag/element pointers explicit. An undecorated concrete enum type carrier
can establish the input kind and non-byref predicate from metadata. It does
not identify the runtime input's data slot: the stored TypeDefinition index
may undergo runtime index-to-record fixup. That writeback is not assumed here.
It also does not establish the class lookup return, the raw flag at class+312, the pointer
at class+64, an initialized placeholder class cell, interned generic contexts
or a formatter callback. Those are required joins, never Int32 width aliases.
Normal compatible class helpers, valid stable disjoint type/class/frame storage
and preserved Win64 nonvolatiles remain conditions. This component admits no
wire grammar, list counts, provider choice, enclosing parent or physical EOF.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='enumNormalizationValuePaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def class_flag_program(regions,entry,target,*,flag_set):
    """Complete direct kind17 arm; generic21 iteration stays outside scope."""
    need('literal-raw-flag-path',type(flag_set)is bool)
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','0f1f8000000000','807b0a11');g.branch('75',False,1)
    g.take('488b0b');g.call(target);g.take('f6803801000004');g.branch('75',flag_set,1)
    if flag_set:g.take('b001')
    else:g.take('807b0a15');g.branch('75',True,1);g.take('32c0')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,inputKind=17,firstQwordPassedUnchanged=True,
        classByteOffset=312,classByteMask=4,classFlagSet=flag_set,returnedLowByte=int(flag_set),
        classLookupIdentityProved=False,normalReturn=True,entryRspRestored=True)


def underlying_program(regions,entry,target,*,flag_set=True,self_element=False):
    """Complete non-byref kind17 arm, with raw class-read alternatives."""
    need('literal-underlying-path',type(flag_set)is bool and type(self_element)is bool and not(self_element and not flag_set))
    g=BytesPath(regions,entry);g.take('4053','4883ec20','80790a11','488bd9');g.branch('74',True,1)
    g.take('f7410800000020');g.branch('75',False,1);g.call(target)
    g.take('f6803801000004');g.branch('74',not flag_set,1)
    if flag_set:
        g.take('488bcb');g.call(target);g.take('48394040');g.branch('74',self_element,1)
        if self_element:g.take('33c0');g.jump('eb',1)
        else:
            g.take('488b4040','4883c020')
            g.take('4883c420','5b','c3')
            return dict(selectedBytes=g.seen,inputKind=17,inputByrefBitClear=True,classByteOffset=312,classByteMask=4,
                classFlagSet=True,freshClassLookupRepeated=True,elementPointerOffset=64,returnedAddress='fresh class.element pointer +32',
                underlyingKindOrClassIdentityProved=False,normalReturn=True,entryRspRestored=True)
    else:g.take('807b0a15');g.branch('74',False,1);g.take('488bc3')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,inputKind=17,inputByrefBitClear=True,classByteOffset=312,classByteMask=4,
        classFlagSet=flag_set,freshClassLookupRepeated=flag_set,elementPointerOffset=64,
        returnedAddress='zero'if self_element else'unchanged original type carrier',underlyingKindOrClassIdentityProved=False,
        normalReturn=True,entryRspRestored=True)


def derive(image,pins,*,enum_type,typed_request,predicate_target,underlying_target,enum_variant=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.enum_nominal_requests import _bind as bind_nominal_request
    from scripts.game_data.il2cpp.enum_source_variants import select,BYTE_CONDITION
    variant=select(enum_variant)
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.buff_ptr_sources import _call
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    need('explicit-nominal-input',isinstance(enum_type,str)and enum_type in ctx.index.types)
    need('actual-ordinary-enum-metadata',ctx.is_enum(enum_type)and ctx.field(enum_type+'::value__')[1:]==(variant['backingType'],16))
    selected=bind_nominal_request(image,enum_type,typed_request,enum_variant=enum_variant);binding=selected['binding']
    carrier=selected['containerCarrier'];element=selected['enumCarrier'];raw=bytes.fromhex(element['rawHex'])
    need('actual-exact-enum-type-record',len(raw)==16 and raw[10:12]==b'\x11\x80'and int.from_bytes(raw[:8],'little')==ctx.index.types[enum_type].index)
    need('explicit-actual-entry-targets',all(type(p)is int and p>base for p in(predicate_target,underlying_target)))
    predicate=owned(image,predicate_target);underlying=owned(image,underlying_target)
    class_target=_call(predicate,25);underlying_class=_call(underlying,39)
    programs=dict(classFlag=[class_flag_program(predicate['regions'],predicate_target,class_target,flag_set=f)for f in(False,True)],
        underlying=[underlying_program(underlying['regions'],underlying_target,underlying_class,**path)
            for path in(dict(flag_set=False),dict(flag_set=True),dict(flag_set=True,self_element=True))])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.enum-normalization-value-paths.v2',status='proved-current-source-only',nativeInputs=pins,
        enumType=enum_type,typedParentRequest=typed_request,parentTypeBinding=binding,closedCarrier=carrier,programs=programs,
        sourceRequestRole=selected['role'],nominalCarrier=element,
        functions=dict(predicate=dict(entryRva=predicate_target-base,windows=predicate['windows']),
            underlying=dict(entryRva=underlying_target-base,windows=underlying['windows'])),
        classHelperTargets=dict(firstQwordClassLookupRva=class_target-base,wholeTypeClassLookupRva=underlying_class-base),
        concreteEnumCallbackSelected=False,placeholderClassIdentityProved=False,underlyingTypeIdentityProved=False,
        storedTypeDataIsDefinitionIndex=True,runtimeTypeDataFixupProved=False,runtimeInputTypeDataIdentityProved=False,
        wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Fresh concrete enum input type record/nonbyref metadata and actual closed nominal parent request; independently supplied complete helper source paths, raw class predicates/return-address transfers and normal frames.',
            conditional=__doc__ if enum_variant is None else BYTE_CONDITION,structuralOnly='Raw runtime class/type representation transfers.',
            unresolved=['actual enclosing normalization caller/source-target joins','stored type-data index versus runtime fixed record pointer',
                'class helper return identity and metadata/startup binding',
                'class flag/element pointer versus concrete enum underlying type','placeholder class cell identity','generic normalization/intern/cache/registered body selection',
                'actual nominal provider/callback/MethodInfo selection','wire framing and whole owner/EOF']))))
