"""Complete current Interactive values, with the raw-format reader's exit gate."""
from pathlib import Path

from scripts.webui.data_inspector.contract import source_descriptor


def interactive_record(path,export_root,*,interactive_decoder):
    path=Path(path);export_root=Path(export_root);raw=path.read_bytes()
    decoded=interactive_decoder(path,raw);fields=decoded.get('fields',{})
    if(decoded.get('schemaStatus')!='named_exact'or decoded.get('wholeSchemaExact')is not True
            or decoded.get('physicalEOF')is not True or decoded.get('serializedMemberCount')!=26
            or decoded.get('bytesConsumed')!=len(raw)or not isinstance(fields,dict)or len(fields)!=26):
        raise ValueError('Interactive complete publication refused: '+str(path))
    types=set()
    def collect(value):
        if isinstance(value,dict):
            if isinstance(value.get('$type'),str):types.add(value['$type'])
            for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(fields)
    return dict(id=path.relative_to(export_root).as_posix(),title=fields['id'],status='named_exact',
        source=source_descriptor(path,export_root=export_root,media_type='application/octet-stream'),
        tags=['interactive','memorypack','current-native','named_exact'],
        summary='26 named root fields; complete stored components and ActionMap; physical EOF',
        searchTerms=[*fields,*sorted(types),fields['id']],
        facts=dict(decoded['facts'],serializedMemberCount=26,closedFieldCount=26,
            decodedFieldNames=list(fields),componentTypes=sorted(types),currentNativeRoot=True),
        payloadKind='reader',payload=decoded,
        evidenceBoundary='Exact current stored values and source-owned native children under explicit callback conditions; source id and physical EOF; no runtime component or action execution claim.')
