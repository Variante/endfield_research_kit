"""Fresh six-route SpecialIdleCondition transport and its own base identity."""
import json

TYPE='Beyond.Gameplay.View.Animation.SpecialIdleCondition'
SCHEMA='endfield.animation-idle-condition-transport.v1'
STATUS='validated-conditional-animation-idle-condition-transport'
TYPES=['Beyond.Gameplay.View.Animation.'+n for n in(
    'CameraPropertyCondition','FloorBumpCondition','IdleTimeCondition','IKCastCondition',
    'LODScreenSizeCondition','TransformInSightCondition')]


def need(check,condition,detail=None):
    if not condition:raise ValueError('animationIdleConditionSources.'+check+':'+str(detail)[:1200])


def norm(value):return json.loads(json.dumps(value))


def derive_transport(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.levelscript_module_union_sources import derive_reference_transport
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    _publication_gate(image,pins)
    value=derive_reference_transport(image,pins,type_name=TYPE,schema=SCHEMA,status=STATUS,expected_count=6,
        evidence_boundary=dict(exact=__doc__,conditional='Initialized own formatter, initially null wrapper output, actual returning ReadPackable contexts and canonical callbacks, normal helpers and independently disabled collector.',
            unresolved=['six independent child grammars','containing list and owner','live callback and existing compatible-wrapper selection']))
    need('exact-own-ordered-nominal-family',[r['wrappedType']for r in value['programs']]==TYPES)
    value['sourceRegions']=[[a-image.pe.image_base,h]for a,h in value['sourceRegions']]
    ctx=NativeReferenceContext(image);original=ctx.index.types[TYPE]
    need('own-abstract-reference-original',not ctx.is_value_type(TYPE)and original.flags&128==128)
    value['nominalOriginal']=dict(typeName=TYPE,typeDefinition=original.index,flags=original.flags,valueType=False)
    header=pointer.owned(image,image.pe.image_base+value['symbolRvas']['header'])
    value['headerSourceRegions']=[[a-image.pe.image_base,b.hex()]for a,b in header['regions']]
    value['readerOffsets']=scalar.reader_offsets(image,'animationIdleCondition')
    value['runtimeAnimationBehaviorProved']=value.pop('runtimeModuleBehaviorProved')
    value=norm(value);replay_transport(value,pins);_publication_gate(image,pins);return value


def replay_transport(value,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.levelscript_module_union_sources import program
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    need('own-complete-selected-native-transport',value.get('schema')==SCHEMA and value.get('status')==STATUS
        and value.get('nativeInputs')==pins and value.get('typeName')==TYPE
        and value.get('concreteChildGrammarAdmitted')is False and value.get('parentFieldAdmitted')is False
        and value.get('wholeOwnerAdmitted')is False and value.get('runtimeAnimationBehaviorProved')is False)
    rows=value.get('programs',[]);method=value.get('slot5Method',[]);switch=value.get('switch',{})
    need('exact-six-current-routes',len(rows)==6 and[r.get('tag')for r in rows]==list(range(6))
        and[r.get('wrappedType')for r in rows]==TYPES and switch.get('entryCount')==6
        and len(switch.get('entries',[]))==6 and len(method)==4 and method[2]=='Deserialize')
    base=rows[0]['source']['selectedBytes'][0][0]-method[3]
    need('literal-native-image-base',type(base)is int and base>=1<<32)
    raw=regions(value['ownedWindows'],value['sourceRegions'],base,'idle-condition-union')
    symbols={k:base+v for k,v in value['symbolRvas'].items()};symbols['imageBase']=base
    table=int(switch['tableVa'],16);entry=base+method[3]
    need('same-own-dispatcher',int(switch['dispatcherVa'],16)==entry)
    for row,selected in zip(rows,switch['entries'],strict=True):
        tag=row['tag'];target=int(selected['bodyVa'],16);slot=row['tableEntry']
        need('own-actual-table-word',selected['tag']==tag and selected['wrapperName']==row['wrapperName']
            and selected['targetVa']==selected['bodyVa'] and slot.get('rva')==table-base+4*tag
            and slot.get('targetRva')==target-base
            and bytes.fromhex(slot.get('rawHex',''))==(target-base).to_bytes(4,'little'))
        need('whole-selected-route-bytes',norm(program(raw,entry,symbols,tag=tag,count=6,table=table,selected=target))==row['source'])
        usage=row['typedRequest'];typed=row['typedArgument']
        need('own-returning-wrapper-request',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[row['wrapperName']])
            and typed.get('argumentType')==row['wrapperName']and typed.get('concreteTypeKind')==18
            and typed.get('methodDefinition')==usage.get('methodSpec',[None])[0]
            and row['originalLineage'][0].get('typeName')==row['wrappedType']and row['originalLineage'][-1].get('typeName')==TYPE
            and row['wrapperLineage'][0]==row['wrapperName']and row['wrapperLineage'][-1]==value['wrapperName'],
            dict(tag=tag,usage=[usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')],
                typed=typed,originalEnds=[row['originalLineage'][0],row['originalLineage'][-1]],wrapperEnds=[row['wrapperLineage'][0],row['wrapperLineage'][-1]]))
    need('whole-canonical-null-bytes',norm(program(raw,entry,symbols,tag=0,count=6,table=table,
        selected=int(switch['entries'][0]['bodyVa'],16),ff=True))==value['canonicalFF'])
    header=regions(value['headerWindows'],value['headerSourceRegions'],base,'idle-condition-header')
    expected={marker:enclosing_header(header,symbols['header'],value['readerOffsets'],marker=marker)for marker in('short','extended','false')}
    need('own-all-header-byte-paths',norm(expected)==value['headerPrograms'])
    holder=value['baseHolder'];pair=value['pair'];adapter=value['adapter'];nominal=value['nominalOriginal']
    need('own-nominal-abstract-reference',nominal.get('typeName')==TYPE and type(nominal.get('typeDefinition'))is int
        and nominal['typeDefinition']>=0 and nominal.get('valueType')is False and nominal.get('flags',0)&128==128
        and holder.get('declaredType')==TYPE and holder.get('offset')==16)
    need('own-canonical-base-pair',pair.get('registration',{}).get('originalType')==TYPE
        and pair['registration'].get('wrapperType')==value['wrapperName']
        and adapter.get('schema')=='endfield.reference-object-adapter-source.v1'and adapter.get('nativeInputs')==pins
        and adapter.get('typeName')==TYPE and adapter.get('wrapperName')==value['wrapperName']and adapter.get('pair')==pair
        and adapter.get('callbackBinding',{}).get('actualCallbackEqualsCanonicalRequired')is True
        and adapter['callbackBinding'].get('runtimeSelectionObserved')is False)
    conversions=value.get('inheritedConversions',[])
    need('all-own-inherited-conversions',len(conversions)==6 and{r['wrapperName']for r in conversions}=={r['wrapperName']for r in rows})
    for row in conversions:
        p=row['conversion'];need('complete-inherited-base-reference',row['holder']['declaredType']==TYPE
            and row['holder']['offset']==16 and p.get('normalReturn')is True
            and p.get('sameFullReferenceReturned')is True and p.get('interfaceOrdinal')==row['interfaceOrdinal'])
    return base
