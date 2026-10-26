"""Finite Module record programs and independently owned collection children."""
import json

from scripts.game_data.memorypack import levelscript_module_collection_sources as collections
from scripts.game_data.memorypack import levelscript_module_record_sources as records
from scripts.game_data.memorypack import levelscript_module_value_components as values

SCHEMA='endfield.story-module-record-components.v1'
RECORD_SCHEMA='endfield.story-module-record-capability.v1'
LIST_SCHEMA='endfield.story-module-list-capability.v1'
RECORD_WIRE='story-module-record'
LIST_WIRE='story-module-list'


def need(check,condition):
 if not condition:raise ValueError('storyModuleRecords.'+check)


def record_key(name):return 'story-module-record:'+name
def list_key(name):return 'story-module-list:'+name


def list_capability(source,*,record=None,parameters=None):
 collections.verify_windows(source);name=source['elementType'];limit=source['countLimit']
 need('own-framing-and-no-element-promotion',source.get('schema')==collections.SCHEMA
  and source.get('status')=='validated-conditional-module-collection-source'and name in collections.ELEMENTS
  and source.get('typeName')==collections.LIST+name+'>'and source.get('listFramingProved')is True
  and source.get('elementGrammarAdmitted')is False and source.get('parentFieldAdmitted')is False and source.get('wholeOwnerAdmitted')is False
  and type(limit)is int and limit==(64 if name=='Beyond.Gameplay.Core.LevelScriptShape'else 4096))
 child=None;canonical=None
 if name in collections.REFERENCE_TYPES and name!=values.PKV:
  need('independent-complete-ordinary-record-element',isinstance(record,dict)and record.get('schema')==RECORD_SCHEMA
   and record.get('typeName')==name and record.get('wholeGrammarAdmitted')is True and record.get('ordinaryOriginalReadValueAdmitted')is True
   and type(record.get('canonicalAdapterTargetRva'))is int and record['canonicalAdapterTargetRva']>0)
  child=record_key(name);canonical=record['canonicalAdapterTargetRva'];element='record'
 elif name==values.PKV:
  from scripts.game_data.codecs.levelscript.current_module_values import validate_parameters
  validate_parameters(parameters);child=values.PARAM_ARRAY;canonical=None;element='param-key-value'
 elif name in('float','int','ulong','UnityEngine.Vector3'):
  need('no-borrowed-record-element',record is None and parameters is None);element={'float':'float32-bits','int':'int32','ulong':'uint64','UnityEngine.Vector3':'vector3-raw12'}[name]
 elif name=='Beyond.Gameplay.Core.LsmPtr':
  own=source['proof'];value=own['proof']['elementList']['child']
  need('own-nominal-Lsm-canonical-MC1-and-default',value.get('status')=='validated-conditional-small-pointer-value'
   and value.get('typeName')==name and(value.get('managedBytes'),value.get('positiveWireBytes'),value.get('nullWireBytes'),value.get('defaultZeroBytes'))==(8,9,1,8)
   and(value.get('fieldName'),value.get('fieldType'))==('id','ulong')and value.get('actualCallbackEqualsCanonicalRequired')is True)
  element='lsm-mc1'
 else:
  own=source['proof'];r=own['record'];t=own['transfer'];c=own['collection']
  need('own-nominal-Shape-record-canonical-and-list',r.get('typeName')==t.get('typeName')==name and r.get('managedBytes')==t.get('managedBytes')==44
   and c.get('elementType')==name and c['capability'].get('wholeGrammarAdmitted')is True
   and c['capability'].get('recordWireBytes')==45 and c['capability'].get('nullReturnsZero44')is True)
  element='shape-mc5'
 return dict(schema=LIST_SCHEMA,capability=list_key(name),typeName=source['typeName'],elementType=name,elementOperation=element,
  elementCapability=child,canonicalElementCallbackTargetRva=canonical,headerBytes=4,countLimit=limit,countRange=[-1,limit],nullable=True,
  positiveCountsAdmitted=True,elementGrammarAdmitted=True,initiallyNullOutputRequired=True,actualCallbackEqualsProvedChildRequired=True,
  packableReaderMethodDefinition=source['readerMethodDefinition'],packableReaderTargetRva=source['sourceTargetRva'],
  rawBitsPreserved=True,wholeGrammarAdmitted=True,liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def collection_component(source,pins,*,record=None,parameters=None):
 need('same-fresh-collection-build',source.get('nativeInputs')==pins);cap=list_capability(source,record=record,parameters=parameters)
 return dict(schema=SCHEMA,nativeInputs=pins,capabilities={cap['capability']:cap},proof=dict(collection=source),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def bind_reference(pins,join,component,capability):
 from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
 cap=component.get('capabilities',{}).get(capability,{})
 need('own-complete-ordinary-record',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
  and cap.get('schema')==RECORD_SCHEMA and capability==record_key(join['typeName'])
  and cap.get('ordinaryOriginalReadValueAdmitted')is True and component.get('proof',{}).get('ordinary',{}).get('ordinaryOriginalAdapterAdmitted')is True)
 return bind_read_value(pins,join,component,capability)


def compile_record(source,pins,*,typed_requests,ordinary_children,list_children,value_children,value_components,rune_arrays=None,rune_dictionary=None):
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack import levelscript_module_enum_list_sources as enums,levelscript_module_entity_list_components as entity_lists
 from scripts.game_data.memorypack import levelscript_rune_array_components as rune_arrays_owner,levelscript_rune_dictionary_components as rune_dict
 from scripts.game_data.memorypack import module_entity_ptr_value_bindings as entity,module_lang_key_value_bindings as lang
 from scripts.game_data.memorypack import levelscript_opera_array_components as opera
 reads=source['orderedSourceReads'];scope=source['sourceScope'];references={};reference_children={};listing={};children={};arrays={};array_children={};typed_values={}
 for read in reads:
  i=read['memberIndex'];name=read['declaredType']
  if name in ordinary_children:
   c=ordinary_children[name];key=record_key(name);references[name]=(key,RECORD_WIRE,key);reference_children[name]=c
  if i in list_children:
   c,key,wire=list_children[i];listing[name]=(key,wire,key);children[i]=c
  if i in value_children:
   c=value_children[i];key=entity.CAPABILITY if name==entity.TYPE else lang.CAP
   typed_values[name]=(key,'entity-ptr-stored-value'if name==entity.TYPE else'lang-key',key)
  if rune_arrays and i in rune_arrays:
   c=rune_arrays[i];key=c['capability'];arrays[name]=(key,rune_arrays_owner.WIRE,key);array_children[i]=c
  if name==values.values.OPERA+'[]':
   arrays[name]=(values.OPERA_ARRAY,opera.WIRE,values.OPERA_ARRAY);array_children[i]=value_components
  if rune_dictionary and name==rune_dict.source.TYPE:
   listing[name]=(rune_dict.CAPABILITY,rune_dict.WIRE,rune_dict.CAPABILITY);children[i]=rune_dictionary
 def collection_binder(selected_pins,join,component,key):
  read,=[r for r in reads if r['fieldName']==join['fieldName']and r['declaredType']==join['typeName']]
  if component.get('schema')==rune_dict.SCHEMA:
   return rune_dict.bind_member(source,scope,read,pins,join['typedRequest'],component,key)
  if component.get('schema')==enums.SCHEMA:
   owned=dict(join,parentType=source['wrappedType'],memberIndex=read['memberIndex'],instruction=read['instruction'])
   result=enums.bind(pins,owned,component,key);cap=result['collectionCapability']
   return dict(fieldName=join['fieldName'],typeName=join['typeName'],capability=key,
    readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],sourceBinding=result)
  if component.get('schema')==entity_lists.SCHEMA:return entity_lists.bind_request(pins,join,component,key)
  if component.get('schema')==values.SCHEMA:
   cap=component['capabilities'][key];name=cap['elementType'];actual=component['proof']['lists'][name]
   expected=values.list_capability(actual,values.value_capability(actual['proof']['value'],pins),pins)
   need('same-independent-value-list-child',cap==expected and key==values.LIST_CAPS[name]
    and join['typeName']==cap['typeName']and join['typedRequest']['methodSpec']==actual['typedRequest']['methodSpec']
    and join['sourceTargetRva']==cap['packableReaderTargetRva'])
   return dict(fieldName=join['fieldName'],typeName=join['typeName'],capability=key,
    readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'])
  need('only-own-Module-list-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==selected_pins==pins)
  cap=component['capabilities'][key];actual=component['proof']['collection'];result=collections.bind_request(pins,join,actual)
  need('same-complete-list-child',key==list_key(actual['elementType'])and cap.get('schema')==LIST_SCHEMA
   and cap.get('wholeGrammarAdmitted')is True and cap.get('elementGrammarAdmitted')is True
   and(cap.get('typeName'),cap.get('countLimit'),cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))==
    (result['typeName'],result['countLimit'],result['readerMethodDefinition'],result['sourceTargetRva']))
  return dict(result,capability=key)
 def managed_binder(*args):
  read=args[2]
  need('only-two-explicit-managed-nominals',read['declaredType']in(entity.TYPE,lang.TYPE))
  return(entity.bind if read['declaredType']==entity.TYPE else lang.bind)(*args)
 return compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=source['wrappedType'],value4={},
  references=references,reference_children=reference_children,reference_binder=bind_reference,
  typed_requests=typed_requests,collections=listing,collection_children=children,collection_binder=collection_binder,
  arrays=arrays,array_children=array_children,typed_values=typed_values,value_children=value_children,value_binder=managed_binder)


def record_component(source,pins,program,*,ordinary=None,reference_reader=None):
 count=source.get('sourceScope',{}).get('memberCount')
 need('complete-current-record-program',source.get('nativeInputs')==pins and source.get('completeSelectedCallerAdmitted')is True
  and type(count)is int and program.get('memberCount')==count
  and len(program.get('reads',[]))==count and[r['memberIndex']for r in program['reads']]==list(range(count)))
 cap=dict(schema=RECORD_SCHEMA,typeName=source['wrappedType'],wrapperName=source['wrapperName'],memberCount=count,
  fields=[{k:r[k]for k in('memberIndex','fieldName','declaredType')}for r in source['orderedSourceReads']],
  enumBackings=source.get('sourceScope',{}).get('enumBackings',[]),program=program,readerMethod=source['method'],
  formatterMethod=source['lifecycle']['concreteFormatter']['method'],wholeGrammarAdmitted=True,positiveAdmitted=True,nullAdmitted=True,
  actualWrapperCallbackEqualsProvedConcreteRequired=True,ordinaryOriginalReadValueAdmitted=ordinary is not None,
  liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 if ordinary is not None:
  records.join_record(source,ordinary['pair'],ordinary['adapter'],pins)
  need('separate-own-reference-reader-ABI',isinstance(reference_reader,dict))
  cap.update(canonicalAdapterTargetRva=ordinary['adapter']['callbackBinding']['canonicalTargetRva'],
   referenceReaderMethodDefinition=reference_reader['referenceReaderMethodDefinition'],referenceReaderTargetRva=reference_reader['referenceReaderTargetRva'])
 return dict(schema=SCHEMA,nativeInputs=pins,capability=record_key(source['wrappedType']),capabilities={record_key(source['wrappedType']):cap},
  proof=dict(source=source,ordinary=ordinary),parentFieldAdmitted=False,wholeOwnerAdmitted=False)
