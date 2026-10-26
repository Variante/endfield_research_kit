"""Current initialized GameplayTag4 and bounded new-list source components."""
import json,struct
from scripts.game_data.memorypack import npc_tag_programs as adapter,npc_tag_programs as lists,npc_tag_programs as child
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,derive_typed_usage_context
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.memorypack.reference_conversion_sources import validate_conversion_context
from scripts.game_data.memorypack.vector_layout import vector_recorder
from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param as primitive
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets


def validate_components(image,pins,fact):
 if fact.get("schema")!="endfield.npc-gameplay-tag-source-component.v1":raise ValueError("npcTag.schema")
 base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image);cs=ContextSymbols(image);regions={};programs=[]
 sources,helpers,registration,children=(fact[k]for k in('sources','helpers','registration','children'));original='Beyond.Gameplay.Core.GameplayTag';composition=next(c for c in registration['compositions']if c['registrations'][0]['originalType']==original);wrapper=composition['registrations'][0]['wrapperType'];td=ctx.index.types[wrapper];static=next(m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize');record=next(c for c in children['records']if c['typeName']==original);reader=next(m for m in record['methods']if m['name']=='Deserialize')
 for selected_fact in(sources,helpers,registration,children):
  if selected_fact['nativeInputs']!=pins:raise ValueError('NPC tag selected inputs')
 for selected in sources['selections']:
  if json.loads(json.dumps(entries.observe(selected['definition'],selected['classArguments'],[])))!=selected['entries']:raise ValueError('NPC tag exact selected current registered entries')
 validate_generic_contexts(image,sources['contexts'],label='npcTag');validate_eager_wrap_registration(image,next(f for f in registration['eagerRegistrations']if f['originalType']==original),label='npcTag');validate_registered_formatter_composition(image,composition,label='npcTag')
 for item in sources['sources']+helpers['helpers']+[reader]:
  if 'windows'not in item:continue
  entry=item['entryRva'];windows=item['windows'];wanted=sorted((w['startRva'],w['endRva'])for w in windows)
  if item.get('leaf'):
   if len(wanted)!=1 or wanted[0][0]!=entry:raise ValueError('NPC tag leaf selected partition')
  else:
   if sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(entry)['ranges'])!=wanted:raise ValueError('NPC tag complete owned membership')
  image.check_windows(windows,label='npcTag');regions[base+entry]=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows];programs.append(dict(entryRva=entry,leaf=item.get('leaf',False),windows=[{k:w[k]for k in('startRva','endRva','sha256')}for w in windows]))
 offsets=scalar.reader_offsets(image,'npcTag');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 if offsets!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68,'totalLength':24}:raise ValueError('NPC tag reader field ownership')
 if not ctx.is_value_type(original)or ctx.is_value_type(wrapper)or ctx.field(original+'::tagId')!=(original,'int',16)or ctx.field(wrapper+'::__instance')!=(wrapper,original,16):raise ValueError('NPC tag exact nominal managed4 ownership')
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+ctx.index.types[original].index*8)
 if(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4))!=(20,4):raise ValueError('NPC tag managed4 ABI size')
 scalar.owned_method_abi(image,ctx,next(m for m in md.methods_for(td)if md.string(m.name_index)=='GetValue').index,td.index,(original,17,False),[],'npcTag.getter')
 for name,expected in(('GetValue','8b4110c3'),('.ctor','33c0894110c3'),('CreateInstance','33c0894110c3')):
  method=next(m for m in md.methods_for(td)if md.string(m.name_index)==name);pointer=image.method_pointer_va(method)
  if image.pe.bytes_at_va(pointer,len(bytes.fromhex(expected)))!=bytes.fromhex(expected):raise ValueError('NPC tag complete getter/default leaf:'+name)
  if name=='GetValue'and ctx.type_name(method.return_type)!=original:raise ValueError('NPC tag nominal getter return')
 interface,=composition['interfaces'];section=md.sections['interfaceOffsets'];a=section.offset+td.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[a:a+td.interface_offsets_count*8]));ordinal=pairs.index((interface['interfaceTypeIndex'],interface['interfaceOffset']))
 def fail(k,e,a):raise ValueError('NPC.tag.context.'+k+':expected='+str(e)[:160]+':actual='+str(a)[:160])
 context=next(c for c in sources['contexts']if c['typeName']=='Beyond.MemoryPack.GenericMemoryPackFormatter`2');typed=validate_conversion_context(image,context,entries,fail=fail)
 for slot,name,ordinals in((0,'ReadIsNull',[0,1]),(3,'DeserializeNotNull',[0,1]),(11,'CreateInstance',[1])):
  r=context['entries'][slot];args=r['classArguments']if slot!=11 else r['methodArguments']
  if r['methodName']!=name or [a['parameterOwner']['ordinal']for a in args]!=ordinals or any(a['parameterOwner'].get('typeIndex')!=context['definition']for a in args):raise ValueError('NPC tag actual adapter factory context')
 s={k:base+v for k,v in fact['symbols'].items()}
 for name in('ReadIsNull','DeserializeNotNull','Deserialize'):
  method=next(m for m in md.methods_for(ctx.index.types['Beyond.MemoryPack.GenericMemoryPackFormatter`2'])if md.string(m.name_index)==name)
  if entries.resolve(method.index,[original,'object'],[])['pointer']!=s[dict(ReadIsNull='readNull',DeserializeNotNull='nonnull',Deserialize='main')[name]]:raise ValueError('NPC tag actual closed canonical pointer')
 rec=vector_recorder(image);primitive.object_header_source(image,rec(s['header']-base),offsets);scalar.integer_source(image,rec(s['integer']-base),offsets,'npcTag.integer')
 proofs=[adapter.peek(regions[s['peek']],s['peek'],offsets)]
 for null in(False,True):proofs.append(adapter.read_null(regions[s['readNull']],s['readNull'],s,null=null))
 for dispatch,entry in((False,s['main']),(True,base+fact['listSymbols']['dispatch'])):
  for create in(False,True):proofs.append(adapter.main(regions[entry],entry,s,create=create,dispatch=dispatch))
  proofs.append(adapter.main(regions[entry],entry,s,null=True,dispatch=dispatch))
 for null in(False,True):proofs.append(adapter.nonnull(regions[s['nonnull']],s['nonnull'],s,wrapper_null=null))
 proofs.append(adapter.conversion(regions[s['conversion']],s['conversion'],s['prepare'],ordinal=ordinal))
 for created in(False,True):proofs.append(child.wrapper(regions[base+reader['entryRva']],base+reader['entryRva'],s,created=created))
 proofs.append(child.wrapper(regions[base+reader['entryRva']],base+reader['entryRva'],s,null=True))
 flow=next(p for p in proofs if p.get('created'))
 allocation=derive_typed_usage_context(image,next(a for a,b in flow['selectedBytes']if bytes.fromhex(b)[:3]==bytes.fromhex('488b0d'))-base,label='npcTag.allocation')
 if allocation.get('typeName')!=wrapper:raise ValueError('NPC tag exact wrapper allocation cell')
 list_symbols={k:base+v for k,v in fact['listSymbols'].items()};list_entry=base+fact['listEntryRva']
 lf=next(c for c in sources['contexts']if c['typeName']=='MemoryPack.Formatters.ListFormatter`1');ls=next(c for c in sources['contexts']if c['typeName']=='System.Collections.Generic.List`1')
 validate_list_formatter_base_context(image,lf,entries,fail=fail);validate_capacity_constructor_context(image,lf,ls,entries,fail=fail)
 list_td=ctx.index.types['System.Collections.Generic.List`1'];list_methods={md.string(m.name_index):[]for m in md.methods_for(list_td)}
 for m in md.methods_for(list_td):list_methods[md.string(m.name_index)].append(m)
 declared={md.string(f.name_index):ctx.type_name(f.type_index)for f in md.fields_for(list_td)}
 if(declared.get('_size'),declared.get('_version'))!=('int','int')or not declared.get('_items','').startswith('VAR[')or not declared['_items'].endswith('[]'):raise ValueError('NPC tag owned List field declarations')
 ctor=entries.resolve(lf['entries'][1]['methodSpec'][0],[original],[])['pointer'];cw=[]
 for part in image.unwind_index.family(ctor-base)['ranges']:
  a,z=part['runtimeTriple'][:2];cw.append((base+a,image.pe.bytes_at_va(base+a,z-a)))
 constructor_proofs=[lists.capacity_constructor(cw,ctor,list_symbols,positive=n)for n in(False,True)]
 clear_pointer=entries.resolve(lf['entries'][2]['methodSpec'][0],[original],[])['pointer'];clear_proof=lists.clear([(clear_pointer,image.pe.bytes_at_va(clear_pointer,11))],clear_pointer)
 list_proofs=[lists.tag_list(regions[list_entry],list_entry,offsets,list_symbols,count=n)for n in range(-1,3)]+[lists.add_no_growth(regions[list_symbols['add']],list_symbols['add'])]
 list_context=next(c for c in sources['contexts']if c['typeName']=='MemoryPack.Formatters.ListFormatter`1')
 for slot,owner,name in((1,'System.Collections.Generic.List`1','.ctor'),(3,'MemoryPack.MemoryPackFormatterProvider','GetFormatter'),(5,'MemoryPack.MemoryPackFormatter`1','Deserialize'),(6,'System.Collections.Generic.List`1','Add')):
  r=list_context['entries'][slot];args=r['methodArguments']if slot==3 else r['classArguments']
  if(r['typeName'],r['methodName'])!=(owner,name)or len(args)!=1 or args[0]['parameterOwner'].get('typeIndex')!=list_context['definition']or args[0]['parameterOwner']['ordinal']!=0:raise ValueError('NPC tag list typed source slot:'+str(slot))
 forward=md.methods[interface['formatterDeserializeMethodIndex']];pointer=image.method_pointer_va(forward);windows=composition['codeWindows'][1:];actual=sorted(tuple(p['runtimeTriple'][:2])for p in image.unwind_index.family(pointer-base)['ranges'])
 if actual!=sorted((w['startRva'],w['endRva'])for w in windows):raise ValueError('NPC tag formatter owned windows')
 forward_rows=[r for w in windows for r in image.body_index._decode(base+w['startRva'],w['endRva']-w['startRva'])];forward_proof=prove_zero_wrapper_forwarder(forward_rows,{k:base+v for k,v in fact['forwarderSymbols'].items()},image.method_pointer_va(static))
 dispatch_entry=s['dispatch'];dispatch_regions=[(base+p['runtimeTriple'][0],image.pe.bytes_at_va(base+p['runtimeTriple'][0],p['runtimeTriple'][1]-p['runtimeTriple'][0]))for p in image.unwind_index.family(dispatch_entry-base)['ranges']];slot=deserialize_slot(dispatch_regions,dispatch_entry,prepare=s['prepare'],callback=pointer)
 return dict(selectedPrograms=len(proofs)+len(list_proofs)+5,managedBytes=4,listCountLimit=2,sourceEntryRva=reader["entryRva"],listEntryRva=fact["listEntryRva"],interfaceOrdinal=ordinal,liveProviderSelectionProved=False,wholeOwnerAdmitted=False)
