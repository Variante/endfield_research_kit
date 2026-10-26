"""Own byte-enum registration, exact registry setter and actual provider clone."""
import json

from scripts.game_data.il2cpp import enum_byte_provider_programs as programs
from scripts.game_data.il2cpp import enum_byte_registry_programs as setter_programs

SCHEMA='endfield.enum-byte-registry-sources.v1'
TYPE='Beyond.Gameplay.Core.EnemyHurtShakeIntensity'
LABEL='enumByteRegistrySources'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def derive(image,pins,*,typed_request,provider_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp import enum_nominal_registration_paths as nominal
    from scripts.game_data.il2cpp import enum_registry_publication_paths as registry
    from scripts.game_data.il2cpp.enum_method_rgctx_paths import provider_program
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_typed_usage_context,validate_generic_contexts
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;symbols=ContextSymbols(image)
    validate_typed_usage_context(image,typed_request,label=LABEL)
    dictionary_type=ctx.index.types['Beyond.SerializeFieldDictionary`2']
    methods=[m for m in md.methods_for(dictionary_type)if md.string(m.name_index)=='DeserializeV2']
    need('one-own-class-only-DeserializeV2',len(methods)==1);method,=methods
    need('actual-closed-byte-key-request',typed_request.get('tag')==6 and typed_request['methodSpec'][0]==method.index
        and typed_request['methodSpec'][1]>=0 and typed_request['methodSpec'][2]==-1
        and typed_request.get('typeName')=='Beyond.SerializeFieldDictionary`2'and typed_request.get('methodName')=='DeserializeV2'
        and len(typed_request.get('classArguments',[]))==2 and typed_request['classArguments'][0]==TYPE
        and typed_request.get('methodArguments')==[]and method.flags&16)
    args=image.instantiations.resolve(typed_request['methodSpec'][1]).arguments;need('two-own-class-arguments',len(args)==2)
    enum=ctx.index.types[TYPE];raw=image.pe.bytes_at_va(args[0].type_pointer_va,16)
    need('exact-byte-backed-nominal-key',ctx.is_enum(TYPE)and ctx.field(TYPE+'::value__')[1:]==('byte',16)
        and args[0].type_pointer_va==ctx.type_pointer(enum.byval_type_index)
        and raw[10:12]==b'\x11\x80'and int.from_bytes(raw[:8],'little')==enum.index)
    # ContextSymbols freshly frames the actual complete directory and decodes
    # only this source-read slot. Unread kind5 entries remain uninterpreted;
    # the older whole-context validator would incorrectly open them here.
    dictionary_context=symbols.context(dictionary_type.index,slots=[23])
    need('only-actual-key-provider-context-selected',dictionary_context.get('selectedSlots')==[23]
        and len(dictionary_context['entries'])==1 and dictionary_context['entries'][0]['relativeSlot']==23)
    provider_slot=dictionary_context['entries'][0];provider_variable,=provider_slot['methodArguments']
    need('actual-key-provider-owned-class-VAR-zero',provider_slot['kind']==3
        and provider_slot['typeName']=='MemoryPack.MemoryPackFormatterProvider'and provider_slot['methodName']=='GetFormatter'
        and provider_slot['classArguments']==[]and bytes.fromhex(provider_variable['rawHex'])[10:12]==b'\x13\x00'
        and provider_variable.get('parameterOwner',{}).get('typeIndex')==dictionary_type.index
        and provider_variable['parameterOwner']['ordinal']==0)
    selected,ctor,register,ctor_target,register_target=nominal._select_nominal_transfers(image,pins,enum_types=[TYPE])
    cb,cr,cf=nominal._full(image,ctor_target)
    constructors=[nominal.constructor_program(cb['regions'],ctor_target,cold=c)for c in(False,True)]
    rb=owned(image,register_target)
    cases=[dict(),dict(cold_context=True),dict(cold_type=True),dict(cold_provider=True),
        dict(cold_context=True,cold_type=True,cold_provider=True)]
    registers=[programs.register_program(rb['regions'],register_target,**case)for case in cases]
    setter=registers[0]['actualDictionarySetter'];rb,rr,rf=nominal._full(image,register_target,tail_targets=(setter,))
    usage=derive_typed_usage_context(image,registers[0]['dictionaryMethodUsageInstruction']-base,label=LABEL)
    registry_type='System.Collections.Concurrent.ConcurrentDictionary`2';registry_arguments=['System.Type','MemoryPack.IMemoryPackFormatter']
    need('own-closed-reference-registry-setter',usage['tag']==6 and usage['typeName']==registry_type
        and usage['methodName']=='set_Item'and usage['classArguments']==registry_arguments and usage['methodArguments']==[])
    static_context=symbols.context(ctx.index.types[registry_type].index)
    context_binding=registry.bind_dictionary_context(static_context,ctx.index.types[registry_type].index)
    own_register_context=symbols.context(register,is_method=True);variable=own_register_context['entries'][0]['type']
    need('own-Register-MVAR-zero-context',own_register_context['count']==1 and own_register_context['entries'][0]['kind']==1
        and bytes.fromhex(variable['rawHex'])[10:12]==b'\x1e\x00'
        and variable.get('parameterOwner',{}).get('methodIndex')==register and variable['parameterOwner']['ordinal']==0)
    formatter_context=symbols.context(ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1'].index)
    validate_generic_contexts(image,[formatter_context,own_register_context],label=LABEL)
    need('own-formatter-base-constructor-context',formatter_context['count']==2
        and [r['kind']for r in formatter_context['entries']]==[3,2])
    base_ctor,base_class=formatter_context['entries'];base_arguments=base_ctor.get('classArguments',[])
    need('exact-reciprocal-formatter-base-VAR-zero',base_ctor['typeName']=='MemoryPack.MemoryPackFormatter`1'
        and base_ctor['methodName']=='.ctor'and base_ctor['methodArguments']==[]and len(base_arguments)==1
        and bytes.fromhex(base_arguments[0]['rawHex'])[10:12]==b'\x13\x00'
        and base_arguments[0].get('parameterOwner',{}).get('typeIndex')==formatter_context['definition']
        and base_arguments[0]['parameterOwner']['ordinal']==0
        and base_class['type']['definition']['name']=='MemoryPack.MemoryPackFormatter`1'
        and base_class['type']['classArguments']==base_arguments)
    parameter,=md.parameters_for(md.methods[register]);formal=symbols.type(ctx.type_pointer(parameter.type_index))
    need('own-Register-formal-formatter-of-same-MVAR',formal.get('definition',{}).get('name')=='MemoryPack.MemoryPackFormatter`1'
        and formal.get('classArguments')==[variable]and bytes.fromhex(formal['rawHex'])[10:12]==b'\x15\x00')
    families={};bodies={}
    def full(role,target):
        source=owned(image,target);rows=[]
        for at,data in source['regions']:rows+=nominal.source_rows(registry.decode(image.mapper,data,at))
        families[role]=dict(windows=source['windows'],program=registry.ordinary_program(source['regions'],rows,target),
            regions=[[at-base,data.hex()]for at,data in source['regions']])
        bodies[role]=source;return source
    sb=full('registrySetter',setter)
    setters=[setter_programs.setter_program(sb['regions'],setter,cold_insertion=c)for c in(False,True)]
    insertion_body=full('insertion',setters[0]['actualInsertion'])
    insertion=registry.insert_empty_program(insertion_body['regions'],insertion_body['pointer'])
    actual_provider=full('actualByteProvider',provider_target)
    pp=[programs.program(actual_provider['regions'],provider_target,**case)for case in cases]
    cold=pp[-1]
    need('same-owned-provider-metadata-cells-and-ready-source',cold['providerTypeUsageCell']==cold['actualProviderClassCell']
        and cold['typeTypeUsageCell']==cold['actualTypeClassCell']
        and cold['actualTypeReadyHelper']==cold['actualProviderReadyHelper'])
    get_formatter=provider_slot['methodSpec'][0]
    canonical=GenericEntries(image).resolve(get_formatter,[],['System.ByteEnum'])
    generic_body=full('canonicalByteProvider',canonical['pointer']);canonical_program=provider_program(generic_body['regions'],generic_body['pointer'])
    for key in('actualTypeClassCell','actualProviderClassCell','actualTypeFromHandle','actualBackend','actualMethodContextInitializer','actualCast'):
        need('same-independently-owned-canonical-actual-provider-role:'+key,cold[key]==canonical_program[key])
    need('actual-optimized-class-slot-one-resolver',cold['actualExpectedClassResolver']==setters[0]['actualClassContextSlotResolver']
        and cold['expectedClassResolverSlotArgument']==1)
    public_body=owned(image,cold['actualBackend']);public=registry.public_program(public_body['regions'],public_body['pointer'])
    _,_,families['actualPublicProvider']=nominal._full(image,public_body['pointer'],tail_targets=(public['actualBackendTail'],))
    backend_body=full('actualInlineBackend',public['actualBackendTail'])
    backend=registry.actual_backend_hit_program(backend_body['regions'],backend_body['pointer'])
    lookup=derive_typed_usage_context(image,backend['lookupMethodUsageInstruction']-base,label=LABEL)
    need('own-closed-registry-lookup-context',lookup['tag']==6 and lookup['typeName']==registry_type
        and lookup['methodName']=='TryGetValue'and lookup['classArguments']==registry_arguments and lookup['methodArguments']==[])
    need('same-actual-registry-class-type-and-formatter-transfer',registers[0]['providerClassCell']==public['providerClassCell']==backend['providerClassCell']==cold['actualProviderClassCell']
        and registers[0]['systemTypeClassCell']==cold['actualTypeClassCell']
        and registers[0]['actualTypeFromHandle']==cold['actualTypeFromHandle'])
    need('same-registry-hash-and-own-context-source',setters[0]['actualHashHelper']==backend['actualHashHelper']
        and setters[0]['actualClassContextSlotResolver']==backend['actualContextSlotResolver']==insertion['actualSlotResolver'])
    need('same-selected-disabled-collector',insertion['collectorFlagCell']==backend['collectorFlagCell'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-byte-registry-roundtrip-source',nativeInputs=pins,
        typeName=TYPE,typeDefinition=enum.index,providerTargetRva=provider_target-base,
        proof=dict(actualDictionaryRequest=typed_request,keyCarrier=symbols.type(args[0].type_pointer_va),
            actualDictionaryClassContext=dictionary_context,keyProviderSlot=provider_slot,nominalCallerSelections=selected,
            constructorDefinition=ctor,constructorFamily=cf,constructorPrograms=constructors,formatterContext=formatter_context,
            registerDefinition=register,registerMethodContext=own_register_context,registerFamily=rf,registerPrograms=registers,
            registerFormalParameter=formal,
            actualClosedRegistrySetter=usage,dictionaryStaticContext=static_context,dictionaryContextBinding=context_binding,
            setterPrograms=setters,selectedEmptyInsertion=insertion,providerPrograms=pp,
            canonicalByteProviderRegistration=canonical,canonicalByteProviderProgram=canonical_program,
            actualPublicProvider=public,actualInlineBackend=backend,actualClosedRegistryLookup=lookup,completeFamilies=families),
        sameOriginalNominalTypeAndFormatterRegistryRoundtripConditional=True,actualInitializedRegistryStateObserved=False,
        actualNominalCallbackSelected=False,parentOrCollectionGrammarAdmitted=False,
        evidenceBoundary=dict(exact='Own actual byte nominal eager caller/constructor/Register/closed registry setter and insertion; independently owned actual optimized and canonical ByteEnum providers, original key VAR0 request, Type/backend/registry roundtrip and actual helper identities.',
            conditional='Original nominal MethodInfo/class/contexts and initialized provider registry remain coherent; successful normal allocation/hash/equality/locks/casts, disabled collector, first-empty insertion and selected matching lookup, no replacement or interfering alias effects.',
            structuralOnly='Unchanged original System.Type and formatter reference transfers.',unresolved=['actual live registry/provider/MethodInfo state','slot-five nominal-to-code join','parent/EOF'])),default=_json_set))
