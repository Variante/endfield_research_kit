"""Selected initialized EntityPtr wrapper MC3 source and named member stores."""
from scripts.game_data.memorypack import scalar_param_native as s
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.il2cpp.initializer_control import control_transfer


def exact(g,text,encoded):
 row=g.row();s.need('entityLeaf',text,(text,bytes.fromhex(encoded)),(row['text'],bytes.fromhex(row['bytes'])));return row


def path(rows,pointer,offsets,symbols,*,allocated=False):
 g=_Path(rows);g.at=pointer;g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','push rdi','sub rsp, 0x20');flag=g.row();raw=bytes.fromhex(flag['bytes']);s.need('entityLeaf','initializedFlag',(7,b'\x80\x3d',0),(len(raw),raw[:2],raw[-1]));g.take('mov rdi, rdx','mov rbx, rcx');g.branch(4,False)
 cur,rem,adv,used=(offsets[k] for k in ('currentPtr','bufferLength','advancedCount','consumed'));exact(g,f'cmp [rbx+{rem:#x}], 0x1','837b'+bytes((rem,1)).hex());g.branch(12,False);g.take(f'mov rax, [rbx+{cur:#x}]');exact(g,'movzx esi, [rax]','0fb630');g.take(f'mov ebp, [rbx+{rem:#x}]','sub ebp, 0x1');g.branch(8,False)
 for offset,prefix in ((cur,'48ff43'),(adv,'ff43'),(used,'ff43')):exact(g,f'inc [rbx+{offset:#x}]',prefix+bytes((offset,)).hex())
 g.take(f'mov [rbx+{rem:#x}], ebp');exact(g,'cmp sil, -0x1','4080feff');g.branch(4,False);exact(g,'cmp [rdi], 0x0','48833f00');g.branch(4,allocated);allocation=None
 if allocated:
  load=g.row();raw=bytes.fromhex(load['bytes']);s.need('entityLeaf','allocationClassLoad',(7,b'\x48\x8b\x0d'),(len(raw),raw[:3]));g.call(symbols['allocation']);g.take('test rax, rax');g.branch(4,False);g.take('xor ecx, ecx','xorps xmm0, xmm0')
  for text,raw in [('movups [rax+0x10], xmm0','0f114010'),('movups [rax+0x20], xmm0','0f114020'),('mov [rax+0x30], rcx','48894830')]:exact(g,text,raw)
  g.take('mov rcx, rdi');exact(g,'mov [rdi], rax','488907');g.call(symbols['barrier']);g.take('nop');g.jump();allocation=dict(classLoad=load,zeroedManagedPayloadBytes=40)
 exact(g,'cmp sil, 0x3','4080fe03');g.branch(5,False);g.take('mov rsi, [rdi]','mov rcx, rbx');g.call(symbols['uint64']);g.take('test rsi, rsi');g.branch(4,False);exact(g,'mov [rsi+0x18], rax','48894618')
 g.take('mov rcx, rbx','mov rsi, [rdi]');g.call(symbols['uint32']);g.take('test rsi, rsi');g.branch(4,False);exact(g,'mov [rsi+0x20], eax','894620')
 g.take('mov rcx, rbx','mov rdi, [rdi]');g.call(symbols['boolean']);g.take('test rdi, rdi');g.branch(4,False);exact(g,'mov [rdi+0x10], al','884710');g.take('mov rbx, [rsp+0x30]','mov rbp, [rsp+0x38]','mov rsi, [rsp+0x40]','add rsp, 0x20','pop rdi','ret')
 return dict(memberCount=3,wireBytes=14,storedMembers=[['logicId',8,24],['slotId',4,32],['useSlotId',1,16]],selectedInstructions=g.seen,allocation=allocation,condition='Initialized metadata, at least fourteen contiguous input bytes, valid disjoint buffer/reader/wrapper/output/frame, nonoverflowing counters and ordinary nonnull typed allocation/barrier. Positive MC3 wrapper source only; generic adapter and owning Param remain separate.')
