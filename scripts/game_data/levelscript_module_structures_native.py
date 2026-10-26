"""Authenticate the current conditional RollingStone/Launcher stored wire profile."""
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,validate_typed_usage_context
from scripts.game_data.memorypack import module_structure_models as models,module_structure_joins as joins,pooled_source_helper,wrapper_members
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs

CONTRACT_PATH=CONTRACTS_DIR/'levelscript_module_structures_native.json'
SCHEMA='endfield.levelscript-module-structures-native.v2'
LABEL='levelscriptModuleStructuresNative'


def need(check,expected,actual):
 if expected!=actual:raise ValueError(LABEL+'.'+check+':expected='+str(expected)[:240]+',actual='+str(actual)[:240])


def _validate_native(image,fact):
 base=image.pe.image_base;ctx=NativeReferenceContext(image);symbols=ContextSymbols(image);entries=GenericEntries(image);wrappers={w.name:w for w in wrapper_members.derive_from_image(image).values()}
 for d in fact['declarations']:
  w=wrappers[d['wrapper']];need('wrapper-original',d['original'],w.wrapped_type);need('wrapper-order',d['members'],[[m.name,m.declared_type]for m in w.members])
  for owner,name,typ,offset in d['fields']:need('owned-field:'+owner+'::'+name,(owner,typ,offset),ctx.field(owner+'::'+name))
 for child,parent in fact['parents']:need('parent:'+child,parent,ctx.parent(child))
 for row in fact['methods']:image.validate_method_row(row,label=LABEL)
 for p in fact['ownedPrograms']:
  need('complete-owned-ranges',sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(p['entryRva'])['ranges']),sorted((w['startRva'],w['endRva'])for w in p['windows']));image.check_windows(p['windows'],label=LABEL)
 for c in fact['compositions']:validate_registered_formatter_composition(image,c,label=LABEL)
 validate_generic_contexts(image,fact['genericContexts'],label=LABEL)
 for usage in fact['usageContexts']:validate_typed_usage_context(image,usage,label=LABEL)
 for d in fact['genericEntries']:need('generic-registration',d['registration'],json.loads(json.dumps(entries.resolve(d['definition'],d['classArguments'],d['methodArguments']))))
 for name,expected in fact['formalListFields'].items():
  td=ctx.index.types['System.Collections.Generic.List`1'];field,=[f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)==name];need('formal-list-field:'+name,expected,symbols.type(ctx.type_pointer(field.type_index)))
 results=[]
 def decode(value):
  if isinstance(value,list):return [decode(v)for v in value]
  if not isinstance(value,dict):return value
  if set(value)=={'result'}:
   index=value['result']
   if type(index)is not int or not 0<=index<len(results):raise ValueError(LABEL+'.model-result-order')
   return results[index]
  if set(value)=={'region'}:
   r=value['region'];raw=image.pe.bytes_at_va(base+r['startRva'],r['length']);need('model-source-window',r['sha256'],hashlib.sha256(raw).hexdigest().upper());return (base+r['startRva'],raw)
  return {k:decode(v)for k,v in value.items()}
 required={'rolling_holder','rolling_owned_prehook','rolling_owned_factory','rolling_owned_reference_setter','rolling_owned_strict_cast','module_caller','launcher_caller','launcher_setter','launcher_factory','float_list','float_constructor','float_add','float_provider','dictionary','enclosing_union','enclosing_root_field','enclosing_header','bridge_packable_return','bridge_list_callback','reference_list','provider_cache_type_from_handle','provider_cache_provider','provider_success'}
 need('required-source-models',required,{r['model']for r in fact['modelCalls']})
 r=fact['components'];need('root-modules-field',tuple(r['enclosing']['rootField']['field']),ctx.field('Beyond.Gameplay.LevelScriptData::modules'));need('root-wrapper-holder',('Beyond.MemoryPack.Beyond_Gameplay_LevelScriptDataForMemoryPack','Beyond.Gameplay.LevelScriptData',16),ctx.field('Beyond.MemoryPack.Beyond_Gameplay_LevelScriptDataForMemoryPack::__instance'));expected={'rolling_holder':base+r['rollingOwned']['typedGetter']['accessor'][3],'dictionary':r['enclosing']['dictionary']['registration']['pointer'],'reference_list':r['lists']['entry']['pointer'],'float_list':r['floats']['entry']['pointer'],'enclosing_union':int(r['enclosing']['moduleUnion']['switch']['dispatcherVa'],16),'enclosing_root_field':base+r['enclosing']['rootField']['typedContext']['instructionRva']-3}
 for row in fact['modelCalls']:
  name=row['model']
  if name in expected:need('model-entry:'+name,expected[name],row['args'][1])
  if name=='module_caller':need('rolling-caller-widths',['byte','qword','reference'],row['args'][3]);need('rolling-caller-kind',False,row['kwargs'].get('rune',False))
  if name not in required:raise ValueError(LABEL+'.unknown-source-model:'+str(name))
  results.append(getattr(models,name)(*decode(row['args']),**decode(row['kwargs'])))
 c=fact['components'];joins.validate_owned_values(image,fact['nativeInputs'],c);wire=joins.validate_wire_joins(image,fact['nativeInputs'],c);joins.validate_base_routes(image,c,wire)
 switch=read_union_switch(image,'Beyond_Gameplay_LevelScriptModuleDataForMemoryPack');need('current-union',c['enclosing']['moduleUnion']['switch'],switch)
 route,=[r for r in switch['entries']if r['wrapperName']==c['rollingOwned']['wrapper']]
 return dict(rollingTag=route['tag'],moduleTypes=['RollingStoneControllerData'],evidenceBoundary=fact['evidenceBoundary'])


def validate(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 before=snapshot_complete_reader_inputs()
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);need('schema',SCHEMA,fact['schema']);need('status','conditional-current-build-wire',fact['status']);need('codec-kinds',['RollingStoneControllerData'],fact['codecKinds']);need('native-input-set',{'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'},set(fact['nativeInputs']))
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.both-native-paths-required')
  root=Path(game_root)if game_root is not None else None;pins=fact['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  dependencies=[Path(models.__file__),Path(joins.__file__),CONTRACTS_DIR/'memorypack_reader_clones_native.json',CONTRACTS_DIR/'levelscript_entity_ptr_param_native.json'];saved=[p.read_bytes()for p in dependencies]
  result=_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  need('contract-unchanged',raw,path.read_bytes());need('dependencies-unchanged',saved,[p.read_bytes()for p in dependencies]);need('complete-reader-inputs-unchanged',before,snapshot_complete_reader_inputs())
  return dict(status='validated',nativeInputs=pins,**result)
 except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)
