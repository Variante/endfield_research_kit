"""Prove a selected cast helper returns null or its incoming reference bits."""
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.owned_partition import BranchGrammar
from scripts.game_data.il2cpp.initializer_control import control_transfer


def check_nullable_cast_program(rows, *, entry, owned_ranges):
    control=check_consumer_control(rows,entry=entry,owned_ranges=owned_ranges)
    refs=check_reference_origins(rows,entry=entry,owned_ranges=owned_ranges,incoming_registers={'rcx':'object','rdx':'target-class'},incoming_stack_slots={},selected_call_returns={})
    g=BranchGrammar(rows,label='nullableCast')
    g.take('push rbx','sub rsp, 0x20','mov rbx, rcx','test rcx, rcx');g.branch('je','null')
    g.take('mov rcx, [rcx]');call=g.row();flow=control_transfer(call)
    if flow['kind']!='call' or refs['registerOrigins'][int(call['va'],16)]['rdx']!=['target-class']:g.fail('type-predicate','direct call with unchanged target-class bits',call)
    g.take('xor ecx, ecx','test al, al','cmove rbx, rcx','mov rax, rbx','add rsp, 0x20','pop rbx','ret')
    g.mark('null');g.take('xor eax, eax','add rsp, 0x20','pop rbx','ret');g.finish()
    return dict(nonNullReturnBitsEqualIncomingReference=True,nullInputReturnsNull=True,
        predicateCallVa=call['va'],predicateTargetVa=hex(flow['target']),originalTargetClassBitsProved=True,
        evidenceBoundary='conditional',condition='Ordinary Win64 callee preservation. The actual predicate/type-compatibility semantics, replacement code, storage validity and live selection are separate.')
