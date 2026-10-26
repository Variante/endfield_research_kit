"""Complete current tagged action-wrapper FF sources, separate from union FF.

Selected null wrapper outputs skip the existing-wrapper lifecycle hook. The
actual buffered helper or inline byte source then clears the complete output
reference and restores its original caller frame. Positive field programs and
parent union routes remain independently owned.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='skillWrapperNullSources'


def peek(g,n=1):return bytes(g.bytes[g.at+i]for i in range(n))


def initialized(g):
    if peek(g)==b'\x75':g.branch('75',True,1)
    elif peek(g)==b'\x74':g.branch('74',False,1)
    elif peek(g,2)==b'\x0f\x85':g.branch('0f85',True)
    else:g.branch('0f84',False)


def helper_ff_program(regions,entry,header,barrier):
    g=BytesPath(regions,entry);saved_rsi=peek(g,5)==bytes.fromhex('48895c2408')
    g.take('48895c2408'if saved_rsi else'48895c2418')
    if saved_rsi:g.take('4889742418')
    g.take('57','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bda','488bf9');initialized(g)
    g.take('488b0b','c644243800','4885c9')
    if peek(g,2)==b'\x0f\x85':g.branch('0f85',False)
    else:g.branch('74',True,1)
    g.take('488d542438','488bcf');g.call(header);g.take('84c0')
    if peek(g,2)==b'\x0f\x84':g.branch('0f84',True)
    else:g.branch('74',True,1)
    g.take('488bcb','48c70300000000');g.call(barrier)
    if peek(g)==b'\x90':g.take('90')
    if peek(g)==b'\xe9':g.jump('e9')
    elif peek(g)==b'\xeb':g.jump('eb',1)
    g.take('488b5c2430'if saved_rsi else'488b5c2440')
    if saved_rsi:g.take('488b742440')
    g.take('4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,headerTarget=header,
        headerBytes=1,marker=255,clearedReferenceBytes=8,initialOutputNull=True,
        prehookCalls=0,allocationCalls=0,barrierTarget=barrier,normalReturn=True,
        sameReader=True,sameOutput=True,entryRspRestored=True,
        restoredRegisters=['rbx','rsi','rdi']if saved_rsi else['rbx','rdi'])


def custom_inline_ff_program(regions,entry,offsets,*,image_base):
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in
        ('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2418','56','57','4155','4156','4157','4881ec80000000')
    flag=g.relative('803d')+1;g.take('00')
    if g.relative('4c8d2d')!=image_base:raise ValueError(LABEL+'.custom:image-base')
    g.take('488bf2','488be9');g.branch('0f85',True)
    g.take('488b3e','4885ff');g.branch('0f84',True)
    g.take('837d'+rem+'01');g.branch('7d',True,1)
    g.take('488b45'+cur,'440fb638','8b5d'+rem,'83eb01');g.branch('79',True,1)
    g.take('48ff45'+cur,'ff45'+adv,'ff45'+used,'895d'+rem,'4180ffff');g.branch('0f84',True)
    collector=g.relative('833d')+1;g.take('00','48c70600000000');g.branch('74',True,1)
    g.take('4c8d9c2480000000','498b5b30','498b6b40','498be3','415f','415e','415d','5f','5e','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,collectorFlag=collector,
        headerBytes=1,marker=255,clearedReferenceBytes=8,initialOutputNull=True,
        prehookCalls=0,allocationCalls=0,normalReturn=True,sameReader=True,sameOutput=True,
        readerEffects=dict(currentPtr=1,bufferLength=-1,advancedCount=1,consumed=1),
        entryRspRestored=True,restoredRegisters=['rbx','rbp','rsi','rdi','r13','r14','r15'])


def derive(image,pins,programs):
    """Join only current finite AbilityActionData routes supplied by the owner."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_timeline_current_sequence import validate_program
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    offsets=scalar.reader_offsets(image,LABEL);proofs=[];identities=set()
    for route in programs:
        validate_program(route)
        if route['family']!='AbilityActionData' or route['wrapperNullAdmitted']:continue
        identity=(route['family'],route['tag'])
        need('unique-current-wrapper-route',False,identity in identities);identities.add(identity)
        wrapper=_selected_wrapper(image,route['wrapperName'])
        need('same-current-wrapper-original',route['wrappedType'],wrapper.wrapped_type)
        method=pointer.methods(image,wrapper)['Deserialize'];entry=image.method_pointer_va(method)
        body=pointer.owned(image,entry);primitive_param.reader_abi(image,ctx,method,wrapper)
        if image.pe.bytes_at_va(entry,10)==bytes.fromhex('48895c240848896c2418'):
            program=custom_inline_ff_program(body['regions'],entry,offsets,image_base=base)
            model=json.loads((CONTRACTS_DIR/'model_view_state_controller_native.json').read_bytes())
            need('collector-source-selected-build',pins,model['nativeInputs'])
            collector=_barrier(image,base+model['collector']['entryRva'])
            need('same-actual-inline-disabled-collector',collector['result']['disabledFlagRva'],
                program['collectorFlag']-base)
            helper=None
        else:
            rows=body['rows'];headers=[];barriers=[]
            for index,row in enumerate(rows):
                raw=bytes.fromhex(row['bytes']);site=int(row['va'],16)
                if len(raw)!=5 or raw[0]!=0xe8:continue
                target=site+5+int.from_bytes(raw[1:],'little',signed=True)
                if index+1<len(rows)and bytes.fromhex(rows[index+1]['bytes'])==b'\x84\xc0':
                    headers.append(target)
                if index and bytes.fromhex(rows[index-1]['bytes'])==bytes.fromhex('48c70300000000'):
                    barriers.append(target)
            need('one-header-helper',1,len(set(headers)));need('one-null-output-barrier',1,len(set(barriers)))
            header=headers[0];barrier=barriers[0]
            program=helper_ff_program(body['regions'],entry,header,barrier)
            helper=vector_recorder(image)(header-base);primitive_param.object_header_source(image,helper,offsets)
            collector=_barrier(image,barrier)
        proofs.append(dict(family=route['family'],tag=route['tag'],wrapperName=wrapper.name,
            wrappedType=wrapper.wrapped_type,readerMethod=[method.index,wrapper.name,'Deserialize',entry-base],
            ownedWindows=body['windows'],program=program,headerSource=helper,collector=collector))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(status='validated-current-wrapper-null-paths',nativeInputs=pins,
        routes=proofs,unionNullAdmitted=False,positiveGrammarAdmitted=False,
        evidenceBoundary=dict(exact='Current finite tagged wrapper source FF, one-byte buffered header/cursor updates, full64-bit null output and complete original frame/nonvolatile return; no child callback or positive field is read on this selected route.',
            conditional='Actual parent union selects this exact generated wrapper callback; initialized coherent matching Reader/contexts, initial wrapper output null, buffered FF and nonwrapping disjoint storage, collector disabled and normal header/barrier/helper ABI.',
            unresolved=['existing nonnull prehook path','positive child grammar','reserved union markers','enabled collector/refill/error behavior','live provider selection','whole owner']))))
