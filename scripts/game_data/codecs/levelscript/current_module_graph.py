"""Complete current stored Module graph; runtime behavior stays unobserved."""
import math
import struct

from scripts.game_data.memorypack import levelscript_module_graph_sources as profiles
from scripts.game_data.memorypack import levelscript_module_record_components as records
from scripts.game_data.memorypack import levelscript_module_value_components as values
from scripts.game_data.memorypack import levelscript_module_collection_sources as collections
from scripts.game_data.memorypack import levelscript_module_enum_list_sources as enum_lists
from scripts.game_data.memorypack import levelscript_module_entity_list_components as entity_lists
from scripts.game_data.memorypack import levelscript_rune_array_components as rune_arrays
from scripts.game_data.memorypack import levelscript_rune_dictionary_components as rune_dictionary
from scripts.game_data.memorypack import levelscript_opera_array_components as opera
from scripts.game_data.codecs.levelscript import current_module_values as value_codec
from scripts.game_data.codecs.levelscript import current_module_entity_list as entity_codec
from scripts.game_data.codecs.levelscript import current_rune_arrays,current_rune_dictionary
from scripts.game_data.codecs.leveldata import current_entity_ptr,current_lang_key


def need(key,condition):
 if not condition:raise ValueError('currentModuleGraph.'+key)


def _positive_integer(value):return type(value)is int and value>0


