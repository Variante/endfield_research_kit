"""Paired ordinary-code value check; foreign-call obligations stay explicit."""
import copy
import re
from collections import deque
from scripts.game_data.il2cpp.initializer_control import control_transfer


def check_geometry_relation(programs, pairs, *, math_effects, foreign_calls, init_calls, incoming_gprs, incoming_vector_lanes):
    mapping=dict(pairs); reverse={b:a for a,b in pairs}; byte_map={}; inverse={}; obligations={}
    if len(mapping)!=len(pairs) or len(reverse)!=len(pairs):raise ValueError('geometry.nonbijective-instructions')
    stack_pattern=r'\[(rsp|rbp)(?:([+-])(0x[0-9a-f]+))?\]'
    def fail(row,reason):raise ValueError('geometry.'+reason+':'+row['va']+':'+row['text'])
    def stack(program,row,operand):
        match=re.fullmatch(stack_pattern,operand)
        if not match:return None
        sp,bp,_=program['control']['frames'][int(row['va'],16)];at=sp if match[1]=='rsp' else bp
        if at is None:fail(row,'unbound-frame')
        return at+(-1 if match[2]=='-' else 1)*int(match[3] or '0',16)
    def width(row):
        op=row['text'].split()[0]
        if row.get('memoryOperation'):return row['memoryOperation']['memoryBytes']
        if op in ('lea','movups','movaps','movdqa','andps'):return 16
        if op=='movsd':return 8
        if op in ('movss','movd'):return 4
        if 'byte [' in row['text']:return 1
        if 'dword [' in row['text']:return 4
        fail(row,'memory-width')
    for a,b in pairs:
        rows=[p['by_at'][at] for p,at in zip(programs,(a,b))]
        normalized=[]
        for row in rows:
            text=re.sub(stack_pattern,'[scratch]',row['text']);flow=control_transfer(row)
            if flow['kind'] in ('jump','conditional'):text=str((flow['kind'],flow.get('conditionCode')))
            text=re.sub(r'\[rip[^\]]*=> (0x[0-9a-f]+)\]',r'[absolute \1]',text);normalized.append(text)
        if normalized[0]!=normalized[1]:fail(rows[0],'paired-operation-differs')
        operands=[re.findall(stack_pattern,r['text']) for r in rows]
        if len(operands[0])!=len(operands[1]):fail(rows[0],'stack-operand-count')
        for ma,mb in zip(re.finditer(stack_pattern,rows[0]['text']),re.finditer(stack_pattern,rows[1]['text'])):
            offsets=[stack(p,r,m[0]) for p,r,m in zip(programs,rows,(ma,mb))];sizes=[width(r) for r in rows]
            if sizes[0]!=sizes[1]:fail(rows[0],'stack-width')
            for delta in range(sizes[0]):
                x,y=[at+delta for at in offsets]
                if x in byte_map and byte_map[x]!=y or y in inverse and inverse[y]!=x:fail(rows[0],'scratch-alias-conflict')
                byte_map[x]=y;inverse[y]=x
    def reg(name):
        if name.startswith('xmm'):return name,128
        aliases={'eax':'rax','ebx':'rbx','ecx':'rcx','edx':'rdx','esi':'rsi','edi':'rdi','ebp':'rbp','esp':'rsp','al':'rax','bl':'rbx','cl':'rcx','dl':'rdx'}
        if name in aliases:return aliases[name],8 if len(name)==2 else 32
        if re.fullmatch(r'r(?:[89]|1[0-5])[db]?',name):return name.rstrip('db'),32 if name.endswith('d') else 8 if name.endswith('b') else 64
        if name in ('rax','rbx','rcx','rdx','rsi','rdi','rsp','rbp'):return name,64
        return None
    def known(state,name):
        key,bits=reg(name);value=state['g'].get(key)
        if key.startswith('xmm'):return state['x'][key]
        return value if value and (value[0]=='stack' and bits==64 or value[0]=='bits' and value[1]>=bits) else None
    def put(state,name,value):
        key,bits=reg(name)
        if value and value[0]=='bits':value=('bits',64 if bits==32 else bits)
        if value and bits<32 and state['g'].get(key) and state['g'][key][0]=='bits':value=('bits',max(bits,state['g'][key][1]))
        state['g'][key]=value
    def memory(state,rows,operands,size):
        offsets=[stack(p,r,o) for p,r,o in zip(programs,rows,operands)]
        if offsets[0] is not None:
            if offsets[1] is None:fail(rows[0],'stack-space-differs')
            x,y=offsets
        else:
            normalized=[re.sub(r'\[rip[^\]]*=> (0x[0-9a-f]+)\]',r'[absolute \1]',o) for o in operands]
            if normalized[0]!=normalized[1]:fail(rows[0],'heap-address-differs')
            names=re.findall(r'\b(?:r(?:ax|bx|cx|dx|si|di|sp|bp|[89]|1[0-5]))\b',operands[0])
            if len(names)==1:
                value=known(state,names[0])
                if value and value[0]=='stack':
                    disp=re.fullmatch(r'\['+names[0]+r'(?:\+(0x[0-9a-f]+))?\]',operands[0])
                    if not disp:fail(rows[0],'relocated-address-arithmetic')
                    delta=int(disp[1] or '0',16);x,y=value[1]+delta,value[2]+delta
                else:
                    if not value or value[0]!='bits':fail(rows[0],'unknown-heap-base')
                    return None
            else:
                if any(not known(state,n) or known(state,n)[0]!='bits' for n in names):fail(rows[0],'unknown-index-address')
                return None
        if any(byte_map.get(x+i)!=y+i for i in range(size)):fail(rows[0],'noncontiguous-scratch-view')
        return x,y
    def load(state,rows,operands,size):
        place=memory(state,rows,operands,size)
        return [True]*((size+3)//4) if place is None else [all(place[0]+i+j in state['m'] for j in range(min(4,size-i))) for i in range(0,size,4)]
    def store(state,rows,operands,lanes,size):
        place=memory(state,rows,operands,size)
        if place is None:
            if not all(lanes):fail(rows[0],'unequal-global-store')
            return
        for i in range(size):
            if lanes[min(i//4,len(lanes)-1)]:state['m'].add(place[0]+i)
            else:state['m'].discard(place[0]+i)
    def call(state,rows,target):
        if target in math_effects:
            effect=math_effects[target]
            for name,bytes_read in effect['reads'].items():
                value=known(state,name)
                if not value or value[0]!='stack':fail(rows[0],'math-argument-pointer')
                if not all(value[1]+i in state['m'] and byte_map.get(value[1]+i)==value[2]+i for i in bytes_read):fail(rows[0],'math-argument-value')
            if any(not state['x'][name][0] for name in effect['scalars']):fail(rows[0],'math-scalar-value')
            for name,bytes_written in effect['writes'].items():
                value=known(state,name)
                if not value or value[0]!='stack' or any(byte_map.get(value[1]+i)!=value[2]+i for i in bytes_written):fail(rows[0],'math-output-pointer')
                state['m'].update(value[1]+i for i in bytes_written)
            state['g']['rax']=known(state,'rcx') if effect['returnKind']=='out-rcx' else state['g'].get('rax')
            state['g']['r11']=None
            for i in range(6):state['x']['xmm'+str(i)]=[False]*4
            if effect['returnKind']=='float32':state['x']['xmm0'][0]=True
            if effect['changesFlags']:state['f']=False
            return
        if target is None:
            effect=foreign_calls.get(int(rows[0]['va'],16))
            if not effect or not known(state,'rax') or known(state,'rax')[0]!='bits':fail(rows[0],'unknown-indirect-call')
            source,destination=known(state,'rcx'),known(state,'rdx')
            if not source or source[0]!='stack' or not destination or destination[0]!='stack':fail(rows[0],'foreign-buffer-arguments')
            if any(source[1]+i not in state['m'] or byte_map.get(source[1]+i)!=source[2]+i for i in range(effect['readBytes'])):fail(rows[0],'foreign-input-value')
            if any(byte_map.get(destination[1]+i)!=destination[2]+i for i in range(effect['writeBytes'])):fail(rows[0],'foreign-output-alias')
            state['m'].update(destination[1]+i for i in range(effect['writeBytes']));obligations[rows[0]['va']]=effect
        elif target in init_calls:
            if not known(state,'rcx') or known(state,'rcx')[0]!='bits':fail(rows[0],'initialization-argument')
        else:fail(rows[0],'unknown-direct-call')
        for name in ('rax','rcx','rdx','r8','r9','r10','r11'):state['g'][name]=None
        if target in init_calls and init_calls[target]=='returns-bits':state['g']['rax']=('bits',64)
        for i in range(6):state['x']['xmm'+str(i)]=[False]*4
        state['f']=False
    if any(reg(name) is None or reg(name)[0].startswith('xmm') or type(bits) is not int or not 1<=bits<=64 for name,bits in incoming_gprs.items()):raise ValueError('geometry.incoming-register-profile')
    if any(not re.fullmatch(r'xmm(?:[0-9]|1[0-5])',name) or len(lanes)!=4 or any(type(value) is not bool for value in lanes) for name,lanes in incoming_vector_lanes.items()):raise ValueError('geometry.incoming-vector-profile')
    initial=dict(g={name:('bits',bits) for name,bits in incoming_gprs.items()},x={'xmm'+str(i):list(incoming_vector_lanes.get('xmm'+str(i),[False]*4)) for i in range(16)},m=set(),f=False)
    states={programs[0]['entry']:initial};pending=deque(states);visits=0
    def intersect(a,b):
        return dict(g={k:v if v==b['g'].get(k) else None for k,v in a['g'].items()},x={k:[x and y for x,y in zip(v,b['x'][k])] for k,v in a['x'].items()},m=a['m']&b['m'],f=a['f'] and b['f'])
    while pending:
        at=pending.popleft();state=copy.deepcopy(states[at]);rows=[programs[0]['by_at'][at],programs[1]['by_at'][mapping[at]]];row=rows[0];flow=control_transfer(row);visits+=1
        text=row['text'];op=text.split()[0];args=text[len(op):].strip().split(', ') if ' ' in text else []
        both=[r['text'].split(' ',1)[1].split(', ') if ' ' in r['text'] else [] for r in rows]
        if flow['kind']=='conditional':
            if not state['f']:fail(row,'unequal-branch-flags')
        elif flow['kind']=='call' or flow['kind']=='registerCall' and flow.get('register')=='rax':call(state,rows,flow.get('target'))
        elif flow['kind']=='jump':pass
        elif op=='lea':
            offsets=[stack(p,r,aa[1]) for p,r,aa in zip(programs,rows,both)]
            if offsets[0] is not None:put(state,args[0],('stack',*offsets))
            elif 'rip' in args[1]:put(state,args[0],('bits',64))
            else:fail(row,'unhandled-address')
        elif op in ('mov','movsxd'):
            if re.sub(r'^(?:byte|word|dword|qword) ','',args[0]).startswith('['):
                size=width(row);value=known(state,args[1]) if reg(args[1]) else ('bits',64) if args[1].startswith('0x') else None
                store(state,rows,[re.sub(r'^(?:byte|word|dword|qword) ','',x[0]) for x in both],[bool(value and value[0]=='bits')],size)
            elif args[1].startswith('['):
                values=load(state,rows,[x[1] for x in both],width(row));put(state,args[0],('bits',reg(args[0])[1]) if all(values) else None)
            elif reg(args[1]):put(state,args[0],known(state,args[1]))
            elif args[1].startswith('0x'):put(state,args[0],('bits',reg(args[0])[1]))
            else:fail(row,'unhandled-move')
        elif op in ('movsd','movss','movups','movaps','movdqa','movd'):
            size={'movsd':8,'movss':4,'movups':16,'movaps':16,'movdqa':16,'movd':4}[op];dest,source=args
            if source.startswith('['):values=load(state,rows,[x[1] for x in both],size)
            elif source.startswith('xmm'):values=state['x'][source][:size//4]
            else:values=[bool(known(state,source) and known(state,source)[0]=='bits')]
            if dest.startswith('['):store(state,rows,[x[0] for x in both],values,size)
            elif dest.startswith('xmm'):state['x'][dest]=values+([True]*(4-len(values)) if source.startswith('[') or op=='movd' else state['x'][dest][len(values):])
            else:put(state,dest,('bits',32) if all(values) else None)
        elif op=='psrldq':
            count=int(args[1],16)
            if count%4:fail(row,'non-lane-shift')
            state['x'][args[0]]=(state['x'][args[0]][count//4:]+[True]*4)[:4]
        elif op in ('xorps','mulss','andps','comiss'):
            dest,source=args;size=16 if op in ('xorps','andps') else 4
            values=load(state,rows,[x[1] for x in both],size) if source.startswith('[') else state['x'][source]
            if op=='xorps' and dest==source:state['x'][dest]=[True]*4
            elif op=='comiss':state['f']=state['x'][dest][0] and values[0]
            else:
                count=4 if op in ('xorps','andps') else 1
                for i in range(count):state['x'][dest][i]=state['x'][dest][i] and values[i]
        elif op in ('cmp','test','sub','dec','imul','xor'):
            clean=[re.sub(r'^(?:dword|byte) ','',s) for s in args];values=[]
            for i,arg in enumerate(clean):
                if arg.startswith('['):values.append(all(load(state,rows,[re.sub(r'^(?:dword|byte) ','',x[i]) for x in both],width(row))))
                elif reg(arg):values.append(bool(known(state,arg) and known(state,arg)[0]=='bits'))
                elif arg.startswith('0x'):values.append(True)
                else:fail(row,'unhandled-integer-source')
            equal=True if op=='xor' and clean[0]==clean[1] else all(values[1:] if op=='imul' else values)
            state['f']=equal
            if op not in ('cmp','test'):put(state,clean[0],('bits',reg(clean[0])[1]) if equal else None)
        else:fail(row,'unhandled-operation')
        for successor in programs[0]['control']['edges'][at]:
            if successor not in mapping:continue
            # The named center reloads are epsilon only under stable center bytes.
            next_state=copy.deepcopy(state)
            if successor in states:
                merged=intersect(states[successor],next_state)
                if merged==states[successor]:continue
                states[successor]=merged
            else:states[successor]=next_state
            pending.append(successor)
        if visits>len(mapping)*50:fail(row,'fixed-point-budget')
    if set(states)!=set(mapping):raise ValueError('geometry.unvisited-normal-pairs')
    return dict(status='conditional-value-relation-with-open-foreign-effects',pairedInstructions=len(mapping),fixedPointVisits=visits,scratchBytes=len(byte_map),foreignCallObligations=obligations,
        condition='Equal typed list and center bytes; stable disjoint inputs; normal compatible initialization; selected foreign buffer effects must be proved separately.',evidenceBoundary='conditional')
