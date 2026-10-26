"""Fresh current compact SubGame source components, below runtime selection."""
import hashlib,json,struct
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.memorypack import primitive_param,scalar_param_native as scalar,pooled_source_helper
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack.module_structure_models import rolling_holder,rolling_owned_prehook,enclosing_header
from scripts.game_data.memorypack.airwall_source import cast,barrier
from scripts.game_data.memorypack.unmanaged_qword_source import validate as qword
from scripts.game_data.memorypack import subgame_world_models as model
from scripts.game_data.memorypack import subgame_enclosing_models as enclosing

def derive_enclosing(image,pins,world):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);build=Build(image,pins);entries=GenericEntries(image);symbols=ContextSymbols(image);programs=[];methods=[];contexts=[];proofs=[];usages=[];need=lambda k,a,b:scalar.need('subgame.enclosing',k,a,b)
 def owned(p):
  regions=[];rows=[];windows=[]
  for part in image.unwind_index.family(p-base)['ranges']:
   a,z=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);regions.append((base+a,raw));rows+=image.body_index._decode(base+a,z-a);windows.append(dict(startRva=a,endRva=z,sha256=hashlib.sha256(raw).hexdigest().upper()))
  programs.append(dict(entryRva=p-base,windows=windows));return regions,rows
 def method(owner,name):
  m,=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name];p=image.method_pointer_va(m);methods.append([m.index,owner,name,p-base]);return m,p
 def calls(rs):return[int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)for r in rs if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 def usage(u,expected):
  fact=derive_typed_usage_context(image,u['site']-base,label='subgame.enclosing');need('typed-context',expected,(fact['typeName'],fact.get('methodName'),fact.get('classArguments',[]),fact.get('methodArguments',[])));usages.append(fact);return fact
 selected={};offsets=scalar.reader_offsets(image,'subgame.enclosing');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 for name,original,field in(('root','Beyond.Gameplay.Core.SubGameInstanceDataTable','dataTable'),('task','Beyond.Gameplay.Core.SubGameInstanceData+Task','taskId')):
  w,=[w for w in build.wrappers.values()if w.wrapped_type==original];need(name+'-reference',False,ctx.is_value_type(original));need(name+'-members',[field],[m.name for m in w.members]);need(name+'-holder',(w.name,original,16),ctx.field(w.name+'::__instance'));m,p=method(w.name,'Deserialize');primitive_param.reader_abi(image,ctx,m,w);re,rs=owned(p);c=calls(rs);_,ctor=method(w.name,'.ctor');at=next(i for i,r in enumerate(rs)if calls([r])==[ctor]);hs=next(i for i,r in enumerate(rs)if bytes.fromhex(r['bytes'])==bytes.fromhex('488d542430'));header=calls(rs[hs:])[0];_,setter=method(w.name,'set___'+field+'__');s=dict(header=header,allocate=calls(rs[:at])[-1],ctor=ctor,barrier=world['symbols']['barrier']if'barrier'in world['symbols']else calls(rs)[-1],setter=setter)
  tail=rs[next(i for i,r in enumerate(rs)if bytes.fromhex(r['bytes'])==bytes.fromhex('488b1b')):]if name=='task'else rs[hs:];target=next(t for t in calls(tail)if t not in(set(s.values())))
  # The exact models check every selected call, including independently derived typed readers.
  if name=='root':
   hit=next(i for i,r in enumerate(rs)if bytes.fromhex(r['bytes'])==bytes.fromhex('488bce488b1b'))if any(bytes.fromhex(r['bytes'])==bytes.fromhex('488bce488b1b')for r in rs)else None
   typed=[]
   for r in rs:
    if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x15':
     try:f=derive_typed_usage_context(image,int(r['va'],16)-base,label='subgame.root')
     except ValueError:continue
     if f.get('methodName')=='ReadPackable':typed.append(f)
   f,=typed;need('root-dictionary-type',['System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.Core.SubGameInstanceData>'],f['methodArguments']);usages.append(f);site=base+f['instructionRva'];callsite=site+13;raw=image.pe.bytes_at_va(callsite,5);need('root-call-opcode',232,raw[0]);target=callsite+5+int.from_bytes(raw[1:],'little',signed=True);s['packable']=target
  else:s['pool']=target;pooled_source_helper.validate_on_image(image,target,pins)
  primitive_param.object_header_source(image,vector_recorder(image,lanes=True)(header-base),offsets)
  for new,null in((True,False),(False,False),(True,True),(False,True)):
   proof=getattr(enclosing,name)(re,p,s,new=new,null=null);proofs.append(dict(role=name,proof=proof))
   if proof['allocation']:usage(proof['allocation'],(w.name,None,[],[]))
  member=w.members[0];setter_m=md.methods[member.method_index];kind=14 if name=='task'else 21;scalar.owned_method_abi(image,ctx,setter_m.index,w.type_definition,('void',1,False),[(member.declared_type,kind,True)],'subgame.'+name+'Setter');field_row=ctx.field(original+'::'+field);need(name+'-field',(original,member.declared_type,16),field_row);sr,srows=owned(setter);proofs.append(dict(role=name+'-setter',proof=model.base_reference(srows,field=16,barrier=s['barrier'])));selected[name]=dict(wrapper=w.name,original=original,symbols=s,entry=p)
 # The exact nine-way dispatch independently authenticates the selected type/tag bijection.
 from scripts.game_data.memorypack.union_dispatch import read_union_switch
 world_wrapper,=[w for w in build.wrappers.values()if w.wrapped_type=='Beyond.Gameplay.Core.WorldChallengeSubGameData'];union=read_union_switch(image,world_wrapper.parent_name,wrappers={w.type_definition:w for w in build.wrappers.values()});item,=[e for e in union['entries']if e['wrapperName']==world_wrapper.name];need('union-family-size',9,len(union['entries']));need('union-world-tag',8,item['tag']);owner=world_wrapper.parent_name+'+'+world_wrapper.parent_name.rsplit('.',1)[-1]+'Formatter';m,p=method(owner,'Deserialize');re,rs=owned(p);at=next(i for i,r in enumerate(rs)if bytes.fromhex(r['bytes'])==bytes.fromhex('488d542438'));cs=calls(rs[at:]);s=dict(header=cs[0],assignable=next(calls(rs[i:])[0]for i,r in enumerate(rs)if bytes.fromhex(r['bytes'])==bytes.fromhex('488b09')),packable=selected['root']['symbols']['packable'],barrier=selected['root']['symbols']['barrier'])
 for existing,null in((False,False),(True,False),(False,True)):
  proof=enclosing.union_world(re,p,s,existing=existing,null=null);proofs.append(dict(role='union',proof=proof))
  if proof['typedWrapperUsage']:usage(proof['typedWrapperUsage'],('MemoryPack.MemoryPackReader','ReadPackable',[],[world_wrapper.name]))
  if proof['comparisonTypeUsage']:usage(proof['comparisonTypeUsage'],(world_wrapper.name,None,[],[]))
 selected['union']=dict(entry=p,symbols=s,dispatch=union)
 hr,_=owned(s['header'])
 for marker in('short','extended','false'):proofs.append(dict(role='unionHeader',proof=enclosing_header(hr,s['header'],offsets,marker=marker)))
 for owner,args,role in(('MemoryPack.Formatters.DictionaryFormatter`2',['object','object'],'dictionary'),('MemoryPack.Formatters.ListFormatter`1',['ulong'],'ulongList')):
  td=ctx.index.types[owner];m,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize'];entry=entries.resolve(m.index,args,[]);re,rs=owned(entry['pointer']);c=calls(rs);context=symbols.context(td.index);validate_generic_contexts(image,[context],label='subgame.'+role);contexts.append(context)
  if role=='dictionary':
   s=dict(classResolve=c[0],allocate=c[1],constructor=c[2],barrier=c[3],provider=c[4],dispatch=c[6],insert=c[8]);need('dictionary-identical-provider',c[4],c[5]);need('dictionary-identical-dispatch',c[6],c[7]);paths=[enclosing.dictionary(re,entry['pointer'],s,offsets,count=n)for n in range(-1,5)]
  else:s=dict(barrier=selected['root']['symbols']['barrier']);paths=[enclosing.null_ulong_list(re,entry['pointer'],s,offsets)]
  need(role+'-same-barrier',selected['root']['symbols']['barrier'],s['barrier']);proofs.extend(dict(role=role,proof=p)for p in paths);selected[role]=dict(entry=entry,context=context,symbols=s)
 return json.loads(json.dumps(dict(programs=programs,methods=methods,contexts=contexts,proofs=proofs,usages=usages,selected=selected)))

