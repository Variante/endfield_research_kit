"""Whole selected managed number-lookup CFG, including its arbitrary loop.

Authenticated block instructions and all selected edges establish a static
relation under coherent stable list/String state and normal dispatch guards.
Actual Burst getter results, receiver contents and execution remain unknown.
"""
from __future__ import annotations
from typing import Any, Callable

MODE='managed-number-lookup-complete-conditional-loop'


def templates(pair: dict, limits: dict, first_char: int) -> dict:
    cells=pair['unboxedCells'];item=pair['closedListItemTransfer'];numeric=pair['numericPredicate']
    if (cells['key']!=0 or pair['unboxedSize']!=32 or item['selectedReadBytes']!=32
            or item['openGenericFieldOffsetsUsed'] or numeric['stringLengthBits']!=32):
        raise ValueError('numberLookup.independent-pair-layout')
    values=[item['arrayReferenceCell'],item['listUnsignedBoundCell'],item['arrayUnsignedBoundCell'],
        numeric['stringLengthOffset'],cells['valueDouble'],0x30+cells['valueStr'],first_char]
    if any(type(v)is not int or not 0<=v<128 for v in values):raise ValueError('numberLookup.cell-width')
    ref,bound,array,length,double,string,char=[f'{v:02X}' for v in values]
    if (set(limits)!={'lookup','comparison','numeric'} or any(type(v)is not int or not 0<=v<1<<31 for v in limits.values())
            or limits['comparison']>=128 or limits['numeric']!=numeric['normalSignedDispatchLimit']):
        raise ValueError('numberLookup.dispatch-limits')
    lookup_limit=limits['lookup'].to_bytes(4,'little').hex().upper()
    numeric_limit=limits['numeric'].to_bytes(4,'little').hex().upper()
    g=lambda name,prefix:('global',name,prefix)
    guard=lambda opcode:('guard',opcode)
    branch=lambda opcode,taken,fallthrough:('branch',opcode,taken,fallthrough)
    jump=lambda opcode,target:('jump',opcode,target)
    return {
        'entry':['4056','57','4155','4881EC90000000','0F57C0','488BF9',g('dispatch','488B0D'),'4D8BE8',
            '0F11442430','488BF2','0F11442440','83B9E000000000',guard('0F84'),'488B81B8000000',
            '48899C24B0000000','4889AC24B8000000','4C89A424C0000000','488B10','4C89B42488000000',
            '4C89BC2480000000','0F29742470','4885D2',guard('0F84'),'817A18'+lookup_limit,guard('0F8F')],
        'initialCount':['4533E4','418BDC','443967'+bound,branch('0F8E','zeroOut','initialClass')],
        'initialClass':[g('comparison','4C8B05'),'660F1F440000'],
        'countCompare':['3B5F'+bound],
        'loopBound':[guard('0F83'),'488B4F'+ref,'4885C9',guard('0F84'),'3B59'+array,guard('0F83'),
            '4863C3','48FFC0','48C1E005','0F103408','4539A0E0000000',guard('0F84'),'498B80B8000000',
            '488B10','4885D2',guard('0F84'),'837A18'+f'{limits["comparison"]:02X}',guard('0F8F'),
            '66480F7EF1','4885C9',guard('0F84'),'4885F6',guard('0F84'),'8B46'+length,'3941'+length,
            branch('74','lengthEqual','advance')],
        'advance':['FFC3','3B5F'+bound,branch('7C','loopBound','zeroOut')],
        'zeroOut':['4D896500','32C0',jump('E9','epilogue')],
        'lengthEqual':['8B69'+length,'4C8D71'+char,g('burstContext','488B0D'),'4439A1E0000000',guard('0F84'),
            g('burstState','488B0D'),'4439A1E0000000',guard('0F84'),'33C9',('call','burstGetterMethod'),
            '84C0',('selected','0F84','callback')],
        'callback':['448BC5','488D56'+char,'498BCE',('call','comparisonMethod'),'90',jump('E9','comparisonResult')],
        'comparisonResult':['84C0',branch('0F84','rejectReload','loadPair')],
        'loadPair':['3B5F'+bound,guard('0F83'),'488B4F'+ref,'4885C9',guard('0F84'),'3B59'+array,guard('0F83'),
            '4863C3','48FFC0','48C1E005','0F100408','0F11442430','0F104C0810',g('dispatch','488B0D'),
            '0F114C2440','4439A1E0000000',guard('0F84'),'488B81B8000000','488B10','4885D2',guard('0F84'),
            '817A18'+numeric_limit,guard('0F8F'),'488B4424'+string,'4885C0',branch('74','numericTrue','numericLength')],
        'numericLength':['443960'+length,branch('76','numericTrue','nonNumeric')],
        'nonNumeric':['32C0'],
        'numericResult':['84C0',branch('74','rejectReload','readDouble')],
        'readDouble':['3B5F'+bound,guard('0F83'),'488B4F'+ref,'4885C9',guard('0F84'),'3B59'+array,guard('0F83'),
            '4863C3','48FFC0','48C1E005','F20F104C08'+double,'B001','F2410F114D00'],
        'epilogue':['0F28742470','4C8BBC2480000000','4C8BB42488000000','4C8BA424C0000000',
            '488BAC24B8000000','488B9C24B0000000','4881C490000000','415D','5F','5E','C3'],
        'numericTrue':['B001',jump('EB','numericResult')],
        'rejectReload':[g('comparison','4C8B05'),jump('E9','advance')]}


