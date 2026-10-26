"""Selected successful manifest lookup used by the actual Patrol resource request.

The native bucket and copied record representations are proved independently of
wire grammar. A valid stable bucket containing the requested raw key, bounded
indices and disabled collection are incoming conditions, not observed assets.
"""
from scripts.game_data.memorypack import leveldata_patrol_request_programs as paths
from scripts.game_data.memorypack import leveldata_patrol_resource_validity_sources as packets

SCHEMA='endfield.story-patrol-request-manifest-lookup-sources.v1'
OWNER='Beyond.ManifestBinary.RuntimeManifestBinary'
PACK=OWNER+'+AssetInfoPack'
DATA='Beyond.ManifestBinary.ManifestDataBinary'
ASSET=DATA+'+AssetInfo'
BUNDLE=DATA+'+Bundle'
MANAGER='Beyond.Resource.Runtime.BundleResourceManager'


def need(check,condition):
 if not condition:raise ValueError('patrolRequestLookup.'+check)


def _programs(p):
 b=p['imageBase'];h=p['helpers']
 return packets.norm(dict(request=paths.request(packets.raw(h['request'],b),b+h['request']['entryRva']),
  lookup=[paths.info_hit(packets.raw(h['lookup'],b),b+h['lookup']['entryRva'],failures=n)for n in range(4)]))


def induction(programs):
 bodies=[body for p in programs for body in p['failedProbeBodies']]
 need('one-identical-failed-probe',bodies and all(b==bodies[0]for b in bodies))
 return dict(countLimit=4096,countRegister='r14d',offsetRegister='r15',initialCount=0,initialOffset=0,
  countStep=1,byteStep=24,guardBeforeEachRecordRead=True,firstMatchingRawQwordRequired=True,
  proof='At the loop entry k equals R14D and R15 equals24*k. A failed raw QWORD comparison advances both once and returns to the same entry. The signed bucket count guard precedes every record access. A first matching record at k<count<=4096 returns its unchanged24 bytes; no counter or24*k arithmetic wraps in this domain.',
  selectedIndexContentsOrMatchObserved=False)


def _layout(image,ctx,symbols,name):
 from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
 td=ctx.index.types[name];offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index)
 at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 return dict(typeDefinition=td.index,typeName=name,parent=ctx.parent(name),valueType=ctx.is_value_type(name),
  boxedBytes=image.pe.u32_at_va(at),nativeBytes=image.pe.u32_at_va(at+4),
  fields=[dict(name=image.metadata.string(f.name_index),type=symbols.type(ctx.type_pointer(f.type_index)),
   offset=offsets[image.metadata.string(f.name_index)],static=bool(ctx.field_attributes(f.type_index)&16))for f in image.metadata.fields_for(td)])


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import leveldata_patrol_resource_handle_sources as parent
 _publication_gate(image,pins);source=parent.derive(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);symbols=ContextSymbols(image)
 h={'request':packets._parent_packet(source['proof']['callees']['request'],base)}
 r=paths.request(packets.raw(h['request'],base),base+h['request']['entryRva'])
 h['lookup']=packets.packet(image,next(c['targetVa']for c in r['calls']if c['role']=='info'))
 td=ctx.index.types[OWNER]
 m,=[m for m in image.metadata.methods_for(td)if image.metadata.string(m.name_index)=='TryGetAssetInfoFromPath'and image.method_pointer_va(m)==base+h['lookup']['entryRva']]
 method=dict(definition=m.index,typeDefinition=td.index,typeName=OWNER,name='TryGetAssetInfoFromPath',static=bool(m.flags&16),
  targetRva=image.method_pointer_va(m)-base,returnType=symbols.type(ctx.type_pointer(m.return_type)),
  parameters=[symbols.type(ctx.type_pointer(p.type_index))for p in image.metadata.parameters_for(m)])
 p=dict(imageBase=base,resourceHandleSource=source,helpers=h,method=method,
  layouts={n:_layout(image,ctx,symbols,n)for n in(OWNER,PACK,DATA,ASSET,BUNDLE,MANAGER)})
 p['programs']=_programs(p);p['recordInduction']=induction(p['programs']['lookup'])
 value=packets.norm(dict(schema=SCHEMA,status='validated-conditional-successful-manifest-lookup-source',nativeInputs=pins,proof=p,
  selectedManifestRecordSearchAndOutputProved=True,actualRequestAndFullFrameProved=True,
  loadedManifestContentsOrAssetIdentityObserved=False,wireGrammarAdmitted=False,missOrColdLookupEffectsProved=False,
  runtimeInvocationObserved=False,playbackProved=False,
  conditions=['The initialized selected RuntimeManifestBinary and ManifestDataBinary contain stable valid bucket/record/RefArray storage. The requested raw64 key has a first matching record in a bucket of1..4096 entries; that match is a condition, not an asset-existence observation.',
   'Bucket count is positive and below2^28; native addresses and record extents are valid/nonwrapping. The selected bundle index is nonnegative, below the RefArray count and its48-byte signed multiplication does not wrap.',
   'The actual metadata-ready byte and disabled collector predicates hold, the selected replacement receiver is null and the incoming writable80-byte byref output is valid. The exact named AssetInfoPack contains raw AssetInfo24, Bundle48 and the same manager reference8; no wire framing or native-marshal size is inferred.']))
 validate(value,pins);_publication_gate(image,pins);return value


