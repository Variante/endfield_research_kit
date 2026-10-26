"""Current enum type-data fixup and reciprocal record-index source programs.

The selected closed enum argument starts as a metadata TypeDefinition index.
It comes from an actual closed enum List read or that exact enum's own
ordinary UnmanagedFormatter constructor request; the latter stays explicitly
a registration input and is never reported as a collection request.
The exact kind17 table arm conditionally rewrites that same registered type
slot to the loaded metadata record pointer. The independent record-pointer
projection reverses the selected record geometry before its actual class
resolver tail. These are address/value transfers, not a concrete class result.

The registration publication is an explicitly bounded straight-line slice;
its complete startup CFG and execution are not claimed. Matching published
registration and loaded metadata globals, one successful stable initialization
pass, valid nonaliasing type records and normal ABI-preserving helper returns
remain conditions. No initialized class flag, element class, placeholder class,
interned generic context, formatter callback or collection grammar is admitted.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.record_index_geometry import prove_record_index_geometry

LABEL='enumTypeDataFixup'
SCHEMA='endfield.enum-type-data-fixup.v2'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def fixup_program(regions,entry,*,null_index=False):
    """Complete frameless index-to-record helper, including the -1 arm."""
    need('literal-null-index-path',type(null_index)is bool)
    g=BytesPath(regions,entry);g.take('486311','4c8bc1','83faff');g.branch('75',not null_index,1)
    if null_index:
        g.take('48c70100000000','c3')
        return dict(selectedBytes=g.seen,storedIndex=-1,storedQword=0,normalReturn=True,entryRspRestored=True)
    header=g.relative('488b05');g.take('486bd2');stride=int.from_bytes(g.read(1),'little',signed=True)
    need('positive-record-stride',stride>0)
    g.take('486388');field=int.from_bytes(g.read(4),'little',signed=True)
    loaded=g.relative('48030d');g.take('4803d1','498910','c3')
    return dict(selectedBytes=g.seen,recordBytes=stride,headerOffsetField=field,metadataHeaderCell=header,
        metadataBaseCell=loaded,inputSignedDwordIndex=True,sameInputQwordOverwritten=True,
        storedAddress='loaded metadata base + signed header section offset + signed index * record bytes',
        normalReturn=True,entryRspRestored=True)


def projection_program(regions,entry,*,record_bytes,records):
    """Complete selected reciprocal projection and actual resolver tail."""
    g=BytesPath(regions,entry);header=g.relative('488b05');g.take('486390')
    field=int.from_bytes(g.read(4),'little',signed=True);g.take('48b8')
    multiplier=int.from_bytes(g.read(8),'little',signed=True);g.take('482bca')
    loaded=g.relative('482b0d');g.take('48f7e9','4803d1','48c1fa');shift=int.from_bytes(g.read(1),'little')
    g.take('488bca','48c1e93f','4803ca');target=g.relative('e9')
    geometry=prove_record_index_geometry(multiplier=multiplier,shift=shift,record_bytes=record_bytes,records=records)
    return dict(selectedBytes=g.seen,metadataHeaderCell=header,metadataBaseCell=loaded,headerOffsetField=field,
        multiplier=multiplier,shift=shift,recordBytes=record_bytes,tailTarget=target,geometry=geometry,
        inputRecordPointerProved=False,returnedIndexRegister='ecx',tailUsesUnchangedEntryFrame=True)


def loop_program(regions,entry,*,image_base,record_target,alternate_target):
    """Complete kind17 iteration/exit and exact dispatch-table ownership.

    EBX counts entries and RDI advances by eight. Stable actual table/count
    and ordinary fixup calls yield the same selected arm for every enum slot.
    Other kind arms are decoded as table targets but are not assigned semantics.
    """
    g=BytesPath(regions,entry);g.take('4053','4883ec20');cell=g.relative('4c8b05')
    g.take('33db','41395830');g.branch('7e',False,1);g.take('4889742430')
    need('actual-image-origin',g.relative('488d35')==image_base)
    g.take('48897c2438','8bfb','0f1f840000000000');iteration=g.at
    g.take('498b4038','488b0c07','0fbe410a','ffc8','83f81d');g.branch('77',False,1)
    g.take('4898','0fb68406');selector=int.from_bytes(g.read(4),'little',signed=True)+image_base
    g.take('8b9486');table=int.from_bytes(g.read(4),'little',signed=True)+image_base
    g.take('4803d6','ffe2');record_site=g.at
    # Table data belongs to the same exception family, separately from code.
    def read(at,n):
        try:return bytes(g.bytes[at+i]for i in range(n))
        except KeyError as error:raise ValueError(LABEL+'.unowned-dispatch-table')from error
    selectors=read(selector,30);raw_targets=read(table,12)
    targets=[image_base+int.from_bytes(raw_targets[i:i+4],'little',signed=True)for i in range(0,12,4)]
    need('bounded-three-kind-arms',set(selectors)=={0,1,2})
    need('kind17-selects-record-arm',targets[selectors[16]]==record_site)
    g.call(record_target);g.jump('eb',1);reload_site=g.at;reload_cell=g.relative('4c8b05')
    need('same-registration-reload',cell==reload_cell);increment=g.at
    g.take('ffc3','4883c708','413b5830');back=g.relative('7c',1)
    need('same-loop-backedge',back==iteration)
    g.take('488b7c2438','488b742430','4883c420','5b','c3')
    # Independently authenticate the other actual callback and skip destination.
    alt=BytesPath(regions,record_site+7);alt.call(alternate_target)
    need('alternate-rejoins-registration-load',alt.at==reload_site)
    need('actual-table-targets',targets==[record_site,record_site+7,increment])
    zero=BytesPath(regions,entry);zero.take('4053','4883ec20')
    need('same-zero-registration-load',zero.relative('4c8b05')==cell)
    zero.take('33db','41395830');zero.branch('7e',True,1);zero.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,zeroCountSelectedBytes=zero.seen,alternateCallSelectedBytes=alt.seen,
        registrationCell=cell,selectorAddress=selector,selectorHex=selectors.hex().upper(),
        targetsAddress=table,targetHex=raw_targets.hex().upper(),actualTargets=targets,kind17Arm=record_site,
        tableCountOffset=48,tablePointerOffset=56,pointerStride=8,counterBits=32,
        stableBoundedTableIterationProved=True,normalReturn=True,entryRspRestored=True,
        otherTypeKindSemanticsAdmitted=False)


def publication_slice(regions,entry,*,code_registration,metadata_registration,registration_cell):
    """Exact four instructions only; no surrounding startup reachability claim."""
    g=BytesPath(regions,entry)
    need('selected-code-registration-address',g.relative('488d0d')==code_registration)
    code_cell=g.relative('48890d')
    need('selected-metadata-registration-address',g.relative('488d05')==metadata_registration)
    need('same-published-registration-cell',g.relative('488905')==registration_cell)
    return dict(selectedBytes=g.seen,codeRegistrationCell=code_cell,metadataRegistrationCell=registration_cell,
        selectedStaticAddressesStored=True,completeStartupControlProved=False,executionObserved=False)


def derive(image,pins,*,enum_requests,loop_target,record_target,alternate_target,projection_target,publication_entry,enum_variant=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.enum_nominal_requests import _bind as bind_nominal_request
    from scripts.game_data.il2cpp.enum_source_variants import select,BYTE_CONDITION
    variant=select(enum_variant)
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base;pe=image.pe;md=image.metadata
    need('explicit-targets',all(type(x)is int and base<x<base+(1<<32)for x in
        (loop_target,record_target,alternate_target,projection_target,publication_entry)))
    need('bounded-nominal-enum-requests',isinstance(enum_requests,list)and 0<len(enum_requests)<=64)
    ctx=NativeReferenceContext(image);section=md.sections['typeDefinitions'];records=len(md.types);stride=md.type_record_size
    header_field=8+8*list(md.sections).index('typeDefinitions')
    need('independent-current-record-geometry',0<stride<128 and section.size==records*stride
        and int.from_bytes(md.buf[header_field:header_field+4],'little',signed=True)==section.offset)
    fix_regions=[(record_target,pe.bytes_at_va(record_target,64))]
    fix=fixup_program(fix_regions,record_target);null=fixup_program(fix_regions,record_target,null_index=True)
    need('same-metadata-record-geometry',(fix['recordBytes'],fix['headerOffsetField'])==(stride,header_field))
    projection=projection_program([(projection_target,pe.bytes_at_va(projection_target,64))],projection_target,record_bytes=stride,records=records)
    need('same-fixup-projection-cells',all(projection[key]==fix[key]for key in('metadataHeaderCell','metadataBaseCell','headerOffsetField')))
    loop=owned(image,loop_target);program=loop_program(loop['regions'],loop_target,image_base=base,
        record_target=record_target,alternate_target=alternate_target)
    publication=publication_slice([(publication_entry,pe.bytes_at_va(publication_entry,28))],publication_entry,
        code_registration=image.code_registration,metadata_registration=image.metadata_registration,registration_cell=program['registrationCell'])
    registration=image.metadata_registration
    count=int.from_bytes(pe.bytes_at_va(registration+48,4),'little',signed=True);table=pe.u64_at_va(registration+56)
    need('same-selected-static-types-table',count==image.registration['typesCount']
        and table==int(image.registration['types'],16)and 0<count<1<<31)
    raw_table=pe.bytes_at_va(table,count*8)
    pointers=[int.from_bytes(raw_table[i:i+8],'little')for i in range(0,len(raw_table),8)]
    cases=[]
    for enum_type,usage in enum_requests:
        need('named-enum-definition',isinstance(enum_type,str)and enum_type in ctx.index.types
            and ctx.is_enum(enum_type)and ctx.field(enum_type+'::value__')[1:]==(variant['backingType'],16))
        selected=bind_nominal_request(image,enum_type,usage,enum_variant=enum_variant);binding=selected['binding'];pointer=selected['enumTypePointerVa']
        raw=pe.bytes_at_va(pointer,16);definition=ctx.index.types[enum_type]
        need('selected-enum-record-index',raw[10:12]==b'\x11\x80'and int.from_bytes(raw[:8],'little')==definition.index)
        need('same-selected-byval-type-slot',0<=definition.byval_type_index<count and pointers[definition.byval_type_index]==pointer)
        need('nonaliasing-enum-type-writeback-slot',[i for i,p in enumerate(pointers)if pointer-7<=p<=pointer+15]==[definition.byval_type_index])
        cases.append(dict(enumType=enum_type,typedParentRequest=usage,parentBinding=binding,typePointerVa=pointer,
            sourceRequestRole=selected['role'],
            byvalTypeIndex=definition.byval_type_index,typeDefinition=definition.index,storedRawTypeHex=raw.hex().upper(),
            conditionalRecordOffsetFromLoadedMetadataBase=section.offset+definition.index*stride))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,cases=cases,
        proof=dict(fixup=fix,nullIndex=null,projection=projection,typeLoop=program,loopWindows=loop['windows'],publicationSlice=publication,
            iterationBound=count,selectedStaticTypePointerCount=count),
        typeDataIndexToRecordPointerConditional=True,sameStaticRegistrationPublicationSliceProved=True,
        completeStartupControlProved=False,initializationExecutionObserved=False,runtimeInputTypeDataIdentityProved=False,
        concreteEnumClassProved=False,concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Actual closed enum carriers/static table slots, complete selected fixup/reciprocal/kind17-loop programs and exact static registration publication slice.',
            conditional=__doc__ if enum_variant is None else BYTE_CONDITION,structuralOnly='Runtime metadata representation transfers.',
            unresolved=['startup/control execution and loaded metadata identity','actual initialized class/cache result',
                'enum class flag and underlying class writes','initialized placeholder class and generic interning',
                'actual nominal formatter/provider/MethodInfo selection','wire framing/parent/whole owner/EOF']))))
