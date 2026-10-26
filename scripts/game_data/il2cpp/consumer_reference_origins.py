"""Conservative reference origins across a complete consumer CFG.

Only full-width register copies, selected incoming stack slots, and declared
call returns retain origins. Scalars and partial overwrites lose provenance.
Stable incoming slots and disjoint storage remain explicit conditions; this
does not prove opaque callee effects or any feasible runtime path.
"""
from collections import deque
from scripts.game_data.il2cpp.method_carrier_instructions import decode_carrier_vector_byte_shift
from scripts.game_data.il2cpp.integer_addressing import decode_lea_address, _prefix, _address
from scripts.game_data.il2cpp.metadata_initialization_instructions import decode_unsigned_register_multiply
from scripts.game_data.il2cpp.integer_effects import decode_register_unary
from scripts.game_data.il2cpp.consumer_control import check_consumer_control, consumer_transfer
from scripts.game_data.il2cpp.initializer_control import (_ALIASES, _PARENTS, _VOLATILE, _WRITERS,
                                  _READ_ONLY, _register_copy, control_transfer, memory_effect)
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.initializer_instructions import decode_initializer_byte_store,decode_initializer_move
from scripts.game_data.il2cpp.integer_effects import decode_immediate_memory_store, decode_locked_memory_exchange
from scripts.game_data.il2cpp.generic_creation_instructions import decode_implicit_memory_exchange
from scripts.game_data.il2cpp.scalar_double_memory import decode_scalar_double_memory_move
from scripts.game_data.il2cpp.scalar_single_memory import decode_scalar_single_memory_move
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_initialization_memory_update
from scripts.game_data.il2cpp.prefetch_instruction import memory_prefetch_address

LABEL='consumerReferenceOrigins'
UNKNOWN=frozenset({'unknown'})

def _literal_register_origins(rows,selected):
    by_at={int(row['va'],16):row for row in rows};result={}
    for at,pair in (selected or {}).items():
        if type(at) is not int or at not in by_at or not isinstance(pair,(tuple,list)) or len(pair)!=2:
            raise ValueError(LABEL+'.literal-register-selection')
        register,value=pair
        if register not in _PARENTS or type(value) is not int or not 0<=value<1<<64:
            raise ValueError(LABEL+'.literal-register-value')
        raw=bytes.fromhex(by_at[at]['bytes']);rex=raw[0] if raw and 0x40<=raw[0]<=0x4f else 0
        code=raw[1:] if rex else raw;matched=False
        if len(code)==2 and code[0] in (0x31,0x33) and code[1]>>6==3:
            left=((code[1]>>3)&7)+(8 if rex&4 else 0);right=(code[1]&7)+(8 if rex&1 else 0)
            matched=left==right and _PARENTS[left]==register and value==0
        lea=decode_lea_address(raw,0,at)
        if lea and lea[1]==len(raw):
            fact=lea[0]['addressOperation']
            matched=(fact.get('destination'),fact.get('destinationBits'),fact.get('base'),fact.get('index'),fact.get('ripRelative'),fact.get('absoluteAddress'))==(register,64,None,None,True,value)
        if not matched:raise ValueError(LABEL+'.literal-register-bytes')
        result[at]=(register,'constant:'+hex(value))
    return result


def _condition_register_write(raw,text):
    from scripts.game_data.il2cpp.integer_widths import _byte
    from scripts.game_data.il2cpp.integer_addressing import _reg
    rex=raw[0] if raw and raw[0] in (0x40,0x41) else 0
    code=raw[1:] if rex else raw
    if len(code)!=3 or code[0]!=0x0f or not 0x90<=code[1]<=0x9f or code[2]&0xf8!=0xc0:return None
    number=(code[2]&7)+(8 if rex&1 else 0);register=_byte(number,rex)
    condition=('o','no','b','ae','e','ne','be','a','s','ns','p','np','l','ge','le','g')[code[1]-0x90]
    if text!='set'+condition+' '+register:raise ValueError(LABEL+'.condition-byte-text')
    return _reg(number-4 if not rex and 4<=number<8 else number)


