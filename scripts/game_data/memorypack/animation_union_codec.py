"""Selected stored animation tags on the authenticated record cursor.

Only short tags proved by the union component are accepted. Collections,
AnimationConfig dictionaries, public raw-owner selection and EOF stay with
their independently authenticated owners.
"""
from scripts.game_data.memorypack.animation_record_codec import AnimationRecordReader
from scripts.game_data.memorypack.animation_union_components import CAPABILITIES


def need(check,condition):
    if not condition:raise ValueError('animationUnionCodec.'+check)


class AnimationUnionReader(AnimationRecordReader):
    def selected_union(self,capability,*,depth=0):
        need('finite-selected-capability',capability in CAPABILITIES.values())
        need('bounded-union-depth',type(depth)is int and 0<=depth<64)
        cap=self.operation.child(capability);routes=cap.get('selectedRoutes',[])
        need('complete-selected-stored-union',cap.get('wholeGrammarAdmitted')is True
            and cap.get('selectedStoredByteGrammarAdmitted')is True and cap.get('ordinaryBaseAdapterAdmitted')is True
            and cap.get('inheritedBaseConversionsAdmitted')is True and cap.get('nullable')is True
            and cap.get('nullMarker')==255 and cap.get('tagEncoding')=='short-byte'and cap.get('wideTagsAdmitted')is False
            and isinstance(routes,list)and bool(routes)and len({r.get('tag')for r in routes})==len(routes)
            and all(type(r.get('tag'))is int and 0<=r['tag']<250 and isinstance(r.get('childCapability'),str)for r in routes))
        marker=self.peek();start=self.pos
        if marker==255:
            self.take(1,capability+'.null');result=dict(kind=capability,start=start,end=self.pos,isNull=True,fields=[])
        else:
            matches=[r for r in routes if r['tag']==marker]
            need('actual-selected-short-tag',len(matches)==1)
            route,=matches;child=self.operation.child(route['childCapability'])
            need('same-exact-child-record',child.get('typeName')==route.get('typeName')
                and child.get('wrapperName')==route.get('wrapperName')and child.get('memberCount')==route.get('memberCount'))
            self.take(1,capability+'.tag');value=self.record(route['childCapability'],depth=depth+1)
            result=dict(kind=capability,start=start,end=self.pos,isNull=False,tag=marker,
                typeName=route['typeName'],child=value)
        result.update(containingCollectionClaimed=False,runtimeAnimationProved=False)
        self.records.append(result);return result
