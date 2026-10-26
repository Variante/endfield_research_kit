"""Conservative reference origins across a complete consumer CFG.

Only full-width register copies, selected incoming stack slots, and declared
call returns retain origins. Scalars and partial overwrites lose provenance.
Stable incoming slots and disjoint storage remain explicit conditions; this
does not prove opaque callee effects or any feasible runtime path.
"""
from collections import deque
from .consumer_control import check_consumer_control
from .initializer_control import (_ALIASES, _PARENTS, _VOLATILE, _WRITERS,
                                  _READ_ONLY, _register_copy, control_transfer, memory_effect)
from .memory_moves import decode_memory_move
from .initializer_instructions import decode_initializer_byte_store,decode_initializer_move
from .integer_effects import decode_immediate_memory_store
from .scalar_double_memory import decode_scalar_double_memory_move

LABEL='consumerReferenceOrigins'
UNKNOWN=frozenset({'unknown'})

def check_reference_origins(rows, *, entry, owned_ranges, incoming_registers,
                            incoming_stack_slots, selected_call_returns):
    control=check_consumer_control(rows,entry=entry,owned_ranges=owned_ranges)
    by_at={int(r['va'],16):r for r in rows};frames=control['frames']
    call_sites={c['site'] for c in control['calls']}
    if not set(selected_call_returns)<=call_sites:raise ValueError(LABEL+'.non-call-return-source')
    if any(register not in _PARENTS or register=='rsp' for register in incoming_registers):
        raise ValueError(LABEL+'.incoming-register')
    if any(type(offset)!=int or offset<40 or offset%8 for offset in incoming_stack_slots):
        raise ValueError(LABEL+'.incoming-stack-slot')
    writes=[]
    for at,row in by_at.items():
        raw=bytes.fromhex(row['bytes']);annotated=row
        for decoder in (decode_initializer_byte_store,decode_immediate_memory_store,
                        decode_initializer_move,decode_scalar_double_memory_move):
            decoded=decoder(raw,0,at)
            if decoded and decoded[1]==len(raw):
                annotated={**row,**{k:v for k,v in decoded[0].items() if k not in ('va','offset','bytes','text','write')}}
                break
        effect=memory_effect(annotated)
        if effect:
            fact=effect['facts'];address=fact.get('address',fact.get('destinationAddress',{}))
            width=fact.get('memoryBytes',fact.get('memoryWriteBytes'))
            if address.get('base')=='rsp':
                if address.get('index') is not None or address.get('ripRelative') or type(width)!=int:
                    raise ValueError(LABEL+'.unclassified-stack-write')
                begin=frames[at][0]+address['displacement']
                if any(begin<slot+8 and slot<begin+width for slot in incoming_stack_slots):
                    raise ValueError(LABEL+'.incoming-stack-slot-overwritten')
                writes.append({'site':at,'entrySpOffset':begin,'bytes':width})
    initial=[UNKNOWN]*len(_PARENTS)
    for register,origin in incoming_registers.items():initial[_PARENTS.index(register)]=frozenset({origin})
    states={entry:tuple(initial)};pending=deque((entry,))
    while pending:
        at=pending.popleft();row=by_at[at];values=list(states[at])
        raw=bytes.fromhex(row['bytes']);head,_,rest=row['text'].partition(' ')
        parent=_ALIASES.get(rest.split(',')[0]);kind=control_transfer(row)['kind']
        if kind in ('call','indirectCall','registerCall'):
            for register in _VOLATILE:values[_PARENTS.index(register)]=UNKNOWN
            if at in selected_call_returns:values[_PARENTS.index('rax')]=frozenset({selected_call_returns[at]})
        elif kind in ('conditional','jump','return','trap') or head in _READ_ONLY:pass
        else:
            decoded=decode_memory_move(raw,0,at)
            fact=decoded[0]['memoryOperation'] if decoded and decoded[1]==len(raw) else None
            copy=_register_copy(raw) if head=='mov' else None
            if copy:
                destination,source=copy;values[_PARENTS.index(destination)]=values[_PARENTS.index(source)]
            elif fact is not None:
                if fact['direction']=='load' and fact['backingRegister'] in _PARENTS:
                    origin=UNKNOWN;address=fact['address']
                    if (fact['registerBits'],fact['memoryBytes'],address.get('base'),address.get('index'),address.get('ripRelative'))==(64,8,'rsp',None,False):
                        slot=frames[at][0]+address['displacement']
                        if slot in incoming_stack_slots:origin=frozenset({incoming_stack_slots[slot]})
                    values[_PARENTS.index(fact['backingRegister'])]=origin
            elif head in _WRITERS or head in ('movd','movq') or head.startswith('cmov'):
                if head=='imul' and ',' not in rest:raise ValueError(LABEL+'.implicit-register-writes')
                if head=='cdqe':parent='rax'
                if parent is not None:values[_PARENTS.index(parent)]=UNKNOWN
            elif head in ('movups','movaps','movsd','movss','movdqa','movdqu','xorps'):pass
            else:raise ValueError(LABEL+'.unreviewed-register-effect:'+row['text'])
        output=tuple(values)
        for target in control['edges'][at]:
            previous=states.get(target)
            joined=output if previous is None else tuple(a|b for a,b in zip(previous,output))
            if joined!=previous:states[target]=joined;pending.append(target)
    return {'registerOrigins':{at:{reg:sorted(state[i]) for i,reg in enumerate(_PARENTS)}
            for at,state in states.items()},'directStackWritesChecked':writes,
            'instructionsChecked':control['instructionsChecked'],'callsChecked':len(control['calls']),
            'evidenceBoundary':'conditional',
            'condition':'ordinary returning Win64 callees; selected incoming stack slots remain stable under indirect stores and opaque callee effects; storage is disjoint',
            'runtimeExecutionKnown':False,'branchFeasibilityKnown':False}
