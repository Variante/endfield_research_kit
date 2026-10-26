"""Authenticate current compiled constant getter transfers on an explicit selected pair."""
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.memorypack import pointer_getter_sources as source,pooled_source_helper
from scripts.game_data.memorypack.levelscript_interactive_sources import collector_disabled_program
from scripts.game_data.memorypack.wrapper_members import derive_from_image
from scripts.game_data.memorypack.union_dispatch import read_union_switch
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes

VALUE_TYPES={'entity40':'Beyond.Gameplay.Core.EntityPtr','spawner8':'Beyond.Gameplay.Core.SpawnerPtr'}

def _regions(image,p):
 base=image.pe.image_base;windows=p['windows'];entry=base+p['entryRva']
 if p['ownership']=='completeOwnedUnwindFamily':
  actual=sorted(q['runtimeTriple'][:2]for q in image.unwind_index.family(p['entryRva'])['ranges'])
  if actual!=sorted([w['startRva'],w['endRva']]for w in windows):raise ValueError('compiledGetter.source:complete-owned-family')
 elif p['ownership']=='closedReachableLeaf':
  if len(windows)!=1:raise ValueError('compiledGetter.source:leaf-window')
  w,=windows;raw=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']);leaf=decode_closed_leaf_entry(image.mapper,raw,entry)
  if not leaf['closedReachableInstructionGraph']or leaf['containsCalls']:raise ValueError('compiledGetter.source:leaf-control')
 elif p['ownership']!='selectedCollectorDisabledReturnPrefix':raise ValueError('compiledGetter.source:ownership-profile')
 image.check_windows(windows,label='compiledGetter.source')
 return[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in windows]

def _child(kind,*,gameassembly,metadata,contracts_dir):
 if kind=='entity40':
  from scripts.game_data.levelscript_entity_ptr_param_native import validate_entity_ptr_param_native_contract
  path=contracts_dir/'levelscript_entity_ptr_param_native.json';raw=path.read_bytes();fact=json.loads(raw);gate=validate_entity_ptr_param_native_contract(contract_path=path,gameassembly=gameassembly,metadata=metadata);slots=fact['profile']['ownedFieldSlots']
 else:
  from scripts.game_data.levelscript_pod_id_param_native import validate
  path=contracts_dir/'levelscript_pod_id_param_native.json';raw=path.read_bytes();fact=json.loads(raw);gate=validate('Param<SpawnerPtr>',contract_path=path,gameassembly=gameassembly,metadata=metadata);row,=[q for q in fact['components']if q['codecKind']=='Param<SpawnerPtr>'];slots=row['proof']['parameter']['ownedFieldSlots']
 if gate.get('status')!='validated':raise ValueError('compiledGetter.child:'+str(gate)[:1000])
 if raw!=path.read_bytes()or slots['paramSource']!=16 or slots['constValue']!=32:raise ValueError('compiledGetter.child:declaration-or-slot-join')
 return gate

def _derive(image,pins,row):
 kind=row['kind'];value=VALUE_TYPES[kind];base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image);symbols=ContextSymbols(image)
 image.validate_method_row(row['method'],label='compiledGetter.GetResult');m=md.methods[row['method'][0]]
 if image.type_name(m.declaring_type)!=row['getterName']or md.string(m.name_index)!='GetResult'or m.flags&16 or m.parameter_count or ctx.type_name(m.return_type)!=value:raise ValueError('compiledGetter.native:GetResult-ABI')
 field=ctx.field(row['getterName']+'::_value')
 if list(field)!=row['field']or field[1]!='Beyond.Gameplay.Actions.Param`1<'+value+'>':raise ValueError('compiledGetter.native:typed-field')
 validate_typed_usage_context(image,row['usage'],label='compiledGetter.GetValue')
 usage=row['usage']
 if (usage['tag'],usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])!=(6,'Beyond.Gameplay.Actions.ParamExtensions','GetValue',[],[value]):raise ValueError('compiledGetter.native:typed-GetValue')
 if symbols.context(usage['methodSpec'][0],is_method=True)!=row['getValueContext']:raise ValueError('compiledGetter.native:GetValue-parameter-context')
 pointers={}
 for name,h in row['helpers'].items():
  method=md.methods[h['methodIndex']]
  if (image.type_name(method.declaring_type),md.string(method.name_index))!=(h['owner'],h['name']):raise ValueError('compiledGetter.native:helper-identity')
  actual=json.loads(json.dumps(ge.resolve(method.index,h['classArguments'],h['methodArguments'])))
  if actual!=h['registration']:raise ValueError('compiledGetter.native:helper-closed-registration:'+name)
  if h['classArguments']!=([]if h['owner'].endswith('ParamExtensions')else[value])or h['methodArguments']!=([value]if h['owner'].endswith('ParamExtensions')else[]):raise ValueError('compiledGetter.native:helper-argument-join')
  abi=dict(static=bool(method.flags&16),returns=ctx.type_name(method.return_type),parameters=[ctx.type_name(a.type_index)for a in md.parameters_for(method)])
  if abi!=h['abi']:raise ValueError('compiledGetter.native:helper-ABI')
  pointers[name]=actual['pointer']
 if row['helpers']['getValue']['methodIndex']!=usage['methodSpec'][0]:raise ValueError('compiledGetter.native:caller-definition-join')
 current=row['getValueContext']['entries'];expected={'useGetter':'get_useGetter','tryGetValue':'TryGetValue'}
 for key,name in expected.items():
  e,=[e for e in current if e['kind']==3 and e['methodName']==name]
  if e['methodSpec'][0]!=row['helpers'][key]['methodIndex']:raise ValueError('compiledGetter.native:actual-child-context')
 programs=row['programs'];regions={k:_regions(image,p)for k,p in programs.items()};at=lambda k:base+programs[k]['entryRva']
 if any(at(k)!=pointers[k]for k in('getValue','tryGetValue','useGetter'))or at('getResult')!=base+row['method'][3]:raise ValueError('compiledGetter.native:program-entry-join')
 proofs={};target=pointers['getValue']
 if kind=='entity40':
  target=at('thunk');proofs['thunk']=source.entity_thunk(regions['thunk'],target,pointers['getValue']);proofs['collectorDisabled']=collector_disabled_program(regions['barrier'],at('barrier'));proofs['constant']=source.try_constant(regions['tryGetValue'],at('tryGetValue'),kind,barrier=at('barrier'))
 else:
  if at('isConst')!=pointers['isConst']:raise ValueError('compiledGetter.native:isConst-entry')
  proofs['isConst']=source.is_const(regions['isConst'],at('isConst'));proofs['constant']=source.try_constant(regions['tryGetValue'],at('tryGetValue'),kind,is_const=at('isConst'))
 proofs['getter']=source.getter(regions['getResult'],at('getResult'),kind,field=field[2],source=target,context=base+usage['usageCellRva']);proofs['useGetter']=source.use_getter(regions['useGetter'],at('useGetter'),16);proofs['value']=source.get_value(regions['getValue'],at('getValue'),kind,use=pointers['useGetter'],target=pointers['tryGetValue'])
 return proofs

