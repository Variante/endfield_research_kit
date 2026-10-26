"""Pure finite animation-record cursor; containing routes are not selected here.

The caller supplies already authenticated record/child components and its
selected pool operation. These codecs do not authenticate a native run, infer
AnimationConfig dictionaries, or select a CharInteract action tag.
"""
import struct
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.animation_record_components import PLANS

ATOMS={'bool-byte':1,'byte':1,'scalar32':4,'gameplay-tag32':4,'float32-bits':4,
       'scalar64-bits':8,'float64-bits':8,'vector2-raw8':8,'unity-vector3-raw12':12,
       'unity-quaternion-raw16':16,'animation-clip-raw36':36}
PROFILES={'alpha-blend-value':'skill-alpha-blend','body-type-def-value':'body-type-def-value',
          'beyond-curve-value':'beyond-curve-value','byte-payload':'byte-payload',
          'transform-desc-profile':'animation-transform-desc'}


def need(check,condition):
    if not condition:raise ValueError('animationRecordCodec.'+check)


class AnimationRecordReader(Reader):
    def __init__(self,data,source,limit=None,*,operation):
        super().__init__(data,source,limit);self.operation=operation

    def byte_payload(self,*,reserve=0):
        cap=self.operation.child('byte-payload')
        need('signed-pooled-string-source',cap.get('wholeGrammarAdmitted')is True and cap.get('encoding')=='int32-pool-index'
            and cap.get('emptyIndex')==-1 and cap.get('nullIndex')==-2)
        need('complete-pool-index',self.pos+4<=self.limit)
        at=self.pos;index=struct.unpack_from('<i',self.data,at)[0]
        # The enclosing raw owner's selected pool operation owns resolution.
        value=self.operation.pool_index(index)
        self.take(4,'string-pool-index-i32');self.records.append(dict(kind='pooled-string',start=at,end=self.pos,poolIndex=index))
        return value

    def record(self,capability,*,depth=0):
        need('bounded-record-depth',type(depth)is int and 0<=depth<=64)
        cap=self.operation.child(capability);name=cap.get('typeName')
        need('own-finite-record',name in PLANS and PLANS[name][0]==capability
            and cap.get('memberCount')==PLANS[name][1]and cap.get('nullable')is True and cap.get('nullMarker')==255
            and cap.get('wholeGrammarAdmitted')is True and cap.get('directWrapperGrammarAdmitted')is True
            and cap.get('actualContainingRouteAdmitted')is False and cap.get('wholeOwnerAdmitted')is False)
        reads=cap.get('orderedReads',[])
        need('complete-finite-wire-program',len(reads)==cap['memberCount']and all(type(r.get('memberIndex'))is int and r['memberIndex']==i
            and isinstance(r.get('fieldName'),str)and bool(r['fieldName'])and(r.get('kind')in ATOMS or r.get('kind')in PROFILES)
            and(r.get('childCapability')is None if r.get('kind')in ATOMS else r.get('childCapability')==PROFILES[r['kind']])
            for i,r in enumerate(reads)))
        start=self.pos;fields=[];null=self.peek()==255
        if null:self.take(1,capability+'.null')
        else:
            self.header(cap['memberCount'])
            for read in reads:
                at=self.pos;kind=read['kind']
                if kind in ATOMS:
                    raw=self.take(ATOMS[kind],capability+'.'+read['fieldName'])
                    extra=dict(rawHex=raw.hex())
                    if kind=='animation-clip-raw36':extra.update(wrapperFramingUsed=False,boolBytesNormalized=False,paddingHex=raw[34:36].hex())
                elif kind=='alpha-blend-value':
                    from scripts.game_data.memorypack.alpha_blend_value_codec import read_alpha
                    extra=dict(child=read_alpha(self,depth=depth+1))
                elif kind=='body-type-def-value':
                    from scripts.game_data.memorypack.body_type_value_codec import read as read_body
                    extra=dict(child=read_body(self,depth=depth+1))
                elif kind=='beyond-curve-value':
                    from scripts.game_data.memorypack.beyond_curve_value_codec import read_curve
                    extra=dict(child=read_curve(self))
                elif kind=='transform-desc-profile':
                    from scripts.game_data.memorypack.animation_transform_desc_codec import read as read_transform
                    extra=dict(child=read_transform(self,depth=depth+1))
                else:extra=dict(value=self.byte_payload())
                fields.append(dict(fieldName=read['fieldName'],kind=kind,start=at,end=self.pos,**extra))
        result=dict(kind=capability,typeName=name,start=start,end=self.pos,isNull=null,fields=fields,
            containingRouteClaimed=False,runtimeAnimationProved=False)
        self.records.append(result);return result
