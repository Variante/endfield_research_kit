"""Exact current Module value children behind independently joined source caps."""
import math
import struct

from scripts.game_data.memorypack import levelscript_module_value_components as profiles
from scripts.game_data.codecs.levelscript.param_graph import Reader as GraphReader


def need(key,condition):
 if not condition:raise ValueError('currentModuleValues.'+key)


def _int(cap,key,value):return type(cap.get(key))is int and cap[key]==value


def validate_parameters(cap):
 need('exact-Param-array-capability',isinstance(cap,dict)and cap.get('schema')==profiles.PARAM_SCHEMA
  and(cap.get('capability'),cap.get('typeName'),cap.get('elementType'))==(profiles.PARAM_ARRAY,profiles.PKV+'[]',profiles.PKV)
  and all(_int(cap,k,v)for k,v in dict(countLimit=4096,nestedAtomCountLimit=16384,nodeLimit=16384,elementLimit=16384,nullIndex=-2,emptyIndex=-1).items())
  and cap.get('memberCounts')==dict(keyValue=2,value=2,atom=2)and cap.get('atomFFOutput')=='zero64-and-null-string'
  and cap.get('stringEncoding')=='int32-pool-index'
  and type(cap.get('arrayReaderMethodDefinition'))is int and cap['arrayReaderMethodDefinition']>=0
  and type(cap.get('arrayReaderTargetRva'))is int and cap['arrayReaderTargetRva']>0
  and all(cap.get(k)is True for k in('positiveCountsAdmitted','actualCallbackEqualsCanonicalRequired','profileAdmitted'))
  and all(cap.get(k)is False for k in('parentFieldAdmitted','wholeOwnerAdmitted','liveFormatterSelectionObserved')))


def validate_value(cap):
 need('finite-value-capability',isinstance(cap,dict)and cap.get('typeName')in profiles.VALUE_CAPS)
 name=cap['typeName'];fields,refs,padding=profiles.LAYOUTS[name];width=profiles.values.WIDTHS[name]
 need('exact-canonical-value-capability',cap.get('schema')==profiles.VALUE_SCHEMA and cap.get('capability')==profiles.VALUE_CAPS[name]
  and all(_int(cap,k,v)for k,v in dict(managedBytes=width,memberCount=len(profiles.VALUE_ORDER[name]),canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=width).items())
  and cap.get('serializedOrder')==profiles.VALUE_ORDER[name]and cap.get('referenceLaneOffsets')==refs
  and cap.get('paddingByteRanges')==padding and cap.get('paddingRangesAreStartEnd')is True
  and type(cap.get('originalTypeDefinition'))is int and cap['originalTypeDefinition']>=0
  and type(cap.get('canonicalCallbackTargetRva'))is int and cap['canonicalCallbackTargetRva']>0
  and cap.get('positiveWireBytes')==(14 if name==profiles.values.AIRWALL else 45 if name==profiles.values.EFFECT else None)
  and cap.get('booleanNormalization')==('any-nonzero-byte-to-one'if name==profiles.values.AIRWALL else None)
  and all(cap.get(k)is True for k in('canonicalOriginalAdapterAdmitted','actualCallbackEqualsCanonicalRequired','profileAdmitted','rawIeeeBitsPreserved'))
  and all(cap.get(k)is False for k in('liveFormatterSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted')))
 if name==profiles.values.OPERA:validate_parameters(cap.get('parametersCapability'))
 else:need('no-unowned-parameters',cap.get('parametersCapability')is None)


