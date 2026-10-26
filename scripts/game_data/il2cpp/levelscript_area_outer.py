"""Selected initialized, unpatched outer rule with an abstract shape predicate.

The caller separately proves the inlined predicate and its scratch footprint.
This proves caller lanes and branch composition, without interpreting geometry.
"""
import re
from scripts.game_data.il2cpp.initializer_control import control_transfer


def evaluate(rows,entry,scenario,symbols,*,inlined=None):
    by={int(r['va'],16):r for r in rows};at=entry;sp=0;g={n:('incoming',n) for n in ('rax','rbx','rcx','rdx','rsi','rdi','rbp','r8','r9','r10','r11','r12','r13','r14','r15')};original=dict(g)
    x={f'xmm{n}':('incoming-vector',n) for n in range(16)};original_x=dict(x);memory={('stack',40):scenario['previous'],('stack',48):('method','hidden')};flags=None;trace=[];calls=[]
    enter=None if scenario['enterNull'] else ('ref','enter',0);exit=None if scenario['exitNull'] else ('ref','exit',0);center=('ref','center',0)
    g.update(rcx=scenario['sensitive'],rdx=enter,r8=exit,r9=center)
    alias={'al':'rax','bl':'rbx','cl':'rcx','dl':'rdx','bpl':'rbp','eax':'rax','ebx':'rbx','ecx':'rcx','edx':'rdx','esi':'rsi','edi':'rdi','ebp':'rbp','r8d':'r8','r13d':'r13'}
    def fail(what):raise ValueError('areaOuter.'+what+':'+hex(at)+':'+by[at]['text'])
    def reg(s):return alias.get(s,s)
    def number(s):
        try:return int(s,0)
        except ValueError:return None
    def address(s):
        s=re.sub(r'^(?:byte|dword|qword) ','',s)
        rip=re.fullmatch(r'\[rip[^\]]*=> (0x[0-9a-f]+)\]',s)
        if rip:return 'global',int(rip[1],16)
        match=re.fullmatch(r'\[(\w+)(?:([+-])(0x[0-9a-f]+))?\]',s)
        if not match:fail('address')
        name,sign,disp=match.groups();offset=(-1 if sign=='-' else 1)*int(disp or '0',16);base=('stack',sp) if name=='rsp' else g.get(reg(name))
        if isinstance(base,tuple) and base[0]=='stack':return 'stack',base[1]+offset
        if isinstance(base,tuple) and base[0]=='ref':return base[1],base[2]+offset
        fail('unbound-address')
    def load(s):
        place=address(s)
        if place in memory:return memory[place]
        if place[0]=='global':
            value=symbols['globals'].get(place[1],('missing',))
            if value==('missing',):fail('unbound-global')
            return value
        if place==('class',symbols['initializedOffset']):return 1
        if place==('patchRoot',symbols['patchTableOffset']):return ('ref','patchTable',0)
        if place==('patchTable',symbols['patchFunctionOffset']):return 0
        if place==('center',0):return ('center-bytes',0,8)
        if place==('center',8):return ('center-bytes',8,4)
        fail('uninitialized-memory')
    def value(s):
        if '[' in s:return load(s)
        if s.startswith('xmm'):return x[s]
        if s=='rsp':return ('stack',sp)
        return number(s) if number(s) is not None else g[reg(s)]
    def store(s,v):
        nonlocal sp
        if '[' in s:memory[address(s)]=v
        elif s.startswith('xmm'):x[s]=v
        elif s=='rsp':
            if not isinstance(v,tuple) or v[0]!='stack':fail('stack-value')
            sp=v[1]
        else:g[reg(s)]=v
    def clobber():
        for name in ('rcx','rdx','r8','r9','r10','r11'):g[name]=('clobber',name)
        for n in range(6):x[f'xmm{n}']=('clobber-vector',n)
    for _ in range(len(rows)*3):
        if at not in by:raise ValueError('areaOuter.missing-instruction:'+hex(at))
        row=by[at];trace.append(at);text=row['text'];op=text.split()[0];args=text[len(op):].strip().split(', ') if ' ' in text else [];flow=control_transfer(row);nxt=at+len(bytes.fromhex(row['bytes']))
        if inlined and at==inlined['entry']:
            if g['rdi']!=enter or enter is None or g['r15']!=center or x['xmm8']!=('center-bytes',0,8) or g['r13']!=('center-bytes',8,4):fail('inlined-inputs')
            at=inlined['true'] if scenario['enterPredicate'] else inlined['false'];calls.append(('inlined-enter',scenario['enterPredicate']));clobber()
            for name in ('rbx','rsi','r12','r13','r14'):g[name]=('core-clobber',name)
            for n in (6,7,8):x[f'xmm{n}']=('core-clobber-vector',n)
            flags=None;continue
        if flow['kind']=='return':
            if sp or any(g[n]!=original[n] for n in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')) or any(x[f'xmm{n}']!=original_x[f'xmm{n}'] for n in range(6,16)):fail('abi-restoration')
            if g['rax'] not in (0,1):fail('boolean-return')
            return dict(result=bool(g['rax']),trace=trace,calls=calls)
        if flow['kind']=='conditional':
            condition=flow.get('conditionCode')
            if flags is None or condition not in (4,5):fail('unproved-branch')
            if flags==(condition==4):nxt=flow['target']
        elif flow['kind']=='jump':nxt=flow['target']
        elif flow['kind']=='call':
            target=flow['target']
            if target==symbols['warmClass']:
                if g['rcx']!=('ref','class',0):fail('class-input')
            elif target==symbols['empty']:
                if g['rcx']!=exit or g['rdx']!=('ref','methodInfo',0):fail('empty-inputs')
                g['rax']=int(scenario['exitEmpty']);clobber();calls.append(('empty-exit',scenario['exitEmpty']))
            elif target==symbols['predicate']:
                source=g['rcx'];pointer=g['rdx']
                if source not in (enter,exit) or source is None or not isinstance(pointer,tuple) or pointer[0]!='stack':fail('predicate-pointers')
                if memory.get(('stack',pointer[1]))!=('center-bytes',0,8) or memory.get(('stack',pointer[1]+8))!=('center-bytes',8,4):fail('predicate-center-copy')
                role='enter' if source==enter else 'exit';g['rax']=int(scenario[role+'Predicate']);clobber();calls.append((role+'-predicate',bool(g['rax'])))
            else:fail('unknown-call')
            flags=None
        elif flow['kind'] not in ('next',):fail('unexpected-flow')
        elif op=='push':
            v=value(args[0]);sp-=8;memory['stack',sp]=v
        elif op=='pop':store(args[0],memory['stack',sp]);sp+=8
        elif op in ('sub','add') and args[0]=='rsp':sp+=(-1 if op=='sub' else 1)*int(args[1],16);flags=None
        elif op=='lea':store(args[0],('stack',address(args[1])[1]) if address(args[1])[0]=='stack' else ('ref',*address(args[1])))
        elif op in ('mov','movzx','movsd','movaps'):store(args[0],value(args[1]))
        elif op in ('test','cmp'):
            left,right=value(args[0]),value(args[1]);flags=(left in (None,0)) if op=='test' and args[0]==args[1] else left==right
        elif op=='xor' and args[0]==args[1]:store(args[0],0);flags=True
        elif op=='nop':pass
        else:fail('unsupported-operation')
        at=nxt
    raise ValueError('areaOuter.step-budget')
