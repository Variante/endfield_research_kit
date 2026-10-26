"""Patrol Count's conditional Object-normalized method-key source selection.

The instruction algorithms are shared with enum source auditors; no enum
nominal, formatter, placeholder or wire proof is imported. The actual Count
registration is independently List<object>.get_Count. Its three-pointer key,
static row/triple publication, selected insert/duplicate paths, normalized
lookup and native pointer projection are joined by their exact source cells.
Initialized tables, normal descriptor/setup/allocator/lock effects and actual
inflated List<Point>/ICollection MethodInfo identity remain conditions.
"""
import json
import struct

SCHEMA='endfield.story-patrol-method-selection-source.v1'


def need(check,condition):
 if not condition:raise ValueError('storyPatrolMethodSelection.'+check)


def join_programs(selection,seed,keys,insertion,*,primitive_entry,registration_cell):
 need('same-actual-reference-normalizer',selection.get('normalizerTarget')==primitive_entry)
 need('same-selected-static-registration-seed',seed.get('registrationCell')==registration_cell)
 need('both-complete-MethodSpec-cache-paths',len(keys)==2 and {p.get('cold')for p in keys}=={False,True})
 cold=next(p for p in keys if p['cold'])
 need('same-cold-MethodSpec-registration-cell',cold.get('registrationCell')==registration_cell)
 need('same-full-pointer-key-table',len(insertion)==2 and {p.get('duplicate')for p in insertion}=={False,True}
  and all(p.get('slotsCell')==selection.get('slotsCell')and p.get('capacityCell')==selection.get('capacityCell')
   and p.get('slotKeyOffset')==selection.get('slotKeyPointerOffset')and p.get('slotTripleOffset')==selection.get('slotValuePointerOffset')for p in insertion))
 need('all-duplicate-and-lookup-key-pointers-compared',selection.get('keyQwordOffsets')==[0,8,16]
  and next(p for p in insertion if p['duplicate']).get('comparedKeyQwordOffsets')==[0,8,16])
 return dict(selectedMethodSpecKeyAndTripleSourceProved=True,conditionalNormalizedCountPointerProjectionProved=True,
  initializedMethodKeyTableIdentityProved=False,actualInflatedCountCallbackIdentityObserved=False)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp import enum_nominal_callback_sources as anchors,enum_method_pointer_selection as select
 from scripts.game_data.il2cpp import enum_method_table_seed_paths as seed_owner,enum_method_table_insertion_paths as insert_owner
 from scripts.game_data.il2cpp import enum_method_key_construction as key_owner
 from scripts.game_data.il2cpp.enum_instantiation_seed_paths import _complete_family
 from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
 from scripts.game_data.il2cpp.owned_partition import checked_rows
 from scripts.game_data.il2cpp.method_carrier_resolution import _project
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 from scripts.game_data.memorypack import leveldata_patrol_object_key_sources as object_key
 _publication_gate(image,pins);base=image.pe.image_base
 profile=json.loads(anchors.CONTRACT_PATH.read_bytes());anchors.validate_profile(profile,pins)
 key=object_key.derive(image,pins);normalization=key['proof']['ObjectLookupSource']['proof']['selectionSource']
 normal=normalization['proof']['selectedReferencePath'];registration=normalization['proof']['independentObjectRegistration']
 primitive=base+profile['sourceEntries']['primitiveEntryRva'];selection_entry=base+profile['sourceEntries']['selectionEntryRva']
 selection_body,rows,selection_cfg,padding=_complete_family(image,selection_entry)
 selected=select.program(selection_body['regions'],selection_entry)
 need('independent-actual-reference-normalization-entry',normal['selectedBytes'][0][0]==primitive and selected['normalizerTarget']==primitive)
 publication_entry=base+profile['fixupEntries']['publicationEntryRva']
 publication=select.registration_alias_program([(publication_entry,image.pe.bytes_at_va(publication_entry,42))],publication_entry,
  code_registration=image.code_registration,metadata_registration=image.metadata_registration)
 seed_body,rows,seed_cfg,seed_padding=_complete_family(image,base+profile['sourceEntries']['seedEntryRva'])
 seed=seed_owner.seed_program(seed_body['regions'],seed_body['pointer'])
 resolver,rows,resolver_cfg,resolver_padding=_complete_family(image,seed['methodKeyTarget'])
 keys=[seed_owner.key_program(resolver['regions'],resolver['pointer'],cold=cold)for cold in(False,True)]
 insert,rows,insert_cfg,insert_padding=_complete_family(image,seed['insertionTarget'])
 inserts=[insert_owner.program(insert['regions'],insert['pointer'],duplicate=duplicate)for duplicate in(False,True)]
 joined=join_programs(selected,seed,keys,inserts,primitive_entry=primitive,registration_cell=publication['metadataRegistrationCell'])
 need('same-selection-and-insertion-hash',all(p['hashPrime']==int.from_bytes(bytes.fromhex(raw)[3:],'little',signed=True)
  for p in inserts for at,raw in selected['selectedBytes']if raw.startswith('4c69c9')and len(bytes.fromhex(raw))==7))
 cold=next(p for p in keys if p['cold'])
 definition,rows,definition_cfg,definition_padding=_complete_family(image,cold['methodDefinitionTarget'])
 definitions=[key_owner.definition_program(definition['regions'],definition['pointer'],cold=cold)for cold in(False,True)]
 constructor,rows,constructor_cfg,constructor_padding=_complete_family(image,cold['keyConstructorTarget'])
 constructed=[key_owner.key_program(constructor['regions'],constructor['pointer'],miss=miss)for miss in(False,True)]
 object_lookup=key['proof']['ObjectLookupSource']['proof']
 need('same-actual-record-class-construction',definitions[1]['classResolverTarget']==object_lookup['recordClassPaths'][0]['selectedBytes'][0][0])
 projection,rows,projection_cfg,projection_padding=_complete_family(image,selected['projectionTarget'])
 g=BytesPath(projection['regions'],projection['pointer']);g.take('48895c2408');code_cell=g.relative('4c8b1d')
 need('actual-projection-uses-selected-code-alias',code_cell==publication['codeRegistrationAliasCell'])
 layout=dict(savedRbxHome=8,primaryCount=16,invokerCount=40,primaryPointers=24,adjustorPointers=32,invokerPointers=48)
 rows=[]
 for at,raw in projection['regions']:rows+=checked_rows(decode_enum_underlying_instructions(image.mapper,raw,at),raw,SCHEMA+'.projection')
 rows.sort(key=lambda r:int(r['va'],16));projected=_project(rows,base,dict(globals=dict(codeRegistrationCellRva=code_cell-base),projectionLayout=layout))
 spec_index=registration['methodSpecIndex'];spec=struct.unpack('<iii',image.pe.bytes_at_va(int(image.registration['methodSpecs'],16)+spec_index*12,12))
 method=normalization['proof']['countMethodDefinition'];klass=registration['classInstantiation'];row=registration['registration']
 need('own-Count-methodspec-class-and-null-method-instantiation',spec==(method,klass['index'],-1))
 row_address=int(image.registration['genericMethodTable'],16)+row['tableIndex']*16;raw=image.pe.bytes_at_va(row_address,16)
 need('same-current-Count-registration-row-and-triple',raw.hex().upper()==row['rawHex']and struct.unpack('<iiii',raw)==(spec_index,*row['indices']))
 need('actual-Count-static-instantiation-array-pointer',image.pe.u64_at_va(int(image.registration['genericInsts'],16)+spec[1]*8)==klass['record_va'])
 need('selected-static-registration-array-layout',image.pe.u32_at_va(image.metadata_registration+32)==image.registration['genericMethodTableCount']
  and image.pe.u64_at_va(image.metadata_registration+40)==int(image.registration['genericMethodTable'],16)
  and image.pe.u64_at_va(image.metadata_registration+72)==int(image.registration['methodSpecs'],16)
  and image.pe.u64_at_va(image.metadata_registration+24)==int(image.registration['genericInsts'],16))
 indices=row['indices'];need('Count-projection-actual-bounded-primary-invoker-no-adjustor',0<=indices[0]<image.pe.u32_at_va(image.code_registration+16)
  and 0<=indices[1]<image.pe.u32_at_va(image.code_registration+40)and indices[2]==-1)
 primary=image.pe.u64_at_va(image.code_registration+24);invokers=image.pe.u64_at_va(image.code_registration+48)
 need('same-actual-static-Count-pointer',image.pe.u64_at_va(primary+indices[0]*8)==registration['pointer'])
 def capture(body,cfg,pad):return dict(sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']],completeCfg=cfg,padding=pad)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-Count-key-seed-and-selection-source',nativeInputs=pins,
  proof=dict(ObjectKeySource=key,selectedNormalizedLookup=selected,selection=capture(selection_body,selection_cfg,padding),
   registrationPublication=publication,selectedMethodSeed=seed,methodSeed=capture(seed_body,seed_cfg,seed_padding),
   MethodSpecCachePrograms=keys,MethodSpecCache=capture(resolver,resolver_cfg,resolver_padding),
   selectedKeyTripleInsertions=inserts,keyTripleInsertion=capture(insert,insert_cfg,insert_padding),
   methodDefinitionPrograms=definitions,methodDefinition=capture(definition,definition_cfg,definition_padding),
   keyConstructorPrograms=constructed,keyConstructor=capture(constructor,constructor_cfg,constructor_padding),
   projectionProgram=projected,projection=capture(projection,projection_cfg,projection_padding),
   selectedStaticCountRow=dict(methodDefinition=method,methodSpecIndex=spec_index,rawMethodSpec=spec,rawRegistrationRowHex=raw.hex().upper(),
    actualClassInstantiationPointer=klass['record_va'],actualMethodInstantiationPointer=None,indexTripleAddress=row_address+4,
    primaryPointer=registration['pointer'],invokerPointer=image.pe.u64_at_va(invokers+indices[1]*8))),**joined,
  methodDefinitionSetupAndCanonicalKeyIdentityProved=False,actualNominalPointCountCallbackProved=False,
  wholeConversionProved=False,runtimeInvocationObserved=False,playbackProved=False,
  evidenceBoundary=dict(exact='Current Count static MethodSpec/row/triple, actual three-pointer key construction/cache/insert/selection and projection source, same registration/table cells and separate reference/null normalization.',
   conditional=__doc__,unresolved=['method descriptor/setup and canonical interner/MethodInfo identity','reservation/resize/collision/table history and opaque aliases','runtime inflated receiver/interface callback selection','complete consumer semantics and playback']))))
