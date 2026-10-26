import hashlib
"""Selected initialized original-body event bridge; runtime delivery stays conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def _flag(g):
 raw=g.read(7)
 if raw[:2]!=b'\x80\x3d' or raw[-1]!=0:raise ValueError('gender-select.initialized-flag')
 return g.at+int.from_bytes(raw[2:6],'little',signed=True)


def execute_path(regions,entry,s,*,receiver_absent=True):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec30');flag=_flag(g);g.take('498bd8','0f29742420','488bf9','0f28f1');g.branch('75',True,1)
 hook=g.relative('488b05');g.take('488b4830','4885c9');g.branch('74',receiver_absent,1)
 if not receiver_absent:g.take('488b8150350000','4885c0');g.branch('74',True,1)
 g.take('33d2','488bcf');g.call(s['pause']);action=g.relative('488b0d');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('75',True,1)
 callback=g.relative('4c8b05');g.take('4533c9','488bd7','488bcb');g.call(s['actionCtor']);game_action=g.relative('488b0d');g.call(s['typeInit']);g.take('33d2','488bcb');g.call(s['start']);g.take('488b5c2440','0f28742420','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,metadataFlag=flag,hookCell=hook,actionClassCell=action,callbackMethodCell=callback,gameActionClassCell=game_action,callback='new Action(incoming this, OnCutscenePlayEnd), same receiver passed to StartGenderSelect',condition='Initialized metadata, selected IFix receiver or callback slot absent, normal allocation/delegate construction/Pause/class-init helpers preserving nonvolatile registers, nonnull delegate; no execution or callback delivery observed.')


def start_path(regions,entry,s,*,receiver_absent=True):
 g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');flag=_flag(g);g.take('488bda','488bf9');g.branch('75',True,1)
 hook=g.relative('488b05');g.take('488b4828','4885c9');g.branch('74',receiver_absent,1)
 if not receiver_absent:g.take('488b8170d50000','4885c0');g.branch('74',True,1)
 singleton=g.relative('488b0d');g.call(s['singleton']);g.take('4885c0');g.branch('75',True,1)
 event=g.relative('488b0d');g.take('8b98'+s['fieldOffset'].to_bytes(4,'little').hex());g.call(s['typeInit']);send=g.relative('4c8b05');g.take('488bd7','8bcb');g.call(s['send']);g.take('b001','488b5c2430','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,metadataFlag=flag,hookCell=hook,singletonContextCell=singleton,eventClassCell=event,sendContextCell=send,keyWidth=4,keyOffset=s['fieldOffset'],keyArgument='ECX: exact owned CombineKey DWORD',payloadArgument='RDX: unchanged incoming Action',normalResult=True,condition='Initialized metadata, selected IFix receiver or callback slot absent, nonnull coherent PredefinedEventKeys singleton and ordinary class-init/SendGlobal effects; canonical reference sharing and matching current MethodInfo required. No runtime event identity/delivery/phase execution proved.')


def initialized_singleton(regions,entry,s):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9','488b4920');g.call(s['context']);g.take('33d2','488b88c0000000');g.call(s['indexed']);g.take('488b88b8000000','48833900');g.branch('74',False,1)
 g.take('488b4b20');g.call(s['context']);g.take('33d2','488b88c0000000');g.call(s['indexed']);g.take('488b80b8000000','488b00','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,result='same nonnull reference from coherent generic class static slot zero',condition='Selected initialized generic context, ordinary context/index helpers and stable nonnull static singleton; creation branch excluded.')


def initialized_keys(regions,entry,fields,*,key,base_ctor):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=_flag(g);g.take('488bd9');g.branch('0f85',True)
 sources=[]
 for field in fields:
  context=g.relative('488b15');literal=g.relative('488b0d');g.call(key)
  offset=field['offset'];g.take(('8943'+bytes([offset]).hex())if 0<=offset<128 else '8983'+offset.to_bytes(4,'little').hex())
  sources.append(dict(name=field['name'],offset=offset,contextCell=context,literalCell=literal))
 g.take('488bcb');base_context=g.relative('488b15');g.take('4883c420','5b')
 if g.relative('e9')!=base_ctor:raise ValueError('gender-select.base-ctor')
 return dict(selectedBytes=g.seen,metadataFlag=flag,fields=sources,baseContextCell=base_context,condition='Initialized metadata and valid incoming object; typed GetKey helper returns its normal CombineKey DWORD, Win64 nonvolatile/disjoint object assumptions. Construction/registry execution and coherent Lua/native key identity remain conditional.')


def context_tail(regions,entry,target):
 g=BytesPath(regions,entry);cell=g.relative('488b15')
 if g.relative('e9')!=target:raise ValueError('gender-select.key-tail')
 return dict(selectedBytes=g.seen,contextCell=cell,target=target)


from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
from scripts.game_data.il2cpp.generic_entries import GenericEntries


def derive(image):
 ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base;owned={};facts={}
 def method(owner,name):
  td=ctx.index.types[owner];m,=[m for m in md.methods_for(td)if md.string(m.name_index)==name];return m
 def source(pointer):
  if pointer not in owned:
   windows=[]
   for part in image.unwind_index.family(pointer-base)['ranges']:
    a,z=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);windows.append(dict(startRva=a,endRva=z,raw=raw.hex(),sha256=hashlib.sha256(raw).hexdigest().upper(),rows=image.body_index._decode(base+a,z-a)))
   owned[pointer]=dict(entryRva=pointer-base,windows=windows,names=image.body_index.names_by_pointer.get(pointer,[]))
  return [(base+w['startRva'],bytes.fromhex(w['raw']))for w in owned[pointer]['windows']]
 def calls(pointer):
  source(pointer);return [(int(r['va'],16),int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True))for w in owned[pointer]['windows']for r in w['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==232]
 def named(pointer,owner,name):
  if not any(r['type']==owner and r['method']==name for r in image.body_index.names_by_pointer.get(pointer,[])):raise ValueError('bridge.named-target:'+owner+'.'+name)
 def usage(cell):
  # Find the sole RIP load into this exact usage cell, with owned instruction bytes.
  rows=[r for v in owned.values()for w in v['windows']for r in w['rows']if len(bytes.fromhex(r['bytes']))==7 and bytes.fromhex(r['bytes'])[:3]in(bytes.fromhex('488b0d'),bytes.fromhex('488b15'),bytes.fromhex('4c8b05')) and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
  if not rows:raise ValueError('bridge.unowned-usage')
  return derive_typed_usage_context(image,int(rows[0]['va'],16)-base,label='gender-select.bridge')
 def literal(cell):
  raw=image.pe.bytes_at_va(cell,8);table=md.sections['stringLiteral'];data=md.sections['stringLiteralData'];index=unresolved_usage_index(raw,table.size//8,tag=5,source='gender-select.literal',offset=cell);a,z=literal_record(md.buf[table.offset+index*8:table.offset+(index+1)*8],data.size,source='gender-select.literal',offset=index*8);return md.buf[data.offset+a:data.offset+a+z].decode('utf-8')
 execute=image.method_pointer_va(method('Beyond.Gameplay.Actions.StartGenderSelect','Execute'));start=image.method_pointer_va(method('Beyond.Gameplay.Actions.GameAction','StartGenderSelect'));ec=calls(execute);sc=calls(start)
 pause=image.method_pointer_va(method('Beyond.Gameplay.Actions.ActionBase','Pause'));action_ctor=image.method_pointer_va(method('System.Action','.ctor'))
 # Current named bodies bind the semantic callees. Remaining ordinary helpers stay explicit conditions.
 e={'pause':pause,'allocate':ec[-5][1],'actionCtor':action_ctor,'typeInit':ec[-2][1],'start':start}
 if ec[-1][1]!=start:raise ValueError('bridge.start-call')
 facts['execute']=[execute_path(source(execute),execute,e,receiver_absent=x)for x in(True,False)]
 td=ctx.index.types['Beyond.PredefinedEventKeys'];offsets=runtime_type_field_offsets(md,image.pe,image.registration,td.index);fields=[dict(name=md.string(f.name_index),type=ctx.type_name(f.type_index),offset=offsets[md.string(f.name_index)])for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 if any(f['type']!='Beyond.CombineKey'for f in fields):raise ValueError('bridge.key-field-type')
 field,=[f for f in fields if f['name']=='GENDER_SELECT_START'];s={'singleton':sc[-4][1],'typeInit':sc[-2][1],'send':sc[-1][1],'fieldOffset':field['offset']}
 named(s['singleton'],'Beyond.Singleton`1','get_instance');named(s['send'],'Beyond.EventManager','SendGlobal')
 facts['start']=[start_path(source(start),start,s,receiver_absent=x)for x in(True,False)]
 singleton=s['singleton'];hc=calls(singleton);facts['singleton']=initialized_singleton(source(singleton),singleton,dict(context=hc[0][1],indexed=hc[1][1]))
 ctor=image.method_pointer_va(method('Beyond.PredefinedEventKeys','.ctor'));regions=source(ctor);rows=owned[ctor]['windows'][0]['rows'];warm=next(r for r in rows if bytes.fromhex(r['bytes'])[:2]==b'\x0f\x85');warm_at=int(warm['va'],16)+6+int.from_bytes(bytes.fromhex(warm['bytes'])[2:],'little',signed=True);first=next(i for i,r in enumerate(rows)if int(r['va'],16)==warm_at);cr=rows[first+2];key=int(cr['va'],16)+5+int.from_bytes(bytes.fromhex(cr['bytes'])[1:],'little',signed=True);tail=rows[-1];base_ctor=int(tail['va'],16)+5+int.from_bytes(bytes.fromhex(tail['bytes'])[1:],'little',signed=True)
 facts['keys']=initialized_keys(regions,ctor,sorted(fields,key=lambda f:f['offset']),key=key,base_ctor=base_ctor)
 contexts=[usage(f['contextCell'])for f in facts['keys']['fields']];expected=(contexts[0]['typeName'],contexts[0]['methodName'],contexts[0]['classArguments'],contexts[0]['methodArguments'])
 if expected!=('Beyond.KeyGenerator`1','GetKey',['string'],[])or any((u['typeName'],u['methodName'],u['classArguments'],u['methodArguments'])!=expected for u in contexts):raise ValueError('bridge.key-contexts')
 for f in facts['keys']['fields']:
  if literal(f['literalCell'])!=f['name']:raise ValueError('bridge.key-literal:'+f['name'])
 thunk=image.pe.bytes_at_va(key,12);target=key+12+int.from_bytes(thunk[8:],'little',signed=True);facts['keyTail']=context_tail([(key,thunk)],key,target);ku=derive_typed_usage_context(image,key-base,label='gender-select.key-tail');facts['keyTail']['typedContext']=ku
 if (ku['typeName'],ku['methodName'],ku['classArguments'],ku['methodArguments'])!=expected:raise ValueError('bridge.tail-context')
 observed=GenericEntries(image).observe(ku['methodSpec'][0],ku['classArguments'],ku['methodArguments'])
 canonical=GenericEntries(image).observe(ku['methodSpec'][0],['object'],[]);named(target,'Beyond.KeyGenerator`1','GetKey');source(target);
 if not any(o['pointer']==target for o in canonical):raise ValueError('gender-select.canonical-key-target')
 facts['keyTail'].update(closedObservation=observed,canonicalObservation=canonical,condition='Exact closed string MethodInfo tail-calls current canonical object GetKey; compatible reference sharing and actual context binding required, no closed AOT registration invented.')
 for group in('execute','start'):
  for f in facts[group]:
   f['typedUsages']={k:usage(v)for k,v in f.items()if k.endswith(('ClassCell','ContextCell'))}
 callback=facts['execute'][0]['callbackMethodCell'];raw=image.pe.bytes_at_va(callback,8);idx=unresolved_usage_index(raw,len(md.methods),tag=3,source='gender-select.callback',offset=callback);cb=md.methods[idx]
 if cb.declaring_type!=method('Beyond.Gameplay.Actions.StartGenderSelect','Execute').declaring_type or md.string(cb.name_index)!='OnCutscenePlayEnd'or md.parameters_for(cb)or ctx.type_name(cb.return_type)!='void':raise ValueError('bridge.callback')
 facts['callback']=dict(methodIndex=idx,owner=image.type_name(cb.declaring_type),method=md.string(cb.name_index));facts['keyField']=field;facts['keyContexts']=contexts;facts['closedSendObservation']=GenericEntries(image).observe(facts['start'][0]['typedUsages']['sendContextCell']['methodSpec'][0],[],['System.Action']);facts['canonicalSendObservation']=GenericEntries(image).observe(facts['start'][0]['typedUsages']['sendContextCell']['methodSpec'][0],[],['object'])
 
 for f in facts['execute']:
  if f['typedUsages']['actionClassCell']['typeName']!='System.Action' or f['typedUsages']['gameActionClassCell']['typeName']!='Beyond.Gameplay.Actions.GameAction':raise ValueError('gender-select.execute-types')
 for f in facts['start']:
  u=f['typedUsages'];a=u['singletonContextCell'];b=u['sendContextCell']
  if (a['typeName'],a['methodName'],a['classArguments'],a['methodArguments'])!=('Beyond.Singleton`1','get_instance',['Beyond.PredefinedEventKeys'],[]) or (b['typeName'],b['methodName'],b['classArguments'],b['methodArguments'])!=('Beyond.EventManager','SendGlobal',[],['System.Action']) or u['eventClassCell']['typeName']!='Beyond.EventManager':raise ValueError('gender-select.dispatch-types')
  singleton_observation=GenericEntries(image).observe(a['methodSpec'][0],a['classArguments'],a['methodArguments'])
  singleton_canonical=GenericEntries(image).observe(a['methodSpec'][0],['object'],[])
  if not any(o['pointer']==singleton for o in singleton_canonical):raise ValueError('gender-select.singleton-registration')
 if not any(o['pointer']==s['send']for o in facts['canonicalSendObservation']):raise ValueError('gender-select.canonical-send-target')
 value=ctx.index.types['Beyond.CombineKey'];vf=[f for f in md.fields_for(value)if not ctx.field_attributes(f.type_index)&16]
 if len(vf)!=1 or ctx.field('Beyond.CombineKey::'+md.string(vf[0].name_index))!=('Beyond.CombineKey','int',16)or not ctx.is_value_type('Beyond.CombineKey'):raise ValueError('gender-select.combine-key-field')
 sizeptr=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+value.index*8);size=image.pe.bytes_at_va(sizeptr,16)
 if int.from_bytes(size[:4],'little')!=20 or int.from_bytes(size[4:8],'little',signed=True)!=4:raise ValueError('gender-select.combine-key-size')
 facts['keyAbi']=dict(type='Beyond.CombineKey',field=ctx.field('Beyond.CombineKey::'+md.string(vf[0].name_index)),boxedBytes=20,nativeBytes=4)
 facts['singletonRegistration']=dict(closed=singleton_observation,canonical=singleton_canonical,condition='Exact closed PredefinedEventKeys MethodInfo calls current canonical reference singleton body under compatible reference sharing, coherent initialized context/static storage; no closed AOT entry invented.')
 def compact(v):
  if isinstance(v,dict):return {k:compact(x)for k,x in v.items()if k not in('selectedBytes','raw','rows')}
  if isinstance(v,(list,tuple)):return [compact(x)for x in v]
  return v
 facts['keyContext']=contexts[0];facts.pop('keyContexts');facts['keys']['fields']=[f for f in facts['keys']['fields']if f['name']=='GENDER_SELECT_START']
 return compact(dict(programs=facts,owned=list(owned.values()),runtimeCaseResolution='unresolved',evidenceBoundary='conditional'))
