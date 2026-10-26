"""Decode admitted query buffers, filter decisions and pre-cleanup guards.

The frozen profile authenticates the layouts. A native result additionally
needs its exact original caller and live cached binding; unbound calls remain
diagnostics. Missing/sampled-out results never establish collision absence.
"""
from __future__ import annotations
from collections import defaultdict
import struct

EVENT_ROLES = ("query_capsule_results", "query_sphere_results", "query_ray_results", "query_overlap_results",
               "query_ray_single", "query_sphere_single", "query_hit", "collider_filter", "movement_query",
               "floor_query", "movement_overlap", "penetration_query", "report_dispatch", "report_build",
               "query_hit_conversion", "report_stream", "proxy_layer", "collider_options", "hit_proxy", "cast_buffer", "overlap_buffer")


def decode_queries(calls, profile, receipt):
    from scripts.game_data.collision_capture_inspect import _require, _bytes, _u64, _floats, _origin, _mesh_join
    c = profile["queryCapture"]["contract"]
    limits = c["limits"]
    base, player = _u64(receipt["gameBase"]), _u64(receipt["playerBase"])
    _require(base > 0 and player > 0, "query module bases")
    types = {t["type"]: t for t in c["types"]}
    fields = {name: {f["name"]: f["offset"] for f in t["fields"]} for name, t in types.items()}
    def raw(entry):
        row = entry["returnRecord"]
        return row, list(map(_u64, row["args"])), _bytes(row["before"], 64, "query input"), _bytes(row["after"], 128, "query result"), _bytes(row["queryHex"], 192, "query payload")
    def signed(value):
        _require(0 <= value <= 0xffffffff, "query integer result width")
        return value if value < 0x80000000 else value-0x100000000
    def carrier(data, proxy=False):
        name = "UnityEngine.ECSColliderResultProxy" if proxy else "UnityEngine.RaycastHit"
        fs = fields[name]
        def val(field, fmt):
            at = fs[field]
            _require(0 <= at <= len(data)-struct.calcsize(fmt), "query field bound:"+field)
            return struct.unpack_from("<"+fmt, data, at)[0]
        out = dict(carrier=name, actorPointer=f"{val('m_Actor','Q'):016x}", colliderInstanceId=val("m_Collider", "i"),
                   ecsId=val("m_EcsId", "i"), ecsVersion=val("m_EcsVersion", "I"),
                   componentIndex=val("m_ComponentIndex" if proxy else "m_Index", "i"), rawHex=data.hex())
        if not proxy:
            out.update(point=_floats(data[fs['m_Point']:fs['m_Point']+12]), normal=_floats(data[fs['m_Normal']:fs['m_Normal']+12]),
                       faceId=val("m_FaceID", "I"), distance=_floats(data[fs['m_Distance']:fs['m_Distance']+4])[0])
        return out
    def proxy_key(hit):
        return (hit['actorPointer'], hit['colliderInstanceId'], hit['ecsId'], hit['ecsVersion'], hit['componentIndex'])
    requests, hits, decisions, owners, guards, streams, conversions, reads, proxies, buffers = [], [], [], [], [], [], [], [], [], []
    bound_requests = set()
    for call, entry in calls.items():
        kind = entry['kind']
        if not 16 <= kind <= 36:
            continue
        row, args, before, after, data = raw(entry)
        result = _u64(row['result'])
        observation = dict(call=call, parentCall=entry['parent'], thread=entry['thread'], kind=EVENT_ROLES[kind-16],
                           entryQpc=entry['qpc'], returnQpc=row['qpc'], flags=row['flags'])
        _require(row['queryState'] in (0, 1, 2, 4) and not row['flags'] & 32, 'query read state/failure')
        if 16 <= kind <= 21:
            b = c['bindings'][kind-16]
            caller_matched = args[2] == base+b['returnRva']
            bound = args[3] == player+b['functionRva'] and (caller_matched or profile.get('queryCallerPolicy')=='reviewed-native-callee-and-live-cache')
            _require((row['queryState'] != 2) == bound, 'query caller/cache binding state differs')
            observation.update(binding=('matched_caller_and_live_cache' if caller_matched else 'reviewed_native_callee_and_live_cache') if bound else 'unbound_caller_or_cache',
                               callerPointer=f'{args[2]:016x}', cachePointer=f'{args[3]:016x}', requestedApi=b['name'],
                               returnValue=signed(result) if kind < 20 else bool(result))
            if kind >= 20:
                _require(result in (0, 1), 'single query Boolean result')
            if bound:
                completion, completion_parent, native_scene, completion_qpc, active_core = struct.unpack_from('<QQQQQ', data, 128)
                observation['completedStepReference'] = dict(completionCall=completion, physicsCall=completion_parent, nativeScene=f'{native_scene:016x}', qpc=completion_qpc, activePhysicsCall=active_core)
                if completion:
                    completed = calls.get(completion, {})
                    _require(completed.get('kind') == 12 and completed['parent'] == completion_parent and completed['thread'] == entry['thread'] and
                             _u64(completed['args'][0]) == native_scene and completed['qpc'] <= completion_qpc <= completed['returnRecord']['qpc'] and
                             completion_qpc <= entry['qpc'], 'query completed-step reference differs')
                if active_core:
                    _require(calls.get(active_core,{}).get('kind') == 11 and calls[active_core]['thread'] == entry['thread'], 'query active physics reference')
                observation.update(sceneHandle=struct.unpack_from('<i', data)[0], layerMask=signed(args[6]),
                                   triggerInteraction=signed(args[7]), radius=_floats(struct.pack('<I', args[4]))[0],
                                   distance=_floats(struct.pack('<I', args[5]))[0], argumentVectors=_floats(before[:36 if kind == 16 else 24]))
                count = signed(result)
                length = struct.unpack_from('<I', after)[0]
                if row['queryState'] == 4:
                    observation['resultStatus'] = 'rejected_return_count_or_pointer'
                else:
                    _require(count >= 0 and count <= length <= c['arrayLayout']['maxLength'], 'query count exceeds actual buffer')
                    observation.update(resultStatus='bounded_result', resultCount=count, arrayLength=length)
                    bound_requests.add(call)
            requests.append(observation)
        elif kind == 22:
            parent = calls.get(entry['parent'], {})
            _require(parent.get('kind') in range(16, 22) and entry['parent'] in bound_requests, 'query hit lacks admitted bound request')
            _, parent_args, _, parent_after, _ = raw(parent)
            parent_result = _u64(parent['returnRecord']['result'])
            stride = 24 if parent['kind'] == 19 else 64
            offset = (0 if parent['kind'] >= 20 else c['arrayLayout']['data'])+args[1]*stride
            _require(args[3] == stride and args[4] == parent['kind'] and args[2] == parent_result and
                     args[1] < min(parent_result, limits['maxPerQuery']) and args[0] == parent_args[1]+offset, 'query hit pointer/count/stride differs')
            observation.update(index=args[1], result=carrier(after[:stride], stride == 24))
            _require(not any(h['parentCall'] == entry['parent'] and h['index'] == args[1] for h in hits), 'duplicate query result ordinal')
            hits.append(observation)
        elif kind == 23:
            _require(result in (0, 1), 'filter Boolean result')
            observation.update(movementPointer=f'{args[0]:016x}', proxy=carrier(before[:24], True), proxyAfter=carrier(after[:24], True), returnedValidForCollisions=bool(result),
                               ignoreInterEnemy=bool(args[2]), baseMask=struct.unpack_from('<i', data, 164)[0], ignoredMask=struct.unpack_from('<i', data, 168)[0])
            decisions.append(observation)
        elif kind in (24, 25, 26):
            observation.update(movementPointer=f'{args[0]:016x}', inputPositionOrDisplacement=_floats(before[:12]),
                               logicPositionBefore=_floats(data[152:164]), baseMask=struct.unpack_from('<i', data, 164)[0], ignoredMask=struct.unpack_from('<i', data, 168)[0])
            if kind == 24:
                _require(result in (0, 1), 'movement Boolean result')
                observation.update(returnValue=bool(result), logicPositionAfter=_floats(data[176:188]), outputHit=carrier(after[:64]))
            elif kind == 25:
                fs = fields['Beyond.Gameplay.Core.MovementComponent+FindFloorResult']
                flags = {key: data[fs[key]] for key in ('isHit', 'walkableFloor', 'walkableFloorByLineTrace', 'climbable', 'lineTrace')}
                _require(all(v in (0, 1) for v in flags.values()), 'floor Boolean fields')
                observation.update(floor={k: bool(v) for k, v in flags.items()}, floorHit=carrier(data[fs['floorHit']:fs['floorHit']+64]), rawFloorHex=data[:152].hex())
            else:
                observation['returnValue'] = signed(result)
            owners.append(observation)
        elif kind == 27:
            _require(result in (0, 1), 'penetration Boolean result')
            observation.update(proxy=carrier(data[:24], True), returnValue=bool(result), argumentVectors=_floats(before[:24]),
                               direction=_floats(after[:12]) if result else None, distance=_floats(after[12:16])[0] if result else None)
            requests.append(observation)
        elif kind in (28, 29):
            callback, core, pair_pointer, count = struct.unpack_from('<QQQI', data)
            sampled = struct.unpack_from('<Q', data, 32)[0]
            _require(entry['qpc'] <= sampled <= row['qpc'], 'report guard pre-original sample timing')
            observation.update(scScenePointer=f'{args[0]:016x}', callbackConsumer=f'{callback:016x}', rawReportCore=f'{core:016x}',
                               pairPointer=f'{pair_pointer:016x}', pairCount=count, sampleQpc=sampled,
                               bypass='no_callback' if kind == 28 and not callback else 'missing_report_core' if not core else 'empty_reports' if not count else 'inspect_streams',
                               boundary='guard fields copied before original dispatch/build; separately timed reads')
            guards.append(observation)
        elif kind == 30:
            parent = calls.get(entry['parent'], {})
            _require(parent.get('kind') in range(16, 22) and entry['parent'] in bound_requests, 'conversion lacks bound native query')
            actor, shape = struct.unpack_from('<QQ', before)
            observation.update(nativeActor=f'{actor:016x}', nativeShape=f'{shape:016x}', result=carrier(after[:64]), sourceBinding='unbound')
            proof = struct.unpack_from('<QQQQQ', data)
            origin = struct.unpack_from('<Q', data, 40)[0]
            if any(proof):
                layout = profile['contactAttachment']['layout']
                _require(proof[:4] == (player+layout['collider']['vtableRva'], shape, player+layout['shape']['vtableRva'], actor) and
                         entry['qpc'] <= proof[4] <= row['qpc'], 'conversion typed Collider/shape/actor proof')
                child = calls.get(origin, {})
                _require(child.get('kind') == 10 and child['thread'] == entry['thread'], 'conversion retained origin')
                baseline = child['returnRecord']
                _require(all(row[k] == baseline[k] for k in ('objectId', 'goId', 'go', 'transform', 'model')), 'conversion retained identity differs')
                observation['reportedColliderMatchesRetained'] = row['objectId'] == observation['result']['colliderInstanceId']
                observation.update(sourceBinding='typed_native_shape_to_retained_collider', originChildCall=origin,
                                   retainedCompletedStepsAtRead=struct.unpack_from('<Q',data,48)[0], nativeCollider=f'{struct.unpack_from("<Q",data,56)[0]:016x}',
                                   colliderOrigin=_origin(row['colliderOrigin']), meshOrigin=_origin(row['meshOrigin'], required=_u64(row['mesh']) != 0))
                observation['meshSourceJoin'] = _mesh_join(observation['meshOrigin'], profile)
            conversions.append(observation)
        elif kind == 31:
            _require(calls.get(entry['parent'], {}).get('kind') in (28, 29), 'stream diagnostic lacks guard parent')
            actor_pair, pointer = struct.unpack_from('<QQ', after)
            state = after[16]
            observation.update(index=args[1], actorPair=f'{actor_pair:016x}', streamPointer=f'{pointer:016x}', streamState=state,
                               bypass='missing_actor_pair' if not actor_pair else 'null_stream' if not pointer else 'excluded_stream' if state & c['reportLayout']['invalidStreamMask'] else 'eligible_stream')
            streams.append(observation)
        elif kind in (32, 33):
            _require(calls.get(entry['parent'], {}).get('kind') == 23, 'filter read lacks filter parent')
            observation.update(proxy=carrier(before[:24], True), proxyAfter=carrier(after[:24], True), returnValue=signed(result))
            reads.append(observation)
        elif kind == 34:
            _require(result == args[0], 'proxy hidden return carrier differs')
            observation.update(hitPointer=f'{args[1]:016x}', outputPointer=f'{args[0]:016x}', hit=carrier(before), proxy=carrier(after[:24],True))
            proxies.append(observation)
        elif kind in (35,36):
            length=struct.unpack_from('<I',after)[0]
            _require((result == 0 and row['queryState']==2) or (result > 0 and row['queryState']==1 and length<=c['arrayLayout']['maxLength']), 'result getter pointer/count')
            observation.update(bufferPointer=f'{result:016x}', arrayLength=length)
            buffers.append(observation)
    # Physical source joins require the converter's actual native shape, never
    # an actor-only or instance-ID-only guess. Filter joins compare full proxies
    # within the same sampled movement invocation and temporal order.
    conversions_by_hit=defaultdict(list)
    hits_by_proxy=defaultdict(list)
    hits_by_source=defaultdict(list)
    reads_by_filter=defaultdict(list)
    proxies_by_output=defaultdict(list)
    buffers_by_owner=defaultdict(list)
    hits_by_call={h['call']:h for h in hits}
    for v in conversions:
        raw=v['result']['rawHex']
        conversions_by_hit[(v['parentCall'],raw[:64],raw[80:])].append(v)
    for h in hits:
        owner=calls[h['parentCall']]['parent']
        hits_by_proxy[(owner,h['thread'],proxy_key(h['result']))].append(h)
        hits_by_source[(owner,h['result']['rawHex'],_u64(calls[h['call']]['args'][0]))].append(h)
    for v in reads:reads_by_filter[v['parentCall']].append(v)
    for p in proxies:proxies_by_output[(p['parentCall'],p['outputPointer'],p['proxy']['rawHex'])].append(p)
    for b in buffers:buffers_by_owner[b['parentCall']].append(b)
    for hit in hits:
        raw=hit['result']['rawHex']
        candidates=conversions_by_hit.get((hit['parentCall'],raw[:64],raw[80:]),[]) if hit['result']['carrier']=='UnityEngine.RaycastHit' else []
        if len(candidates) == 1:
            hit['conversionCall'] = candidates[0]['call']
            hit['sourceBinding'] = candidates[0]['sourceBinding']
            if 'meshSourceJoin' in candidates[0]:
                hit['meshSourceJoin'] = candidates[0]['meshSourceJoin']
        else:
            hit['sourceBinding'] = 'unresolved_native_shape_join'
    for decision in decisions:
        candidates = [h for h in hits_by_proxy.get((decision['parentCall'],decision['thread'],proxy_key(decision['proxy'])),[]) if h['returnQpc'] <= decision['entryQpc']]
        decision['matchingQueryHitCalls'] = [h['call'] for h in candidates]
        decision['joinStatus'] = 'unique_same_owner_returned_proxy' if len(candidates) == 1 else 'ambiguous_or_unobserved_query'
        decision['reads'] = reads_by_filter.get(decision['call'],[])
        filter_entry=calls[decision['call']]
        matches=[p for p in proxies_by_output.get((decision['parentCall'],f'{_u64(filter_entry["args"][1]):016x}',decision['proxy']['rawHex']),[]) if p['returnQpc']<=decision['entryQpc']]
        decision['proxyProducerCalls']=[p['call'] for p in matches]
        for p in matches:
            p['matchingReturnedHitCalls']=[h['call'] for h in hits_by_source.get((p['parentCall'],p['hit']['rawHex'],int(p['hitPointer'],16)),[]) if h['returnQpc']<=p['entryQpc']]
            pointers={_u64(calls[hits_by_call[call]['parentCall']]['args'][1]) for call in p['matchingReturnedHitCalls']}
            p['matchingBufferGetterCalls']=[b['call'] for b in buffers_by_owner.get(p['parentCall'],[]) if b['returnQpc']<=p['entryQpc'] and int(b['bufferPointer'],16) in pointers]
    counters = receipt['queries']
    expected = dict(requests=len(requests), results=len(hits), unbound=sum(r.get('binding') == 'unbound_caller_or_cache' for r in requests),
                    conversions=len(conversions), selected=sum(v['sourceBinding'] != 'unbound' for v in conversions),
                    decisions=len(decisions), accepted=sum(d['returnedValidForCollisions'] for d in decisions),
                    rejected=sum(not d['returnedValidForCollisions'] for d in decisions), owners=len(owners), guards=len(guards), streams=len(streams), filterReads=len(reads), proxyConversions=len(proxies), bufferReads=len(buffers))
    _require(all(type(counters.get(k)) is int and counters[k] == v for k, v in expected.items()), 'query/filter/guard producer accounting')
    _require(type(counters.get('limited')) is int and counters['limited'] >= 0, 'query limit counter')
    for h in c['hooks']:
        _require(receipt['entered'][12+list(c['hooks']).index(h)] >= sum(e['kind'] == h['kind'] for e in calls.values()), 'query hook entry census')
    _require(len(requests)<=limits['maxRequests'] and len(hits)<=limits['maxResults'] and len(conversions)<=limits['maxResults'] and
             len(proxies)<=limits['maxResults'] and len(buffers)<=limits['maxResults'] and len(decisions)<=limits['maxDecisions'] and
             len(owners)<=limits['maxOwners'] and len(guards)<=limits['maxGuards'] and len(streams)<=limits['maxStreams'] and len(reads)<=limits['maxFilterReads'], 'query sample budget')
    return dict(requests=requests, hits=hits, decisions=decisions, owners=owners, conversions=conversions, guards=guards, streams=streams, reads=reads, proxies=proxies, buffers=buffers,
                counters=counters, boundary=c['evidenceBoundary'], gaps=['Sampling, unsupported call sites and absent notifications never prove collision absence.']+
                ['Some queries, hits, filter reads or guards reached explicit bounds.']*bool(counters['limited'])+
                ['Some native query entries lacked a reviewed original caller/cache binding.']*bool(counters['unbound']))
