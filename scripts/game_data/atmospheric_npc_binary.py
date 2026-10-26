"""Current sequential pooled Atmospheric NPC dictionary; no marker scans."""
from scripts.game_data.codecs.leveldata.npc_runtime import LevelNpcCodecError
from scripts.game_data.memorypack.npc_runtime import npc_runtime_decoder,require_selected_decoder
from scripts.game_data.string_pool import StringPool


def _frame(data,decode):
    result=dict(schemaStatus='partial',bytes=len(data),bytesConsumed=0,entries=[],entryCount=None,evidenceBoundary='Conditional current native NPC source; stored authored values, not observed runtime spawning.')
    rows=[]
    try:
        if not data or data[0]!=1:raise LevelNpcCodecError('AtmosphericNpcData.memberCount',0,1,None if not data else data[0])
        table,cursor=decode.dictionary(data,1,key_wire='pool');rows=table['entries']or[];result['entryCount']=table['count']
        if cursor!=len(data):raise LevelNpcCodecError('AtmosphericNpcData.eof',cursor,len(data),cursor)
        result.update(schemaStatus='named_exact',bytesConsumed=cursor,rootMemberCount=1,namedNpcRuntimeProxyCount=len(rows),namedLevelEntityPrefixCount=len(rows))
    except LevelNpcCodecError as error:
        rows=getattr(error,'partial_entries',rows);result.update(bytesConsumed=error.diagnostic.get('offset')or 0,entryCount=getattr(error,'entry_count',result['entryCount']),diagnostic=error.diagnostic)
    for entry in rows:
        value=entry['value'];result['entries'].append(dict(key=entry['key'],keyOffset=entry['keyOffset'],payloadOffset=entry['valueOffset'],payloadLength=value['endOffset']-value['startOffset'],payloadMemberCount=value['memberCount'],proxyBodyStatus='named_exact_npc_runtime_proxy',levelEntityData=value['levelEntityData'],npcRuntimeProxyData=value))
    return result


def frame_atmospheric_npc_table(data,*,strings,game_root=None,gameassembly=None,metadata=None,npc_decoder=None):
    """A partial result stops at its first named unproved field; EOF stays separate."""
    if not isinstance(strings,StringPool):raise LevelNpcCodecError('matching-StringPool-required',None,'StringPool',type(strings).__name__)
    if npc_decoder is None:
        with npc_runtime_decoder(strings=strings,game_root=game_root,gameassembly=gameassembly,metadata=metadata)as decode:return _frame(data,decode)
    require_selected_decoder(npc_decoder,strings=strings,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
    return _frame(data,npc_decoder)
