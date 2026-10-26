"""Current Montage owned field programs; collection and provider joins are separate."""
import hashlib,re
from scripts.game_data.levelscript_family_regenerate import Build,select_calls
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
from scripts.game_data.il2cpp.body_claims import _writes_register
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.memorypack.record_sources import normal_source_rows,typed_source_context,prove_reference_setter_rows
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param
from scripts.game_data.il2cpp.owned_partition import BranchGrammar

from scripts.game_data.memorypack.scalar_param_native import parameter_setter

def check_inline_copy(rows, *, width, field, remaining, current, instance, advance, reader_setup=False):
    if width not in (16,32,36) or type(field) is not int or field<16:
        raise ValueError('montageCopy.layout')
    g=BranchGrammar(rows,label='montageCopy')
    g.take(f'cmp dword [rbx+{remaining:#x}], {width:#x}', 'mov rsi, [rdi]')
    refill=g.branch('jl')['target']
    g.take(f'mov rax, [rbx+{current:#x}]',f'mov edx, {width:#x}','mov rcx, rbx','movups xmm6, [rax]')
    if width==36:g.take('mov ebp, [rax+0x20]')
    if width>=32:g.take('movups xmm7, [rax+0x10]')
    g.call(advance)
    g.take('test rsi, rsi');null=g.branch('je')['target']
    g.take(f'mov rax, [rsi+{instance:#x}]','test rax, rax')
    if g.branch('je')['target']!=null:raise ValueError('montageCopy.null-target')
    g.take(f'movups [rax+{field:#x}], xmm6')
    if reader_setup:g.take('mov rcx, rbx')
    if width>=32:g.take(f'movups [rax+{field+16:#x}], xmm7')
    if width==36:g.take(f'mov [rax+{field+32:#x}], ebp')
    g.finish();start=int(rows[0]['va'],16);end=int(rows[-1]['va'],16)+len(bytes.fromhex(rows[-1]['bytes']))
    if start<=refill<end or start<=null<end:raise ValueError('montageCopy.guard-target')
    return dict(bufferedCopyBytes=width,fieldOffset=field,refillTarget=refill,nullTarget=null,
        evidenceBoundary='conditional',condition='Selected original decoded instructions, validated typed holder/field and advance helper, sufficient contiguous input, nonnull matching objects and ordinary Win64 nonvolatile preservation. Refill/error paths, typed source order and whole owner are separate.')

def scalar_setter(rows, *, field, mode, instance=16):
    value={'byte':'dl','dword':'edx','qword':'rdx','single':'xmm1'}.get(mode)
    if value is None or type(field) is not int or field<16:raise ValueError('montageSetter.layout')
    g=BranchGrammar(rows,label='montageSetter')
    g.take('sub rsp, 0x28',f'mov rax, [rcx+{instance:#x}]','test rax, rax');g.branch('jne','store')
    call=g.row();raw=bytes.fromhex(call['bytes']);at=int(call['va'],16)
    if len(raw)!=5 or raw[0]!=0xe8 or call['text']!=f'call {at+5+int.from_bytes(raw[1:],"little",signed=True):#x}':raise ValueError('montageSetter.null-call')
    g.take('int3');g.mark('store')
    g.take(('movss' if mode=='single' else 'mov')+f' [rax+{field:#x}], {value}','add rsp, 0x28','ret');g.finish()
    return dict(fieldOffset=field,storedBytes=1 if mode=='byte' else 8 if mode=='qword' else 4,evidenceBoundary='conditional',condition='Valid typed nonnull instance and ordinary incoming scalar; complete field store and frame return. Null-helper effects and caller/owner selection are separate.')

