"""Finite current PolyLineShape profile; cached BVH children stay bounded."""
TYPE='Beyond.BeyondPolyLineShape'
TREE='Beyond.Simple2DBVHTree'
NODE='Beyond.Simple2DBVHTreeNode'
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
CAP='story-polyline-shape'
LIMIT=4096
COLLECTIONS={
 LIST('int'):('story-polyline-int-list','int32-list','int',True,4),
 LIST('UnityEngine.Vector2'):('story-polyline-vector2-list','vector2-list','UnityEngine.Vector2',True,8),
 LIST(NODE):('story-polyline-bvh-empty','empty-reference-list',NODE,False,None),
 LIST(LIST('UnityEngine.Vector2')):('story-polyline-convex-empty','empty-reference-list',LIST('UnityEngine.Vector2'),False,None)}
NULL_CAP='story-polyline-tree-null'
PLAN=(('m_baseHeightOffset','float','float32-bits'),('m_BVHNodeRightChildIndex',LIST('int'),'int32-list'),
 ('m_BVHNodes',LIST(NODE),'empty-reference-list'),('m_checkedConvex','bool','bool-byte'),
 ('m_convexPolygons',LIST(LIST('UnityEngine.Vector2')),'empty-reference-list'),('m_height','float','float32-bits'),
 ('m_isClockWise','bool','bool-byte'),('m_isDirty','bool','bool-byte'),
 ('m_position','UnityEngine.Vector3','unity-vector3-raw12'),('m_posList',LIST('UnityEngine.Vector2'),'vector2-list'),
 ('m_rotation','UnityEngine.Vector3','unity-vector3-raw12'),('m_tree',TREE,'null-reference'))


