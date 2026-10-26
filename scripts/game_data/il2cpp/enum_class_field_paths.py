"""Source-only enum class flag/element provenance on current complete bodies.

The complete class constructor CFG and normal frame are checked before the
bounded source/flag/element/return projections. Exact dominating register
origins tie the selected metadata record to the allocated class. The enum
flag store takes metadata bit one, and its element callback receives the
exact registered element type pointer. The callback result remains opaque.

Coherent loaded metadata/registration/cache state, valid allocation and normal
ABI-preserving disjoint child effects are conditions. No initialized cache hit,
actual class/element identity, placeholder sharing, provider callback or bytes
are admitted. A fresh static type record is not observed live runtime state.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.type_data_initialization_control import _complete
from scripts.game_data.il2cpp.class_creation_control import _dominators
from scripts.game_data.il2cpp.class_enum_fields_control import enum_flag_update,_no_register_write,_closed_projection

LABEL='enumClassFieldPaths'
SCHEMA='endfield.enum-class-field-paths.v1'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def unique(regions,raw):
    found=[at+i for at,data in regions for i in range(len(data)-len(raw)+1)if data[i:i+len(raw)]==raw]
    need('unique-source-instruction-pattern',len(found)==1)
    return found[0]


def prefix_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','48897c2420','4156','4883ec20')
    header=g.relative('488b05');g.take('4863f1');allocator_context=g.relative('488b0d')
    g.take('486bfe');stride=int.from_bytes(g.read(1),'little',signed=True)
    g.take('486390');field=int.from_bytes(g.read(4),'little',signed=True);loaded=g.relative('480315')
    registration=g.relative('488b05');record_origin=g.at;g.take('4803fa','488b5068','440fb7474e',
        '4983c014','49c1e004','4c8b34f2','ba01000000')
    allocator_site=g.at;allocator=g.relative('e8');image_count=g.relative('448b0d')
    zero_origin=g.at;g.take('33ed');class_origin=g.at;g.take('488bd8')
    return dict(selectedBytes=g.seen,metadataHeaderCell=header,metadataBaseCell=loaded,registrationCell=registration,
        allocatorContextCell=allocator_context,allocatorTarget=allocator,allocatorSite=allocator_site,imageCountCell=image_count,
        recordBytes=stride,headerOffsetField=field,typeSizesArrayOffset=104,typeSizesIndexScale=8,
        recordOrigin=record_origin,zeroOrigin=zero_origin,classOrigin=class_origin,sourceEnd=g.at,
        allocationArgument='(metadata vtable count word +20)*16',allocatedClassRegister='rbx',recordRegister='rdi')


def flag_program(regions):
    entry=unique(regions,bytes.fromhex('8b4f540fb68338010000'))
    constant=unique(regions,bytes.fromhex('ba10000000418b06'))
    g=BytesPath(regions,entry);g.take('8b4f54','0fb68338010000','d1e9','c0e102','32c8','80e104','32c8','8bc5')
    first=g.at;g.take('888b38010000','837f18ff');use_constant=g.at;g.take('0f45c2','80e1ef','0ac1')
    last=g.at;g.take('888338010000')
    for old in range(256):
        for bit in(0,1):
            for generic in(False,True):
                result=enum_flag_update(old,bit<<1,generic)
                need('complete-byte-flag-truth-table',bool(result&4)==bool(bit)and bool(result&16)==generic and result&0xeb==old&0xeb)
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,constantOrigin=constant,useConstant=use_constant,
        stores=[first,last],recordBitfieldOffset=84,genericContainerOffset=24,classFlagsOffset=312,
        enumMask=4,enumFlagAtStoreEqualsMetadataBitOne=True,truthCases=1024)


def element_program(regions,*,enum_flag=True,null_index=False):
    need('literal-element-path',type(enum_flag)is bool and type(null_index)is bool)
    entry=unique(regions,bytes.fromhex('f683380100000448895b4048895b48'))
    g=BytesPath(regions,entry);g.take('f6833801000004','48895b40','48895b48');g.branch('74',not enum_flag,1)
    registration=None;target=None;call_site=None;load_site=None
    if enum_flag:
        g.take('48634714','83f8ff');g.branch('74',null_index,1)
        if not null_index:
            g.take('488bd0');registration=g.relative('488b05');g.take('488b4838')
            load_site=g.at;g.take('488b2cd1')
        g.take('b201','488bcd');call_site=g.at;target=g.relative('e8');g.take('48894340','48894348')
    after=g.at;g.take('488b6c2438','488bc3','488b5c2430','488b742440','488b7c2448','4883c420','415e','c3')
    return dict(selectedBytes=g.seen,entry=entry,returnStart=after,registrationCell=registration,
        typePointerTableOffset=56,elementTypeIndexOffset=20,elementPointerLoad=load_site,
        callSite=call_site,helperTarget=target,elementFieldOffsets=[64,72],enumFlag=enum_flag,nullIndex=null_index,
        returnedValue='unchanged allocated class',elementClassHelperResultIdentityProved=False,entryRspRestored=True)


def constructor_fields(rows,regions,entry):
    memory={at+i:b for at,raw in regions for i,b in enumerate(raw)};covered=set()
    for row in rows:
        at=int(row['va'],16);raw=bytes.fromhex(row['bytes']);positions=set(range(at,at+len(raw)))
        need('full-constructor-instruction-partition',not covered&positions and all(memory.get(at+i)==b for i,b in enumerate(raw)))
        covered.update(positions)
    need('full-owned-constructor-byte-coverage',covered==set(memory))
    graph=_complete(rows,entry);prefix=prefix_program(regions,entry);flag=flag_program(regions)
    elements=[element_program(regions,**p)for p in(dict(enum_flag=False),dict(enum_flag=True),dict(enum_flag=True,null_index=True))]
    by={int(r['va'],16):i for i,r in enumerate(rows)};dom=_dominators(graph['edges'],entry)
    need('all-normal-returns-use-owned-field-program',graph['returns']==[int(elements[0]['selectedBytes'][-1][0])])
    for origin in(prefix['recordOrigin'],prefix['zeroOrigin'],prefix['classOrigin'],flag['constantOrigin']):
        need('source-or-allocation-origin-dominates-flag',origin in dom[flag['entry']])
    need('allocator-dominates-class-save',prefix['allocatorSite']in dom[prefix['classOrigin']])
    _no_register_write(rows,by[prefix['allocatorSite']]+1,by[prefix['classOrigin']],'rax',calls_allowed=False)
    for register,key in(('rdi','recordOrigin'),('rbx','classOrigin')):
        _no_register_write(rows,by[prefix[key]]+1,by[elements[1]['returnStart']],register,calls_allowed=True)
    _no_register_write(rows,by[prefix['zeroOrigin']]+1,by[elements[1]['elementPointerLoad']],'rbp',calls_allowed=True)
    _no_register_write(rows,by[flag['constantOrigin']]+1,by[flag['useConstant']],'rdx',calls_allowed=False)
    need('flag-store-dominates-element-test',flag['stores'][-1]in dom[elements[1]['entry']])
    selected=[r for r in rows if flag['entry']<=int(r['va'],16)<flag['end']]
    _closed_projection(selected,graph['edges'])
    selected=[r for r in rows if elements[1]['entry']<=int(r['va'],16)<elements[1]['returnStart']]
    _closed_projection(selected,graph['edges'])
    writes=[]
    for store in graph['stores']:
        f=store['facts'];a=f.get('address',f.get('destinationAddress',{}));width=f.get('memoryBytes',f.get('memoryWriteBytes'));disp=a.get('displacement')
        if a.get('base')=='rbx'and a.get('index')is None and width is not None and disp is not None and disp<=312<disp+width:writes.append(store['siteVa'])
    need('complete-explicit-class-flag-store-inventory',writes==flag['stores'])
    need('same-current-registration-source',prefix['registrationCell']==elements[1]['registrationCell'])
    serial_graph=dict(graph,edges={at:sorted(targets)for at,targets in graph['edges'].items()})
    return dict(prefix=prefix,flag=flag,elements=elements,completeCfg=serial_graph,
        allocatedClassAndRecordOriginsProved=True,actualClassOrCallbackIdentityProved=False,
        opaqueChildrenAndAliasesCannotMutateClassProved=False)


def derive(image,pins,**fixup_arguments):
    """Freshly rederive fixup, actual cold class constructor and field inputs."""
    from scripts.game_data.il2cpp.enum_source_variants import select,BYTE_CONDITION
    enum_variant=fixup_arguments.get("enum_variant");variant=select(enum_variant)
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp import enum_type_data_fixup
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.pe_exports import resolve_named_exports
    from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base;pe=image.pe
    fixed=enum_type_data_fixup.derive(image,pins,**fixup_arguments)
    resolver_target=fixed['proof']['projection']['tailTarget'];resolver=owned(image,resolver_target)
    sites=[]
    for at,raw in resolver['regions']:
        for i in range(len(raw)-17):
            if raw[i:i+3]!=bytes.fromhex('8bcbe8')or raw[i+7:i+10]!=bytes.fromhex('488b0d')or raw[i+14:i+18]!=bytes.fromhex('488904d9'):continue
            site=at+i+2;target=site+5+int.from_bytes(raw[i+3:i+7],'little',signed=True)
            cell=at+i+14+int.from_bytes(raw[i+10:i+14],'little',signed=True)
            sites.append(dict(instructionVa=site,target=target,cacheCell=cell))
    need('actual-one-cold-record-class-constructor',len(sites)==1);site,=sites
    constructor=owned(image,site['target']);rows=[]
    for at,raw in constructor['regions']:
        rows+=checked_rows(decode_enum_underlying_instructions(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16))
    proof=constructor_fields(rows,constructor['regions'],site['target'])
    fixed_program=fixed['proof']['fixup'];prefix=proof['prefix']
    need('same-fresh-fixup-constructor-source-cells',all(prefix[k]==fixed_program[k]
        for k in('metadataHeaderCell','metadataBaseCell','recordBytes','headerOffsetField')))
    need('same-fresh-registration-cell',prefix['registrationCell']==fixed['proof']['typeLoop']['registrationCell'])
    exports=resolve_named_exports(pe,['il2cpp_class_from_il2cpp_type']);export,=exports['selectedExports']
    need('direct-named-class-helper-api',export['isForwarder']is False)
    api_entry=base+export['targetRva'];api_raw=pe.bytes_at_va(api_entry,7)
    need('exact-named-class-helper-selector-tail',api_raw[:3]==bytes.fromhex('b201e9'))
    helper=api_entry+7+int.from_bytes(api_raw[3:],'little',signed=True)
    need('same-actual-element-class-callback',proof['elements'][1]['helperTarget']==helper)
    ctx=NativeReferenceContext(image);md=image.metadata;section=md.sections['typeDefinitions'];stride=md.type_record_size
    table=int(image.registration['types'],16);cases=[]
    for selected in fixed['cases']:
        td=ctx.index.types[selected['enumType']];raw=md.buf[section.offset+td.index*stride:section.offset+(td.index+1)*stride]
        bits=int.from_bytes(raw[84:88],'little');element=int.from_bytes(raw[20:24],'little',signed=True)
        generic=int.from_bytes(raw[24:28],'little',signed=True)
        need('exact-enum-record-fields',bits==td.bitfield and element==td.element_type_index
            and generic==td.generic_container_index and bool(bits&2)and element>=0)
        pointer=ctx.type_pointer(element);element_raw=pe.bytes_at_va(pointer,16)
        actual=dict(slot=pe.u64_at_va(table+element*8),pointer=pointer,name=ctx.type_name(element),
            rawHex=element_raw.hex().upper(),field=list(ctx.field(selected['enumType']+'::value__')))
        # The high value-type flag is not a byref/modifier. Use the existing
        # ordinary-kind checker, whose low seven flag bits must all be clear.
        ctx.require_ordinary_kind(element,variant["underlyingKind"])
        need('actual-registered-underlying-int-type:'+selected['enumType']+':'+repr(actual),actual['slot']==pointer
            and actual['name']==variant['backingType']
            and actual['field'][1:]==[variant['backingType'],16])
        cases.append(dict(enumType=selected['enumType'],typeDefinition=td.index,recordHex=raw.hex().upper(),
            enumFlagAtStoreConditional=True,elementTypeIndex=element,elementTypePointerVa=pointer,
            elementRawTypeHex=element_raw.hex().upper(),elementArgumentKind=variant["underlyingKind"],elementClassResultIdentityProved=False))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,cases=cases,
        proof=dict(typeDataFixup=fixed,constructor=proof,constructorWindows=constructor['windows'],
            resolverWindows=resolver['windows'],actualColdClassConstructor=site,namedClassApi=exports,
            namedApiEntryRva=export['targetRva'],namedApiRawHex=api_raw.hex().upper()),
        classEnumFlagAtSelectedStoreConditional=True,**({"elementCallbackReceivesSelectedIntTypeConditional":True}if enum_variant is None else{"elementCallbackReceivesSelectedByteTypeConditional":True}),
        runtimeClassCacheIdentityProved=False,actualEnumElementClassProved=False,placeholderClassIdentityProved=False,
        opaqueChildrenAndAliasesCannotMutateClassProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete current class-constructor CFG/frame, dominating metadata/allocation origins, exact enum flag writes and registered underlying type callback argument for each selected nominal enum.',
            conditional=__doc__ if enum_variant is None else BYTE_CONDITION,structuralOnly='Runtime class/metadata representation transfers.',
            unresolved=['actual initialized metadata/class cache state','opaque class-helper result and alias effects',
                'placeholder class/result identity and generic interning','actual nominal formatter/provider/MethodInfo selection',
                'wire framing/parent/whole owner/EOF']))))
