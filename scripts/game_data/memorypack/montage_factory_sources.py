"""Current reference creation composition, with ordinary helper effects explicit."""
import hashlib,json,re
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.memorypack import scalar_param_native as scalar

def validate_factories(image,records):
 ctx=NativeReferenceContext(image);base=image.pe.image_base;md=image.metadata;out=[]
 for record in records:
  original,name=record['original'],record['wrapper'];td=ctx.index.types[original]
  if ctx.is_value_type(original) or ctx.field(name+'::__instance')!=(name,original,16):raise ValueError('factory reference holder differs')
  for program in record['programs']:
   image.validate_method_row(program['method']);method=image.metadata.methods[program['method'][0]]
   scalar.owned_method_abi(image,ctx,method.index,ctx.index.types[name].index,('void',1,False),[],'montage.factory')
   if program['method'][1]!=name or program['method'][2] not in ('.ctor','CreateInstance'):raise ValueError('montage.factory:method-role')
   parts=program['parts'];entry=base+program['method'][3];owned=[(base+p['startRva'],base+p['endRva']) for p in parts]
   if sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(entry-base)['ranges'])!=sorted((p['startRva'],p['endRva']) for p in parts):raise ValueError('factory complete owner differs')
   image.check_windows(parts,label='montage.factory');rows=[r for p in parts for r in image.body_index._decode(base+p['startRva'],p['endRva']-p['startRva'])]
   for r in rows:
    if image.pe.bytes_at_va(int(r['va'],16),len(bytes.fromhex(r['bytes'])))!=bytes.fromhex(r['bytes']):raise ValueError('factory instruction differs')
   usage=program['allocationContext']
   if usage['tag']!=1 or usage['typeName']!=original:raise ValueError('montage.factory:original-allocation-type')
   validate_typed_usage_context(image,usage,label='montage.factory');load=next(i for i,r in enumerate(rows) if int(r['va'],16)==base+usage['instructionRva']);allocation=rows[load+1]
   if allocation['text'].split()[0]!='call':raise ValueError('factory allocation adjacency differs')
   returns={int(allocation['va'],16):'original'};tails={int(r['va'],16):{'target':control_transfer(r)['target']} for r in rows if control_transfer(r)['kind']=='jump' and not any(a<=control_transfer(r)['target']<b for a,b in owned)}
   flow=check_reference_origins(rows,entry=entry,owned_ranges=owned,incoming_registers={'rcx':'wrapper'},incoming_stack_slots={},selected_call_returns=returns,tail_exits=tails)
   holder_stores=[];defaults=[];constructors=[];calls=[]
   for i,r in enumerate(rows):
    state=flow['registerOrigins'][int(r['va'],16)];text=r['text'];transfer=control_transfer(r)
    if transfer['kind']=='call':
     calls.append(transfer['target'])
     aliases=[m for m in md.methods_for(td) if md.string(m.name_index)=='.ctor' and image.method_pointer_va(m)==transfer['target']]
     if aliases:
      ctor,=aliases
      if state['rcx']!=['original'] or ctor.parameter_count or ctx.type_name(ctor.return_type)!='void' or ctor.flags&16:raise ValueError('factory actual original constructor ABI differs')
      constructors.append(dict(methodIndex=ctor.index,call=r,argumentOrigin=state['rcx']))
    match=re.fullmatch(r'mov \[(rbx|rdi)\+0x10\], (rax|rbx)',text)
    if match and state[match[1]]==['wrapper']:
     if state[match[2]]!=['original']:raise ValueError('factory original result not stored unchanged')
     holder_stores.append(r);continue
    match=re.fullmatch(r'mov \[rax\+(0x[0-9a-f]+)\], (0x[0-9a-f]+)',text)
    if match:
     offset=int(match[1],16);fields=[f for f in md.fields_for(td) if not ctx.field_attributes(f.type_index)&16 and ctx.field(original+'::'+md.string(f.name_index))[2]==offset]
     if state['rax']!=['original'] or len(fields)!=1 or ctx.type_name(fields[0].type_index) not in ('int','float','Beyond.NPC.Animation.GPUAnimType'):raise ValueError('factory initialized owned scalar differs')
     defaults.append(dict(field=md.string(fields[0].name_index),instruction=r))
   if len(holder_stores)!=1 or len(tails)!=1:raise ValueError('factory unique holder store/tail differs')
   tail_at,tail=next(iter(tails.items()));tail_index=next(i for i,r in enumerate(rows) if int(r['va'],16)==tail_at);store_at=rows.index(holder_stores[0]);leas=[r for r in rows[:tail_index] if re.fullmatch(r'lea rcx, \[(rbx|rdi)\+0x10\]',r['text'])]
   if len(leas)!=1:raise ValueError('factory collector address differs')
   address=leas[0];reg=address['text'].split('[',1)[1].split('+',1)[0]
   if flow['registerOrigins'][int(address['va'],16)][reg]!=['wrapper'] or not store_at<tail_index:raise ValueError('factory collector wrapper origin/order differs')
   between=rows[store_at+1:tail_index]
   if any(control_transfer(r)['kind'] not in ('next',) or not re.fullmatch(r'(mov rbx, \[rsp\+0x30\]|add rsp, 0x20|pop rbx|pop rdi)',r['text']) for r in between):raise ValueError('factory effects after holder assignment differ')
   out.append(dict(original=original,wrapper=name,method=program['method'],allocationUsage=usage,allocationCall=allocation,originalConstructors=constructors,ownedDefaults=defaults,holderStore=holder_stores[0],collectorAddress=address,collectorTail=tail,localControl={k:v for k,v in flow.items() if k!='registerOrigins'}))
 return out