def _validate_list(cap,table):
 element=cap.get('elementType');key=records.list_key(element)
 operations={'float':'float32-bits','int':'int32','ulong':'uint64','UnityEngine.Vector3':'vector3-raw12',
  'Beyond.Gameplay.Core.LsmPtr':'lsm-mc1','Beyond.Gameplay.Core.LevelScriptShape':'shape-mc5'}
 expected='param-key-value'if element==values.PKV else'record'if element in collections.REFERENCE_TYPES else operations.get(element)
 need('exact-independent-list-shape',element in collections.ELEMENTS and cap.get('schema')==records.LIST_SCHEMA
  and cap.get('capability')==key and cap.get('typeName')==collections.LIST+element+'>'and cap.get('elementOperation')==expected
  and type(cap.get('countLimit'))is int and cap['countLimit']==(64 if element=='Beyond.Gameplay.Core.LevelScriptShape'else 4096)
  and type(cap.get('headerBytes'))is int and cap['headerBytes']==4 and cap.get('countRange')==[-1,cap['countLimit']]
  and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted','initiallyNullOutputRequired',
   'actualCallbackEqualsProvedChildRequired','rawBitsPreserved','wholeGrammarAdmitted'))
  and all(cap.get(k)is False for k in('liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))
  and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>=0
  and _positive_integer(cap.get('packableReaderTargetRva')))
 if expected=='record':
  child=table.get(cap.get('elementCapability'),{})
  need('own-ordinary-list-record-child',cap.get('elementCapability')==records.record_key(element)
   and child.get('schema')==records.RECORD_SCHEMA and child.get('typeName')==element
   and child.get('ordinaryOriginalReadValueAdmitted')is True
   and cap.get('canonicalElementCallbackTargetRva')==child.get('canonicalAdapterTargetRva'))
 elif expected=='param-key-value':
  need('separate-Param-record-child',cap.get('elementCapability')==values.PARAM_ARRAY)
  value_codec.validate_parameters(table.get(values.PARAM_ARRAY))
 else:need('no-unowned-list-element-child',cap.get('elementCapability')is None and cap.get('canonicalElementCallbackTargetRva')is None)


def _validate_record(cap,table):
 count=cap.get('memberCount');fields=cap.get('fields');program=cap.get('program',{});reads=program.get('reads',[])
 need('complete-record-ordered-plan',cap.get('schema')==records.RECORD_SCHEMA and type(count)is int and 0<count<250
  and type(fields)is list and len(fields)==count and len(reads)==count and program.get('memberCount')==count
  and[f.get('memberIndex')for f in fields]==[r.get('memberIndex')for r in reads]==list(range(count))
  and len({f.get('fieldName')for f in fields})==count
  and all(f.get('fieldName')==r.get('fieldName')and type(f.get('declaredType'))is str for f,r in zip(fields,reads))
  and all(cap.get(k)is True for k in('wholeGrammarAdmitted','positiveAdmitted','nullAdmitted','actualWrapperCallbackEqualsProvedConcreteRequired'))
  and all(cap.get(k)is False for k in('liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))
  and type(cap.get('ordinaryOriginalReadValueAdmitted'))is bool
  and cap.get('readerMethod',[None,None])[1]==cap.get('wrapperName'))
 enums={r['typeName']:r['backingType']for r in cap.get('enumBackings',[])}
 fixed={'bool-byte':'bool','byte-payload':'string','float32-bits':'float','float64-bits':'double',
  'unity-vector3-raw12':'UnityEngine.Vector3','unity-quaternion-raw16':'UnityEngine.Quaternion','story-posrot-raw24':'Beyond.PosRot'}
 for field,read in zip(fields,reads):
  kind=read.get('kind');nominal=field['declaredType'];child=read.get('childCapability')
  if kind in fixed:need('exact-atomic-nominal',nominal==fixed[kind]and child==('byte-payload'if kind=='byte-payload'else None))
  elif kind=='scalar32':need('own-scalar32-or-nominal-enum',child is None and(nominal in('int','uint')or enums.get(nominal)in('int','uint')))
  elif kind=='scalar64-bits':need('own-scalar64',nominal in('long','ulong')and child is None)
  elif kind==records.RECORD_WIRE:
   need('own-ordinary-reference-field',child==records.record_key(nominal)and table.get(child,{}).get('typeName')==nominal
    and table[child].get('ordinaryOriginalReadValueAdmitted')is True)
  elif kind==records.LIST_WIRE:need('own-positive-list-field',table.get(child,{}).get('schema')==records.LIST_SCHEMA and table[child]['typeName']==nominal)
  elif kind=='story-module-value-list':need('own-managed-value-list-field',child in values.LIST_CAPS.values()and table.get(child,{}).get('typeName')==nominal)
  elif kind==entity_lists.WIRE:need('own-Entity-list-field',child==entity_lists.CAP and nominal==entity_lists.TYPE)
  elif kind==enum_lists.WIRE:need('own-enum-list-field',child in{enum_lists.list_capability(n)for n in enum_lists.PLANS}and table.get(child,{}).get('closedListType')==nominal)
  elif kind==rune_arrays.WIRE:need('own-Rune-array-field',cap['typeName']==rune_arrays.OWNER and child==rune_arrays.key(nominal[:-2])and nominal in('int[]','bool[]'))
  elif kind==rune_dictionary.WIRE:need('own-Rune-raw-pair-field',cap['typeName']==rune_arrays.OWNER and nominal==rune_dictionary.source.TYPE and child==rune_dictionary.CAPABILITY)
  elif kind==opera.WIRE:need('own-Opera-array-field',cap['typeName']in opera.PARENTS and nominal==values.values.OPERA+'[]'and child==values.OPERA_ARRAY)
  elif kind=='entity-ptr-stored-value':need('own-Entity-value-field',nominal==current_entity_ptr.TYPE and child==current_entity_ptr.CAP)
  elif kind=='lang-key':need('own-LangKey-value-field',nominal==current_lang_key.TYPE and child=='story-lang-key')
  else:raise ValueError('currentModuleGraph.unowned-field-operation:'+str(kind))
  if child not in(None,'byte-payload'):need('all-required-child-capabilities-present',child in table)
 required=sorted({r['childCapability']for r in reads if r.get('childCapability')is not None})
 need('exact-record-requirements',program.get('requiredCapabilities')==required)
 if cap['ordinaryOriginalReadValueAdmitted']:
  need('independent-ordinary-reference-ABI',all(_positive_integer(cap.get(k))for k in('canonicalAdapterTargetRva','referenceReaderTargetRva'))
   and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>=0)


def validate(cap):
 need('whole-current-Module-profile',isinstance(cap,dict)and cap.get('schema')==profiles.CAP_SCHEMA
  and cap.get('moduleType')==profiles.BASE and cap.get('typeName')=='System.Collections.Generic.Dictionary`2<ulong,'+profiles.BASE+'>'
  and cap.get('headerModes')==['short','extended','canonical-FF']
  and all(type(cap.get(k))is int and cap[k]==v for k,v in dict(nodeLimit=16384,elementLimit=16384,depthLimit=64,pooledIndexBytes=4,pooledNullIndex=-2,pooledEmptyIndex=-1).items())
  and all(cap.get(k)is True for k in('storedModuleGrammarAdmitted','allPositiveChildDomainsAdmitted'))
  and all(cap.get(k)is False for k in('liveFormatterSelectionObserved','runtimeModuleBehaviorAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
 routes=cap.get('routes',{});table=cap.get('capabilities',{})
 need('complete-21-union-routes',set(routes)=={str(i)for i in range(21)}and len({r.get('typeName')for r in routes.values()})==21)
 ordinary_names=set(__import__('scripts.game_data.memorypack.levelscript_module_record_sources',fromlist=['TYPES']).TYPES)
 record_names={c.get('typeName')for c in table.values()if c.get('schema')==records.RECORD_SCHEMA}
 need('complete-34-record-graph',record_names=={r['typeName']for r in routes.values()}|ordinary_names and len(record_names)==34)
 for route in routes.values():
  child=table.get(route.get('recordCapability'),{})
  need('selected-complete-concrete-route',route.get('recordCapability')==records.record_key(route.get('typeName'))
   and(child.get('typeName'),child.get('wrapperName'))==(route.get('typeName'),route.get('wrapperName'))
   and route.get('actualClosedReadPackableProved')is True and route.get('actualWrapperCallbackEqualsProvedChildRequired')is True)
 expected_lists={records.list_key(n)for n in collections.ELEMENTS}
 need('all-13-positive-list-domains',{k for k,c in table.items()if c.get('schema')==records.LIST_SCHEMA}==expected_lists)
 for key,child in table.items():
  schema=child.get('schema')
  if schema==records.RECORD_SCHEMA:need('record-key-matches-nominal',key==records.record_key(child['typeName']));_validate_record(child,table)
  elif schema==records.LIST_SCHEMA:_validate_list(child,table)
  elif schema==values.VALUE_SCHEMA:value_codec.validate_value(child)
  elif schema==values.LIST_SCHEMA:value_codec.validate_list(child)
  elif schema==values.ARRAY_SCHEMA:value_codec.validate_array(child)
  elif schema==values.PARAM_SCHEMA:value_codec.validate_parameters(child)
  elif key==entity_lists.CAP:entity_codec.validate(child)
  elif key==current_entity_ptr.CAP:current_entity_ptr.validate(child)
  elif key=='story-lang-key':current_lang_key.validate(child)
  elif key==rune_dictionary.CAPABILITY:current_rune_dictionary.validate(child)
  elif key in{rune_arrays.key(n)for n in('int','bool')}:current_rune_arrays.validate(child)
  elif key in{enum_lists.list_capability(n)for n in enum_lists.PLANS}:
   enum_lists.require_capability(child,table.get(child.get('elementCapability')),enum_type=child['elementType'])
  elif key in{enum_lists.element_capability(n)for n in enum_lists.PLANS}:
   need('independent-own-enum-callback',child==table[enum_lists.list_capability(child.get('typeName'))]['elementCallback'])
  else:raise ValueError('currentModuleGraph.unowned-capability:'+key)
 dictionary=cap.get('dictionary',{});binding=cap.get('rootBinding',{})
 need('own-UInt64-reference-dictionary-and-root-field',dictionary.get('countRange')==[-1,4096]
  and all(type(dictionary.get(k))is int and dictionary[k]==v for k,v in dict(headerBytes=4,keyWireBytes=8,countLimit=4096).items())
  and(dictionary.get('keyType'),dictionary.get('valueType'))==('ulong',profiles.BASE)
  and all(dictionary.get(k)is True for k in('initiallyNullOutputRequired','actualKeyCallbackEqualsProvedUInt64Required',
   'actualValueCallbackEqualsProvedModuleRequired','freshDictionaryRequired'))and dictionary.get('duplicateAndHashBehaviorAdmitted')is False
  and(binding.get('ownerType'),binding.get('fieldName'),binding.get('typeName'))==(profiles.ROOT,'modules',cap['typeName'])
  and all(binding.get(k)is True for k in('existingWrapperRequired','disabledCollectorRequired','completeRootFrameProved'))
  and binding.get('rootGrammarAdmitted')is False)


def _budget(budget):
 if budget is None:return dict(nodes=16384,elements=16384)
 need('shared-budget',isinstance(budget,dict)and all(type(budget.get(k))is int and 0<=budget[k]<=16384 for k in('nodes','elements')))
 return budget


def _use(budget,key,count=1):
 need('budget-'+key,type(count)is int and 0<=count<=budget[key]);budget[key]-=count


def _count(reader,field,limit,budget,*,width=None):
 reader.need(4,field+'.count');count=struct.unpack_from('<i',reader.data,reader.offset)[0]
 need('bounded-signed-count',-1<=count<=limit)
 if width is not None:reader.need(4+width*max(count,0),field+'.elements')
 _use(budget,'elements',max(count,0));_use(budget,'nodes');reader.offset+=4;return count


def _float(reader,field):
 reader.need(4,field);raw=bytes(reader.data[reader.offset:reader.offset+4]);reader.offset+=4;value=struct.unpack('<f',raw)[0]
 return dict(bits=raw.hex().upper(),value=value if math.isfinite(value)else None,finite=math.isfinite(value))


def _vector(reader,field,axes='xyz'):return{axis:_float(reader,field+'.'+axis)for axis in axes}


class _EntityReader:
 """Adapt the dedicated list codec's explicit refusal to the outer reader."""
 def __init__(self,reader):self.reader=reader
 def __getattr__(self,name):return getattr(self.reader,name)
 @property
 def offset(self):return self.reader.offset
 @offset.setter
 def offset(self,value):self.reader.offset=value
 def refuse(self,field,reason,*values):raise ValueError(field+':'+reason+(':'+str(values)if values else''))


def _value_record(reader,field,operation,budget):
 _use(budget,'nodes');start=reader.offset;marker=reader.number('<B',field+'.memberCount');count=1 if operation=='lsm-mc1'else 5
 need('value-record-header',marker in(255,count));result=dict(startOffset=start,defaultValue=marker==255)
 if operation=='lsm-mc1':result['id']='0'if marker==255 else str(reader.number('<Q',field+'.id'))
 elif marker==255:
  zero=lambda:dict(bits='00000000',value=0.0,finite=True)
  result.update(eulerAngles={a:zero()for a in'xyz'},offset={a:zero()for a in'xyz'},radius=zero(),size={a:zero()for a in'xyz'},typeRaw=0)
 else:result.update(eulerAngles=_vector(reader,field+'.eulerAngles'),offset=_vector(reader,field+'.offset'),radius=_float(reader,field+'.radius'),
  size=_vector(reader,field+'.size'),typeRaw=reader.number('<i',field+'.type'))
 result['endOffset']=reader.offset;return result


def _list(reader,field,cap,table,budget,depth):
 start=reader.offset;op=cap['elementOperation'];width={'float32-bits':4,'int32':4,'uint64':8,'vector3-raw12':12}.get(op,1)
 count=_count(reader,field,cap['countLimit'],budget,width=width);rows=None
 if count>=0:
  rows=[]
  for i in range(count):
   path=field+'['+str(i)+']'
   if op=='record':value=_record(reader,path,table[cap['elementCapability']],table,budget,depth+1)
   elif op=='param-key-value':value=value_codec.read_parameter_record(reader,path,table[values.PARAM_ARRAY],budget=budget)
   elif op in('lsm-mc1','shape-mc5'):value=_value_record(reader,path,op,budget)
   else:
    _use(budget,'nodes')
    if op=='float32-bits':value=_float(reader,path)
    elif op=='int32':value=reader.number('<i',path)
    elif op=='uint64':value=str(reader.number('<Q',path))
    else:value=_vector(reader,path)
   rows.append(value)
 return dict(startOffset=start,endOffset=reader.offset,count=count,values=rows)


def _record(reader,field,cap,table,budget,depth):
 need('depth-limit',type(depth)is int and 0<=depth<64);_use(budget,'nodes');start=reader.offset
 marker=reader.number('<B',field+'.memberCount')
 if marker==255:return None
 need('exact-record-member-count',marker==cap['memberCount']);result=dict(typeName=cap['typeName'],startOffset=start,fieldRanges={})
 enums={r['typeName']:r['backingType']for r in cap.get('enumBackings',[])}
 for member,read in zip(cap['fields'],cap['program']['reads'],strict=True):
  name=member['fieldName'];nominal=member['declaredType'];kind=read['kind'];path=field+'.'+name;at=reader.offset;child=table.get(read.get('childCapability'))
  if kind=='bool-byte':
   raw=reader.number('<B',path);value=dict(value=bool(raw),wireByte=raw,storedByte=int(bool(raw)))
  elif kind=='scalar32':value=reader.number('<I'if nominal=='uint'or enums.get(nominal)=='uint'else'<i',path)
  elif kind=='scalar64-bits':value=str(reader.number('<Q'if nominal=='ulong'else'<q',path))
  elif kind=='float32-bits':value=_float(reader,path)
  elif kind=='float64-bits':
   reader.need(8,path);raw=bytes(reader.data[reader.offset:reader.offset+8]);reader.offset+=8;number=struct.unpack('<d',raw)[0]
   value=dict(bits=raw.hex().upper(),value=number if math.isfinite(number)else None,finite=math.isfinite(number))
  elif kind=='byte-payload':value=reader.string(path)
  elif kind=='unity-vector3-raw12':value=_vector(reader,path)
  elif kind=='unity-quaternion-raw16':value=_vector(reader,path,'xyzw')
  elif kind=='story-posrot-raw24':value=dict(position=_vector(reader,path+'.position'),eulerAngles=_vector(reader,path+'.eulerAngles'))
  elif kind==records.RECORD_WIRE:value=_record(reader,path,child,table,budget,depth+1)
  elif kind==records.LIST_WIRE:value=_list(reader,path,child,table,budget,depth+1)
  elif kind=='story-module-value-list':_use(budget,'nodes');value=value_codec.read_list(reader,path,child,budget=budget)
  elif kind==opera.WIRE:_use(budget,'nodes');value=value_codec.read_array(reader,path,child,budget=budget)
  elif kind==rune_arrays.WIRE:value=current_rune_arrays.read(reader,path,child,budget=budget)
  elif kind==rune_dictionary.WIRE:value=current_rune_dictionary.read(reader,path,child,budget=budget)
  elif kind=='entity-ptr-stored-value':_use(budget,'nodes');value=current_entity_ptr.read(reader,path,child)
  elif kind=='lang-key':_use(budget,'nodes');value=current_lang_key.read(reader,path,child)
  elif kind==enum_lists.WIRE:
   start_list=reader.offset;count=_count(reader,path,4096,budget,width=4);_use(budget,'nodes',max(0,count))
   rows=None if count==-1 else[]
   for i in range(max(0,count)):
    raw=bytes(reader.data[reader.offset:reader.offset+4]);reader.offset+=4;rows.append(dict(rawHex=raw.hex().upper()))
   value=dict(startOffset=start_list,endOffset=reader.offset,count=count,values=rows,elementType=child['elementType'])
  elif kind==entity_lists.WIRE:
   reader.need(4,path+'.count');count=struct.unpack_from('<i',reader.data,reader.offset)[0]
   need('bounded-Entity-list-count',-1<=count<=4096);reader.need(4+max(count,0),path+'.headers')
   _use(budget,'elements',max(count,0));needed=1+max(count,0);need('Entity-list-node-budget',needed<=budget['nodes'])
   local={'remaining':budget['nodes']};value=entity_codec.read(_EntityReader(reader),path,child,budget=local);budget['nodes']=local['remaining']
  else:raise ValueError('currentModuleGraph.unvalidated-operation:'+kind)
  result[name]=value;result['fieldRanges'][name]=[at,reader.offset]
 result['endOffset']=reader.offset;return result


def _union(reader,field,cap,budget,depth):
 need('depth-limit',type(depth)is int and 0<=depth<64);_use(budget,'nodes');start=reader.offset;tag=reader.number('<B',field+'.tag')
 if tag==255:return None
 if tag==250:
  # The owned helper accepts any UInt16 payload here; the selected finite
  # union table supplies the bound. It does not impose a shortest encoding.
  tag=reader.number('<H',field+'.extendedTag')
 else:need('reserved-union-marker',tag<250)
 need('selected-current-union-tag',str(tag)in cap['routes']);route=cap['routes'][str(tag)]
 value=_record(reader,field+'.value',cap['capabilities'][route['recordCapability']],cap['capabilities'],budget,depth+1)
 return dict(startOffset=start,endOffset=reader.offset,tag=tag,typeName=route['typeName'],value=value)


def read_union(reader,field,cap,*,budget=None):
 validate(cap);return _union(reader,field,cap,_budget(budget),0)


def read(reader,field,cap,*,budget=None):
 validate(cap);budget=_budget(budget);start=reader.offset;count=_count(reader,field,4096,budget,width=9);rows=None
 if count>=0:
  rows=[]
  for i in range(count):
   path=field+'['+str(i)+']';key=str(reader.number('<Q',path+'.key'));value=_union(reader,path+'.value',cap,budget,0)
   rows.append(dict(key=key,value=value))
 return dict(startOffset=start,endOffset=reader.offset,count=count,entries=rows,duplicateAndHashBehaviorAdmitted=False,
  runtimeModuleBehaviorAdmitted=False)
