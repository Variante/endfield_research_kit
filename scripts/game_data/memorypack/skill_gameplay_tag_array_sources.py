"""Current exact GameplayTag bulk-array source and nominal helper ownership.

Signed counts -1/0 and positive1..64 are separate selected paths. The actual
four-byte multiplier, buffered payload guard, unchanged allocation count,
independently typed data-reference source, bounded copy256 and all four Reader
updates establish raw4 elements; a managed size or reference-array owner does
not. No callback is used for bulk payload. Ready coherent contexts, normal
compatible typed allocations, disjoint stable buffered storage and copy/helper
ABI are explicit conditions. Runtime class/inflation/helper selection, larger
counts and enclosing Query/list/root framing remain unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_root_tag_query_sources import need,ELEMENT


def tag_array_program(regions,entry,offsets,s,*,count=1):
    if type(count)is not int or not -1<=count<=64:raise ValueError('tagArray.count')
    g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('48895c2410','48896c2418','4889742420','57','4883ec20','48837a3800','488bfa','488bd9')
    g.branch('0f84',False)
    g.take('488b4738','488b30','48837e3800');g.branch('0f84',False)
    g.take('837b'+rem+'04');g.branch('0f8c',False)
    g.take('488b43'+cur,'8b38','8b6b'+rem,'83c5fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','896b'+rem,
        '486343'+used,'488b53'+total,'482bd0','4863c7','483bd0');g.branch('0f8c',False)
    g.take('83ffff');g.branch('0f84',count==-1)
    if count==-1:g.take('33ff');g.jump('e9')
    else:
        g.take('85ff');g.branch('75',count>0,1)
        if count==0:
            g.take('488b4638','488b18','48837b3800');g.branch('0f84',False)
            g.take('488b4b38','33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('0f84',False)
            g.take('488b4b38','33d2');g.call(s['context'])
            g.take('488b88b8000000','488b39')
        else:
            g.take('4c89742430','448d34bd00000000','443b73'+rem);g.branch('0f8f',False)
            g.take('488b4638','488b6808','48837d3800');g.branch('0f84',False)
            g.take('488b4d38','33d2');g.call(s['context'])
            g.take('488bd7','488bc8');g.call(s['arrayAllocate'])
            g.take('488b5638','488bc8','488bf8','488b5210');g.call(s['dataReference'])
            g.take('488b53'+cur,'488bc8','458bc6');g.call(s['copy'])
            g.take('4585f6');g.branch('74',False,1)
            g.take('8b73'+rem,'412bf6');g.branch('0f88',False)
            g.take('440173'+adv,'4963c6','480143'+cur,'440173'+used,'8973'+rem,'4c8b742430')
            g.jump('e9')
    g.take('488b5c2438','488bc7','488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,countWitness=count,headerBytes=4,elementBytes=4,
        payloadBytes=max(0,count)*4,actualReader='incoming rcx preserved rbx',
        output='typed new/empty array or null returned rax unchanged from rdi',
        count='signed32 header saved edi',byteCount='r14d computed4*count without overflow under0..64',
        allocationCountPassedUnchanged=count>0,dataReferenceAndCopySourcesRequireIndependentProof=True,
        sameReaderCounters=True,normalReturn=True)


def data_reference_program(regions,entry):
    """Actual optimized typed GetArrayDataReference: selected nonnull array+32."""
    from scripts.game_data.memorypack.pooled_string_list_sources import flag
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec30','48837a3800','488bfa','488bd9');g.branch('74',False,1)
    g.take('488b4738','488b08','4883793800');g.branch('74',False,1)
    ready=flag(g);g.branch('74',False,1)
    g.take('4885db');g.branch('0f84',False);g.take('4883c320','488b4738','488b4808','4883793800');g.branch('74',False,1)
    g.take('488bc3','488b5c2440','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,normalReturn=True,entryRspRestored=True,
        result='same incoming nonnull RCX array address plus32',arrayDataOffset=32,
        concreteElementGrammarAdmitted=False,executedAsSpanCallInferred=False)


def derive(image,pins,*,typed_request,call_target,count_limit=64):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar,buff_gameplay_tag_native as atomic
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_unmanaged_array_context import derive as context_source
    from scripts.game_data.memory_copy_bounded_native import validate_components as copy_source
    _publication_gate(image,pins);need('bounded-bulk-count',True,type(count_limit)is int and 0<=count_limit<=64)
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    context=context_source(image,typed_request,element_type=ELEMENT)
    body=owned(image,call_target)
    def call(offset):
        rows=[r for r in body['rows']if int(r['va'],16)==call_target+offset]
        need('one-owned-direct-call',1,len(rows));raw=bytes.fromhex(rows[0]['bytes'])
        need('actual-E8',(5,232),(len(raw),raw[0]));return control_transfer(rows[0])['target']
    s={k:call(o)for k,o in dict(context=159,arrayAllocate=281,dataReference=300,copy=315).items()}
    offsets=scalar.reader_offsets(image,'gameplayTagArray');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    paths=[tag_array_program(body['regions'],call_target,offsets,s,count=n)for n in range(-1,count_limit+1)]
    data=owned(image,s['dataReference']);data_program=data_reference_program(data['regions'],s['dataReference'])
    fact=json.loads((CONTRACTS_DIR/'memory_copy_bounded_native.json').read_bytes())
    need('same-copy-native-pins',pins,fact['nativeInputs']);need('actual-bounded-copy-target',base+fact['entryRva'],s['copy'])
    copy=copy_source(image,fact);need('adequate-bulk-copy-bound',True,copy['maxBytes']>=count_limit*4)
    element=atomic.validate_on_image(image,pins)
    need('same-nominal-unmanaged-element',(ELEMENT,ctx.index.types[ELEMENT].index,17,4),
        (element['typeName'],element['typeDefinition'],element['contextTypeKind'],element['wireBytes']))
    _publication_gate(image,pins)
    capability=dict(elementType=ELEMENT,closedArrayType=ELEMENT+'[]',elementValueType=True,
        collectionCounts=[-1,0],positiveCountsAdmitted=count_limit>0,countLimit=count_limit,
        nullable=True,elementWireBytes=4,elementGrammarAdmitted=True,elementCapability='skill-root-gameplay-tag-raw4',
        arrayReaderMethodDefinition=typed_request['methodSpec'][0],arrayReaderTargetRva=call_target-base,
        bulkCopyProved=True,wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(schema='endfield.skill-gameplay-tag-array-source.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities={'skill-root-gameplay-tag-array':capability,
            'skill-root-gameplay-tag-raw4':dict(typeName=ELEMENT,elementValueType=True,managedBytes=4,wireBytes=4,
                nullable=False,wholeGrammarAdmitted=True,typeDefinition=element['typeDefinition'],contextTypeKind=17)},
        proof=dict(context=context,programs=paths,sourceWindows=body['windows'],dataReferenceProgram=data_program,
            dataReferenceWindows=data['windows'],copy=copy,element=element,symbolRvas={k:v-base for k,v in s.items()}),
        evidenceBoundary=dict(exact='Nominal GameplayTag array context, complete selected signed null/empty/positive1..64 source, raw4 multiplier and buffered byte-count/counter proof, actual data-reference array+32, copy0..256 and independently proved ordinary GameplayTag value4.',
            conditional=__doc__,structuralOnly='Stored tag array.',unresolved=['counts above64','enclosing parent/Query/root','runtime selection','physical EOF']))))
