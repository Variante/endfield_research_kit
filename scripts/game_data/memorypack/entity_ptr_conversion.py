"""Complete initialized/cold adapter transfer program; concrete helper effects stay separate."""
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.zero_wrapper_programs import _exact
from scripts.game_data.il2cpp.initializer_control import control_transfer

def edge(g,cc,label):
 row=g.row();flow=control_transfer(row)
 if flow['kind']!='conditional' or flow['conditionCode']!=cc:g.fail('condition',cc,row)
 g.edges.append((flow['target'],label,row))

def rip(g,prefix):
 row=g.row();raw=bytes.fromhex(row['bytes'])
 if len(raw)!=7 or raw[:3]!=bytes.fromhex(prefix):g.fail('rip-operand',prefix,row)
 return int(row['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True)

def flag(g,store=False):
 row=g.row();raw=bytes.fromhex(row['bytes']);prefix=bytes.fromhex('c605' if store else '803d')
 if len(raw)!=7 or raw[:2]!=prefix or raw[-1]!=int(store):g.fail('initialized-flag',prefix,row)
 return int(row['va'],16)+7+int.from_bytes(raw[2:6],'little',signed=True)

def check(rows,s):
 g=ProgramGrammar(rows,label='entityDeserializeNotNull')
 def take(*pairs):
  for text,raw in pairs:_exact(g,text,raw)
 take(('mov [rsp+0x10], rbx','48895c2410'),('mov [rsp+0x20], rbp','48896c2420'),('mov [rsp+0x18], r8','4c89442418'),('push rdi','57'),('sub rsp, 0x50','4883ec50'));initialized=flag(g)
 take(('mov rbx, r9','498bd9'),('mov rbp, rdx','488bea'),('mov rdi, rcx','488bf9'));g.branch('je','metadataCold');g.mark('class');klass=rip(g,'488b0d');take(('cmp dword [rcx+0xe0], 0x0','83b9e000000000'));g.branch('je','classCold');g.mark('context')
 take(('mov rcx, [rbx+0x20]','488b4b20'));g.call(s['classContext']);take(('mov rcx, [rax+0xc0]','488b88c0000000'),('mov rcx, [rcx+0x20]','488b4920'));g.call(s['formatter']);take(('test rax, rax','4885c0'));g.branch('je','missingFormatter')
 take(('mov ecx, 0x5','b905000000'),('mov [rsp+0x60], rsi','4889742460'),('lea r9, [rsp+0x70]','4c8d4c2470'),('mov r8, rdi','4c8bc7'),('mov rdx, rax','488bd0'));g.call(s['slotDispatch']);take(('mov rsi, [rsp+0x70]','488b742470'),('test rsi, rsi','4885f6'));g.branch('je','nullWrapper')
 take(('mov rcx, [rbx+0x20]','488b4b20'));g.call(s['classContext']);take(('mov edx, 0x8','ba08000000'),('mov rcx, [rax+0xc0]','488b88c0000000'));g.call(s['interfaceContext'])
 take(('mov rdi, [rsi]','488b3e'),('mov rbx, rax','488bd8'),('mov rcx, rdi','488bcf'));g.call(s['classPrepare']);take(('movzx r8d, word [rdi+0x130]','440fb78730010000'),('xor ecx, ecx','33c9'),('cmp cx, r8w','66413bc8'));edge(g,3,'fallback')
 take(('mov rdx, [rdi+0xb0]','488b97b0000000'));g.mark('scan');take(('movzx eax, cx','0fb7c1'),('add rax, rax','4803c0'),('cmp qword [rdx+rax*8], rbx','48391cc2'));g.branch('je','matched');take(('inc cx','66ffc1'),('cmp cx, r8w','66413bc8'));edge(g,2,'scan')
 g.mark('fallback');take(('xor r8d, r8d','4533c0'),('mov rdx, rbx','488bd3'),('mov rcx, rsi','488bce'));g.call(s['interfaceFallback']);g.branch('jmp','getter')
 g.mark('matched');take(('mov rax, [rdi+0xb0]','488b87b0000000'),('movzx edx, cx','0fb7d1'),('add rdx, rdx','4803d2'),('movsxd rax, dword [rax+rdx*8+0x8]','486344d008'),('add rax, 0x14','4883c014'),('shl rax, 0x4','48c1e004'),('add rax, rdi','4803c7'))
 g.mark('getter');take(('mov r9, [rax]','4c8b08'),('lea rcx, [rsp+0x20]','488d4c2420'),('mov r8, [rax+0x8]','4c8b4008'),('mov rdx, rsi','488bd6'),('call r9','41ffd1'),('lea rcx, [rbp+0x18]','488d4d18'),('movups xmm1, [rax]','0f1008'),('movups xmm2, [rax+0x10]','0f105010'),('movsd xmm0, [rax+0x20]','f20f104020'),('movups [rbp], xmm1','0f114d00'),('movups [rbp+0x10], xmm2','0f115510'),('movsd [rbp+0x20], xmm0','f20f114520'));g.call(s['barrier'])
 g.mark('restore');take(('mov rsi, [rsp+0x60]','488b742460'),('mov rbx, [rsp+0x68]','488b5c2468'),('mov rbp, [rsp+0x78]','488b6c2478'),('add rsp, 0x50','4883c450'),('pop rdi','5f'),('ret','c3'));g.mark('metadataCold')
 if rip(g,'488d0d')!=klass:g.fail('class-cell',klass,'different')
 g.call(s['metadataInit'])
 if flag(g,True)!=initialized:g.fail('initialized-flag-cell',initialized,'different')
 g.branch('jmp','class');g.mark('classCold');g.call(s['classInit']);g.branch('jmp','context');g.mark('missingFormatter');g.call(s['throwMissing']);take(('int3','cc'));g.mark('nullWrapper');take(('xorps xmm0, xmm0','0f57c0'),('xor eax, eax','33c0'),('movups [rbp], xmm0','0f114500'),('movups [rbp+0x10], xmm0','0f114510'),('mov [rbp+0x20], rax','48894520'));g.branch('jmp','restore');g.finish()
 return dict(completeOwnedProgram=True,readerForwarding='Reader RCX -> RDI -> slot5 R8',wrapperStorage='entry R8 saved to caller home/local+0x70 and passed byref as slot5 R9',contextSlots=dict(formatter=4,wrapperInterface=8),interfaceLoop=dict(indexBits=16,entryBytes=16,signedOffsetBits=32,vtableBaseBytes=320,slotBytes=16),getterAbi='hidden40 stack+0x20, wrapper RDX, method R8; returned RAX supplies16+16+8 bytes to original output RBP',directReaderWrites=0,unresolved=['actual inflated class context and helper effects','concrete formatter/virtual receiver/slot bodies','runtime provider replacement','outer Param and owner composition'])
