"""Closed sibling stores and conditional saved-cookie state of the whole caller."""
from __future__ import annotations
from .type_data_initialization_control import _complete
from .method_carrier_control import _Grammar
from .memory_moves import decode_memory_move
from .name_cache_handler_direct_init_control import validate_handler_direct_init

LABEL='nameCacheHandlerSiblingStoresControl'


def validate_handler_sibling_stores(programs, *, image_base, contract, direct_contract):
    c=contract;direct=direct_contract;base=image_base
    if set(programs)!=set(c['functions']):raise ValueError(LABEL+'.function-membership')
    for key in ('nativeInputs','cookieRva','encodedHandlerRva','calls'):
        if c[key]!=direct[key]:raise ValueError(LABEL+'.direct-contract-join:'+key)
    if any(c['functions'][k]!=direct['functions'][k] for k in ('caller','directStore')):raise ValueError(LABEL+'.caller-store-definition-join')
    previous=validate_handler_direct_init({k:programs[k] for k in ('caller','directStore')},image_base=base,contract=direct)
    children={role:f for role,f in c['functions'].items() if role!='caller'}
    entries={f['entryRva']:role for role,f in children.items()}
    if len(entries)!=len(children) or set(entries)!={p['targetRva'] for p in c['calls']}:raise ValueError(LABEL+'.complete-direct-child-membership')
    stores=c['stores']
    if not stores or any(p['role'] not in children or type(p['destinationRva']) is not int or p['destinationRva']<0 for p in stores):raise ValueError(LABEL+'.store-declarations')
    destinations=[p['destinationRva'] for p in stores]
    if any(abs(a-b)<8 for i,a in enumerate(destinations) for b in destinations[i+1:]):raise ValueError(LABEL+'.overlapping-store-cells')
    if any(abs(p-c['cookieRva'])<8 for p in destinations):raise ValueError(LABEL+'.cookie-storage-write')
    encoded=[p for p in stores if abs(p['destinationRva']-c['encodedHandlerRva'])<8]
    if encoded!=[{'role':'directStore','destinationRva':c['encodedHandlerRva']}]:raise ValueError(LABEL+'.unique-encoded-store')
    for role,f in children.items():
        rows=programs[role];graph=_complete(rows,base+f['entryRva']);g=_Grammar(rows,label=LABEL+'.'+role)
        selected=[p for p in stores if p['role']==role]
        if not selected:raise ValueError(LABEL+'.empty-child-stores:'+role)
        for store in selected:
            row=g.row();raw=bytes.fromhex(row['bytes']);parsed=decode_memory_move(raw,0,int(row['va'],16))
            facts=parsed[0]['memoryOperation'] if parsed and parsed[1]==len(raw) else {};a=facts.get('address',{})
            expected=('store','rcx',64,8,True,base+store['destinationRva'])
            actual=(facts.get('direction'),facts.get('register'),facts.get('registerBits'),facts.get('memoryBytes'),a.get('ripRelative'),a.get('absoluteAddress'))
            if actual!=expected:g.fail('exact-qword-argument-store',expected,row)
        g.take('ret');g.finish()
        if graph['calls'] or graph['traps']:raise ValueError(LABEL+'.closed-no-call-body:'+role)
    return {'status':'all-direct-children-closed-stores-and-conditional-cookie-state-proved',
        'codeInstructions':sum(map(len,programs.values())),'closedChildFunctions':len(children),'qwordStores':len(stores),
        'wholeCallerAndActualFiveChildEdgesProved':previous['callerPassesSameSavedCookieWordToEveryDirectChildProved'],
        'allDirectChildProgramsClosedWithoutCallsOrExplicitRegisterWritesProved':True,
        'exactNonoverlappingCookieDisjointGlobalStoresProved':True,
        'conditionalReturnStateEncodedEqualsEntryCookieProved':True,
        'conditionalSameCookieGetterDecodeAtReturnIsZeroProved':True,
        'fullRaxUpperBitsPreservedFromCallerEntryProved':True,'callerReturnOnlyAlTrueProved':True,
        'siblingEffectsRemainUnknownWithinSelectedClosedPrograms':False,
        'fullRaxBooleanReturnProved':False,'actualCallerInvocationOrStartupOrderProved':False,
        'concurrentWriterAbsenceProved':False,'allHandlerWriterCoverageProved':False,
        'absenceOfEnclosingLockProved':False,'actualCallbackIdentityOrInvocationProved':False,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'conditions':c['conditionalDomain']}