def check_reference_origins(rows, *, entry, owned_ranges, incoming_registers,
                            incoming_stack_slots, selected_call_returns, computed_jump_targets=None, selected_literal_registers=None,tail_exits=None):
    control=check_consumer_control(rows,entry=entry,owned_ranges=owned_ranges,computed_jump_targets=computed_jump_targets,tail_exits=tail_exits)
    by_at={int(r['va'],16):r for r in rows};frames=control['frames']
    literals=_literal_register_origins(rows,selected_literal_registers)
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
                        decode_initializer_move,decode_scalar_double_memory_move,decode_scalar_single_memory_move,decode_implicit_memory_exchange,decode_locked_memory_exchange):
            decoded=decoder(raw,0,at)
            if decoded and decoded[1]==len(raw):
                annotated={**row,**{k:v for k,v in decoded[0].items() if k not in ('va','offset','bytes','text','write')}}
                break
        implicit=annotated.get('implicitMemoryExchangeOperation')
        update=decode_initialization_memory_update(raw,0,at)
        effect=({'kind':'initializationMemoryUpdateOperation','facts':update[0]['initializationMemoryUpdateOperation']}
            if update and update[1]==len(raw) else None)
        effect=None if memory_prefetch_address(raw)is not None else effect or ({'kind':'implicitMemoryExchangeOperation','facts':dict(implicit,memoryBytes=implicit['memoryWriteBytes'])} if implicit else memory_effect(annotated))
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
        parent=_ALIASES.get(rest.split(',')[0]);kind=consumer_transfer(row,computed_jump_targets=computed_jump_targets,tail_exits=tail_exits)['kind']
        exchange=None
        for decoder in (decode_implicit_memory_exchange,decode_locked_memory_exchange):
            decoded=decoder(raw,0,at)
            if decoded and decoded[1]==len(raw):
                exchange=decoded[0];break
        if kind in ('call','indirectCall','registerCall'):
            for register in _VOLATILE:values[_PARENTS.index(register)]=UNKNOWN
            if at in selected_call_returns:values[_PARENTS.index('rax')]=frozenset({selected_call_returns[at]})
        elif exchange:
            implicit=exchange.get('implicitMemoryExchangeOperation',{})
            locked=exchange.get('lockedMemoryExchangeOperation',{})
            affected=implicit.get('register') or (locked.get('sourceRegister') if locked.get('operation')=='xadd' else locked.get('accumulatorRegister'))
            if affected is None:raise ValueError(LABEL+'.exchange-register-effect')
            values[_PARENTS.index(_ALIASES[affected])]=UNKNOWN
        elif memory_prefetch_address(raw)is not None:pass
        elif head.startswith('set'):
            destination=_condition_register_write(raw,row['text'])
            if destination is None:raise ValueError(LABEL+'.condition-register-bytes')
            values[_PARENTS.index(destination)]=UNKNOWN
        elif head=='mul' or head=='imul' and ',' not in rest:
            decoded=(decode_unsigned_register_multiply if head=='mul' else decode_register_unary)(raw,0,at)
            key='implicitUnsignedMultiplyOperation' if head=='mul' else 'implicitSignedMultiplyOperation'
            if decoded is None or decoded[1]!=len(raw) or key not in decoded[0]:raise ValueError(LABEL+'.implicit-register-product')
            fact=decoded[0][key]
            for role in ('lowResultRegister','highResultRegister'):values[_PARENTS.index(_ALIASES[fact[role]])]=UNKNOWN
        elif head=='bts':
            pos,rex=_prefix(raw,0);code=raw[pos:]
            if len(code)!=3 or code[:2]!=b'\x0f\xab' or code[2]>>6!=3:raise ValueError(LABEL+'.register-bit-set')
            destination=_PARENTS[(code[2]&7)+(8 if rex&1 else 0)]
            if parent!=destination:raise ValueError(LABEL+'.register-bit-set-destination')
            values[_PARENTS.index(destination)]=UNKNOWN
        elif head=='psrldq':
            decoded=decode_carrier_vector_byte_shift(raw,0,at)
            if decoded is None or decoded[1]!=len(raw):raise ValueError(LABEL+'.vector-byte-shift')
        elif kind in ('conditional','jump','return','trap','computedJump','tailExit') or head in _READ_ONLY:pass
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
        if at in literals:
            register,origin=literals[at];values[_PARENTS.index(register)]=frozenset({origin})
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
