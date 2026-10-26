"""Compare observed query fields with later gameplay consumers.

Callers authenticate the query records and field layouts. Equal copied values
are conditional candidates, never pointer identity or an inferred native copy.
UV bytes are retained as a separate comparison, not part of the physical hit
key used for point/normal/face/distance and collider identity.

Evidence and admission boundary
-------------------------------
Same-owner/thread floor-return candidates compare point, normal, face, distance
and collider identity bitwise; UV is independent. Unique matching returns and
uniquely joined accepted proxy-filter candidates supply sampled gameplay-use
evidence for collision-only cooked assets, independently of contact solving.
Repeated equal candidates and ambiguous proxies remain explicit. A stack-copy
value match is conditional and never establishes pointer identity or native copy.
"""
from collections import defaultdict


def physical_hit_key(hit, fields):
    raw = bytes.fromhex(hit['rawHex'])
    if hit['carrier'] != 'UnityEngine.RaycastHit' or len(raw) != 64:
        raise ValueError('consumption RaycastHit width/carrier')
    widths = {'m_Point': 12, 'm_Normal': 12, 'm_FaceID': 4, 'm_Distance': 4,
              'm_Collider': 4, 'm_Index': 4, 'm_EcsId': 4, 'm_EcsVersion': 4, 'm_Actor': 8}
    values = []
    for name, size in widths.items():
        offset = fields[name]
        if type(offset) is not int or not 0 <= offset <= len(raw)-size:
            raise ValueError('consumption field range:' + name)
        values.append(raw[offset:offset+size])
    return tuple(values)


def consumption_index(queries, fields):
    requests = {r['call']: r for r in queries['requests']}
    hits = {h['call']: h for h in queries['hits']}
    by_owner = defaultdict(list)
    by_conversion = defaultdict(list)
    for hit in hits.values():
        if hit['result']['carrier'] != 'UnityEngine.RaycastHit':
            continue
        request = requests[hit['parentCall']]
        key = physical_hit_key(hit['result'], fields)
        by_owner[(request['parentCall'], hit['thread'], key)].append(hit)
        if 'conversionCall' in hit:
            by_conversion[hit['conversionCall']].append(hit['call'])

    selected = defaultdict(list)
    for owner in queries['owners']:
        value = owner.get('floorHit') if owner['kind'] == 'floor_query' else owner.get('outputHit')
        if value is None:
            continue
        # A false floor flag leaves the carrier uninterpreted.
        if owner['kind'] == 'floor_query' and not owner['floor']['isHit']:
            continue
        candidates = [h for h in by_owner.get((owner['call'], owner['thread'], physical_hit_key(value, fields)), [])
                      if owner['entryQpc'] <= h['entryQpc'] <= h['returnQpc'] <= owner['returnQpc']]
        evidence = dict(ownerCall=owner['call'], kind=owner['kind'], matchingHitCalls=[h['call'] for h in candidates],
                        status='unique_physical_hit_fields' if len(candidates) == 1 else 'ambiguous_or_unobserved_physical_hit',
                        boundary='conditional: same original owner/thread and bitwise physical result fields; copied pointer provenance and UV are separate')
        if 'floor' in owner:
            evidence['floor'] = owner['floor']
        if 'returnValue' in owner:
            evidence['returnValue'] = owner['returnValue']
        for hit in candidates:
            comparison = dict(evidence, uvBytesEqual=(value['rawHex'] == hit['result']['rawHex']))
            selected[hit['call']].append(comparison)

    filters = defaultdict(list)
    for decision in queries['decisions']:
        for hit_call in decision['matchingQueryHitCalls']:
            filters[hit_call].append(dict(filterCall=decision['call'], ownerCall=decision['parentCall'],
                                         accepted=decision['returnedValidForCollisions'], joinStatus=decision['joinStatus'],
                                         matchingHitCalls=decision['matchingQueryHitCalls'],
                                         boundary='observed filter return on matching collider proxy; ambiguous candidates do not select a particular hit'))
    return {conversion: dict(hitCalls=hit_calls,
                             selectedOwnerReturns=[dict(queryHitCall=call, **row) for call in hit_calls for row in selected[call]],
                             filterDecisions=[dict(queryHitCall=call, **row) for call in hit_calls for row in filters[call]])
            for conversion, hit_calls in by_conversion.items()}
