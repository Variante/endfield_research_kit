"""Re-prove named task hooks on the selected build; never publish old addresses.

Hook entries identify methods and declared storage. They do not establish live
dispatch, ownership or execution. Inlined copies bypass named entry hooks.
"""
from __future__ import annotations

import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex,evaluate
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import canonical_type_name
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes

SCHEMA='endfield.mission-task-path-claims.v2'
DEFAULT_CONTRACT=CONTRACTS_DIR/'mission_task_paths.json'
REQUIRED_HOOKS=frozenset(('conditionResultChanged','sendProgress','stateUpdate','progressUpdate','conditionCompletionChanged','startFinish','scriptSetDone'))


class MissionTaskPathContractError(RuntimeError):pass


def _factory_callers(image,index,context,spec):
 factory=spec.get('factory')
 if not factory:return []
 definition,=[m for m in image.metadata.methods_for(context.index.types[factory['type']]) if image.metadata.string(m.name_index)==factory['method'] and m.parameter_count==0]
 if not definition.flags&0x10:raise ValueError('factory must be static')
 context.require_ordinary_kind(definition.return_type,30)
 canonical=GenericEntries(image).resolve(definition.index,[],['object']);body=index.body(spec['type'],spec['method'],parameters=spec['parameters']);rows=body.all_rows;results=[]
 for row,call in zip(rows,rows[1:]):
  raw=bytes.fromhex(row['bytes']);flow=control_transfer(call)
  if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x0d' or int(call['va'],16)!=int(row['va'],16)+7 or flow['kind']!='call' or flow['target']!=canonical['pointer']:continue
  usage=derive_typed_usage_context(image,int(row['va'],16)-image.pe.image_base,label='missionTaskPaths.factory')
  if usage['tag']!=6 or usage['methodSpec'][0]!=definition.index or usage['classArguments'] or len(usage['methodArguments'])!=1:raise ValueError('factory MethodInfo identity/arity differs')
  value,=usage['methodArguments']
  if value not in context.index.types or context.is_value_type(value):raise ValueError('factory result is not a named reference')
  results.append(dict(type=value,usage=usage,call=flow,canonical=canonical,evidenceBoundary='conditional',boundary='Exact typed Allocate<T> MethodInfo reaches the actual reference-canonical call. Normal factory reference-return effects are conditional; allocation success, later transport and execution are separate.'))
 if sorted(r['type'] for r in results)!=sorted(factory['results']):raise ValueError('factory result set differs: '+str([r['type'] for r in results]))
 return results


def load_mission_task_paths(path:Path=DEFAULT_CONTRACT,*,gameassembly:Path|None=None,metadata:Path|None=None)->dict:
 path=Path(path).resolve()
 try:raw=path.read_bytes();contract=json.loads(raw)
 except (OSError,UnicodeError,ValueError) as error:raise MissionTaskPathContractError(f'missionTaskPaths.read:{path}:{error}') from error
 hooks=contract.get('hooks')
 if contract.get('schema')!=SCHEMA or contract.get('status')!='reviewed' or not isinstance(hooks,dict) or set(hooks)!=REQUIRED_HOOKS:
  raise MissionTaskPathContractError(f'missionTaskPaths.shape:expected={SCHEMA}/reviewed/seven-hooks:source={path}')
 for name,spec in hooks.items():
  if not all(isinstance(spec.get(k),str) and spec[k] for k in ('type','method','captureScope')) or not isinstance(spec.get('parameters'),list) or not isinstance(spec.get('claims'),list) or not isinstance(spec.get('fields'),list):
   raise MissionTaskPathContractError(f'missionTaskPaths.hook-shape:{name}:source={path}')
 provenance=dict(schema=SCHEMA,source=str(path),sha256=hashlib.sha256(raw).hexdigest())
 def failed(status,gate,expected,actual):return dict(provenance,status=status,hooks={},failures=[dict(validator='missionTaskPaths',gate=gate,expected=expected,actual=actual,sourceFile=str(path))])
 native=check_installed_native_inputs(gameassembly=gameassembly,metadata=metadata)
 if not native.validated:return failed(native.status,'selected-native-inputs','validated',native.detail[:1000])
 before=snapshot_complete_reader_inputs();image=open_native_image(native.gameassembly,native.metadata);index=BodyIndex(image);context=NativeReferenceContext(image,index=index);rows,failures=evaluate(index,hooks)
 if failures:return failed('mismatched','named-native-claims','all hooks proved',failures[:2])
 by_name={row['symbol']:row for row in rows};resolved={}
 for name,spec in hooks.items():
  wanted=[canonical_type_name(p) for p in spec['parameters']]
  methods=[m for m in image.metadata.methods_for(context.index.types[spec['type']]) if image.metadata.string(m.name_index)==spec['method'] and [canonical_type_name(context.type_name(p.type_index)) for p in image.metadata.parameters_for(m)]==wanted]
  if len(methods)!=1:return failed('mismatched','typed-method-identity',dict(hook=name,matches=1),len(methods))
  method,=methods;row=by_name[name];pointer=image.method_pointer_va(method)
  if row['token']!=f'0x{method.token:08x}' or int(row['address'],16)!=pointer:return failed('mismatched','selected-method-pointer',dict(hook=name,token=f'0x{method.token:08x}',address=hex(pointer)),row)
  fields=[]
  for qualified,declared in spec['fields']:
   try:owner,actual,offset=context.field(qualified)
   except ValueError as error:return failed('mismatched','typed-field',dict(hook=name,field=qualified,type=declared),str(error)[:1200])
   if canonical_type_name(actual)!=canonical_type_name(declared):return failed('mismatched','typed-field',dict(hook=name,field=qualified,type=declared),actual)
   fields.append(dict(field=qualified,type=actual,offset=offset,evidenceBoundary='structuralOnly'))
  resolved[name]=dict(symbol=spec['type']+'.'+spec['method'],token=row['token'],methodIndex=method.index,rva=hex(pointer-image.pe.image_base),parameters=spec['parameters'],bodySha256=row['bodySha256'],claims=row['claims'],fieldLayouts=fields,captureScope=spec['captureScope'],evidenceBoundary=spec['evidenceBoundary'])
  try:resolved[name]['factoryCallers']=_factory_callers(image,index,context,spec)
  except (ValueError,KeyError) as error:return failed('mismatched','typed-factory-callers',dict(hook=name,factory=spec.get('factory')),str(error)[:1200])
  resolved[name].update({key:spec[key] for key in ('message','messageId') if key in spec})
 after=check_installed_native_inputs(native.gameassembly_sha256,native.metadata_sha256,gameassembly=native.gameassembly,metadata=native.metadata)
 if not after.validated:return failed(after.status,'selected-native-inputs-after-read','validated',after.detail[:1000])
 current=snapshot_complete_reader_inputs()
 if before!=current:return failed('mismatched','reader-inputs-after-read','unchanged',reader_input_changes(before,current,limit=2))
 if raw!=path.read_bytes():return failed('mismatched','contract-after-read','unchanged','contract changed')
 return dict(provenance,status='validated',gameBuild='installed-'+native.gameassembly_sha256[:12].lower(),nativeInputs={'GameAssembly.dll':native.gameassembly_sha256,'global-metadata.dat':native.metadata_sha256},readerInputs=before,hooks=resolved,evidenceBoundary=contract['evidenceBoundary'])
