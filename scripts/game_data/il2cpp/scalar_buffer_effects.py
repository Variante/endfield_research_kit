"""Bounded relational effects for reviewed scalar arithmetic instruction rows.

This checks dependence and storage, not the numerical interpretation of trig.
Rows and their complete native byte ownership must be authenticated by callers.
"""
import copy,re
from collections import deque


def prove(rows,entry,*,inputs=(),buffers=None,calls=None,finite=False,required=(),constant_inputs=None):
 constant_inputs=constant_inputs or {};buffers=buffers or {};calls=calls or {};by={int(r['va'],16):r for r in rows};reads=set();writes=set();returns=[];excluded=[]
 if len(by)!=len(rows) or entry not in by:raise ValueError('scalar.partition')
 aliases={x:y for y,xx in {'rax':['eax','ax','al'],'rbx':['ebx','bx','bl'],'rcx':['ecx','cx','cl'],'rdx':['edx','dx','dl'],'rsi':['esi'],'rdi':['edi'],'rbp':['ebp']}.items() for x in xx}
 def reg(s):return aliases.get(s,re.sub(r'^(r(?:[89]|1[0-5]))[dbw]$',r'\1',s))
 def bits(s):return 8 if s in ('al','bl','cl','dl') or re.fullmatch(r'r\d+b',s) else 32 if s.startswith('e') or re.fullmatch(r'r\d+d',s) else 16 if s in ('ax','bx','cx','dx') else 64
 gs=['rax','rbx','rcx','rdx','rsi','rdi','rbp']+[f'r{n}' for n in range(8,16)]
 initial=dict(g={n:('in',n) for n in gs},x={f'xmm{n}':[('in',f'xmm{n}',i) for i in range(4)] for n in range(16)},m={},sp=0,f=False,eq=None,constants=dict(constant_inputs))
 for name,count in inputs:
  if name.startswith('xmm'):initial['x'][name][:count//32]=[True]*(count//32)
  else:initial['g'][reg(name)]=True
 if any(name not in dict(inputs) for name in constant_inputs):raise ValueError('scalar.constant-input-declaration')
 for name in buffers:initial['g'][name]=('ptr',name,0)
 def fail(row,what):raise ValueError('scalar.'+what+':'+row['va']+':'+row['mnemonic']+' '+row['operands'])
 def args(row):return [a.strip() for a in row['operands'].split(',')] if row['operands'] else []
 def clean(s):return re.sub(r'^(?:byte|word|dword|qword|xmmword) ptr ','',s)
 def size(s,default=8):return next((n for k,n in [('xmmword',16),('qword',8),('dword',4),('word',2),('byte',1)] if s.startswith(k+' ptr ')),default)
 def integer(s):
  try:return int(s,0)
  except ValueError:return None
 def ptr(s):return isinstance(s,tuple) and s[0]=='ptr'
 def address(state,row,operand,width,write=False):
  operand=clean(operand);terms=re.findall(r'[a-z][a-z0-9]*',operand)
  if not operand.startswith('[') or not operand.endswith(']'):fail(row,'memory-operand')
  if 'rip' in terms:
   if write:fail(row,'global-write')
   reads.add(('selected-global',row['va'],width));return None
  match=re.fullmatch(r'\[(\w+)(?: ([+-]) (0x[\da-f]+|\d+))?\]',operand)
  if match:
   name,sign,disp=match.groups();value=('ptr','stack',state['sp']) if name=='rsp' else state['g'].get(reg(name));offset=(-1 if sign=='-' else 1)*int(disp or '0',0)
   if ptr(value):
    base,at=value[1],value[2]+offset
    if at%4 or width%4:fail(row,'word-alignment')
    if base=='stack':
     if at<state['sp'] or at+width>32:fail(row,'frame-bounds')
    else:
     if at<0 or at+width>buffers[base]['write' if write else 'read']:fail(row,'argument-bounds')
     (writes if write else reads).add((base,at,width))
    return base,at
  names=[reg(s) for s in terms if reg(s) in state['g']]
  if not names or any(state['g'][n] is not True for n in names) or 'rsp' in terms:fail(row,'unproved-memory-address')
  if write:fail(row,'external-write')
  reads.add(('equal-global-address',row['va'],width));return None
 def get(state,row,s,width):
  if clean(s).startswith('['):
   location=address(state,row,s,width)
   if location is None:return [True]*(width//4)
   base,at=location;return [state['m'].get((base,at+i),True if base!='stack' else None) for i in range(0,width,4)]
  if s.startswith('xmm'):return state['x'][s][:width//4]
  if integer(s) is not None:return [True]*(width//4)
  value=('ptr','stack',state['sp']) if s=='rsp' else state['g'].get(reg(s));value=None if ptr(value) and (bits(s)!=64 or width!=8) else value;return [True if i*32<value[1] else None for i in range(width//4)] if isinstance(value,tuple) and value[0]=='low' else [value]*(width//4)
 def collapse(values):
  if all(v==values[0] for v in values):return values[0]
  count=next((i for i,v in enumerate(values) if v is not True),len(values))
  return ('low',count*32) if count else None
 def set_g(state,s,value,constant=None):
  name=reg(s)
  if name=='rsp':
   if not ptr(value) or value[1]!='stack':raise ValueError('scalar.unproved-sp')
   state['sp']=value[2];return
  state['g'][name]=None if ptr(value) and bits(s)!=64 else True if bits(s)==32 and isinstance(value,tuple) and value[0]=='low' and value[1]>=32 else value
  state['constants'].pop(name,None)
  if constant is not None:state['constants'][name]=constant
 def const(state,s):return integer(s) if integer(s) is not None else state['constants'].get(reg(s))

 def write_mem(state,row,s,values,width):
  base,at=address(state,row,s,width,True)
  for i in range(width//4):state['m'][base,at+4*i]=values[i]
 def known(values):return all(v is True for v in values)
 def summary(state,row,target):
  effect=calls.get(target)
  if effect is None:fail(row,'unproved-call-'+hex(target))
  if any(state['constants'].get(k)!=v for k,v in effect.get('constantInputs',{}).items()):fail(row,'callee-constant-input')
  for name,count in effect['inputs']:
   if not known(get(state,row,name,count//8)):fail(row,'callee-input-'+name)
  old=copy.deepcopy(state)
  def resolve(value):
   if isinstance(value,tuple) and value[0]=='in':return old['x'][value[1]][value[2]] if len(value)==3 else old['g'][value[1]]
   if ptr(value):
    if value[1]=='stack':return ('ptr','stack',old['sp']-8+value[2])
    origin=old['g'].get(value[1])
    if not ptr(origin):fail(row,'callee-output-pointer')
    return ('ptr',origin[1],origin[2]+value[2])
   return value
  for name,shape in effect['buffers'].items():
   value=old['g'].get(name)
   if not ptr(value):fail(row,'callee-buffer-'+name)
   base,at=value[1:]
   if base=='stack':
    if at<state['sp'] or at+max(shape['read'],shape['write'])>32:fail(row,'callee-local-bounds')
   elif base not in buffers or at<0 or any(at+shape[k]>buffers[base][k] for k in ('read','write') if shape[k]):fail(row,'callee-argument-bounds')
   for offset in range(0,shape['read'],4):
    if old['m'].get((base,at+offset),True if base!='stack' else None) is not True:fail(row,'callee-buffer-input')
   for offset in range(0,shape['write'],4):state['m'][base,at+offset]=True
  state['g']={k:resolve(v) for k,v in effect['return']['g'].items()};state['x']={k:[resolve(v) for v in lanes] for k,lanes in effect['return']['x'].items()};state['f']=effect['return']['f'];state['eq']=None;state['constants']={k:old['constants'][v[1]] for k,v in effect['return']['g'].items() if isinstance(v,tuple) and v[0]=='in' and v[1] in old['constants']}
 def merge(a,b):
  if a['sp']!=b['sp']:raise ValueError('scalar.frame-join')
  return dict(g={k:v if v==b['g'][k] else None for k,v in a['g'].items()},x={k:[v if v==w else None for v,w in zip(lanes,b['x'][k])] for k,lanes in a['x'].items()},m={k:v for k,v in a['m'].items() if v==b['m'].get(k)},sp=a['sp'],f=a['f'] and b['f'],eq=a['eq'] if a['eq']==b['eq'] else None,constants={k:v for k,v in a['constants'].items() if b['constants'].get(k)==v})
 states={entry:initial};queue=deque([entry]);visits=0
 while queue:
  at=queue.popleft();state=copy.deepcopy(states[at]);row=by[at];op=row['mnemonic'];a=args(row);nxt=at+len(bytes.fromhex(row['bytes']));edges=[nxt];visits+=1
  if visits>len(rows)*100:fail(row,'budget')
  if op=='nop':pass
  elif op=='ret':
   if state['sp']!=0:fail(row,'frame-return')
   returns.append(state);continue
  elif op.startswith('j'):
   target=integer(a[0])
   if target is None:fail(row,'indirect-jump')
   if op=='jmp':edges=[target]
   else:
    if not state['f']:fail(row,'unknown-branch-flags')
    edges=[nxt,target]
    if op in ('je','jne') and state['eq'] is not None:edges=[target if state['eq']==(op=='je') else nxt]
    if finite and op=='jae':
     previous=sorted(v for v in by if v<at)[-3:];texts=[(by[v]['mnemonic'],by[v]['operands']) for v in previous]
     if texts[1:]==[('btr','eax, 0x1f'),('cmp','eax, 0x7f800000')] and texts[0] in [('movd','eax, xmm0'),('vmovd','eax, xmm0')]:edges=[nxt];excluded.append(dict(branch=row['va'],target=hex(target),reason='finite-entry-Single'))
   if op=='jmp' and target not in by:
    summary(state,row,target)
    if state['sp']!=0:fail(row,'tail-frame')
    returns.append(state);continue
  elif op=='call':summary(state,row,integer(a[0]))
  elif op in ('sub','add') and a[0]=='rsp':state['sp']+=(-1 if op=='sub' else 1)*integer(a[1]);state['f']=False;state['eq']=None
  elif op=='lea':
   location=address(state,row,a[1],4)
   set_g(state,a[0],('ptr',*location) if location is not None else True)
  elif op in ('push','pop'):
   if op=='push':
    values=get(state,row,a[0],8);state['sp']-=8
    for i,v in enumerate(values):state['m']['stack',state['sp']+4*i]=v
   else:
    values=[state['m'].get(('stack',state['sp']+i)) for i in (0,4)];set_g(state,a[0],collapse(values));state['sp']+=8
  elif op in ('mov','movabs','movsxd'):
   width=size(a[0],bits(a[0])//8);width=max(4,width)
   if clean(a[0]).startswith('['):write_mem(state,row,a[0],get(state,row,a[1],width),width)
   else:
    values=get(state,row,a[1],size(a[1],width));value=collapse(values);set_g(state,a[0],value,const(state,a[1]))
  elif op in ('cmp','test','bt','btr','bts','and','or','xor','adc','add','sub','shl','shr','neg','not','bsr','mul'):
   values=[v for s in a for v in get(state,row,s,max(4,size(s,bits(s)//8)))]
   if op=='adc':values.append(state['f'])
   value=True if op=='xor' and len(a)==2 and a[0]==a[1] else True if known(values) else None
   if op=='and' and len(a)==2 and integer(a[1]) is not None:
    mask=integer(a[1]);source=state['g'].get(reg(a[0]))
    if mask==0 or mask>=0 and isinstance(source,tuple) and source[0]=='low' and mask.bit_length()<=source[1]:value=True
   if op=='mul':value=True if value is True and state['g']['rax'] is True else None;state['g']['rax']=state['g']['rdx']=value
   elif op not in ('cmp','test','bt'):set_g(state,a[0],value)
   if op!='not':state['eq']=const(state,a[0])==const(state,a[1]) if op=='cmp' and all(const(state,s) is not None for s in a) else None;state['f']=value is True and (op not in ('shl','shr') or integer(a[-1]) not in (None,0) or state['f'])
  elif op.lstrip('v') in ('movaps','movups','movapd','movdqa','movdqu','movss','movsd','movd','movq'):
   bare=op.lstrip('v');width=16 if bare in ('movaps','movups','movapd','movdqa','movdqu') else 4 if bare in ('movss','movd') else 8;values=get(state,row,a[-1],width)
   if clean(a[0]).startswith('['):write_mem(state,row,a[0],values,width)
   elif a[0].startswith('xmm'):
    upper=state['x'][a[1]][width//4:] if len(a)==3 else state['x'][a[0]][width//4:] if bare in ('movss','movsd') and a[-1].startswith('xmm') else [True]*(4-width//4)
    state['x'][a[0]]=values+upper
   else:set_g(state,a[0],collapse(values))
  elif op.lstrip('v') in ('cvtss2sd','cvtsd2ss','cvttpd2dq','cvtdq2pd','pmovsxdq'):
   bare=op.lstrip('v');source=get(state,row,a[-1],16);dest=state['x'][a[0]];source1=state['x'][a[1]] if len(a)==3 else dest
   if bare=='cvtss2sd':dest=[True if source[0] is True else None]*2+source1[2:]
   elif bare=='cvtsd2ss':dest=[True if known(source[:2]) else None]+source1[1:]
   elif bare=='cvttpd2dq':dest=[True if known(source[i:i+2]) else None for i in (0,2)]+[True,True]
   else:dest=sum(([True if source[i] is True else None]*2 for i in (0,1)),[])
   state['x'][a[0]]=dest
  elif op=='unpcklps':
   left,right=state['x'][a[0]],get(state,row,a[1],16)
   state['x'][a[0]]=[left[0],right[0],left[1],right[1]]
  elif op in ('vshufps','shufps'):
   immediate=integer(a[-1]);left=state['x'][a[1] if op=='vshufps' else a[0]];right=state['x'][a[2] if op=='vshufps' else a[1]]
   if immediate is None or not 0<=immediate<256:fail(row,'shuffle-immediate')
   state['x'][a[0]]=[left[immediate&3],left[(immediate>>2)&3],right[(immediate>>4)&3],right[(immediate>>6)&3]]
  elif op=='vpcmpeqq':
   left,right=get(state,row,a[1],16),get(state,row,a[2],16)
   state['x'][a[0]]=sum(([True if a[1]==a[2] or known(left[i:i+2]+right[i:i+2]) else None]*2 for i in (0,2)),[])
  elif op.lstrip('v')=='psrldq':
   count=integer(a[-1]);source=state['x'][a[1]] if len(a)==3 else state['x'][a[0]]
   if count%4:fail(row,'shift-lane')
   state['x'][a[0]]=(source[count//4:]+[True]*4)[:4]
  elif re.fullmatch(r'v?(?:add|sub|mul|andn?|or|xor)(?:ss|sd|pd|ps)|v(?:fmadd|fnmadd|fmsub)\d+sd',op):
   scalar=op.endswith(('ss','sd'));width=4 if op.endswith('ss') else 8 if scalar else 16;lanes=width//4
   source_operands=a if 'fm' in op or 'fnm' in op else a[1:] if op.startswith('v') else a
   sources=[get(state,row,s,width) for s in source_operands];dest=state['x'][a[1]][:] if op.startswith('v') and len(a)==3 and 'fm' not in op and 'fnm' not in op else state['x'][a[0]][:]
   if op.lstrip('v').startswith('xor') and len(set(a[1:] if op.startswith('v') else a))==1:dest[:lanes]=[True]*lanes
   elif scalar:dest[:lanes]=[True if all(known(v) for v in sources) else None]*lanes
   else:dest=[True if all(v[i] is True for v in sources) else None for i in range(4)]
   state['x'][a[0]]=dest
  else:fail(row,'unsupported-operation')
  for successor in edges:
   if successor not in by:
    if successor not in calls:fail(row,'missing-successor-'+hex(successor))
    tail=copy.deepcopy(state);summary(tail,row,successor)
    if tail['sp']!=0:fail(row,'tail-frame')
    returns.append(tail);continue
   updated=merge(states[successor],state) if successor in states else copy.deepcopy(state)
   if successor not in states or updated!=states[successor]:states[successor]=updated;queue.append(successor)
 if not returns:raise ValueError('scalar.no-return')
 result=returns[0]
 for state in returns[1:]:result=merge(result,state)
 for name,count in required:
  if not known(get(result,by[entry],name,count//8)):raise ValueError('scalar.undefined-return:'+name+':'+str(get(result,by[entry],name,count//8)))
 for name in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15'):
  if result['g'][name]!=initial['g'][name]:raise ValueError('scalar.nonvolatile:'+name)
 for n in range(6,16):
  if result['x'][f'xmm{n}']!=initial['x'][f'xmm{n}']:raise ValueError('scalar.nonvolatile-vector')
 for name,shape in buffers.items():
  if any(result['m'].get((name,at)) is not True for at in range(0,shape['write'],4)):raise ValueError('scalar.undefined-buffer:'+name)
 return dict(status='conditional-relocation-effects-proved',inputs=list(inputs),constantInputs=constant_inputs,buffers=buffers,required=list(required),return_omitted=False,**{'return':{k:result[k] for k in ('g','x','f')}},visitedInstructions=len(states),fixedPointVisits=visits,finiteErrorBranches=excluded,memoryReads=sorted(reads,key=str),memoryWrites=sorted(writes,key=str))
