"""Saved-cookie argument flow into a closed direct store, not startup ordering."""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .method_carrier_resolution import _global
from .memory_moves import decode_memory_move

LABEL='nameCacheHandlerDirectInitControl'


def validate_handler_direct_init(programs,*,image_base,contract):
    c=contract;base=image_base
    if set(programs)!={'caller','directStore'} or set(c['functions'])!=set(programs):raise ValueError(LABEL+'.function-membership')
    graphs={role:_complete(rows,base+c['functions'][role]['entryRva']) for role,rows in programs.items()}
    g=_Grammar(programs['caller'],label=LABEL+'.caller');g.take('push rbx','sub rsp, 0x20');_global(g,'rbx',8,base+c['cookieRva'])
    if len(c['calls'])!=5:raise ValueError(LABEL+'.call-sequence-length')
    for call in c['calls']:
        g.take('mov rcx, rbx');row=g.call(base+call['targetRva'])
        if int(row['va'],16)!=base+call['siteRva']:g.fail('actual-call-site',call['siteRva'],row)
    g.take('mov al, 0x1','add rsp, 0x20','pop rbx','ret');g.finish()
    selected=[r for r in c['calls'] if r['targetRva']==c['functions']['directStore']['entryRva']]
    if len(selected)!=1:raise ValueError(LABEL+'.selected-direct-store-call')
    g=_Grammar(programs['directStore'],label=LABEL+'.store');row=g.row();raw=bytes.fromhex(row['bytes'])
    parsed=decode_memory_move(raw,0,int(row['va'],16));f=parsed[0]['memoryOperation'] if parsed and parsed[1]==len(raw) else {};a=f.get('address',{})
    if (f.get('direction'),f.get('register'),f.get('memoryBytes'),a.get('ripRelative'),a.get('absoluteAddress'))!=('store','rcx',8,True,base+c['encodedHandlerRva']):g.fail('direct-qword-store',c['encodedHandlerRva'],row)
    g.take('ret');g.finish()
    if graphs['directStore']['calls'] or graphs['directStore']['traps']:raise ValueError(LABEL+'.closed-store-body')
    return {'status':'saved-cookie-to-direct-handler-store-and-sibling-argument-flow-proved',
        'codeInstructions':sum(len(p) for p in programs.values()),
        'callerPassesSameSavedCookieWordToEveryDirectChildProved':True,
        'actualStoreEntryAndExactQwordDestinationProved':True,'directStoreHasNoGuardCallProved':True,
        'sameSavedCookieDecodedAtStoreWouldGiveZeroProved':True,'callerReturnOnlyAlTrueProved':True,
        'siblingCallsPreserveNonvolatileRbxAssumed':True,'siblingMemoryEffectsProved':False,
        'globalCookieStillEqualsSavedWordProved':False,'storedWordSurvivesLaterSiblingCallsProved':False,
        'callerInvokedOrStartupOrderingProved':False,'guardNotHeldByAncestorProved':False,
        'allWriterProtectionProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,
        'conditions':c['conditionalDomain']}
