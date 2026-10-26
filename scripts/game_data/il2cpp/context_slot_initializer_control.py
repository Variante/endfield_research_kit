"""Closed instruction graph and physical slot-loop geometry, below slot meaning."""
from __future__ import annotations
from collections import deque
from .relation_control import transfer


def validate_closed_initializer_graph(rows, *, entry_va):
    label='contextSlotInitializerGraph'
    by_at={int(r['va'],16):r for r in rows}
    if len(by_at)!=len(rows) or entry_va not in by_at:raise ValueError(label+'.entry-or-duplicate')
    edges={};calls=[];returns=[];traps=[]
    for at,row in by_at.items():
        raw=bytes.fromhex(row['bytes']);end=at+len(raw)
        if raw==b'\xcc':flow={'kind':'trap'}
        elif raw==b'\xff\xd0':flow={'kind':'registerCall','register':'rax'}
        else:flow=transfer(row)
        kind=flow['kind'];targets=[]
        if kind in ('next','conditional','call','indirectCall','registerCall'):targets.append(end)
        if kind in ('jump','conditional'):targets.append(flow['target'])
        if kind in ('call','indirectCall','registerCall'):calls.append({'site':at,**flow})
        elif kind=='return':returns.append(at)
        elif kind=='trap':traps.append(at)
        elif kind not in ('next','conditional','jump'):raise ValueError(label+'.unsupported-transfer:'+row['bytes'])
        if any(t not in by_at for t in targets):raise ValueError(label+'.nonlocal-or-interior-edge:'+row['va'])
        edges[at]=targets
    reached=set();pending=[entry_va]
    while pending:
        at=pending.pop()
        if at in reached:continue
        reached.add(at);pending.extend(edges[at])
    if reached!=set(by_at):raise ValueError(label+'.unreachable-owned-instructions')
    frames={entry_va:0};pending=deque([entry_va]);call_sites={r['site'] for r in calls}
    while pending:
        at=pending.popleft();row=by_at[at];delta=frames[at]
        head,_,args=row['text'].partition(' ')
        if head in ('push','pop'):
            if args=='rsp':raise ValueError(label+'.rsp-push-or-pop')
            delta+=-8 if head=='push' else 8
        elif args.split(',')[0]=='rsp' and head not in ('cmp','test'):
            if head not in ('add','sub') or not args.startswith('rsp, 0x'):raise ValueError(label+'.dynamic-frame')
            value=int(args.split(', ')[1],16);delta+=value if head=='add' else -value
        if at in call_sites and ((8+delta)%16 or -delta<32):raise ValueError(label+'.unaligned-call-or-missing-home-space')
        if at in returns and delta!=0:raise ValueError(label+'.return-frame')
        for target in edges[at]:
            if target in frames and frames[target]!=delta:raise ValueError(label+'.inconsistent-frame-join')
            if target not in frames:frames[target]=delta;pending.append(target)
    return {'instructionsChecked':len(rows),'allOwnedInstructionsReachable':True,
        'allLocalTargetsAreInstructionBoundaries':True,'normalCallsHaveAlignedHomeSpace':True,
        'allNormalReturnsRestoreEntryRsp':True,'calls':calls,'returnSites':returns,'trapSites':traps,
        'loopTerminationProved':False,'calleeEffectsProved':False,'runtimeExecutionKnown':False}


def validate_slot_loop_geometry(rows, *, loop_va, suffix_va, publication_va):
    """Check full shared advancement/back-edge and final source-array publication."""
    by_at={int(r['va'],16):r for r in rows};label='contextSlotLoopGeometry'
    def take(at,expected):
        row=by_at.get(at)
        if row is None or bytes.fromhex(row['bytes'])!=bytes.fromhex(expected):raise ValueError(label+'.instruction-at-'+hex(at))
        return at+len(bytes.fromhex(expected))
    at=suffix_va
    for raw in ('4983C410','4883C608','48897577','4983EE01','4C89757F'):at=take(at,raw)
    branch=by_at.get(at);raw=bytes.fromhex(branch['bytes']) if branch else b''
    if len(raw)!=6 or raw[:2]!=b'\x0f\x85' or at+6+int.from_bytes(raw[2:],'little',signed=True)!=loop_va:
        raise ValueError(label+'.remaining-count-back-edge')
    at+=6
    for raw in ('4C8B6D67','488B45AF','EB03'):at=take(at,raw)
    null_at=at;at=take(at,'488BC6')
    if at!=publication_va:raise ValueError(label+'.publication-successor')
    take(at,'498985C0000000')
    return {'inputDefinitionStrideBytes':16,'outputSlotStrideBytes':8,'countDecrement':1,
        'loopBackEdgeUsesRemainingCountNonzero':True,'publishedValueReloadsOriginalOutputArray':True,
        'classPublicationOffset':192,'loopByteAccountingOnly':True,
        'condition':'Positive compatible count, valid disjoint definition/output/frame storage and normal ABI-preserving loop callees. The prefix count/allocation and each slot producer remain separate obligations.'}


