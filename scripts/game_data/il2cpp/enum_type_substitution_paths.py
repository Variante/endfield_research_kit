"""Actual nominal VAR substitution versus separately normalized method code.

The current type-substitution family is partitioned into its complete code,
one guarded sixteen-entry RVA table and its exact alignment padding. The
selected VAR/MVAR arms pass the unchanged input carrier and the actual class/
method instantiation to the same resolver. The concrete kind17 default arm
returns the incoming carrier unchanged. No primitive normalization occurs on
these selected paths. Every declared computed target and external tail is
checked against the actual source and restored normal frame.

The resolver obtains the ordinal WORD from the input generic-parameter record,
then selects that exact entry from the supplied instantiation vector. Equal
attribute/byref paths return the selected carrier unchanged; either mismatch
copies its complete sixteen-byte native type record, updates only attributes
and the byref bit from the input parameter, and returns that copy. The copy's
size describes a native type carrier, never a serialized enum width.

Coherent initialized generic-parameter payloads, bounded instantiations,
ordinary ABI-preserving helpers, valid disjoint allocations and cache effects
are conditions. Source-level substitution is not a live nominal MethodInfo,
class RGCTX, formatter callback, enum/list grammar or parent/EOF admission.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-type-substitution-paths.v1'
LABEL='enumTypeSubstitutionPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def decode(mapper,data,entry):
    """Own only the resolver's exact additional XOR memory instruction."""
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode as inherited
    from scripts.game_data.il2cpp.integer_tag_dispatch import _row
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            if raw[offset:offset+3]==bytes.fromhex('315008'):
                return _row(raw,offset,offset+3,at,'xor dword [rax+0x8], edx',write=None,
                    enumTypeAttributeXor=dict(bits=32,sourceRegister='edx',baseRegister='rax',displacement=8,
                        memoryReadBytes=4,memoryWriteBytes=4,preservesRegisters=True,
                        clearsFlags=['CF','OF'],undefinedFlags=['AF'],resultFlags=['SF','ZF','PF']))
            return mapper.decode_one_x64(raw,offset,at)
    return inherited(Fallback(),data,entry)


def partition(mapper,regions,entry,*,image_base):
    """An explicit current R9 switch shape; no generic guessed table scan."""
    need('one-owned-contiguous-type-source',len(regions)==1 and regions[0][0]==entry)
    need('explicit-selected-image-base',type(image_base)is int and 0<image_base<entry<image_base+(1<<32))
    raw=regions[0][1];g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','0fbe410a','488bf9','83c0f1')
    guard=g.at;g.take('83f80f');default=g.relative('0f87')
    base_site=g.at;need('same-literal-image-base',g.relative('488d0d')==image_base)
    g.take('4898');load=g.at;g.take('448b8c81');table=image_base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('4c03c9');jump=g.at;g.take('41ffe1')
    need('exact-16-entry-owned-table-tail',table%4==0 and table>g.at and table+64==entry+len(raw))
    table_raw=raw[table-entry:];targets=[image_base+int.from_bytes(table_raw[n:n+4],'little')for n in range(0,64,4)]
    need('exact-selected-table-padding',raw[table-entry-3:table-entry]==bytes.fromhex('0f1f00'))
    code=raw[:table-entry-3];rows=decode(mapper,code,entry)
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    checked_rows(rows,code,LABEL)
    need('ret-precedes-alignment-padding',bytes.fromhex(rows[-1]['bytes'])==b'\xc3')
    boundaries={int(row['va'],16)for row in rows}
    need('every-switch-value-and-default-is-code-boundary',default in boundaries and all(target in boundaries for target in targets))
    return dict(rows=rows,codeRange=(entry,entry+len(code)),padding=[dict(start=table-3,end=table,rawHex='0F1F00')],
        tables=[dict(guard=guard,guardExit=default,baseLoad=base_site,load=load,jump=jump,maximum=15,
            tableStart=table,tableEnd=table+64,rawHex=table_raw.hex().upper(),targets=targets,
            baseRegister='rcx',destinationRegister='r9',imageBase=image_base)],
        computedJumpTargets={jump:set(targets)},prefixSelectedBytes=g.seen,
        inputKindByteOffset=10,signedKindSubtrahend=15,boundedUnsignedTableIndexProved=True)


