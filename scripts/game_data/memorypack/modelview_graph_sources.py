"""Exact selected current ModelView inline record transfers; construction stays conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

_REG={n:i for i,n in enumerate(('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15'))}


def mov(dst,src,slot=None):
    d,s=_REG[dst],_REG[src];rex=0x48+(4 if d>=8 else 0)+(1 if s>=8 else 0)
    if slot is None:return bytes((rex,0x8b,0xc0+(d%8)*8+s%8)).hex()
    if s%8==4 or type(slot)is not int or not 0<=slot<2**31:raise ValueError('modelViewGraph.load-slot')
    if slot==0 and s%8!=5:return bytes((rex,0x8b,(d%8)*8+s%8)).hex()
    return (bytes((rex,0x8b,(0x40 if slot<128 else 0x80)+(d%8)*8+s%8))+slot.to_bytes(1 if slot<128 else 4,'little',signed=True)).hex()


def store(dst,slot,kind):
    r=_REG[dst]
    if r%8==4 or type(slot)is not int or not 0<=slot<2**31 or kind not in('bool','dword','single','reference'):raise ValueError('modelViewGraph.store-scope')
    head=(bytes((0x48+(r>=8),0x89))if kind=='reference'else bytes((0x41,))if r>=8 else b'')
    if kind!='reference':head+=(b'\xf3\x0f\x11'if kind=='single'else b'\x88'if kind=='bool'else b'\x89')
    return(head+bytes(((0x40 if slot<128 else 0x80)+r%8,))+slot.to_bytes(1 if slot<128 else 4,'little',signed=True)).hex()


def guarded(g,register):
    r=_REG[register];g.take(bytes((0x48+(4 if r>=8 else 0)+(1 if r>=8 else 0),0x85,0xc0+(r%8)*9)).hex())
    return g.relative('74',1)if g.bytes.get(g.at)==0x74 else g.relative('0f84')


def inline_result(regions,entry,*,kind,receiver,field,reader,holder,prefetch=(),collector=None,embedded=False,barrier=None,early_restore=False):
    if kind not in('bool','dword','single','reference')or receiver not in('rsi','rbx','rdi'):raise ValueError('modelViewGraph.result-scope')
    g=BytesPath(regions,entry);guards=[guarded(g,receiver)];destination=receiver if embedded else'rax'if kind=='single'else'r8'if kind=='reference'else'rcx'
    if not embedded:g.take(mov(destination,receiver,16));guards.append(guarded(g,destination))
    flag=None
    if kind=='reference'and not embedded:
        flag=g.relative('833d')+1;g.take('00')
        if flag!=collector:raise ValueError('modelViewGraph.collector-identity')
    carried=[]
    for role in prefetch:
        if kind!='single':raise ValueError('modelViewGraph.prefetch-before-live-integer')
        if role=='reader':g.take(mov('rcx',reader));carried.append(role)
        elif role=='holder':g.take(mov(receiver,holder,0));carried.append(role)
        else:raise ValueError('modelViewGraph.prefetch-role')
    if early_restore:
        if kind!='dword'or receiver!='rbx'or embedded:raise ValueError('modelViewGraph.early-restore-scope')
        g.take('488b742438')
    if kind=='reference'and embedded:
        r=_REG[receiver];g.take((bytes((0x48+(1 if r>=8 else 0),0x8d,0x48+r%8))+bytes((field,))).hex())
        if g.bytes.get(g.at)==0x48 and g.bytes.get(g.at+1)==0x89 and g.bytes.get(g.at+2)==1:g.take('488901')
        else:g.take(store(receiver,field,kind))
        g.call(barrier)
    else:
        g.take(store(destination,field,kind))
        if kind=='reference':g.branch('0f84'if g.bytes.get(g.at)==0x0f else'74',True,4 if g.bytes.get(g.at)==0x0f else 1)
    return dict(selectedBytes=g.seen,end=g.at,nullTargets=guards,field=field,kind=kind,embeddedValue=embedded,prefetched=carried,collectorCell=flag,unchangedSourceStored=True,normalPath=True,condition='Actual typed same wrapper/original and field, valid disjoint source/Reader/storage, ordinary current child and helper ABI; disabled collector for reference stores. Constructor/provider/runtime effects and child grammar remain separately conditional.')


def condition_value16(regions,entry,offsets,advance,field):
    g=BytesPath(regions,entry);b=lambda k:bytes((offsets[k],)).hex();g.take('837b'+b('bufferLength')+'10','488b37');g.branch('0f8c',False)
    g.take('488b43'+b('currentPtr'),'ba10000000','488bcb','0f1000','0f11442420');g.call(advance);guards=[guarded(g,'rsi')];g.take('488b4610');guards.append(guarded(g,'rax'));g.take('0f10442420','488bcb','0f1140'+bytes((field,)).hex())
    return dict(selectedBytes=g.seen,end=g.at,nullTargets=guards,wireBytes=16,field=field,prefetched=['reader'],completeValueCopy=True,condition='Actual unmanaged16 ConditionValue and current owned field, sufficient signed buffer and disjoint storage; same Reader passes EDX16 to independently proved Advance, ordinary ABI preserves RSI and copied stack. No nested wrapper or value/provider/default semantics inferred.')


def envelope_result32(regions,entry,field,barrier):
    g=BytesPath(regions,entry);guards=[guarded(g,'rbx')];g.take('488b4b10');guards.append(guarded(g,'rcx'));g.take('0f10442420','0f104c2430','0f1141'+bytes((field,)).hex(),'0f1149'+bytes((field+16,)).hex(),'4883c1'+bytes((field,)).hex());g.call(barrier)
    return dict(selectedBytes=g.seen,end=g.at,nullTargets=guards,managedValueBytes=32,completeValueCopy=True,condition='Current typed hidden32 Envelope ReadValue writes same disjoint stack+32/+48; exact original field receives all32bytes, same wrapper/Reader aliases and disabled ordinary barrier. Wire child and matched managed32 adapter/context composition separate.')
