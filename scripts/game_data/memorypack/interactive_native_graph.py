"""Fresh native field and child obligations for Interactive and action values.

This graph owns native programs only. A sequential reader must separately
consume each selected child, its exact header/count domain and physical EOF.
Unsupported children have no null-marker fallback. No saved source declaration
or diagnostic JSON is accepted by this operation.
"""
import json

from scripts.game_data.memorypack import interactive_parent_bindings as parent

ROOT='Beyond.Gameplay.InteractiveTemplateData'
PREFIX='Beyond.Gameplay.Actions.Param'


def need(check,condition,detail=''):
    if not condition:raise ValueError('interactiveNativeGraph.'+check+':'+str(detail)[:1600])


class InteractiveNativeGraph:
    def __init__(self,image,pins,*,action_owner=None):
        self.image=image;self.pins=dict(pins);self.active=False;self.action_owner=action_owner

    def __enter__(self):
        from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
        from scripts.game_data.memorypack.generated_action_sources import _source_preparation_scope,_prepare
        _publication_gate(self.image,self.pins)
        need('one-active-source-epoch',not self.active)
        self.scope=_source_preparation_scope(self.image,self.pins);self.scope.__enter__()
        try:
            self.targets,self.barrier,self.disabled=_prepare(self.image,self.pins)
            inventory=list(self.image.memorypack_wrappers.values())
            self.wrappers={w.name:w for w in inventory};self.by_type={}
            for w in inventory:
                need('unique-exact-wrapped-nominal',w.wrapped_type not in self.by_type,w.wrapped_type)
                self.by_type[w.wrapped_type]=w
            self.records={};self.transports={};self.members={};self.getters={};self.callbacks={};self.leaves={}
            self._action_switches={};self._action_cases={}
            self._readers=None;self._enum=None;self._params={};self._param_graph=None;self._components=None
            self._layouts=None
            self.active=True
            return self
        except BaseException:
            import sys
            self.scope.__exit__(*sys.exc_info());raise

    def __exit__(self,*error):
        from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
        try:_publication_gate(self.image,self.pins)
        finally:
            self.active=False;self.scope.__exit__(*error)

    def _active(self):need('active-fresh-source-epoch',self.active)

    def value_layouts(self):
        """Name raw fields once per selected native graph, without wire authority."""
        from scripts.game_data.memorypack.stored_value_layouts import StoredValueLayouts
        self._active()
        if self._layouts is None:self._layouts=StoredValueLayouts(self.image)
        need('same-selected-layout-image',self._layouts.image is self.image)
        return self._layouts

    def reference_readers(self):
        from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
        self._active()
        if self._readers is None:self._readers=reference_reader_abi(self.image,self.pins)
        return self._readers

    def record(self,name):
        from scripts.game_data.memorypack.generated_reader_sources import _derive
        from scripts.game_data.memorypack.generated_record_components import compile_member_program
        from scripts.game_data.memorypack import buff_gameplay_tag_native,buff_layer_mask_native
        self._active()
        if name in self.records:return self.records[name]
        need('selected-exact-wrapper',name in self.by_type,name)
        wrapper=self.by_type[name]
        # Match the public generated-reader declaration boundary. Native
        # parsers use tuple instruction pairs internally; pure component
        # contracts deliberately compare their JSON list representation.
        source=json.loads(json.dumps(_derive(self.image,self.pins,wrapper,self.wrappers,
            self.targets,self.barrier,self.disabled,self.getters)))
        scope=source.get('sourceScope',{});value4={}
        for read in source['orderedSourceReads']:
            if not read['kind'].startswith('value4:'):continue
            typ=read['declaredType'];actual=scope.get('primitiveSources',{}).get(str(read['memberIndex']))
            if actual is None:
                module={'Beyond.Gameplay.Core.GameplayTag':buff_gameplay_tag_native,
                    'UnityEngine.LayerMask':buff_layer_mask_native}.get(typ)
                if module is None:continue
                key=('atomic4',typ)
                if key not in self.leaves:self.leaves[key]=module.validate_on_image(self.image,self.pins)
                actual=self.leaves[key]
            value4[typ]=actual
        compiled,pending=compile_member_program(source,self.pins,wrapper_name=wrapper.name,type_name=name,
            value4=value4,value8={'UnityEngine.Vector2':scope.get('primitiveSources',{})})
        result=dict(source=source,pending={p['memberIndex']:p for p in pending},primitiveProgram=compiled)
        self.records[name]=result
        return result

    def original(self,name):
        from scripts.game_data.memorypack.interactive_object_sources import derive
        self._active()
        if name not in self.transports:
            self.transports[name]=derive(self.image,self.pins,self.record(name)['source'],
                reference_readers=self.reference_readers())
        return self.transports[name]

    def callback(self,name):
        from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_integer,derive_string
        self._active();need('finite-primitive-callback',name in('int','string'))
        if name not in self.callbacks:
            self.callbacks[name]=(derive_integer if name=='int'else derive_string)(self.image,self.pins)
        return self.callbacks[name]

    def enums(self):
        from scripts.game_data.memorypack.interactive_enum_sources import derive
        self._active()
        if self._enum is None:self._enum=derive(self.image,self.pins)
        return self._enum

    def parameters(self,name):
        from scripts.game_data.memorypack.interactive_param_sources import derive
        self._active()
        if name not in self._params:
            self._params[name]=derive(self.image,self.pins,parameter_types=[name])
        return self._params[name]

    def param_graph(self):
        from scripts.game_data.memorypack.levelscript_param_graph_sources import derive
        self._active()
        if self._param_graph is None:self._param_graph=derive(self.image,self.pins)
        return self._param_graph

    def components(self):
        from scripts.game_data.memorypack.interactive_component_union_sources import derive
        self._active()
        if self._components is None:self._components=derive(self.image,self.pins)
        return self._components

    def action_case(self,family,tag):
        from scripts.game_data.memorypack.levelscript_action_route_sources import BASES,_declaration,_join_source
        from scripts.game_data.memorypack.union_dispatch import read_union_switch
        self._active();need('finite-action-union-family',family in BASES,family)
        need('literal-action-union-tag',type(tag)is int and 0<=tag<=65535)
        key=(family,tag)
        if key in self._action_cases:return self._action_cases[key]
        if family not in self._action_switches:
            self._action_switches[family]=read_union_switch(self.image,BASES[family],
                wrappers={w.type_definition:w for w in self.wrappers.values()})
        switch=self._action_switches[family];entries=[r for r in switch['entries']if r['tag']==tag]
        need('one-actual-action-union-case',len(entries)==1,(family,tag));entry=entries[0]
        wrapper=self.wrappers[entry['wrapperName']]
        need('same-own-native-case-wrapper',wrapper.type_definition==entry['typeDefinition'])
        route=dict(family=family,tag=tag,**_declaration(wrapper),unionIdentity=dict(
            dispatcherVa=switch['dispatcherVa'],tableVa=switch['tableVa'],entryCount=switch['entryCount'],**entry))
        from scripts.game_data.memorypack import levelscript_manual_action_sources as manual
        if wrapper.name==manual.WRAPPER:
            proof=manual.derive(self.image,self.pins,wrapper=wrapper,wrappers=self.wrappers,
                barrier=self.barrier,getter_cache=self.getters,reference_readers=self.reference_readers())
            result=dict(family=family,tag=tag,wrapperName=wrapper.name,typeName=wrapper.wrapped_type,
                memberCount=proof['memberCount'],status='complete-manual-route-source-proved',
                unionIdentity=route['unionIdentity'],manualSource=proof,
                routeGrammarAdmitted=False,wholeOwnerAdmitted=False)
            self._action_cases[key]=result;return result
        source=self.record(wrapper.wrapped_type)['source']
        result=_join_source(route,source,self.pins)
        # The native table supplies only the conditional nominal assignment.
        # Own concrete static reads, slot-five callback and Original conversion
        # are independent obligations; the table alone grants none of them.
        result['originalConversion']=self.original(wrapper.wrapped_type)
        self._action_cases[key]=result
        return result

    def _external(self,name):
        from scripts.game_data.memorypack import skill_blackboard_double_sources as double
        from scripts.game_data.memorypack import skill_blackboard_vector3_sources as vector
        from scripts.game_data.memorypack import skill_animation_curve_sources as curve
        modules={double.TYPE:(double,'skill-blackboard-double'),
            vector.TYPE:(vector,'skill-blackboard-vector3'),curve.TYPE:(curve,curve.CAPABILITY)}
        need('finite-independent-record-owner',name in modules,name)
        if name not in self.leaves:
            module,key=modules[name]
            if module is vector:
                self.leaves[name]=vector._derive_on_double(self.image,self.pins,self._external(double.TYPE)[0])
            else:self.leaves[name]=module.derive(self.image,self.pins)
        module,key=modules[name]
        return self.leaves[name],self.leaves[name]['capabilities'][key]

    def _bind_external(self,source,read):
        from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
        proof,cap=self._external(read['declaredType']);binding=parent.bind_reference_result(source,read,self.pins)
        usage=parent.fresh_request(self.image,read)
        bind_typed_read(self.image,usage,method_name='ReadValue',argument=read['declaredType'],kind=18,reference=True)
        readers=proof.get('proof',{}).get('referenceReaders',{})
        definition=cap.get('referenceReaderMethodDefinition',readers.get('referenceReaderMethodDefinition'))
        target=cap.get('referenceReaderTargetRva',readers.get('referenceReaderTargetRva'))
        need('same-independent-external-reference-reader',definition==usage['methodSpec'][0]
            and target==read['sourceTargetRva'],read['declaredType'])
        return dict(operation='external-reference',typeName=read['declaredType'],proof=proof,capability=cap,binding=binding)

    def member(self,name,index):
        from scripts.game_data.memorypack import interactive_collection_sources as lists
        from scripts.game_data.memorypack import interactive_array_components as arrays
        from scripts.game_data.memorypack import interactive_optional_components as optional
        from scripts.game_data.memorypack import interactive_dictionary_components as dictionaries
        from scripts.game_data.memorypack import interactive_dictionary_children as dictionary_children
        from scripts.game_data.memorypack import interactive_audio_dictionary_sources as audio
        from scripts.game_data.memorypack import interactive_object_sources as objects
        from scripts.game_data.memorypack import pooled_source_helper
        self._active();key=(name,index)
        if key in self.members:return self.members[key]
        record=self.record(name);source=record['source'];scope=source.get('sourceScope',{})
        need('literal-ordered-parent-member',type(index)is int and 0<=index<len(source['orderedSourceReads']))
        read=source['orderedSourceReads'][index];typ=read['declaredType']
        if read['kind']=='byte-payload':
            target=read['sourceTargetRva'];slot=('pool',target)
            if slot not in self.leaves:self.leaves[slot]=pooled_source_helper.validate_on_image(
                self.image,self.image.pe.image_base+target,self.pins)
            result=dict(operation='pooled-string',typeName=typ,proof=self.leaves[slot])
        elif index not in record['pending']:
            result=dict(operation='primitive',typeName=typ,sourceRead=read)
        elif typ in('Beyond.Gameplay.Actions.Param`1<bool>[]','Beyond.Gameplay.Actions.Param`1<UnityEngine.Vector3>[]'):
            from scripts.game_data.memorypack import levelscript_boolean_param_array_sources as booleans
            from scripts.game_data.memorypack import levelscript_vector_param_array_sources as vectors
            module=booleans if typ==booleans.TYPE else vectors
            component=module.derive_member(self.image,self.pins,source,member_index=index)
            result=dict(operation='parameter-array',typeName=typ,proof=component,
                capability=module.validate_component(component,self.pins),boolean=module is booleans)
        elif typ=='Beyond.Gameplay.Actions.Param`1<Beyond.Gameplay.Core.EntityPtr>[]':
            from scripts.game_data.memorypack import levelscript_entity_param_array_sources as entity
            from scripts.game_data.codecs.levelscript.current_entity_param_array import validate
            from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
            need('own-Entity-array-parent',(name,index,read['fieldName'])==(entity.PARENT,7,'_list'))
            proof=scope['arraySources'][str(index)];cap=proof['capabilities'][entity.CAPABILITY];validate(cap)
            binding=parent.bind_reference_result(source,read,self.pins);usage=parent.fresh_request(self.image,read)
            bind_typed_read(self.image,usage,method_name='ReadArray',argument=entity.ELEMENT,kind=21,reference=True)
            need('own-actual-Entity-array-source',proof['nativeInputs']==self.pins
                and proof['proof']['actualRequest']==usage and proof['proof']['actualInstruction']==read['instruction']
                and cap['readerMethodDefinition']==usage['methodSpec'][0]and cap['sourceTargetRva']==read['sourceTargetRva'])
            result=dict(operation='parameter-array',typeName=typ,proof=proof,capability=cap,binding=binding,entity=True)
        elif typ.startswith(PREFIX)and typ.endswith('>'):
            from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
            proof=self.parameters(typ);cap=proof['capabilities'][typ]
            transfer=parent.bind_reference_result(source,read,self.pins);usage=parent.fresh_request(self.image,read)
            bind_typed_read(self.image,usage,method_name='ReadValue',argument=typ,kind=21,reference=True)
            need('same-own-Param-source',cap.get('readerMethodDefinition')==usage['methodSpec'][0]
                and cap.get('sourceTargetRva')==read['sourceTargetRva'])
            result=dict(operation='parameter',typeName=typ,proof=proof,capability=cap,binding=transfer)
        elif typ=='Beyond.LangKey':
            from scripts.game_data.memorypack import leveldata_lang_key_components as lang
            child=scope['managedValueSources'][str(index)]
            component=dict(schema='endfield.story-lang-key-component.v1',nativeInputs=self.pins,
                capabilities={lang.CAP:lang._capability(child)},proof=dict(readSource=child))
            usage=parent.fresh_request(self.image,read)
            binding=lang.bind_value(source,scope,read,self.pins,usage,component,lang.CAP)
            result=dict(operation='lang-key',typeName=typ,capability=component['capabilities'][lang.CAP],
                proof=component,binding=binding)
        elif typ.startswith(layout_optional_prefix()):
            result=dict(operation='managed-optional',typeName=typ,binding=optional.bind_member(source,read,self.pins),
                proof=scope['managedValueSources'][str(index)])
        elif typ.startswith(lists.HEAD):
            proof=lists.derive_member(self.image,self.pins,source,index,
                enum_source=self.enums()if typ=='System.Collections.Generic.List`1<Beyond.Gameplay.Core.EGameplayEvents>'else None)
            element=proof['elementType']
            if element=='Beyond.Gameplay.ParamKeyValue':self.param_graph()
            if element=='string':self.callback('string')
            result=dict(operation='collection',typeName=typ,proof=proof)
        elif typ.endswith('[]')and name==ROOT and index in arrays.FIELDS:
            binding=arrays.bind_member(source,read,self.pins)
            usage=parent.fresh_request(self.image,read)
            need('same-fresh-array-parent-request',usage==binding['typedRequest'])
            proof=scope['arraySources'][str(index)];child=None
            if index==4:child=self.components()
            elif index==17:
                from scripts.game_data.memorypack.interactive_mount_transfer_sources import derive
                child=derive(self.image,self.pins,array_source=proof)
            result=dict(operation='array',typeName=typ,proof=proof,binding=binding,child=child)
        elif read.get('mode')=='typed-static-out-reference':
            actual=scope['staticReferenceSources'][str(index)]
            binding=dictionaries.bind_parent_source(source,scope,read,self.pins,actual)
            _,k,v=dictionaries.replay_source(actual,self.pins)
            callbacks={t:self.callback(t)for t in set((k,v))&{'int','string'}}
            reference=self.original(v)if v in dictionary_children.REFERENCES else None
            child=dictionary_children.compose(actual,self.pins,callbacks=callbacks,reference=reference)
            result=dict(operation='static-dictionary',typeName=typ,proof=actual,binding=binding,children=child)
        elif typ==audio.TYPE:
            transfer=parent.bind_reference_result(source,read,self.pins);usage=parent.fresh_request(self.image,read)
            proof=audio.derive(self.image,self.pins,typed_request=usage,
                call_target=self.image.pe.image_base+read['sourceTargetRva'],enum_source=self.enums())
            # This is an independent actual List<string> source witness. The
            # Audio dictionary's own closed carrier proves its value nominal;
            # no Model component execution or enclosing owner is inferred.
            witness=self.member('Beyond.Gameplay.Core.InteractiveModelLevelUpComponentData',1)
            need('independent-actual-pooled-string-list-value',witness['operation']=='collection'
                and witness['proof']['elementType']=='string')
            result=dict(operation='audio-dictionary',typeName=typ,proof=proof,binding=transfer,
                valueList=witness,pooledCallback=self.callback('string'))
        elif typ=='Beyond.Gameplay.GameCondition':
            from scripts.game_data.memorypack.levelscript_current_source import require_current_owner
            from scripts.game_data.codecs.levelscript.current_task_game_conditions import validate
            from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
            need('active-current-condition-owner',self.action_owner is not None)
            owner=self.action_owner;require_current_owner(owner,strings=owner.strings)
            need('same-current-condition-native-build',owner.proof['nativeInputs']==self.pins)
            validate(owner.task_caps)
            binding=parent.bind_reference_result(source,read,self.pins);usage=parent.fresh_request(self.image,read)
            bind_typed_read(self.image,usage,method_name='ReadValue',argument=typ,kind=18,reference=True)
            child=owner.task_caps['conditionBinding']
            need('same-actual-nominal-condition-reader',usage['methodSpec'][0]==child['readerMethodDefinition']
                and read['sourceTargetRva']==child['sourceTargetRva']and child['typeName']==typ)
            result=dict(operation='game-condition',typeName=typ,binding=binding,capability=owner.task_caps['condition'])
        elif typ in('Beyond.Blackboard+BlackboardDouble','Beyond.Blackboard+BlackboardVector3','UnityEngine.AnimationCurve'):
            result=self._bind_external(source,read)
        elif read['kind']=='reference:'+typ and (read.get('context')or{}).get('typeKind')==18:
            child=self.original(typ)
            binding=objects.bind_member(self.image,self.pins,source,read,child)
            result=dict(operation='object-reference',typeName=typ,proof=child,binding=binding)
        else:raise ValueError('interactiveNativeGraph.unproved-child:'+str(dict(
            parent=name,memberIndex=index,fieldName=read['fieldName'],typeName=typ,kind=read['kind'],mode=read.get('mode'))))
        self.members[key]=result
        return result


def layout_optional_prefix():
    from scripts.game_data.memorypack.interactive_value_layouts import OPTIONAL
    return OPTIONAL