def _start(regions,entry,*,kind,image_base):
    need('finite-literal-type-kind',type(kind)is int and kind in(17,19,21,30))
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','0fbe410a','488bf9','83c0f1','83f80f')
    g.branch('0f87',False);need('selected-path-literal-image-base',g.relative('488d0d')==image_base)
    g.take('4898','448b8c81');table=image_base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('4c03c9','41ffe1')
    read=BytesPath(regions,table+(kind-15)*4);target=image_base+int.from_bytes(read.read(4),'little')
    need('selected-table-target-owned',target in g.bytes);g.at=target
    return g


def kind_program(regions,entry,*,kind,image_base,method_instantiation_present=True):
    need('finite-literal-selected-kind-path',type(kind)is int and kind in(17,19,30))
    need('literal-method-instantiation-presence',type(method_instantiation_present)is bool)
    g=_start(regions,entry,kind=kind,image_base=image_base);target=None
    if kind==19:
        g.take('488b12','488bcf','488b5c2430','488b742438','4883c420','5f');target=g.relative('e9')
    elif kind==30:
        g.take('48837a0800');g.branch('0f84',not method_instantiation_present)
        if method_instantiation_present:
            g.take('488b5208','488bcf','488b5c2430','488b742438','4883c420','5f');target=g.relative('e9')
    if target is None:g.take('488b5c2430','488bc7','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,kind=kind,actualResolverTarget=target,
        instantiationSource='incoming context.classInstantiation +0'if kind==19 else
            'incoming context.methodInstantiation +8'if kind==30 and method_instantiation_present else None,
        methodInstantiationPresent=method_instantiation_present if kind==30 else None,
        actualCarrierUnchangedAtResolver=target is not None,returnsIncomingCarrierUnchanged=target is None,
        primitiveNormalizationOnSelectedPath=False,entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'])


def constructed_program(regions,entry,*,image_base,changed_key):
    need('literal-constructed-key-path',type(changed_key)is bool)
    g=_start(regions,entry,kind=21,image_base=image_base)
    g.take('488b07','488b4808','4885c9');g.branch('75',True,1)
    substitute=g.relative('e8');g.take('488b0f','488bd8','4c8b01','4d85c0');g.branch('75',True,1)
    header=g.relative('488b05');g.take('4d8b00','486388a0000000','48b8')
    multiplier=int.from_bytes(g.read(8),'little',signed=True)
    g.take('4c2bc1');metadata=g.relative('4c2b05');g.take('49f7e8','4903d0','48c1fa06','488bca',
        '48c1e93f','4803ca');definition_class=g.relative('e8')
    g.take('488d4820','488bd3');class_key=g.relative('e8');g.take('488bd8','483b07');g.branch('74',not changed_key,1)
    allocator=None;allocate=None;stats=None
    if changed_key:
        allocator=g.relative('488b0d');g.take('ba10000000');allocate=g.relative('e8');g.jump('e9')
        g.take('0f1007','0f1100','488918');stats=g.relative('f048ff05')
        g.take('488b5c2430','488b742438','4883c420','5f','c3')
    else:g.take('488b5c2430','488bc7','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,kind=21,changedKey=changed_key,
        actualInstantiationSubstitution=substitute,substitutionArguments=dict(rcx='actual input generic-key.classInstantiation +8',
            rdx='unchanged incoming generic context',r8b='unchanged incoming substitution flag'),
        metadataHeaderCell=header,metadataBaseCell=metadata,recordSectionHeaderOffset=160,
        recordMultiplier=multiplier,recordShift=6,actualDefinitionClassResolver=definition_class,
        actualGenericClassKeyConstructor=class_key,keyArguments=dict(rcx='actual original definition class.byval +32',
            rdx='actual instantiation-substitution result'),
        actualKeyComparedToOriginalDataWord=True,actualKeyStoredAsOnlyChangedCarrierWord=changed_key,
        returnsIncomingCarrierUnchanged=not changed_key,nativeCarrierCopyBytes=16 if changed_key else None,
        actualAllocator=allocate,allocatorContextCell=allocator,allocationStatsCell=stats,
        originalDefinitionAndInstantiationMustBeNonnull=True,
        normalDisjointAllocationAndCoherentClassKeyCacheRequired=True,primitiveNormalizationOnSelectedPath=False,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'])


def resolver_program(regions,entry,*,attribute_mismatch=False,byref_mismatch=False):
    need('literal-attribute-and-byref-path',type(attribute_mismatch)is bool and type(byref_mismatch)is bool)
    need('byref-not-reached-after-attribute-mismatch',not(attribute_mismatch and byref_mismatch))
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488b01','488bf9','440fb7400c',
        '488b4208','4a8b1cc0','8b5308','335108','6685d2')
    g.branch('75',attribute_mismatch,1)
    if not attribute_mismatch:
        g.take('8b4b08','334f08','0fbae11d');g.branch('72',byref_mismatch,1)
    allocate=None;cell=None;stats=None
    if attribute_mismatch or byref_mismatch:
        cell=g.relative('488b0d');g.take('ba10000000');allocate=g.relative('e8')
        g.take('0f1003','0f1100','8b5008','335708','81e200000020','315008','0fb74f08','66894808')
        stats=g.relative('f048ff05')
    else:g.take('488bc3')
    g.take('488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,attributeMismatch=attribute_mismatch,byrefMismatch=byref_mismatch,
        parameterPayloadOffset=0,parameterOrdinalOffset=12,parameterOrdinalBytes=2,
        instantiationVectorOffset=8,argumentPointerStride=8,selectedArgumentRegister='rbx',
        returnedSelectedArgumentUnchanged=not(attribute_mismatch or byref_mismatch),
        copiesCompleteSelectedTypeRecord=bool(attribute_mismatch or byref_mismatch),nativeCarrierCopyBytes=16 if allocate else None,
        attributesOffset=8,attributesBytes=2,byrefDwordOffset=8,byrefMask=1<<29,
        selectedOtherRecordBitsUnchanged=True,actualAllocation=allocate,allocatorContextCell=cell,statsCell=stats,
        validInitializedParameterPayloadAndBoundedInstantiationRequired=True,
        normalDisjointAllocationRequired=allocate is not None,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'])


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_inflated_method_class_paths import derive as inflated_source
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    from scripts.game_data.il2cpp.consumer_control import check_consumer_control
    from scripts.game_data.il2cpp.consumer_rva_switches import ordinary_entry_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=inflated_source(image,pins,**arguments)
    entry,={p['actualTypeSubstitution']for p in prior['proof']['selectedConstructorPrograms']}
    body=owned(image,entry);part=partition(image.mapper,body['regions'],entry,image_base=image.pe.image_base)
    paths=[kind_program(body['regions'],entry,kind=kind,image_base=image.pe.image_base)for kind in(17,19,30)]
    paths.append(kind_program(body['regions'],entry,kind=30,image_base=image.pe.image_base,method_instantiation_present=False))
    target,={p['actualResolverTarget']for p in paths if p['actualResolverTarget']is not None}
    tails={p['selectedBytes'][-2][0]:dict(target=target)for p in paths if p['actualResolverTarget']is not None}
    # The final E9 is recorded in two read pieces by BytesPath.relative.
    need('exact-var-and-mvar-external-tail-sites',len(tails)==2)
    graph=ordinary_entry_program(part,entry=entry,tail_exits=tails)
    resolver=owned(image,target);rows=[]
    for at,raw in resolver['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16))
    resolver_graph=check_consumer_control(rows,entry=target,owned_ranges=[(a,a+len(raw))for a,raw in resolver['regions']])
    resolved=[resolver_program(resolver['regions'],target,**kw)for kw in({},dict(attribute_mismatch=True),dict(byref_mismatch=True))]
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(inflatedMethodSource=prior,typeSourceWindows=body['windows'],partition=part,
            completeTypeSource=graph,selectedKindPrograms=paths,actualResolverWindows=resolver['windows'],
            completeResolver=resolver_graph,selectedResolverPrograms=resolved),
        actualNominalArgumentSubstitutionTransfersProved=True,initializedParameterPayloadOrMethodInfoIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete actual type/resolver code partitions, table/CFG/frame checks and selected kind17/VAR/MVAR/attribute/byref transfer paths.',
            conditional=__doc__,structuralOnly='Native generic type carrier substitution, not wire values.',
            unresolved=['initialized parameter payload, class/method instantiation and opaque allocation/helper effects',
                'complete class RGCTX and exact callback binding','concrete enum/list/parent/EOF'])),default=_json_set))
