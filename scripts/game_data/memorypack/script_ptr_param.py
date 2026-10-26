"""Current initialized raw16 Param<LevelScriptPtr> source/store paths; no semantic mode claim."""
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.memorypack.null_param import exact

def path(rows,pointer,slots,symbols,offsets,*,allocated=False,null=False,refill=False):
 g=_Path(rows);g.at=pointer;calls={};allocation=None
 def take(*pairs):
  for text,raw in pairs:exact(g,text,raw)
 def call(name):
  calls[name]=g.rows[g.at]
  try:g.call(symbols[name])
  except ValueError as error:raise ValueError('scriptPtr.call:'+name+':expected='+str(symbols[name])+':row='+str(calls[name])) from error
 def nonnull(reg):g.take('test '+reg+', '+reg);g.branch(4,False)
 g.take('mov [rsp+0x18], rbx','push rdi','sub rsp, 0x30');flag=g.row();raw=bytes.fromhex(flag['bytes'])
 if len(raw)!=7 or raw[:2]!=b'\x80\x3d' or raw[-1]!=0:raise ValueError('scriptPtr.initialized-flag')
 g.take('mov rdi, rdx','mov rbx, rcx');g.branch(4,False)
 g.take('lea rdx, [rsp+0x40]');take(('mov [rsp+0x40], 0x0','c644244000'));g.take('mov rcx, rbx');call('header');g.take('test al, al');g.branch(4,null)
 if null:
  g.take('mov rcx, rdi');take(('mov [rdi], 0x0','48c70700000000'));call('barrier');g.take('nop');g.jump()
 else:
  g.take('mov [rsp+0x48], rsi');take(('cmp [rdi], 0x0','48833f00'));g.branch(4,allocated)
  if allocated:
   allocation=g.row();raw=bytes.fromhex(allocation['bytes'])
   if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x0d':raise ValueError('scriptPtr.allocation-class')
   call('allocate');g.take('mov rsi, rax');nonnull('rax');g.take('xor edx, edx','mov rcx, rax');call('constructor');g.take('mov rcx, rdi');take(('mov [rdi], rsi','488937'));call('barrier');g.take('nop');g.jump()
  take(('movzx esi, [rsp+0x40]','0fb6742440'),('cmp sil, 0x4','4080fe04'));g.branch(5,False)
  take((f'cmp [rbx+{offsets["bufferLength"]:#x}], 0x10','837b'+bytes((offsets['bufferLength'],16)).hex()));g.take('mov rsi, [rdi]');g.branch(12,refill)
  if refill:
   take(('xor r8d, r8d','4533c0'),('mov edx, 0x10','ba10000000'),('mov rcx, rbx','488bcb'));call('refill');g.take('nop');g.jump()
  take((f'mov rax, [rbx+{offsets["currentPtr"]:#x}]','488b43'+bytes((offsets['currentPtr'],)).hex()),('mov edx, 0x10','ba10000000'),('mov rcx, rbx','488bcb'),('movups xmm0, [rax]','0f1000'),('movups [rsp+0x20], xmm0','0f11442420'));call('advance');nonnull('rsi');g.take('mov rax, [rsi+0x10]');nonnull('rax')
  take(('movups xmm0, [rsp+0x20]','0f10442420'),('mov rcx, rbx','488bcb'),('movups [rax+'+hex(slots['constValue'])+'], xmm0','0f1140'+bytes((slots['constValue'],)).hex()))
  for field in ('idRef','paramSource'):
   g.take('mov rsi, [rdi]') if field=='idRef' else None
   call('integer');nonnull('rsi');g.take('xor r8d, r8d','mov edx, eax','mov rcx, rsi');call(field+'Setter');g.take('mov rsi, [rdi]','mov rcx, rbx') if field=='idRef' else None
  g.take('mov rdi, [rdi]','mov rcx, rbx');call('pool');nonnull('rdi');g.take('xor r8d, r8d','mov rdx, rax','mov rcx, rdi');call('pathSetter');g.take('mov rsi, [rsp+0x48]')
 g.take('mov rbx, [rsp+0x50]','add rsp, 0x30','pop rdi','ret')
 return dict(selectedInstructions=g.seen,allocation=allocation,calls=calls,allocated=allocated,null=null,refill=refill,rawConstantBytes=16,tailEncoding='two-int32-and-pool-index',condition='Initialized metadata, ordinary ABI and disjoint valid storage, normal compatible header/refill/advance/allocation/constructor/setter helpers. Cache/padding meaning, runtime selection and complete parent admission remain separate.')

import hashlib,json
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.memorypack import primitive_param as primitive,scalar_param_native as scalar,pooled_source_helper
from scripts.game_data.memorypack.vector_layout import vector_recorder

