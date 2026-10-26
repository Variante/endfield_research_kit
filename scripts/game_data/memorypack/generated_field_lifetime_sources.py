"""Rejoin completed hidden-source bytes before retiring their stack interval.

The source VM separately owns each source/type/local/field flow. This helper
only authenticates the selected marker bytes, order and complete field cover;
it never infers a managed or serialized width from a name.
"""
from scripts.game_data.il2cpp.initializer_control import control_transfer


def need(key,condition,detail=None):
    if not condition:raise ValueError('generatedFieldLifetime.'+key+':'+str(detail)[:700])


def hidden_certificates(path,*,base,hidden_locals,field_stores):
    from scripts.game_data.memorypack.buff_ec_profiles_native import va,site
    need('literal-inputs',type(base)is int and isinstance(path,list)and isinstance(hidden_locals,list)and isinstance(field_stores,list))
    indices={va(r):i for i,r in enumerate(path)}
    need('unique-selected-instruction-boundaries',len(indices)==len(path))
    out=[]
    for item in hidden_locals:
        member=item.get('memberIndex');width=item.get('bytes');marker=item.get('sourceInstruction')
        static8=width==8 and item.get('sourceAbi')=='void-byref-reference8'and item.get('initiallyZeroLocalRequired')is True
        if static8:
            from scripts.game_data.memorypack.skill_gait_dictionary_sources import TYPE
            from scripts.game_data.memorypack.animation_extra_dictionary_sources import TYPES
            need('own-static-reference-local-identity',item.get('nominalTypeName')in({TYPE}|set(TYPES))and type(item.get('nominalTypeDefinition'))is int)
        entity40=width==40 and item.get('nominalTypeName')=='Beyond.Gameplay.Core.EntityPtr'and type(item.get('nominalTypeDefinition'))is int
        sk_morph40=width==40 and item.get('nominalTypeName')=='Beyond.Gameplay.Core.SkMorphPlaySetting'and type(item.get('nominalTypeDefinition'))is int
        montage_value=(width,item.get('nominalTypeName'))in((32,'Beyond.Gameplay.BodyTypeDef'),(56,'Beyond.Gameplay.View.Animation.AlphaBlend'))and type(item.get('nominalTypeDefinition'))is int
        if entity40:
            need('own-opaque-Entity40-lifetime-policy',item.get('opaqueRuntimeStorageRanges')==[[24,40]]
                and item.get('selectedBarrierValueOffsets')==[24]and item.get('runtimeReferenceLayoutAdmitted')is False
                and item.get('completeRuntimePaddingMapAdmitted')is False and'referenceLaneOffsets'not in item)
        need('independent-current-hidden-member-width',type(member)is int and member>=0 and type(width)is int and(width in(12,16,24)or static8 or entity40 or sk_morph40 or montage_value)
             and isinstance(marker,list)and len(marker)==2 and type(marker[0])is int)
        address=base+marker[0]
        need('same-selected-hidden-source-marker',address in indices and site(path[indices[address]],base)==marker)
        start=indices[address]
        need('actual-hidden-source-call',control_transfer(path[start])['kind']=='call')
        stores=[s for s in field_stores if s['memberIndex']==member]
        coverage=[];positions=[]
        for store in stores:
            target=store['instruction'];at=base+target[0]
            need('same-selected-complete-field-store',at in indices and site(path[indices[at]],base)==target)
            offset,count=store['sourceOffset'],store['storedBytes']
            need('finite-exact-field-byte-slice',type(offset)is int and type(count)is int and 0<=offset<offset+count<=width)
            coverage.extend(range(offset,offset+count));positions.append(indices[at])
        need('every-hidden-source-byte-stored-once-after-call',sorted(coverage)==list(range(width))and positions and min(positions)>start,
             dict(memberIndex=member,bytes=width,coverage=coverage))
        end=max(positions)
        out.append(dict(memberIndex=member,displacement=item['displacement'],bytes=width,sourceInstruction=marker,
                        fieldStores=stores,liveThroughPathIndex=end,liveThroughInstruction=site(path[end],base),
                        completeIndependentSourceFlowRequired=True,childGrammarAdmitted=False))
        if entity40:out[-1].update(opaqueRuntimeStorageRanges=[[24,40]],selectedBarrierValueOffsets=[24],
            runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False)
    return out


def montage_copy_certificates(path,*,base,hidden_locals,copied_locals,hidden_certificates):
    """Retire exact Body32/Alpha56 argument homes after complete field transfer."""
    from scripts.game_data.memorypack.buff_ec_profiles_native import va,site
    indices={va(r):i for i,r in enumerate(path)};out=[]
    need('unique-copy-lifetime-instructions',len(indices)==len(path))
    for hidden in hidden_locals:
        member=hidden['memberIndex'];width=hidden['bytes'];name=hidden.get('nominalTypeName')
        need('finite-montage-value-lifetime',(width,name)in((32,'Beyond.Gameplay.BodyTypeDef'),(56,'Beyond.Gameplay.View.Animation.AlphaBlend')))
        certificates=[p for p in hidden_certificates if p['memberIndex']==member and p['sourceInstruction']==hidden['sourceInstruction']]
        need('one-independent-complete-field-lifetime',len(certificates)==1)
        certificate=certificates[0];copies=[c for c in copied_locals if c.get('memberIndex')==member];covered=[];positions=[]
        source_index=indices[base+hidden['sourceInstruction'][0]]
        for copied in copies:
            marker=copied.get('storeInstruction');offset=copied.get('sourceOffset');count=copied.get('bytes')
            need('same-owned-copied-nominal',copied.get('nominalTypeName')==name and copied.get('nominalTypeDefinition')==hidden.get('nominalTypeDefinition'))
            need('literal-complete-copy-slice',type(offset)is int and type(count)is int and 0<=offset<offset+count<=width)
            address=base+marker[0]
            need('same-actual-selected-copy-marker',address in indices and site(path[indices[address]],base)==marker)
            positions.append(indices[address]);covered.extend(range(offset,offset+count))
        field_positions=[indices[base+s['instruction'][0]]for s in certificate['fieldStores']]
        need('whole-copy-before-complete-field-transfer',sorted(covered)==list(range(width))and positions
            and source_index<min(positions)<=max(positions)<min(field_positions),dict(memberIndex=member,bytes=width,coverage=covered))
        out.append(dict(memberIndex=member,nominalTypeName=name,nominalTypeDefinition=hidden['nominalTypeDefinition'],
            copiedLocals=copies,fieldLifetime=certificate,liveThroughPathIndex=certificate['liveThroughPathIndex'],
            completeIndependentSourceFlowRequired=True,childGrammarAdmitted=False))
    return out
