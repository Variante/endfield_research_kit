"""Complete generated inlined reference-record source programs.

Member and field identities are independently supplied current metadata facts.
Every selected instruction has a source, field, conditional barrier or frame
role; this proof never chooses a child grammar or an effective live provider.
"""
from __future__ import annotations
import re
from scripts.game_data.il2cpp.initializer_control import control_transfer,_ALIASES
from scripts.game_data.memorypack import buff_ec_profiles_native as ec

LABEL='generatedInlineReaderSource'
def need(check,condition,detail=None):
 if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:900])
def reg(name):return _ALIASES.get(name,name)

def complete_program(rows,path,events,setters,contexts,*,reader,output,offsets,base,disabled_flag,provider,dispatch):
 """Own the full selected count-to-return program with symbolic value flow."""
 need('member-setter-bijection',len(events)==len(setters)>0)
 by={ec.va(r):r for r in rows};context_by={base+c['instructionRva']:c for c in contexts};event_by={base+e['instruction'][0]:(n,e)for n,e in enumerate(events)}
 provider_starts={base+e['context']['instructionRva']:(n,e)for n,e in enumerate(events)if e.get('mode')=='typed-provider-slot-five'}
 state={reader:('reader',),output:('output',)};locals_={};source_locals=[];sources=[];stores=[];calls=[];at=0;flags=None;pending=None
 def row():need('complete-owned-path',at<len(path));r=path[at];need('same-owned-bytes',ec.raw(r)==ec.raw(by[ec.va(r)]));return r
 def take(text=None,site=None):
  nonlocal at
  r=row();need('exact-instruction',(text is None or r['text']==text)and(site is None or ec.site(r,base)==site),(text,r));at+=1;return r
 def branch(kind):
  r=take();flow=control_transfer(r);need('actual-conditional',flow['kind']=='conditional')
  code=flow['conditionCode'];truth=code==5 if kind=='nonnull'else code==13 if kind=='buffer'else code==4 if kind=='disabled'else code==4 if kind=='count'else None
  need('reviewed-branch-condition',truth is not None and code in((4,5)if kind in('nonnull','disabled','count')else(12,13)),(kind,r))
  need('same-selected-edge',at<len(path)and ec.va(path[at])==(flow['target']if truth else ec.va(r)+len(ec.raw(r))))
 def member_value(n,normalized=False):return('member',n,normalized)
 def provider_program(n,e):
  nonlocal at
  start=at;context=e['context'];cr=context['register'];need('provider-owned-context',cr=='rsi'and context_by[base+context['instructionRva']]==context)
  take(site=[context['instructionRva'],context['instructionHex']]);w=take();m=re.fullmatch(r'mov (rbx|rbp|rsi|rdi|r1[2345]), \['+output+r'\]',w['text']);need('provider-wrapper-output',m is not None);wr=m[1];state[wr]=('wrapper',)
  take(f'cmp qword [{cr}+0x38], 0x0');branch('nonnull')
  c=take();need('provider-static-class-load',len(ec.raw(c))==7 and ec.raw(c)[:3]==bytes.fromhex('488b0d'))
  z=take();m=re.fullmatch(r'mov qword \[rsp\+0x([0-9a-f]+)\], 0x0',z['text']);need('provider-zero-full-output',m is not None);local=int(m[1],16);need('provider-local-outside-call-home',32<=local<256)
  take('cmp dword [rcx+0xe0], 0x0');branch('nonnull');take(f'mov rcx, [{cr}+0x38]');take('mov rcx, [rcx]')
  c=take();f=control_transfer(c);need('actual-provider-call',f['kind']=='call'and f['target']==provider);calls.append(ec.site(c,base))
  take('test rax, rax');branch('nonnull');take('mov ecx, 0x5');take(f'lea r9, [rsp+{local:#x}]');take(f'mov r8, {reader}');take('mov rdx, rax');take(site=e['instruction']);need('actual-dispatch-call',control_transfer(path[at-1])['target']==dispatch);calls.append(e['instruction'])
  locals_[local]=member_value(n);source_locals.append(dict(displacement=local,bytes=8,zeroInstruction=ec.site(z,base),sourceMember=n))
  for r in('rax','rcx','rdx','r8','r9','r10','r11'):state.pop(r,None)
  sources.append(dict(memberIndex=n,mode='typed-provider-slot-five',program=[ec.site(r,base)for r in path[start:at]],outputLocal=local,context=context,callbackSelectionConditional=True))
 # The actual count comparison and branch precede every source and field store.
 count=take();need('actual-byte-count-guard',count['text'].startswith('cmp ')and ec.raw(count)[-1]==len(events))
 # For a matching count JE is taken and JNE falls through.
 r=take();f=control_transfer(r);need('matching-count-branch',f['kind']=='conditional'and f['conditionCode']in(4,5));need('matching-count-edge',ec.va(path[at])==(f['target']if f['conditionCode']==4 else ec.va(r)+len(ec.raw(r))))
 while at<len(path):
  r=row();address=ec.va(r);text=r['text'];flow=control_transfer(r);move=r.get('memoryOperation',{});memory=move.get('address',{})
  if address in provider_starts:
   n,e=provider_starts[address];provider_program(n,e);flags=None;continue
  if address in event_by:
   n,e=event_by[address]
   if 'program'in e:
    start=at;width,program=ec.inline_read(path,at,reader,offsets);need('fresh-complete-inline-source',[ec.site(x,base)for x in program]==e['program']and width==e['wireBytes'])
    load=program[1];dest=load.get('byteMemoryZeroExtensionOperation',{}).get('destinationRegister')or load.get('memoryOperation',{}).get('register');need('inline-result-register',dest is not None)
    state[reg(dest)]=member_value(n);at+=len(program);sources.append(dict(memberIndex=n,mode='buffered-inline',program=[ec.site(x,base)for x in path[start:at]],wireBytes=width,resultRegister=reg(dest)));flags=None;continue
   need('direct-current-source-call',flow['kind']=='call'and state.get('rcx')==('reader',))
   take(site=e['instruction']);calls.append(e['instruction'])
   for name in('rax','rcx','rdx','r8','r9','r10','r11'):state.pop(name,None)
   state['rax']=member_value(n,e['kind']=='byte');sources.append(dict(memberIndex=n,mode=e.get('mode'),program=[e['instruction']]));flags=None;continue
  if flow['kind']=='conditional':
   need('flags-have-owned-role',flags in('nonnull','buffer','disabled'),(flags,r));branch(flags)
   if flags=='disabled':need('reference-store-before-disabled-edge',pending is not None);pending=None
   flags=None;continue
  if flow['kind']=='jump':
   take();need('owned-jump-edge',at<len(path)and flow['target']==ec.va(path[at]));continue
  if flow['kind']=='return':need('whole-final-return',at==len(path)-1 and pending is None);take();continue
  if flow['kind']in('call','indirectCall','registerCall'):raise ValueError(LABEL+'.unowned-call:'+text)
  if address in context_by:
   context=context_by[address];take(site=[context['instructionRva'],context['instructionHex']]);state[reg(context['register'])]=('context',context['fullTypeName'],context['methodName']);continue
  match=re.fullmatch(r'test (\w+), \1',text)
  if match:
   value=state.get(reg(match[1]));need('known-test-value',value is not None,(text,state))
   if value[0]in('wrapper','original'):flags='nonnull'
   elif value[0]=='member'and events[value[1]]['kind']=='byte':flags=('bool',value[1])
   else:raise ValueError(LABEL+'.unowned-test:'+str(value))
   take();continue
  match=re.fullmatch(r'setne (\w+)',text)
  if match:
   need('bool-normalization',isinstance(flags,tuple)and flags[0]=='bool');state[reg(match[1])]=member_value(flags[1],True);take();continue
  compare=r.get('memoryImmediateComparisonOperation',{})
  if compare:
   a=compare['sourceAddress'];immediate=compare['immediateValue'];bits=compare['bits']
   if a.get('base')==reader and a.get('displacement')==offsets['bufferLength']and immediate in(1,4)and bits==32:flags='buffer'
   elif a.get('ripRelative')and a.get('absoluteAddress')==base+disabled_flag and immediate==0 and bits==32:flags='disabled'
   else:raise ValueError(LABEL+'.unowned-comparison:'+text)
   take();continue
  if move:
   direction=move['direction'];operand=memory.get('base');displacement=memory.get('displacement',0);register=reg(move.get('register'));width=move.get('memoryBytes')
   need('ordinary-memory-address',memory.get('index')is None and not memory.get('ripRelative'))
   if direction=='load':
    value=state.get(operand)
    if value==('output',)and displacement==0 and width==8:state[register]=('wrapper',)
    elif value==('wrapper',)and displacement==16 and width==8:state[register]=('original',)
    elif operand=='rsp'and displacement in locals_ and width==8:state[register]=locals_[displacement]
    elif operand=='rsp'and register in('rbx','rbp','rsi','rdi','r12','r13','r14','r15')and width==8:state[register]=('restored',register)
    else:raise ValueError(LABEL+'.unowned-load:'+str((r,value)))
   else:
    if operand=='rsp':
     need('frame-home-only',width==8 and register in('rbx','rbp','rsi','rdi','r12','r13','r14','r15')and displacement not in locals_)
    else:
     value=state.get(register);need('whole-current-field-value',value is not None and value[0]=='member'and state.get(operand)==('original',),(r,value,state.get(operand)))
     n=value[1];setter=setters[n];need('field-order-and-identity',n==len(stores)and displacement==setter['fieldOffset']and width==setter['storedBytes'],(n,setter,r))
     need('owned-direct-holder-setter',setter['getter']is None and (setter['profile']=='direct-base-holder-setter'or setter['profile']=='metadata-field-binding'and setter['setterImplementationAdmitted']is False)and setter['program']['holderOffset']==16)
     if events[n]['kind']=='byte':need('bool-source-normalization',value[2])
     reference=events[n]['kind'].startswith('reference:')or events[n]['kind']=='byte-payload'
     if reference:need('actual-disabled-reference-barrier',flags=='disabled'and pending is None);pending=n
     stores.append(dict(memberIndex=n,instruction=ec.site(r,base),fieldOffset=displacement,storedBytes=width,normalIncomingValueStoredUnchanged=True,conditionalDisabledBarrier=reference))
   take();continue
  match=re.fullmatch(r'mov (\w+), (\w+)',text)
  if match:
   destination,source=map(reg,match.groups());need('known-register-transfer',source in state,(r,state))
   def bits(name):return 64 if name in('rax','rbx','rcx','rdx','rbp','rsp','rsi','rdi')or re.fullmatch(r'r(?:[89]|1[0-5])',name)else 32 if name.startswith('e')or name.endswith('d')else 8
   value=state[source];width=setters[value[1]]['storedBytes']if value[0]=='member'else 8
   need('whole-register-transfer-width',min(map(bits,match.groups()))>=8*width)
   state[destination]=value;take();continue
  if text.startswith('lea '):
   destination=text.split()[1].rstrip(',');raw=ec.raw(r);need('dead-RIP-address-only',len(raw)==7 and raw[1]==0x8d and raw[2]&0xc7==5 and destination in('rbp','r15'))
   state[destination]=('address',);take();continue
  if text.startswith(('add rsp, ','pop ')):
   take();continue
  raise ValueError(LABEL+'.unowned-instruction:'+str(r))
 need('all-current-fields-written-once',len(stores)==len(events)and pending is None)
 return dict(selectedProgram=[ec.site(r,base)for r in path],sources=sources,fieldStores=stores,actualCalls=calls,
  sourceLocalReferences=source_locals,completeSelectedNormalProgram=True,wholeOwnerAdmitted=False,childGrammarAdmitted=False)