def validate_list(cap):
 need('finite-list-capability',isinstance(cap,dict)and cap.get('elementType')in profiles.LIST_CAPS)
 name=cap['elementType'];child=cap.get('elementCapability');validate_value(child)
 need('exact-value-list-capability',cap.get('schema')==profiles.LIST_SCHEMA and cap.get('capability')==profiles.LIST_CAPS[name]
  and cap.get('typeName')=='System.Collections.Generic.List`1<'+name+'>'and child['typeName']==name
  and all(_int(cap,k,v)for k,v in dict(countLimit=4096,headerBytes=4,managedElementBytes=profiles.values.WIDTHS[name]).items())
  and cap.get('countRange')==[-1,4096]and cap.get('elementWireBytes','missing')is None
  and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>=0
  and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0
  and all(cap.get(k)is True for k in('initiallyNullListRequired','actualCallbackEqualsCanonicalRequired','positiveCountsAdmitted','completeManagedValueStored','profileAdmitted'))
  and all(cap.get(k)is False for k in('growthAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))


def validate_array(cap):
 need('exact-value-array-capability',isinstance(cap,dict)and cap.get('schema')==profiles.ARRAY_SCHEMA
  and(cap.get('capability'),cap.get('typeName'),cap.get('elementType'))==
   (profiles.OPERA_ARRAY,profiles.values.OPERA+'[]',profiles.values.OPERA)
  and all(_int(cap,k,v)for k,v in dict(countLimit=4096,headerBytes=4,managedElementBytes=16).items())
  and cap.get('countRange')==[-1,4096]and cap.get('elementWireBytes','missing')is None
  and type(cap.get('arrayReaderMethodDefinition'))is int and cap['arrayReaderMethodDefinition']>=0
  and type(cap.get('arrayReaderTargetRva'))is int and cap['arrayReaderTargetRva']>0
  and all(cap.get(k)is True for k in('initiallyNullArrayRequired','actualCallbackEqualsCanonicalRequired','positiveCountsAdmitted','profileAdmitted'))
  and all(cap.get(k)is False for k in('parentFieldAdmitted','wholeOwnerAdmitted')))
 validate_value(cap.get('elementCapability'));need('own-Opera-element',cap['elementCapability']['typeName']==profiles.values.OPERA)


def _budget(budget):
 if budget is None:return dict(nodes=16384,elements=16384)
 need('shared-resource-budget',isinstance(budget,dict)and all(type(budget.get(k))is int and 0<=budget[k]<=16384 for k in('nodes','elements')))
 return budget


def _use(budget,key,amount):
 need('resource-'+key,type(amount)is int and 0<=amount<=budget[key]);budget[key]-=amount


def _count(reader,field,limit,budget):
 reader.need(4,field+'.count');count=struct.unpack_from('<i',reader.data,reader.offset)[0]
 need('count-domain',-1<=count<=limit);_use(budget,'elements',max(count,0));reader.offset+=4
 return count


def _single(reader,field):
 at=reader.offset;reader.need(4,field);raw=bytes(reader.data[at:at+4]);reader.offset+=4;value=struct.unpack('<f',raw)[0]
 return dict(value=value if math.isfinite(value)else None,bits=raw.hex().upper(),finite=math.isfinite(value))


def _vector(reader,field):return{axis:_single(reader,field+'.'+axis)for axis in'xyz'}
def _zero_single():return dict(value=0.0,bits='00000000',finite=True)
def _zero_vector():return{axis:_zero_single()for axis in'xyz'}


class _Parameters(GraphReader):
 def __init__(self,reader,field,budget):super().__init__(reader.data,reader.offset,reader.strings,field);self.budget=budget
 def member(self,field,count):_use(self.budget,'nodes',1);return super().member(field,count)
 def items(self,field,decode):
  start=self.offset;count=_count(self,field,16384,self.budget)
  return dict(startOffset=start,endOffset=self.offset,count=-1,values=None)if count==-1 else self._items(field,start,count,decode)
 def _items(self,field,start,count,decode):
  values=[decode(field+'['+str(i)+']')for i in range(count)]
  return dict(startOffset=start,endOffset=self.offset,count=count,values=values)


def read_parameters(reader,field,cap,*,budget=None):
 validate_parameters(cap);budget=_budget(budget);start=reader.offset;count=_count(reader,field,4096,budget)
 rows=None
 if count!=-1:
  cursor=_Parameters(reader,field,budget);rows=[cursor.key_value(field+'['+str(i)+']')for i in range(count)];reader.offset=cursor.offset
 return dict(startOffset=start,endOffset=reader.offset,count=count,values=rows,runtimeParameterEvaluationAdmitted=False)


def read_parameter_record(reader,field,cap,*,budget=None):
 """One independently framed List element; this consumes no array header."""
 validate_parameters(cap);budget=_budget(budget)
 cursor=_Parameters(reader,field,budget);value=cursor.key_value(field);reader.offset=cursor.offset
 return value


def read_value(reader,field,cap,*,budget=None):
 validate_value(cap);budget=_budget(budget);_use(budget,'nodes',1);start=reader.offset;marker=reader.number('<B',field+'.memberCount')
 need('canonical-member-count',marker in(255,cap['memberCount']));name=cap['typeName']
 result=dict(startOffset=start,typeName=name,memberCount=marker,defaultValue=marker==255,fieldRanges={})
 if marker==255:
  if name==profiles.values.EFFECT:result.update(delayToHide=_zero_single(),effectKey=None,eulerAngles=_zero_vector(),position=_zero_vector(),scale=_zero_vector())
  elif name==profiles.values.AIRWALL:result.update(logicId='0',slotId=0,useSlotId=dict(value=False,wireByte=None,storedByte=0))
  else:result.update(operaType=dict(value=0,bits='00000000'),parameters=None)
 else:
  for member,declared in cap['serializedOrder']:
   at=reader.offset;path=field+'.'+member
   if declared=='float':value=_single(reader,path)
   elif declared=='UnityEngine.Vector3':value=_vector(reader,path)
   elif declared=='string':value=reader.string(path)
   elif declared=='ulong':value=str(reader.number('<Q',path))
   elif declared=='uint':value=reader.number('<I',path)
   elif declared=='bool':
    raw=reader.number('<B',path);value=dict(value=bool(raw),wireByte=raw,storedByte=int(bool(raw)))
   elif member=='operaType':
    raw=reader.number('<i',path);value=dict(value=raw,bits=struct.pack('<i',raw).hex().upper())
   else:value=read_parameters(reader,path,cap['parametersCapability'],budget=budget)
   result[member]=value;result['fieldRanges'][member]=[at,reader.offset]
 result.update(endOffset=reader.offset,runtimeModuleBehaviorAdmitted=False);return result


def read_list(reader,field,cap,*,budget=None):
 validate_list(cap);return _read_collection(reader,field,cap,_budget(budget))


def read_array(reader,field,cap,*,budget=None):
 validate_array(cap);return _read_collection(reader,field,cap,_budget(budget))


def _read_collection(reader,field,cap,budget):
 start=reader.offset;count=_count(reader,field,4096,budget);reader.need(max(count,0),field+'.elementHeaders')
 rows=None if count==-1 else[read_value(reader,field+'['+str(i)+']',cap['elementCapability'],budget=budget)for i in range(count)]
 return dict(startOffset=start,endOffset=reader.offset,count=count,values=rows,runtimeModuleBehaviorAdmitted=False)
