"""Selected initialized shared-adapter paths; callee/context joins stay explicit."""
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.memorypack.scalar_param_native import need


def raw(g,encoded):
 row=g.row();need('entityAdapter','operand-encoding',bytes.fromhex(encoded),bytes.fromhex(row['bytes']));return row


def rip(g,prefix):
 row=g.row();code=bytes.fromhex(row['bytes']);need('entityAdapter','rip-load',(7,bytes.fromhex(prefix)),(len(code),code[:3]));return int(row['va'],16)+7+int.from_bytes(code[3:],'little',signed=True)


def flag(g):
 row=g.row();code=bytes.fromhex(row['bytes']);need('entityAdapter','initialized-byte-flag',(7,b'\x80\x3d',0),(len(code),code[:2],code[-1]))


def adapter(rows,pointer,symbols,*,dispatch=False,null=False,skip_factory=False):
 g=_Path(rows);g.at=pointer
 if dispatch:
  g.take('mov [rsp+0x10], rbx','mov [rsp+0x18], rbp','mov [rsp+0x20], rsi');raw(g,'66894c2408');g.take('push rdi','sub rsp, 0x20','mov rcx, [rdx]','mov rbp, r9','mov rsi, r8','mov rbx, rdx');g.call(symbols['classPrepare']);g.take('mov rax, [rbx]');raw(g,'4c8b9090010000');raw(g,'488bb898010000');need('entityAdapter','actual-compared-entry',symbols['adapter'],rip(g,'488d05'));g.take('cmp r10, rax');g.branch(5,False)
 else:g.take('mov [rsp+0x18], rbp','mov [rsp+0x20], rsi','push rdi','sub rsp, 0x20');flag(g);g.take('mov rdi, r9','mov rbp, r8','mov rsi, rdx');g.branch(4,False)
 if dispatch:flag(g);g.branch(4,False)
 g.take('mov rcx, rsi');raw(g,'c64424'+('30' if dispatch else '38')+'00');g.call(symbols['peek']);g.take('test al, al');g.branch(5,null)
 if null:
  g.take('lea rdx, [rsp+'+('0x30' if dispatch else '0x38')+']','mov rcx, rsi');g.call(symbols['readNull']);g.take('xorps xmm0, xmm0','xor eax, eax');raw(g,'0f114500');raw(g,'0f114510');raw(g,'48894520');g.jump()
 else:
  if not dispatch:g.take('mov [rsp+0x30], rbx')
  g.take('mov rax, [rdi+0x20]');klass=rip(g,'488b0d');g.take('mov rbx, [rax+0xc0]');raw(g,'83b9e000000000');g.take('mov rbx, [rbx+0x50]');g.branch(4,False);g.take('xor edx, edx','mov rcx, rbx');g.call(symbols['typeFromHandle'])
  if not dispatch:g.take('mov rbx, [rsp+0x30]')
  g.take('test rax, rax');g.branch(4,False);g.take('mov ecx, 0x44','mov rdx, rax');g.call(symbols['typeFlags']);raw(g,'a980000000');g.branch(7,skip_factory)
  if skip_factory:g.take('xor eax, eax');g.jump()
  else:g.take('mov rax, [rdi+0x20]','mov rcx, [rax+0xc0]','mov rcx, [rcx+0x58]');g.call(symbols['factory'])
  g.take('mov rcx, [rdi+0x20]','mov r8, rax','mov rdx, rbp','mov r9, [rcx+0xc0]','mov rcx, rsi','mov r9, [r9+0x18]');g.call(symbols['notNull'])
 if dispatch:g.take('mov rbx, [rsp+0x38]')
 g.take('mov rbp, [rsp+0x40]','mov rsi, [rsp+0x48]','add rsp, 0x20','pop rdi','ret')
 return dict(profile='actual-slot-match' if dispatch else 'compared-shared-entry',null=null,skipFactory=skip_factory,zeroOutputBytes=40 if null else 0,directReaderWrites=0,selectedInstructions=g.seen,condition='Initialized class/metadata, normal ABI-preserving helpers, coherent closed MethodInfo, valid disjoint frame/reader/output and matched default adapter. Null uses the separately proved one-byte consume; positive forwards the unchanged reader/output and class-context slot3 method to DeserializeNotNull. Concrete inflater/provider/callee effects remain separate.')
