"""Finite UTF16 string effects for the actual Patrol three-string caller.

The proof selects warm cached storage and explicit class, Type, TLS and context
identities. Those selections are conditions, never observations of execution.
Only pure byte algorithms are reused from the older string domain.
"""
from functools import lru_cache
import hashlib
import json

from scripts.game_data.il2cpp import fmv_string_sources as strings
from scripts.game_data.il2cpp import forward_copy_sources as copying
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as packets

SCHEMA = 'endfield.story-patrol-concat-string-sources.v1'


def need(check, condition, detail=None):
    if not condition:
        raise ValueError('patrolConcatStrings.' + check + ':' + str(detail)[:700])


@lru_cache(maxsize=1)
def _mapper():
    # Loading a stateless decoder does not open an installed native image.
    from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH
    from scripts.game_data.il2cpp.protocol import load_native_mapper
    return load_native_mapper(NATIVE_MAPPER_PATH)


def string_rows(packet, base, mapper=None):
    from scripts.game_data.il2cpp.string_source_instructions import decode_string_source_instructions
    from scripts.game_data.il2cpp.text_source_instructions import decode_text_instruction
    mapper = mapper or _mapper()

    class Decoder:
        def decode_one_x64(self, raw, offset, at):
            return decode_text_instruction(raw, offset, at) or mapper.decode_one_x64(raw, offset, at)

    result = []
    for at, raw in packets.regions(packet, base):
        rows = decode_string_source_instructions(Decoder(), raw, at)
        need('complete-string-instruction-partition', b''.join(bytes.fromhex(r['bytes']) for r in rows) == raw)
        result += rows
    return result


def locate(packet, base, pattern):
    pattern = bytes.fromhex(pattern)
    hits = [at + i for at, raw in packets.regions(packet, base)
            for i in range(len(raw) - len(pattern) + 1) if raw[i:i + len(pattern)] == pattern]
    need('unique-actual-program-boundary', len(hits) == 1, dict(pattern=pattern.hex(), hits=hits))
    return hits[0]


def locations(caller, mapper=None):
    p = caller['proof']; base = p['imageBase']; h = p['helpers']
    ar = string_rows(h['append'], base, mapper); sr = string_rows(h['string_ctor'], base, mapper)
    ae = locate(h['append'], base, '4183f820')
    af = locate(h['append'], base, '017308488b742478488b6c2470')
    se = locate(h['string_ctor'], base, '4183f820')
    sf = locate(h['string_ctor'], base, '488bc6488b5c2438488b6c2440')
    ac = packets._calls([r for r in ar if ae <= int(r['va'], 16) < af and bytes.fromhex(r['bytes'])[:1] == b'\xe8'])
    need('one-actual-append-copy-target', len(ac) == 1)
    all_calls = packets._calls([r for r in ar if bytes.fromhex(r['bytes'])[:1] == b'\xe8'])
    sc = packets._calls([r for r in sr if bytes.fromhex(r['bytes'])[:1] == b'\xe8'])
    need('actual-context-and-allocator-calls', bool(all_calls) and bool(sc))
    return dict(appendCopyEntryRva=ae-base, appendCopyFinishRva=af-base,
        stringCopyEntryRva=se-base, stringCopyFinishRva=sf-base,
        copyTargetRva=ac[0][1]-base, allocateTargetRva=sc[0][1]-base,
        typeContextTargetRva=all_calls[0][1]-base)


def cached_dispose(regions, entry):
    g=BytesPath(regions,entry);classes=[];tls=[]
    g.take('4053','4883ec20');ready=g.relative('803d')+1;g.take('00','488bd9');g.branch('75',True,1)
    g.take('48833b00');g.branch('0f84',False)
    g.take('807b0c00','4889742440','48897c2448');g.branch('74',False,1)
    classes.append(g.relative('488b05'));g.take('488b33','48896c2430','83b8e000000000');g.branch('75',True,1)
    index=g.relative('488b0d');g.take('4863a810010000','8b09');tls.append(g.relative('ff15'))
    g.take('488bf8','4885c0');g.branch('75',True,1)
    g.take('488b4710','488b4060','488b0ce8','488b6c2430','483b31');g.branch('74',True,1)
    g.take('4533c9');barrier=g.relative('44390d');g.take('4c890b');g.branch('74',True,1)
    g.take('44894b08','44384b0c');g.branch('74',False,1)
    classes.append(g.relative('488b05'));g.take('443988e0000000');g.branch('75',True,1)
    need('same-dispose-TLS-index',g.relative('488b0d')==index)
    g.take('4863b810010000','8b09');tls.append(g.relative('ff15'))
    g.take('488bd8','4885c0');g.branch('75',True,1)
    g.take('488b4310','488b4060','488b0cf8','c6410800','488b742440','488b7c2448','4883c420','5b','c3')
    need('same-dispose-class-import',len(set(classes))==len(set(tls))==1)
    return dict(selectedBytes=g.seen,metadataReadyFlagVa=ready,builderClassCellVa=classes[0],tlsIndexCellVa=index,
        tlsImportCellVa=tls[0],barrierFlagCellVa=barrier,requiredSameNonNullThreadBuffer=True,
        requiredUsesThreadStaticBuffer=True,requiredBarrierFlagZero=True,
        writes=dict(builderBuffer=0,builderIndex=0,threadBufferUsed=False),builderBufferOffset=0,
        builderIndexOffset=8,threadUsedFlagOffset=8,charPayloadWrites=0,externalPoolCallbacks=0,
        entryRspRestored=True,frameBytes=40,callShadow=[0,32],restoredNonvolatiles=['rbx','rbp','rsi','rdi'],
        returnedStringArgumentAbsent=True,
        condition='Ready builder class and metadata; same stable compatible nonnull TLS storage and scratch char[] as construction; builder uses its thread buffer; barrier flag0. All storage is disjoint from the returned String. TLS getter returns normally and consistently. Alternate pool/cold/barrier paths are separate.')


