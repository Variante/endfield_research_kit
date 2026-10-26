"""Actual LoaderHandle-to-Handle retention, set insertion and hash requests.

This outer source tier preserves the full twenty bytes, including padding. Its
HashSet element is FAssetProxyHandle; the LoaderHandle is its independently
named single-field wrapper. Native field hashing and boxed-child effects are
separate joins, not inferred from the generic comparer marker.
"""
from scripts.game_data.memorypack import leveldata_patrol_retain_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-retain-outer-sources.v1'
HANDLE='Beyond.Resource.FAssetProxyHandle'
LOADER='Beyond.Resource.FAssetProxyLoaderHandle'
HASHSET='System.Collections.Generic.HashSet`1'
COMPARER='System.Collections.Generic.GenericEqualityComparer`1'
INTERFACE='System.Collections.Generic.IEqualityComparer`1'


def need(check,condition):
 if not condition:raise ValueError('patrolRetainSource.'+check)


def _programs(p):
 base=p['imageBase'];h=p['helpers'];rr={k:packets.raw(v,base)for k,v in h.items()}
 return packets.norm(dict(retain=[paths.retain(rr['retain'],base+h['retain']['entryRva'],valid=v)for v in(False,True)],
  add=paths.spare_add(rr['add'],base+h['add']['entryRva']),
  hash=[paths.hash_invoker(rr['hashInvoke'],base+h['hashInvoke']['entryRva'],interface_steps=i)for i in range(4)],
  valueHashNull=paths.value_hash_no_objects(rr['valueHash'],base+h['valueHash']['entryRva']),
  valueHashObjects=[paths.value_hash_objects(rr['valueHash'],base+h['valueHash']['entryRva'],count=n,null_elements=m)
   for n in range(5)for m in((),tuple(range(n)),tuple(i for i in range(n)if i%2))]))


