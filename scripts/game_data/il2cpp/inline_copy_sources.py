"""Symbolic pointer/byte proof for current even-length inlined char copies."""
import copy,re
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.byte_copy_programs import prove_byte_copy_moves
from scripts.game_data.il2cpp.memory_moves import decode_memory_move


def prove_inline_copy(rows,entry,finish,*,source,copy_target,spill=None,count_register="r8",stack_release=None,destination_register="rcx"):
 if count_register not in ('r8','r9')or destination_register not in ('rcx','r9')or len({source,count_register,destination_register})!=3 or stack_release not in (None,40):raise ValueError('inlineCopy.selected-ABI')
 by={int(r['va'],16):r for r in rows};cases=[];seen=set()
 aliases={r:n for n,rr in {'rax':('rax','eax','ax','al'),'rbx':('rbx','ebx','bx','bl'),'rcx':('rcx','ecx','cx','cl'),'rdx':('rdx','edx','dx','dl'),'rsi':('rsi','esi','si','sil'),'rdi':('rdi','edi','di','dil')}.items()for r in rr}
 aliases.update(rsp='rsp',esp='rsp')
 for n in range(8,16):
  for suffix in ('','d','w','b'):aliases['r'+str(n)+suffix]='r'+str(n)
 def bits(r):return 32 if r.startswith('e') or re.fullmatch(r'r\d+d',r) else 8 if r in ('al','bl','cl','dl','sil','dil') or r.endswith('b') else 16 if r in ('ax','bx','cx','dx','si','di') or r.endswith('w') else 64
 def affine(x):return x if isinstance(x,tuple) and len(x)==3 else (0,0,x) if type(x)is int else None
 def arithmetic(a,b,subtract=False):
  a,b=affine(a),affine(b)
  if a is None or b is None:raise ValueError('inlineCopy.unproved-affine-operation')
  r=tuple(x+(-y if subtract else y)for x,y in zip(a,b));return r[2]if r[:2]==(0,0)else r
 def mul(a,n):return tuple(x*n for x in a)if isinstance(a,tuple)else a*n
 for count in range(0,257,2):
  for sr in (0,2):
   for dr in (0,2):
    originals={r:('incoming-register',r)for r in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15')}if stack_release is not None else {}
    state={**originals,source:(1,0,0),destination_register:(0,1,0),count_register:count,**({'rsp':0}if stack_release is not None else {})};stack={};ops=[];flags=None;pc=entry;steps=0;large=False
    def low(v):
     if type(v)is int:return v&3
     if isinstance(v,tuple)and len(v)==3:return (v[0]*sr+v[1]*dr+v[2])&3
     if isinstance(v,dict)and 'low' in v:return v['low']
     raise ValueError('inlineCopy.unknown-low-bits')
    def read(r):
     if r not in aliases:
      try:return int(r,0)
      except ValueError:raise ValueError('inlineCopy.operand:'+r)
     v=state.get(aliases[r]);n=bits(r)
     if v is None:raise ValueError('inlineCopy.uninitialized-register:'+r)
     if type(v)is int:return v&((1<<n)-1)
     return v if n==64 else dict(low=low(v))
    def put(r,v):state[aliases[r]]=v&((1<<bits(r))-1)if type(v)is int else v
    def flag(a,b,n,op='sub'):
     if type(a)is not int or type(b)is not int:return None
     mask=(1<<n)-1;a&=mask;b&=mask;value=(a-b if op=='sub' else a+b)&mask;sign=1<<(n-1)
     return dict(z=value==0,s=bool(value&sign),c=a<b if op=='sub'else a+b>mask,o=bool(((a^b)&(a^value)if op=='sub'else ~(a^b)&(a^value))&sign))
    def address(a):
     value=a.get('displacement',0)
     for key,scale in (('base',1),('index',a.get('scale',1))):
      if a.get(key):value=arithmetic(value,mul(read(a[key]),scale))
     return affine(value)
    while pc!=finish:
     steps+=1
     if steps>1000 or pc not in by:raise ValueError('inlineCopy.selected-control-bound')
     row=by[pc];raw=bytes.fromhex(row['bytes']);nxt=pc+len(raw);seen.update(range(pc,nxt));text=row['text'];op,_,args=text.partition(' ');args=[a.strip()for a in args.split(',')]
     memory=decode_memory_move(raw,0,pc)
     if memory is not None and memory[1]==len(raw):row={**row,**memory[0]}
     transfer=control_transfer(row)
     if transfer['kind']=='conditional':
      if flags is None:raise ValueError('inlineCopy.unknown-branch-flags')
      cc=(raw[0]&15)if len(raw)==2 else raw[1]&15;z,s,c,o=(flags[k]for k in ('z','s','c','o'))
      predicates={2:c,3:not c,4:z,5:not z,6:c or z,7:not c and not z,12:s!=o,13:s==o,14:z or s!=o,15:not z and s==o}
      if cc not in predicates:raise ValueError('inlineCopy.unproved-branch-predicate')
      nxt=transfer['target']if predicates[cc]else nxt
     elif transfer['kind']=='jump':
      nxt=transfer['target']
      if nxt==copy_target and stack_release is not None:
       if not 32<count<=256 or read('rcx')!=(0,1,0)or read('rdx')!=(1,0,0)or read('r8')!=count or read('rsp')!=stack_release:raise ValueError('inlineCopy.large-tail-ABI')
       large=True;nxt=finish
     elif transfer['kind']=='call':
      if transfer['target']!=copy_target or not 32<count<=256 or read('rcx')!=(0,1,0)or read('rdx')!=(1,0,0)or read('r8')!=count:raise ValueError('inlineCopy.large-copy-ABI')
      if nxt!=finish:raise ValueError('inlineCopy.copy-call-continuation')
      large=True
     elif row.get('memoryOperation'):
      f=row['memoryOperation'];a=f['address'];r=f['register'];width=f['memoryBytes']
      if f['direction']=='load'and spill and a.get('base')==spill[0]and a.get('index')is None and a['displacement']==spill[1]and width==4:put(r,dict(low=sr));pc=nxt;continue
      if stack_release is not None and a.get('base')=='rsp'and a.get('index')is None:
       at=read('rsp')+a['displacement']
       if at not in (32,48,56,64)or width!=8:raise ValueError('inlineCopy.unreviewed-frame-slot')
       if f['direction']=='store':stack[at]=read(r)
       elif at in stack:put(r,stack[at])
       else:raise ValueError('inlineCopy.uninitialized-frame-slot')
       pc=nxt;continue
      location=address(a);expected=(1,0)if f['direction']=='load'else(0,1)
      if location is None or location[:2]!=expected or not 0<=location[2]<=location[2]+width<=count:raise ValueError('inlineCopy.payload-range')
      normalized=copy.deepcopy(f);normalized['address']=dict(base='rdx'if f['direction']=='load'else'rcx',index=None,scale=1,displacement=location[2],ripRelative=False,addressBits=64);ops.append(normalized)
      if f['direction']=='load':state[f['backingRegister']]={'payload':True}
     elif row.get('addressOperation'):
      a=row['addressOperation'];value=address(dict(base=a.get('base'),index=a.get('index'),scale=a.get('scale',1),displacement=a.get('displacement',0)))
      if value is None:raise ValueError('inlineCopy.lea-value')
      put(a['destination'],value[2]if value[:2]==(0,0)else value)
     elif op in ('mov','movsxd','movzx'):put(args[0],read(args[1]))
     elif op in ('cmp','test','and','or','add','sub','shr','shl','neg','inc','dec'):
      a=read(args[0]);b=read(args[1])if len(args)>1 else 1;n=bits(args[0])
      if op in ('test','and','or'):
       if type(a)is int and type(b)is int:value=a&b if op in ('test','and')else a|b
       elif op=='test'and type(b)is int and not b&~3:value=low(a)&b
       else:value=dict(low=(low(a)&low(b))if op=='and'else(low(a)|low(b)))
       flags=dict(z=value==0,s=bool(value&(1<<(n-1))),c=False,o=False)if type(value)is int else None
      elif op in ('cmp','sub','add','inc','dec','neg'):
       left,right=(0,a)if op=='neg'else(a,b);subtract=op in ('cmp','sub','dec','neg');value=arithmetic(left,right,subtract);flags=flag(left,right,n,'sub'if subtract else'add')
      else:
       if type(a)is not int or type(b)is not int:raise ValueError('inlineCopy.unproved-shift')
       value=a>>b if op=='shr'else a<<b;flags=None
      if op not in ('cmp','test'):put(args[0],value)
     elif op=='ret'and stack_release is not None:
      if read('rsp')!=stack_release:raise ValueError('inlineCopy.return-stack-balance')
      nxt=finish
     elif op!='nop':raise ValueError('inlineCopy.unreviewed-instruction:'+text)
     pc=nxt
    if stack_release is not None and any(state.get(r)!=v for r,v in originals.items()):raise ValueError('inlineCopy.nonvolatile-register-restore')
    if not large:prove_byte_copy_moves(ops,length=count,pointers={'rdx':'source','rcx':'destination'},overlap='forward-safe',label='inlineCopy.bytes')
    cases.append(dict(bytes=count,sourceMod4=sr,destinationMod4=dr,largeCopy=large))
 return dict(destinationRegister=destination_register,countRegister=count_register,stackRelease=stack_release,maxBytes=256,evenCounts=129,completeCases=len(cases),reviewedByteCount=len(seen),allSmallStoresEqualInitialSource=True,largeCopyTarget=copy_target,largeCopyCountBound=256,source=source,spill=spill,
  condition='Even counts0..256, stable char-aligned disjoint source/destination with nonwrapping endpoints. Scalar copy paths cover all mod4 residues using symbolic affine pointers and distinct source bytes; larger selected calls require the separately authenticated bounded-copy component. Optional spill carries the original source pointer, proved by caller. Selected whole-helper return mode separately proves exact stack release and all nonvolatile register restores; its large tail forwards the same RCX/RDX/R8 ABI. No overlap guards, surrounding builder fields or unrelated paths are admitted.')
