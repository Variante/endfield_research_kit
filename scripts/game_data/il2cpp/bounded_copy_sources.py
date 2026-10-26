"""Exact current small/vector copy paths for every count 0..256; no larger copy."""
import copy
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.byte_copy_programs import prove_byte_copy_moves


def prove_bounded_copy(regions,entry,*,rows,tables,image_base):
 by_at={int(r['va'],16):r for r in rows};seen=set();cases=[];table_uses=set()
 def transfer_table(g,*,small,index):
  g.take('478b8c82' if small else '478b9c9a');rva=int.from_bytes(g.read(4),'little',signed=True)
  raw=tables.get(rva)
  if not isinstance(raw,bytes) or len(raw)!=(16 if small else 9)*4 or not 0<=index<len(raw)//4:raise ValueError('boundedCopy.table-domain')
  target=image_base+int.from_bytes(raw[index*4:index*4+4],'little');table_uses.add(rva)
  g.take('4d03ca' if small else '4d03da','41ffe1' if small else '41ffe3')
  if target not in by_at:raise ValueError('boundedCopy.table-instruction-boundary')
  g.at=target
 def move(g,operations,*,length,position=0,remaining=None,rounded=None,aligned=False,destination_residue=0):
  row=by_at.get(g.at,{});op=row.get('memoryOperation')
  if not op:raise ValueError('boundedCopy.selected-memory-move')
  raw=bytes.fromhex(row['bytes'])
  if g.read(len(raw))!=raw:raise ValueError('boundedCopy.original-move')
  op=copy.deepcopy(op);a=op['address'];base=a.get('base');index=a.get('index')
  if a.get('scale')!=1 or index not in (None,'r8','r9') or base not in ('rax','rcx','rdx'):raise ValueError('boundedCopy.payload-address')
  a['displacement']+=(0 if base=='rax' else position)+(remaining if index=='r8' else rounded if index=='r9' else 0)
  a['index']=None
  if op['requiredAlignmentBytes']!=1:
   if not aligned or op['direction']!='store' or op['requiredAlignmentBytes']!=16 or (a['displacement']+destination_residue)%16:raise ValueError('boundedCopy.aligned-store')
   op['requiredAlignmentBytes']=1
  operations.append(op)
 def payload(g,operations,**kw):
  while True:
   row=by_at.get(g.at,{})
   if row.get('text')=='ret':g.take('c3');return
   if row.get('text')=='vzeroupper':g.take('c5f877','c3');return
   move(g,operations,**kw)
 for length in range(257):
  for mode in ((False,True) if length>32 else (False,)):
   for residue in (range(16) if mode and length>128 else (0,)):
    g=BytesPath(regions,entry);operations=[];position=0;remaining=length
    g.take('488bc1')
    if g.relative('4c8d15')!=image_base:raise ValueError('boundedCopy.image-base')
    g.take('4983f80f');g.branch('0f87',length>15)
    if length<=15:
     g.take('666666660f1f840000000000');transfer_table(g,small=True,index=length);payload(g,operations,length=length)
    else:
     g.take('4983f820');g.branch('77',length>32,1)
     if length<=32:payload(g,operations,length=length,remaining=length)
     else:
      g.take('4e8d0c02','483bca','4c0f46c9','493bc9');g.branch('0f82',False)
      mode_cell=g.relative('833d');g.take('03');g.branch('0f82',mode)
      g.take('4981f800080000' if mode else '4981f800200000');g.branch('76',True,1)
      width,limit=(16,128) if mode else (32,256)
      move(g,operations,length=length,remaining=length);move(g,operations,length=length,remaining=length)
      g.take('4981f880000000' if mode else '4981f800010000');g.branch('0f86',length<=limit)
      if length>limit:
       # Only the SSE lane aligns/loops within this explicit count bound.
       if not mode:raise ValueError('boundedCopy.unproved-large-AVX')
       advance=16-residue;position=advance;remaining=length-advance
       g.take('4c8bc9','4983e10f','4983e910','492bc9','492bd1','4d03c1','4981f880000000');g.branch('76',remaining<=128,1)
       if remaining>128:
        g.take('0f1f440000')
        while True:
         for _ in range(16):move(g,operations,length=length,position=position,aligned=True,destination_residue=residue)
         position+=128;remaining-=128
         g.take('4881c180000000','4881c280000000','4981e880000000','4981f880000000');g.branch('73',remaining>=128,1)
         if remaining<128:break
      rounded=(remaining+width-1)&-width
      g.take('4d8d480f' if mode else '4d8d481f','4983e1f0' if mode else '4983e1e0','4d8bd9','49c1eb04' if mode else '49c1eb05')
      transfer_table(g,small=False,index=rounded//width)
      payload(g,operations,length=length,position=position,remaining=remaining,rounded=rounded)
    proof=prove_byte_copy_moves(operations,length=length,pointers={'rdx':'source','rcx':'destination','rax':'destination'},overlap='forward-safe',label='boundedCopy.bytes')
    seen.update(at+i for at,raw in g.seen for i in range(len(bytes.fromhex(raw))))
    cases.append(dict(length=length,lowMode=mode,residue=residue,loads=proof['loads'],stores=proof['stores']))
 return dict(maxBytes=256,completeIntegerCounts=257,completeCases=len(cases),tableRvas=sorted(table_uses),reviewedByteCount=len(seen),allSelectedBytesEqualInitialSource=True,allSelectedPayloadRangesInBounds=True,returnsOriginalDestination=True,proofs=cases,
  condition='Counts 0..256 only; valid stable ordinary nonwrapping source/destination disjoint from the call frame, forward-safe overlap, supported CPU state for selected native mode. Both mode classes and every relevant destination alignment residue are covered; no runtime mode value, backward overlap, larger count, REP or non-temporal path is admitted.')
