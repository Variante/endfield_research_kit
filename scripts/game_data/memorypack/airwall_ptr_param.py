"""Derive the selected raw24 AirWall parameter and its exact typed action caller."""
import hashlib,json
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.memorypack import airwall_source as source,primitive_param,scalar_param_native as scalar,pooled_source_helper,reference_adapter_sources
from scripts.game_data.memorypack.unmanaged_qword_source import advance
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.levelscript_family_regenerate import Build,select_calls
VALUE='Beyond.Gameplay.Core.AirWallPtr'
PARAM='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>'
ACTION='Beyond.Gameplay.Actions.AirWallEnable'
LABEL='airWallPtrParam'

def derive(image,pins,profile):
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);build=Build(image,pins);rec=vector_recorder(image,lanes=True);need=lambda check,expected,actual:scalar.need(LABEL,check,expected,actual)
 def wrapper(original):
  rows=[w for w in build.wrappers.values()if w.wrapped_type==original];need('unique-wrapper',1,len(rows));return rows[0]
 def method(w,name):
  rows=[m for m in md.methods_for(md.types[w.type_definition])if md.string(m.name_index)==name];need('unique-method:'+name,1,len(rows));m=rows[0];return m,image.method_pointer_va(m)
 def owned(pointer):
  regions=[];windows=[];rows=[]
  for part in image.unwind_index.family(pointer-base)['ranges']:
   a,z=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);regions.append((base+a,raw));windows.append(dict(startRva=a,endRva=z,sha256=hashlib.sha256(raw).hexdigest().upper()));rows+=image.body_index._decode(base+a,z-a)
  return regions,windows,rows
 def calls(rows):return [int(r['va'],16)+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)for r in rows if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 def class_usage(site,expected):
  usage=derive_typed_usage_context(image,site-base,label=LABEL);need('typed-class',expected,usage['typeName']);return usage
 td=ctx.index.types[VALUE];need('non-generic-value',(True,-1),(ctx.is_value_type(VALUE),td.generic_container_index));fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 expected=[('useSlotId','bool',16,2),('logicId','ulong',24,11),('slotId','uint',32,9)];need('value-field-count',3,len(fields));declarations=[]
 for field,(name,typ,offset,kind)in zip(fields,expected,strict=True):
  need('field-name',name,md.string(field.name_index));need('value-field',(VALUE,typ,offset),ctx.field(VALUE+'::'+name));scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,LABEL+'.valueField');declarations.append([name,typ,offset-16])
 need('type-size-index',True,0<=td.index<image.registration['typeDefinitionsSizesCount']);sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);need('boxed/native-size',(40,24),(image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4)))
 w=wrapper(PARAM);need('parameter-members',[('constValue',VALUE),('idRef','int'),('paramSource','int'),('path','string')],[(m.name,m.declared_type)for m in w.members]);need('parameter-holder',(w.name,PARAM,16),ctx.field(w.name+'::__instance'));methods={};slots={};windows=[]
 for name in ('.ctor','CreateInstance','GetValue','Deserialize',*('set___'+m.name+'__'for m in w.members)):
  m,p=method(w,name)
  if name=='GetValue':
   raw=image.pe.bytes_at_va(p,5);need('getter',bytes.fromhex('488b4110c3'),raw);record=dict(pointerRva=p-base,window=dict(startRva=p-base,endRva=p-base+5,sha256=hashlib.sha256(raw).hexdigest().upper()),instructions=[[p-base,'488B4110'],[p-base+4,'C3']])
  elif name=='Deserialize':regions,ws,rows=owned(p);record=dict(pointerRva=p-base,windows=ws);windows+=ws;primitive_param.reader_abi(image,ctx,m,w)
  else:record=rec(p-base,fragments=True)
  methods[name]=dict(methodIndex=m.index,**record)
  if name!='Deserialize':
   result=(PARAM,21,True)if name=='GetValue'else('void',1,False);args=[{'constValue':(VALUE,17,False),'idRef':('int',8,False),'paramSource':('int',8,False),'path':('string',14,True)}[name[6:-2]]]if name.startswith('set___')else[];scalar.owned_method_abi(image,ctx,m.index,w.type_definition,result,args,LABEL)
  if name.startswith('set___'):
   member=name[6:-2]
   if member=='constValue':sr,sw,_=owned(p);constant=source.constant_setter(sr,p);slots[member]=constant['destinationOffset'];windows+=sw
   else:
    instructions=record['instructions'];ispath=member=='path';nonnull=ispath and bytes.fromhex(instructions[3][1])==b'\x75\x06';slots[member]=bytes.fromhex(instructions[6 if nonnull or not ispath else 4][1])[-1];scalar.parameter_setter(image,instructions,name=member,slot=slots[member],width=4,label=LABEL)
 need('owned-slots',{'constValue':32,'idRef':56,'paramSource':16,'path':24},slots)
 occupied=[at for name,size in (('constValue',24),('idRef',4),('paramSource',4),('path',8))for at in range(slots[name],slots[name]+size)];need('disjoint-slots',40,len(set(occupied)))
 loads=[r for r in methods['.ctor']['instructions']if bytes.fromhex(r[1])[:3]==b'\x48\x8b\x0d'];need('one-param-allocation-load',1,len(loads));allocation=derive_typed_usage_context(image,loads[0][0],label=LABEL);need('param-allocation-type',PARAM,allocation['typeName']);parameter=dict(methods=methods,ownedFieldSlots=slots,allocationContext=allocation);scalar.allocation_bridge(image,ctx,parameter,LABEL)
 _,p=method(w,'Deserialize');regions,ws,rows=owned(p);c=calls(rows);ctor=base+methods['.ctor']['pointerRva'];i,=[i for i,r in enumerate(rows)if calls([r])==[ctor]];n,=[i for i,r in enumerate(rows)if bytes.fromhex(r['bytes'])==bytes.fromhex('48c70700000000')];s=dict(header=c[0],advance=c[1],integer=c[2],idRef=base+methods['set___idRef__']['pointerRva'],paramSource=base+methods['set___paramSource__']['pointerRva'],path=c[6],pathSetter=base+methods['set___path__']['pointerRva'],barrier=calls(rows[n:n+4])[0],allocate=calls(rows[:i])[-1],ctor=ctor);offsets=scalar.reader_offsets(image,LABEL)
 paths=[source.param(regions,p,s,offsets,new=a,null=b)for a,b in ((False,False),(True,False),(False,True),(True,True))]
 for result in paths:
  if result['wrapperAllocation']:class_usage(result['wrapperAllocation']['site'],w.name)
 ar,aw,_=owned(s['advance']);advance_proofs=[advance(ar,s['advance'],offsets,zero=z)for z in (True,False)];windows+=aw
 header=rec(s['header']-base);primitive_param.object_header_source(image,header,offsets);integer=rec(s['integer']-base);scalar.integer_source(image,integer,offsets,LABEL+'.int32');pool=pooled_source_helper.validate_on_image(image,s['path'],pins);need('pool-encoding','int32-pool-index',pool['wireEncoding'])
 path=methods['set___path__']['instructions'];tail=path[9 if bytes.fromhex(path[3][1])==b'\x75\x06'else 7];need('same-path-barrier',s['barrier'],base+tail[0]+5+int.from_bytes(bytes.fromhex(tail[1])[1:],'little',signed=True))
 composition=profile['composition'];validate_registered_formatter_composition(image,composition,label=LABEL);need('registered-param',[(PARAM,w.name)],[(r['originalType'],r['wrapperType'])for r in composition['registrations']]);validate_eager_wrap_registration(image,profile['eager'],label=LABEL);need('eager-param',(PARAM,w.name),(profile['eager']['originalType'],profile['eager']['wrapperType']));reference=reference_adapter_sources.validate_reference_routes(image,profile['referenceRoutes'],[composition])
 action=_action(image,pins,build,ctx,owned,method,calls,class_usage,s)
 return json.loads(json.dumps(dict(parameter=parameter,valueFields=declarations,boxedSize=40,rawSize=24,ownedWindows=windows,paths=paths,constantSetter=constant,advance=advance_proofs,headerSource=header,int32Source=integer,pooledSource=pool,symbolRvas={k:v-base for k,v in s.items()},referenceComposition=reference,action=action,evidenceBoundary={'exact':'Current AirWallPtr bool/UInt64/UInt32 declared unboxed offsets0/8/16 in24-byte unmanaged representation, padding preserved. Selected MC4 source copies exactly24 bytes, advances24 and forwards two Int32 plus pooled String results into disjoint owned Param slots. Current MC10 parent source and owned typed holders/setters preserve the actual child result reference.','conditional':'Initialized generated route, coherent selected typed adapter/inflation/provider and callback, successful normal disjoint constructors/helpers, sufficient buffer and disabled collector.','unresolved':'Effective live provider/default selection, refill/error paths and gameplay execution.'})))


