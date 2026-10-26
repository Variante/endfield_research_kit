"""Pooled opera arrays after independent opera and Param-graph native gates."""
from scripts.game_data.codecs.levelscript.param_graph import Reader,ParamGraphDecodeError

def decode_positive_encounter_opera_segments(data,offset,field,contract,*,strings=None):
 if contract.get('schema')!='endfield.levelscript-encounter-opera-segments-native.v3':raise ParamGraphDecodeError(field+':current-opera-contract-required')
 reader=Reader(data,offset,strings,field)
 def segment(name):
  start=reader.offset
  if not reader.member(name,2):return dict(operaTypeRaw=0,parameters=None,wasNull=True,startOffset=start,endOffset=reader.offset)
  value=dict(operaTypeRaw=reader.number('<i',name+'.operaType'),parameters=reader.items(name+'.parameters',reader.key_value),startOffset=start)
  value['endOffset']=reader.offset;return value
 value=reader.items(field,segment)
 return value,reader.offset
