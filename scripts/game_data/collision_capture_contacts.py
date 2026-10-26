"""Validate pre-cleanup contact records and their retained source provenance.

Raw report data remains available even if a peer has no Unity asset identity.
Zero callback reports never establish absence of physical contact.
"""
from __future__ import annotations
import struct


def decode_contacts(calls, observations, profile, receipt):
    from scripts.game_data.collision_capture_inspect import _require, _bytes, _u64, _origin, _mesh_join
    rows={r['call']:r for r in observations}
    layout=profile['contactAttachment']['layout'];base=_u64(receipt['playerBase'])
    h=profile['contactCapture']['header'];p=profile['contactCapture']['pair']
    headers=[];pairs=[];selected=0;header_physics={}
    for call,entry in calls.items():
        kind=entry['kind']
        if kind not in (14,15):continue
        row=entry['returnRecord']
        args=list(map(_u64,row['args']));after=_bytes(row['after'],128,'contact header/proof')
        raw_header=after[:48]
        actors=[struct.unpack_from('<Q',raw_header,at)[0] for at in h['actors']]
        header_flags=struct.unpack_from('<H',raw_header,h['flags'])[0]
        pair_pointer=struct.unpack_from('<Q',raw_header,h['pairs'])[0]
        pair_count=struct.unpack_from('<I',raw_header,h['count'])[0]
        if kind==14:
            physics_parent=entry['parent']
            if profile.get('schema') in tuple('endfieldCapture.collisionBuild.v'+str(v) for v in range(7,18)) and calls.get(physics_parent,{}).get('kind') in (28,29):
                physics_parent=calls[physics_parent]['parent']
            _require(physics_parent in calls and calls[physics_parent]['kind']==11 and row['queryState']==1,
                     f'contact header lacks native simulation parent: call={call}, parent={entry["parent"]}, resolved={physics_parent}')
            _require(args[0]>0 and args[1]>0 and args[4]<=0xffffffff and args[5]-base in profile['contactCapture']['returnRvas'],'contact finalizer caller/ABI differs')
            original_return=struct.unpack_from('<Q',after,48)[0]
            _require(entry['qpc']<=original_return<=row['qpc'],'contact finalizer return timing')
            _require(pair_count==0 or pair_pointer>0,'contact header lacks pair storage')
            headers.append(dict(call=call,physicsCall=physics_parent,scScenePointer=f'{args[0]:016x}',actors=[f'{v:016x}' for v in actors],
                flags=header_flags,pairCount=pair_count,rawHeaderHex=raw_header.hex(),originalReturnQpc=original_return,
                route='direct_dispatch' if args[5]-base==profile['contactCapture']['returnRvas'][0] else 'split_headers'))
            header_physics[call]=physics_parent
            continue
        parent=calls.get(entry['parent'],{})
        _require(parent.get('kind')==14,'contact pair lacks finalized header parent')
        parent_after=_bytes(parent['returnRecord']['after'],128,'parent contact header')
        _require(raw_header==parent_after[:48] and args[1]==_u64(parent['args'][1]) and args[3]==pair_count and
                 args[2]<min(pair_count,profile['contactCapture']['maxPairsPerHeader']) and args[0]==pair_pointer+args[2]*64 and
                 entry['qpc']>=struct.unpack_from('<Q',parent_after,48)[0],'contact pair/header framing or return ordering differs')
        raw=_bytes(row['before'],64,'raw contact pair')
        shapes=[struct.unpack_from('<Q',raw,at)[0] for at in p['shapes']]
        flags=struct.unpack_from('<H',raw,p['flags'])[0];events=struct.unpack_from('<H',raw,p['events'])[0]
        removed=(header_flags|flags)&3
        _require(entry['parent'] in header_physics,'contact pair lacks decoded simulation ancestry')
        physics_call=header_physics[entry['parent']]
        observed=dict(call=call,headerCall=entry['parent'],physicsCall=physics_call,pairIndex=args[2],
            actors=[f'{v:016x}' for v in actors],shapes=[f'{v:016x}' for v in shapes],removedMask=removed,
            flags=flags,eventsRaw=events,contactCountRaw=raw[p['contactCount']],patchCountRaw=raw[p['patchCount']],streamSizeRaw=struct.unpack_from('<H',raw,p['streamSize'])[0],
            rawPairHex=raw.hex(),provenance=dict(status='peer_asset_identity_unresolved'))
        if args[4] != (1<<64)-1:
            side=args[4];origin=rows.get(args[5],{})
            _require(side in (0,1) and not removed&(1<<side) and row['queryState']==1 and args[6]>0,'contact selected side/removal state')
            _require(origin.get('kind')=='child_collider' and args[5]==origin['retainedOriginCall'] and args[7]==origin['enrollmentQpc'] and
                row['model']==calls[args[5]]['model'] and row['objectId']==origin['objectInstanceId'] and
                row['goId']==origin['gameObjectInstanceId'] and row['go']==origin['gameObjectPointer'] and
                row['transform']==origin['transformPointer'] and args[7]<calls[physics_call]['qpc'],'contact retained object/source identity differs')
            native=_u64(calls[args[5]]['returnRecord']['colliderMemory']['root'])
            _require(args[6]==native,'contact native Collider differs from enrollment')
            collider_table,shape,shape_table,actor,binding_qpc=struct.unpack_from('<5Q',after,56)
            _require(collider_table==base+layout['collider']['vtableRva'] and shape_table==base+layout['shape']['vtableRva'] and
                shape==shapes[side] and actor==actors[side] and shape>0 and actor>0 and
                struct.unpack_from('<Q',parent_after,48)[0]<=binding_qpc<=entry['qpc'],'contact native attachment proof differs')
            collider_origin=_origin(row['colliderOrigin']);mesh_origin=_origin(row['meshOrigin'],required=bool(_u64(row['mesh'])))
            observed['provenance']=dict(status='observed_current_attachment',selectedSide=side,originChildCall=args[5],
                nativeCollider=f'{native:016x}',managedCollider=origin['colliderPointer'],meshPointer=row['mesh'],meshInstanceId=row['meshId'],
                colliderOrigin=collider_origin,meshOrigin=mesh_origin,meshSourceJoin=_mesh_join(mesh_origin,profile),bindingQpc=binding_qpc,
                boundary='conditional: rooted Collider/root identity checked before native reads; current Collider shape and typed PxShape actor match this report side; separately timed reads')
            selected+=1
        else:
            _require(args[5:]==[0,0,0] and row['queryState']==0 and not any(after[56:96]),'unbound contact carries selected provenance')
        pairs.append(observed)
    counters=receipt['contacts']
    _require(all(type(counters.get(k)) is int and counters[k]>=0 for k in ('headers','pairs','selected','limited','removed','unselectedSkipped')),'contact receipt scalar')
    _require(counters['headers']==len(headers) and counters['pairs']==len(pairs)<=profile['contactCapture']['maxPairSamples'] and
             counters['selected']==selected and len(pairs)-selected<=profile['contactCapture']['maxUnselectedSamples'] and receipt['entered'][11]>=len(headers),'contact producer/observer accounting')
    source_matches=sum(r['provenance'].get('meshSourceJoin',{}).get('status')=='matched_frozen_source' for r in pairs)
    return dict(headers=headers,pairs=pairs,selectedBindings=selected,matchedFrozenSources=source_matches,limits=counters['limited'],removed=counters['removed'],unselectedSkipped=counters['unselectedSkipped'],
        boundary=profile['contactCapture']['evidenceBoundary'],
        gaps=['Missing reports do not prove absence of physical contact; notification filtering and other simulation routes remain outside this observer.']+
             ['Some report pairs were skipped at explicit capture bounds.']*bool(counters['limited'])+
             ['No report pair matched a retained selected collider.']*bool(not selected))
