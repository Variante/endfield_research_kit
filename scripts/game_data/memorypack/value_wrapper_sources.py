"""Prove source-return flow to named inline fields of a value wrapper.

The complete compiled normal program must preserve the incoming reader and
derive every stored destination from the exact wrapper-reference argument.
This proves stored fields under the selected source profile, not a live call.
"""
import re
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets,runtime_type_name
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack import named_native_records as named

ROOTS={r:r for r in ['rax','rbx','rcx','rdx','rsi','rdi','rbp','rsp',*(f'r{n}' for n in range(8,16))]}
for r in ['rax','rbx','rcx','rdx','rsi','rdi','rbp','rsp']:
 ROOTS['e'+r[1:]]=r
for r,aliases in [('rax',['ax','al','ah']),('rbx',['bx','bl','bh']),('rcx',['cx','cl','ch']),('rdx',['dx','dl','dh']),('rsi',['si','sil']),('rdi',['di','dil']),('rbp',['bp','bpl']),('rsp',['sp','spl'])]:
 ROOTS.update({a:r for a in aliases})
for n in range(8,16):ROOTS.update({f'r{n}d':f'r{n}',f'r{n}w':f'r{n}',f'r{n}b':f'r{n}'})

def validate_inline_wrapper_fields(image,source,record,*,label,fail):
 def bad(check,expected,actual):fail('inline-value-wrapper-'+check,expected,actual)
 metadata,pe=image.metadata,image.pe;table=int(image.registration['types'],16)
 def raw_type(index):return pe.bytes_at_va(pe.u64_at_va(table+index*8),16)
 def type_name(index):return runtime_type_name(pe,metadata,pe.u64_at_va(table+index*8))
 wrapper=derive_from_image(image).get(record['wrapperTypeDefinition']);runtime=metadata.types[record['runtimeTypeDefinition']]
 if (wrapper is None or not wrapper.wrapped_is_value_type or wrapper.inherited_members
     or wrapper.name!=record['wrapperTypeName'] or wrapper.wrapped_type!=record['runtimeTypeName']
     or image.type_name(runtime.index)!=record['runtimeTypeName']
     or metadata.metadata_type_name(runtime.parent_index)!='System.ValueType'):
  bad('runtime','noninherited inline value wrapper',record['runtimeTypeName'])
 members=record['members']
 if [(m['fieldName'],m['declaredType'],m['setterMethodIndex']) for m in members]!=[(m.name,m.declared_type,m.method_index) for m in wrapper.members]:
  bad('members','current generated ordered fields',members)
 if [m['kind'] for m in members]!=source['anonymousReadOrder'][record['sourceReadOrder']]:bad('read-order','current source order',members)
 if (record['readerMethod'] not in source['methods'] or record['readerMethod'][1]!=wrapper.name
     or record['readerMethod'][2]!='Deserialize'):
  bad('reader-owner','selected source wrapper Deserialize',record['readerMethod'])
 method=metadata.methods[record['readerMethod'][0]];image.validate_method_row(record['readerMethod'],label=label)
 params=list(metadata.parameters_for(method));result=raw_type(method.return_type);args=[raw_type(p.type_index) for p in params]
 if (not method.flags&0x10 or len(args)!=2 or len(result)!=16 or result[10]!=1 or result[11]&0x7f
     or any(len(r)!=16 or r[11]&0x7f!=0x20 for r in args) or args[0][10]!=0x11
     or args[1][10]!=0x12 or type_name(params[0].type_index)!='MemoryPack.MemoryPackReader'
     or int.from_bytes(args[1][:8],'little')!=record['wrapperTypeDefinition']):bad('abi','static void reader and exact ref wrapper',args)
 fields=[f for f in metadata.fields_for(metadata.types[record['wrapperTypeDefinition']]) if metadata.string(f.name_index)=='__instance']
 if len(fields)!=1:bad('instance-field','one __instance',len(fields))
 value=raw_type(fields[0].type_index)
 if len(value)!=16 or int.from_bytes(value[8:10],'little')&0x10 or value[10]!=0x11 or int.from_bytes(value[:8],'little')!=runtime.index:bad('instance-type',runtime.index,value.hex())
 inline=runtime_type_field_offsets(metadata,pe,image.registration,record['wrapperTypeDefinition'])['__instance']
 offsets=runtime_type_field_offsets(metadata,pe,image.registration,runtime.index)
 if inline<16 or any(offsets[m['fieldName']]<16 for m in members):bad('offsets','selected boxed and wrapper headers',offsets)
 physical={m['fieldName']:inline+offsets[m['fieldName']]-16 for m in members}
 runtime_fields={metadata.string(f.name_index):f for f in metadata.fields_for(runtime)}
 for member in members:
  field=runtime_fields.get(member['fieldName'])
  raw=raw_type(field.type_index) if field is not None else b''
  if (len(raw)!=16 or int.from_bytes(raw[8:10],'little')&0x10
      or type_name(field.type_index)!=member['declaredType']
      or (member['kind'],member['declaredType']) not in {
          ('curve','UnityEngine.AnimationCurve'),('scalar32','float'),('byte','bool'),('byte-payload','string')}):
   bad('runtime-field-type','exact supported nonstatic stored member',member)
 normal=next(w for w in source['codeWindows'] if w['startRva']==record['readerMethod'][3]);program=record['inlineValueFlow']['normalProgram']
 if (record['inlineValueFlow'].get('mode')!='reader-and-inline-wrapper-field-flow' or not program
     or program[0][0]!=normal['startRva'] or program[-1][0]+len(bytes.fromhex(program[-1][1]))!=normal['endRva']
     or any(a[0]+len(bytes.fromhex(a[1]))!=b[0] for a,b in zip(program,program[1:]))):bad('program','entire contiguous normal body',program)
 image.check_instruction_windows(program,label=label)
 refs={'rcx':('reader',0),'rdx':('wrapper-ref',0)};values={};seen=set();sources={m['sourceCall']['rva']:m for m in members};destinations={m['assignment']['rva']:m for m in members}
 if len(sources)!=len(members) or len(destinations)!=len(members):bad('unique-operations','one source and destination per member',members)
 volatile={'rax','rcx','rdx','r8','r9','r10','r11'}
 contexts={m.get('sourceContextInstructionRva'):m for m in members if m['kind']=='curve'}
 for at,hex_value in program:
  rows=image.mapper.decode_x64_subset(bytes.fromhex(hex_value),pe.image_base+at,stop_offset=len(bytes.fromhex(hex_value)))
  if len(rows)!=1 or rows[0]['text'].startswith('db'):bad('instruction','one understood instruction',[at,hex_value,rows])
  row=rows[0];text=row['text']
  if text.startswith('call '):
   source_member=sources.get(at)
   if source_member is not None:
    named.check_call(image,source_member['sourceCall'],label=label,fail=bad)
    if refs.get('rcx')!=('reader',0):bad('source-reader','preserved incoming reader',[at,refs])
    context=next((c for c in source['nestedContexts'] if c['instructionRva']==source_member.get('sourceContextInstructionRva')),None)
    if source_member['kind']=='curve':
     if context is None or refs.get('rdx')!=('typed-context',source_member['fieldName']):bad('typed-curve','closed AnimationCurve context passed in RDX',source_member)
     named.check_typed_context(image,context,source_member['declaredType'],label=label,fail=bad)
   for register in volatile:refs.pop(register,None);values.pop(register,None)
   values.pop('xmm0',None)
   if source_member is not None:values['xmm0' if source_member['declaredType']=='float' else 'rax']=source_member['fieldName']
   continue
  planned=destinations.get(at)
  if planned is not None:
   store=re.fullmatch(r'(mov|movss) \[(\w+)(?:\+0x([0-9a-f]+))?\], (\w+)',text)
   if store is None:bad('store','full scalar/reference store',text)
   op,base,disp,value_register=store.groups();kind=refs.get(base);delta=int(disp or '0',16)
   width=4 if op=='movss' and value_register=='xmm0' else 8 if value_register==ROOTS.get(value_register) else 1 if value_register=='al' else None
   expected=8 if planned['kind'] in {'curve','byte-payload'} else 4 if planned['declaredType']=='float' else 1 if planned['declaredType']=='bool' else None
   value_key=value_register if op=='movss' else ROOTS.get(value_register)
   assignment=planned['assignment'];name=planned['fieldName']
   actual_offset=(kind[1]+delta) if kind and kind[0] in {'wrapper','field-address'} else None
   if (width!=expected or values.get(value_key)!=name or actual_offset!=physical[name]
       or assignment['rawHex']!=hex_value or assignment['fieldOffset']!=physical[name]
       or assignment['fieldOwnerTypeDefinition']!=runtime.index):bad('destination',{'name':name,'offset':physical[name],'width':expected},[text,kind,values,assignment])
   seen.add(name)
  moved=re.fullmatch(r'mov (\w+), (\w+)',text)
  load=re.fullmatch(r'mov (\w+), \[(\w+)\]',text)
  lea=re.fullmatch(r'lea (\w+), \[(\w+)\+0x([0-9a-f]+)\]',text)
  write=(row.get('write') or {}).get('register');root=ROOTS.get(write,write)
  origin=None;origin_value=None
  if moved and moved[1]==ROOTS.get(moved[1]) and moved[2]==ROOTS.get(moved[2]):origin=refs.get(moved[2]);origin_value=values.get(moved[2])
  if load and load[1]==ROOTS.get(load[1]) and refs.get(load[2])==('wrapper-ref',0):origin=('wrapper',0)
  if lea and lea[1]==ROOTS.get(lea[1]) and refs.get(lea[2])==('wrapper',0):origin=('field-address',int(lea[3],16))
  if root:
   refs.pop(root,None);values.pop(root,None)
   if origin:refs[root]=origin
   if origin_value:values[root]=origin_value
  if at in contexts:
   member=contexts[at]
   context=next((c for c in source['nestedContexts'] if c['instructionRva']==at),None)
   if (context is None or hex_value!=context.get('instructionHex') or root!='rdx'):
    bad('context-instruction','exact typed context load into RDX',[at,hex_value])
   refs['rdx']=('typed-context',member['fieldName'])
  if text.startswith(('jmp ','ret')) and len(seen)!=len(members):bad('control-flow','all normal field stores before terminal',text)
 if seen!=set(physical):bad('coverage',sorted(physical),sorted(seen))
 return [{'fieldName':m['fieldName'],'kind':m['kind']} for m in members]
