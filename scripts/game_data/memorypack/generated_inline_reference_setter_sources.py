"""Whole incoming reference store behind an actual disabled collector cell.

The parent component must independently own the nominal holder and named field,
ordinary setter ABI and current collector helper. This complete selected frame
does not assume a getter spelling or admit the enabled collector program.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

def need(key,condition,detail=None):
    if not condition:raise ValueError('generatedInlineReferenceSetter.'+key+':'+str(detail)[:700])

def program(regions,entry,*,holder,field,disabled):
    need('finite-current-holder-and-field',type(holder)is int and 16<=holder<128 and type(field)is int and 16<=field<128 and type(disabled)is int and disabled>0)
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488b59'+bytes((holder,)).hex(),'4885db')
    at=g.at;null=g.relative('74',1)
    need('owned-nonreturning-null-exit',g.bytes.get(null)==0xe8 and g.bytes.get(null+5)==0xcc)
    need('actual-disabled-collector-cell',flag(g,prefix='833d')==disabled)
    store=g.at;g.take('488953'+bytes((field,)).hex());g.branch('74',True,1)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,holderOffset=holder,fieldOffset=field,storedBytes=8,sourceRegister='incoming rdx',
        nullGuardInstructionVa=at,ownedNullExitVa=null,referenceStoreVa=store,disabledCollectorCellVa=disabled,
        completeOriginalProgram=True,normalIncomingValueStoredUnchanged=True,ordinaryFrameRestored=True,
        entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],normalReturn=True,enabledCollectorAdmitted=False,
        condition='Compatible nonnull current nominal original holder, stable disjoint pointer-sized destination and an independently proved current DWORD collector cell equal to zero. Incoming whole RDX is stored before JE without flag clobber; original Win64 homes/frame are restored. Enabled collection and live invocation remain unobserved.')
