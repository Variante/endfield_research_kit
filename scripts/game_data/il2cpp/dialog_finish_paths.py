"""Exact ordinary inlined dialog paths; replacement and child-call effects stay conditional."""
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.memorypack.null_param import exact
from scripts.game_data.il2cpp.initializer_control import control_transfer

def rip(g,prefix):
 row=g.row();raw=bytes.fromhex(row['bytes']);p=bytes.fromhex(prefix)
 if len(raw)!=7 or raw[:3]!=p:raise ValueError('dialogInline.rip-width')
 return dict(instruction=row,cell=int(row['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True))

def finish(rows,pointer,*,exit_dialog,fields,carrier_null=True):
 g=_Path(rows);g.at=pointer;g.take('sub rsp, 0x38');root=rip(g,'488b05');guard_load(g,'4c8b50','r10','rax');g.take('test r10, r10');g.branch(4,carrier_null)
 if not carrier_null:guard_load(g,'4d8b9a','r11','r10');g.take('test r11, r11');g.branch(4,True)
 for name,register,prefix in (('finishType','r9d','448989'),('finishId','r8d','448981')):
  if name=='finishId':exact(g,'xor r9d, r9d','4533c9')
  offset=fields[name];exact(g,f'mov [rcx+{offset:#x}], {register}',prefix+offset.to_bytes(4,'little').hex())
 offset=fields['isSkipping'];exact(g,f'mov r8b, [rcx+{offset:#x}]','448a81'+offset.to_bytes(4,'little').hex());g.take('add rsp, 0x38');tail=g.row()
 if control_transfer(tail)!=dict(kind='jump',target=exit_dialog):raise ValueError('dialogInline.ExitDialog-tail')
 return dict(selectedInstructions=g.seen,root=root,finishIdArgument='incoming R8D',finishTypeArgument='incoming R9D',exitArguments=dict(rcx='original manager',rdx='original dialog string',r8b='stored isSkipping byte',r9='zero MethodInfo'),entryRspRestored=True,condition='Carrier pointer null or its tested code slot null, valid original manager and stable disjoint storage, ordinary tail callee. No SetFinishId call or its replacement dispatch is inferred.')

def getter(rows,pointer,*,field,carrier_null=True):
 g=_Path(rows);g.at=pointer;g.take('sub rsp, 0x28');root=rip(g,'488b05');g.take('mov r9, rcx');guard_load(g,'488b48','rcx','rax');g.take('test rcx, rcx');g.branch(4,carrier_null)
 if not carrier_null:guard_load(g,'488b81','rax','rcx');g.take('test rax, rax');g.branch(4,True)
 exact(g,f'mov rax, [r9+{field:#x}]','498b41'+bytes((field,)).hex());g.take('add rsp, 0x28','ret')
 return dict(selectedInstructions=g.seen,root=root,field=field,returnRegister='rax',entryRspRestored=True,condition='Original getter carrier/code absent, valid incoming CinematicSystem receiver and stable reference field. Replacement behavior remains separate.')

def check(rows,pointer,*,symbols,fields,carrier_null=True,outcome='contains'):
 if outcome not in ('missing','negative','contains','absent'):raise ValueError('dialogInline.unproved-outcome')
 g=_Path(rows);g.at=pointer;g.take('mov [rsp+0x8], rbx','push rdi','sub rsp, 0x20');flag=g.row();raw=bytes.fromhex(flag['bytes'])
 if len(raw)!=7 or raw[:2]!=bytes.fromhex('803d') or raw[-1]!=0:raise ValueError('dialogInline.metadata-flag')
 g.take('mov rdi, rdx','mov rbx, rcx');g.branch(5,True);root=rip(g,'488b05');guard_load(g,'488b48','rcx','rax');g.take('test rcx, rcx');g.branch(4,carrier_null)
 if not carrier_null:guard_load(g,'488b81','rax','rcx');g.take('test rax, rax');g.branch(4,True)
 klass=rip(g,'488b0d');exact(g,'mov [rsp+0x40], 0x0','48c744244000000000');g.call(symbols['warm']);exact(g,'xor ecx, ecx','33c9');g.call(symbols['player']);g.take('test rax, rax');g.branch(4,False)
 for name,register,prefix in (('cinematic','rax','488b40'),('dictionary','rcx','488b48')):
  offset=fields[name];exact(g,f'mov {register}, [rax+{offset:#x}]',prefix+bytes((offset,)).hex());g.take(f'test {register}, {register}');g.branch(4,False)
 dictionary=rip(g,'4c8b0d');exact(g,'lea r8, [rsp+0x40]','4c8d442440');offset=fields['dialogId'];exact(g,f'mov rdx, [rbx+{offset:#x}]','488b93'+offset.to_bytes(4,'little').hex());g.call(symbols['lookup']);g.take('test al, al');g.branch(4,outcome=='missing');contains=None
 if outcome!='missing':
  offset=fields['finishNum'];exact(g,f'cmp [rbx+{offset:#x}], 0x0','83bb'+offset.to_bytes(4,'little').hex()+'00');g.branch(12,outcome=='negative')
  if outcome!='negative':
   g.take('mov rax, [rsp+0x40]','test rax, rax');g.branch(4,False);offset=fields['finishList'];exact(g,f'mov rcx, [rax+{offset:#x}]','488b48'+bytes((offset,)).hex());g.take('test rcx, rcx');g.branch(4,False);contains=rip(g,'4c8b05');offset=fields['finishNum'];exact(g,f'mov edx, [rbx+{offset:#x}]','8b93'+offset.to_bytes(4,'little').hex());g.call(symbols['contains']);g.take('test al, al');g.branch(4,outcome=='absent')
 truth=outcome in ('negative','contains');exact(g,'xor r8d, r8d','4533c0')
 if truth:exact(g,'lea rdx, [r8+0x1]','418d5001');g.jump()
 else:exact(g,'xor edx, edx','33d2')
 g.take('mov rcx, rbx');g.call(symbols['result']);g.jump();g.take('mov rbx, [rsp+0x30]','add rsp, 0x20','pop rdi','ret')
 return dict(selectedInstructions=g.seen,root=root,playerClass=klass,dictionaryContext=dictionary,listContext=contains,resultBits=int(truth),resultReceiver='original condition',entryRspRestored=True,condition='Initialized metadata; tested replacement carrier/code absent; nonnull compatible player, cinematic, dictionary, lookup result and list where reached; matching helper MethodInfos and ordinary ABI-preserving calls; valid stable disjoint frames/storage. Live history, collection contents, replacement and whole mission execution remain separate.')


def guard_load(g,prefix,register,base):
 row=g.row();raw=bytes.fromhex(row['bytes']);encoded=bytes.fromhex(prefix);size=1 if encoded[-1]&0xc0==0x40 else 4
 if len(raw)!=3+size or raw[:3]!=encoded:raise ValueError('dialogInline.guard-load-width')
 offset=int.from_bytes(raw[3:],'little',signed=True)
 if offset<0 or row['text']!=f'mov {register}, [{base}+{offset:#x}]':raise ValueError('dialogInline.guard-load-operands')
 return offset

def prove_claim(index,body,kind):
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import scalar_param_native as scalar
 image=index.image;ctx=NativeReferenceContext(image);md=image.metadata;label='dialogInline.'+kind
 def need(name,wanted,actual):scalar.need(label,name,wanted,actual)
 def method(owner,name,result,args):
  methods=[m for m in md.methods_for(ctx.index.types[owner]) if md.string(m.name_index)==name];need('methodCount.'+owner+'.'+name,1,len(methods));m=methods[0];scalar.owned_method_abi(image,ctx,m.index,ctx.index.types[owner].index,result,args,label+'.'+name);return m
 def field(owner,name,declared):
  matches=[f for f in md.fields_for(ctx.index.types[owner]) if md.string(f.name_index)==name];need('fieldCount.'+owner+'::'+name,1,len(matches));need('instanceField.'+name,0,ctx.field_attributes(matches[0].type_index)&16);value=ctx.field(owner+'::'+name);need('fieldType.'+name,declared,value[1]);need('fieldOffset.'+name,True,value[2]>=16);return value[2]
 def owned(source,proofs):
  ranges=[r['runtimeTriple'][:2] for r in image.unwind_index.family(source.pointer-image.pe.image_base)['ranges']];rows={int(r['va'],16):r for r in source.all_rows}
  for proof in proofs:
   for at in proof['selectedInstructions']:
    raw=bytes.fromhex(rows[at]['bytes']);need('selectedNativeBytes',raw,image.pe.bytes_at_va(at,len(raw)));need('selectedOwnedInstruction',True,any(image.pe.image_base+a<=at and at+len(raw)<=image.pe.image_base+b for a,b in ranges))
 manager='Beyond.Gameplay.Core.DialogManager';cinematic='Beyond.Gameplay.CinematicSystem';condition='Beyond.Gameplay.CheckTalkOptionFinish';finish_type='Beyond.Gameplay.DialogEnums+DialogFinishType';result_type='Beyond.Gameplay.ConditionResult';info='Beyond.Gameplay.DialogFinishInfo';dictionary='System.Collections.Generic.Dictionary`2<string,'+info+'>'
 if kind=='finish':
  current=method(manager,'FinishDialog',('void',1,False),[('string',14,True),('int',8,False),(finish_type,17,False)]);need('selectedCaller',image.method_pointer_va(current),body.pointer);method(manager,'ExitDialog',('void',1,False),[('string',14,True),('bool',2,False)]);need('finishTypeBacking','int',ctx.field(finish_type+'::value__')[1]);fields=dict(finishId=field(manager,'m_finishId','int'),finishType=field(manager,'m_finishType',finish_type),isSkipping=field(manager,'<isSkipping>k__BackingField','bool'));exit_pointer=index.body(manager,'ExitDialog').pointer;paths=[finish(body.all_rows,body.pointer,exit_dialog=exit_pointer,fields=fields,carrier_null=n) for n in (True,False)];owned(body,paths);return paths
 need('claimKind','check',kind);current=method(condition,'Check',('void',1,False),[]);need('selectedCaller',image.method_pointer_va(current),body.pointer);method(cinematic,'get_dialogFinishInfos',(dictionary,21,True),[]);result=method('Beyond.Gameplay.GameCondition','set_result',('void',1,False),[(result_type,17,False)]);need('resultBacking','int',ctx.field(result_type+'::value__')[1]);need('falseValue',0,index.enum_member_id(result_type,'False'));need('trueValue',1,index.enum_member_id(result_type,'True'))
 player='Beyond.Gameplay.GamePlayer';getters=[m for m in md.methods_for(ctx.index.types['Beyond.Gameplay.GameInstance']) if md.string(m.name_index)=='get_player'];need('playerGetterCount',1,len(getters));player_getter=getters[0];need('staticPlayerGetter',(16,0,player),(player_getter.flags&16,player_getter.parameter_count,ctx.type_name(player_getter.return_type)));scalar.ordinary(image,ctx.type_pointer(player_getter.return_type),18,label+'.player',reference=True)
 fields=dict(cinematic=field(player,'cinematic',cinematic),dictionary=field(cinematic,'m_dialogFinishInfos',dictionary),dialogId=field(condition,'m_dialogId','string'),finishNum=field(condition,'m_finishNum','int'),finishList=field(info,'finishIds','System.Collections.Generic.List`1<int>'));calls=[control_transfer(r)['target'] for r in body.all_rows if r['text'].startswith('call 0x')];need('callCount',9,len(calls));symbols=dict(zip(('warm','player','lookup','contains','result'),calls[3:8]));need('typedPlayerTarget',image.method_pointer_va(player_getter),symbols['player']);need('typedResultTarget',image.method_pointer_va(result),symbols['result'])
 for key,name in (('lookup','System.Collections.Generic.Dictionary`2.TryGetValue'),('contains','System.Collections.Generic.List`1.Contains')):need('namedTarget.'+key,True,name in index.names_of(symbols[key]))
 paths=[check(body.all_rows,body.pointer,symbols=symbols,fields=fields,carrier_null=n,outcome=o) for n in (True,False) for o in ('missing','negative','contains','absent')];getter_body=index.body(cinematic,'get_dialogFinishInfos');getter_paths=[getter(getter_body.all_rows,getter_body.pointer,field=fields['dictionary'],carrier_null=n) for n in (True,False)];need('sameGuardRoot',1,len({p['root']['cell'] for p in [*paths,*getter_paths]}));owned(body,paths);owned(getter_body,getter_paths)
 for key,owner,name,args in (('dictionaryContext','System.Collections.Generic.Dictionary`2','TryGetValue',['string',info]),('listContext','System.Collections.Generic.List`1','Contains',['int'])):
  context=derive_typed_usage_context(image,int(paths[2][key]['instruction']['va'],16)-image.pe.image_base,label=label+'.'+key);need('closedContext.'+key,(6,owner,name,args,[]),(context['tag'],context['typeName'],context['methodName'],context['classArguments'],context['methodArguments']))
 return [*paths,*getter_paths]

def check_dialog_finish_claim(index,body,spec,*,kind):
 if spec is not True:return 'dialogInline.claim: expected=true actual='+repr(spec)[:100]
 try:prove_claim(index,body,kind)
 except (ValueError,KeyError,IndexError,TypeError,RuntimeError,OverflowError) as error:return str(error)[:1800]
 return None
