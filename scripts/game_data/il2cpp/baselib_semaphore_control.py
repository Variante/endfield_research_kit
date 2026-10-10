"""Complete selected Baselib semaphore/thread-ID control and physical arguments.

Imported functions returning normally with the selected ABI remain a condition.
All owned primary/chained bytes and graph edges are checked; no live DLL/IAT,
valid semaphore creation, finite wait/retry or requested-total effect is inferred.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.integer_effects import decode_effect_instructions
from scripts.game_data.il2cpp.integer_source_operands import is_unknown_instruction
from scripts.game_data.il2cpp.integer_addressing import decode_lea_address
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.relation_control import transfer
from scripts.game_data.il2cpp.relation_import_control import _memory, _lea, _import
from scripts.game_data.il2cpp.resolver_scan_control import _raw


def _transfer(row):
    raw = bytes.fromhex(row['bytes'])
    if len(raw) == 7 and raw[:3] == b'\x48\xff\x25' or len(raw) == 6 and raw[:2] == b'\xff\x25':
        return {'kind':'importTail', 'cell':int(row['va'],16)+len(raw)+int.from_bytes(raw[-4:],'little',signed=True)}
    return transfer(row)


def _owned_rows(index, function):
    base = index.pe.image_base; entry = base+function['entryRva']
    if entry not in index.extents:
        raise ValueError('baselibControl.primary-entry-missing')
    actual = sorted(set([(entry,index.extents[entry])] + [(a,a+n) for a,n in index.chained_fragments.get(entry,[])]))
    expected = [(base+w['startRva'],base+w['endRva']) for w in function['ownedWindows']]
    if actual != expected or len(set(expected)) != len(expected):
        raise ValueError('baselibControl.complete-owned-fragments')
    rows = []
    for window in function['ownedWindows']:
        start,end = base+window['startRva'],base+window['endRva']
        raw = _raw(index,start,end,window['sha256'])
        decoded = decode_effect_instructions(index.mapper,raw,start)
        if any(is_unknown_instruction(row) for row in decoded) or b''.join(bytes.fromhex(row['bytes']) for row in decoded) != raw:
            raise ValueError('baselibControl.complete-known-instructions')
        rows.extend(decoded)
    if len(rows) != function['checkedInstructionCount']:
        raise ValueError('baselibControl.instruction-count')
    return rows


def _graph(rows, base, entry):
    starts = {int(row['va'],16) for row in rows}; edges = {}; calls = []; tails = []; returns = []; branches = 0
    if len(starts) != len(rows):
        raise ValueError('baselibControl.duplicate-start')
    for row in rows:
        at = int(row['va'],16); f = _transfer(row); kind = f['kind']; targets = []
        if kind in ('jump','conditional'):
            targets.append(f['target']); branches += 1
        if kind in ('next','conditional','indirectCall'):
            targets.append(at+len(bytes.fromhex(row['bytes'])))
        if kind == 'indirectCall':
            calls.append({'siteRva':at-base,'slotRva':f['cell']-base})
        elif kind == 'importTail':
            tails.append({'siteRva':at-base,'slotRva':f['cell']-base})
        elif kind == 'return':
            returns.append(at-base)
        elif kind not in ('next','conditional','jump'):
            raise ValueError('baselibControl.unlisted-transfer-kind')
        if any(target not in starts for target in targets):
            raise ValueError('baselibControl.branch-or-continuation-boundary')
        edges[at] = set(targets)
    reached = set(); pending = [base+entry]
    while pending:
        at = pending.pop()
        if at in reached:
            continue
        reached.add(at); pending.extend(edges[at]-reached)
    if reached != starts:
        raise ValueError('baselibControl.uncovered-owned-instructions')
    return {'checkedInstructions':len(rows),'checkedBranches':branches,'importCallSites':calls,
            'importTailSites':tails,'returnSites':returns,'staticPossibleReachableInstructions':len(reached)}


def _point(g, base, function, label):
    if int(g.rows[g.cursor]['va'],16) != base+function['labels'][label]:
        g.fail('checked-label:'+label,function['labels'][label],g.rows[g.cursor])


def _same_eax(g):
    row = g.take('mov eax, eax')
    if bytes.fromhex(row['bytes']) != b'\x8b\xc0':
        g.fail('zero-extend-eax','original DWORD self move',row)


def validate_baselib_semaphore_control(index, contract):
    base = index.pe.image_base; imports = {r['role']:base+r['slotRva'] for r in contract['kernelImports']}
    if set(imports) != {'GetLastError','ReleaseSemaphore','WaitForSingleObjectEx','GetCurrentThreadId'} or len(set(imports.values())) != 4:
        raise ValueError('baselibControl.kernel-import-roles')
    functions = {f['role']:f for f in contract['functions']}
    if set(functions) != {'Acquire','Release','ThreadId'} or len(functions) != len(contract['functions']):
        raise ValueError('baselibControl.function-roles')
    frame = contract['frames']; programs = {}; summaries = []
    for role,function in functions.items():
        rows = _owned_rows(index,function); programs[role] = rows
        summaries.append({'role':role,'ownedBytes':sum(w['endRva']-w['startRva'] for w in function['ownedWindows']),
                          **_graph(rows,base,function['entryRva'])})
    leaf = frame['callBytes']; release_frame = frame['releaseBytes']
    g = ProgramGrammar(programs['ThreadId'],label='baselibControl.threadId')
    g.take(f'sub rsp, 0x{leaf:x}'); _import(g,imports['GetCurrentThreadId']); _same_eax(g)
    g.take(f'add rsp, 0x{leaf:x}','ret'); g.finish()
    f = functions['Acquire']; g = ProgramGrammar(programs['Acquire'],label='baselibControl.acquire')
    g.take(f'sub rsp, 0x{leaf:x}','xor r8d, r8d',f'mov edx, 0x{contract["infiniteWaitWord"]:x}')
    _import(g,imports['WaitForSingleObjectEx']); g.take('cmp eax, -0x1')
    g.branch('jne','ordinaryReturn'); g.take(f'add rsp, 0x{leaf:x}')
    row = g.row()
    if _transfer(row) != {'kind':'importTail','cell':imports['GetLastError']}:
        g.fail('restored-error-tail','GetLastError tail after full frame restoration',row)
    g.mark('ordinaryReturn'); _point(g,base,f,'ordinaryReturn')
    g.take(f'add rsp, 0x{leaf:x}','ret'); g.finish()
    f = functions['Release']; g = ProgramGrammar(programs['Release'],label='baselibControl.release')
    g.take('test edx, edx'); g.branch('je','zeroReturn')
    _memory(g,'store','rbx',8,base='rsp',displacement=frame['saveRbxEntryOffset'])
    g.take('push rdi',f'sub rsp, 0x{release_frame:x}','xor r8d, r8d','mov edi, edx','mov rbx, rcx')
    _import(g,imports['ReleaseSemaphore']); g.take('test eax, eax'); g.branch('jne','restoreRbx')
    _memory(g,'store','rsi',8,base='rsp',displacement=frame['saveRsiOffset']); g.take('xor esi, esi','nop')
    g.mark('retry'); _point(g,base,f,'retry'); _import(g,imports['GetLastError'])
    _lea(g,'r8',displacement=frame['previousCountOffset'])
    _memory(g,'store','esi',4,base='rsp',displacement=frame['previousCountOffset'])
    g.take('mov edx, 0x1','mov rcx, rbx'); _import(g,imports['ReleaseSemaphore'])
    g.take('test eax, eax'); g.branch('je','failedSingleRelease')
    g.take(f'mov eax, 0x{contract["releaseLimitWord"]:x}','mov rcx, rbx')
    row = g.row(); fact = row.get('memorySourceSubtractOperation',{}); address = fact.get('sourceAddress',{})
    if (fact.get('bits'),fact.get('destinationRegister'),fact.get('memoryReadBytes'),
        address.get('base'),address.get('index'),address.get('displacement')) != (32,'eax',4,'rsp',None,frame['previousCountOffset']):
        g.fail('previous-count-dword-subtract','DWORD previous count from actual output slot',row)
    g.take('cmp edi, eax'); row = g.row()
    if row.get('conditionalMove') != {'condition':'b','destination':'eax','source':'edi','width':32}:
        g.fail('unsigned-request-cap-selection','CMOVB EAX, EDI',row)
    g.take('xor r8d, r8d'); row = g.row(); raw = bytes.fromhex(row['bytes'])
    decoded = decode_lea_address(raw,0,int(row['va'],16))
    fact = decoded[0]['addressOperation'] if decoded is not None and decoded[1] == len(raw) else {}
    if (fact.get('destination'),fact.get('destinationBits'),fact.get('base'),fact.get('index'),fact.get('displacement'),
        fact.get('readsMemory'),fact.get('zeroExtendsTo64')) != ('edi',32,'rax',None,-1,False,True):
        g.fail('dword-adjusted-request','DWORD zero-extending LEA of selected value minus one',row)
    g.take('mov edx, edi'); _import(g,imports['ReleaseSemaphore'])
    g.take('test eax, eax'); g.branch('je','retry')
    _memory(g,'load','rsi',8,base='rsp',displacement=frame['saveRsiOffset'])
    restore_rbx = frame['saveRbxEntryOffset']+8+release_frame
    _memory(g,'load','rbx',8,base='rsp',displacement=restore_rbx)
    g.take(f'add rsp, 0x{release_frame:x}','pop rdi','ret')
    g.mark('failedSingleRelease'); _point(g,base,f,'failedSingleRelease'); _import(g,imports['GetLastError'])
    _memory(g,'load','rsi',8,base='rsp',displacement=frame['saveRsiOffset'])
    g.mark('restoreRbx'); _point(g,base,f,'restoreRbx')
    _memory(g,'load','rbx',8,base='rsp',displacement=restore_rbx)
    g.take(f'add rsp, 0x{release_frame:x}','pop rdi')
    g.mark('zeroReturn'); _point(g,base,f,'zeroReturn'); g.take('ret'); g.finish()
    return {'completeOwnedPrimaryChainedProgramsChecked':True,'programs':summaries,
        'checkedInstructions':sum(s['checkedInstructions'] for s in summaries),
        'ownedBytes':sum(s['ownedBytes'] for s in summaries),
        'threadIdZeroExtendedDwordResultProved':True,
        'acquirePreservesHandleAndPassesInfiniteNonalertableWaitProved':True,
        'acquireFailedWaitRestoresFrameThenTailCallsGetLastErrorProved':True,
        'releaseZeroRequestReturnsBeforeAnyImportProved':True,
        'releaseOriginalHandleAndRequestFirstCallProved':True,
        'releaseFailureSinglePreviousCountOutputAndUnsignedCapControlProved':True,
        'releaseRetryCarriesAdjustedDwordRequestProved':True,
        'adjustedReleaseHasNoAdditionalZeroGuardProved':True,
        'normalBranchesRestoreApplicableSavedRegistersAndFrameProved':True,
        'adjustedRequestExpression':'uint32(min_unsigned(previous request, uint32(recorded limit minus previous count)) minus one)',
        'releaseLimitWord':contract['releaseLimitWord'],'counterArithmeticBits':32,
        'conditions':contract['conditions'],'actualLoadedLibraryOrIatBindingProved':False,
        'validSemaphoreInitializationOrObservedEffectsProved':False,
        'finiteWaitOrRetryProved':False,'totalSuccessfulReleaseEqualsOriginalRequestProved':False,
        'contextChildSlotMutationProved':False,'callbackCursorEqualityProved':False,
        'positiveListAdmitted':False,'wholeRootAdmitted':False}
