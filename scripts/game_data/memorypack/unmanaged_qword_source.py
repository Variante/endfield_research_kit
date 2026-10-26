"""Selected buffered reads across one authenticated owned unwind family."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def advance(regions,entry,offsets,*,zero=False):
 g=BytesPath(regions,entry);g.take('85d2');g.branch('74',zero,1)
 if not zero:
  g.take('48895c2410','57','4883ec20','4863fa','488bd9','4889742430','8b71'+bytes((offsets['bufferLength'],)).hex(),'2bf7');g.branch('0f88',False)
  g.take('48017b'+bytes((offsets['currentPtr'],)).hex(),'017b'+bytes((offsets['advancedCount'],)).hex(),'017b'+bytes((offsets['consumed'],)).hex(),'8973'+bytes((offsets['bufferLength'],)).hex(),'488b742430','488b5c2438','4883c420','5f')
 g.take('c3');return dict(selectedBytes=g.seen,zero=zero,entryRspRestored=True,preserves=['rbx','rdi','rsi'],effect='No state change' if zero else 'currentPtr += sign-extended EDX; advancedCount and consumed add EDX; bufferLength subtracts EDX',condition='EDX zero, or positive count with sufficient nonnegative signed32 buffer length and valid disjoint reader/span; refill branch excluded.')

def uint64(regions,entry,offsets,advance_target):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','8379'+bytes((offsets['bufferLength'],8)).hex(),'488bf9');g.branch('0f8c',False);g.take('488b5f'+bytes((offsets['currentPtr'],)).hex(),'ba08000000','488bcf','488b1b');g.call(advance_target);g.take('488bc3','488b5c2430','4883c420','5f','c3');return dict(selectedBytes=g.seen,bytesRead=8,advanceArgument=8,entryRspRestored=True,condition='Sufficient eight-byte buffer, valid reader/current pointer and ordinary owned Advance with preserved nonvolatile registers; cold refill excluded.')


def validate(image,pointer,offsets):
 import json
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 record=vector_recorder(image);base=image.pe.image_base
 def owned(entry):
  ranges=image.unwind_index.family(entry-base)['ranges'];windows=[];regions=[]
  import hashlib
  for row in ranges:
   a,z=row['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);regions.append((base+a,raw));windows.append(dict(startRva=a,endRva=z,sha256=hashlib.sha256(raw).hexdigest().upper()))
  return regions,windows
 source=record(pointer-base,fragments=True);at,encoded=source['instructions'][10];raw=bytes.fromhex(encoded)
 if len(raw)!=5 or raw[0]!=0xe8:raise ValueError('unmanagedQword.advance-call-shape')
 target=base+at+5+int.from_bytes(raw[1:],'little',signed=True)
 regions,windows=owned(pointer);advance_regions,advance_windows=owned(target)
 return json.loads(json.dumps(dict(sourceWindows=windows,advanceWindows=advance_windows,source=uint64(regions,pointer,offsets,target),advance=[advance(advance_regions,target,offsets,zero=z) for z in (True,False)])))