def replay_copy(value, packet, rep, base, pins, mapper=None):
    need('current-copy-schema-inputs',value.get('schema')=='endfield.forward-copy-source.v1' and value.get('nativeInputs')==pins)
    packets.verify_packet(packet); need('same-copy-entry',value['entryRva']==packet['entryRva'])
    need('same-all-owned-copy-windows',value['proof']['windows']==packet['windows'])
    mapper = mapper or _mapper(); regions = packets.regions(packet,base)
    rows=[r for at,raw in regions for r in copying.decode(mapper,raw,at)]
    need('complete-copy-byte-partition',b''.join(bytes.fromhex(r['bytes'])for r in rows)==b''.join(raw for _,raw in regions))
    tables={}
    for window in value['proof']['tables']:
        raw=bytes.fromhex(window['rawHex'])
        need('complete-copy-table-window',window['endRva']-window['startRva']==len(raw) and
            hashlib.sha256(raw).hexdigest().upper()==window['sha256'])
        need('unique-copy-table',window['startRva']not in tables);tables[window['startRva']]=raw
    raw=bytes.fromhex(rep['rawHex']);descriptor={k:v for k,v in rep.items()if k!='rawHex'}
    need('exact-reachable-rep-prefix',descriptor==value['proof']['repReachablePrefix'] and
        len(raw)==16 and rep['endRva']-rep['startRva']==len(raw) and
        hashlib.sha256(raw).hexdigest().upper()==rep['sha256'] and rep['physicalExtentProved']is False)
    replay=copying.prove(regions,base+packet['entryRva'],rows=rows,tables=tables,
        rep_rows=copying.decode(mapper,raw,base+rep['startRva']),image_base=base,max_bytes=256)
    need('complete-current-copy-replay',json.loads(json.dumps(replay))==value['proof']['program'] and value['maxBytes']==256)
    return replay


