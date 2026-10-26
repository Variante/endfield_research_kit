"""Conditional registered placeholder record to class.byval_arg source copy.

The complete selected class constructor copies the actual registered byval
type's sixteen bytes unchanged to class+32. A separate copy at+48 receives the
byref-bit update. The selected metadata record's byval index, registered type
pointer and exact System.Int32Enum generic-entry arguments are independently
joined. The current kind17 fixup applies to that same registered type slot.

If the startup System/Int32Enum lookup returns a class constructed from this
exact record after coherent type-data initialization, its byval key contents
match the registered placeholder argument even at a different pointer address.
That lookup result, constructor invocation/cache hit, disjoint opaque helper
effects and initialized interner/formatter selection are not observed here.
No actual concrete enum callback or wire grammar follows from this conditional
copy or from the presence of placeholder generic registrations.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-placeholder-type-copy.v1'
TYPE='System.Int32Enum'
LABEL='enumPlaceholderTypeCopy'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48634708','83f8ff');g.branch('75',True,1)
    g.take('488bd0');registration=g.relative('488b05')
    g.take('488b4838','488b04d1','0f1000','48897b68','0f114330','8b4338','25ffffff5f','0fbae81d','894338')
    byval_store=g.at;g.take('0f114320')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,recordByvalTypeIndexOffset=8,byvalIndexMustNotBeMinusOne=True,
        registrationCell=registration,typePointerTableOffset=56,typePointerStride=8,typeRecordReadBytes=16,
        classMetadataRecordOffset=104,byrefCopyOffset=48,byrefDwordOffset=56,byrefMaskAnd=0x5fffffff,byrefBitSet=29,
        byvalCopyOffset=32,byvalCopyBytes=16,byvalStore=byval_store,byvalCopyUnmodifiedFromRegisteredRecord=True,
        byrefCopyModificationDoesNotChangeXmmSource=True,opaqueCalls=0,wholeConstructorReturnProved=False)


def _control(graph,prefix,source,entry):
    from scripts.game_data.il2cpp.class_creation_control import _dominators
    edges={int(at):set(v)for at,v in graph['edges'].items()};dom=_dominators(edges,entry)
    need('actual-instruction-entry-boundaries',source['entry']in edges and source['byvalStore']in edges and source['end']in edges)
    need('actual-record-and-class-origins-dominate-copy',all(prefix[k]in dom[source['entry']]for k in('recordOrigin','classOrigin')))
    need('byval-copy-dominates-all-normal-returns',bool(graph['returns'])and all(source['byvalStore']in dom[at]for at in graph['returns']))
    need('same-selected-registration-cell',source['registrationCell']==prefix['registrationCell'])
    stores=[]
    for store in graph['stores']:
        f=store['facts'];a=f.get('address',f.get('destinationAddress',{}));width=f.get('memoryBytes',f.get('memoryWriteBytes'));offset=a.get('displacement')
        if a.get('base')=='rbx'and a.get('index')is None and type(width)is int and type(offset)is int and offset<48 and offset+width>32:
            stores.append(store['siteVa'])
    need('complete-direct-byval-field-store-inventory',stores==[source['byvalStore']])
    return stores


def derive(image,pins,**key_arguments):
    from scripts.game_data.il2cpp.enum_source_variants import select,BYTE_CONDITION
    enum_variant=key_arguments.get("enum_variant");variant=select(enum_variant)
    placeholder_type=variant["placeholderType"]
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_argument_key_paths import derive as key_source
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.class_enum_fields_control import _no_register_write
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    keys=key_source(image,pins,**key_arguments);fields=keys['proof']['normalizerSelection']['proof']['classFieldSource']
    constructor_proof=fields['proof']['constructor'];target=fields['proof']['actualColdClassConstructor']['target']
    body=owned(image,target);patterns=[]
    for at,raw in body['regions']:
        offset=raw.find(bytes.fromhex('4863470883f8ff'))
        while offset>=0:patterns.append(at+offset);offset=raw.find(bytes.fromhex('4863470883f8ff'),offset+1)
    need('one-current-type-copy-program',len(patterns)==1);source=program(body['regions'],patterns[0])
    graph=constructor_proof['completeCfg'];prefix=constructor_proof['prefix'];stores=_control(graph,prefix,source,target)
    rows=[]
    from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    for at,raw in body['regions']:rows+=checked_rows(decode_enum_underlying_instructions(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda r:int(r['va'],16));by={int(r['va'],16):i for i,r in enumerate(rows)}
    for register,key in(('rdi','recordOrigin'),('rbx','classOrigin')):
        _no_register_write(rows,by[prefix[key]]+1,by[source['end']],register,calls_allowed=True)
    td=ctx.index.types[placeholder_type];need('exact-placeholder-value-enum',ctx.is_enum(placeholder_type)and td.generic_container_index<0
        and ctx.field(placeholder_type+'::value__')[1:]==(variant['backingType'],16))
    pointer=ctx.type_pointer(td.byval_type_index);raw=image.pe.bytes_at_va(pointer,16)
    need('actual-registered-placeholder-type',len(raw)==16 and raw[10:12]==bytes.fromhex('1180')and int.from_bytes(raw[:8],'little')==td.index)
    section=md.sections['typeDefinitions'];record=md.buf[section.offset+td.index*md.type_record_size:section.offset+(td.index+1)*md.type_record_size]
    need('same-metadata-byval-index-field',int.from_bytes(record[8:12],'little',signed=True)==td.byval_type_index>=0)
    entries=GenericEntries(image);registrations=[]
    for owner in variant['formatterTypes']:
        declaration=ctx.index.types[owner];method,=[m for m in md.methods_for(declaration)if md.string(m.name_index)=='Deserialize']
        selected=entries.resolve(method.index,[placeholder_type],[]);argument,=selected['classInstantiation']['arguments']
        need('same-own-registered-placeholder-generic-argument:'+owner,argument['type_pointer_va']==pointer)
        registrations.append(dict(formatterType=owner,methodDefinition=method.index,registration=selected,
            actualConcreteNominalSelectionProved=False))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(argumentKeySource=keys,classConstructorWindows=body['windows'],typeCopy=source,
            allDirectByvalStores=stores,placeholder=dict(typeName=placeholder_type,typeDefinition=td.index,recordHex=record.hex().upper(),
                byvalTypeIndex=td.byval_type_index,registeredTypePointerVa=pointer,typeRecordHex=raw.hex().upper()),
            registeredPlaceholderEntries=registrations),
        placeholderClassByvalMatchesRegisteredKeyConditional=True,placeholderLookupResultIdentityProved=False,
        opaqueAliasPreservationProved=False,initializedInternerResultIdentityProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete current class-constructor CFG/dominance/direct byval-store inventory and selected unchanged registered16-byte type copy; exact current metadata byval index/type record and placeholder generic-entry argument pointers.',
            conditional=__doc__ if enum_variant is None else BYTE_CONDITION,structuralOnly='Runtime metadata/class generic key representation.',
            unresolved=['actual startup lookup/cache result and constructor record index','opaque helper/alias preservation',
                'interner/comparison caller/result identity','actual nominal provider/formatter/MethodInfo callback selection','wire/parent/EOF']))))