def _action(image,pins,build,ctx,owned,method,calls,class_usage,param_symbols):
 base=image.pe.image_base;md=image.metadata;need=lambda check,expected,actual:scalar.need(LABEL,check,expected,actual);w,=[w for w in build.wrappers.values()if w.wrapped_type==ACTION];need('action-fields',[('dontLogWarning','bool'),('ID','int'),('releaseWhenExecutionFinished','bool'),('uid','string'),('scopeMask','Beyond.GEnums.ScopeName'),('useCurrentScope','bool'),('useGraphScope','bool'),('nextID','int'),('airWallPtr',PARAM),('enable','Beyond.Gameplay.Actions.Param`1<bool>')],[(m.name.lstrip('_'),m.declared_type)for m in w.members]);programs=[];methods=[];results=[]
 def program(name):
  m,p=method(w,name);regions,windows,rows=owned(p);programs.append(dict(entryRva=p-base,windows=windows));methods.append([m.index,w.name,name,p-base]);return p,regions,rows
 parent='Beyond.MemoryPack.Beyond_Gameplay_Actions_ActionBaseForMemoryPack';node='Beyond.MemoryPack.Beyond_Gameplay_NodeBaseForMemoryPack';need('action-wrapper-parent',parent,ctx.parent(w.name));need('base-wrapper-parent',node,ctx.parent(parent));need('typed-owned-holder',(w.name,ACTION,32),ctx.field(w.name+'::__realInstance'));node_fields=[ctx.field(node+'::'+md.string(f.name_index))for f in md.fields_for(ctx.index.types[node])if not ctx.field_attributes(f.type_index)&16];need('base-owned-holder',[(node,'Beyond.Gameplay.NodeBase',16)],node_fields)
 for name,args,result in(('get___instance',[],(ACTION,18,True)),('set___instance',[(ACTION,18,True)],('void',1,False)),('OnDeserialized',[],('void',1,False)),('.ctor',[],('void',1,False))):
  m,_=method(w,name);scalar.owned_method_abi(image,ctx,m.index,w.type_definition,result,args,LABEL+'.actionOwned')
 getter,gr,gs=program('get___instance');caster=calls(gs)[1];s=dict(barrier=param_symbols['barrier'],getter=getter,cast=caster)
 for cached,same in ((False,False),(True,False),(True,True)):results.append(source.action_getter(gr,getter,s,cached=cached,same=same))
 instance,ir,_=program('set___instance');results.append(source.dual_holder(ir,instance,s['barrier']))
 hook,hr,_=program('OnDeserialized');results.extend(source.prehook(hr,hook,s,cached=a,base_null=b)for a,b in ((True,False),(False,False),(False,True)))
 ctor,cr,cs=program('.ctor');cc=calls(cs);s.update(baseCtor=cc[0],allocate=cc[1],originalCtor=cc[2],instanceSetter=instance,factoryCast=cc[4]);need('same-action-allocator',param_symbols['allocate'],s['allocate']);need('factory-casts-same',cc[4],cc[5]);factory=source.factory(cr,ctor,s);results.append(factory);class_usage(next(int(r['va'],16)for r in cs if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'),ctx.parent(w.name))
 base_ctor,=[m for m in md.methods_for(ctx.index.types[parent])if md.string(m.name_index)=='.ctor'];need('actual-base-ctor',image.method_pointer_va(base_ctor),s['baseCtor']);original_td=ctx.index.types[ACTION];original_ctor,=[m for m in md.methods_for(original_td)if md.string(m.name_index)=='.ctor'];need('actual-original-ctor',image.method_pointer_va(original_ctor),s['originalCtor'])
 for member,slot,typ in (('airWallPtr',216,PARAM),('enable',208,'Beyond.Gameplay.Actions.Param`1<bool>')):
  need('owned-action-slot',(ACTION,typ,slot),ctx.field(ACTION+'::_'+member));m,p=method(w,'set____'+member+'__');scalar.owned_method_abi(image,ctx,m.index,w.type_definition,('void',1,False),[(typ,21,True)],LABEL);p,re,_=program('set____'+member+'__');results.append(source.action_setter(re,p,s,slot=slot))
 predicates=[]
 for target,strict in ((caster,False),(s['factoryCast'],True)):
  re,ws,rs=owned(target);programs.append(dict(entryRva=target-base,windows=ws));predicate=calls(rs)[0];predicates.append(predicate);results.append(source.cast(re,target,predicate,strict=strict))
 need('same-current-class-predicate',predicates[0],predicates[1]);prefix=image.pe.bytes_at_va(s['barrier'],12);need('barrier-branch-shape',b'\x74',prefix[10:11]);leaf=s['barrier']+12+int.from_bytes(prefix[11:12],'little',signed=True);need('barrier-distinct-terminal',True,leaf>=s['barrier']+12);re=[(s['barrier'],prefix),(leaf,image.pe.bytes_at_va(leaf,1))];results.append(source.barrier(re,s['barrier']));programs.append(dict(entryRva=s['barrier']-base,selectedRanges=[dict(startRva=a-base,endRva=a-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper())for a,raw in re],boundary='Exact selected collector-disabled flag/branch/RET only; cold paths and physical function extent excluded.'))
 p,re,rs=program('Deserialize');m,_=method(w,'Deserialize');primitive_param.reader_abi(image,ctx,m,w);count=next(i for i,r in enumerate(rs)if bytes.fromhex(r['bytes'])==bytes.fromhex('4080fe0a'));c=calls(rs[count:]);s.update(header=calls(rs[:count])[0],reads=c[:20:2],setters=c[1:20:2],prehook=hook,ctor=ctor)
 paths=[source.action(re,p,s,new=a,null=b)for a,b in ((False,False),(True,False),(False,True),(True,True))];results+=paths
 for r in results:
  for usage in r.get('classUsages',[]):class_usage(usage['site'],ACTION)
 for r in paths:
  if r['wrapperAllocation']:class_usage(r['wrapperAllocation']['site'],w.name)
  for usage in r['typedUsages']:
   context=derive_typed_usage_context(image,usage['site']-base,label=LABEL);expected='ReadUnmanaged'if usage['member']==4 else'ReadValue';need('action-typed-read',('MemoryPack.MemoryPackReader',expected,[],[w.members[usage['member']].declared_type]),(context['typeName'],context['methodName'],context['classArguments'],context['methodArguments']))
 for i in (8,9):build.prove_named_target(s['reads'][i],'MemoryPack.MemoryPackReader','ReadValue',result_abi='reference')
 need('same-current-header',param_symbols['header'],s['header']);need('same-raw-integer',param_symbols['integer'],s['reads'][1]);build.prove_pooled_string_target(s['reads'][3]);need('same-raw-bool',True,len({s['reads'][i]for i in(0,2,5,6)})==1);scalar.boolean_source(image,vector_recorder(image)(s['reads'][0]-base),scalar.reader_offsets(image,LABEL),LABEL+'.actionBoolean')
 return dict(programs=programs,methods=methods,paths=results,symbolRvas={k:[a-base for a in v]if isinstance(v,list)else v-base for k,v in s.items()})
