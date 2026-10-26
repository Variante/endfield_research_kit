"""Selected current outer Param<EntityPtr> buffered read/store and allocation paths."""
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.memorypack.null_param import exact
from scripts.game_data.il2cpp.initializer_control import control_transfer

def path(rows,pointer,slots,symbols,*,allocated=False,null=False):
 if set(slots)!={'constValue','idRef','paramSource','path'} or any(type(v) is not int or not 16<=v<80 for v in slots.values()):raise ValueError('entityParam.owned-slots')
 g=_Path(rows);g.at=pointer;calls={};stores={}
 def take(*pairs):
  for text,raw in pairs:exact(g,text,raw)
 def call(name):
  row=g.rows[g.at];g.call(symbols[name]);calls[name]=row
 def nonnull(reg):g.take('test '+reg+', '+reg);g.branch(4,False)
 g.take('mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','push rdi','sub rsp, 0x50');r=g.row();raw=bytes.fromhex(r['bytes'])
 if len(raw)!=7 or raw[:2]!=b'\x80\x3d' or raw[-1]!=0:raise ValueError('entityParam.initialized-flag')
 g.take('mov rdi, rdx','mov rbx, rcx');g.branch(4,False);take(('cmp [rbx+0x30], 0x1','837b3001'));g.branch(12,False);g.take('mov rax, [rbx+0x50]');take(('movzx esi, [rax]','0fb630'));g.take('mov ebp, [rbx+0x30]','sub ebp, 0x1');g.branch(8,False)
 take(('inc [rbx+0x50]','48ff4350'),('inc [rbx+0x40]','ff4340'),('inc [rbx+0x44]','ff4344'),('mov [rbx+0x30], ebp','896b30'),('cmp sil, -0x1','4080feff'));g.branch(4,null);allocation=None;context=None
 if null:take(('mov [rdi], 0x0','48c70700000000'));g.take('mov rcx, rdi');g.jump()
 else:
  take(('cmp [rdi], 0x0','48833f00'));g.branch(4,allocated)
  if allocated:
   allocation=g.row();raw=bytes.fromhex(allocation['bytes'])
   if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x0d':raise ValueError('entityParam.allocation-class')
   call('allocateWrapper');g.take('mov rbp, rax');nonnull('rax');g.take('xor edx, edx','mov rcx, rax');call('constructor');g.take('mov rcx, rdi');take(('mov [rdi], rbp','48892f'));call('barrier');g.take('nop');g.jump()
  take(('cmp sil, 0x4','4080fe04'));g.branch(5,False);context=g.row();raw=bytes.fromhex(context['bytes'])
  if len(raw)!=7 or raw[:3]!=b'\x4c\x8b\x05':raise ValueError('entityParam.value-context')
  g.take('lea rcx, [rsp+0x20]','mov rsi, [rdi]','mov rdx, rbx');call('value');nonnull('rsi');g.take('mov rcx, [rsi+0x10]');nonnull('rcx')
  slots_hex=lambda name:bytes((slots[name],)).hex();c=slots['constValue'];stores['constValue']=g.at
  take(('movups xmm0, [rsp+0x20]','0f10442420'),('movups xmm1, [rsp+0x30]','0f104c2430'),(f'movups [rcx+{c:#x}], xmm0','0f1141'+bytes((c,)).hex()),('movsd xmm0, [rsp+0x40]','f20f10442440'),(f'movups [rcx+{c+16:#x}], xmm1','0f1149'+bytes((c+16,)).hex()),(f'movsd [rcx+{c+32:#x}], xmm0','f20f1141'+bytes((c+32,)).hex()),(f'add rcx, {c+24:#x}','4883c1'+bytes((c+24,)).hex()));call('barrier')
  g.take('mov rsi, [rdi]','mov rcx, rbx');call('idRef');nonnull('rsi');g.take('mov rcx, [rsi+0x10]');nonnull('rcx');stores['idRef']=g.at;take((f'mov [rcx+{slots["idRef"]:#x}], eax','8941'+slots_hex('idRef')))
  g.take('mov rcx, rbx','mov rsi, [rdi]');call('paramSource');nonnull('rsi');g.take('mov rcx, [rsi+0x10]');nonnull('rcx');stores['paramSource']=g.at;take((f'mov [rcx+{slots["paramSource"]:#x}], eax','8941'+slots_hex('paramSource')))
  g.take('mov rcx, rbx','mov rdi, [rdi]');call('path');nonnull('rdi');g.take('mov rcx, [rdi+0x10]');nonnull('rcx');stores['path']=g.at;take((f'mov [rcx+{slots["path"]:#x}], rax','488941'+slots_hex('path')),(f'add rcx, {slots["path"]:#x}','4883c1'+slots_hex('path')))
 g.take('mov rbx, [rsp+0x60]','mov rbp, [rsp+0x68]','mov rsi, [rsp+0x70]','add rsp, 0x50','pop rdi');tail=g.row();flow=control_transfer(tail)
 if flow['kind']!='jump' or flow['target']!=symbols['barrier']:raise ValueError('entityParam.barrier-tail')
 return dict(selectedInstructions=g.seen,calls=calls,stores=stores,allocation=allocation,valueContext=context,outerNull=null,allocated=allocated,outerBytes=1 if null else 13,nestedValueBytes='separate selected EntityPtr source',boundary='Initialized contiguous header path, normal ABI-preserving callees and valid disjoint storage; exact outer count, value hidden40 alias/store, Int32 bindings and pooled path call. Nested value/default/formatter/provider, cold refill and owner admission remain separate.')