VALUE_TYPE='Beyond.Gameplay.Core.LevelScriptPtr'

def derive(image,pins,profile):
 base=image.pe.image_base;build=Build(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;wrapped='Beyond.Gameplay.Actions.Param`1<'+VALUE_TYPE+'>';w,=[w for w in build.wrappers.values() if w.wrapped_type==wrapped];methods={md.string(m.name_index):m for m in md.methods_for(md.types[w.type_definition])};slots=profile['ownedFieldSlots'];label='scriptPtrParam'
 scalar.need(label,'members',[('constValue',VALUE_TYPE),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type) for m in w.members]);scalar.need(label,'holder',(w.name,wrapped,16),ctx.field(w.name+'::__instance'));primitive.reader_abi(image,ctx,methods['Deserialize'],w)
 def record(method):
  pointer=image.method_pointer_va(method) if not isinstance(method,int) else method
  try:ranges=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(pointer-base)['ranges'])
  except ValueError as error:
   if not str(error).startswith('unwind-chain.entry-missing:'):raise
   leaf=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(pointer,512),pointer);end=max(int(r['va'],16)+len(bytes.fromhex(r['bytes'])) for r in leaf['rows']);ranges=[(pointer-base,end-base)]
  windows=[];rows=[]
  for a,b in ranges:
   raw=image.pe.bytes_at_va(base+a,b-a);rows+=image.body_index._decode(base+a,b-a);windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()))
  return dict(pointerRva=pointer-base,windows=windows,rows=rows,instructions=[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()] for r in rows])
 caller=record(methods['Deserialize']);rows=caller['rows'];target=lambda r:control_transfer(r)['target']
 def after(text):return target(next(rows[n+1] for n,r in enumerate(rows[:-1]) if r['text']==text and control_transfer(rows[n+1])['kind']=='call'))
 def before(text):return target(next(rows[n-1] for n,r in enumerate(rows) if n and r['text']==text))
 symbols=dict(header=before('test al, al'),advance=after('movups [rsp+0x20], xmm0'),integer=after('mov rsi, [rdi]'),idRefSetter=image.method_pointer_va(methods['set___idRef__']),paramSourceSetter=image.method_pointer_va(methods['set___paramSource__']),pathSetter=image.method_pointer_va(methods['set___path__']),pool=before('test rdi, rdi'),constructor=image.method_pointer_va(methods['.ctor']),allocate=before('mov rsi, rax'))
 symbols['barrier']=target(next(rows[n+1] for n,r in enumerate(rows[:-1]) if bytes.fromhex(r['bytes'])==b'\x48\x89\x37'))
 symbols['refill']=target(next(rows[n+1] for n,r in enumerate(rows[:-1]) if n>1 and r['text']=='mov rcx, rbx' and rows[n-1]['text']=='mov edx, 0x10' and rows[n-2]['text']=='xor r8d, r8d'))
 offsets=scalar.reader_offsets(image,label);paths=[path(rows,base+caller['pointerRva'],slots,symbols,offsets,allocated=a,null=n,refill=f) for a,n,f in ((False,False,False),(True,False,False),(False,True,False),(False,False,True))]
 allocation=derive_typed_usage_context(image,int(paths[1]['allocation']['va'],16)-base,label=label+'.wrapper');scalar.need(label,'allocation',w.name,allocation['typeName'])
 def primary(record):return dict(window=record['windows'][0],instructions=[r for r in record['instructions'] if record['windows'][0]['startRva']<=r[0]<record['windows'][0]['endRva']])
 integer=record(symbols['integer']);scalar.integer_source(image,primary(integer),offsets,label+'.integer');advance=vector_recorder(image)(symbols['advance']-base,fragments=True);scalar.advance_source(image,advance,offsets,label+'.advance');header=record(symbols['header']);primitive.object_header_source(image,primary(header),offsets)
 strings=pooled_source_helper.validate_on_image(image,symbols['pool'],pins);scalar.need(label,'pool-encoding','int32-pool-index',strings['wireEncoding'])
 owned={name:record(methods[name]) for name in ('.ctor','CreateInstance','GetValue','set___constValue__','set___idRef__','set___paramSource__','set___path__')}
 for name in ('idRef','paramSource','path'):
  scalar.owned_method_abi(image,ctx,methods['set___'+name+'__'].index,w.type_definition,('void',1,False),[('string',14,True) if name=='path' else ('int',8,False)],label+'.setter');scalar.parameter_setter(image,owned['set___'+name+'__']['instructions'],name=name,slot=slots[name],width=4,label=label+'.setter')
 load,=[r for r in owned['.ctor']['rows'] if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'];parameter=derive_typed_usage_context(image,int(load['va'],16)-base,label=label+'.parameter');scalar.need(label,'closed-Param',wrapped,parameter['typeName']);scalar.allocation_bridge(image,ctx,dict(allocationContext=parameter,ownedFieldSlots=slots,methods=owned),label+'.factory')
 constant=owned['set___constValue__'];expected=['4883ec28','488b4110','4885c0','7506',None,'cc','0f1002','0f1140'+bytes((slots['constValue'],)).hex(),'4883c428','c3'];scalar.program(image,constant['instructions'],[bytes.fromhex(v) if v else None for v in expected],label+'.constant');scalar.need(label,'constant-nonnull-target',int(constant['rows'][6]['va'],16),control_transfer(constant['rows'][3])['target']);scalar.need(label,'constant-null-call','call',control_transfer(constant['rows'][4])['kind']);scalar.owned_method_abi(image,ctx,methods['set___constValue__'].index,w.type_definition,('void',1,False),[(VALUE_TYPE,17,False)],label+'.constant')
 scalar.program(image,owned['GetValue']['instructions'],[b'\x48\x8b\x41\x10',b'\xc3'],label+'.getter');scalar.owned_method_abi(image,ctx,methods['GetValue'].index,w.type_definition,(wrapped,21,True),[],label+'.getter')
 fields=[(md.string(f.name_index),*ctx.field(VALUE_TYPE+'::'+md.string(f.name_index))[1:]) for f in md.fields_for(ctx.index.types[VALUE_TYPE]) if not ctx.field_attributes(f.type_index)&16];scalar.need(label,'value-fields',[('scriptId','ulong',16),('<levelId>k__BackingField','int',24)],fields);scalar.need(label,'value-type',True,ctx.is_value_type(VALUE_TYPE));definition=ctx.index.types[VALUE_TYPE];sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8);scalar.need(label,'boxed-size',32,image.pe.u32_at_va(sizes))
 eager=profile['registration'];scalar.need(label,'registered-pair',(wrapped,w.name),(eager['originalType'],eager['wrapperType']));validate_eager_wrap_registration(image,eager,label=label+'.registration');composition=profile['composition'];validate_registered_formatter_composition(image,composition,label=label+'.composition');scalar.need(label,'composition-bijection',[wrapped],[r['originalType'] for r in composition['registrations']])
 fmt=w.name+'+'+w.name.rsplit('.',1)[-1]+'Formatter';forward_method,=[m for m in md.methods_for(image.body_index.types[fmt]) if md.string(m.name_index)=='Deserialize'];forward=record(forward_method);calls=[target(r) for r in forward['rows'] if control_transfer(r)['kind']=='call'];scalar.need(label,'forward-helper-count',2,len(calls));forward_proof=prove_zero_wrapper_forwarder(forward['rows'],dict(metadataInit=calls[0],classInit=calls[1]),base+caller['pointerRva'],label=label+'.forward')
 def rip(row):return int(row['va'],16)+7+int.from_bytes(bytes.fromhex(row['bytes'])[3:],'little',signed=True)
 class_row,=[r for r in forward['rows'] if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'];init_row,=[r for r in forward['rows'] if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8d\x0d'];scalar.need(label,'forward-class-cell',rip(class_row),rip(init_row));forward_context=derive_typed_usage_context(image,int(class_row['va'],16)-base,label=label+'.forward-type');scalar.need(label,'forward-class',w.name,forward_context['typeName'])
 return json.loads(json.dumps(dict(wrappedType=wrapped,wrapperName=w.name,codecKind='Param<LevelScriptPtr>',memberCount=4,rawSize=16,pathEncoding='int32-pool-index',readerOffsets=offsets,callerMethod=[methods['Deserialize'].index,w.name,'Deserialize',caller['pointerRva']],caller=caller,paths=paths,wrapperAllocation=allocation,parameterAllocation=parameter,ownedMethods=owned,integerSource=integer,advanceSource=advance,headerSource=header,pooledPath=strings,valueFields=fields,forwarder=forward,forwarderContext=forward_context,forwarderProgram=forward_proof,evidenceBoundary=dict(direct='Current typed raw16 constant copy and stores, UInt64 scriptId/signed Int32 stored levelId, bindings/pool tail, null marker and reference factories/getter; registered concrete Param/wrapper declarations and forwarding program.',conditional='Initialized metadata, valid disjoint readable storage and ordinary ABI-preserving helpers, normal compatible generated reference formatter/wrapper route and sufficient contiguous input.',unresolved=['refill helper effects','live provider/cache/override selection','effective script resolution and current-script inference','meaning of four trailing copied bytes','whole-owner execution']))))
