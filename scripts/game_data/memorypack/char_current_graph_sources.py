"""Fresh finite CharInteract dependency graph; no generated report is an input."""
from scripts.game_data.memorypack.char_union_sources import TYPE,NESTED,PREFIX


def need(check,condition,detail=None):
    if not condition:raise ValueError('charCurrentGraph.'+check+':'+str(detail)[:1600])


def derive(image,pins,*,pooled_capability,stage=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources as reader,char_record_components as records
    from scripts.game_data.memorypack import char_current_root_sources as roots,char_current_components as root_components
    from scripts.game_data.memorypack import char_union_sources as transports,char_union_components as unions
    from scripts.game_data.memorypack import char_reference_lists as references,char_value_lists as values
    from scripts.game_data.memorypack import char_reference_records as reference_records
    from scripts.game_data.memorypack import body_type_value_components as body,alpha_blend_value_bindings as alpha
    from scripts.game_data.memorypack import animation_transform_desc_components as transform
    from scripts.game_data.memorypack import char_static_dictionary_components as dictionaries,char_tag_dictionary_components as tags
    _publication_gate(image,pins)
    need('one-explicit-fresh-pool-capability',pooled_capability.get('wholeGrammarAdmitted')is True
        and pooled_capability.get('encoding')=='int32-pool-index'and pooled_capability.get('wireBytes')==4)
    need('callable-progress',stage is None or callable(stage))
    def progress(name,**data):
        if stage is not None:stage(dict(stage=name,**data))
    progress('char-root-source');root=roots.derive(image,pins)
    progress('char-record-sources');sources=records.derive_sources(image,pins,stage=stage)
    progress('char-union-sources');transport=transports.derive(image,pins)
    nested={r['wrappedType']:r for r in transport['nestedTransports']['owners']}
    need('all-eight-exact-nested-transports',set(nested)==set(NESTED)
        and all(r['status']=='complete-nested-union-transport-source'for r in nested.values()))
    ordinary={r['typeName']:r['proof']for r in transport['outcomes']if r['status']=='complete-union-source-and-adapter'}
    need('both-list-element-Original-adapters',set(NESTED[-2:])<=set(ordinary))
    base=image.pe.image_base;record_cache={};union_cache={};list_cache={};other_cache={};active=set()
    def usage(full,index):
        r=full['orderedSourceReads'][index]
        return derive_typed_usage_context(image,r['context']['instructionRva'],label='charCurrentGraph.actual-child'),base+r['sourceTargetRva']
    def root_request(name):
        row,=[r for r in root['requests']if r['fieldName']==name]
        return row['typedRequest'],base+row['sourceTargetRva']
    def once(cache,key,build):
        if key not in cache:
            token=(id(cache),key);need('acyclic-exact-owner-dependencies',token not in active,key);active.add(token)
            try:cache[key]=build()
            finally:active.remove(token)
        return cache[key]
    def value(name,full,index):
        if name=='Beyond.Gameplay.BodyTypeDef':return once(other_cache,'body-type-value',lambda:body.derive(image,pins))
        need('finite-own-managed-value',name=='Beyond.Gameplay.View.Animation.AlphaBlend',name)
        # Each outer ordinary/closed source is independently joined by this
        # owner; the complete resulting semantic capability must still agree.
        return alpha.derive(image,pins,parent_source=full,member_index=index)['proof']['childComponent']
    def reference(name):
        if name==reference_records.TRANSFORM:
            def build_transform():
                wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==name]
                return transform.derive(image,pins,source=reader.derive(image,pins,wrapper.name))
            return once(other_cache,name,build_transform)
        if name==reference_records.CURVE:return once(other_cache,name,lambda:reference_records.derive_curve(image,pins))
        need('finite-own-NPC-reference',name==reference_records.NPC,name);return record(name)
    def reference_list(name):
        need('finite-own-reference-element',name in references.TYPES,name)
        def build():
            child=None if name=='string'else record(name)if name==PREFIX+'CharInteractPerformActor'else union(name)
            if name in(TYPE,PREFIX+'CharInteractPerformActor','string'):
                call={'string':'inheritPerformIds',TYPE:'loopActions',PREFIX+'CharInteractPerformActor':'chars'}[name]
                actual,target=root_request(call)
            else:
                parent,index={PREFIX+'SubSpecialPerformEntry':(PREFIX+'SubSpecialPerformEntryData',0),
                    PREFIX+'SpecialSubPerformCondition':(PREFIX+'LoopSubSpecialPerformEntry',0)}[name]
                actual,target=usage(sources[parent],index)
            return references.derive(image,pins,typed_request=actual,call_target=target,element_type=name,element_component=child)
        return once(list_cache,('reference',name),build)
    def value_list(name):
        need('finite-own-value-element',name in values.TYPES,name)
        def build():
            actual,target=usage(sources[PREFIX+'CharWeaponShowActData'],17)if name=='int'else root_request(
                'activeTags'if name==values.TAG else'interruptReasons')
            return values.derive(image,pins,element_type=name,typed_request=actual,call_target=target)
        return once(list_cache,('value',name),build)
    def ordinary_bind(full,scope,read,pins,actual,component,capability):
        if read['declaredType']=='System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.Core.GameplayTag>':
            return tags.bind_member(full,scope,read,pins,actual,component,capability)
        return reference_records.bind_member(full,scope,read,pins,actual,component,capability)
    def collection_bind(full,scope,read,pins,actual,component,capability):
        owner=references if component.get('schema')==references.SCHEMA else values
        return owner.bind_member(full,scope,read,pins,actual,component,capability)
    def record(name):
        need('finite-own-concrete-record',name in records.PLANS,name)
        def build():
            progress('char-record-grammar',typeName=name,index=len(record_cache),total=len(records.PLANS))
            full=sources[name];managed={};ref_children={};ref_ops={};collection_children={};collection_ops={}
            for read in full['orderedSourceReads']:
                index=read['memberIndex'];typ=read['declaredType'];kind=read['kind']
                if kind.startswith('managed:'):
                    managed[index]=value(typ,full,index)
                elif kind.startswith('reference:'):
                    if typ.startswith('System.Collections.Generic.List`1<'):
                        element=typ[len('System.Collections.Generic.List`1<'):-1]
                        child=reference_list(element)if element in references.TYPES else value_list(element)
                        capability=child['capability'];wire=references.WIRE if element in references.TYPES else values.WIRE
                        collection_children[index]=child;collection_ops[typ]=(capability,wire,capability)
                    else:
                        if typ=='System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.Core.GameplayTag>':
                            child=once(other_cache,typ,lambda:tags.derive_member(image,pins,parent_source=full,member_index=index));wire=tags.WIRE
                        else:
                            child=reference(typ);wire=transform.WIRE if typ==transform.TYPE else reference_records.WIRE if typ==reference_records.CURVE else records.WIRE
                        capability=transform.CAPABILITY if typ==transform.TYPE else child['capability']
                        ref_children[index]=child;ref_ops[typ]=(capability,wire,capability)
            children=dict(value_children=managed,reference_children=ref_children,reference_operations=ref_ops,
                reference_binder=ordinary_bind,collection_children=collection_children,collection_operations=collection_ops,
                collection_binder=collection_bind)
            result=records.derive_selected(image,pins,sources={name:full},children={name:children});owner,=result['owners']
            need('complete-own-concrete-record',owner.get('status')=='validated-conditional-char-interact-record-components',
                dict(typeName=name,reason=owner.get('reason'),pending=owner.get('proof',{}).get('pending')))
            return owner['proof']
        return once(record_cache,name,build)
    def union(name):
        need('finite-own-abstract-union',name in(TYPE,)+NESTED,name)
        def build():
            progress('char-union-grammar',typeName=name)
            selected=transport['top']if name==TYPE else ordinary.get(name,dict(nativeInputs=pins,source=nested[name]))
            rows=transport['top']['families']['char-animation']['selectedRoutes']if name==TYPE else nested[name]['cases']
            children={r['wrappedType']:union(r['wrappedType'])if r['wrappedType']in NESTED else record(r['wrappedType'])for r in rows}
            return unions.compose(selected,children,pins)
        return once(union_cache,name,build)
    root_children={}
    for row in root['requests']:
        typ=row['typeName']
        if row['mode']!='reference':continue
        if typ.startswith('System.Collections.Generic.List`1<'):
            element=typ[len('System.Collections.Generic.List`1<'):-1]
            root_children[typ]=reference_list(element)if element in references.TYPES else value_list(element)
        else:root_children[typ]=record(typ)
    progress('char-root-static-dictionaries')
    dictionary_children={row['typeName']:record(PREFIX+('BodyTypeActData'if row['fieldName']=='bodyTypeActDataDict'else'SubSpecialPerformEntryData'))
        for row in root['requests']if row['mode']=='out8'}
    static=dictionaries.derive(image,pins,root=root,value_children=dictionary_children)
    for row in static['owners']:
        need('whole-own-static-dictionary',row.get('status')!='pendingReview',row.get('reason'))
        root_children[row['typeName']]=row['proof']
    need('all-finite-concrete-records-and-unions-reached',set(record_cache)==set(records.PLANS)
        and set(union_cache)=={TYPE,*NESTED},dict(records=sorted(set(records.PLANS)-set(record_cache)),unions=sorted({TYPE,*NESTED}-set(union_cache))))
    progress('char-whole-root-composition')
    result=root_components.compose(root,root_children,pins,pooled_capability=pooled_capability)
    summary=dict(concreteRecords=len(record_cache),abstractUnions=len(union_cache),referenceAndValueListTypes=len(list_cache),
        staticDictionaries=len(static['owners']),generatedReportsRead=False)
    _publication_gate(image,pins);progress('char-current-graph-complete',**summary)
    return result