def validate(contract_path,*,schema,gameassembly=None,metadata=None,parent_contract_path=None,layout_path=None,contracts_dir=CONTRACTS_DIR):
 label='compiledPointerGetterNative';path=Path(contract_path)
 try:
  inputs=snapshot_complete_reader_inputs();raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
  if set(fact)!={'schema','status','nativeInputs','getters','evidenceBoundary'}or fact['schema']!=schema or fact['status']!='conditional-current-build-compiled-getter'or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}or not fact['getters']:raise ValueError(label+'.contract:shape')
  if gameassembly is None or metadata is None:return {},dict(status='missing',detail='Both selected GameAssembly.dll and global-metadata.dat paths are required.')
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
  if gate.status!='validated':return {},dict(status=gate.status,detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return {},failed
  image=open_native_image(gate.gameassembly,gate.metadata);wrappers=derive_from_image(image);switch=read_union_switch(image,'Beyond.MemoryPack.Beyond_Gameplay_Actions_PureGetterForMemoryPack',wrappers=wrappers);out={};proofs={}
  from scripts.game_data import levelscript_route_deserialize_native as parent
  for row in fact['getters']:
   kind=row['kind'];wrapper,=[w for w in wrappers.values()if w.name==row['wrapperName']];route,=[q for q in switch['entries']if q['wrapperName']==wrapper.name];shape=(route['tag'],len(wrapper.members))
   if kind not in VALUE_TYPES or wrapper.wrapped_type!=row['getterName']or shape!=(row['unionTag'],row['serializedMemberCount'])or[(q.name,q.declared_type)for q in wrapper.members]!=[tuple(f)for f in row['fields']]or shape in out:raise ValueError(label+'.native:unique-generated-shape')
   kwargs=dict(gameassembly=gate.gameassembly,metadata=gate.metadata,selected_route=('GetterBase',shape[0]))
   if parent_contract_path is not None:kwargs['contract_path']=parent_contract_path
   if layout_path is not None:kwargs['layout_path']=layout_path
   p=parent.validate(**kwargs)
   if p.get('status')!='validated':raise ValueError(label+'.parent:'+str(p)[:1000])
   child=_child(kind,gameassembly=gate.gameassembly,metadata=gate.metadata,contracts_dir=Path(contracts_dir));proofs[row['getterName']]=_derive(image,pins,row)
   out[shape]=dict(getterName=row['getterName'],unionTag=shape[0],serializedMemberCount=shape[1],resolutionKind='constant_param_alias',valueType=VALUE_TYPES[kind],valueBytes=40 if kind=='entity40'else 8,fieldName='_value',wireField='value',memberOrdinal=next(i for i,m in enumerate(wrapper.members)if m.name=='_value'),evidenceBoundary=fact['evidenceBoundary'])
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata);failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if after.status!='validated':return {},dict(status=after.status,detail='Selected native inputs changed: '+after.detail)
  if failed:return {},failed
  if raw!=path.read_bytes():raise ValueError(label+'.contract:changed-during-validation')
  later=snapshot_complete_reader_inputs()
  if inputs!=later:raise ValueError(label+'.source:reader-input-drift:'+str(reader_input_changes(inputs,later)))
  return out,dict(status='validated',nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'],compiledSourceProofs=proofs)
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return {},native_validation_failure(error,label=label,source_path=path)
