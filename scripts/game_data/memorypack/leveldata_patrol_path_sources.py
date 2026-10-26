"""Selected warm ordinary path caller and its result/input cache store.

The actual prefix predicate selects the ordinary path child. Its normal result
is returned unchanged and cached together with the unchanged input. The result
is a path-hash QWORD; the second cache lane is the input string reference. Collector
disabled, initialized metadata/classes and compatible static storage are source
conditions; this does not infer a live cached path or asset identity.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.story-patrol-path-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolPath.'+check)


def program(regions,entry,*,hash_prefix=False,lock_taken=True):
 need('literal-prefix-and-lock-selections',type(hash_prefix)is bool and type(lock_taken)is bool)
 g=BytesPath(regions,entry);g.take('48895c2420','4889542410','48894c2408','57','4883ec40','488bd9')
 ready=g.relative('803d')+1;g.take('00');g.branch('75',True,1)
 g.take('33ff','48897c2460','40887c2458','4885db');g.branch('0f84',False)
 usage=g.at;cell=g.relative('488b0d');g.take('39b9e0000000');g.branch('75',True,1)
 prefix_ready=g.relative('40383d');g.branch('75',True,1);g.take('4533c9','41b805000000')
 prefix_usage=g.at;literal=g.relative('488b15');g.take('488bcb');prefix_site=g.at;prefix_target=g.relative('e8')
 g.take('84c0');g.branch('0f84',not hash_prefix);acquire=None;release=None
 if hash_prefix:
  need('same-class-cell-hash-path',g.relative('488b05')==cell);g.take('39b8e0000000');g.branch('75',True,1)
  g.take('488b80b8000000','488b4808','48894c2460','40887c2458','48897c2428','488d442458','4889442430',
   '488d442460','4889442438','807c245800');g.branch('0f85',False)
  g.take('488b4c2460','4885c9');g.branch('0f84',False);g.take('baffffffff');acquire_site=g.at;acquire_target=g.relative('e8')
  acquire=dict(instructionVa=acquire_site,targetVa=acquire_target,arguments=dict(rcx='same static field at byte8',edx=-1),
   resultStoredToLocalByte=88,normalCallRequired=True,effectsProved=False)
  g.take('88442458');need('same-class-cell-locked-hash-path',g.relative('488b0d')==cell)
  g.take('83b9e000000000');g.branch('75',True,1);g.take('488bcb');ordinary_site=g.at;ordinary=g.relative('e8')
  g.take('488bf8','807c245800');g.branch('74',not lock_taken,1)
  if lock_taken:
   g.take('488b4c2460');release_site=g.at;release_target=g.relative('e8');release=dict(instructionVa=release_site,
    targetVa=release_target,arguments=dict(rcx='unchanged same lock-object local'),effectsProved=False)
  g.at=g.relative('eb',1)
 else:
  need('same-class-cell-ordinary-path',g.relative('488b0d')==cell);g.take('83b9e000000000');g.branch('75',True,1)
  g.take('488bcb');ordinary_site=g.at;ordinary=g.relative('e8');g.take('488bf8')
 g.take('48897c2428','48895c2430')
 table=g.relative('488d1d');collector=g.relative('833d')+1;g.take('00');g.branch('74',True,1)
 need('same-class-cell-cache-store',g.relative('488b05')==cell);g.take('83b8e000000000');g.branch('75',True,1)
 g.take('0f10442428','488b80b8000000','0f114010')
 need('same-disabled-collector-cell',g.relative('833d')+1==collector);g.take('00');g.branch('74',True,1)
 g.take('488bc7','488b5c2468','4883c440','5f','c3')
 return dict(selectedBytes=g.seen,entry=entry,metadataReadyCell=ready,prefixMetadataReadyCell=prefix_ready,
  classUsageInstructionVa=usage,classCell=cell,prefixUsageInstructionVa=prefix_usage,prefixStringCell=literal,
  prefixInstructionVa=prefix_site,prefixTargetVa=prefix_target,prefixArguments=dict(rcx='unchanged input string',
   rdx='actual owned string-literal usage',r8d=5,r9d=0),selectedPrefixPredicateReturnsFalseRequired=not hash_prefix,
  hashPrefix=hash_prefix,selectedLockTakenBool=lock_taken if hash_prefix else None,acquireCall=acquire,releaseCall=release,
  ordinaryPathInstructionVa=ordinary_site,ordinaryPathTargetVa=ordinary,ordinaryPathArguments=dict(rcx='unchanged input string'),
  collectorCell=collector,selectedCollectorDisabledRequired=True,unusedCollectorTableBase=table,
  staticFieldsPointerOffset=184,cachePairStaticOffset=16,cachePairBytes=16,
  cacheSourceSlices=[dict(offset=0,bytes=8,value='unchanged ordinary helper result QWORD'),dict(offset=8,bytes=8,value='unchanged input string reference')],
  returnedHelperResultUnchanged=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],normalReturn=True,
  prefixAndOrdinaryChildEffectsProved=False,liveCacheOrAssetIdentityProved=False)


def ordinary_program(regions,entry,*,nonnull=True,nonempty=True,length_offset=16,char_offset=20):
 need('literal-string-source-branches',type(nonnull)is bool and type(nonempty)is bool and(nonnull or not nonempty))
 need('owned-small-string-field-offsets',all(type(n)is int and 0<=n<128 for n in(length_offset,char_offset)))
 g=BytesPath(regions,entry);g.take('4883ec28','4885c9');g.branch('74',not nonnull,1)
 if nonnull:g.take('8379'+bytes((length_offset,)).hex()+'00');g.branch('76',not nonempty,1)
 if not nonempty:
  g.take('33c0');g.at=g.relative('eb',1);g.take('4883c428','c3')
  return dict(selectedBytes=g.seen,entry=entry,nonnull=nonnull,nonempty=False,resultQword=0,
   entryRspRestored=True,nonvolatilesUnchanged=True,normalReturn=True,hashChildEffectsProved=False)
 g.take('48895c2420','488d59'+bytes((char_offset,)).hex());usage=g.at;cell=g.relative('488b0d')
 g.take('83b9e000000000');g.branch('74',False,1);g.take('33d2','488bcb','488b5c2420','4883c428')
 site=g.at;target=g.relative('e9')
 return dict(selectedBytes=g.seen,entry=entry,nonnull=True,nonempty=True,lengthOffset=length_offset,charOffset=char_offset,
  classUsageInstructionVa=usage,classCell=cell,selectedClassInitializedRequired=True,hashInstructionVa=site,hashTargetVa=target,
  hashArguments=dict(rcx='same input string first UTF16 character address',edx=0),
  inputUtf16TerminatingZeroAndCompatibleStableStorageRequired=True,entryRspRestored=True,
  nonvolatilesRestored=['rbx'],normalTail=True,hashChildEffectsProved=False)


def data_program(regions,entry):
 g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=g.relative('803d')+1;g.take('00','488bd9');g.branch('74',False,1)
 first_usage=g.at;first_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
 replacements=g.relative('488b05');g.take('488b4878','4885c9');g.branch('0f85',False)
 second_usage=g.at;second_cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
 g.take('33d2','488bcb','4883c420','5b');site=g.at;target=g.relative('e9')
 return dict(selectedBytes=g.seen,entry=entry,metadataReadyCell=ready,
  classUsageInstructions=[first_usage,second_usage],classCells=[first_cell,second_cell],
  replacementRootCell=replacements,selectedReplacementReceiverAt120RequiredNull=True,
  tailInstructionVa=site,tailTargetVa=target,tailArguments=dict(rcx='unchanged original input path string',edx=0),
  entryRspRestored=True,nonvolatilesRestored=['rbx'],normalTail=True,childEffectsProved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
 from scripts.game_data.memorypack import leveldata_patrol_lookup_sources as lookup_owner,pointer_param as pointer
 _publication_gate(image,pins);base=image.pe.image_base;lookup=lookup_owner.derive(image,pins)
 child=lookup['proof']['tailChildren']['process-path'];body=pointer.owned(image,base+child['entryRva']);p=program(body['regions'],body['pointer'])
 programs=[p,program(body['regions'],body['pointer'],hash_prefix=True,lock_taken=False),
  program(body['regions'],body['pointer'],hash_prefix=True,lock_taken=True)]
 usage=derive_typed_usage_context(image,p['classUsageInstructionVa']-base,label='storyPatrolPath.class')
 need('same-nominal-HashStringPathProcessor-class',usage.get('tag')==1 and usage.get('typeName')=='Beyond.Resource.HashStringPathProcessor')
 from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
 ctx=NativeReferenceContext(image);td=ctx.index.types['Beyond.Resource.HashStringPathProcessor']
 cache,=[f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)=='s_currentHashString']
 need('actual-distinct-hash-and-string-cache-lanes',ctx.field_attributes(cache.type_index)&16 and
  ctx.type_name(cache.type_index)=='System.ValueTuple`2<long,string>'and
  runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index)['s_currentHashString']==p['cachePairStaticOffset'])
 # The actual direct helper is not required to equal an ordinary named method
 # pointer. Retain the exact selected code and the table observation separately;
 # absence does not fabricate a canonical method or pointer alias.
 names=image.body_index.names_by_pointer.get(body['pointer'],[])
 # String literal selection remains an actual code-registration usage, rather
 # than a name/namespace inference or an invented generic MethodInfo request.
 md=image.metadata;section=md.sections['stringLiteral'];data=md.sections['stringLiteralData'];raw=image.pe.bytes_at_va(p['prefixStringCell'],8)
 literal_index=unresolved_usage_index(raw,section.size//8,tag=5,source='storyPatrolPath.literal',offset=p['prefixStringCell'])
 start,length=literal_record(md.buf[section.offset+literal_index*8:section.offset+(literal_index+1)*8],data.size,source='storyPatrolPath.literal',offset=literal_index*8)
 literal=dict(index=literal_index,usageRawHex=raw.hex(),utf8Hex=md.buf[data.offset+start:data.offset+start+length].hex(),
  value=md.buf[data.offset+start:data.offset+start+length].decode('utf-8'),liveStringObjectObserved=False)
 children={}
 for role,target in(('prefix',p['prefixTargetVa']),('ordinary',p['ordinaryPathTargetVa']),('hash-path',programs[-1]['ordinaryPathTargetVa'])):
  b=pointer.owned(image,target);children[role]=dict(entryRva=target-base,sourceWindows=b['windows'],sourceRegions=[[a,h.hex()]for a,h in b['regions']],rows=b['rows'],effectsProved=False)
 string_fields={name:list(ctx.field('System.String::'+name))for name in('_stringLength','_firstChar')}
 need('own-managed-String-fields',string_fields['_stringLength'][:2]==['System.String','int']and
  string_fields['_firstChar'][:2]==['System.String','char'])
 ob=pointer.owned(image,p['ordinaryPathTargetVa']);ordinary_programs=[ordinary_program(ob['regions'],ob['pointer'],
  nonnull=n,nonempty=z,length_offset=string_fields['_stringLength'][2],char_offset=string_fields['_firstChar'][2])
  for n,z in((False,False),(True,False),(True,True))]
 hash_body=pointer.owned(image,ordinary_programs[-1]['hashTargetVa'])
 hash_source=dict(entryRva=hash_body['pointer']-base,sourceWindows=hash_body['windows'],sourceRegions=[[a,h.hex()]for a,h in hash_body['regions']],rows=hash_body['rows'],effectsProved=False)
 db=pointer.owned(image,programs[-1]['ordinaryPathTargetVa']);dp=data_program(db['regions'],db['pointer'])
 data_body=pointer.owned(image,dp['tailTargetVa']);data_source=dict(entryRva=data_body['pointer']-base,sourceWindows=data_body['windows'],
  sourceRegions=[[a,h.hex()]for a,h in data_body['regions']],rows=data_body['rows'],effectsProved=False)
 data_usages=[derive_typed_usage_context(image,a-base,label='storyPatrolPath.dataClass')for a in dp['classUsageInstructions']]
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-warm-nonhash-path-source',nativeInputs=pins,
  proof=dict(lookupSource=lookup,sourceWindows=body['windows'],sourceRegions=[[a,h.hex()]for a,h in body['regions']],program=p,programs=programs,
   actualClassUsage=usage,registeredSourceMethodCandidates=names,registeredSourceMethodIdentityResolved=False,
   cacheField=dict(index=cache.index,typeName=ctx.type_name(cache.type_index),rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(cache.type_index),16).hex()),
   prefixStringUsageCellRva=p['prefixStringCell']-base,prefixString=literal,children=children,
   nominalStringFields=string_fields,ordinaryPrograms=ordinary_programs,hashSource=hash_source,
   dataProgram=dp,dataClassUsages=data_usages,dataHashSource=data_source),
  selectedPathArgumentsCachePairAndResultFrameProved=True,prefixAndOrdinaryChildEffectsProved=False,
  runtimeInvocationObserved=False,playbackProved=False,wholeConversionProved=False,
  evidenceBoundary=dict(exact='Actual warm non-hash prefix predicate and ordinary helper arguments, returned path-hash QWORD, complete frame and disabled-collector static16-byte hash/string cache store.',
   conditional=__doc__,unresolved=['actual prefix-string/ordinary path child effects','hash-path alternative','live asset/cache/class selection']))))