def derive_outer(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as parent
 _publication_gate(image,pins);source=parent.derive(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);symbols=ContextSymbols(image)
 asset=source['proof']['resourceSource']['proof']['assetSource'];h={};h['retain']=packets._parent_packet(asset['proof']['children']['retain-loader-handle'],base)
 r=paths.retain(packets.raw(h['retain'],base),base+h['retain']['entryRva']);h['add']=packets.packet(image,r['addCall']['targetVa'])
 add=paths.spare_add(packets.raw(h['add'],base),base+h['add']['entryRva'])
 for c in add['calls']:
  h[c['role']]=packets.packet(image,c['targetVa'],**({'span':15}if c['role']=='indexedContext'else{}))
 ih=paths.hash_invoker(packets.raw(h['hashInvoke'],base),base+h['hashInvoke']['entryRva'])
 target=next(c['targetVa']for c in ih['calls']if c['role']=='valueHash');h['valueHash']=packets.packet(image,target)
 usage=derive_typed_usage_context(image,r['methodContextUsage']['instructionVa']-base,label='patrolRetain.ownHashSetMethodInfo')
 definition=image.metadata.methods[usage['methodSpec'][0]].declaring_type
 context=symbols.context(definition,is_method=False,slots=[0,16,17,18]);ge=GenericEntries(image)
 ctd=ctx.index.types[COMPARER];method,=[m for m in image.metadata.methods_for(ctd)if image.metadata.string(m.name_index)=='GetHashCode'and m.parameter_count==1]
 _vtable(image,ctd.index,method.slot,method.index,'patrolRetain.ownGenericComparer')
 formal=symbols.type(ctx.type_pointer(next(iter(image.metadata.parameters_for(method))).type_index))
 comparer=dict(definition=method.index,typeDefinition=ctd.index,typeName=COMPARER,methodName='GetHashCode',slot=method.slot,returnType=ctx.type_name(method.return_type),
  parameterType=formal,context=symbols.context(ctd.index,is_method=False,slots=[0]),registrations=ge.observe(method.index,[HANDLE],[]))
 fields={}
 for name in(LOADER,HANDLE,'Beyond.Resource.FAssetProxyUntrackedHandle'):
  td=ctx.index.types[name];row=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
  fields[name]=dict(typeDefinition=td.index,typeName=name,valueType=ctx.is_value_type(name),enum=ctx.is_enum(name),parent=ctx.parent(name),
   boxedBytes=image.pe.u32_at_va(row),fields=[list(ctx.field(name+'::'+image.metadata.string(f.name_index)))for f in image.metadata.fields_for(td)if not ctx.field_attributes(f.type_index)&16])
 proof=dict(imageBase=base,resourceValiditySource=source,helpers=h,actualUsage=usage,hashSetContext=context,comparer=comparer,valueLayouts=fields)
 loader=ctx.index.types['Beyond.Resource.SimpleAssetLoader'];own_fields=[list(ctx.field(image.type_name(loader.index)+'::'+image.metadata.string(f.name_index)))
  for f in image.metadata.fields_for(loader)if not ctx.field_attributes(f.type_index)&16]
 proof['retainedSetField'],=[f for f in own_fields if f[2]==r['setReferenceFieldOffset']]
 methods=[m for m in image.metadata.methods_for(loader)if image.method_pointer_va(m)==base+h['retain']['entryRva']]
 proof['retainerMethods']=[dict(definition=m.index,typeName=image.type_name(m.declaring_type),name=image.metadata.string(m.name_index),
  parameters=[ctx.type_name(p.type_index)for p in image.metadata.parameters_for(m)],returnType=ctx.type_name(m.return_type),static=bool(m.flags&16),targetRva=image.method_pointer_va(m)-base)for m in methods]
 proof['programs']=_programs(proof)
 value=packets.norm(dict(schema=SCHEMA,status='validated-conditional-retain-outer-source',nativeInputs=pins,proof=proof,
  sameWholeHandleAndPaddingTransferredProved=True,selectedSpareSetInsertionAndFramesProved=True,
  actualHashInterfaceAndValueTransfersProved=True,selectedNativeAndChildHashEffectsProved=False,
  actualRuntimeComparerTableOrValueObserved=False,runtimeInvocationObserved=False,playbackProved=False,
  conditions=['Same valid stable LoaderHandle/Handle20 value, disabled collector and absent replacement. LoaderHandle contains exactly the own Handle value at its first payload byte; no nominal width alias is used.',
   'Existing nonnull HashSet storage/comparer/slots/buckets, positive bucket count, empty selected bucket, negative free-list, spare next slot and nonwrapping counters are required. The same full20 bytes, including padding, are written to that slot.',
   'Actual comparer interface, selected GenericEqualityComparer callback/MethodInfo pair and its own closed Handle context are coherent. Native value hashing and any boxed child callbacks require independent effect proofs; no hash-null-array branch is selected from width or from this wrapper alone.']))
 validate_outer(value,pins);_publication_gate(image,pins);return value


def validate_outer(value,pins):
 need('outer-source-envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-retain-outer-source'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('sameWholeHandleAndPaddingTransferredProved','selectedSpareSetInsertionAndFramesProved','actualHashInterfaceAndValueTransfersProved'))
  and all(value.get(k)is False for k in('selectedNativeAndChildHashEffectsProved','actualRuntimeComparerTableOrValueObserved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];source=p['resourceValiditySource'];packets.validate(source,pins)
 need('exact-helper-roles',set(p['helpers'])=={'retain','add','indexedContext','hashInvoke','valueHash'})
 q=_programs(p);need('full-outer-program-replay',q==p['programs'])
 asset=source['proof']['resourceSource']['proof']['assetSource'];need('actual-asset-retention-call',p['helpers']['retain']==packets._parent_packet(asset['proof']['children']['retain-loader-handle'],base))
 r=q['retain'][-1];u=p['actualUsage'];need('actual-whole-Handle-HashSet-request',u['tag']==6 and u['typeName']==HASHSET and u['methodName']=='Add'
  and u['classArguments']==[HANDLE]and u['methodArguments']==[]and u['instructionRva']+base==r['methodContextUsage']['instructionVa']and u['usageCellRva']+base==r['methodContextUsage']['cellVa'])
 need('same-independent-validity-and-add',r['validityCall']['targetVa']==base+source['proof']['helpers']['output']['entryRva']and r['addCall']['targetVa']==base+p['helpers']['add']['entryRva'])
 for c in q['add']['calls']:need('same-own-add-child:'+c['role'],c['targetVa']==base+p['helpers'][c['role']]['entryRva'])
 need('same-independent-indexed-context-source',p['helpers']['indexedContext']==source['proof']['helpers']['indexedContext'])
 for program in q['hash']:
  for c in program['calls']:
   target=source['proof']['classPreparation']['actualEntryRva']if c['role']=='prepareComparerClass'else p['helpers']['indexedContext'if c['role']=='indexedContext'else'valueHash']['entryRva']
   need('same-own-hash-child:'+c['role'],c['targetVa']==base+target)
 context=p['hashSetContext'];need('actual-selected-HashSet-class-context',context['typeName']==HASHSET and context['isMethod']is False and context['selectedSlots']==[0,16,17,18])
 by={r['relativeSlot']:r for r in context['entries']};row=by[16];arg,=row['classArguments']
 need('own-AddIfNotPresent-slot16',row['kind']==3 and row['typeName']==HASHSET and row['methodName']=='AddIfNotPresent'and row['methodArguments']==[]
  and bytes.fromhex(arg['rawHex'])[10]==19 and arg['parameterOwner']['typeIndex']==context['definition']and arg['parameterOwner']['ordinal']==0)
 row=by[18];a,=row['type']['classArguments'];need('own-same-T-IEqualityComparer-slot18',row['kind']==2 and row['type']['definition']['name']==INTERFACE and a==arg)
 c=p['comparer'];formal=c['parameterType'];need('own-GenericEqualityComparer-method',c['typeName']==COMPARER and c['methodName']=='GetHashCode'and c['returnType']=='int'
  and bytes.fromhex(formal['rawHex'])[10]==19 and formal['parameterOwner']['typeIndex']==c['typeDefinition']and formal['parameterOwner']['ordinal']==0)
 marker=q['hash'][0]['inlineCallbackTargetVa'];need('actual-Handle-comparer-callback-marker',any(r['pointer']==marker and c['definition']in r['methodDefinitionIndices']
  and len(r['classInstantiation']['arguments'])==1 and bytes.fromhex(r['classInstantiation']['arguments'][0]['raw_type_record_hex'])[10]==17
  and int.from_bytes(bytes.fromhex(r['classInstantiation']['arguments'][0]['raw_type_record_hex'])[:8],'little')==p['valueLayouts'][HANDLE]['typeDefinition']
  for r in c['registrations'])and all(r['runtimeSelectionObserved']is False for r in c['registrations']))
 row,=c['context']['entries'];need('same-T-indexed-comparer-context',c['context']['typeName']==COMPARER and c['context']['definition']==c['typeDefinition']and row['relativeSlot']==0 and row['kind']==2
  and bytes.fromhex(row['type']['rawHex'])[10]==19 and row['type']['parameterOwner']==formal['parameterOwner'])
 layouts=p['valueLayouts'];need('exact-nominal-wrapper-set',set(layouts)=={LOADER,HANDLE,'Beyond.Resource.FAssetProxyUntrackedHandle'})
 for name,v in layouts.items():need('actual-plain-value20-layout:'+name,v['typeName']==name and v['valueType']is True and v['enum']is False and v['parent']=='System.ValueType'and v['boxedBytes']==36)
 need('actual-LoaderHandle-single-field',layouts[LOADER]['fields']==[[LOADER,HANDLE,16]])
 need('actual-Handle-single-field',layouts[HANDLE]['fields']==[[HANDLE,'Beyond.Resource.FAssetProxyUntrackedHandle',16]])
 need('own-retained-Handle-set-field',p['retainedSetField']==['Beyond.Resource.SimpleAssetLoader',HASHSET+'<'+HANDLE+'>',r['setReferenceFieldOffset']])
 need('own-retainer-method-identity',bool(p['retainerMethods'])and all(m['typeName']=='Beyond.Resource.SimpleAssetLoader'and m['static']is False
  and m['name']=='HandleAsset'and m['parameters']==[HANDLE]and m['returnType']=='void'and m['targetRva']==p['helpers']['retain']['entryRva']for m in p['retainerMethods']))
 return value
