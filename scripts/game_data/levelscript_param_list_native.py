"""Authenticate the current pooled ParamListForGraph stored representation."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition,validate_generic_contexts,validate_typed_usage_context
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.memorypack import pooled_source_helper,wrapper_members

CONTRACT_PATH=CONTRACTS_DIR/'levelscript_param_list.json'
SCHEMA='endfield.levelscript-template-param-list-native.v2'
LABEL='levelscriptParamListNative'


def _validate_native(image,fact):
 ctx=NativeReferenceContext(image);wrappers={w.name:w for w in wrapper_members.derive_from_image(image).values()}
 for declaration in fact['declarations']:
  name=declaration['wrapperName'];wrapper=wrappers[name]
  expected=[(m['name'],m['typeName']) for m in declaration['members']]
  if wrapper.wrapped_type!=declaration['typeName'] or [(m.name,m.declared_type) for m in wrapper.members]!=expected or ctx.is_value_type(wrapper.wrapped_type)!=declaration['originalIsValueType']:raise ValueError(LABEL+'.native:wrapper-members:'+name)
  for field in declaration['originalFields']:
   if list(ctx.field(declaration['typeName']+'::'+field['name']))!=field['field']:raise ValueError(LABEL+'.native:original-field:'+field['name'])
  if ctx.field(name+'::__instance')!=(name,wrapper.wrapped_type,16):raise ValueError(LABEL+'.native:wrapper-holder:'+name)
 for row in fact['methods']:image.validate_method_row(row,label=LABEL)
 image.check_windows(fact['codeWindows'],label=LABEL)
 image.check_instruction_windows(fact['instructionWindows'],label=LABEL)
 for flow in fact['registrations']:validate_eager_wrap_registration(image,flow,label=LABEL)
 for composition in fact['compositions']:validate_registered_formatter_composition(image,composition,label=LABEL)
 validate_generic_contexts(image,fact['genericContexts'],label=LABEL)
 for usage in fact['usageContexts']:validate_typed_usage_context(image,usage,label=LABEL)


def validate_param_list_for_graph_native_contract(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw)
  if (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build') or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'} or fact['layout']['stringEncoding']!='int32-pool-index':raise ValueError(LABEL+'.contract:schema-or-layout')
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-paths-required')
  root=Path(game_root) if game_root is not None else None;pins=fact['nativeInputs']
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  _validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes():raise ValueError(LABEL+'.contract:changed-during-validation')
  return dict(status='validated',layout=fact['layout'],nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
 except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)


def load_param_list_for_graph_contract(*,game_root=None,contract_path=CONTRACT_PATH):
 audit=validate_param_list_for_graph_native_contract(game_root=game_root,contract_path=contract_path)
 return (audit['layout'] if audit['status']=='validated' else None),audit


if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=CONTRACT_PATH if name=='contract' else None)
 args=parser.parse_args();result=validate_param_list_for_graph_native_contract(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='validated' else 2)
