"""Authenticate current pooled opera components; source owners remain separate."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,validate_typed_usage_context
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.memorypack import pooled_source_helper,wrapper_members
from scripts.game_data.levelscript_param_list_native import validate_param_list_for_graph_native_contract,CONTRACT_PATH as GRAPH_CONTRACT
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_encounter_opera_segments_native.json'
SCHEMA='endfield.levelscript-encounter-opera-segments-native.v3'
LABEL='levelscriptEncounterOperaNative'

def _validate_native(image,fact):
 ctx=NativeReferenceContext(image);base=image.pe.image_base;wrappers={w.name:w for w in wrapper_members.derive_from_image(image).values()}
 for row in fact['declarations']:
  wrapper=wrappers[row['wrapperName']]
  if wrapper.wrapped_type!=row['typeName'] or ctx.is_value_type(row['typeName'])!=row['originalIsValueType']:raise ValueError(LABEL+'.declaration:type')
  if row.get('members') is not None and [(m.name,m.declared_type) for m in wrapper.members]!=[(m['name'],m['typeName']) for m in row['members']]:raise ValueError(LABEL+'.declaration:members')
  if ctx.field(wrapper.name+'::__instance')!=(wrapper.name,wrapper.wrapped_type,16):raise ValueError(LABEL+'.declaration:holder')
  for field in row['fields']:
   if list(ctx.field(row['typeName']+'::'+field['name']))!=field['field']:raise ValueError(LABEL+'.declaration:field:'+field['name'])
  if row['originalIsValueType']:
   td=image.body_index.types[row['typeName']];sizes=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
   if (image.pe.u32_at_va(sizes),image.pe.u32_at_va(sizes+4))!=(32,0xffffffff):raise ValueError(LABEL+'.declaration:managed16-reference-value')
 if ctx.field('Beyond.Gameplay.EncounterData+OperaType::value__')[1]!='int':raise ValueError(LABEL+'.declaration:enum-backing')
 for row in fact['methods']:image.validate_method_row(row,label=LABEL)
 for program in fact['ownedPrograms']:
  owned=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(program['entryRva'])['ranges'])
  if owned!=sorted((p['startRva'],p['endRva']) for p in program['windows']):raise ValueError(LABEL+'.complete-owned-program:'+program['role'])
  image.check_windows(program['windows'],label=LABEL)
 image.check_windows(fact['leafWindows'],label=LABEL);image.check_instruction_windows(fact['instructionWindows'],label=LABEL)
 for flow in fact['registrations']:validate_eager_wrap_registration(image,flow,label=LABEL)
 for composition in fact['compositions']:validate_registered_formatter_composition(image,composition,label=LABEL)
 entries=GenericEntries(image)
 for row in fact['genericEntries']:
  actual=entries.resolve(row['definition'],row['classArguments'],row['methodArguments'])
  if json.loads(json.dumps(actual))!=row['registration']:raise ValueError(LABEL+'.generic-entry:'+str(row['definition']))
 validate_generic_contexts(image,fact['genericContexts'],label=LABEL)
 for usage in fact['usageContexts']:validate_typed_usage_context(image,usage,label=LABEL)

def validate_levelscript_encounter_opera_segments_native_contract(*,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs'];layout=fact['layout']
  if (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build') or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'} or layout!=dict(stringEncoding='int32-pool-index',memberCount=2,operaTypeFormat='<i',parametersType='Beyond.Gameplay.ParamKeyValue[]',maximumCount=16384,wholeOwnerAdmitted=False):raise ValueError(LABEL+'.contract:schema-or-layout')
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-paths-required')
  root=Path(game_root) if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  child_raw=GRAPH_CONTRACT.read_bytes();child=validate_param_list_for_graph_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
  if child['status']!='validated':return dict(status=child['status'],failedGate='param_key_value_child',detail=child.get('detail',''))
  if child['nativeInputs']!=pins:raise ValueError(LABEL+'.dependency:graph-inputs')
  _validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes() or child_raw!=GRAPH_CONTRACT.read_bytes():raise ValueError(LABEL+'.contract:changed-during-validation')
  return dict(status='validated',contract=fact,layout=layout,nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
 except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)
