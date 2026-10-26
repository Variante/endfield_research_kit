"""Current pooled graph records; the owning caller authenticates native facts."""
import struct
from scripts.game_data.string_pool import resolve_string_pool_index

class ParamGraphDecodeError(ValueError):pass

class Reader:
 def __init__(self,data,offset,strings,field):self.data=data;self.offset=offset;self.strings=strings;self.field=field
 def need(self,size,field):
  if type(self.offset) is not int or not 0<=self.offset<=len(self.data)-size:raise ParamGraphDecodeError(f'{field}:truncated,offset={self.offset},size={size},bytes={len(self.data)}')
 def number(self,fmt,field):
  size=struct.calcsize(fmt);self.need(size,field);value=struct.unpack_from(fmt,self.data,self.offset)[0];self.offset+=size;return value
 def member(self,field,count):
  marker=self.number('<B',field+'.memberCount')
  if marker==255:return False
  if marker!=count:raise ParamGraphDecodeError(f'{field}:member-count,offset={self.offset-1},expected={count},actual={marker}')
  return True
 def string(self,field):
  index=self.number('<i',field+'.poolIndex')
  try:return resolve_string_pool_index(index,self.strings,field)
  except ValueError as error:raise ParamGraphDecodeError(str(error)) from error
 def items(self,field,decode):
  start=self.offset;count=self.number('<i',field+'.count')
  if count==-1:return dict(status='null',count=None,values=None)
  if not 0<=count<=16384:raise ParamGraphDecodeError(f'{field}:unsupported-count,offset={start},actual={count}')
  values=[decode(f'{field}[{i}]') for i in range(count)]
  return dict(status='present',count=count,values=values,startOffset=start,endOffset=self.offset)
 def atom(self,field):
  if not self.member(field,2):return dict(valueBit64=0,valueString=None,wasNull=True)
  return dict(valueBit64=self.number('<q',field+'.valueBit64'),valueString=self.string(field+'.valueString'))
 def value(self,field):
  if not self.member(field,2):return None
  return dict(typeRaw=self.number('<i',field+'.type'),valueArray=self.items(field+'.valueArray',self.atom))
 def key_value(self,field):
  if not self.member(field,2):return None
  return dict(key=self.string(field+'.key'),value=self.value(field+'.value'))


def decode_param_key_value_list(data,offset,field='paramKeyValues',*,strings=None):
 reader=Reader(data,offset,strings,field);result=reader.items(field,reader.key_value)
 return result,reader.offset


def decode_param_blackboard(data,offset,*,strings=None):
 reader=Reader(data,offset,strings,'actionMap.paramBlackboard');start=offset
 if not reader.member(reader.field,1):return None,reader.offset
 reader.need(4,reader.field+'.value.count');count=struct.unpack_from('<i',data,reader.offset)[0]
 if count>0:
  from scripts.game_data.levelscript_param_list_native import load_param_list_for_graph_contract
  layout,audit=load_param_list_for_graph_contract()
  if layout is None:raise ParamGraphDecodeError(f"{reader.field}.nativeContract: status={audit['status']}, count={count}, detail={audit.get('detail','')}")
 value=reader.items(reader.field+'.value',reader.key_value)
 return dict(startOffset=start,endOffset=reader.offset,serializedMemberCount=1,valueCount=value['count'],value=value['values']),reader.offset
