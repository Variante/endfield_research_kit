"""Conditional value-pair constructors, numeric predicate and list transfer.

The selected barrier's actual instructions, rather than a volatile-register
ABI assumption, establish preservation across constructor calls. Managed
references and opaque padding make this a runtime value layout, not wire data.
"""
from __future__ import annotations
from typing import Any, Callable
from scripts.game_data.memorypack import reference_conversion_sources as paths
from scripts.game_data.memorypack.buffered_reference_wrappers import validate_fast_reference_barrier

MODE = 'value-pair-constructors-numeric-predicate-and-closed-list-copy'


def _profile(image: Any, proof: dict, expected: list, branches: dict, fail: Callable) -> list:
    paths.validate_program(image, proof, fail=fail)
    rows = proof['program']
    if len(rows) != len(expected):fail('pair-program-size', len(expected), len(rows))
    for i, (row, wanted) in enumerate(zip(rows, expected, strict=True)):
        raw = bytes.fromhex(row[1])
        if wanted is not None and row[1] != wanted:fail('pair-instruction', [i, wanted], row)
        if i in branches:
            opcode, taken = branches[i];op = bytes.fromhex(opcode)
            if len(raw) != len(op)+(1 if len(op)==1 else 4) or not raw.startswith(op):
                fail('pair-branch-opcode', [i, opcode], row)
            next_pc = paths._target(row[0], raw) if taken else row[0]+len(raw)
            if rows[i+1][0] != next_pc:fail('pair-selected-edge', next_pc, rows[i+1])
    return rows


def _call(row: list, target: int, fail: Callable) -> None:
    raw = bytes.fromhex(row[1])
    if len(raw)!=5 or raw[0]!=0xe8 or paths._target(row[0], raw)!=target:
        fail('pair-barrier-callee', target, row)


