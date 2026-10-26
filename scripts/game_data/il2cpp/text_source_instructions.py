"""Optional WORD immediate comparison and register-source subtraction facts."""
from scripts.game_data.il2cpp.integer_addressing import _address,_prefix,_required
from scripts.game_data.il2cpp.integer_tag_dispatch import _row,_memory_text
from scripts.game_data.il2cpp.memory_moves import _register


def decode_text_instruction(data,offset,start_va):
 if not 0<=offset<len(data):return None
 word=data[offset]==0x66
 at,rex=_prefix(data,offset+int(word))
 opcode=data[at] if at<len(data) else -1
 if word and opcode==0x83 and not rex&12:
  at+=1;modrm=_required(data,at,1,offset,'word-compare')[0];at+=1
  if (modrm>>3)&7!=7:return None
  if modrm>>6==3:operand=_register((modrm&7)+(8 if rex&1 else 0),16,bool(rex))[0];address=None
  else:address,at=_address(data,at,modrm,rex,offset,'word-compare');operand=_memory_text(address,at+1,start_va,16)
  immediate=int.from_bytes(_required(data,at,1,offset,'word-compare'),'little',signed=True);at+=1
  return _row(data,offset,at,start_va,f'cmp {operand}, {hex(immediate) if immediate>=0 else "-"+hex(-immediate)}',wordImmediateComparison=dict(bits=16,sourceAddress=address,encodedImmediateBits=8,immediate=immediate&65535,preservesRegisters=True,writesMemory=False,flags='16-bit subtraction comparison flags'))
 if not word and opcode==0x2b:
  at+=1;modrm=_required(data,at,1,offset,'register-subtract')[0];at+=1
  if modrm>>6!=3:return None
  bits=64 if rex&8 else 32;left=_register(((modrm>>3)&7)+(8 if rex&4 else 0),bits,bool(rex))[0];right=_register((modrm&7)+(8 if rex&1 else 0),bits,bool(rex))[0]
  return _row(data,offset,at,start_va,f'sub {left}, {right}',registerSubtraction=dict(bits=bits,destination=left,source=right,zeroExtendsUpper32=bits==32,writesMemory=False,flags='CF/OF/SF/ZF/AF/PF from modular subtraction'))
 return None
