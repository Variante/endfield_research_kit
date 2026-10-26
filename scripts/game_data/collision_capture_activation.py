"""Decode original activation stages without inferring a physical outcome."""
import struct


def frame(raw, kind, args, limits, *, item_count_validated=True):
    owner,mono,settings,items,handle,colliders,count,timer,manager,state,flags = struct.unpack('<5Q4i2I',raw[:64])
    if owner != args[0] or state & ~2047:
        raise ValueError('collision-activation:owner/read mask')
    for bit,parent in ((2,1),(4,2),(8,4),(16,1),(32,1),(128,64),(1024,64)):
        if state & bit and not state & parent:
            raise ValueError('collision-activation:field read dependency')
    if kind in (94,96,97) and mono != owner:
        raise ValueError('collision-activation:original Mono receiver')
    if kind == 98 and handle != args[1]:
        raise ValueError('collision-activation:original submit handle')
    if item_count_validated and state & 8 and not 0 <= count <= limits['maxItems']:
        raise ValueError('collision-activation:bounded physics item count')
    if state & 512 and flags & 255 not in (0,1) or state & 1024 and flags >> 8 not in (0,1):
        raise ValueError('collision-activation:Boolean field scalar')
    result=dict(owner=f'{owner:016x}',mono=f'{mono:016x}',settings=f'{settings:016x}',items=f'{items:016x}',
        handle=f'{handle:016x}',colliderCount=colliders if state&16 else None,itemCount=count if state&8 and item_count_validated else None,
        timerId=timer if state&32 else None,managerColliderCount=manager if state&256 else None,
        interactiveBroken=bool(flags&255) if state&512 else None,handleValid=bool(flags>>8) if state&1024 else None,readState=state)
    if not item_count_validated:
        result.update(itemCountStatus='withheld_invalid_open_generic_offset',uninterpretedItemCountWord=count if state&8 else None)
    return result


def decode(entry, profile):
    from scripts.game_data.collision_capture_inspect import _origin, _floats
    row = entry['returnRecord'];kind = entry['kind']
    args = [int.from_bytes(bytes.fromhex(x),'little') for x in row['args']]
    before = bytes.fromhex(row['before']);after = bytes.fromhex(row['after']);query = bytes.fromhex(row['queryHex'])
    contract = profile['lifecycleCapture']['activation']['contract'];limits=contract['limits']
    count_validated=contract['schema']=='endfield.collision-activation-capture-native.v3'
    if not count_validated:
        if contract['schema']!='endfield.collision-activation-capture-native.v2' or next(t for t in contract['types'] if t['role']=='list')['fields'][0]['offset']!=0:
            raise ValueError('collision-activation:unsupported list count declaration')
    first,last = frame(before,kind,args,limits,item_count_validated=count_validated),frame(after,kind,args,limits,item_count_validated=count_validated)
    if row['queryState'] != 1|(2 if before == after[:64] else 0):
        raise ValueError('collision-activation:frame repeat state')
    identities=[]
    for index, observation in enumerate((first,last)):
        native,instance,state = struct.unpack_from('<QiI',query,128+index*16)
        klass,statics,offset,initialized,witness_native = struct.unpack_from('<2QiIQ',query,64+index*32)
        if state & ~3 or state&2 and not state&1:
            raise ValueError('collision-activation:Mono identity read dependencies')
        if state&2 and not (observation['mono']!='0000000000000000' and klass and statics and initialized and 0<=offset<=256 and native==witness_native):
            raise ValueError('collision-activation:Mono InstanceID offset witness')
        identities.append(dict(native=f'{native:016x}',instanceId=instance,readState=state))
    source = _origin(row['colliderOrigin'],required=row['colliderOrigin']['state']!=0)
    repeat = _origin(row['meshOrigin'],required=row['meshOrigin']['state']!=0)
    result = dict(before=first,after=last,identityBefore=identities[0],identityAfter=identities[1],source=source,repeatedSource=repeat,
        stableNativeIdentity=first['mono']==last['mono'] and identities[0]==identities[1] and identities[0]['readState']==3,
        stableSerializedIdentity=source==repeat and source['status']=='mapped',
        boundary='Original stage entry/return and separately timed fields; no inferred budget branch, IFix choice, physical activation or solver contact.')
    if kind in (96,97):
        result.update(attackBefore=_floats(query[:12]) if not row['flags']&256 else None,
                      attackAfter=_floats(query[16:28]) if not row['flags']&512 else None)
    if kind==98:
        scalar = int.from_bytes(bytes.fromhex(row['result']),'little')
        if scalar not in (0,1):
            raise ValueError('collision-activation:original manager Boolean result')
        result['originalManagerResult'] = bool(scalar)
    return result
