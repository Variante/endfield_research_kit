"""Own MC7/FF impulse Envelope codec, inactive until its native joins pass.

Managed32, its two reference lanes and padding are ABI facts. Each serialized
Curve uses the separately proved Unity custom formatter; no fixed positive
wire width or reference-object adapter is inferred from the value layout.
"""
from scripts.game_data.memorypack.skill_impulse_envelope_sources import TYPE,CURVE,MEMBERS

CAPABILITY='skill-impulse-envelope'
ORDER=[dict(fieldName=n,kind={CURVE:'curve-profile','float':'single-bits','bool':'bool'}[t],
    childCapability='curve-profile'if t==CURVE else None)for n,t in MEMBERS]
LABEL='skillImpulseEnvelopeCodec'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def require_capability(cap):
    need('own-nominal-value-and-layout',isinstance(cap,dict)and cap.get('typeName')==TYPE
        and all(type(cap.get(k))is int and cap[k]==v for k,v in
            (('memberCount',7),('managedBytes',32),('nullMarker',255),('nullWireBytes',1)))
        and cap.get('referenceLaneOffsets')==[0,8]and cap.get('paddingByteRanges')==[[30,32]]
        and all(type(n)is int for n in cap['referenceLaneOffsets'])
        and all(type(n)is int for row in cap['paddingByteRanges']for n in row))
    need('own-complete-source-default-and-wire',all(cap.get(k)is True for k in
        ('nullable','nullReturnsDefaultValue','wholeGrammarAdmitted','ownConcreteGetterSemanticsProved',
         'ownConcreteFactorySemanticsProved','actualValueReadValueAdmitted','callbackSelectionConditional'))
        and cap.get('ordinaryOriginalReadValueAdmitted')is False and cap.get('wireBytes')is None
        and cap.get('positiveWireBytes')is None and cap.get('orderedReads')==ORDER)
    need('actual-value-reader-identities',all(type(cap.get(k))is int and cap[k]>0 for k in
        ('valueReaderMethodDefinition','valueSourceTargetRva','valueDispatcherTargetRva')))
    return cap


class ImpulseEnvelopeReader:
    def __init__(self,reader):self.reader=reader

    def record(self,depth=0):
        from scripts.game_data.memorypack.skill_animation_curve_codec import read_curve
        need('bounded-depth',type(depth)is int and 0<=depth<=64)
        r=self.reader;cap=require_capability(r.operation.child(CAPABILITY));start=r.pos;fields=[]
        null=r.peek()==255
        if null:r.take(1,CAPABILITY+'.default')
        else:
            r.header(cap['memberCount'])
            for field in ORDER:
                at=r.pos;kind=field['kind']
                if kind=='curve-profile':
                    need('bounded-child-depth',depth<64);read_curve(r,'curve-profile')
                else:r.take(4 if kind=='single-bits'else 1,CAPABILITY+'.'+field['fieldName'])
                fields.append(dict(fieldName=field['fieldName'],start=at,end=r.pos))
        out=dict(kind=CAPABILITY,start=start,end=r.pos,isNull=null,fields=fields)
        if null:out['returnsDefaultValue']=True
        else:out['memberCount']=7
        r.records.append(out);return out
