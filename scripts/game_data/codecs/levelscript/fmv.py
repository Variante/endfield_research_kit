"""Current pooled stored FMV fields and bounded conditional name candidates."""
import hashlib,struct
from scripts.game_data.levelscript_union_tags import short_name
from scripts.game_data.codecs.levelscript.string_param import decode_string_param

def project_typed_fmv(node,payload_start,payload_end):
 """Structural projection only; the owning reader gates complete parent/Param."""
 action=short_name(node['wrapperName']);field={'PlayFmvAction':'moviePath','StartFmvAndTeleportAction':'fmvId'}.get(action)
 if field is None or node.get('fieldTypes',{}).get(field)!='Param<string>':return None
 param=node['fields'].get(field);span=node.get('fieldRanges',{}).get(field)
 if(not isinstance(param,dict)or type(param.get('paramSource'))is not int or param['paramSource']!=0 or type(param.get('idRef'))is not int or not -(1<<31)<=param['idRef']<1<<31 or not isinstance(param.get('value'),str)or not param['value']or not isinstance(span,(list,tuple))or len(span)!=2 or any(type(at)is not int for at in span)or not payload_start<=span[0]<span[1]<=payload_end or span[1]-span[0]!=17):return None
 return dict(action=action,fmvId=param['value'],sourceField='_'+field,fieldOffset=hex(span[0]),valueOffset=hex(span[0]+1),fieldEndOffset=hex(span[1]),payloadShape='fmv-stored-current-pooled-param',evidenceBoundary='structuralOnly')

def project_owner(data,frame,*,source,strings):
 """Re-read exact typed fields after a fresh owning reader reaches physical EOF."""
 if frame.get('schemaStatus')!='named_exact'or type(frame.get('bytesConsumed'))is not int or frame['bytesConsumed']!=len(data):raise ValueError('fmvOwner.complete-named-eof-required:'+source+':schema='+str(frame.get('schemaStatus'))+':consumed='+str(frame.get('bytesConsumed'))+':stop='+str(frame.get('stopField')))
 action_map=frame.get('ranges',{}).get('actionMap',{})
 if action_map.get('value','present')is None:return dict(rows=[],diagnostics=[])
 data_map=action_map.get('dataMap',{});actions=data_map.get('actionList',[])
 if type(data_map.get('actionListCount'))is not int or data_map['actionListCount']!=len(actions):raise ValueError('fmvOwner.complete-typed-action-list-required:'+source)
 rows=[];diagnostics=[]
 for node in actions:
  name=short_name(node['wrapperName'])
  if name not in('PlayFmvAction','StartFmvAndTeleportAction'):continue
  spans=node.get('fieldRanges',{});fields=node['fields'];common=list(fields)[7]if len(fields)>=8 else None
  if common not in spans:raise ValueError('fmvOwner.common-field-boundary:'+source)
  start,end=node['sourceOffset'],node['endOffset'];payload_start=spans[common][1]
  if type(start)is not int or type(end)is not int or not 0<=start<payload_start<=end<=len(data):raise ValueError('fmvOwner.action-boundary:'+source)
  projection=project_typed_fmv(node,payload_start,end)
  if projection is None:diagnostics.append(dict(action=name,actionStart=start,check='fmvOwner.stored-constant-projection-unavailable'));continue
  at,stop=spans[projection['sourceField'][1:]];decoded=decode_string_param(data,at,strings=strings)
  if decoded is None or decoded!=(fields[projection['sourceField'][1:]],stop):raise ValueError('fmvOwner.exact-pooled-field-join:'+source)
  row=dict(source=source,sourceSha256=hashlib.sha256(data).hexdigest().upper(),ownerBytes=len(data),actionStart=start,actionEnd=end,unionTag=node['unionTag'],memberCount=node['memberCount'],fieldRange=[at,stop],valuePoolIndex=struct.unpack_from('<i',data,at+1)[0],pathPoolIndex=struct.unpack_from('<i',data,stop-4)[0],storedParam=fields[projection['sourceField'][1:]],projection=projection)
  if name!='PlayFmvAction':diagnostics.append(dict(action=name,actionStart=start,check='fmvOwner.current-native-name-consumer-unproved'));continue
  rows.append(row)
 return dict(rows=rows,diagnostics=diagnostics)

def name_candidates(movie,layout):
 """Pure recipe; callers freshly authenticate the native gate for each operation.

 Each returned path has explicit gender/existence/suffix-result witnesses.
 File matches establish neither those live results nor action execution.
 """
 if not isinstance(movie,str)or not movie or len(movie.encode('utf-16-le'))//2>layout['maxSourceUtf16Chars']:raise ValueError('fmvName.source-outside-proved-UTF16-bound')
 rows=[]
 for prefix in('',*layout['genderPrefixes']):
  value=prefix+movie;subpath=layout['subpathTemplate'].format(value)
  for has_suffix,template in zip((True,False),layout['templates']):
   path=template.format(layout['root'],subpath)
   if len(path.encode('utf-16-le'))//2>layout['maxIntermediateUtf16Chars']:raise ValueError('fmvName.intermediate-outside-proved-UTF16-bound')
   rows.append(dict(path=path,variant=prefix[:-1]if prefix else'fallback',selectedPrefixExists=bool(prefix),effectiveGender='Female'if prefix=='f_'else'not-Female'if prefix else'candidate-missing',hasUsmSuffixComparison=has_suffix,evidenceBoundary='conditional'))
 return rows
