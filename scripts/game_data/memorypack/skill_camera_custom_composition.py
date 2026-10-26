"""Pure complete CustomConfig descendant join; never a native admission gate.

Fresh source owners supply the component and independently selected operation
capabilities. This joins every finite child/list/ordinary context before making
a new mapping. It neither mutates caller mappings nor authenticates source
bytes, observes runtime selection, or grants enclosing owner/EOF authority.
"""
from scripts.game_data.memorypack import skill_camera_custom_components as custom
from scripts.game_data.memorypack import skill_camera_custom_codec as codec
from scripts.game_data.memorypack import skill_camera_module_components as modules
from scripts.game_data.memorypack import skill_camera_module_codec as module_codec
from scripts.game_data.memorypack import skill_camera_module_list_sources as module_lists
from scripts.game_data.memorypack import skill_camera_transition_sources as transitions
from scripts.game_data.memorypack import skill_camera_transition_codec as transition_codec
from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability as require_curve
from scripts.game_data.memorypack.skill_enum_list_codec import require_capability as require_enum
from scripts.game_data.memorypack.skill_action_reference_list_sources import compose_reference_list
from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value


def need(check,condition):
    if not condition:raise ValueError('skillCameraCustomComposition.'+check)


def _scope(value,pins,schema,status):
    need('same-source-scope:'+schema,value.get('schema')==schema and value.get('status')==status
        and value.get('nativeInputs')==pins)