def validate(image: Any, contract: dict, barrier_proof: dict, *, fail: Callable) -> dict:
    cells = contract['unboxedCells'];widths = {'key':8,'valueDouble':8,'valueStr':8,'isDynamic':1}
    if (contract.get('mode')!=MODE or set(cells)!=set(widths) or cells.get('key')!=0
            or any(type(v)is not int or not 0<=v<128 for v in cells.values())):
        fail('pair-cells', 'four distinct bounded value cells with key at receiver', cells)
    spans = [set(range(cells[n], cells[n]+w)) for n,w in widths.items()]
    if any(a & b for i,a in enumerate(spans) for b in spans[i+1:]):
        fail('pair-overlapping-cells', widths, cells)
    size = contract['unboxedSize']
    if type(size)is not int or size!=32 or any(cells[n]+w>size for n,w in widths.items()):
        fail('pair-element-extent', '32-byte value containing all four cells', size)
    double=f'{cells["valueDouble"]:02X}';string=f'{cells["valueStr"]:02X}';flag=f'{cells["isDynamic"]:02X}'
    fast=validate_fast_reference_barrier(image,barrier_proof,fail=fail)
    # The shared validator checks CMP dword [RIP+disp],0; MOV R8,RCX; JE RET;
    # RET. This entire selected path has no writes/calls or other clobbers.
    barrier={**fast,'guardBits':32,'guardValueCondition':0,'changedGprs':['r8'],
        'flagsChanged':True,'preservedVolatileGprs':['rax','rcx','rdx','r9','r10','r11'],
        'preservedVolatileXmmRegisters':[f'xmm{i}' for i in range(6)],
        'normalReturnAndStableDisabledFlagRequired':True}
    expected={
        'numeric':['4883EC28','4C8BD1','488911',None,f'498D4A{string}',f'F2410F1152{double}',
            f'49C742{string}00000000',None,f'45884A{flag}','4883C428','C3'],
        'string':['4883EC28','4D8BD0','488911','4C8BD9',None,f'498D4B{string}',
            f'4D8953{string}',None,f'49C743{double}00000000',f'45884B{flag}','4883C428','C3'],
        'copy':['4883EC28','488B02','4C8BD2','488901','4C8BD9',None,f'498B42{string}',
            f'498D4B{string}',f'4D8B4A{double}',f'498943{string}',f'4D894B{double}',None,
            f'450FB64A{flag}',f'45884B{flag}','4883C428','C3']}
    for name,pattern in expected.items():
        proof=contract['constructors'][name];rows=_profile(image,proof,pattern,{},fail)
        if (rows[0][0]!=proof['method'][3] or len(proof['codeWindows'])!=1
                or rows[-1][0]+1!=proof['codeWindows'][0]['endRva']):
            fail('pair-whole-constructor', 'entry through final RET and entire owned extent', proof)
        for position in {'numeric':(3,7),'string':(4,7),'copy':(5,11)}[name]:
            _call(rows[position], fast['entryRva'], fail)
    constructors={
        'numeric':{'keySource':'rdx','doubleBitsSource':'xmm2.low64','stringBits':0,'dynamicByteSource':'r9b'},
        'string':{'keySource':'rdx','stringSource':'r8','doubleBits':0,'dynamicByteSource':'r9b'},
        'copy':{'sourceValueAddress':'rdx','sameNamedFieldBitsCopied':True,'paddingCopied':False}}
    for row in constructors.values():row.update(completeConditionalReturnProved=True,
        barrierDisabledRequired=True,rawDynamicBytePreserved=True,coherentReadableWritablePairRequired=True)
    length=contract['stringLengthOffset']
    limit=contract['numericDispatchLimit']
    if type(length)is not int or not 0<=length<128 or type(limit)is not int or not 0<=limit<1<<31:
        fail('pair-numeric-guard-shape', 'bounded String length cell and nonnegative signed dispatch limit', [length,limit])
    prefix=['4053','4883EC20','488BD9',None,'83B9E000000000',None,'488B81B8000000',
        '488B10','4885D2',None,'817A18'+limit.to_bytes(4,'little').hex().upper(),None,
        f'488B43{string}','4885C0',None]
    guards={5:('74',False),9:('74',False),11:('0F8F',False)}
    for name in ('null','empty','nonempty'):
        proof=contract['numericPredicate']['paths'][name]
        middle=[] if name=='null' else [f'8378{length:02X}00',None]
        suffix=['32C0' if name=='nonempty' else 'B001','4883C420','5B','C3']
        branches={**guards,14:('74',name=='null')}
        if name!='null':branches[16]=('76',name=='empty')
        rows=_profile(image,proof,prefix+middle+suffix,branches,fail)
        if rows[0][0]!=contract['numericPredicate']['method'][3]:
            fail('pair-numeric-entry', contract['numericPredicate']['method'][3], rows[0])
        raw=bytes.fromhex(rows[3][1])
        if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x0d':fail('pair-numeric-global-load','actual RIP-relative class pointer load',rows[3])
    numeric={'completeSelectedPaths':['null','empty','nonempty'],
        'resultRelation':'valueStr is null or its managed String length DWORD is zero',
        'doubleValueOrDynamicFlagRead':False,'normalClassFlagNonzeroRequired':True,
        'normalDispatchReferenceNonNullRequired':True,'normalSignedDispatchLimit':limit,
        'stringLengthBits':32,'stringLengthOffset':length,'numericTrueForNullOrEmpty':True,
        'numericFalseForNonempty':True,'selectedCalls':0,'selectedPairMemoryWrites':0,
        'alternateDispatchAndClassInitializationProved':False}
    item=contract['listItem'];pattern=['4883EC28','4C8BC9','443B4218',None,'488B4210',
        '4885C0',None,'443B4018',None,'4963C8','48FFC1','48C1E105','0F100401',
        '0F104C0110','498BC1','410F1101','410F114910','4883C428','C3']
    rows=_profile(image,item,pattern,{3:('73',False),6:('74',False),8:('73',False)},fail)
    if rows[0][0]!=item['method'][3]:fail('pair-list-entry',item['method'][3],rows[0])
    copied={'completeSelectedReturnProved':True,'argumentAliases':{'rcx':'32-byte output address','rdx':'list receiver','r8d':'Int32 index'},
        'returnRegister':'same output address in rax','selectedReadBytes':32,'selectedWriteBytes':32,
        'sourceRelation':'arrayReference + 32 * (signExtend(index) + 1)',
        'arrayReferenceCell':16,'listUnsignedBoundCell':24,'arrayUnsignedBoundCell':24,
        'unsignedIndexBelowBothBoundsRequired':True,'arrayReferenceNonNullRequired':True,
        'coherentNonnegativeIndexAndListStateRequired':True,'selectedCalls':0,
        'twoChunksLoadedBeforeOutputWrites':True,'paddingBitsTransferredWithoutInterpretation':True,
        'openGenericFieldOffsetsUsed':False,'namedListItemsOrSizeFieldsAdmitted':False,
        'outOfRangeAndFailurePathsProved':False}
    return {'unboxedCells':cells,'unboxedSize':size,'managedReferenceFields':['key','valueStr'],
        'constructorFieldTransfers':constructors,'disabledBarrier':barrier,
        'numericPredicate':numeric,'closedListItemTransfer':copied,'rawWireSchemaAdmitted':False,
        'runtimeExecutionKnown':False,'wholeLookupControlFlowProved':False,
        'actualLookupFoundValueProved':False,'wholeActionAdmitted':False,'wholeRootAdmitted':False}