def unmanaged4(image,record,offsets):
    label='unmanagedDword';cur,rem,adv,used=(offsets[k] for k in ('currentPtr','bufferLength','advancedCount','consumed'))
    expected=[b'\x48\x89\x5c\x24\x08',b'\x48\x89\x74\x24\x10',b'\x57',b'\x48\x83\xec\x20',b'\x83\x79'+bytes((rem,4)),b'\x48\x8b\xf9',None,
        b'\x48\x8b\x5f'+bytes((cur,)),b'\x8b\x1b',b'\x8b\x77'+bytes((rem,)),b'\x83\xc6\xfc',None,b'\x48\x83\x47'+bytes((cur,4)),
        b'\x83\x47'+bytes((adv,4)),b'\x83\x47'+bytes((used,4)),b'\x89\x77'+bytes((rem,)),b'\x48\x8b\x74\x24\x38',b'\x8b\xc3',b'\x48\x8b\x5c\x24\x30',b'\x48\x83\xc4\x20',b'\x5f',b'\xc3']
    image.check_windows([record['window']],label=label);scalar.program_extent(record['instructions'],record['window'],label);scalar.program(image,record['instructions'],expected,label)
    for i,prefix in ((6,b'\x0f\x8c'),(11,b'\x0f\x88')):
        at,raw=record['instructions'][i];raw=bytes.fromhex(raw)
        scalar.need(label,'cold guard',(6,prefix),(len(raw),raw[:2]))
        target=at+6+int.from_bytes(raw[2:],'little',signed=True)
        scalar.need(label,'cold guard outside buffered program',False,record['window']['startRva']<=target<record['window']['endRva'])
    return dict(bufferedWireBytes=4,normalFrameAndReturnChecked=True,condition='Sufficient contiguous selected input, valid disjoint reader/storage and ordinary managed helper conditions; cold refill and failure effects remain separate.')

