"""Finite ExtraData record cursor on an independently native-owned operation."""
from scripts.game_data.memorypack.animation_union_codec import AnimationUnionReader
from scripts.game_data.memorypack.animation_extra_record_components import PLANS,record_key
from scripts.game_data.memorypack.animation_record_codec import ATOMS

NODE_LIMIT=16384


def need(check,condition):
    if not condition:raise ValueError('animationExtraRecordCodec.'+check)


def budget_node(budget):
    if budget is None:budget=dict(remaining=NODE_LIMIT)
    need('shared-node-budget',isinstance(budget,dict)and set(budget)=={'remaining'}
        and type(budget['remaining'])is int and 0<budget['remaining']<=NODE_LIMIT)
    budget['remaining']-=1;return budget


class AnimationExtraReader(AnimationUnionReader):
    def extra_array(self,capability,*,depth=0,budget=None):
        from scripts.game_data.memorypack.animation_extra_array_codec import read
        return read(self,capability,depth=depth,budget=budget)

    def extra_record(self,capability,*,depth=0,budget=None):
        need('bounded-record-depth',type(depth)is int and 0<=depth<=64)
        cap=self.operation.child(capability);name=cap.get('typeName')
        from scripts.game_data.memorypack import animation_enemy_shake_value_components as shake
        if name==shake.TYPE:
            need('own-enemy-shake-value8-key',capability==shake.CAPABILITY)
            from scripts.game_data.memorypack.animation_enemy_shake_value_codec import read
            return read(self,depth=depth,budget=budget)
        from scripts.game_data.memorypack import shader_property_value_components as shader
        if name==shader.source.TYPE:
            need('own-shader-property-value24-key',capability==shader.CAPABILITY)
            from scripts.game_data.memorypack.shader_property_value_codec import read
            return read(self,depth=depth,budget=budget)
        from scripts.game_data.memorypack import animation_extra_value32_components as value32
        if name in value32.PLANS:
            need('own-State-or-Play-value32-key',capability==value32.key(name))
            from scripts.game_data.memorypack.animation_extra_value32_codec import read
            return read(self,name,depth=depth,budget=budget)
        from scripts.game_data.memorypack import animation_renderer_value_components as renderer
        if name==renderer.source.TYPE:
            need('own-renderer-value8-key',capability==renderer.CAPABILITY)
            from scripts.game_data.memorypack.animation_renderer_value_codec import read
            return read(self,depth=depth,budget=budget)
        budget=budget_node(budget)
        need('own-reference-record',name in PLANS and capability==record_key(name)
            and cap.get('valueStorageKind')=='reference8'and cap.get('wholeGrammarAdmitted')is True
            and cap.get('ordinaryOriginalReadValueAdmitted')is True and cap.get('ordinaryOriginalCallbackAdmitted')is True and cap.get('nullable')is True
            and cap.get('nullMarker')==255 and cap.get('memberCount')==len(PLANS[name]))
        reads=cap.get('orderedReads',[])
        need('complete-own-wire-order',len(reads)==len(PLANS[name])
            and[(r.get('memberIndex'),r.get('fieldName'))for r in reads]==[(i,f[0])for i,f in enumerate(PLANS[name])]
            and all(r.get('kind')in ATOMS or r.get('kind')in('byte-payload','beyond-curve-value','animation-sk-morph-setting','animation-extra-value-array',
                'animation-extra-record','animation-extra-static-dictionary','animation-extra-reference-list',
                'animation-extra-enum-list','animation-extra-int32-array')for r in reads))
        start=self.pos;fields=[];null=self.peek()==255
        if null:self.take(1,capability+'.null')
        else:
            self.header(cap['memberCount'])
            for read in reads:
                at=self.pos;kind=read['kind']
                if kind in ATOMS:value=dict(rawHex=self.take(ATOMS[kind],read['fieldName']).hex())
                elif kind=='byte-payload':value=dict(value=self.byte_payload())
                elif kind=='beyond-curve-value':
                    from scripts.game_data.memorypack.beyond_curve_value_codec import read_curve
                    value=dict(child=read_curve(self))
                elif kind=='animation-extra-value-array':
                    value=dict(child=self.extra_array(read['childCapability'],depth=depth+1,budget=budget))
                elif kind=='animation-extra-record':
                    value=dict(child=self.extra_record(read['childCapability'],depth=depth+1,budget=budget))
                elif kind=='animation-extra-reference-list':
                    from scripts.game_data.memorypack.animation_extra_reference_lists import read as read_list
                    value=dict(child=read_list(self,read['childCapability'],depth=depth+1,budget=budget))
                elif kind=='animation-extra-enum-list':
                    from scripts.game_data.memorypack.animation_enemy_hurt_enum_lists import read as read_enum_list
                    value=dict(child=read_enum_list(self,depth=depth+1,budget=budget))
                elif kind=='animation-extra-int32-array':
                    from scripts.game_data.memorypack.animation_extra_int_array_codec import read as read_int_array
                    value=dict(child=read_int_array(self,depth=depth+1,budget=budget))
                elif kind=='animation-extra-static-dictionary':
                    from scripts.game_data.memorypack.animation_extra_dictionary_codec import read as read_dictionary
                    value=dict(child=read_dictionary(self,PLANS[name][read['memberIndex']][1],depth=depth+1,budget=budget))
                else:
                    # This distinct managed40 child must supply its own codec;
                    # it is never read as another nominal40 or raw40 bits.
                    from scripts.game_data.memorypack.sk_morph_value_codec import read as read_sk_morph
                    value=dict(child=read_sk_morph(self,depth=depth+1,budget=budget))
                fields.append(dict(fieldName=read['fieldName'],kind=kind,start=at,end=self.pos,**value))
        result=dict(kind=capability,typeName=name,start=start,end=self.pos,isNull=null,fields=fields,
            runtimeAnimationProved=False,containingRouteClaimed=False)
        self.records.append(result);return result
