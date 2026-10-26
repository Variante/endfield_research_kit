"""Exact TrackingBounds36 and Mission TriggerShape44 argument-copy fragments.

These are finite parent byte programs, separate from both nominal raw child
sources, named setter semantics, complete caller frames and wire grammars.
No other value of the same width may use either profile.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

BOUNDS='Beyond.Gameplay.TrackingBounds'
TRIGGER='Beyond.Gameplay.Core.TriggerShapeData'


def need(check,condition):
    if not condition:raise ValueError('outerValueTransfer.'+check)


def frame_prefix(regions,entry,*,type_name):
    need('finite-parent-nominal',type_name in(BOUNDS,TRIGGER))
    g=BytesPath(regions,entry)
    if type_name==TRIGGER:
        g.take('488bc4','48895810','48897018','48897820','55','488d68a1','4881eca0000000')
        facts=dict(profile='mission-trigger44-RAX-RBP-frame.v1',frameBytes=168,
            entryRspAliasRegister='rax',rbpEntryRspOffset=-95,headerRbpDisplacement=103,
            headerEntryRspOffset=8,headerRspDisplacement=176,hiddenRspDisplacement=64,argumentRspDisplacement=112,
            originalIntegerHomes=dict(rbx=16,rsi=24,rdi=32,rbp=-8))
    else:
        g.take('48895c2410','4889742418','57','4881ec80000000')
        facts=dict(profile='tracking-bounds36-RSP-frame.v1',frameBytes=136,
            hiddenRspDisplacement=32,argumentRspDisplacement=80,originalIntegerHomes=dict(rbx=16,rsi=24,rdi=-8))
    return dict(typeName=type_name,selectedBytes=g.seen,**facts,
        completeFrameProved=False,headerProgramProved=False,nominalLayoutProved=False)


def program(regions,entry,*,type_name,source_target,setter_target):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    need('finite-parent-nominal',type_name in(BOUNDS,TRIGGER))
    need('literal-actual-source-and-setter',type(source_target)is type(setter_target)is int
        and source_target>0 and setter_target>0)
    trigger=type_name==TRIGGER;width=44 if trigger else 36
    g=BytesPath(regions,entry);context_at=g.at;context_cell=g.relative('4c8b05')
    g.take('488d4df7'if trigger else'488d4c2420','488b33','488bd7')
    source_at=g.at;g.call(source_target);g.take('4885f6');null=_nonnull(g)
    null=dict(null,bytes=bytes(g.bytes[null['nullTargetVa']+i]for i in range(6)).hex().upper())
    copies=[]
    def copy(opcode,offset,size,register,displacement):
        at=g.at;g.take(opcode);copies.append(dict(instructionVa=at,hex=opcode.upper(),sourceOffset=offset,
            bytes=size,sourceRegister=register,displacement=displacement,baseRegister='rbp'if trigger else'rsp'))
    if trigger:
        g.take('0f1045f7','8b451f','4533c0','0f104d07','488d5527','488bce')
        copy('0f294527',0,16,'xmm0',39)
        g.take('f20f104517');copy('f20f114547',32,8,'xmm0',71)
        copy('0f294d37',16,16,'xmm1',55);copy('89454f',40,4,'rax',79)
    else:
        g.take('0f10442420','8b442440','4533c0','0f104c2430','488d542450','488bce')
        copy('0f29442450',0,16,'xmm0',80);copy('0f294c2460',16,16,'xmm1',96)
        copy('89442470',32,4,'rax',112)
    setter_at=g.at;g.call(setter_target)
    covered=sorted(i for item in copies for i in range(item['sourceOffset'],item['sourceOffset']+item['bytes']))
    need('all-and-only-own-argument-source-bits',covered==list(range(width)))
    return dict(typeName=type_name,managedBytes=width,selectedBytes=g.seen,
        actualContextLoadInstructionVa=context_at,actualContextCellVa=context_cell,contextRegister='r8',
        actualSourceInstructionVa=source_at,actualSourceTargetVa=source_target,
        actualSetterInstructionVa=setter_at,actualSetterTargetVa=setter_target,
        actualReaderRegister='rdi',wrapperRegister='rsi',outputRegister='rbx',
        hiddenSourceLocal=dict(baseRegister='rbp'if trigger else'rsp',displacement=-9 if trigger else 32,
            rspDisplacement=64 if trigger else 32,bytes=width),
        argumentLocal=dict(baseRegister='rbp'if trigger else'rsp',displacement=39 if trigger else 80,
            rspDisplacement=112 if trigger else 80,bytes=width),
        sourceLocalCopies=copies,ownedNullExit=null,completeArgumentBitsCopiedUnchanged=True,
        rawBooleanOrEnumBitsPreserved=True,namedSetterSemanticsProved=False,nominalRawSourceProved=False,
        completeCallerFrameProved=False,parentFieldAdmitted=False,childGrammarAdmitted=False)
