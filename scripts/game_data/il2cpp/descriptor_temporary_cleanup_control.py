"""Nullable old-array field handoff; the guard and reload are separate reads."""
from __future__ import annotations
from .owned_partition import BranchGrammar
from .context_slot_initializer_control import validate_closed_initializer_graph


def validate_descriptor_temporary_cleanup(rows,*,entry_va,release_va):
    g=BranchGrammar(rows,label='descriptorTemporaryCleanup')
    g.take('sub rsp, 0x28','cmp qword [rcx+0x60], 0x0');g.branch('je','finish')
    g.take('mov rcx, [rcx+0x60]');g.call(release_va);g.take('nop')
    g.mark('finish');g.take('add rsp, 0x28','ret');g.finish()
    graph=validate_closed_initializer_graph(rows,entry_va=entry_va)
    return {'instructionsChecked':len(rows),'completeControlAndFramesChecked':True,'graph':graph,
        'testedAndReloadedFieldOffset':96,'fieldMemoryReadBytes':8,'releaseArgument':'fresh field QWORD passed in RCX',
        'guardAndReloadAreSeparateReads':True,'releaseArgumentGuaranteedNonzero':False,
        'fieldWritesByThisBody':0,'releaseEffectsProved':False,'runtimeExecutionKnown':False,
        'conditions':'Readable coherent record and valid frame/call storage; normally returning release callee. Without field stability the later argument can differ from the value tested by the guard.'}