def bind_collection(pins,join,child,capability):
    declared=join['typeName'];expected=COLLECTIONS.get(declared);usage=join['typedRequest']
    cap=child.get('capabilities',{}).get(capability,{})
    if (expected is None or capability!=expected[0]or child.get('nativeInputs')!=pins
            or(cap.get('typeName'),cap.get('elementType'),cap.get('elementWireBytes'))!=(declared,expected[2],expected[4])
            or cap.get('nullable')is not True or cap.get('positiveCountsAdmitted')is not expected[3]
            or type(cap.get('countLimit'))is not int or cap['countLimit']!=(LIMIT if expected[3]else 0)
            or cap.get('collectionCounts')!=[-1,0]or any(type(n)is not int for n in cap['collectionCounts'])
            or cap.get('actualCallbackEqualsProvedChildRequired')is not True
            or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[declared]
            or any(type(cap.get(k))is not int for k in('readerMethodDefinition','sourceTargetRva'))
            or(cap['readerMethodDefinition'],cap['sourceTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentPolyline.exact-independent-collection:'+declared)
    return dict(fieldName=join['fieldName'],typeName=declared,capability=capability,
        readerMethodDefinition=cap['readerMethodDefinition'],sourceTargetRva=cap['sourceTargetRva'],
        countLimit=cap['countLimit'],positiveCountsAdmitted=cap['positiveCountsAdmitted'],
        actualCallbackEqualsProvedChildRequired=True)


def bind_null(pins,join,child,capability):
    cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
    if (capability!=NULL_CAP or child.get('nativeInputs')!=pins or join['typeName']!=TREE
            or cap.get('typeName')!=TREE or cap.get('nullAdmitted')is not True or cap.get('positiveAdmitted')is not False
            or type(cap.get('nullMarker'))is not int or cap['nullMarker']!=255
            or type(cap.get('consumedBytes'))is not int or cap['consumedBytes']!=1
            or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[TREE]
            or(cap.get('referenceReaderMethodDefinition'),cap.get('referenceReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
        raise ValueError('currentPolyline.exact-independent-Tree-FF')
    return dict(fieldName=join['fieldName'],typeName=TREE,capability=capability,
        readerMethodDefinition=cap['referenceReaderMethodDefinition'],sourceTargetRva=cap['referenceReaderTargetRva'],
        positiveAdmitted=False,nullMarker=255,consumedBytes=1)


def derive(image,pins):
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data import levelscript_int_list_native as int_list
    from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.leveldata_vector2_list_sources import derive_collection
    from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component,_load
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda k,e,a:scalar.need('currentPolyline',k,e,a)
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
    source=generated_reader_sources.derive(image,pins,wrapper.name)
    need('exact-finite-declarations',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    tree=derive_reference_null(image,pins,TREE);proofs={};caps={};requests={};children={};collections={}
    int_raw=int_list.CONTRACT_PATH.read_bytes();int_fact=_load(int_list.CONTRACT_PATH.name,pins)
    int_list._validate_native(image,int_fact)
    # This separate value-list proof also authenticates the actual reference
    # ReadPackable helper used by each typed child collection request.
    read=next(r for r in source['orderedSourceReads']if r['fieldName']=='m_posList')
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentPolyline.Vector2')
    vectors=derive_collection(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'])
    reference=vectors['context'];need('independent-Vector2-wire',(8,8,4),
        (vectors['capability']['managedElementBytes'],vectors['capability']['elementWireBytes'],vectors['capability']['headerBytes']))
    for read in source['orderedSourceReads']:
        declared=read['declaredType'];index=read['memberIndex']
        if declared not in COLLECTIONS and declared!=TREE:continue
        usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentPolyline.child')
        requests[index]=usage
        if declared==TREE:
            bind_typed_read(image,usage,method_name='ReadValue',argument=TREE,kind=18,reference=True)
            need('actual-Tree-parent',(read['sourceTargetRva'],usage['methodSpec'][0]),
                (tree['referenceReaderTargetRva'],tree['referenceReaderMethodDefinition']))
            continue
        key,wire,element,positive,width=COLLECTIONS[declared]
        bind_typed_read(image,usage,method_name='ReadPackable',argument=declared,kind=21,reference=True)
        need('actual-collection-helper',(read['sourceTargetRva'],usage['methodSpec'][0]),
            (reference['callTargetRva'],reference['typedRequest']['methodSpec'][0]))
        if element=='int':
            argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
            carrier=ContextSymbols(image).type(argument.type_pointer_va);arg,=carrier['classArguments']
            need('actual-Int32-element',('int',b'\x08\x80'),(arg['name'],bytes.fromhex(arg['rawHex'])[10:12]))
            proof=dict(closedCarrier=carrier,sourceContract=int_list.CONTRACT_PATH.name,source=int_fact)
        elif element=='UnityEngine.Vector2':proof=vectors
        else:proof=derive_reference_list_component(image,pins,typed_request=usage,
            call_target=base+read['sourceTargetRva'],element_type=element,count_limit=0)
        cap=dict(typeName=declared,elementType=element,nullable=True,collectionCounts=[-1,0],
            countLimit=LIMIT if positive else 0,positiveCountsAdmitted=positive,elementWireBytes=width,
            readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'],
            actualCallbackEqualsProvedChildRequired=True)
        collections[declared]=(key,wire,key);children[index]=dict(nativeInputs=pins,capabilities={key:cap})
        caps[key]=cap;proofs[read['fieldName']]=dict(source=read,typedRequest=usage,component=proof)
    program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},
        references={TREE:(NULL_CAP,'null-reference',NULL_CAP)},reference_children={TREE:dict(nativeInputs=pins,capabilities={NULL_CAP:tree})},
        collections=collections,collection_children=children,typed_requests=requests,
        collection_binder=bind_collection,reference_binder=bind_null)
    need('complete-finite-program',[],pending)
    need('exact-finite-wire-order',[(n,k)for n,t,k in PLAN],[(r['fieldName'],r['kind'])for r in program['reads']])
    pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
    need('complete-owned-GetValue',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
    need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
    need('same-owned-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
    need('Int32-declaration-bookend',int_raw,int_list.CONTRACT_PATH.read_bytes())
    cap=dict(typeName=TYPE,memberCount=len(PLAN),program=program,collections=caps,
        nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,
        finiteFloatProfile=True,actualCallbackEqualsProvedChildRequired=True,
        positiveBvhNodesAdmitted=False,positiveConvexPolygonsAdmitted=False,positiveTreeAdmitted=False,
        referenceReaderMethodDefinition=tree['referenceReaderMethodDefinition'],referenceReaderTargetRva=tree['referenceReaderTargetRva'],
        liveFormatterSelectionObserved=False)
    return json.loads(json.dumps(dict(nativeInputs=pins,source=source,pair=pair,adapter=adapter,children=proofs,
        nullTree=tree,capability=cap,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
