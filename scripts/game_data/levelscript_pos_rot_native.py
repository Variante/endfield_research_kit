"""Authenticate current PosRot wire grammar on a matching generated route."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,validate_typed_usage_context
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.memorypack import pooled_source_helper,wrapper_members

SCHEMA='endfield.levelscript-pos-rot-native-contract.v3'
LABEL='levelscriptPosRotNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_pos_rot_native.json'

def _validate_native(image,fact):
 ctx=NativeReferenceContext(image);wrappers={w.name:w for w in wrapper_members.derive_from_image(image).values()}
 for declaration in fact['declarations']:
  wrapper=wrappers[declaration['wrapperName']]
  if (wrapper.wrapped_type,[(m.name,m.declared_type) for m in wrapper.members],ctx.is_value_type(wrapper.wrapped_type))!=(declaration['originalType'],[tuple(m) for m in declaration['members']],declaration['originalIsValueType']):raise ValueError(LABEL+'.wrapper-declaration:'+wrapper.name)
  if ctx.field(wrapper.name+'::__instance')!=(wrapper.name,wrapper.wrapped_type,16):raise ValueError(LABEL+'.wrapper-holder:'+wrapper.name)
 for field in fact['originalFields']:
  if list(ctx.field(field[0]+'::'+field[1]))!=field[2]:raise ValueError(LABEL+'.original-field:'+field[1])
 for row in fact['methods']:image.validate_method_row(row,label=LABEL)
 image.check_windows(fact['codeWindows'],label=LABEL);image.check_instruction_windows(fact['instructionWindows'],label=LABEL)
 for flow in fact['registrations']:validate_eager_wrap_registration(image,flow,label=LABEL)
 for composition in fact['compositions']:validate_registered_formatter_composition(image,composition,label=LABEL)
 validate_generic_contexts(image,fact['genericContexts'],label=LABEL)
 for usage in fact['usageContexts']:validate_typed_usage_context(image,usage,label=LABEL)
 entries=GenericEntries(image)
 for row in fact['genericEntries']:
  actual=entries.resolve(row['definition'],row['classArguments'],row['methodArguments'])
  if actual['pointer']-image.pe.image_base!=row['pointerRva']:raise ValueError(LABEL+'.registered-entry:'+str(row['definition']))

def load_pos_rot_contract(*,game_root=None,contract_path=DEFAULT_CONTRACT,include_fact=True):
 audit=dict(validator=LABEL,source=str(contract_path),parentProofStatus='unresolved')
 try:
  if type(include_fact)is not bool:raise ValueError(LABEL+'.include-fact:bool-required')
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs'];audit['nativeInputs']=pins
  if (fact['schema'],fact['status'],fact['layout']['stringEncoding'])!=(SCHEMA,'exact-current-build','int32-pool-index') or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError(LABEL+'.contract:schema-or-inputs')
  root=Path(game_root) if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=root.parent/'GameAssembly.dll' if root else None,metadata=root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return {},dict(audit,status=gate.status,failedCheck='installed-native-inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return {},dict(audit,**failed)
  _validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return {},dict(audit,status=after.status,failedCheck='installed-native-inputs-after',detail=after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return {},dict(audit,**failed)
  if path.read_bytes()!=raw:raise ValueError(LABEL+'.contract:changed-during-validation')
  return fact if include_fact else {},dict(audit,status='validated',parentProofStatus='selected-generated-route',evidenceBoundary=fact['evidenceBoundary'])
 except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError) as error:return {},dict(audit,**native_validation_failure(error,label=LABEL,source_path=contract_path))

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--game-root',type=Path);parser.add_argument('--contract',type=Path,default=DEFAULT_CONTRACT);args=parser.parse_args();_,audit=load_pos_rot_contract(game_root=args.game_root,contract_path=args.contract);print(json.dumps(audit,indent=2));raise SystemExit(0 if audit['status']=='validated' else 2)
