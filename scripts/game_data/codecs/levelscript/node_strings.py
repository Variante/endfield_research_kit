"""Decode node string fields through their owning route and proved source helper."""
from __future__ import annotations
import json
import struct
from functools import lru_cache
from pathlib import Path

from scripts.common import resolve_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.string_pool import resolve_string_pool_index
from scripts.game_data.levelscript_node_strings_native import CONTRACT as SOURCE_CONTRACT, SCHEMA as SOURCE_SCHEMA


@lru_cache(maxsize=128)
def _profiles(raw, schema):
    fact=json.loads(raw)
    status='validated' if schema==SOURCE_SCHEMA else 'exact-current-build'
    if not isinstance(fact,dict) or (fact.get('schema'),fact.get('status'))!=(schema,status):
        raise ValueError('nodeString.source:contract-identity')
    pins=fact.get('nativeInputs',{})
    typed=schema=='endfield.levelscript-route-deserialize-native.v2'
    if typed:
        if (not isinstance(pins,dict) or set(pins)!={'gameAssembly','metadata'}
                or any(not isinstance(v,dict) or set(v)!={'sha256'} for v in pins.values())):
            raise ValueError('nodeString.source:native-pin-scope')
        pins={name:pins[key]['sha256'] for name,key in (('GameAssembly.dll','gameAssembly'),('global-metadata.dat','metadata'))}
    if (not isinstance(pins,dict) or not {'GameAssembly.dll','global-metadata.dat'} <= pins.keys()
            or not pins.keys() <= {'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
            or any(not isinstance(v,str) for v in pins.values())):raise ValueError('nodeString.source:native-pin-scope')
    profiles=[]
    if schema==SOURCE_SCHEMA:
        if set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:
            raise ValueError('nodeString.source:native-pin-scope')
        for record in fact.get('records',[]):
            prefix=record.get('prefixReads',[])
            if (not record.get('codeWindows') or not record.get('stringSources') or not record.get('primitiveWindows')
                    or [(r.get('field'),r.get('kind')) for r in prefix] != [('dontLogWarning','bool'),('ID','int32'),('releaseWhenExecutionFinished','bool'),('uid','string')]):
                raise ValueError('nodeString.source:incomplete-field-source')
            for row in record['stringSources']:
                source=row['source'];field=row['field']
                if ([field,'string'] not in record['fields'] or [field,source['field']] not in record['stringFields']
                        or not source.get('readerArgument') or not source.get('wrapperArgument')
                        or not source.get('setter') or not source.get('setterWindows')
                        or field!='uid' or source.get('callRva')!=prefix[3].get('callRva')):
                    raise ValueError('nodeString.source:unproved-field-transfer')
                profiles.append((record['wrapperName'],tuple(map(tuple,record['fields'])),source['targetRva'],
                                 tuple(sorted(pins.items())),(field,)))
        return tuple(profiles)
    def walk(value, helpers=None):
        if isinstance(value,dict):
            helpers=value.get('readerHelpers',helpers)
            fields=value.get('fields',[])
            if typed and value.get('wrapperName') and isinstance(fields,list):
                reads=value.get('readOrder',[])
                if ([r.get('name') for r in reads]!=[f[0] for f in fields]
                        or any(r.get('declaredType')!='string' for r,f in zip(reads,fields) if f[1]=='string')):
                    raise ValueError('nodeString.source:typed-field-plan')
                targets={r.get('readTargetRva') for r,f in zip(reads,fields) if f[1]=='string'}
                if len(targets)!=1:raise ValueError('nodeString.source:typed-string-helper-count')
                helpers={'string':targets.pop()}
            if value.get('wrapperName') and isinstance(fields,list) and any(isinstance(f,list) and len(f)==2 and f[1]=='string' for f in fields) and isinstance(helpers,dict):
                target=helpers.get('string')
                if type(target) is int and 0<target<1<<32:profiles.append((value['wrapperName'],tuple(map(tuple,fields)),target,tuple(sorted(pins.items())),tuple(f[0] for f in fields if f[1]=='string')))
            for child in value.values():walk(child,helpers)
        elif isinstance(value,list):
            for child in value:walk(child,helpers)
    walk(fact)
    return tuple(profiles)


def decode_node_string(data, offset, layout, contracts, *, field, game_root=None, strings=None):
    """The caller first validates the route's native gate and exact field list."""
    if [field,'string'] not in layout['fields']:raise ValueError(f'nodeString.source:unproved-string-field={field}')
    matches=[]
    for filename,schema,gate in contracts:
        if gate!=layout.get('nativeGate'):continue
        path=CONTRACTS_DIR/filename
        for wrapper,fields,target,pins,proved_fields in _profiles(path.read_bytes(),schema):
            if wrapper==layout['wrapperName'] and fields==tuple(map(tuple,layout['fields'])) and field in proved_fields:matches.append((target,pins))
    if not matches:
        for wrapper,fields,target,pins,proved_fields in _profiles(SOURCE_CONTRACT.read_bytes(),SOURCE_SCHEMA):
            if wrapper==layout['wrapperName'] and fields==tuple(map(tuple,layout['fields'])) and field in proved_fields:
                matches.append((target,pins))
    if len(matches)!=1:raise ValueError(f"nodeString.source:unproved-or-ambiguous-wrapper={layout['wrapperName']},matches={len(matches)}")
    root=Path(game_root) if game_root is not None else None
    ga,md=(root.parent/'GameAssembly.dll',root/'il2cpp_data/Metadata/global-metadata.dat') if root else resolve_installed_native_inputs()
    audit=pooled_source_helper.validate_current_native_contract(gameassembly=ga,metadata=md)
    target,pins=matches[0]
    if (audit.get('status')!='validated' or audit.get('wireEncoding')!='int32-pool-index'
            or target not in audit.get('sourceHelpers',[]) or any(audit.get('nativeInputs',{}).get(k,'').upper()!=v.upper() for k,v in pins)):
        raise ValueError(f"nodeString.source:expected=proved-current-pooled-helper,actual={audit.get('status')},detail={str(audit.get('detail',''))[:300]}")
    if type(offset) is not int or not 0<=offset<=len(data)-4:raise ValueError(f'nodeString.source:truncated-index,offset={offset}')
    index=struct.unpack_from('<i',data,offset)[0]
    return resolve_string_pool_index(index,strings,field),offset+4