def validate(value,pins):
 from scripts.game_data.memorypack import leveldata_patrol_resource_handle_sources as parent
 need('envelope',value.get('schema')==SCHEMA and value.get('status')=='validated-conditional-successful-manifest-lookup-source'and value.get('nativeInputs')==pins
  and all(value.get(k)is True for k in('selectedManifestRecordSearchAndOutputProved','actualRequestAndFullFrameProved'))
  and all(value.get(k)is False for k in('loadedManifestContentsOrAssetIdentityObserved','wireGrammarAdmitted','missOrColdLookupEffectsProved','runtimeInvocationObserved','playbackProved')))
 p=value['proof'];base=p['imageBase'];parent.validate(p['resourceHandleSource'],pins)
 need('actual-helper-set',set(p['helpers'])=={'request','lookup'})
 need('same-parent-request',p['helpers']['request']==packets._parent_packet(p['resourceHandleSource']['proof']['callees']['request'],base))
 q=_programs(p);need('complete-source-replay',q==p['programs']and p['recordInduction']==induction(q['lookup']))
 need('actual-request-E8',next(c['targetVa']for c in q['request']['calls']if c['role']=='info')==base+p['helpers']['lookup']['entryRva'])
 m=p['method'];args=m['parameters']
 need('own-actual-byref-method',m['typeName']==OWNER and m['name']=='TryGetAssetInfoFromPath'and m['static']is False
  and m['targetRva']==p['helpers']['lookup']['entryRva']and m['returnType']['name']=='bool'and len(args)==2
  and args[0]['name']=='long'and bytes.fromhex(args[0]['rawHex'])[10]==10
  and args[1]['name']==PACK and bytes.fromhex(args[1]['rawHex'])[10]==17 and bytes.fromhex(args[1]['rawHex'])[11]&127==32
  and int.from_bytes(bytes.fromhex(args[1]['rawHex'])[8:10],'little')&2==2)
 layouts=p['layouts'];need('exact-nominal-layout-set',set(layouts)=={OWNER,PACK,DATA,ASSET,BUNDLE,MANAGER})
 for n,size in((PACK,96),(ASSET,40),(BUNDLE,64)):
  x=layouts[n];need('own-value-layout:'+n,x['typeName']==n and x['valueType']is True and x['parent']=='System.ValueType'and x['boxedBytes']==size)
 for n in(OWNER,DATA,MANAGER):need('own-reference-layout:'+n,layouts[n]['typeName']==n and layouts[n]['valueType']is False)
 def field(n,name,typ,offset):
  r,=[f for f in layouts[n]['fields']if f['name']==name]
  need('own-field:'+n+'::'+name,r['type']['name']==typ and r['offset']==offset and r['static']is False)
 field(OWNER,'m_manifestData',DATA,16);field(OWNER,'m_bundleResourceManager',MANAGER,24)
 field(PACK,'assetData',ASSET,16);field(PACK,'bundleData',BUNDLE,40);field(PACK,'bundleResourceManager',MANAGER,88)
 need('exact-output-field-set',{f['name']for f in layouts[PACK]['fields']if not f['static']}=={'assetData','bundleData','bundleResourceManager'})
 field(ASSET,'pathHashHead','long',16);field(ASSET,'bundleIndex','int',28)
 field(DATA,'m_assetInfoAddress','byte*',152)
 field(DATA,'assetInfoDictionary','Beyond.ManifestBinary.RefMultiHashTable`2<string,'+ASSET+'>',64)
 field(DATA,'bundles','Beyond.ManifestBinary.RefArray`1<'+BUNDLE+'>',16)
 for name,args_ in(('assetInfoDictionary',['string',ASSET]),('bundles',[BUNDLE])):
  t=next(f['type']for f in layouts[DATA]['fields']if f['name']==name)
  need('actual-closed-storage:'+name,[a['name']for a in t['classArguments']]==args_ and bytes.fromhex(t['rawHex'])[10]==21)
 need('same-source-cell-domain',len({r['replacementRootCellVa']for r in q['lookup']}|{q['request']['replacementRootCellVa']})==1)
 return value
