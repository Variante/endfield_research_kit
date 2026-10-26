"""Finite ordinary Module children: fresh reader and Original adapter joins.

This source layer grants no field grammar, list, enclosing Module route or
root. It collects independent failures so a later complete graph need not
stop at the first unrelated child. Top-level Module wrappers use their own
already selected union transport instead of an unused Original adapter.
"""
import json

SCHEMA='endfield.story-module-record-sources.v1'
TYPES=(
 'Beyond.Gameplay.BeaconPoleControllerData+AltarInfo','Beyond.Gameplay.BeaconPoleControllerData+BeaconPoleInfo',
 'Beyond.Gameplay.BattlerStageData','Beyond.Gameplay.EncounterData+BattlePart','Beyond.Gameplay.EncounterData+IntroPart',
 'Beyond.Gameplay.EncounterData+TailPart','Beyond.Gameplay.ButterflyScatterSerializeInfo',
 'Beyond.Gameplay.RollingStoneControllerData+LauncherData','Beyond.Gameplay.TyphoeaArcheryObstacleData',
 'Beyond.Gameplay.TyphoeaArcheryTargetData','Beyond.Gameplay.TyphoeaArcheryExtraBattleInfo',
 'Beyond.Gameplay.TyphoeaArcheryMovementData','Beyond.Gameplay.TyphoeaArcheryMVSCScaleData')


def need(key,condition):
 if not condition:raise ValueError('storyModuleRecordSource.'+key)


def join_record(source,pair,adapter,pins):
 name=source.get('wrappedType');life=source.get('lifecycle',{});getter=life.get('GetValue',{})
 face=pair.get('composition',{}).get('interfaces',[])
 need('complete-exact-owned-class-reader',name in TYPES and source.get('schema')=='endfield.generated-concrete-reader-source.v1'
  and source.get('nativeInputs')==pins and source.get('completeSelectedCallerAdmitted')is True)
 need('same-own-Original-adapter',adapter.get('schema')=='endfield.reference-object-adapter-source.v1'
  and adapter.get('nativeInputs')==pins and adapter.get('typeName')==name and adapter.get('wrapperName')==source.get('wrapperName')
  and adapter.get('pair')==pair and adapter.get('getterMethod')==getter.get('method')and len(face)==1
  and face[0].get('formatterDeserializeMethodIndex')==life.get('concreteFormatter',{}).get('method',[None])[0]
  and adapter.get('getterReturnedReferenceSemanticsProved')is False)
 need('independent-complete-Original-reference-getter',getter.get('program',{}).get('fullReferenceOutput')is True
  or getter.get('ownedCoherentGetter',{}).get('coherentNonNullSamePointerReturn')is True)
 need('all-four-complete-reader-frames',len(source.get('programs',[]))==4
  and{(p.get('existing'),p.get('wrapperNull'))for p in source['programs']}=={(n,f)for n in(False,True)for f in(False,True)}
  and all(p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in source['programs']))
 return dict(typeName=name,source=source,pair=pair,adapter=adapter,ordinaryOriginalAdapterAdmitted=True,
  childGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive_adapter_for_source(image,pins,source):
 """Fresh adapter join; the caller separately owns the complete reader proof."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 _publication_gate(image,pins);name=source.get('wrappedType')
 need('explicit-source-nominal',name in TYPES and source.get('nativeInputs')==pins
  and source.get('completeSelectedCallerAdmitted')is True)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source.get('wrapperName')and w.wrapped_type==name]
 # These ordinary children have simple direct reference getters. Asking for
 # a complete unwind family would incorrectly reject their bounded leaf ABI.
 need('own-direct-reference-getter-profile',source.get('lifecycle',{}).get('GetValue',{}).get('program',{}).get('fullReferenceOutput')is True)
 pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrapper)
 result=join_record(source,pair,adapter,pins);_publication_gate(image,pins);return result


def derive_many(image,pins,*,type_names=None):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources
 import traceback
 names=list(TYPES)if type_names is None else type_names
 need('finite-explicit-class-selection',isinstance(names,(list,tuple))and 0<len(names)<=len(TYPES)
  and len(set(names))==len(names)and all(n in TYPES for n in names))
 _publication_gate(image,pins);ctx=NativeReferenceContext(image)
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in names}
 need('exact-fresh-class-wrappers',set(wrappers)==set(names)and all(not ctx.is_value_type(n)and not ctx.is_enum(n)for n in names))
 sources=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in names]);owners=[]
 for name,row in zip(names,sources['owners'],strict=True):
  try:
   need('complete-selected-reader:'+name,row.get('status')=='complete-reader-source-proved')
   proof=derive_adapter_for_source(image,pins,row['proof'])
   owners.append(dict(typeName=name,status='validated-conditional-module-record-source',proof=proof))
  except(ValueError,KeyError,TypeError,IndexError,RuntimeError,AttributeError)as error:
   owners.append(dict(typeName=name,status='pendingReview',reason=str(error)[:2200],errorType=type(error).__name__,
    source=row,diagnostic=dict(validator='storyModuleRecordSource',failedGate=str(error).split(':',1)[0],
     sourceStatus=row.get('status'),sourceReason=row.get('reason'),sourceDiagnostic=row.get('diagnostic'),
     sourcePath='scripts/game_data/memorypack/levelscript_module_record_sources.py',traceback=traceback.format_exc()[-8000:])))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,owners=owners,
  complete=[r['typeName']for r in owners if r['status']=='validated-conditional-module-record-source'],
  held=[r['typeName']for r in owners if r['status']=='pendingReview'],
  childGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
