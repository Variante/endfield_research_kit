"""Fresh Montage reference children and their actual positive list requests.

Reference list stride is never an element wire width. Each request is joined
to its own current wrapper, complete stored fields and canonical callback.
The retained declarations are reviewed native source windows, not receipts.
"""
import copy
import json

from scripts.game_data.contracts import CONTRACTS_DIR

PREFIX='Beyond.Montage.'
REFERENCES=tuple(PREFIX+n for n in('DecoEntity','DynamicEntity','EventInfo','DynamicEntityExtraEffect'))
LISTS={'decoEntities':REFERENCES[0],'dynamicEntities':REFERENCES[1],'extraEffects':REFERENCES[3]}


def need(check,condition,detail=None):
    if not condition:raise ValueError('npcMontageChildren.'+check+':'+str(detail)[:1200])


def derive(image,pins,root_records,layout):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import montage_sources,generated_reader_sources,pooled_source_helper,generated_lifecycle_sources
    from scripts.game_data.memorypack import reference_list_value_sources as lists
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.pointer_param import methods
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    fact=json.loads((CONTRACTS_DIR/'npc_montage_children_native.json').read_bytes())
    need('reviewed-selected-source-declarations',fact['schema']=='endfield.npc-montage-child-sources.v1'
        and fact['status']=='exact-current-build'and fact['nativeInputs']==pins
        and{r['type']for r in fact['fieldSources']}==set(REFERENCES[:3]))
    records=montage_sources.validate_fields(image,pins,fact['fieldSources'])
    wrappers={w.wrapped_type:w for w in derive_from_image(image).values()if w.wrapped_type in REFERENCES}
    need('all-four-nominal-wrappers',set(wrappers)==set(REFERENCES))
    lifecycle=generated_lifecycle_sources.derive_many(image,pins,[wrappers[n].name for n in REFERENCES[:3]])
    refused=[{k:r[k]for k in('wrapperName','status','reason')if k in r}
        for r in lifecycle['owners']if r['status']!='lifecycle-source-proved']
    need('all-own-reference-factories-and-GetValue',not refused,refused)
    extra=generated_reader_sources.derive(image,pins,wrappers[REFERENCES[3]].name)
    reads=extra['orderedSourceReads']
    need('complete-extra-effect-ordered-source',extra.get('completeSelectedCallerAdmitted')is True
        and [(r['fieldName'],r['declaredType'],r['kind'])for r in reads]==[
            ('effectPath','string','byte-payload'),('localEulerAngles','UnityEngine.Vector3','value12:UnityEngine.Vector3'),
            ('localPosition','UnityEngine.Vector3','value12:UnityEngine.Vector3'),('mountNodePath','string','byte-payload')])
    pool=[pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
        for r in reads if r['kind']=='byte-payload']
    need('fresh-extra-pool-sources',all(p.get('status')=='validated'for p in pool))
    result=copy.deepcopy(layout);routes={}
    for name in REFERENCES:
        wrapper=wrappers[name];pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrapper)
        getter=methods(image,wrapper)['GetValue'];pointer=image.method_pointer_va(getter)
        need('own-complete-reference-GetValue',ctx.field(wrapper.name+'::__instance')==(wrapper.name,name,16)
            and image.pe.bytes_at_va(pointer,5)==bytes.fromhex('488b4110c3')
            and adapter['getterMethod'][0]==getter.index)
        routes[name]=dict(pair=pair,adapter=adapter,getterBytes='488B4110C3')
    for record in records:
        rows=[]
        for field in record['fields']:
            kind=field['kind'];name=field['declaredType']
            wire='raw16'if'component'in field else {'bool':'bool','enum':'i32','scalar64':'i64',
                'float32':'f32','string':'pool','list':'reference-list','object':'record'}.get(kind)
            need('finite-own-child-field-wire',wire is not None,(record['type'],field['name'],kind))
            rows.append(dict(name=field['name'],type=name,wire=wire))
            if wire=='record':
                need('own-finite-event-child',name==REFERENCES[2])
                usage=field['typedContext'];need('same-actual-reference-ReadValue',
                    usage['methodName']=='ReadValue'and usage['methodArguments']==[name])
        result['records'][record['type']]=rows
    result['records'][REFERENCES[3]]=[dict(name=r['fieldName'],type=r['declaredType'],
        wire='pool'if r['kind']=='byte-payload'else'vector3')for r in reads]
    collection_proofs={};parent=next(r for r in root_records if r['type']==PREFIX+'NPCMontageAnim')
    for field_name,element in LISTS.items():
        owner=next(r for r in records if r['type']==REFERENCES[1])if field_name=='extraEffects'else parent
        field,=[r for r in owner['fields']if r['name']==field_name]
        usage=field['typedContext'];actual=derive_typed_usage_context(image,usage['instructionRva'],label='npcMontageChildren.parent')
        need('same-actual-parent-MethodInfo',actual==usage)
        source=lists.derive_source(image,pins,typed_request=actual,call_target=base+field['targetRva'],element_type=element)
        witness,_=lists.verify_source(source,pins)
        carrier,=witness['closedCarrier']['classArguments'];raw=bytes.fromhex(carrier['rawHex'])
        need('same-nominal-reference-element',raw[10:12]==bytes((18,0))
            and int.from_bytes(raw[:8],'little')==ctx.index.types[element].index and carrier['name']==element)
        collection_proofs[field_name]=dict(source=source,element=element,adapter=routes[element]['adapter'])
        target=next(r for r in result['records'][owner['type']]if r['name']==field_name)
        target.update(wire='reference-list',elementType=element,countLimit=4096)
    _publication_gate(image,pins)
    return dict(layout=result,records=records,extraSource=extra,poolSources=pool,
        referenceRoutes=routes,collections=collection_proofs,lifecycle=lifecycle,nativeInputs=pins)