def derive_world(image,pins):
 base=image.pe.image_base;build=Build(image,pins);md=image.metadata;ctx=NativeReferenceContext(image);world,=[w for w in build.wrappers.values()if w.wrapped_type=='Beyond.Gameplay.Core.WorldChallengeSubGameData'];original=world.wrapped_type;parent=build.wrappers[world.parent_name];rec=vector_recorder(image,lanes=True);need=lambda k,a,b:scalar.need('subgame.world',k,a,b);programs=[];results=[];usages=[];methods=[]
 def method(w,n):
  m,=[m for m in md.methods_for(md.types[w.type_definition])if md.string(m.name_index)==n];return m,image.method_pointer_va(m)
 def owned(p):
  windows=[];regions=[];rows=[]
  for part in image.unwind_index.family(p-base)['ranges']:
   a,z=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);windows.append(dict(startRva=a,endRva=z,sha256=hashlib.sha256(raw).hexdigest().upper()));regions.append((base+a,raw));rows+=image.body_index._decode(base+a,z-a)
  programs.append(dict(entryRva=p-base,windows=windows));return regions,rows
 def program(w,n):
  m,p=method(w,n);methods.append([m.index,w.name,n,p-base]);return m,p,*owned(p)
 def calls(rs):return[int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)for r in rs if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 def usage(site,expected):
  fact=derive_typed_usage_context(image,site-base,label='subgame.world');need('type-usage',expected,fact['typeName']);usages.append(fact);return fact
 area='Beyond.Gameplay.Core.FunctionAreaPtr';area_td=ctx.index.types[area];need('area-value',True,ctx.is_value_type(area));af=[f for f in md.fields_for(area_td)if not ctx.field_attributes(f.type_index)&16];need('area-fields',[(area,'ulong',16)],[ctx.field(area+'::'+md.string(f.name_index))for f in af]);scalar.ordinary(image,ctx.type_pointer(af[0].type_index),11,'subgame.areaField');need('area-size-index',True,0<=area_td.index<image.registration['typeDefinitionsSizesCount']);sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*area_td.index);need('area-boxed-native-size',(24,8),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)))
 need('world-reference',False,ctx.is_value_type(original));need('world-parent','Beyond.Gameplay.Core.SubGameInstanceData',ctx.parent(original));need('typed-holder',(world.name,original,24),ctx.field(world.name+'::__realInstance'));need('base-holder',(parent.name,parent.wrapped_type,16),ctx.field(parent.name+'::___instance'));need('wrapper-parent',parent.name,ctx.parent(world.name));need('member-count',36,len(world.members))
 m,getter,gr,gs=program(world,'get___instance');scalar.owned_method_abi(image,ctx,m.index,world.type_definition,(original,18,True),[],'subgame.worldGetter');cs=calls(gs);caster=cs[1];write_barrier=cs[-1]
 for cached,same in((False,False),(True,False),(True,True)):
  result=rolling_holder(gr,getter,cast=caster,barrier=write_barrier,cached=cached,same=same);results.append(dict(role='getter',proof=result))
  for u in result['classUsages']:usage(u['site'],original)
 m,inst,ir,_=program(world,'set___instance');scalar.owned_method_abi(image,ctx,m.index,world.type_definition,('void',1,False),[(original,18,True)],'subgame.worldHolder');results.append(dict(role='dual-holder',proof=model.dual_holder(ir,inst,write_barrier)))
 m,hook,hr,_=program(world,'OnDeserialized');scalar.owned_method_abi(image,ctx,m.index,world.type_definition,('void',1,False),[],'subgame.worldHook')
 for cached,null in((True,False),(False,False),(False,True)):
  result=rolling_owned_prehook(hr,hook,dict(cast=caster,barrier=write_barrier),cached=cached,base_null=null);results.append(dict(role='prehook',proof=result))
  for u in result['classUsages']:usage(u['site'],original)
 factory_casts=[]
 for name,isctor in(('.ctor',True),('CreateInstance',False)):
  m,p,re,rs=program(world,name);scalar.owned_method_abi(image,ctx,m.index,world.type_definition,('void',1,False),[],'subgame.worldFactory');c=calls(rs);normal=c[2:]if isctor else c[1:];s=dict(baseReady=c[2]if isctor else 0,allocate=normal[1]if isctor else normal[0],instanceSetter=inst,cast=normal[4]if isctor else normal[3],barrier=write_barrier);result=model.factory(re,p,s,ctor=isctor);results.append(dict(role='factory',proof=result));factory_casts.append(s['cast']);usage(result['allocation']['site'],original)
  if result['baseClassUsage']:usage(result['baseClassUsage']['site'],parent.name)
  for u in result['classUsages']:usage(u['site'],original)
 need('factory-same-casts',factory_casts[0],factory_casts[1]);predicates=[]
 for target,strict in((caster,False),(factory_casts[0],True)):
  re,rs=owned(target);predicate=calls(rs)[0];predicates.append(predicate);results.append(dict(role='compatible-cast',proof=cast(re,target,predicate,strict=strict)))
 need('same-class-predicate',predicates[0],predicates[1]);prefix=image.pe.bytes_at_va(write_barrier,12);need('disabled-barrier-branch',b'\x74',prefix[10:11]);end=write_barrier+12+int.from_bytes(prefix[11:12],'little',signed=True);results.append(dict(role='disabled-barrier',proof=barrier([(write_barrier,prefix),(end,image.pe.bytes_at_va(end,1))],write_barrier)))
 m,p,re,rs=program(world,'Deserialize');primitive_param.reader_abi(image,ctx,m,world);count=next(i for i,r in enumerate(rs)if bytes.fromhex(r['bytes'])==bytes.fromhex('807d2824'));c=calls(rs[count:]);setters=[image.method_pointer_va(md.methods[m.method_index])for m in world.members];need('current36-named-setter-targets',setters,c[1:72:2]);plan=[];field_rows=[]
 for member in world.members:
  kind=('lang'if member.declared_type=='Beyond.LangKey'else'list'if member.declared_type.startswith('System.Collections.Generic.List`1<')else'area'if member.declared_type=='Beyond.Gameplay.Core.FunctionAreaPtr'else {'enum':'enum','bool':'bool','scalar32':'int','scalar64':'qword','string':'string'}.get(member.kind))
  if kind is None:raise ValueError('subgame.world.unreviewed-field:'+member.name)
  plan.append(kind);owner=build.wrappers[member.declaring_wrapper];owner_type=owner.wrapped_type;field=ctx.field(owner_type+'::'+member.name);need('declared-field-type',member.declared_type,field[1]);setter=md.methods[member.method_index];scalar.owned_method_abi(image,ctx,setter.index,owner.type_definition,('void',1,False),[(member.declared_type,{'lang':17,'area':17,'enum':17,'list':21,'string':14,'bool':2,'qword':11,'int':8}[kind],kind in('list','string'))],'subgame.worldSetter');setter_p=image.method_pointer_va(setter);sr,srows=owned(setter_p);slot=field[2]
  if member.declaring_wrapper==world.name:
   proof=model.owned_reference(sr,setter_p,getter,write_barrier,slot=slot)if kind=='list'else model.owned_scalar(sr,setter_p,getter,slot=slot,width=1 if kind=='bool'else 8)
  elif kind in('string','list','lang'):proof=model.base_reference(srows,field=slot,barrier=write_barrier,wide=kind=='lang')
  else:proof=model.base_scalar(srows,field=slot,mode='byte'if kind=='bool'else'qword'if kind=='qword'else'dword')
  field_rows.append(dict(name=member.name,type=member.declared_type,kind=kind,field=field,setter=[setter.index,owner.name,md.string(setter.name_index),setter_p-base],proof=proof))
 header_at=next(i for i,r in enumerate(rs)if bytes.fromhex(r['bytes'])==bytes.fromhex('488d5528'));header=calls(rs[header_at:])[0];ctor=method(world,'.ctor')[1];i=next(i for i,r in enumerate(rs)if calls([r])==[ctor]);s=dict(header=header,prehook=hook,allocate=calls(rs[:i])[-1],ctor=ctor,reads=c[:72:2],setters=setters);offsets=scalar.reader_offsets(image,'subgame.world')
 for existing,null in((False,False),(True,False),(False,True),(True,True)):
  result=model.world(re,p,s,plan,existing=existing,null=null);results.append(dict(role='caller',proof=result))
  if result['allocation']:usage(result['allocation']['site'],world.name)
  for u in result['typedUsages']:
   actual=derive_typed_usage_context(image,u['site']-base,label='subgame.world');typ=world.members[u['member']].declared_type;expected='ReadValue'if plan[u['member']]=='lang'else'ReadPackable'if plan[u['member']]=='list'else'ReadUnmanaged';need('current-typed-child-context',('MemoryPack.MemoryPackReader',expected,[],[typ]),(actual['typeName'],actual['methodName'],actual['classArguments'],actual['methodArguments']));usages.append(actual)
 primitive_param.object_header_source(image,rec(header-base),offsets)
 for kind in('bool','int','enum','qword','string','area'):
  targets={t for t,k in zip(s['reads'],plan)if k==kind}
  for target in targets:
   r=rec(target-base,fragments=True)
   if kind=='bool':scalar.boolean_source(image,r,offsets,'subgame.worldBool')
   elif kind in('int','enum','qword'):scalar.integer_source(image,r,offsets,'subgame.worldInteger',width=8 if kind=='qword'else 4)
   elif kind=='string':pooled_source_helper.validate_on_image(image,target,pins)
   else:qword(image,target,offsets)
 return json.loads(json.dumps(dict(fields=field_rows,programs=programs,methods=methods,usages=usages,results=results,plan=plan,symbols=s)))