def validate_method_slot_argument_flow(rows, *, dispatch_va, producer_va, key_va, return_store_va):
    """Authenticate kind-three payload, two argument handoffs and stored return."""
    by_at={int(r['va'],16):r for r in rows};label='contextMethodSlotArgumentFlow';calls=[]
    def take(at,expected):
        row=by_at.get(at)
        if row is None or bytes.fromhex(row['bytes'])!=bytes.fromhex(expected):raise ValueError(label+'.instruction-at-'+hex(at))
        return at+len(bytes.fromhex(expected))
    def call(at):
        row=by_at.get(at);raw=bytes.fromhex(row['bytes']) if row else b''
        if len(raw)!=5 or raw[0]!=0xe8:raise ValueError(label+'.actual-direct-call')
        target=at+5+int.from_bytes(raw[1:],'little',signed=True);calls.append((at,target));return at+5,target
    at=take(dispatch_va,'418B4C24F8');at=take(at,'83F903')
    raw=bytes.fromhex(by_at[at]['bytes'])
    if len(raw)!=6 or raw[:2]!=b'\x0f\x84' or at+6+int.from_bytes(raw[2:],'little',signed=True)!=producer_va:
        raise ValueError(label+'.kind-three-dispatch-target')
    at=take(producer_va,'498B0C24');at=take(at,'8B09');at,_=call(at)
    for b in ('488BD8','41B001','498BD5','488B4808'):at=take(at,b)
    at,first=call(at);at=take(at,'488BF8')
    for b in ('41B001','498BD5','488B4B10'):at=take(at,b)
    at,second=call(at);take(at,'488BF0')
    if first!=second:raise ValueError(label+'.same-argument-transform-helper')
    at=key_va
    for b in ('4C8B33','4C8975EF','48897DF7','488975FF'):at=take(at,b)
    at=return_store_va
    for b in ('33D2','488BCB'):at=take(at,b)
    at,_=call(at);at=take(at,'488B7577');take(at,'488906')
    return {'selectedDefinitionKind':3,'definitionPayloadPointerRegister':'r12',
        'payloadIndexLoadBits':32,'descriptorArgumentOffsets':[8,16],
        'sameSavedContextRegisterForBothCalls':'r13','argumentTransformR8bValue':1,
        'constructedLocalKeyQwords':['descriptor QWORD at +0','first helper return','second helper return'],
        'returnProducerRcx':'selected descriptor/key pointer in rbx','returnProducerRdx':0,
        'sameFullReturnStoredToCurrentOutputSlot':True,'callSitesAndTargets':calls,
        'descriptorAndTransformSemanticsProved':False,'cacheSelectionOrCalleeEffectsProved':False,
        'condition':'Compatible descriptor/frame storage and normal Win64 nonvolatile/stack preservation; intervening cache/depth paths and helper results remain separate semantic obligations.'}


def validate_definition_range_prefix(rows, *, range_va, selected_count_va, loop_setup_va):
    """Bind the lookup count/start to definition stride and loop setup."""
    by_at={int(r['va'],16):r for r in rows};label='contextDefinitionRangePrefix'
    def take(at,expected):
        row=by_at.get(at)
        if row is None or bytes.fromhex(row['bytes'])!=bytes.fromhex(expected):raise ValueError(label+'.instruction-at-'+hex(at))
        return at+len(bytes.fromhex(expected))
    at=range_va
    for b in ('448B7808','4C637004','49C1E604','488B4338','4C037058','4585FF'):at=take(at,b)
    row=by_at.get(at);raw=bytes.fromhex(row['bytes']) if row else b''
    if len(raw)!=6 or raw[:2]!=b'\x0f\x84':raise ValueError(label+'.zero-count-guard')
    if at+6!=selected_count_va:raise ValueError(label+'.positive-count-successor')
    take(selected_count_va,'4963DF')
    at=loop_setup_va
    for b in ('488BF0','48894577','4D8D6608','4D8BF7','4C897D7F','4C8B6D97','4C8B7D6F'):at=take(at,b)
    return {'rangeStartSourceOffset':4,'rangeCountSourceOffset':8,'rangeStartSignExtended':True,
        'definitionEntryBytes':16,'moduleDefinitionArrayOffset':88,'definitionPayloadOffset':8,
        'outputCursorStartsAtCompatibleFillReturn':True,'sameRangeCountSavedForLoop':True,
        'genericContextReloadedFromSavedFrameSlot':True,
        'lookupSelectionAndFillReturnSemanticsProved':False}
