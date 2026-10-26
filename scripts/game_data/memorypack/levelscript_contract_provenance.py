"""Story-specific native data/trace envelopes over the shared compact graph.

Literal native constant data retain their exact range, bytes and native hash.
They never enter the code-window catalog. Additional explicitly named source
region traces use the shared trace omission policy; all semantic keys and
conditions remain lossless. No tracked-contract digest or admission is added.
"""
import hashlib
import re

from scripts.game_data.memorypack import skill_contract_provenance as common

CONSTANT='$storyNativeConstantData'
REGIONS='$storyNativeRegionTrace'
CODE='$storyNativeCodeObservation'
PREFIX='$storyNativePrefixWindow'
REGION_KEYS={'sourceRegions','actualSourceRegions','actualRegions','sourceRegionsRva','ownedSourceRegions'}
HEX=re.compile(r'[0-9a-fA-F]+')


def need(check,condition):
 if not condition:raise ValueError('levelscriptContractProvenance.'+check)


def _constant(value):
 need('exact-native-constant-fields',type(value)is dict and set(value)in({'startRva','endRva','sha256','hex'},{'startRva','endRva','sha256','raw'}))
 payload='hex'if'hex'in value else'raw'
 start,end,encoded,digest=(value[key]for key in('startRva','endRva',payload,'sha256'))
 need('native-constant-range',type(start)is int and type(end)is int and 0<=start<end<=1<<32)
 need('native-constant-bytes',type(encoded)is str and bool(encoded)and len(encoded)%2==0 and HEX.fullmatch(encoded)is not None)
 raw=bytes.fromhex(encoded)
 need('native-constant-hash',type(digest)is str and len(digest)==64 and HEX.fullmatch(digest)is not None
  and len(raw)==end-start and hashlib.sha256(raw).hexdigest().upper()==digest.upper())
 return value


def _regions(value):
 return(isinstance(value,list)and bool(value)and all(isinstance(row,list)and len(row)==2
  and type(row[0])is int and row[0]>=0 and type(row[1])is str and bool(row[1])
  and len(row[1])%2==0 and HEX.fullmatch(row[1])is not None for row in value))


def _encode(value,role='',*,depth=0,active=None):
 need('bounded-source-depth',depth<=256)
 if active is None:active=set()
 if isinstance(value,(dict,list)):
  need('acyclic-source-proof',id(value)not in active)
  active.add(id(value))
  try:return _encode_value(value,role,depth,active)
  finally:active.remove(id(value))
 return value


def _encode_value(value,role,depth,active):
 if isinstance(value,dict):
  need('reserved-envelope-key-absent',not{CONSTANT,REGIONS,CODE,PREFIX}&set(value))
  if {'startRva','endRva','sha256'}<=set(value)and('hex'in value or'raw'in value):
   _constant(value)
   return {CONSTANT:[[key,value[key]]for key in sorted(value)]}
  if set(value)=={'startRva','endRva','sha256','rawHex','rows'}:
   _constant(dict(startRva=value['startRva'],endRva=value['endRva'],sha256=value['sha256'],hex=value['rawHex']))
   need('complete-decoded-code-observation',common._trace(value['rows'],'rows')=='decoded-rows')
   return {CODE:dict(window={key:value[key]for key in('startRva','endRva','sha256')},
    regions=[[value['startRva'],value['rawHex']]],rows=value['rows'])}
  if set(value)=={'startRva','endRva','sha256','physicalExtentProved'}:
   need('literal-physical-extent-condition',type(value['physicalExtentProved'])is bool)
   return {PREFIX:dict(window={key:value[key]for key in('startRva','endRva','sha256')},physicalExtentProved=value['physicalExtentProved'])}
  return {key:_encode(item,key,depth=depth+1,active=active)for key,item in value.items()}
 if isinstance(value,list):
  if role in REGION_KEYS and _regions(value):return {REGIONS:{'regions':value}}
  return [_encode(item,role,depth=depth+1,active=active)for item in value]
 return value


def _decode(value):
 if isinstance(value,dict):
  if CONSTANT in value:
   need('constant-envelope-shape',set(value)=={CONSTANT}and isinstance(value[CONSTANT],list)
    and all(isinstance(row,list)and len(row)==2 and isinstance(row[0],str)for row in value[CONSTANT]))
   pairs=value[CONSTANT];keys=[row[0]for row in pairs]
   need('constant-envelope-ordered-unique-keys',keys in(sorted({'startRva','endRva','sha256','hex'}),sorted({'startRva','endRva','sha256','raw'})))
   return _constant(dict(pairs))
  if REGIONS in value:
   need('region-envelope-shape',set(value)=={REGIONS}and isinstance(value[REGIONS],dict)and set(value[REGIONS])=={'regions'})
   marker=value[REGIONS]['regions']
   need('region-envelope-owned-trace',isinstance(marker,dict)and marker.get('$omittedTrace')=='raw-regions')
   return marker
  if CODE in value:
   body=value[CODE]
   need('code-observation-envelope-shape',set(value)=={CODE}and isinstance(body,dict)and set(body)=={'window','regions','rows'})
   need('code-observation-owned-traces',isinstance(body['regions'],dict)and isinstance(body['rows'],dict)
    and body['regions'].get('$omittedTrace')=='raw-regions'
    and body['rows'].get('$omittedTrace')=='decoded-rows'and common._window(body['window'])is not None)
   return dict(body['window'],rawHex=body['regions'],rows=body['rows'])
  if PREFIX in value:
   body=value[PREFIX]
   need('prefix-window-envelope-shape',set(value)=={PREFIX}and isinstance(body,dict)and set(body)=={'window','physicalExtentProved'}
    and type(body['physicalExtentProved'])is bool and common._window(body['window'])is not None)
   return dict(body['window'],physicalExtentProved=body['physicalExtentProved'])
  return {key:_decode(item)for key,item in value.items()}
 if isinstance(value,list):return [_decode(item)for item in value]
 return value


def project_contract(contract,*,image_base=None):
 need('full-contract-proof',isinstance(contract,dict)and isinstance(contract.get('proof'),dict))
 prepared=dict(contract);prepared['proof']=_encode(contract['proof'])
 return common.project_contract(prepared,image_base=image_base)


def expand_proof(projection):
 return _decode(common.expand_proof(projection))


def validate_projection(projection):
 result=common.validate_projection(projection);expand_proof(projection)
 return result
