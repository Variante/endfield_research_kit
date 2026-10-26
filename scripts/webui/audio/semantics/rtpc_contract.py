"""Current selected Audio static identities, independent of old callsite rows."""
from scripts.game_data.audio_static_names_native import declarations,validate as validate_names

_FACT=declarations()
CANONICAL_METADATA_PREFIX=_FACT['rtpc']['typeName']+'.'
CANONICAL_RTPC_IDS={f['name']:f['value']for f in _FACT['rtpc']['fields']}
CANONICAL_RTPC_HEX={name:f'0x{value:08x}'for name,value in CANONICAL_RTPC_IDS.items()}
BOUNDARY='Exact selected static metadata field names and UInt32 defaults cross-matched to authored HIRC RTPC IDs; no live setter, target, branch, DSP state or audibility is observed.'

def selected_static_names(context):
 if context is None:return dict(status='missing',detail='Audio selected native context was not provided')
 if not getattr(context,'gate_verified',False):return dict(status='unverified',detail='Audio explicit selected native pair was not authenticated')
 # The old callsite disposition is independent; this gate freshly checks its own facts.
 return validate_names(gameassembly=getattr(context,'gameassembly_path',None),metadata=getattr(context,'metadata_path',None))


def game_parameter_evidence(*,gameassembly,metadata,node_counts,bus_counts):
 audit=validate_names(gameassembly=gameassembly,metadata=metadata)
 result=dict(status=audit['status'],nativeGate={k:audit[k]for k in('status','detail','gateVerified','metadataSha256','gameAssemblySha256')if k in audit},source='il2cpp_data/Metadata/global-metadata.dat',metadataSha256=audit.get('metadataSha256'),evidence='exactStaticFieldValueCrossMatchedToSerializedHircRtpcId',entries=[],evidenceBoundary=BOUNDARY)
 if audit['status']=='validated':
  for f in audit['rtpcFields']:
   value=f['value'];nodes=int(node_counts.get(value,0));buses=int(bus_counts.get(value,0));result['entries'].append(dict(parameterId=value,parameterIdHex=f'0x{value:08x}',metadataField=CANONICAL_METADATA_PREFIX+f['name'],nodeRtpcCurveCount=nodes,busRtpcCurveCount=buses,serializedHircMatch=bool(nodes or buses)))
 return result
