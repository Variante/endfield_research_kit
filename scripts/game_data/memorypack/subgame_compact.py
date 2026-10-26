"""Bounded conditional compact WorldChallenge table framing after native admission."""
import re
from scripts.game_data.string_pool import StringPoolDecodeError

class SubGameDecodeError(ValueError):pass

def frame(data,strings,layout):
 if strings is None:raise SubGameDecodeError('SubGame table requires an explicit current string pool')
 offset=0;task_total=0
 def take(size,field):
  nonlocal offset
  if offset+size>len(data):raise SubGameDecodeError(field+': truncated')
  start=offset;offset+=size;return data[start:offset]
 def number(size,field,signed=False):return int.from_bytes(take(size,field),'little',signed=signed)
 def header(expected,field):
  actual=number(1,field)
  if actual!=expected:raise SubGameDecodeError(f'{field}: member count {actual}, expected {expected}')
 def pooled(field):
  try:return strings.resolve(number(4,field+'.poolIndex',True))
  except StringPoolDecodeError as error:raise SubGameDecodeError(field+': '+str(error))from error
 def count(limit,field):
  n=number(4,field+'.count',True)
  if not -1<=n<=limit:raise SubGameDecodeError(f'{field}: count {n} outside reviewed -1..{limit} source profile')
  return max(n,0)
 def task(field):
  marker=number(1,field)
  if marker==255:return
  if marker!=1:raise SubGameDecodeError(field+': task member count is not 1/null')
  pooled(field+'.taskId')
 def value(field):
  nonlocal task_total
  name,kind,typ=field['name'],field['kind'],field['type']
  if kind=='string':return pooled(name)
  if kind=='lang':
   marker=number(1,name)
   if marker==255:return
   if marker!=1:raise SubGameDecodeError(name+': LangKey member count is not 1/null')
   return pooled(name+'.key')
  if kind=='list':
   element=typ.removeprefix('System.Collections.Generic.List`1<').removesuffix('>')
   if element=='ulong':
    n=number(4,name+'.count',True)
    if n!=-1:raise SubGameDecodeError(name+': only the reviewed null UInt64-list source path is admitted')
    return 0
   if element not in('string','Beyond.Gameplay.Core.SubGameInstanceData+Task'):raise SubGameDecodeError(name+': unreviewed list element')
   n=count(3 if element=='string'else 1,name)
   for i in range(n):(pooled if element=='string'else task)(f'{name}[{i}]')
   if element!='string':task_total+=n
   return n
  if kind not in('bool','enum','int','qword','area'):raise SubGameDecodeError(name+': unreviewed scalar kind')
  return number(1 if kind=='bool'else 8 if kind in('qword','area')else 4,name,kind in('enum','int'))
 header(1,'SubGame table');n=count(4,'dataTable');rows=[]
 for i in range(n):
  start=offset;key=pooled(f'dataTable[{i}].key')
  if not key or not re.fullmatch('[A-Za-z0-9_]+',key):raise SubGameDecodeError(f'dataTable[{i}]: invalid key')
  tag=number(1,f'dataTable[{i}].union')
  if tag==250:tag=number(2,f'dataTable[{i}].extendedUnion')
  if tag!=layout['unionTag']:raise SubGameDecodeError(f'dataTable[{i}]: union {tag} outside reviewed WorldChallenge route')
  header(len(layout['fields']),f'dataTable[{i}]');values={f['name']:value(f)for f in layout['fields']}
  if values.get('id')!=key:raise SubGameDecodeError(f'dataTable[{i}]: key/id mismatch')
  rows.append(dict(startOffset=start,endOffset=offset,key=key,unionTag=tag,memberCount=len(layout['fields']),spawnerIdCount=values.get('spawnerIds',0),areaId=values.get('isolateEntityArea')))
 if offset!=len(data):raise SubGameDecodeError(f'SubGame table trailing bytes: {len(data)-offset}')
 return dict(status='exact',schemaStatus='named_exact',bytesConsumed=offset,entryCount=n,taskCount=task_total,rows=rows)
