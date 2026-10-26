"""Selected buffered four-byte output-list programs and scalar source transfer.

The caller owns native gates, exact unwind membership and typed registrations.
The list's output and array widths never choose a serialized element formatter.
Allocation, growth, refill, barriers and live generic inflation remain separate.
"""
from __future__ import annotations

from .reference_conversion_sources import _target, validate_program


def _guards(proof, choices, *, fail):
    for index, opcode, taken in choices:
        at, raw_hex = proof['program'][index]; raw = bytes.fromhex(raw_hex)
        if (raw[:len(opcode)] != opcode or proof['program'][index+1][0] !=
                (_target(at, raw) if taken else at+len(raw))):
            fail('value-list-selected-guard', {'position':index,'taken':taken}, [at,raw_hex])


def validate_buffered_dword_output_list(image, programs, offsets, *, fail):
    """Own null, existing-empty and a complete repeated spare-capacity loop."""
    if set(programs) != {'singleElement','twoElements','emptyExisting','nullList'}:
        fail('value-list-programs','four explicit selected paths',sorted(programs))
    if (set(offsets) != {'currentPtr','bufferLength','advancedCount','consumed','totalLength'}
            or any(type(n) is not int or not 0 <= n < 128 for n in offsets.values())
            or len(set(offsets.values())) != len(offsets)):
        fail('value-list-reader-fields','distinct bounded reader offsets',offsets)
    for proof in programs.values():
        validate_program(image,proof,fail=fail,extra_opcodes={'482BC8':'sub rcx, rax'})
    pointer,remaining,advanced,consumed,total = (offsets[k] for k in
        ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    prefix=['4053','55','4154','4155','4156','4883EC30',f'837A{remaining:02X}04',
        '498BE9','4D8BF0','C744246800000000','4C8BEA',None,
        f'498B45{pointer:02X}','448B20','4489642420',f'418B5D{remaining:02X}','83EB04',None,
        f'498345{pointer:02X}04',f'418345{advanced:02X}04',f'418345{consumed:02X}04',
        f'41895D{remaining:02X}',f'496345{consumed:02X}',f'498B4D{total:02X}',
        '482BC8','4963C4','483BC8',None,'4183FCFF','4889742460','0F95C0','84C0',None,
        '48897C2470','4C897C2478','49833E00','488B4520','488B88C0000000',None,
        '488B4110','498B1E','4883782000',None,'FF431C','C7431800000000',None,
        None,'83B9E000000000',None,'488B4520','488B88C0000000','488B4918',None,
        '33FF','4C8BF8','4585E4',None]
    loop=['C744246800000000','4D85FF',None,'498B0F',None,'498B07','4C8D442468',
        '498BD5','498BCF','4C8B8898010000','FF9090010000','498B1E','448B642468',
        '4885DB',None,'488B4520','488B88C0000000','488B4130','4883782000',None,
        '488B4520','488B5310','488B88C0000000','488B7130','FF431C','48634B18',
        '4885D2',None,'3B4A18',None,'8D4101','894318','3B4A18',None,'4489648A20',
        'FFC7','3B7C2420',None]
    suffix=['488B7C2470','4C8B7C2478','488B742460','4883C430','415E','415D','415C','5D','5B','C3']
    single=programs['singleElement']; program=single['program']
    if (len(prefix),len(loop),len(suffix),len(program)) != (57,38,10,105):
        fail('value-list-complete-profile','57 + 38 + 10 instructions',len(program))
    for index,(row,wanted) in enumerate(zip(program,prefix+loop+suffix,strict=True)):
        if wanted is not None and row[1] != wanted:
            fail('value-list-owned-transfer-or-cursor',{'position':index,'bytes':wanted},row)
    if programs['twoElements']['program'] != program[:57]+program[57:95]*2+program[95:]:
        fail('value-list-exact-loop-repetition','same full loop repeated with its actual back edge',programs['twoElements']['program'])
    if programs['emptyExisting']['program'] != program[:57]+program[95:]:
        fail('value-list-empty-path','same saved-count control and restored frame, without a child',programs['emptyExisting']['program'])
    null=programs['nullList']; np=null['program']
    if len(np) != 44 or np[:33] != program[:33] or np[-8:] != program[-8:]:
        fail('value-list-null-complete-path','same count reader, null branch and full epilogue',np)
    barrier=bytes.fromhex(np[33][1])
    if len(barrier) != 7 or barrier[:2] != b'\x83\x3d' or barrier[-1] != 0 or np[34][1] != '49C70600000000':
        fail('value-list-null-output','RIP DWORD zero guard and full null output pointer',np[33:35])
    _guards(single,[(11,b'\x7d',True),(17,b'\x79',True),(27,b'\x0f\x8c',False),
        (32,b'\x0f\x84',False),(38,b'\x74',False),(42,b'\x75',True),(48,b'\x75',True),
        (56,b'\x0f\x8e',False),(59,b'\x0f\x84',False),(71,b'\x0f\x84',False),
        (76,b'\x75',True),(84,b'\x0f\x84',False),(86,b'\x72',True),(90,b'\x0f\x83',False)],fail=fail)
    _guards(programs['emptyExisting'],[(56,b'\x0f\x8e',True)],fail=fail)
    _guards(null,[(32,b'\x0f\x84',True),(35,b'\x74',True)],fail=fail)
    back_at,back_hex=program[94];back=bytes.fromhex(back_hex)
    if (back[:2] != b'\x0f\x8c' or _target(back_at,back) != program[57][0]
            or program[95][0] != back_at+len(back)):
        fail('value-list-saved-count-back-edge','signed index/count comparison to actual loop entry',program[93:96])
    jump=bytes.fromhex(program[45][1])
    if len(jump) != 5 or jump[0] != 0xe9 or _target(program[45][0],jump) != program[46][0]:
        fail('value-list-existing-list-edge','reset joins the same provider preparation',program[45])
    usage=bytes.fromhex(program[46][1])
    if len(usage) != 7 or usage[:3] != b'\x48\x8b\x0d':
        fail('value-list-provider-class-load','complete RIP class usage',program[46])
    calls=[]
    for index in (52,61):
        at,raw_hex=program[index];raw=bytes.fromhex(raw_hex)
        if len(raw) != 5 or raw[0] != 0xe8:
            fail('value-list-physical-helper-call','complete actual CALL',program[index])
        calls.append(_target(at,raw))
    return {'scope':'selected-buffered-existing-dword-output-list-control',
        'headerWireBytes':4,'signedCountBits':32,'headerReaderCounterStores':4,
        'savedHeaderCountFrameOffset':32,'elementOutputFrameOffset':104,
        'elementOutputZeroedEachIteration':True,'runtimeElementOutputBytes':4,'runtimeArrayStrideBytes':4,
        'elementWireBytes':None,'readerRegister':'r13','childOutputRegister':'r8','formatterRegister':'r15',
        'childReceiverClassMethodPointerOffset':400,'childCompanionOffset':408,
        'physicalProviderCallRva':calls[0],'classPreparationCallRva':calls[1],
        'listStorageOffsets':{'count':24,'version':28,'items':16,'arrayLength':24,'arrayData':32},
        'loopInstructionCount':38,'loopBackEdgeRva':back_at,'singlePathInstructions':105,
        'twoElementPathInstructions':143,'existingEmptyPathInstructions':67,'nullPathInstructions':44,
        'nullSentinelBits':32,'nullSentinelSignedValue':-1,
        'nullOutputProvedUnderUnsetBarrierFlag':True,'otherNegativeCountsProvedRejected':False,
        'allocatedListPathProved':False,'runtimeProviderObserved':False,'positiveStoredGrammarAdmitted':False,
        'condition':'Coherent readable reader with a buffered count, remaining total at least the signed count; an existing list with ready generic contexts and spare capacity, non-null formatter and normal helper/child returns. The null path additionally selects an unset barrier flag.'}


def validate_buffered_dword_output_formatter(image, proof, offsets, *, fail):
    """Authenticate four source bytes to a by-reference DWORD output and RET."""
    validate_program(image,proof,fail=fail)
    pointer,remaining,advanced,consumed = (offsets[k] for k in
        ('currentPtr','bufferLength','advancedCount','consumed'))
    expected=['48895C2408','57','4883EC20',f'837A{remaining:02X}04','498BF8','488BDA',None,
        f'488B42{pointer:02X}','8B00','8907',f'8B7B{remaining:02X}','83EF04',None,
        f'488343{pointer:02X}04',f'8343{advanced:02X}04',f'8343{consumed:02X}04',
        f'897B{remaining:02X}','488B5C2430','4883C420','5F','C3']
    program=proof['program']
    if len(program) != 21:fail('dword-output-complete-profile',21,len(program))
    for index,(row,wanted) in enumerate(zip(program,expected,strict=True)):
        if wanted is not None and row[1] != wanted:
            fail('dword-output-owned-transfer',{'position':index,'bytes':wanted},row)
    _guards(proof,[(6,b'\x0f\x8c',False),(12,b'\x0f\x88',False)],fail=fail)
    cold=[]
    for index in (6,12):
        at,raw_hex=program[index];target=_target(at,bytes.fromhex(raw_hex))
        if any(p[0]==target for p in program):fail('dword-output-cold-edge','outside complete normal program',target)
        cold.append({'instructionRva':at,'targetRva':target,'effectsProved':False})
    return {'scope':'complete-buffered-normal-dword-output-formatter','wireBytesRead':4,
        'runtimeOutputBytes':4,'sourceBitsPreservedToOutput':True,'readerRegister':'rdx','outputRegister':'r8',
        'cursorUpdates':{'currentPtr':4,'bufferLength':-4,'advancedCount':4,'consumed':4},
        'normalInstructions':21,'coldEdges':cold,'elementProviderSelectionProved':False,
        'condition':'Coherent readable reader with signed bufferLength at least four, valid by-reference output, normal stack/return behavior.'}
