"""Bounded compiled Recorder counter/queue facts for an existing producer DLL.

This validates a relocation-aware COFF/CRT cohort and finite machine programs.
Ordinary CRT copy/fill and x64 memory ordering remain premises; no runtime
delivery, Recorder epoch or whole-session admission follows.
The no-reset conclusion additionally requires compatible live objects and a
pop output Record disjoint from the complete Recorder storage (metadata and
queue). It excludes direct resets in these bodies; an aliasing copy destination
could otherwise overwrite counters despite the ordinary memcpy premise.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.coff_pe_match import CoffObject,PeImage,archive_members,bookended_inputs,match_function,cohort_bindings

SCHEMA='endfield.capture-checkpoint-recorder-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'capture_checkpoint_recorder_native.json'


def need(check,value):
    if not value:raise ValueError('checkpoint-recorder: '+check)


def _instruction(raw,rva):
    """Finite reviewed AMD64 vocabulary; reject hidden control instructions."""
    at=0;rex=0;operand16=False
    while at<len(raw)and(raw[at]in(0xf0,0x66,0xf2,0xf3)or 0x40<=raw[at]<=0x4f):
        if 0x40<=raw[at]<=0x4f:rex=raw[at]
        operand16=operand16 or raw[at]==0x66;at+=1
    need('instruction-prefix',at<len(raw));op=raw[at];at+=1
    if op in(0xe8,0xe9,0xeb)or 0x70<=op<=0x7f:
        width=1 if op==0xeb or 0x70<=op<=0x7f else 4
        need('relative-control-width',len(raw)==at+width)
        target=rva+len(raw)+int.from_bytes(raw[at:],'little',signed=True)
        if op==0xe8:return [rva+len(raw)],'call',target
        if op in(0xeb,0xe9):return [target],'jump',target
        return [rva+len(raw),target],'branch',target
    if op==0xc3:need('return-width',at==len(raw));return [],'return',None
    if op==0x90 or 0x50<=op<=0x5f:
        need('simple-instruction-width',at==len(raw));return [rva+len(raw)],'next',None
    if 0xb0<=op<=0xbf:
        width=1 if op<0xb8 else 8 if rex&8 else 2 if operand16 else 4
        need('mov-immediate-width',len(raw)==at+width);return [rva+len(raw)],'next',None
    if op in(0x05,0x25):
        need('accumulator-immediate-width',len(raw)==at+(2 if operand16 else 4));return [rva+len(raw)],'next',None
    immediate=0
    if op==0x0f:
        need('two-byte-opcode',at<len(raw));second=raw[at];at+=1
        if 0x80<=second<=0x8f:
            need('near-branch-width',len(raw)==at+4);target=rva+len(raw)+struct.unpack_from('<i',raw,at)[0]
            return [rva+len(raw),target],'branch',target
        need('reviewed-two-byte-opcode',second in(0x1f,0xb1,0x57,0x10,0x11))
    else:
        need('reviewed-opcode',op in(0x8b,0x89,0x8d,0x3b,0x33,0x32,0x03,0x2b,0x85,0x69,0x81,0x83,0x80,0xc6,0xc7,0xff))
        immediate=1 if op in(0x83,0x80,0xc6)else(2 if operand16 else 4)if op in(0x69,0x81,0xc7)else 0
    need('modrm-bound',at<len(raw));modrm=raw[at];at+=1;mod,rm=modrm>>6,modrm&7
    if op==0xff:need('no-indirect-control',((modrm>>3)&7)in(0,1))
    if mod!=3 and rm==4:
        need('sib-bound',at<len(raw));sib=raw[at];at+=1
        if mod==0 and sib&7==5:at+=4
    if mod==0 and rm==5:at+=4
    if mod==1:at+=1
    if mod==2:at+=4
    need('complete-finite-instruction',at+immediate==len(raw))
    return [rva+len(raw)],'next',None


def _program(function,pe=None):
    nodes={};edges={};flows={};at=function['rva'];end=at+function['bytes']
    for row in function['program']:
        raw=bytes.fromhex(row['hex']);need('contiguous-program',row['rva']==at and 0<len(raw)<=15)
        if pe is not None:need('native-program-bytes',pe.read(at,len(raw))==raw)
        destinations,kind,target=_instruction(raw,at);nodes[at]=raw;edges[at]=destinations;flows[at]=(kind,target);at+=len(raw)
    need('whole-program-extent',at==end)
    need('all-successors-owned',all(destination in nodes for values in edges.values()for destination in values))
    return nodes,edges,flows


def _dominates(nodes,edges,entry,left,right):
    seen=set();todo=[entry]
    while todo:
        at=todo.pop()
        if at==left or at in seen:continue
        seen.add(at);todo.extend(edges[at])
    return right not in seen


def _check_semantics(fact,pe=None):
    layout=fact['layout'];need('integer-layout',all(type(value)is int and value>=0 for value in layout.values()))
    cap=layout['capacity'];stride=layout['cellStride'];seq=layout['sequenceOffset'];record=layout['recordOffset']
    need('queue-geometry',0<cap<=1<<20 and cap&(cap-1)==0 and record==seq+8 and layout['recordBytes']+8==stride
        and seq+cap*stride<=layout['enqueueOffset']<layout['dequeueOffset']<1<<31)
    def disp(value):return struct.pack('<i',value).hex()
    def inc(base,offset,lock=True):
        prefix='f048ff'if lock else'48ff';rm={'rcx':1,'rbx':3}[base]
        if offset==0:return prefix+bytes([rm]).hex()
        if offset<=127:return prefix+bytes([0x40|rm,offset]).hex()
        return prefix+bytes([0x80|rm]).hex()+disp(offset)
    def zero_store(offset):return '488901'if offset==0 else'488941'+bytes([offset]).hex()
    graphs={key:_program(row,pe)for key,row in fact['functions'].items()}
    for fn,(nodes,edges,flows) in graphs.items():
        reachable=set();todo=[fact['functions'][fn]['rva']]
        while todo:
            at=todo.pop()
            if at in reachable:continue
            reachable.add(at);todo.extend(edges[at])
        required=[at for value in fact['roles'][fn].values()for at in(value if isinstance(value,list)else[value])]
        need('all-required-roles-reachable',all(at in reachable for at in required))
    # Complete push/pop programs cannot hide a counter reset behind an
    # otherwise admitted instruction. Stack spills and the two reviewed cell
    # stores are the only MOV-to-memory forms; ordinary CRT copying is a
    # separate stated premise and is checked at every call below.
    for fn,cell_role in [('push','publish'),('pop','freeStore')]:
        roles=fact['roles'][fn]
        atomics={roles[name]for name in(['attempted','state2Inc','state3Inc','nullFieldsInc','kindCounterInc','admitted','fullInc','contentionInc','dropped']if fn=='push'else['dequeueInc'])}
        for at,raw in graphs[fn][0].items():
            pos=0
            while raw[pos]in(0xf0,0x66,0xf2,0xf3)or 0x40<=raw[pos]<=0x4f:pos+=1
            op=raw[pos];pos+=1
            if op in(0x89,0xc6,0xc7,0x81,0x83,0xff):
                modrm=raw[pos];memory=modrm>>6!=3
                if not memory:continue
                if op==0x89:
                    rex=next((value for value in raw[:pos-1]if 0x40<=value<=0x4f),0)
                    stack=modrm&7==4 and raw[pos+1]==0x24 and not rex&1
                    need('no-hidden-memory-store',stack or at==fact['roles'][fn][cell_role])
                elif op==0xff:
                    need('only-reviewed-memory-increments',modrm>>3&7==0 and at in atomics)
                elif op in(0x81,0x83):need('no-hidden-memory-arithmetic',modrm>>3&7==7)
                else:need('no-hidden-memory-immediate-store',False)
            if op==0x0f and raw[pos]==0x11:need('no-hidden-vector-store',False)
            if op==0x0f and raw[pos]==0xb1:need('only-reviewed-memory-cas',fn=='push'and at==roles['reserve'])
    def exact(fn,role,value):
        at=fact['roles'][fn][role];need('role-owned-'+role,at in graphs[fn][0]);need('opcode-'+role,graphs[fn][0][at]==bytes.fromhex(value));return at
    def dominance(fn,left,right):
        nodes,edges,flows=graphs[fn];roles=fact['roles'][fn]
        need('dominance-'+left+'-'+right,_dominates(nodes,edges,fact['functions'][fn]['rva'],roles[left],roles[right]))
    def span(fn,role,expected):
        nodes,edges,flows=graphs[fn];at=fact['roles'][fn][role]
        for value in expected:need('ordered-span-'+role,nodes.get(at)==bytes.fromhex(value));at+=len(bytes.fromhex(value))
        return at
    exact('push','receiver','488bd9');exact('push','attempted',inc('rcx',layout['attempted']))
    for state,label in [(2,'unreadable'),(3,'truncated')]:
        role='state'+str(state);exact('push',role+'Cmp','8039'+bytes([state]).hex());at=exact('push',role+'Inc',inc('rbx',layout[label]))
        branch=fact['roles']['push'][role+'Branch'];raw=graphs['push'][0][branch]
        need('state-counter-guard',raw[0]==0x75 and graphs['push'][2][branch][1]==at+len(graphs['push'][0][at])
            and fact['roles']['push'][role+'Cmp']+3==branch and branch+len(raw)==at)
    exact('push','enqueueLoad','488bbb'+disp(layout['enqueueOffset']))
    exact('push','mask','25'+struct.pack('<I',cap-1).hex());exact('pop','mask','25'+struct.pack('<I',cap-1).hex())
    exact('push','stride','4869f0'+disp(stride));exact('pop','stride','4869f8'+disp(stride))
    exact('push','sequenceLoad','488b841e'+disp(seq));exact('pop','sequenceLoad','4c8b840f'+disp(seq))
    exact('push','reserve','f0480fb18b'+disp(layout['enqueueOffset']))
    push_roles=fact['roles']['push'];pn,pegs,pflows=graphs['push']
    rb=push_roles['reserveBranch'];need('reserve-success-to-copy',pn[rb][0]==0x74 and pflows[rb][1]==push_roles['copyStart'])
    need('push-copy-call-adjacent',span('push','copyStart',['488d8b'+disp(record),'41b8'+disp(layout['recordBytes']),'4803ce','498bd1'])==push_roles['copyCall'])
    exact('push','admitted',inc('rbx',layout['admitted']));exact('push','publish','4889841e'+disp(seq))
    need('publish-increment-value',span('push','admitted',[inc('rbx',layout['admitted']),'488d4701','90'])==push_roles['publish'])
    exact('push','trueValue','b001');exact('push','trueReturn','c3')
    exact('push','fullInc',inc('rbx',layout['queueFullDrops']));exact('push','contentionInc',inc('rbx',layout['contentionDrops']))
    exact('push','dropped',inc('rbx',layout['dropped']));exact('push','falseValue','32c0');exact('push','falseReturn','c3')
    exact('push','fullTest','4885c0');branch=push_roles['fullBranch']
    need('queue-full-guard',pn[branch][0]==0x78 and pflows[branch][1]==push_roles['fullInc'])
    exact('push','retryCmp','4883fa'+bytes([layout['retryLimit']]).hex())
    need('bounded-retry-branch',pn[push_roles['retryBranch']][0]==0x72)
    need('contention-joins-drop',pflows[push_roles['contentionJump']]==('jump',push_roles['dropped']))
    for left,right in [('attempted','trueReturn'),('attempted','falseReturn'),('copyCall','admitted'),('admitted','publish'),('publish','trueReturn'),('dropped','falseReturn'),('falseValue','falseReturn')]:dominance('push',left,right)
    exact('pop','receiver','488bd9');exact('pop','dequeueLoad','488b81'+disp(layout['dequeueOffset']))
    exact('pop','nextValue','48ffc0');exact('pop','sequenceCompare','4c3bc0')
    rn,redges,rflows=graphs['pop'];roles=fact['roles']['pop'];branch=roles['readyBranch']
    need('pop-compare-consumed-by-guard',span('pop','dequeueLoad',['488b81'+disp(layout['dequeueOffset']),'48ffc0','4c3bc0'])==branch)
    need('pop-sequence-guard',rn[branch][0]==0x74 and rflows[branch][1]==roles['copyStart'])
    need('pop-copy-call-adjacent',span('pop','copyStart',['488d91'+disp(record),'41b8'+disp(layout['recordBytes']),'4803d7','498bc9'])==roles['copyCall'])
    exact('pop','freeAdd','4805'+disp(cap));exact('pop','freeStore','4889841f'+disp(seq))
    after_call=roles['copyCall']+len(rn[roles['copyCall']])
    expected=['488b83'+disp(layout['dequeueOffset']),'90','4805'+disp(cap),'4889841f'+disp(seq)]
    for value in expected:
        need('pop-release-value-flow',rn.get(after_call)==bytes.fromhex(value));after_call+=len(bytes.fromhex(value))
    exact('pop','dequeueInc',inc('rbx',layout['dequeueOffset'],False));exact('pop','emptyValue','32c0')
    exact('pop','emptyReturn','c3');exact('pop','trueValue','b001');exact('pop','trueReturn','c3')
    for left,right in [('readyBranch','copyCall'),('copyCall','freeStore'),('freeStore','dequeueInc'),('dequeueInc','trueReturn'),('emptyValue','emptyReturn')]:dominance('pop',left,right)
    exact('ctor','zero','33c0');exact('ctor','receiver','4c8bf1')
    names=['attempted','admitted','dropped','unreadable','truncated','nullFields','queueFullDrops','contentionDrops','pairingFailures']
    stores=fact['roles']['ctor']['zeroStores'];need('initial-counter-count',len(stores)==len(names))
    for at,name in zip(stores,names):need('initial-counter-zero',graphs['ctor'][0].get(at)==bytes.fromhex(zero_store(layout[name])))
    exact('ctor','queueBase','498db6'+disp(seq));exact('ctor','zeroIndex','33ff');exact('ctor','zeroPosition','33c0')
    exact('ctor','enqueueReset','498986'+disp(layout['enqueueOffset']));exact('ctor','dequeueReset','4989be'+disp(layout['dequeueOffset']))
    exact('ctor','seqStore','48893e');exact('ctor','seqStride','488db6'+disp(stride));exact('ctor','seqInc','48ffc7')
    exact('ctor','seqCmp','4881ff'+disp(cap));branch=fact['roles']['ctor']['seqBranch']
    need('initial-sequence-loop',graphs['ctor'][0][branch][0]==0x72 and graphs['ctor'][2][branch][1]==fact['roles']['ctor']['seqStore'])
    return graphs


def _scope(fact):
    need('schema-status',fact.get('schema')==SCHEMA and fact.get('status')=='reviewed')
    expected=dict(compiledLocalRecorderEffects=True,allExternalRelocationsClosed=False,crtOrdinaryCopyAndFillPremise=True,
        platformX64MemoryOrderingPremise=True,noResetWithinPushPop=True,wholeProducerEpochProved=False,localDeliveryAdmitted=False,runtimeAdmission=False)
    need('rules',fact['rules'].keys()==expected.keys()and all(type(fact['rules'][key])is bool and fact['rules'][key]is value for key,value in expected.items()))
    need('function-coverage',set(fact['functions'])=={'ctor','push','pop'})


def validate_bytes(object_bytes,dll_bytes,archive_bytes,fact):
    _scope(fact)
    for key,raw in [('objectSha256',object_bytes),('producerDllSha256',dll_bytes),('crtArchiveSha256',archive_bytes)]:
        need('input-sha256-'+key,hashlib.sha256(raw).hexdigest()==fact['inputs'][key])
    obj=CoffObject(object_bytes);pe=PeImage(dll_bytes);matches={}
    members=list(archive_members(archive_bytes))
    for name,row in fact['crt'].items():
        selected=[member for member in members if member['offset']==row['memberOffset']and member['name']==row['memberName']]
        need('unique-CRT-member',len(selected)==1);raw=selected[0]['data'];need('CRT-member-sha256',hashlib.sha256(raw).hexdigest()==row['memberSha256'])
        result=match_function(CoffObject(raw),pe,row['symbol']);need('CRT-complete-candidate',result['unique']and result['candidates'][0]['rva']==row['rva']and result['sectionBytes']==row['bytes']);matches[name]=result
    bindings=cohort_bindings(list(matches.values()))
    for role,row in fact['functions'].items():
        result=match_function(obj,pe,row['symbol'],symbol_bindings=bindings)
        need('complete-Recorder-candidate',result['unique']and result['candidates'][0]['rva']==row['rva']and result['sectionBytes']==row['bytes']);matches[role]=result
    graphs=_check_semantics(fact,pe)
    for role,rows in [('push',[fact['roles']['push']['copyCall']]),('pop',[fact['roles']['pop']['copyCall']]),('ctor',fact['roles']['ctor']['calls'])]:
        target=fact['crt']['memset'if role=='ctor'else'memcpy']['rva']
        observed=[at for at,value in graphs[role][2].items()if value[0]=='call'];need('complete-copy-call-coverage',observed==rows)
        need('physical-CRT-cohort-targets',all(graphs[role][2][at]==('call',target)for at in rows))
    return dict(schema='endfield.capture-checkpoint-recorder-native-audit.v1',status='validated',inputs=fact['inputs'],rules=fact['rules'],
        matches=matches,layout=fact['layout'],evidenceBoundary=fact['evidenceBoundary'],
        compiledLocalFacts=['entry/state2/state3/admitted/drop counter increments','copy-before-admission-before-sequence publication','sequence guard before pop copy; copy-before-cell release-before-dequeue increment','constructor zero counters and positions; sequence-index initialization','no local counter reset in complete push/pop programs'],
        functionIdentityTier='bounded-relocation-aware-COFF-and-CRT-cohort',allExternalRelocationsClosed=False,wholeProducerEpochProved=False,localDeliveryAdmitted=False,runtimeAdmission=False)


def validate(*,object_path,dll_path,crt_library,contract_path=CONTRACT_PATH):
    paths=[Path(value).resolve()for value in [object_path,dll_path,crt_library,contract_path]]
    try:
        with bookended_inputs(paths)as(data,identities):
            result=validate_bytes(data[paths[0]],data[paths[1]],data[paths[2]],json.loads(data[paths[3]]));result['sourceInputs']=identities
        return result
    except(ValueError,KeyError,IndexError,TypeError,OSError,struct.error)as error:
        return dict(status='refused',detail=str(error),localDeliveryAdmitted=False,runtimeAdmission=False)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--object',dest='object_path',type=Path,required=True);parser.add_argument('--dll',dest='dll_path',type=Path,required=True)
    parser.add_argument('--crt-library',type=Path,required=True);parser.add_argument('--contract',dest='contract_path',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/battle_sim/capture_checkpoint_recorder_native.json')
    args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('--output must be below reports/')
    result=validate(object_path=args.object_path,dll_path=args.dll_path,crt_library=args.crt_library,contract_path=args.contract_path)
    if result['status']=='validated':args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],detail=result.get('detail'),localDeliveryAdmitted=False,runtimeAdmission=False)))
    return 0 if result['status']=='validated'else 2


if __name__=='__main__':raise SystemExit(main())
