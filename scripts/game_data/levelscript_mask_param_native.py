"""Authenticate pooled mask Params; positive masks require a null stored curve."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts,validate_typed_usage_context,_vtable
from scripts.game_data.memorypack import mask_param as proof,pooled_source_helper
from scripts.game_data.memorypack.wrapper_members import unmanaged_value_sizes_from_image
SCHEMA='endfield.levelscript-mask-param-native.v2'
LABEL='levelscriptMaskParamNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_mask_param_native.json'


def _contract(path):
 fact=json.loads(Path(path).read_bytes())
 if (set(fact)!={'schema','status','nativeInputs','profile','proof','positive','layout','evidenceBoundary'} or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build') or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}):raise ValueError(LABEL+'.contract:shape')
 return fact


def _validate_native(image,fact):
 actual=proof.derive(image,fact['nativeInputs'],fact['profile']);validate_claims(fact['proof'],actual,label=LABEL+'.nullProof');validate_claims(actual,fact['proof'],label=LABEL+'.nullDeclaration')
 positive=fact['positive'];ctx=NativeReferenceContext(image);base=image.pe.image_base
 for field in positive['fields']:
  if list(ctx.field(proof.VALUE+'::'+field['name']))!=field['field']:raise ValueError(LABEL+'.positive:field:'+field['name'])
 audio=positive['audioType']
 if not ctx.is_value_type(audio) or unmanaged_value_sizes_from_image(image).get(audio)!=16:raise ValueError(LABEL+'.positive:managed-audio-width')
 for row in positive['audioFields']:
  if ctx.field(audio+'::'+row['name'])!=(audio,row['typeName'],row['offset']+16):raise ValueError(LABEL+'.positive:audio-field:'+row['name'])
  kind=row['typeName'];code='f' if kind=='float' else 'B' if kind=='bool' or ctx.is_enum(kind) and ctx.field(kind+'::value__')[1]=='byte' else None
  if row['format']!=code:raise ValueError(LABEL+'.positive:audio-representation')
 if ctx.field('Beyond.Gameplay.CommonMaskType::value__')[1]!='int':raise ValueError(LABEL+'.positive:mask-enum-backing')
 for role,program in positive['programs'].items():
  entry=program['entryRva'];windows=program['windows'];owned=sorted(tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(entry)['ranges'])
  if owned!=sorted((w['startRva'],w['endRva']) for w in windows):raise ValueError(LABEL+'.positive:complete-owned-program:'+role)
  if 'method' in program:
   image.validate_method_row(program['method'],label=LABEL)
   if program['method'][3]!=entry:raise ValueError(LABEL+'.positive:entry-method:'+role)
  image.check_windows(windows,label=LABEL)
  for path in program['paths']:
   if not path or path[0][0]!=entry or any(not any(w['startRva']<=at<at+len(bytes.fromhex(raw))<=w['endRva'] for w in windows) for at,raw in path):raise ValueError(LABEL+'.positive:owned-path:'+role)
   image.check_instruction_windows(path,label=LABEL)
 for usage in positive['usageContexts']:validate_typed_usage_context(image,usage,label=LABEL)
 validate_generic_contexts(image,positive['genericContexts'],label=LABEL)
 curve=positive['curveFormatter'];image.validate_method_row(curve['method'],label=LABEL);_vtable(image,curve['definition'],5,curve['method'][0],LABEL)
 if ctx.parent(curve['method'][1])!='MemoryPack.MemoryPackFormatter`1<UnityEngine.AnimationCurve>':raise ValueError(LABEL+'.positive:curve-formatter-base')
 method=image.metadata.methods[curve['method'][0]];parameters=image.metadata.parameters_for(method)
 if method.flags&16 or method.slot!=5 or len(parameters)!=2 or ctx.type_name(method.return_type)!='void':raise ValueError(LABEL+'.positive:curve-formatter-abi')
 for parameter,name,kind in zip(parameters,('MemoryPack.MemoryPackReader','UnityEngine.AnimationCurve'),(0x11,0x12),strict=True):
  if ctx.type_name(parameter.type_index)!=name or image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)[10:12]!=bytes((kind,0x20)):raise ValueError(LABEL+'.positive:curve-formatter-byref')
 if fact['layout']!=dict(audioFields=positive['audioFields'],audioRawBytes=16,positiveConstantWireBytes=31,curveNullOnly=True):raise ValueError(LABEL+'.contract:positive-layout')
 return fact['layout']


def validate_mask_param_native_contract(*,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs']
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both paths required')
  root=Path(game_root) if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  strings=pooled_source_helper.CONTRACT_PATH.read_bytes();layout=_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes() or strings!=pooled_source_helper.CONTRACT_PATH.read_bytes():raise ValueError(LABEL+'.contract:declaration changed during validation')
  return dict(status='validated',codecKind='Param<CommonMaskBlendData>',memberCount=4,rawSize=8,pathEncoding='int32-pool-index',constantNullMarker=255,constantWireBytes=1,positiveConstantAdmitted=True,**layout,nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
 except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract' else None)
 args=parser.parse_args();result=validate_mask_param_native_contract(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='validated' else 2)