FALLTHROUGH={'entry':'initialCount','initialClass':'countCompare','countCompare':'loopBound',
    'nonNumeric':'numericResult','readDouble':'epilogue'}


def _relative(row: list, opcode: str, fail: Callable) -> int:
    at,h=row;raw=bytes.fromhex(h);prefix=bytes.fromhex(opcode)
    width=4 if opcode in ('E8','E9') or len(prefix)==2 else 1
    if len(raw)!=len(prefix)+width or not raw.startswith(prefix):
        fail('lookup-control-opcode',opcode,row)
    return at+len(raw)+int.from_bytes(raw[-width:],'little',signed=True)


def validate(image: Any,c: dict,pair: dict,comparison: dict,*,fail: Callable) -> dict:
    if c.get('mode')!=MODE:fail('lookup-mode',MODE,c.get('mode'))
    if (not comparison['completeLeafControlFlowProved'] or comparison['inputUnitBits']!=16
            or comparison['foldDomain']!='ASCII uppercase A-Z' or comparison['unicodeCaseFoldingPerformed']):
        fail('lookup-comparison-relation','independently proved complete ASCII-only word comparison',comparison)
    specs=templates(pair,c['limits'],c['stringFirstCharOffset']);blocks=c['blocks'];windows=c['codeWindows']
    if set(blocks)!=set(specs):fail('lookup-whole-cfg-blocks',sorted(specs),sorted(blocks))
    image.check_windows(windows,label='blackboardNumberLookup')
    for name,expected in specs.items():
        rows=blocks[name]
        if (not isinstance(rows,list) or len(rows)!=len(expected)
                or any(not isinstance(r,list) or len(r)!=2 or type(r[0])is not int or not isinstance(r[1],str) for r in rows)):
            fail('lookup-block-shape',[name,len(expected)],rows)
    starts={name:rows[0][0] for name,rows in blocks.items()}
    if len(set(starts.values()))!=len(starts) or starts['entry']!=c['method'][3]:
        fail('lookup-cfg-entry','unique block entries and actual registered method entry',starts)
    all_rows=[row for rows in blocks.values() for row in rows]
    if len({row[0] for row in all_rows})!=len(all_rows):fail('lookup-overlapping-blocks','distinct selected instruction cells',all_rows)
    spans=sorted((at,at+len(bytes.fromhex(h))) for at,h in all_rows)
    if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):fail('lookup-overlapping-instructions','distinct complete instructions',spans)
    selected_addresses={row[0] for row in all_rows};edges={};guards=[];calls=[]
    for name,expected in specs.items():
        rows=blocks[name]
        if len(rows)!=len(expected):fail('lookup-block-size',[name,len(expected)],len(rows))
        image.check_instruction_windows(rows,label='blackboardNumberLookup')
        for i,(row,wanted) in enumerate(zip(rows,expected,strict=True)):
            at,h=row;raw=bytes.fromhex(h)
            if not raw or not any(w['startRva']<=at<at+len(raw)<=w['endRva'] for w in windows):
                fail('lookup-owned-instruction','one exact current unwind-owned window',row)
            if i and rows[i-1][0]+len(bytes.fromhex(rows[i-1][1]))!=at:
                fail('lookup-block-contiguity',name,rows[i-1:i+1])
            if isinstance(wanted,str):
                if h!=wanted:fail('lookup-field-or-register-instruction',[name,i,wanted],row)
                continue
            kind=wanted[0]
            if kind=='global':
                _,role,prefix=wanted;op=bytes.fromhex(prefix)
                if len(raw)!=7 or not raw.startswith(op) or at+7+int.from_bytes(raw[3:],'little',signed=True)!=c['globalCells'][role]:
                    fail('lookup-global-source',[role,prefix,c['globalCells'][role]],row)
            elif kind=='call':
                target=_relative(row,'E8',fail)
                if target!=c[wanted[1]][3]:fail('lookup-callee-identity',c[wanted[1]],row)
                calls.append({'block':name,'method':c[wanted[1]]})
            elif kind=='guard':
                target=_relative(row,wanted[1],fail)
                if any(a<=target<b for a,b in spans) or not any(w['startRva']<=target<w['endRva'] for w in windows):
                    fail('lookup-unselected-guard-target','excluded owned path, never another selected instruction',row)
                guards.append({'block':name,'instruction':i,'opcode':wanted[1],'selectedTaken':False})
            elif kind in ('branch','selected','jump'):
                if i!=len(rows)-1:fail('lookup-block-terminator','last instruction',row)
                target=_relative(row,wanted[1],fail)
                if target!=starts[wanted[2]]:fail('lookup-selected-branch-target',starts[wanted[2]],row)
                if kind=='branch':
                    if at+len(raw)!=starts[wanted[3]]:fail('lookup-branch-fallthrough',starts[wanted[3]],row)
                    edges[name]=[wanted[2],wanted[3]]
                else:
                    if kind=='selected' and any(a<=at+len(raw)<b for a,b in spans):
                        fail('lookup-burst-enabled-exclusion','enabled path excluded from managed CFG',row)
                    edges[name]=[wanted[2]]
            else:fail('lookup-template-kind','known complete instruction semantics',wanted)
        if name in FALLTHROUGH:
            last=rows[-1];next_pc=last[0]+len(bytes.fromhex(last[1]));successor=FALLTHROUGH[name]
            if next_pc!=starts[successor]:fail('lookup-block-fallthrough',starts[successor],last)
            edges[name]=[successor]
        elif name=='epilogue':edges[name]=[]
        elif name not in edges:fail('lookup-unclosed-block',name,rows[-1])
    reached=set();pending=['entry']
    while pending:
        node=pending.pop()
        if node in reached:continue
        reached.add(node);pending.extend(edges[node])
    if reached!=set(blocks):fail('lookup-cfg-reachability','every selected block reachable from actual entry',sorted(set(blocks)-reached))
    # Every rejection reaches the same INC EBX/CMP; JL returns to the existing
    # unsigned branch, preserving those CMP flags. For stable coherent count
    # N <= INT32_MAX and 0 <= i < N, i+1 <= N cannot overflow. This is a loop
    # invariant proof, not a finite trace or an observed receiver/result.
    return {'completeSelectedManagedLookupCfgProved':True,'selectedBlocks':len(blocks),
        'selectedInstructions':len(all_rows),'selectedEdges':edges,'normalFallthroughGuards':guards,'actualDirectCalls':calls,
        'inputOriginsProved':{'rdi':'incoming Blackboard rcx','rsi':'incoming key rdx','r13':'incoming double-output address r8'},
        'indexRelation':'Int32 index starts at zero; every rejected candidate increments once; signed continuation reuses the same count CMP flags at the unsigned bound branch',
        'arbitraryLoopProved':True,'loopCountStableCoherentNonnegativeInt32Required':True,
        'loopRank':'stable list count minus current nonnegative index',
        'keyInputOriginsProved':{'first':'selected element key -> xmm6.low64 -> rcx -> firstChar pointer in r14',
            'second':'original key in rsi -> same firstChar pointer','length':'candidate key length in ebp after equal Int32 length check'},
        'normalManagedComparisonRelation':'equal lengths and equal ASCII-uppercase-folded 16-bit units',
        'lengthMismatchAndUnequalKeysContinue':True,'matchingNonNumericValuesContinue':True,
        'numericSelectionRelation':'selected pair valueStr is null or its named String length is zero',
        'foundOutputRelation':'first matching numeric candidate valueDouble bits -> xmm1.low64 -> original r13 output; AL=1',
        'notFoundOutputRelation':'zero Int64 bits from r12 -> original r13 output; AL=0',
        'outputWriteBytes':8,'numericConversionPerformed':False,'pairDynamicFlagRead':False,
        'allSelectedReturnsRestoreSavedRegistersAndFrame':True,
        'burstGetterFalseForEveryReachedComparisonRequired':True,'normalWin64BurstGetterReturnRequired':True,
        'stableCoherentReadableInputsAndDispatchCellsRequired':True,'validWritableOriginalOutputRequired':True,
        'lookupPrefixCallbackAndCompleteLoopComposed':True,
        'wholeLookupAllDispatchPathsProved':False,'actualInputStateOrFoundValueKnown':False,
        'runtimeExecutionKnown':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}
