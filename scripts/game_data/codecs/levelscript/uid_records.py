"""Current pooled LevelScript records, consumed from the three declared lists."""
import struct
from pathlib import Path
from typing import Any
from scripts.game_data.codecs.levelscript.framing_common import _is_printable_ascii
from scripts.game_data.string_pool import export_string_pool
from scripts.game_data.codecs.levelscript.action_map import ActionMapCodecError,decode_reviewed_node


def _extract_levelscript_tagged_ascii_strings(
    data: bytes,
    tag: int = 0x04,
    *,
    max_len: int = 120,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    end = len(data) - 5
    i = 0
    while i < end:
        if data[i] != tag:
            i += 1
            continue
        size = struct.unpack_from("<I", data, i + 1)[0]
        if size <= 0 or size > max_len or i + 5 + size > len(data):
            i += 1
            continue
        raw = data[i + 5 : i + 5 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({"offset": i, "text": text})
        i += 5 + size
    return hits


def _extract_levelscript_plain_ascii_strings(
    data: bytes,
    *,
    min_len: int = 3,
    max_len: int = 120,
    tagged_offsets: set[int] | None = None,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    tagged_offsets = tagged_offsets or set()
    end = len(data) - 4
    i = 0
    while i < end:
        size = struct.unpack_from("<I", data, i)[0]
        if size < min_len or size > max_len or i + 4 + size > len(data):
            i += 1
            continue
        if i > 0 and data[i - 1] == 0x04 and (i - 1) in tagged_offsets:
            i += 4 + size
            continue
        raw = data[i + 4 : i + 4 + size]
        if not _is_printable_ascii(raw):
            i += 1
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            i += 1
            continue
        hits.append({"offset": i, "payloadOffset": i + 4, "text": text})
        i += 4 + size
    return hits



LISTS=(('actionList','ActionBase'),('getterList','GetterBase'),('headerList','ActionHeader'))

class LevelScriptUidDecodeError(ValueError):
 def __init__(self,gate,**detail):
  self.diagnostics=dict(validator='levelscriptUidRecords',gate=gate,**detail)
  super().__init__(','.join(f'{key}={value}' for key,value in self.diagnostics.items()))

class LevelScriptUidRecords(list):
 def __init__(self,records,action_map):super().__init__(records);self.action_map=action_map


def typed_strings(node):
 """Only proved string fields and selected constant/path operands become text hits."""
 hits=[];spans=node.get('fieldRanges',node.get('fieldSpans',{}))
 def add(text,field,offset):
  if isinstance(text,str) and text:hits.append(dict(text=text,field=field,offset=offset,encoding='int32-pool-index'))
 for name,kind in node.get('fieldTypes',{}).items():
  span=spans.get(name);value=node['fields'].get(name)
  if not span or name=='uid':continue
  if kind=='string':add(value,name,span[0])
  elif kind.startswith(('Param<','ParamOutput<')) and isinstance(value,dict):
   if kind=='Param<string>' and value.get('paramSource')==0:add(value.get('value'),name+'.value',span[0]+1)
   add(value.get('path'),name+'.path',span[1]-4)
 return hits

def _map_start(data,offset):
 if offset is None:
  if len(data)<2 or data[0]!=28:raise LevelScriptUidDecodeError('levelScriptMemberCount',expected=28,actual=data[0] if data else None)
  if data[1]==255:return None
  if data[1]!=2:raise LevelScriptUidDecodeError('actionMapAssetMemberCount',expected=2,actual=data[1])
  offset=2
 if type(offset) is not int or not 0<=offset<len(data):raise LevelScriptUidDecodeError('mapOffset',offset=offset,bytes=len(data))
 return offset

def extract_levelscript_uid_records(data,*,strings=None,source_path=None,game_root=None,map_offset=None,null_list_params=None):
 """Refuse an unknown child instead of guessing its end or returning an empty graph."""
 if source_path is not None and strings is None:
  parents=[p for p in Path(source_path).parents if p.name=='Json']
  if len(parents)!=1:raise LevelScriptUidDecodeError('sourceJsonRoot',source=str(source_path))
  strings=export_string_pool(parents[0])
 map_offset=_map_start(data,map_offset)
 if map_offset is None:return LevelScriptUidRecords([],dict(status='null',serializedLists=[],listCounts={}))
 marker=data[map_offset]
 if marker==255:return LevelScriptUidRecords([],dict(status='null',serializedLists=[],listCounts={}))
 if marker!=3:raise LevelScriptUidDecodeError('mapMemberCount',expected=3,actual=marker,offset=map_offset)
 cursor=map_offset+1;records=[];lists=[]
 for name,family in LISTS:
  count_at=cursor
  if cursor+4>len(data):raise LevelScriptUidDecodeError('listCountTruncated',family=family,offset=cursor)
  count=struct.unpack_from('<i',data,cursor)[0];cursor+=4;first=len(records)
  if not 0<=count<=10000:raise LevelScriptUidDecodeError('listCount',family=family,offset=count_at,expected='0..10000',actual=count)
  for index in range(count):
   start=cursor
   try:node,cursor=decode_reviewed_node(data,cursor,family,strings=strings,game_root=game_root,null_list_params=null_list_params)
   except (ActionMapCodecError,ValueError) as error:
    raise LevelScriptUidDecodeError('typedNode',family=family,index=index,offset=start,detail=str(error)[:1000]) from error
   if node.get('sourceOffset')!=start or node.get('endOffset')!=cursor or not start<cursor<=len(data):
    raise LevelScriptUidDecodeError('nodeBoundary',family=family,index=index,offset=start,endOffset=cursor)
   fields=node['fields'];tag=node['unionTag'];members=node['memberCount']
   common=7 if family=='GetterBase' else 14 if family=='ActionHeader' else 8
   ranges=node.get('fieldRanges',node.get('fieldSpans',{}))
   common_name=list(fields)[common-1] if len(fields)>=common else None
   if common_name not in ranges:raise LevelScriptUidDecodeError('commonFieldBoundary',family=family,index=index,offset=start)
   payload_start=ranges[common_name][1]
   records.append(dict(start=start,end=cursor,layout='pooled',code=tag,kind=members,unionTag=tag,
    serializedMemberCount=members,unionTagEncoding='memorypack-fa-u16' if data[start]==250 else 'memorypack-u8',
    dontLog=fields.get('dontLogWarning'),localId=fields.get('ID'),uid=fields.get('uid'),nextId=fields.get('nextID'),
    listName=name,listIndex=index,family=family,typedNode=node,payloadStart=payload_start,
    strings=typed_strings(node),plainStrings=[]))
  lists.append(dict(name=name,status='present',count=count,countOffset=hex(count_at),countMarker=count,
   recordIndexStart=first,recordIndexEnd=len(records),decodedRecordCount=count,source='sequentialTypedPooledRecords'))
 return LevelScriptUidRecords(records,dict(status='present',serializedLists=lists,
  listCounts={r['name']:r['count'] for r in lists},serializedListOrder=[r[0] for r in LISTS],
  exactEmptyActionMap=not records,dataMapEndOffset=cursor))

def frame_uid_record_lists(data, records, *, map_offset=None):
 """Recheck declared counts and exact cursors when callers copy or sort records."""
 map_offset=_map_start(data,map_offset)
 if map_offset is None:
  if records:raise LevelScriptUidDecodeError('recordsOutsideNullMap',actual=len(records))
  return dict(status='null',serializedLists=[],listCounts={})
 if data[map_offset]==255:
  if records:raise LevelScriptUidDecodeError('recordsOutsideNullMap',actual=len(records))
  return dict(status='null',serializedLists=[],listCounts={})
 if data[map_offset]!=3:raise LevelScriptUidDecodeError('mapMemberCount',offset=map_offset)
 ordered=sorted(records,key=lambda r:r.get('start',-1));cursor=map_offset+1;index=0;lists=[]
 for name,family in LISTS:
  count_at=cursor
  if cursor+4>len(data):raise LevelScriptUidDecodeError('listCountTruncated',family=family,offset=cursor)
  count=struct.unpack_from('<i',data,cursor)[0];cursor+=4;first=index
  if not 0<=count<=10000:raise LevelScriptUidDecodeError('listCount',family=family,offset=count_at,actual=count)
  for ordinal in range(count):
   row=ordered[index] if index<len(ordered) else {}
   end=row.get('end')
   if (row.get('start')!=cursor or row.get('family')!=family or row.get('listIndex')!=ordinal
       or not isinstance(end,int) or not cursor<end<=len(data) or not row.get('typedNode')):
    raise LevelScriptUidDecodeError('sequentialRecordBoundary',family=family,index=ordinal,offset=cursor,availableRecords=len(ordered))
   cursor=end;index+=1
  lists.append(dict(name=name,status='present',count=count,countOffset=hex(count_at),countMarker=count,
   recordIndexStart=first,recordIndexEnd=index,decodedRecordCount=count,source='sequentialTypedPooledRecords'))
 if index!=len(ordered):raise LevelScriptUidDecodeError('recordsOutsideMap',expected=index,actual=len(ordered))
 return dict(status='present',serializedLists=lists,listCounts={r['name']:r['count'] for r in lists},
  serializedListOrder=[r[0] for r in LISTS],exactEmptyActionMap=not ordered,dataMapEndOffset=cursor)
