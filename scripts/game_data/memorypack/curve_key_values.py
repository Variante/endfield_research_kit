"""Retain source-proved headerless keyframe words without float normalization.

Each caller authenticates its own nominal key type, field order and stride.
This projection grants no native capability and never substitutes Unity's
seven words for Beyond's eight words.
"""


def read_named_keys(reader,count,fields,width):
    if(type(count)is not int or count<0 or type(width)is not int or width<=0
        or not isinstance(fields,list)or len(fields)*4!=width
        or any(not isinstance(f,dict)or f.get('declaredType')not in('float','int')
            or type(f.get('wireOffset'))is not int or f['wireOffset']!=4*i
            or f.get('bytes')!=4 or not isinstance(f.get('fieldName'),str)
            for i,f in enumerate(fields))):
        raise ValueError('curveKeyValues.source-owned-word-layout')
    if count*width>reader.limit-reader.pos:
        raise ValueError('curveKeyValues.truncated-key-array: expected='+str(count*width)
            +' remaining='+str(reader.limit-reader.pos)+' offset='+str(reader.pos))
    keys=[]
    for _ in range(count):
        start=reader.pos;members=[]
        for field in fields:
            at=reader.pos;raw=reader.take(4,field['fieldName'])
            members.append(dict(fieldName=field['fieldName'],declaredType=field['declaredType'],
                start=at,end=reader.pos,rawHex=raw.hex()))
        keys.append(dict(start=start,end=reader.pos,fields=members))
    return keys