def _reader(cap,source):
    need('exact-own-ordinary-reader',all(type(cap.get(k))is int and cap[k]>0 and cap[k]==source.get(k)
        for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')))


def _list_reader(collection,proof,element):
    witness=collection['witnessComponent'];reader=proof['listElementReaderBinding']
    need('same-independent-list-element-reader',
        witness['referenceSource']['valueContext']['readerMethodDefinition']==element['referenceReaderMethodDefinition']
        and reader['callbackReaderMethodDefinition']==element['referenceReaderMethodDefinition']
        and reader['actualOptimizedReaderTargetRva']==element['referenceReaderTargetRva']
        and reader.get('canonicalPointerEqualityClaimed')is False
        and reader['actualReadValue']['equivalentMethod'][0]==element['referenceReaderMethodDefinition']
        and reader['actualReadValue']['targetRva']==element['referenceReaderTargetRva'])


def _module_graph(graph,pins,curve):
    _scope(graph,pins,modules.SCHEMA,'validated-conditional-camera-module-components')
    expected={modules.CAPABILITY,*[r['capability']for r in modules.RECORDS.values()]}
    need('exact-module-graph-capabilities',set(graph['capabilities'])==expected and graph.get('wholeOwnerAdmitted')is False)
    union=module_codec.require_union(graph['capabilities'][modules.CAPABILITY]);proof=graph['proof'];native=proof['union']
    _scope(native,pins,modules.union_source.SCHEMA,'validated-conditional-camera-module-source')
    need('exact-module-base-source',native.get('nativeInputs')==pins and native.get('baseGetterSemanticsAdmitted')is True
        and all(native.get(k)is False for k in('concreteGetterSemanticsAdmitted','concreteFactorySemanticsAdmitted',
            'concreteChildGrammarAdmitted','wholeUnionAdmitted','wholeOwnerAdmitted')))
    routes=native['programs'];need('all-thirteen-source-routes',len(routes)==13
        and [r.get('tag')for r in routes]==list(range(13))and all(type(r.get('tag'))is int for r in routes)
        and set(proof['concreteRecords'])==set(modules.RECORDS))
    expected_routes=[]
    for route in routes:
        nominal=route['wrappedType'];record=proof['concreteRecords'][nominal]
        cap=modules.bind_child(route,record['source'],record['compiled'],pins)
        key=modules.RECORDS[nominal]['capability'];module_codec.require_record(graph['capabilities'][key],key)
        need('same-complete-module-record:'+key,cap==graph['capabilities'][key])
        expected_routes.append(dict(tag=route['tag'],wrappedType=nominal,wrapperName=route['wrapperName'],childCapability=key))
        for binding in record['compiled'].get('childBindings',[]):
            need('same-full-module-curve-identity',binding['readerMethodDefinition']==curve['referenceReaderMethodDefinition']
                and binding['sourceTargetRva']==curve['referenceReaderTargetRva'])
    need('same-thirteen-source-owned-union-routes',union['routes']==expected_routes)
    _reader(union,proof['referenceReader'])
    need('same-base-source-reader-definition',union['referenceReaderMethodDefinition']==
        native['proof']['referencePackable']['valueContext']['readerMethodDefinition'])
    identity={k:curve[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
    need('module-exact-external-curve',graph.get('requiredExternalCapabilities')==['curve-profile']
        and graph.get('requiredExternalCapabilityIdentities')=={'curve-profile':identity}
        and proof['curve'].get('nativeInputs')==pins and proof['curve']['capabilities']=={'curve-profile':curve})


def _transition_graph(graph,pins):
    _scope(graph,pins,'endfield.skill-camera-transition-sources.v1','validated-conditional-camera-transitions')
    need('exact-transition-scope',set(graph['capabilities'])=={transitions.LEAF,transitions.INNER_LIST,transitions.CAPABILITY}
        and graph.get('parentFieldAdmitted')is False and graph.get('wholeOwnerAdmitted')is False
        and graph.get('requiredExternalCapabilities')==['byte-payload'])
    caps=graph['capabilities'];transition_codec.require_leaf(caps[transitions.LEAF])
    transition_codec.require_and(caps[transitions.CAPABILITY]);transition_codec.require_collection(caps[transitions.INNER_LIST],outer=False)
    proof=graph['proof'];condition=proof['condition'];inner=proof['inner'];transitions.require_source(proof['source'],pins)
    from scripts.game_data.memorypack import skill_action_reference_components as leaf_owner
    _scope(condition,pins,leaf_owner.SCHEMA,'validated-conditional-action-reference-components')
    need('exact-leaf-source-record-scope',set(condition['proof']['records'])=={transitions.CONDITION}
        and condition.get('requiredExternalCapabilities')==['byte-payload']and condition.get('wholeSkillDataAdmitted')is False)
    leaf=condition['proof']['records'][transitions.CONDITION]
    leaf_owner.require_record_scope(leaf['source'],pins,transitions.CONDITION)
    need('same-full-leaf-compiled-program',leaf_owner.bind_program(transitions.CONDITION,leaf['compiled'])==caps[transitions.LEAF]['orderedReads'])
    _reader(caps[transitions.LEAF],condition['proof']['referenceReaders'])
    need('same-full-leaf-adapter-source',leaf['adapter']['getterMethod']==leaf['source']['lifecycle']['GetValue']['method']
        and leaf['adapter']['pairForwarder']['readerMethod']==leaf['source']['method'])
    transitions.bind_program(proof['compiled']);_reader(caps[transitions.CAPABILITY],proof['referenceReader'])
    need('same-full-condition-child',condition.get('nativeInputs')==pins
        and condition['capabilities']=={transitions.LEAF:caps[transitions.LEAF]}
        and inner.get('nativeInputs')==pins and inner['proof']['child']==condition
        and inner['capabilities']=={k:caps[k]for k in(transitions.LEAF,transitions.INNER_LIST)})
    collection=inner['proof']['collection'];_list_reader(collection,inner['proof'],caps[transitions.LEAF])
    derived=compose_reference_list(collection,condition,pins,element_type=transitions.CONDITION,
        element_capability=transitions.LEAF,label='camera-custom-inner-list')
    need('same-inner-list-source-program',derived==caps[transitions.INNER_LIST])
    read,=proof['source']['orderedSourceReads'];witness=collection['witnessComponent']
    usage=witness['typedRequest'];request=inner['proof']['actualParentRequestBinding']
    need('same-inner-actual-source-context',read['context']['instructionRva']==usage['instructionRva']
        and read['context']['methodSpec']==usage['methodSpec']and read['sourceTargetRva']==witness['callTargetRva']
        and request==dict(typedRequest=usage,callTargetRva=witness['callTargetRva']))
    joined=transitions.bind_inner(pins,dict(fieldName='and',typeName=read['declaredType'],typedRequest=usage,
        sourceTargetRva=read['sourceTargetRva']),inner,transitions.INNER_LIST)
    need('same-inner-compiled-binding',proof['compiled']['childBindings']==[joined])


def compose(component,pins,caps):
    """Return a new merged capability mapping only after every check succeeds."""
    _scope(component,pins,custom.SCHEMA,'validated-conditional-camera-custom-components')
    need('unadmitted-enclosing-owner',component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    own=codec.require_capability(component['capabilities'][custom.CAPABILITY]);proof=component['proof']
    source_owner=proof['ownSource'];_scope(source_owner,pins,custom.owner.SCHEMA,'proved-current-source-only')
    need('separate-own-source-and-grammar',source_owner.get('ordinarySourceAndAdapterProved')is True
        and source_owner.get('wholeGrammarAdmitted')is False and source_owner.get('wholeOwnerAdmitted')is False
        and source_owner.get('capabilities')=={} and(source_owner.get('typeName'),source_owner.get('wrapperName'))==(custom.TYPE,custom.WRAPPER))
    source=source_owner['proof']['source'];custom.bind_program(source,proof['compiled'],pins)
    need('same-custom-compiled-order',own['orderedReads']==proof['compiled']['reads'])
    _reader(own,source_owner['proof']['referenceReader'])
    adapter=source_owner['proof']['adapter']
    need('same-own-source-adapter-getter-and-reader',adapter['getterMethod']==source['lifecycle']['GetValue']['method']
        and adapter['pairForwarder']['readerMethod']==source['method'])
    curve=require_curve(caps['curve-profile'])
    pool=caps.get('byte-payload',{})
    need('explicit-pooled-index-domain',pool.get('wholeGrammarAdmitted')is True and pool.get('encoding')=='int32-pool-index'
        and type(pool.get('emptyIndex'))is int and pool['emptyIndex']==-1
        and type(pool.get('nullIndex'))is int and pool['nullIndex']==-2)
    need('full-fresh-external-curve-shape',component.get('requiredExternalCapabilities')==['byte-payload','curve-profile']
        and component.get('requiredExternalCapabilityShapes')=={'curve-profile':curve}
        and proof['curve'].get('nativeInputs')==pins and proof['curve']['capabilities']=={'curve-profile':curve})
    _module_graph(proof['moduleGraph'],pins,curve);_transition_graph(proof['transitionGraph'],pins)
    enums=proof['enumSource'];_scope(enums,pins,'endfield.nominal-enum-list-sources.v1','validated-conditional-nominal-enum-lists')
    enum_list=enums['capabilities'][custom.ENUM_LIST];enum_element=enums['capabilities'][custom.ENUM_ELEMENT]
    require_enum(enum_list,enum_element,name=custom.owner.ENUM)
    need('own-enum-native-inputs',enum_list.get('nativeInputs')==pins and enum_element.get('nativeInputs')==pins)
    expected={custom.CAPABILITY,custom.ENUM_LIST,custom.ENUM_ELEMENT,modules.LIST,transitions.LIST,
        *proof['moduleGraph']['capabilities'],*proof['transitionGraph']['capabilities']}
    need('exact-complete-descendant-scope',set(component['capabilities'])==expected
        and set(proof['collections'])=={'15','19','25','26'})
    derived={custom.CAPABILITY:own,custom.ENUM_LIST:enum_list,custom.ENUM_ELEMENT:enum_element,
        **proof['moduleGraph']['capabilities'],**proof['transitionGraph']['capabilities']}
    bindings={b['fieldName']:b for b in proof['compiled']['childBindings']}
    for index,read in enumerate(source['orderedSourceReads']):
        nominal=read['declaredType']
        if nominal!=custom.owner.CURVE and nominal not in custom.COLLECTIONS:continue
        key=str(index);usage=proof['typedRequests'][key]if key in proof['typedRequests']else proof['typedRequests'][index]
        need('same-every-actual-child-context:'+key,read['context']['instructionRva']==usage['instructionRva']
            and read['context']['methodSpec']==usage['methodSpec'])
        join=dict(fieldName=read['fieldName'],typeName=nominal,typedRequest=usage,sourceTargetRva=read['sourceTargetRva'])
        if nominal==custom.owner.CURVE:
            binding=bind_read_value(pins,join,proof['curve'],'curve-profile')
        else:
            child=proof['collections'][key];capability=custom.COLLECTIONS[nominal][0]
            binding=custom.bind_collection(pins,join,child,capability)
            if index==15:
                need('same-full-enum-source',child['proof']['source']==enums
                    and child['capabilities']=={custom.ENUM_LIST:enum_list,custom.ENUM_ELEMENT:enum_element})
            elif index==26:
                need('same-full-module-graph',child['proof']['union']==proof['moduleGraph'])
                derived_list=module_lists.compose(child['proof']['collection'],proof['moduleGraph'],pins)
                need('same-module-list-source',derived_list==child['capabilities'][modules.LIST])
                _list_reader(child['proof']['collection'],child['proof'],derived[modules.CAPABILITY])
            else:
                need('same-full-transition-graph',child['proof']['child']==proof['transitionGraph'])
                derived_list=compose_reference_list(child['proof']['collection'],proof['transitionGraph'],pins,
                    element_type=transitions.TYPE,element_capability=transitions.CAPABILITY,label='camera-custom-outer-list')
                need('same-outer-list-source',derived_list==child['capabilities'][transitions.LIST])
                _list_reader(child['proof']['collection'],child['proof'],derived[transitions.CAPABILITY])
            for name,cap in child['capabilities'].items():
                need('identical-child-overlap:'+name,name not in derived or derived[name]==cap);derived[name]=cap
        need('same-every-compiled-child-binding:'+key,binding==bindings[read['fieldName']])
    need('same-complete-derived-capabilities',derived==component['capabilities'])
    for name,cap in derived.items():need('identical-existing-operation-capability:'+name,name not in caps or caps[name]==cap)
    return{**caps,**derived}
