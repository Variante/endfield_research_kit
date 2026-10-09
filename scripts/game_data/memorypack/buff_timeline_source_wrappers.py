"""Scoped source-wrapper FF and constructor transfers, outside root admission."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack.struct_output_sources import check_reader_ref_wrapper_abi
from scripts.game_data.memorypack.buffered_reference_wrappers import (
 validate_fast_reference_barrier,validate_buffered_wrapper_null,validate_wrapper_constructor_transfer)

LABEL='buffTimelineSourceWrapper'
SCHEMA='endfield.buff-timeline-source-wrappers-native-contract.v1'
SCOPE='buffered-source-null-and-conditional-constructor-transfer-only'
CONTRACT_PATH=CONTRACTS_DIR/'buff_timeline_source_wrappers_native.json'

def _fail(check: str,expected: Any,actual: Any) -> None:
 error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
 error.diagnostic.update(validator=LABEL,scope=SCOPE);error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error

def _contract() -> dict:
 c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
 if c.get('scope')!=SCOPE or set(c['records'])!={'timeline','forceSync'}:
  _fail('scope','both concrete source-wrapper null and constructor paths',c.get('scope'))
 return c

def _validate_image(image: Any,c: dict) -> dict:
 source,_=read_reviewed_contract(CONTRACTS_DIR/c['sourceDependency'],schema='endfield.buff-timeline-element-sources-native-contract.v1',status='exact-current-build',label=LABEL)
 if source['nativeInputs']!=c['nativeInputs']:_fail('source-build',c['nativeInputs'],source['nativeInputs'])
 selected=NativeReferenceContext(image);offsets=source['readerFieldsUnboxedOffsets']
 if offsets!={n:selected.field('MemoryPack.MemoryPackReader::'+n)[2]-16 for n in offsets}:
  _fail('reader-layout','same owned unboxed Reader fields',offsets)
 barrier=validate_fast_reference_barrier(image,c['barrierProgram'],fail=_fail);result={}
 for key,row in c['records'].items():
  owned=source['records'][key];check_reader_ref_wrapper_abi(image,owned,fail=_fail)
  if row['nullProgram']['program'][0][0]!=owned['readerMethod'][3]:_fail('source-entry','same owned static source entry',row)
  field=selected.field(owned['wrapperTypeName']+'::__instance')
  if field!=(owned['wrapperTypeName'],owned['runtimeTypeName'],16):_fail('instance-field','owned original reference field',field)
  image.validate_method_row(row['constructorMethod'],label=LABEL);m=image.metadata.methods[row['constructorMethod'][0]]
  if (image.type_name(m.declaring_type)!=owned['wrapperTypeName']or m.flags&0x10
      or image.metadata.parameters_for(m)or selected.type_name(m.return_type)!='void'
      or row['constructorMethod'][2]!='.ctor'or row['constructorProgram']['program'][0][0]!=row['constructorMethod'][3]):
   _fail('constructor-abi','owned instance constructor with no explicit parameters',row['constructorMethod'])
  allocation=row['allocation'];validate_typed_usage_context(image,allocation,label=LABEL)
  if allocation['tag']not in(1,2)or allocation['typeName']!=owned['runtimeTypeName']or selected.is_value_type(owned['runtimeTypeName']):
   _fail('allocation-original-type','same concrete original reference type',allocation)
  null=validate_buffered_wrapper_null(image,row['nullProgram'],offsets,c['barrierProgram'],layout=row['nullLayout'],fail=_fail)
  constructor=validate_wrapper_constructor_transfer(image,row['constructorProgram'],allocation,c['barrierProgram'],instance_offset=field[2],fail=_fail)
  result[key]={'sourceNull':null,'constructorTransfer':constructor}
 return {'sourceWrappers':result,'disabledBarrier':barrier,'allocationEffects':'conditional-unresolved',
  'runtimeConstructorInvocationObserved':False}

def validate_current_native_contract(*,gameassembly: Path|None=None,metadata: Path|None=None) -> dict:
 c=_contract();pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
 if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'scope':SCOPE,'nativeInputs':pins}
 unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
 def match():return unity.is_file()and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
 if not match():return {'status':'mismatched'if unity.is_file()else 'missing','detail':'UnityPlayer.dll missing or mismatched','scope':SCOPE,'nativeInputs':pins}
 try:summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
 except ValueError as error:
  if isinstance(error,CensusGateError):raise
  _fail('native-source-wrapper','owned complete null and constructor paths',str(error))
 after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
 if after.status!='validated'or not match():return {'status':after.status if after.status!='validated'else 'mismatched','detail':'native inputs changed during source-wrapper validation','scope':SCOPE,'nativeInputs':pins}
 return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,'positiveListAdmitted':False,
  'wholeRootAdmitted':False,'runtimeMeaningExact':False,'evidenceBoundary':c['evidenceBoundary']}
