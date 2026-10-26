"""Exact cached wrapper constructor with independently proved scalar defaults."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle

def need(key,condition,detail=None):
 if not condition:raise ValueError('generatedScalarFactory.'+key+':'+str(detail)[:700])

def constructor_program(regions,entry,barrier,*,base_slot,cache_slot,initializers):
 need('owned-initializers-required',type(initializers)is list and 0<=len(initializers)<=32)
 need('finite-holder-slots',16<=base_slot<cache_slot<128)
 expected={}
 for store in initializers:
  width,offset=store['bytes'],store['offset'];need('finite-constant-field',width in(1,2,4)and 16<=offset<2**31)
  raw=('66'if width==2 else'')+('c6'if width==1 else'c7')+('40'if offset<128 else'80')+offset.to_bytes(1 if offset<128 else 4,'little',signed=True).hex()+store['constantHex'].lower()
  need('distinct-current-initializer',raw not in expected);expected[raw]=store
 g=BytesPath(regions,entry);rbx=lifecycle._peek(g,2)==bytes.fromhex('4053')
 g.take('4053'if rbx else'4057'if lifecycle._peek(g,2)==b'\x40\x57'else'57','4883ec20');flag=lifecycle._direct_flag(g,'803d');g.take('488bd9'if rbx else'488bf9');lifecycle._initialized(g)
 site=g.at;cell=g.relative('488b0d');ancestor=dict(site=site,cell=cell);g.take('83b9e000000000');lifecycle._initialized(g)
 site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocate=g.relative('e8');g.take('4c8bc8','4885c0');lifecycle._nonnull(g)
 b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();arguments={('488d4b'if rbx else'488d4f')+c,('488943'if rbx else'488947')+c,'48897c2430'if rbx else'48895c2430'}
 while arguments or expected:
  matches=[h for h in list(arguments)+list(expected)if all(g.bytes.get(g.at+i)==v for i,v in enumerate(bytes.fromhex(h)))]
  need('every-initializer-and-holder-instruction',len(matches)==1,(hex(g.at),list(arguments),list(expected)))
  raw=matches[0];g.take(raw)
  if raw in arguments:arguments.remove(raw)
  else:del expected[raw]
 g.call(barrier);g.take(('488d4b'if rbx else'488d4f')+b,('4c894b'if rbx else'4c894f')+b);g.call(barrier);g.take(('488b7b'if rbx else'488b5f')+b);usages=[];casts=[]
 for i in range(2):
  site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell))
  if i==0:g.take('488bcf'if rbx else'488bcb')
  casts.append(g.relative('e8'))
  if i==0:g.take(('488943'if rbx else'488947')+c,'488bcf'if rbx else'488bcb')
 need('same-typed-allocation-and-cast',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in usages))
 g.take(('488d4b'if rbx else'488d4f')+c,'488b7c2430'if rbx else'488b5c2430','4883c420','5b'if rbx else'5f');need('same-final-barrier',g.relative('e9')==barrier)
 result=dict(selectedBytes=g.seen,initializedFlag=flag,constructor=True,allocation=allocation,allocationTarget=allocate,baseClassUsage=ancestor,baseReady=None,
  instanceSetter=None,inlineHolderWrites=[dict(offset=o,bytes=8,sameAllocatedReference=True)for o in(cache_slot,base_slot)],
  strictCast=casts[0],classUsages=usages,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
  originalConstructorCalled=False,originalConstructorTarget=None,originalConstructorEffectsProved=False,inlinedOriginalInitializers=initializers,
  normalReturnViaBarrier=True,condition='Fresh original leaf constants and exact current typed allocation; both whole holders receive the same allocation, actual compatible casts and disabled reference barriers; complete ordinary stack/nonvolatile frame.')
 if rbx:result['wrapperRegister']='rbx'
 return result

def register_defaults_program(regions,entry,barrier,*,base_slot,cache_slot,initializers):
 """Exact EBX/ECX DWORD defaults, holder setter, two casts and full tail."""
 need('owned-register-defaults',isinstance(initializers,list)and 0<len(initializers)<=32 and 16<=base_slot<cache_slot<128)
 expected={s['offset']:s['constantHex'].upper()for s in initializers}
 need('distinct-independent-DWORD-defaults',len(expected)==len(initializers)and all(s['bytes']==4 and 16<=s['offset']<2**31 for s in initializers))
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag=lifecycle._direct_flag(g,'803d');g.take('488bf9','bb');ebx=g.read(4)
 lifecycle._initialized(g);site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocate=g.relative('e8');g.take('4885c0');lifecycle._nonnull(g)
 ecx=None;arguments=set();stores=[];steps=0
 while expected or arguments!={'rdx','rcx','r8'}:
  steps+=1;need('bounded-default-register-program',steps<=48)
  prefix=bytes(g.bytes.get(g.at+i,0)for i in range(3));at=g.at
  if prefix[:1]==b'\xb9':g.take('b9');ecx=g.read(4);arguments.discard('rcx');continue
  if prefix==bytes.fromhex('4533c0'):g.take('4533c0');need('one-zero-MethodInfo', 'r8'not in arguments);arguments.add('r8');continue
  if prefix==bytes.fromhex('488bd0'):g.take('488bd0');need('one-whole-allocation-argument','rdx'not in arguments);arguments.add('rdx');continue
  if prefix==bytes.fromhex('488bcf'):g.take('488bcf');need('one-wrapper-receiver','rcx'not in arguments);arguments.add('rcx');ecx=None;continue
  if prefix[:1]==b'\x89'and prefix[1]in(0x48,0x58,0x88,0x98):
   modrm=prefix[1];g.take('89'+format(modrm,'02x'));offset=int.from_bytes(g.read(1 if modrm<128 else 4),'little',signed=True)
   value=ebx if(modrm>>3)&7==3 else ecx;need('known-whole-constant-register',value is not None)
  elif prefix[:2]in(bytes.fromhex('c740'),bytes.fromhex('c780')):
   modrm=prefix[1];g.take('c7'+format(modrm,'02x'));offset=int.from_bytes(g.read(1 if modrm==0x40 else 4),'little',signed=True);value=g.read(4)
  else:raise ValueError('generatedScalarFactory.unowned-register-default-instruction:'+str((hex(at),prefix.hex())))
  need('same-current-Original-DWORD-default',offset in expected and value.hex().upper()==expected[offset],(offset,value.hex(),expected))
  stores.append(dict(instructionVa=at,offset=offset,bytes=4,constantHex=value.hex().upper()));del expected[offset]
 setter=g.relative('e8');b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g.take('488b5f'+b);usages=[];casts=[]
 for i in range(2):
  site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell))
  if i==0:g.take('488bcb')
  casts.append(g.relative('e8'))
  if i==0:g.take('488947'+c,'488bcb')
 need('same-current-typed-cast-twice',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in usages))
 g.take('488d4f'+c,'488b5c2430','4883c420','5f');need('same-restored-tail-barrier',g.relative('e9')==barrier)
 return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=False,allocation=allocation,allocationTarget=allocate,baseClassUsage=None,baseReady=None,
  instanceSetter=setter,inlineHolderWrites=None,strictCast=casts[0],classUsages=usages,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
  originalConstructorCalled=False,originalConstructorTarget=None,originalConstructorEffectsProved=False,inlinedOriginalInitializers=initializers,
  registerDefaultStores=stores,normalReturnViaBarrier=True,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],
  condition='Initialized metadata and exact fresh typed zeroed Original allocation. Every literal EBX/ECX/immediate DWORD store matches an independently current Original constructor field default; whole allocation/zero MethodInfo/actual holder setter, same nominal compatible casts twice and complete restored Win64 tail. No constructor invocation or serialized framing is inferred.')
