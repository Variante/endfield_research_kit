"""Finite non-enum Param storage sources; no canonical or parent admission.

Pointer constants require their own sole UInt64 id field, sizes and actual
closed ReadUnmanaged program. Signed Int64 uses its independently reviewed
source, and EntityPtr preserves its dedicated hidden40/opaque-runtime boundary.
Neither a type spelling nor an eight-byte size selects one of these sources.
"""
import json

SCHEMA='endfield.story-condition-storage-param-sources.v1'
POINTER_TYPES=(
 'Beyond.Gameplay.Core.LsmPtr','Beyond.Gameplay.Core.SpawnerPtr','Beyond.Gameplay.Core.WaterVolumePtr',
)
SCRIPT='Beyond.Gameplay.Core.LevelScriptPtr'
TASK='Beyond.Gameplay.Core.ScriptTaskPtr'
ENTITY='Beyond.Gameplay.Core.EntityPtr'
TYPES=POINTER_TYPES+('long',ENTITY,SCRIPT,TASK)
LABEL='storyConditionStorageParam'


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def _long(image,pins):
 from scripts.game_data import levelscript_long_param_native as native
 from scripts.game_data.memorypack import pooled_source_helper
 raw=native.CONTRACT_PATH.read_bytes();fact=json.loads(raw)
 need('reviewed-signed-Int64-source',fact.get('schema')==native.SCHEMA and fact.get('status')=='exact-current-build'
  and fact.get('codecKind')=='Param<long>'and fact.get('nativeInputs')=={k:pins[k]for k in('GameAssembly.dll','global-metadata.dat')}
  and fact.get('dependencies')==[dict(role='pooledStringSource',path=pooled_source_helper.CONTRACT_PATH.name)])
 call=fact['parameter']['orderedReads'][-1]['readCall']
 need('owned-pooled-tail-selection',fact['parameter']['orderedReads'][-1]['name']=='path'
  and isinstance(call,list)and len(call)==3 and all(type(call[i])is int for i in(0,2)))
 strings=pooled_source_helper.validate_on_image(image,image.pe.image_base+call[2],pins)
 proof=native._composition(image,fact,strings)
 need('long-contract-bookend',native.CONTRACT_PATH.read_bytes()==raw)
 return dict(parameter=fact['parameter'],reviewedSource=fact,pooledPath=strings,composition=proof)


def _entity(image,pins):
 from scripts.game_data import levelscript_entity_ptr_param_native as native
 from scripts.game_data.memorypack import entity_ptr_param
 from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
 path=native.DEFAULT_CONTRACT;before=path.read_bytes();fact=native._contract(path)
 need('same-dedicated-EntityPtr-inputs',fact['nativeInputs']==pins)
 proof=entity_ptr_param.derive(image,pins,fact['profile'])
 validate_claims(fact['proof'],proof,label=LABEL+'.EntityProof')
 validate_claims(proof,fact['proof'],label=LABEL+'.EntityDeclaration')
 need('Entity-contract-bookend',path.read_bytes()==before)
 return dict(dedicatedContract=path.name,source=proof,
  runtimeReferenceLayoutAdmitted=False,opaqueRuntimeStorageRanges=[[24,40]],
  selectedBarrierValueOffsets=[24],completeRuntimePaddingMapAdmitted=False)


def _script(image,pins):
 from scripts.game_data import levelscript_script_ptr_param_native as native
 from scripts.game_data.memorypack import script_ptr_param
 from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
 path=native.DEFAULT_CONTRACT;before=path.read_bytes();fact=native._contract(path)
 need('same-dedicated-LevelScriptPtr-inputs',fact['nativeInputs']==pins)
 proof=script_ptr_param.derive(image,pins,fact['profile'])
 validate_claims(fact['proof'],proof,label=LABEL+'.LevelScriptPtrProof')
 validate_claims(proof,fact['proof'],label=LABEL+'.LevelScriptPtrDeclaration')
 need('LevelScriptPtr-contract-bookend',path.read_bytes()==before)
 return dict(dedicatedContract=path.name,source=proof,copiedUninterpretedRanges=[[12,16]],runtimeScriptResolutionProved=False)


def derive_one(image,pins,*,value_type):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack import primitive_param
 need('explicit-finite-storage-selection',type(value_type)is str and value_type in TYPES)
 _publication_gate(image,pins)
 if value_type in POINTER_TYPES:
  proof=primitive_param.derive_parameter(image,pins,'ulong',value_type=value_type,unmanaged_qword=True)
  need('own-one-UInt64-field-source',proof.get('status')=='validated'and proof.get('valueType')==value_type
   and proof.get('valueFields')==[['id','ulong',16]]and type(proof.get('rawSize'))is int and proof['rawSize']==8)
  wire,width='nominal-id-uint64',8
 elif value_type=='long':proof=_long(image,pins);wire,width='i64',8
 elif value_type==ENTITY:proof=_entity(image,pins);wire,width='entity-ptr-stored-value',None
 elif value_type==SCRIPT:proof=_script(image,pins);wire,width='level-script-ptr-raw16',16
 else:raise ValueError(LABEL+'.ScriptTaskPtr-own-string-key-source-required')
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-storage-Param-source',nativeInputs=pins,
  typeName='Beyond.Gameplay.Actions.Param`1<'+value_type+'>',valueType=value_type,constantWireKind=wire,constantWireBytes=width,
  proof=proof,sourceAdmitted=True,canonicalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))


def derive(image,pins,*,value_types):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 need('bounded-distinct-storage-selection',isinstance(value_types,(list,tuple))and 0<len(value_types)<=len(TYPES)
  and all(type(v)is str and v in TYPES for v in value_types)and len(set(value_types))==len(value_types))
 _publication_gate(image,pins);owners=[]
 for value in value_types:
  try:owners.append(derive_one(image,pins,value_type=value))
  except(ValueError,KeyError,IndexError,TypeError)as error:
   owners.append(dict(status='pendingReview',valueType=value,typeName='Beyond.Gameplay.Actions.Param`1<'+value+'>',
    reason=str(error)[:2200],sourceAdmitted=False,canonicalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False))
 _publication_gate(image,pins)
 return dict(schema=SCHEMA,nativeInputs=pins,owners=owners,
  complete=sum(o.get('sourceAdmitted')is True for o in owners),parentFieldAdmitted=False,wholeOwnerAdmitted=False)
