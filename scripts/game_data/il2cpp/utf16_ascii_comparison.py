"""Prove the pure 16-bit ASCII-folding comparison CFG of a registered leaf.

Readable spans, unchanged input memory and normal instruction completion are
conditions. This validates the whole bounded leaf, including both returns and
the arbitrary-length loop; it does not observe execution or Unicode folding.
"""
from __future__ import annotations
from typing import Any, Callable

MODE = 'utf16-unit-ascii-uppercase-fold-comparison'
# Only instruction semantics live here. Native locations and bytes are read
# from a reviewed contract and authenticated against the selected image.
PATTERNS = ['4D63D8','4C8BCA','4533C0','4C8BD1','4D85DB',None,'4C2BD2',
    '430FB7040A','430FB7140A','6683E841','410FB709','6683C220','6683F819',
    '410FB701','66430F47140A','6683C120','6683E841','6683F819','66410F4709',
    '663BD1',None,'49FFC0','4983C102','4D3BC3',None,'B001','C3','32C0','C3']

def fold_unit(unit: int) -> int:
    """The proved word-width SUB/CMP/ADD/CMOVA relation, not a Unicode codec."""
    if type(unit) is not int or not 0 <= unit <= 0xffff:
        raise ValueError('UTF-16 unit must be an unsigned word')
    return (unit+0x20)&0xffff if ((unit-0x41)&0xffff) <= 0x19 else unit

def validate(image: Any, proof: dict, *, fail: Callable) -> dict:
    rows = proof['instructions'];window = proof['codeWindow']
    if len(rows) != len(PATTERNS):fail('ascii-comparison-program-size',len(PATTERNS),len(rows))
    image.check_windows([window],label='utf16AsciiComparison')
    image.check_instruction_windows(rows,label='utf16AsciiComparison')
    if rows[0][0] != window['startRva'] or rows[-1][0]+1 != window['endRva']:
        fail('ascii-comparison-whole-leaf','exact registered entry through final RET',[rows[0],rows[-1],window])
    for i,(row,wanted) in enumerate(zip(rows,PATTERNS,strict=True)):
        raw=bytes.fromhex(row[1])
        if wanted is not None and row[1]!=wanted:fail('ascii-comparison-instruction',[i,wanted],row)
        if i and rows[i-1][0]+len(bytes.fromhex(rows[i-1][1])) != row[0]:
            fail('ascii-comparison-contiguity','complete bounded leaf',row)
    for index,opcode,target in ((5,0x7e,25),(20,0x75,27),(24,0x7c,7)):
        row=rows[index];raw=bytes.fromhex(row[1])
        if len(raw)!=2 or raw[0]!=opcode or row[0]+2+int.from_bytes(raw[1:],'little',signed=True)!=rows[target][0]:
            fail('ascii-comparison-branch',[index,opcode,rows[target][0]],row)
    # The word-width conditional moves restore the original units outside
    # unsigned ((unit-'A') mod 2^16) <= 25. The checked counter starts at zero,
    # advances once per equal unit and reaches a sign-extended Int32 bound.
    # The pointer difference is constant; the second pointer advances by two.
    return {'completeLeafControlFlowProved':True,'inputRegisters':['rcx','rdx','r8d'],
        'inputUnitBits':16,'lengthBits':32,'lengthSigned':True,
        'nonpositiveLengthReturnsTrueWithoutInputReads':True,
        'foldDomain':'ASCII uppercase A-Z','uppercaseDelta':32,
        'outsideFoldDomainUnitsPreserved':True,'unicodeCaseFoldingPerformed':False,
        'equalFoldedUnitsContinueUntilSignedLengthBound':True,
        'firstDifferentFoldedUnitsReturnFalse':True,
        'selectedMemoryWrites':0,'selectedCalls':0,
        'readableStableInputSpansRequired':True,'normalInstructionCompletionRequired':True,
        'runtimeExecutionKnown':False,'actualInputStringsOrComparisonResultKnown':False,
        'evidenceBoundary':'conditional'}
