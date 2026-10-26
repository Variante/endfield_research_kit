"""Ordinary active-area call lanes and result store; callee rule is separate."""
from scripts.game_data.il2cpp.body_claims import _REGISTER_ROOT


def check_area_call_program(program, refs, *, entry, fields, sensitive_pointer):
    rows=program['rows'];edges=program['control']['edges'];origins=refs['registerOrigins'];by_at={int(r['va'],16):r for r in rows}
    def fail(check):raise ValueError('levelscriptAreaCall.'+check)
    def reaches(start,target,blocked=()):
        seen=set();pending=[start]
        while pending:
            at=pending.pop()
            if at in blocked or at in seen:continue
            if at==target:return True
            seen.add(at);pending.extend(edges[at]-seen)
        return False
    def dominates(source,target):
        if not reaches(source,target) or reaches(entry,target,{source}):fail('source-dominance')
    def one(raw):
        found=[r for r in rows if bytes.fromhex(r['bytes'])==raw]
        if len(found)!=1:fail('unique-instruction:'+raw.hex())
        return found[0]
    def at(row):return int(row['va'],16)
    def writes(row,register):
        head,_,rest=row['text'].partition(' ')
        if head in ('cmp','test','bt','push','nop','prefetch') or head.startswith('j'):return False
        if head=='call':return register in ('rax','rcx','rdx','r8','r9','r10','r11')
        operands=rest.split(',')
        if head not in ('xchg','xadd'):operands=operands[:1]
        return any(_REGISTER_ROOT.get(operand.strip())==register for operand in operands)
    def preserved(source,target,register):
        dominates(source,target)
        for address,row in by_at.items():
            if address not in (source,target) and reaches(source,address) and reaches(address,target) and writes(row,register):fail('register-clobber:'+register)
    if any(type(v)is not int or not 16<=v<=127 for v in fields.values()):fail('disp8-fields')
    spans=sorted((fields[role],fields[role]+width) for role,width in [('within',1),('enter',8),('exit',8)])
    if any(left[1]>right[0] for left,right in zip(spans,spans[1:])):fail('overlapping-fields')
    sources={role:one(prefix+bytes((fields[role],))) for role,prefix in [('within',bytes.fromhex('440fb676')),('enter',bytes.fromhex('4c8b66')),('exit',bytes.fromhex('4c8b6e'))]}
    sensitive=one(bytes.fromhex('440fb6f8'))
    calls=[r for r in rows if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8
        and at(r)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)==sensitive_pointer]
    if len(calls)!=1:fail('unique-sensitive-getter')
    getter=calls[0]
    if origins[at(getter)]['rcx']!=['this']:fail('getter-receiver')
    preserved(at(getter),at(sensitive),'rax')
    for row in sources.values():
        if origins[at(row)]['rsi']!=['this']:fail('field-receiver')
    setup=[bytes.fromhex(raw) for raw in ('4c8d4c2430','4d8bc5','f20f11442430','498bd4','895c2438','410fb6cf','4488742420')]
    starts=[i for i in range(len(rows)-len(setup)) if [bytes.fromhex(r['bytes']) for r in rows[i:i+len(setup)]]==setup]
    if len(starts)!=1:fail('unique-five-argument-setup')
    start=starts[0];block=rows[start:start+8];call=block[-1];raw=bytes.fromhex(call['bytes'])
    if len(raw)!=5 or raw[0]!=0xe8:fail('direct-rule-call')
    for before,after in zip(block,block[1:]):
        if at(before)+len(bytes.fromhex(before['bytes']))!=at(after):fail('setup-byte-partition')
        if {source for source,targets in edges.items() if at(after) in targets}!={at(before)}:fail('setup-bypass')
    for role,register in [('within','r14'),('enter','r12'),('exit','r13')]:preserved(at(sources[role]),at(call),register)
    preserved(at(sensitive),at(call),'r15')
    result=one(bytes.fromhex('0fb6d8'));store=one(bytes.fromhex('885e')+bytes((fields['within'],)))
    if at(result)!=at(call)+5 or {source for source,targets in edges.items() if at(result) in targets}!={at(call)}:fail('result-bypass')
    preserved(at(result),at(store),'rbx')
    if origins[at(store)]['rsi']!=['this']:fail('store-receiver')
    return dict(callSiteOffset=at(call)-entry,withinStoreOffset=at(store)-entry,
        optimizedCalleeVa=hex(at(call)+5+int.from_bytes(raw[1:],'little',signed=True)),
        callSitePassesFieldsInSignatureOrder=True,callResultStoredToWithin=True,
        sourceOffsets={role:at(row)-entry for role,row in sources.items()},sensitiveGetterOffset=at(getter)-entry,
        evidenceBoundary='conditional',condition='Typed original fields and getter, ordinary Win64 callees, stable disjoint storage and selected ordinary CFG. Callee rule equivalence, center-coordinate meaning, IFix and runtime execution remain separate.')
