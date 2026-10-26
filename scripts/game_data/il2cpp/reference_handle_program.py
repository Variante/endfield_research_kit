"""Two incoming references initialize a handle stored before a manager call."""
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.memory_moves import decode_memory_move


def check_handle_reference_program(rows, *, entry, owned_ranges, constructor, play, field_offset):
    control=check_consumer_control(rows,entry=entry,owned_ranges=owned_ranges)
    origins=check_reference_origins(rows,entry=entry,owned_ranges=owned_ranges,
        incoming_registers={'rcx':'manager','rdx':'first-argument','r8':'second-argument'},incoming_stack_slots={},
        selected_call_returns={call['site']:'returnBits@'+hex(call['site']) for call in control['calls']})
    ctors=[call for call in control['calls'] if call['kind']=='call' and call['target']==constructor]
    plays=[call for call in control['calls'] if call['kind']=='call' and call['target']==play]
    if len(ctors)!=1 or len(plays)!=1:raise ValueError('handleReferenceProgram.unique-constructor-and-play')
    source=origins['registerOrigins'][ctors[0]['site']]
    if (source['rdx'],source['r8'],source['r9'])!=(['first-argument'],['second-argument'],['manager']):
        raise ValueError('handleReferenceProgram.constructor-arguments')
    receiver=source['rcx']
    if len(receiver)!=1 or not receiver[0].startswith('returnBits@'):
        raise ValueError('handleReferenceProgram.constructor-receiver-call-result')
    stores=[]
    for row in rows:
        at=int(row['va'],16);raw=bytes.fromhex(row['bytes']);decoded=decode_memory_move(raw,0,at)
        if not decoded or decoded[1]!=len(raw):continue
        operation=decoded[0]['memoryOperation'];address=operation['address'];state=origins['registerOrigins'][at]
        if ((operation['direction'],operation['memoryBytes'],operation['registerBits'],address.get('index'),address.get('ripRelative'),address.get('displacement'))
                ==('store',8,64,None,False,field_offset) and state.get(address.get('base'))==['manager']
                and state.get(operation['backingRegister'])==receiver):stores.append(at)
    if len(stores)!=1:raise ValueError('handleReferenceProgram.unique-same-receiver-field-store')
    def dominates(first,later):
        seen=set();pending=[entry]
        while pending:
            at=pending.pop()
            if at==first or at in seen:continue
            seen.add(at);pending.extend(control['edges'][at]-seen)
        return later not in seen
    if not dominates(ctors[0]['site'],stores[0]) or not dominates(stores[0],plays[0]['site']):
        raise ValueError('handleReferenceProgram.constructor-store-play-dominance')
    if origins['registerOrigins'][plays[0]['site']]['rcx']!=['manager']:
        raise ValueError('handleReferenceProgram.play-manager-identity')
    return dict(constructor=ctors[0]['site'],store=stores[0],play=plays[0]['site'],receiver=receiver,
        instructions=control['instructionsChecked'],evidenceBoundary='conditional',
        condition='Complete owned ordinary flow with constructor and store dominance; correctly typed ordinary calls, stable disjoint storage and caller/callee reference ABI must be checked by the owner. Allocation internals, opaque effects and runtime playback remain separate.')
