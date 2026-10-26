"""Exact ordinary-program equivalence of a selected collection-empty clone.

Both programs initialize the same incoming MethodInfo context, return true for
a null incoming collection, otherwise invoke the same target with slot zero,
the same resolved context type and collection, and return whether EAX is zero.
Opaque helper behavior and live context compatibility remain conditional.
"""
import re
from scripts.game_data.il2cpp.initializer_control import control_transfer


def _program(rows, pattern, label):
    if len(rows)!=len(pattern):raise ValueError(label+'.instruction-count')
    start=int(rows[0]['va'],16);cursor=start
    for row,wanted in zip(rows,pattern):
        raw=bytes.fromhex(row['bytes'])
        if int(row['va'],16)!=cursor:raise ValueError(label+'.byte-partition')
        cursor+=len(raw)
        if wanted is not None and raw!=bytes.fromhex(wanted):raise ValueError(label+'.instruction-bytes')
    return start,cursor


def _target(row, opcode):
    raw=bytes.fromhex(row['bytes'])
    if len(raw)!=5 or raw[0]!=opcode:raise ValueError('collectionEmpty.transfer-bytes')
    return int(row['va'],16)+5+int.from_bytes(raw[1:],'little',signed=True)


def check_true_result_returns_false(rows,call_va):
    by_at={int(r['va'],16):r for r in rows}
    def following(row):
        result=by_at.get(int(row['va'],16)+len(bytes.fromhex(row['bytes'])))
        if result is None:raise ValueError('collectionEmpty.false-result-missing-instruction')
        return result
    test=following(by_at[call_va]);branch=following(test);flow=control_transfer(branch)
    if test['bytes']!='84 c0' or flow['kind']!='conditional' or flow.get('conditionCode')!=5:raise ValueError('collectionEmpty.true-result-guard')
    row=by_at[flow['target']]
    if bytes.fromhex(row['bytes']) not in (b'\x32\xc0',b'\x30\xc0'):raise ValueError('collectionEmpty.false-result-value')
    seen=set();row=following(row)
    for _ in range(16):
        at=int(row['va'],16)
        if at in seen:break
        seen.add(at);flow=control_transfer(row)
        if flow['kind']=='return':return dict(trueResultReturnsFalse=True,falseReturnVa=row['va'])
        if flow['kind']=='jump':row=by_at[flow['target']];continue
        if flow['kind']!='next' or not (row['text']=='nop' or re.fullmatch(r'mov (?:rbx|rbp|rsi|rdi|r1[2-5]), \[rsp(?:\+0x[0-9a-f]+)?\]',row['text']) or re.fullmatch(r'add rsp, 0x[0-9a-f]+',row['text']) or re.fullmatch(r'pop (?:rbx|rbp|rsi|rdi|r1[2-5])',row['text'])):break
        row=following(row)
    raise ValueError('collectionEmpty.false-result-return')


def check_collection_empty_clone(canonical, clone, indexed_type_leaf):
    common=['48895c2408','57','4883ec20','48837a3800']
    a=_program(canonical,common+['488bda','488bf9','7508','488bca',None,'4885ff','7504','b001','eb1e',
        '488b4b38','488b09',None,'33c9','4c8bc7','488bd0',None,'85c0','0f94c0','488b5c2430','4883c420','5f','c3'],'collectionEmpty.canonical')
    b=_program(clone,common+['488bfa','488bd9','742e','4885db','7433','488b4f38','33d2',None,
        '488bd0','33c9','4c8bc3',None,'85c0','7417','32c0','488b5c2430','4883c420','5f','c3','488bcf',None,'ebc8','b001','ebe7'],'collectionEmpty.clone')
    leaf=_program(indexed_type_leaf,['488bc1','4863ca','488b0cc8',None],'collectionEmpty.indexedTypeLeaf')
    if _target(clone[11],0xe8)!=leaf[0]:raise ValueError('collectionEmpty.indexed-type-entry')
    if _target(indexed_type_leaf[3],0xe9)!=_target(canonical[15],0xe8):raise ValueError('collectionEmpty.resolved-type-target')
    if _target(canonical[8],0xe8)!=_target(clone[24],0xe8):raise ValueError('collectionEmpty.context-initializer')
    if _target(canonical[19],0xe8)!=_target(clone[15],0xe8):raise ValueError('collectionEmpty.invoker-target')
    ranges=sorted((a,b,leaf))
    if any(left[1]>right[0] for left,right in zip(ranges,ranges[1:])):raise ValueError('collectionEmpty.overlapping-programs')
    for row in (canonical[8],canonical[15],canonical[19]):
        if any(start<=_target(row,0xe8)<end for start,end in ranges):raise ValueError('collectionEmpty.helper-inside-program')
    return dict(status='proved-program-equivalence',canonicalRange=list(a),cloneRange=list(b),indexedTypeLeafRange=list(leaf),
        contextInitializerVa=hex(_target(canonical[8],0xe8)),typeResolverVa=hex(_target(canonical[15],0xe8)),
        invokerVa=hex(_target(canonical[19],0xe8)),incomingCollectionAndMethodInfoBitsProved=True,
        invokerSlotZeroAndArgumentBitsProved=True,low32ZeroTestEquivalent=True,
        evidenceBoundary=dict(exact='Complete selected instruction grammars, byte partitions, branch displacements and shared physical helper targets.',
            conditional='Ordinary Win64 callees, stable compatible incoming MethodInfo context, successful context/type initialization and opaque shared helper behavior.',
            unresolved='Live generic context, exceptional/resumption behavior, replacement code and collection contents.'))
