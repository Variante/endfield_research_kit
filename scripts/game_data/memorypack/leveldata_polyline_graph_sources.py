"""Finite current Polyline/Tree/Node sources with explicit recursive edges.

The recursive nominal grammar is closed only after every whole reader, field
transfer, Original adapter and list callback is independently joined. FF is
the recursion base; positive records always consume a header and Node bounds.
Runtime provider choices and geometry interpretation are not observed.
"""
TYPE='Beyond.BeyondPolyLineShape'
TREE='Beyond.Simple2DBVHTree'
NODE='Beyond.Simple2DBVHTreeNode'
VECTOR='UnityEngine.Vector2'
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
LIMIT=4096
CAP='story-polyline-positive-graph'
SCHEMA='endfield.story-polyline-positive-graph.v2'
PLANS={
 TYPE:(('m_baseHeightOffset','float'),('m_BVHNodeRightChildIndex',LIST('int')),
       ('m_BVHNodes',LIST(NODE)),('m_checkedConvex','bool'),('m_convexPolygons',LIST(LIST(VECTOR))),
       ('m_height','float'),('m_isClockWise','bool'),('m_isDirty','bool'),('m_position','UnityEngine.Vector3'),
       ('m_posList',LIST(VECTOR)),('m_rotation','UnityEngine.Vector3'),('m_tree',TREE)),
 TREE:(('root',NODE),),
 NODE:(('bounds','Beyond.AABB'),('left',NODE),('right',NODE),('segments',LIST(VECTOR))),
}


def need(check,condition,detail=None):
    if not condition:raise ValueError('polylinePositiveGraph.'+check+':'+str(detail)[:1600])


def derive_sources(image,pins):
    """Fresh raw source obligations; this function grants no wire grammar."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources as reader,wrapper_members
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
    from scripts.game_data.memorypack import leveldata_int_list_sources as integers
    from scripts.game_data.memorypack import leveldata_vector2_list_sources as vectors
    from scripts.game_data.memorypack import reference_list_value_sources as references
    _publication_gate(image,pins);wrappers=wrapper_members.derive_from_image(image);records={};collections={}
    for name,plan in PLANS.items():
        wrapper,=[w for w in wrappers.values()if w.wrapped_type==name]
        source=reader.derive(image,pins,wrapper.name)
        need('exact-own-ordered-fields',[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']]==list(plan),name)
        pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrapper)
        need('same-complete-GetValue',source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True
            and source['lifecycle']['GetValue']['method']==adapter['getterMethod'],name)
        need('same-owned-slot5',source['lifecycle']['concreteFormatter']['method'][0]
            ==pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'],name)
        records[name]=dict(source=source,pair=pair,adapter=adapter,referenceSource=derive_reference_null(image,pins,name))
    full=records[TYPE]['source'];base=image.pe.image_base
    for read in full['orderedSourceReads']:
        name=read['declaredType']
        if not name.startswith('System.Collections.Generic.List`1<'):continue
        actual=derive_typed_usage_context(image,read['context']['instructionRva'],label='polylinePositiveGraph.list')
        kwargs=dict(typed_request=actual,call_target=base+read['sourceTargetRva'],count_limit=LIMIT)
        if name==LIST('int'):child=integers.derive(image,pins,**kwargs)
        elif name==LIST(VECTOR):child=vectors.derive_collection(image,pins,**kwargs)
        else:child=references.derive_source(image,pins,element_type=name[len('System.Collections.Generic.List`1<'):-1],**kwargs)
        collections[name]=dict(typedRequest=actual,sourceTargetRva=read['sourceTargetRva'],source=child)
    _publication_gate(image,pins)
    return dict(nativeInputs=pins,records=records,collections=collections,wireGrammarAdmitted=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)
