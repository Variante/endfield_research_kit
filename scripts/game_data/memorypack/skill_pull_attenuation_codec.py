"""Finite Pull MC2/FF driver; managed16 defaults are never serialized padding."""
from scripts.game_data.memorypack import skill_pull_attenuation_sources as source


def need(check,condition):
    if not condition:raise ValueError('skillPullAttenuationCodec.'+check)


def require_capability(cap):
    need('exact-managed-value-and-wire-plan',cap.get('typeName')==source.TYPE and cap.get('wrapperName')==source.WRAPPER
        and cap.get('orderedReads')==source.ORDER and cap.get('elementValueType')is True
        and all(type(cap.get(k))is int and cap[k]==n for k,n in(('memberCount',2),('managedBytes',16),('nullMarker',255),('nullWireBytes',1)))
        and cap.get('referenceLaneOffsets')==[0]and all(type(n)is int for n in cap['referenceLaneOffsets'])
        and cap.get('paddingByteRanges')==[[12,16]]and all(type(n)is int for row in cap['paddingByteRanges']for n in row)
        and cap.get('wireBytes')is None and cap.get('positiveWireBytes')is None
        and all(cap.get(k)is True for k in('nullable','nullAdmitted','nullReturnsDefaultValue','wholeGrammarAdmitted',
            'canonicalValueCallbackProved','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved','completeSourceOwnedProgram')))
    return cap


class PullAttenuationReader:
    def __init__(self,reader):self.reader=reader

    def record(self,depth=0):
        need('depth',type(depth)is int and 0<=depth<=64);r=self.reader;require_capability(r.operation.child(source.CAPABILITY))
        start=r.pos;fields=[];null=r.peek()==255
        if null:r.take(1,source.CAPABILITY+'.default16')
        else:
            r.header(2);at=r.pos;r.take(4,source.CAPABILITY+'.attenuationFactor.Single')
            fields.append(dict(fieldName='attenuationFactor',start=at,end=r.pos));at=r.pos
            need('depth',depth+1<=64);cap=r.operation.child(source.CHILD)
            need('independent-ordinary-SuperArmor-reference',cap.get('typeName')==source.REFERENCE
                and all(cap.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
                    'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved'))
                and type(cap.get('referenceReaderMethodDefinition'))is int and cap['referenceReaderMethodDefinition']>0
                and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0)
            from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
            RootChildrenReader(r).record(source.CHILD,depth+1)
            fields.append(dict(fieldName='superArmorValue',start=at,end=r.pos))
        out=dict(kind=source.CAPABILITY,start=start,end=r.pos,isNull=null,returnsDefaultValue=null,fields=fields)
        r.records.append(out);return out