def validate_fields(image,pins,selected):
 build=Build(image,pins);base=image.pe.image_base;offsets=scalar.reader_offsets(image,'montage');recorder=vector_recorder(image);records=[]
 for observation in selected:
  name=observation['type'];wrapper=build.wrappers[observation['wrapper']];rows=[]
  if wrapper.wrapped_type!=name or [[m.name,m.declared_type,m.kind] for m in wrapper.members]!=observation['members']:raise ValueError('montage.native:field-declarations:'+name)
  method,=[m for m in image.metadata.methods_for(image.metadata.types[wrapper.type_definition]) if image.metadata.string(m.name_index)=='Deserialize'];entry=image.method_pointer_va(method)
  if entry!=base+observation['entry'] or sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(entry-base)['ranges'])!=sorted((w['startRva'],w['endRva']) for w in observation['windows']):raise ValueError('montage.native:complete-reader-ownership:'+name)
  for window in observation['windows']:rows+=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(base+window['startRva'],window['endRva']-window['startRva']),base+window['startRva'])
  owned=[(base+w['startRva'],base+w['endRva']) for w in observation['windows']]
  for window in observation['windows']:
   raw=image.pe.bytes_at_va(base+window['startRva'],window['endRva']-window['startRva'])
   if hashlib.sha256(raw).hexdigest().upper()!=window['sha256']:raise ValueError('current observed owned bytes differ')
  for row in rows:
   if image.pe.bytes_at_va(int(row['va'],16),len(bytes.fromhex(row['bytes'])))!=bytes.fromhex(row['bytes']):raise ValueError('instruction bytes differ')
  tails={int(r['va'],16):{'target':t['target']} for r in rows if (t:=control_transfer(r))['kind']=='jump' and not any(a<=t['target']<b for a,b in owned)}
  flow=check_reference_origins(rows,entry=base+observation['entry'],owned_ranges=owned,incoming_registers={'rcx':'reader','rdx':'holder'},incoming_stack_slots={},selected_call_returns={},tail_exits=tails)
  inline={}
  for i,row in enumerate(rows):
   if not row['text'].startswith(f"cmp dword [rbx+{offsets['bufferLength']:#x}], "):continue
   width=int(row['text'].rsplit(' ',1)[1],16)
   if width not in (16,32,36):continue
   part=rows[i:i+28];writes=[(j,r) for j,r in enumerate(part) if r['text'].startswith('movups [rax+')]
   if not writes:continue
   j,store=writes[0];slot=int(store['text'].split('+',1)[1].split(']',1)[0],16)
   matches=[m for m in wrapper.members if _setter_metadata(image,build.wrappers,m)[4]==slot]
   if len(matches)!=1:raise ValueError('typed inline field identity ambiguous')
   member=matches[0];context=_setter_metadata(image,build.wrappers,member)[0];declared=member.declared_type
   definition=context.index.types[declared];size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*definition.index)
   if not context.is_value_type(declared) or image.pe.u32_at_va(size)-16!=width:raise ValueError('inline managed field extent differs')
   end=j+1 if width==16 else next(k for k,r in enumerate(part) if k>j and r['text'].startswith(f'movups [rax+{slot+16:#x}]'))+1
   if width==36:end=next(k for k,r in enumerate(part) if k>=end and r['text']==f'mov [rax+{slot+32:#x}], ebp')+1
   part=part[:end]
   if flow['registerOrigins'][int(part[0]['va'],16)]['rbx']!=['reader'] or flow['registerOrigins'][int(part[1]['va'],16)]['rdi']!=['holder']:raise ValueError('inline source reader/holder entry origin differs')
   call=next(r for r in part if r['text'].startswith('call '));advance=int(call['text'].split()[1],16)
   advance_record=recorder(advance-base,fragments=True);scalar.advance_source(image,advance_record,offsets,'montage.inline.advance')
   holder=context.field(wrapper.name+'::__instance')
   if holder!=(wrapper.name,name,16):raise ValueError('inline typed holder differs')
   proof=check_inline_copy(part,width=width,field=slot,remaining=offsets['bufferLength'],current=offsets['currentPtr'],instance=holder[2],advance=advance,reader_setup=any(r['text']=='mov rcx, rbx' for r in part[j+1:]))
   inline[member.name]=dict(start=i,end=rows.index(part[-1]),rows=part,proof=proof,advanceSource=advance_record)
  fields=[];previous=-1
  for member in wrapper.members:
   _,declaring,_,field,slot,setter_method=_setter_metadata(image,build.wrappers,member);pointer=image.method_pointer_va(setter_method)
   field_result=dict(name=member.name,declaredType=member.declared_type,kind=member.kind,fieldOffset=slot,status='refused');fields.append(field_result)
   try:
    if member.name in inline:
     component=inline[member.name]
     if component['end']<=previous:raise ValueError('inline field order differs')
     field_result.update(status='selected-buffered-inline-source-and-owned-store',component=component);previous=component['end'];continue
    calls=[i for i,r in enumerate(rows) if r['text']==f'call {pointer:#x}' or r['text']==f'jmp {pointer:#x}']
    if len(calls)!=1 or calls[0]<=previous:raise ValueError('ordered setter count/order differs')
    end=calls[0];block=rows[previous+1:end+1];reads=[r for r in block[:-1] if r['text'].startswith('call ')]
    if not reads:raise ValueError('field has no read call')
    read=reads[-1];target=int(read['text'].split()[1],16);read_at=int(read['va'],16);state=flow['registerOrigins'][read_at]
    if state['rcx']!=['reader']:raise ValueError('actual source reader argument differs')
    transfer=block[block.index(read)+1:-1];receiver=transfer[0]['text'].split()[1].rstrip(',')
    setup=block[:block.index(read)]
    changes=[r for r in setup if _writes_register(r,receiver)]
    if not changes or receiver not in ('rbx','rbp','rsi','rdi','r12','r13','r14','r15'):raise ValueError('nonvolatile field receiver missing')
    load=changes[-1];match=re.fullmatch(r'mov '+receiver+r', \[(rbx|rbp|rsi|rdi|r1[2-5])\]',load['text'])
    if not match or flow['registerOrigins'][int(load['va'],16)][match[1]]!=['holder']:raise ValueError('actual field receiver is not loaded from entry holder')
    value4=member.declared_type=='Beyond.Gameplay.Core.GameplayTag'
    mode={'bool':'byte','scalar32':'dword','enum':'dword','scalar64':'qword','float32':'single'}.get(member.kind,'dword' if value4 else None)
    move='movzx edx, al' if mode=='byte' else 'mov edx, eax' if mode=='dword' else 'movaps xmm1, xmm0' if mode=='single' else 'mov rdx, rax'
    if [r['text'] for r in transfer[:5]]!=[f'test {receiver}, {receiver}',transfer[1]['text'],'xor r8d, r8d',move,f'mov rcx, {receiver}']:raise ValueError('unchanged returned field transfer differs')
    branch=bytes.fromhex(transfer[1]['bytes'])
    if not (len(branch)==2 and branch[0]==0x74 or len(branch)==6 and branch[:2]==b'\x0f\x84'):raise ValueError('field null guard differs')
    for row in transfer[5:]:
     if not (re.fullmatch(r'mov (rbx|rsi|rdi|rbp), \[rsp\+0x[0-9a-f]+\]',row['text']) or re.fullmatch(r'movaps xmm[67], \[rsp\+0x[0-9a-f]+\]',row['text']) or re.fullmatch(r'add rsp, 0x[0-9a-f]+',row['text']) or row['text'] in ('pop rdi','pop rbx')):raise ValueError('unexpected effect between read and setter')
    setter=recorder(pointer-base)
    decoded=decode_type_data_initialization_instructions(image.mapper,image.pe.bytes_at_va(pointer,setter['window']['endRva']-setter['window']['startRva']),pointer)
    if member.kind in ('list','object','string') and not value4:
     if decoded[3]['text'].startswith('jne '):parameter_setter(image,setter['instructions'],name='path',slot=slot,width=8,label='montage.reference')
     else:prove_reference_setter_rows(decoded,slot=16,field=slot)
    else:scalar_setter(decoded,field=slot,mode=mode)
    setup=block[:block.index(read)+1];typed=None
    if member.kind in ('list','object','enum'):
     method='ReadPackable' if member.kind=='list' else 'ReadUnmanaged' if member.kind=='enum' or value4 else 'ReadValue'
     typed=typed_source_context(image,setup[:-1],field=member.name,method=method,argument=member.declared_type)
    leaf=dict(status='child-wire-unproved')
    try:
     native=recorder(target-base,fragments=True)
     if member.kind=='bool':scalar.boolean_source(image,native,offsets,'montage.bool')
     elif member.kind=='scalar32':scalar.integer_source(image,native,offsets,'montage.int')
     elif member.kind=='scalar64':scalar.integer_source(image,native,offsets,'montage.long',width=8)
     elif member.kind=='float32':primitive_param.single_source(image,native,offsets)
     elif member.kind=='string':build.prove_pooled_string_target(target)
     elif member.kind=='enum' or value4:
      context=_setter_metadata(image,build.wrappers,member)[0];definition=context.index.types[member.declared_type]
      if member.kind=='enum':
       declared=context.field(member.declared_type+'::value__')[1]
       if declared!='int':raise ValueError('selected montage enum backing differs')
      else:
       size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*definition.index)
       if not context.is_value_type(member.declared_type) or image.pe.u32_at_va(size)!=20:raise ValueError('selected GameplayTag managed value4 extent differs')
       declared_fields=[f for f in image.metadata.fields_for(definition) if not context.field_attributes(f.type_index)&16]
       if len(declared_fields)!=1 or context.field(member.declared_type+'::'+image.metadata.string(declared_fields[0].name_index))!=(member.declared_type,'int',16):raise ValueError('selected GameplayTag signed value4 field differs')
      if value4:unmanaged4(image,native,offsets)
      else:scalar.integer_source(image,native,offsets,'montage.enum')
     else:raise ValueError('independent typed child source gate required')
     leaf=dict(status='current-source-validated',source=native)
    except (KeyError,ValueError) as error:leaf['diagnostic']=str(error)[:1000]
    field_result.update(status='typed-ordered-read-and-owned-unchanged-store',readRva=read_at-base,targetRva=target-base,transfer=transfer,setter=setter,typedContext=typed,leaf=leaf)
    previous=end
   except (KeyError,ValueError,IndexError,StopIteration) as error:field_result['diagnostic']=str(error)[:1400]
  setters=[image.method_pointer_va(image.metadata.methods[m.method_index]) for m in wrapper.members]
  first=next(f for f in fields if 'readRva' in f)
  register=next(r['text'].split(', ')[1] for r in reversed(rows[:next(i for i,r in enumerate(rows) if int(r['va'],16)==base+first['readRva'])]) if r['text'].startswith('mov rcx, '))
  header,_,_,_=select_calls(normal_source_rows(rows),len(wrapper.members),setters,reader_register=register,prefix_count=1)
  at=rows.index(header);g=BranchGrammar(rows[at:at+2],label='montage.count');g.take(header['text']);mismatch=g.branch('jne')['target'];g.finish()
  header_candidates=[]
  for i,row in enumerate(rows[:at]):
   if row['text'].startswith('call ') and i>=3 and rows[i+1]['text']=='test al, al':header_candidates.append(i)
  if len(header_candidates)!=1:raise ValueError('owning object-header source ambiguous')
  i=header_candidates[0];call=rows[i];setup=rows[i-3:i]
  slot_match=re.fullmatch(r'lea rdx, \[rsp\+(0x[0-9a-f]+)\]',setup[0]['text'])
  if not slot_match or [r['text'] for r in setup[1:]]!=[f'mov byte [rsp+{slot_match[1]}], 0x0',f'mov rcx, {register}']:raise ValueError('owning header output setup differs')
  slot=slot_match[1]
  if flow['registerOrigins'][int(call['va'],16)]['rcx']!=['reader']:raise ValueError('object header reader origin differs')
  compare=header['text']
  if f'[rsp+{slot}]' not in compare:
   low=compare.split(' ',1)[1].split(',')[0];full={'sil':'esi','bl':'ebx','dil':'edi'}.get(low)
   if not full or rows[at-1]['text']!=f'movzx {full}, byte [rsp+{slot}]':raise ValueError('count does not compare same returned header byte')
  g=BranchGrammar(rows[i+1:i+3],label='montage.header');g.take('test al, al');null=g.branch('je')['target'];g.finish()
  target=int(call['text'].split()[1],16);header_source=recorder(target-base,fragments=True);primitive_param.object_header_source(image,header_source,offsets)
  header_proof=dict(memberCount=len(wrapper.members),countInstruction=header,mismatchTarget=mismatch,nullTarget=null,headerSource=header_source,headerCall=call,outputStackSlot=slot,condition='Selected normal nonnull matching wrapper and sufficient contiguous input; helper/allocation/cold paths remain separate')
  records.append(dict(type=name,wrapper=wrapper.name,fields=fields,headerProof=header_proof,localControl={k:v for k,v in flow.items() if k!='registerOrigins'},ownedWindows=observation['windows']))
  for field in fields:
   if field['status']=='refused':raise ValueError('montage.native:field='+name+'.'+field['name']+':'+field.get('diagnostic','refused'))
   if 'component' in field:continue
   if field['kind']=='object' and field['declaredType'] in {r['type'] for r in selected}:build.prove_reader_clone_target(base+field['targetRva'],'MemoryPack.MemoryPackReader.ReadValue',result_abi='reference')
   elif field['kind']=='list':build.prove_reader_clone_target(base+field['targetRva'],'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
   elif field.get('leaf',{}).get('status')!='current-source-validated':raise ValueError('montage.native:scalar-source='+name+'.'+field['name']+':'+field.get('leaf',{}).get('diagnostic','refused'))
 return records
