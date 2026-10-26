"""Actual metadata virtual-word to plain MethodInfo resolver transfer.

The complete current encoded-method resolver has its owned byte partition,
CFG and normal local/tail frames checked. Its selected tag3 path extracts the
actual definition index from the same encoded metadata word and tail-calls
the independently proved definition-cache/class-method-ordinal resolver with
that unchanged index. Tag6 instead requests a MethodSpec key and transfers
the returned key to the distinct inflated-method helper; it is not treated as
the plain definition path. Both actual external tails are explicit witnesses.

The exact RuntimeType MakeGenericType metadata slot, declaring class, ordinal
and token are joined to the same independently proved plain descriptor source
programs. Coherent initialized class/method caches, descriptor storage, actual
class identity and normal disjoint opaque helper effects remain conditions.
The source does not observe an initialized MethodInfo pointer, prove the tag6
inflated context, native target overrides or establish the concrete enum
formatter callback. No list/wire/parent or whole owner is admitted.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-encoded-method-paths.v1'
LABEL='enumEncodedMethodPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry,*,tag):
    need('literal-selected-method-tag',type(tag)is int and tag in(3,6))
    g=BytesPath(regions,entry);g.take('4883ec28','8bc1','c1e91d','d1e8','25ffffff0f','85c9')
    g.branch('74',False,1);g.take('83f903');g.branch('74',tag==3,1)
    helper=None
    if tag==6:
        g.take('83f906');g.branch('75',False,1)
        g.take('8bc8');helper=g.relative('e8');g.take('33d2','488bc8')
    else:g.take('8bc8')
    g.take('4883c428');tail=g.at;target=g.relative('e9')
    return dict(selectedBytes=g.seen,entry=entry,tag=tag,inputRegister='ecx',kindShift=29,
        definitionOrSpecIndexShift=1,definitionOrSpecIndexMask=0x0fffffff,
        actualKeyResolver=helper,tailInstruction=tail,tailTarget=target,
        outgoingArguments=dict(ecx='unchanged extracted definition index')if tag==3 else
            dict(rcx='unchanged actual MethodSpec-key resolver return',edx=0),
        entryRspRestoredBeforeTail=True,nonvolatilesUnchanged=True,
        actualReturnedMethodInfoIdentityProved=False)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_plain_method_descriptor_paths import derive as descriptor_source
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import derive as reflection_source,decode
    from scripts.game_data.il2cpp.consumer_control import check_consumer_control
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.memorypack.pointer_param import owned
    expected={'seed_entry','selection_entry','primitive_entry','enum_requests','normalizer_entry','publication_entry','fixup_arguments'}
    need('explicit-complete-source-arguments',set(arguments)==expected
        or set(arguments)==expected|{'enum_variant'}and arguments['enum_variant']=='byte')
    _publication_gate(image,pins);descriptor=descriptor_source(image,pins,**arguments)
    reflection_arguments={k:arguments[k]for k in('enum_requests','normalizer_entry','publication_entry','fixup_arguments')}
    if 'enum_variant'in arguments:reflection_arguments['enum_variant']=arguments['enum_variant']
    reflection=reflection_source(image,pins,**reflection_arguments)
    target=reflection['proof']['metadataSlot']['resolverTarget'];body=owned(image,target);rows=[]
    for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda r:int(r['va'],16));paths=[program(body['regions'],target,tag=tag)for tag in(3,6)]
    tails={p['tailInstruction']:dict(target=p['tailTarget'])for p in paths}
    graph=check_consumer_control(rows,entry=target,owned_ranges=[(a,a+len(raw))for a,raw in body['regions']],tail_exits=tails)
    graph['edges']={a:sorted(v)for a,v in graph['edges'].items()}
    plain=descriptor['proof']['methodKeySource'];definition_entry=plain['proof']['definitionPrograms'][0]['selectedBytes'][0][0]
    need('same-independent-actual-definition-resolver',paths[0]['tailTarget']==definition_entry)
    key_entry=plain['proof']['methodTableSeedSource']['proof']['keyResolverPrograms'][0]['selectedBytes'][0][0]
    need('same-independent-actual-MethodSpec-key-resolver',paths[1]['actualKeyResolver']==key_entry)
    selected,=[row for row in reflection['proof']['selectedSlotMethods']if row['method'][1]=='System.RuntimeType']
    word=selected['rawVtableWord'];method=image.metadata.methods[selected['method'][0]]
    need('exact-selected-vtable-tag3-definition',word>>29==3 and(word>>1)&0x0fffffff==method.index
        and word==(0x60000000|(method.index<<1)|1))
    md=image.metadata;td=md.types[method.declaring_type];section=md.sections['methods']
    raw=md.buf[section.offset+method.index*md.method_record_size:section.offset+(method.index+1)*md.method_record_size]
    need('same-source-proved-record-token-geometry',md.method_record_size==descriptor['proof']['recordSource']['methodRecordBytes']==32)
    name,declaring=struct.unpack_from('<ii',raw);token=struct.unpack_from('<I',raw,20)[0]
    need('same-selected-MethodInfo-definition-record',name==method.name_index and declaring==td.index==selected['typeDefinition']
        and token==method.token and td.method_start<=method.index<td.method_start+td.method_count
        and md.type_full_name(td)=='System.RuntimeType'and md.string(name)=='MakeGenericType')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(descriptorSource=descriptor,reflectionSource=reflection,encodedResolverWindows=body['windows'],
            encodedResolverCfg=graph,encodedResolverPaths=paths,selectedMethod=dict(method=selected['method'],
                rawMetadataVtableWord=word,rawMetadataMethodRecordHex=raw.hex().upper(),token=token,
                declaringTypeDefinition=td.index,classMethodStart=td.method_start,ordinal=method.index-td.method_start)),
        exactPlainDefinitionIndexOrdinalAndTokenTransferProved=True,actualInitializedMethodInfoPointerIdentityProved=False,
        inflatedMethodInfoAndContextProved=False,concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,
        wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete current encoded resolver partition/CFG/normal-tail frames; actual tag3 definition and distinct tag6 key/helper transfers, exact RuntimeType metadata record/slot and same plain descriptor programs.',
            conditional=__doc__,structuralOnly='Encoded metadata word, definition/ordinal/token and MethodInfo resolver transfers.',
            unresolved=['initialized class/method cache/descriptor identity and opaque aliases','inflated generic MethodInfo/RGCTX and target overrides',
                'reflection construction/default-provider selection','concrete enum callback','wire/parent/EOF']))))
