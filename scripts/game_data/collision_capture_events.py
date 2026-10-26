"""Expand the current collision JSON format's omitted default fields.

Only default values are omitted. Missing required event identity or explicitly
invalid values are never repaired, and observation checks still run afterward.
"""
from __future__ import annotations

FORMAT='endfield.collision-event-json.v2'
REQUIRED=('sequence','call','parent','qpc','thread','kind','phase','flags','args')
HEX_WIDTHS=dict(result=8,model=96,before=64,after=128,nameUtf16=128,sceneUtf16=128,world=64,
                transform=8,go=8,mesh=8,queryHex=192,ecsBeforeHex=192,ecsAfterHex=192,sourceContextHex=144)
ZERO_NUMBERS=('objectId','goId','meshId','active','enabled','convex','queryState')
ORIGIN=dict(state=0,check=0,fileIndex=-1,pathIdHex=bytes(8).hex(),filenameHex=bytes(512).hex())
MEMORY=dict(root=bytes(8).hex(),startQpc=0,endQpc=0,blocks=0,bytes=0,examined=0,rejected=0,unreadable=0,limits=0)
ORIGIN_FIELDS=('colliderOrigin','meshOrigin')
MEMORY_FIELDS=('colliderMemory','meshMemory','contactMemory','sourceMemory','meshIdsMemory')


def expand(record: dict, event_format: str) -> dict:
    if event_format!=FORMAT or not isinstance(record,dict) or any(k not in record for k in REQUIRED):
        raise ValueError('collision event: format or required identity/arguments missing')
    allowed=set(REQUIRED)|set(HEX_WIDTHS)|set(ZERO_NUMBERS)|set(ORIGIN_FIELDS)|set(MEMORY_FIELDS)
    if set(record)-allowed:
        raise ValueError('collision event: undeclared fields:'+','.join(sorted(set(record)-allowed)))
    out={k:bytes(n).hex() for k,n in HEX_WIDTHS.items()}
    out.update(dict.fromkeys(ZERO_NUMBERS,0));out.update(record)
    for fields,defaults in ((ORIGIN_FIELDS,ORIGIN),(MEMORY_FIELDS,MEMORY)):
        for name in fields:
            supplied=record.get(name,{})
            if not isinstance(supplied,dict) or set(supplied)-set(defaults):
                raise ValueError('collision event: invalid optional object:'+name)
            out[name]={**defaults,**supplied}
    return out


def compact(record: dict) -> dict:
    """Lossless size projection for offline examples over existing dense rows."""
    expand(record,FORMAT)  # Declared keys only; never infer defaults for identity.
    out={k:record[k] for k in REQUIRED}
    for k,n in HEX_WIDTHS.items():
        if k in record and record[k]!=bytes(n).hex():out[k]=record[k]
    for k in ZERO_NUMBERS:
        if record.get(k,0)!=0:out[k]=record[k]
    for fields,defaults in ((ORIGIN_FIELDS,ORIGIN),(MEMORY_FIELDS,MEMORY)):
        for name in fields:
            subset={k:v for k,v in record.get(name,{}).items() if v!=defaults[k]}
            if subset:out[name]=subset
    return out