def prove(caller, proof, pins, mapper=None):
    p=caller['proof'];base=p['imageBase'];helpers=p['helpers'];where=locations(caller,mapper)
    need('same-locations',where==proof['locations'])
    allocated=proof['allocatedSource'];packets.verify_packet(allocated)
    need('actual-allocator-entry',allocated['entryRva']==where['allocateTargetRva'])
    copier=proof['copySource'];need('actual-copy-entry',copier['entryRva']==where['copyTargetRva'])
    copy=replay_copy(copier,proof['copyPacket'],proof['repPrefix'],base,pins,mapper)
    create=strings.cached_builder(packets.regions(helpers['create'],base),base+helpers['create']['entryRva'])
    append=strings.append_string(packets.regions(helpers['append'],base),base+helpers['append']['entryRva'],string_rows(helpers['append'],base,mapper),
        substring=False,type_context=base+where['typeContextTargetRva'],copy_entry=base+where['appendCopyEntryRva'],
        copy_finish=base+where['appendCopyFinishRva'],copy_target=base+where['copyTargetRva'],length=128,index=0,capacity=128)
    final=strings.final_string(packets.regions(helpers['string_ctor'],base),base+helpers['string_ctor']['entryRva'],string_rows(helpers['string_ctor'],base,mapper),
        allocate=base+where['allocateTargetRva'],copy_entry=base+where['stringCopyEntryRva'],copy_finish=base+where['stringCopyFinishRva'],
        copy_target=base+where['copyTargetRva'],count=128,start=0,array_length=128)
    allocations=[strings.cached_string(packets.regions(allocated,base),base+allocated['entryRva'],mode=m,count=n)
        for m in(0,3)for n in range(1,129)]
    dispose=cached_dispose(packets.regions(helpers['dispose'],base),base+helpers['dispose']['entryRva'])
    caller_class=p['programs'][0]['typedClassUsageSites']['builderClass'][0]['cellVa']
    need('same-builder-class-across-helpers',caller_class==create['sourceClassCell']==dispose['builderClassCellVa'] and
        [v for k,v in append['cells']if k=='builderClass']==[caller_class])
    need('same-create-dispose-TLS-storage',create['tlsIndexCell']==dispose['tlsIndexCellVa'] and create['tlsImportCell']==dispose['tlsImportCellVa'])
    fields={r['name']:r['field']for r in p['builderFields']}
    need('exact-own-builder-value-layout',fields==dict(buffer=['Cysharp.Text.Utf16ValueStringBuilder','char[]',16],
        index=['Cysharp.Text.Utf16ValueStringBuilder','int',24],usesThreadStaticBuffer=['Cysharp.Text.Utf16ValueStringBuilder','bool',28]))
    need('exact-current-string-value-layout',proof['stringFields']==dict(length=['System.String','int',16],firstChar=['System.String','char',20]))
    transitions=[(i,n)for i in range(129)for n in range(129-i)]
    need('all-bounded-index-count-transitions',len(transitions)==8385 and all(0<=i+n<=128 and 2*n<=copy['maxBytes']for i,n in transitions))
    return dict(create=create,append=append,finalString=final,allocations=allocations,dispose=dispose,
        sourceJoins=dict(sameBuilderClass=True,sameCreateDisposeTls=True,sameActualCopyTarget=True,
            sameActualAllocationTarget=True,ownBuilderAndStringLayouts=True,allCopyProgramsReplayed=True),
        composition=dict(maxTotalUtf16Chars=128,maxCopiedBytes=256,builderCapacityMinimum=128,
            initialBuilderIndex=0,orderedStringArguments=[0,1,2],nullContributesChars=0,
            allPrefixCountPairs=8385,allPositiveAllocatorCountModes=256,
            induction='For each selected nonnull argument, preserve the existing prefix, copy its exact full UTF16 payload to buffer[index:], then set index=index+length. Null arguments preserve the prefix. Each valid prefix/count pair has sum<=128; the bound applies at all three stages.',
            emptyResult='Same canonical live System.String.Empty static reference, with length0 condition.',
            positiveResult='Fresh selected allocation with exact concatenated UTF16 payload, length and zero terminator; unchanged returned reference across Dispose.',
            disposedBuilderCannotWriteReturnedString=True,allRuntimeProviderIdentitiesConditional=True))


def derive(image,pins,caller):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _publication_gate(image,pins);base=image.pe.image_base;where=locations(caller,image.mapper)
    copy=copying.derive(image,pins,entry=base+where['copyTargetRva'],max_bytes=256)
    prefix=dict(copy['proof']['repReachablePrefix']);prefix['rawHex']=image.pe.bytes_at_va(base+prefix['startRva'],16).hex()
    ctx=NativeReferenceContext(image);fields={}
    for f in image.metadata.fields_for(ctx.index.types['System.String']):
        if ctx.field_attributes(f.type_index)&16:continue
        name=image.metadata.string(f.name_index);row=ctx.field('System.String::'+name)
        if row[1:]==('int',16)or list(row[1:])==['int',16]:fields['length']=list(row)
        if row[1:]==('char',20)or list(row[1:])==['char',20]:fields['firstChar']=list(row)
    proof=dict(locations=where,allocatedSource=packets.packet(image,base+where['allocateTargetRva']),
        copySource=copy,copyPacket=packets.packet(image,base+where['copyTargetRva']),repPrefix=prefix,stringFields=fields)
    proof['programs']=prove(caller,proof,pins,image.mapper)
    value=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-bounded-concat-string-effects',nativeInputs=pins,proof=proof,
        concatStringEffectsProved=True,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Actual helper entries and owned bytes, current copy family/tables/REP, complete cached String count/mode domain, builder layout, UTF16 prefix/count induction and unchanged normal return.',
            conditional='Ready own classes/metadata/typed span contexts; canonical corresponding Type.GetTypeFromHandle results; canonical live String.Empty length0. Same stable nonnull TLS cached char[] with capacity>=128 and unused flag0. Stable sources, disjoint scratch/output/frame/global state; total UTF16 length<=128. Actual context helper calls preserve these identities and storage. String allocator selects a compatible disjoint cached block, canonical String class, supported mode0or3, lockFlag0, profilerMask0x80 clear; barrier flags0, ordinary supported Win64/SIMD/DF=0 ABI. No concurrent interference.',
            unresolved=['actual class/MethodInfo/Type/TLS/allocator provider selection and invocation','non-string arguments, total length above128, growth/cold/non-temporal/overlap/exceptional paths','asset/controller ownership, activation and playback']))))
    validate(value,pins,caller);_publication_gate(image,pins);return value


def validate(value,pins,caller):
    need('schema-native-inputs',value.get('schema')==SCHEMA and value.get('nativeInputs')==pins)
    need('complete-program-replay',json.loads(json.dumps(prove(caller,value['proof'],pins)))==value['proof']['programs'])
    need('conditional-source-flags',value.get('concatStringEffectsProved')is True and value.get('runtimeInvocationObserved')is False and value.get('playbackProved')is False)
    return value
