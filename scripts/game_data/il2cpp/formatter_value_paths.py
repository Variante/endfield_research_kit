"""Byte-exact selected formatter transfers with explicit runtime conditions."""
class BytesPath:
 def __init__(self,regions,entry):self.bytes={p+i:b for p,raw in regions for i,b in enumerate(raw)};self.at=entry;self.seen=[]
 def read(self,n):
  try:r=bytes(self.bytes[self.at+i] for i in range(n))
  except KeyError as error:raise ValueError('dispatch.unowned-byte') from error
  self.seen.append((self.at,r.hex()));self.at+=n;return r
 def take(self,*hexes):
  for h in hexes:
   if self.read(len(bytes.fromhex(h)))!=bytes.fromhex(h):raise ValueError('dispatch.instruction:'+h)
 def relative(self,prefix,width=4):
  self.take(prefix);return self.at+width+int.from_bytes(self.read(width),'little',signed=True)
 def call(self,target):
  if self.relative('e8')!=target:raise ValueError('dispatch.call-target')
 def jump(self,prefix,width=4):self.at=self.relative(prefix,width)
 def branch(self,prefix,taken,width=4):
  target=self.relative(prefix,width)
  if target not in self.bytes:raise ValueError('dispatch.branch-outside-owned-bytes')
  if taken:self.at=target


def deserialize_slot(regions,entry,*,prepare,callback):
 g=BytesPath(regions,entry);g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec70','4d8be9','4d8bf8','488bfa','0fb7d9','488b0a');g.call(prepare)
 g.take('488d4b14','4803c9','488b07','4c8b14c8','488b5cc808','48899c24c0000000');excluded=[]
 for _ in range(3):
  fast=g.relative('488d05')
  if fast==callback:raise ValueError('dispatch.selected-target-enters-unproved-inline-body')
  excluded.append(fast);g.take('4c3bd0');g.branch('0f85',True)
 g.take('4c8bcb','4d8bc5','498bd7','488bcf','41ffd2','488b9c24b0000000','4883c470','415f','415e','415d','415c','5f','5e','5d','c3')
 return dict(selectedBytes=g.seen,excludedInlinedTargets=excluded,slotStride=16,vtableBase=320,callbackOffsetForSlotFive=400,methodInfoOffsetForSlotFive=408,callbackArguments=dict(rcx='incoming RDX receiver',rdx='incoming R8 reader',r8='incoming R9 output',r9='selected slot MethodInfo'),sameReaderAndOutput=True,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],condition='Incoming selector low16 is five; valid ready receiver/class with original selected slot callback and MethodInfo, normal preparation ABI, stable disjoint storage and nonthrowing callback. Runtime receiver/MethodInfo binding and inlined alternatives remain separate.')


