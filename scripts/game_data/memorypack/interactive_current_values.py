"""Sequential Interactive values under fresh per-member native obligations.

Metadata supplies candidate names and plans only. Every consumed field first
joins its actual parent and independent child source. Unproved plans always
raise, including FF; derived EOF never grants a native schema by itself.
Source/VFS/native entry and exit authentication belongs to the outer operation.
"""
import json
import struct
from pathlib import Path

from scripts.game_data.memorypack.derived_schema import (
    Resolver,MemberPlan,FIXED,NULL_ONLY,OBJECT,UNION,STRING,LIST,MAP,PROFILE)
from scripts.game_data.memorypack.derived_plans import PlanRegistry
from scripts.game_data.memorypack.derived_values import ValueReader
from scripts.game_data.memorypack.interactive_native_graph import ROOT
from scripts.game_data.memorypack.buff_actions import Reader as FramingReader

UNPROVED='unproved-interactive-child'
VARIANT='Beyond.Gameplay.Core.InteractiveTemplateVariant'
ACTION_MAP='Beyond.Gameplay.Actions.ActionSerializedMap'


def need(check,condition,detail=''):
    if not condition:raise ValueError('interactiveCurrentValues.'+check+':'+str(detail)[:1800])


class CandidateResolver(Resolver):
    """Plan construction cannot admit a refused reference's null marker."""
    def plan(self,definition,stack=frozenset()):
        previous=getattr(self,'_parent',None)
        self._parent=self.wrappers[definition].wrapped_type if definition in self.wrappers else None
        try:return super().plan(definition,stack)
        finally:self._parent=previous

    def _plan_for_type(self,name,declared,**kwargs):
        from scripts.game_data.memorypack.interactive_raw_optional_components import FIELDS
        from scripts.game_data.memorypack.interactive_value_layouts import RAW,OPTIONAL
        selected={field:value for field,value in FIELDS.values()}
        if getattr(self,'_parent',None)==VARIANT and name in selected and declared==OPTIONAL+selected[name]+'>':
            return MemberPlan(name,FIXED,width=RAW[selected[name]][1],scalar='raw',declared_type=declared)
        candidate=super()._plan_for_type(name,declared,**kwargs)
        if candidate is None or candidate.kind==NULL_ONLY:
            return MemberPlan(name,UNPROVED,declared_type=declared)
        return candidate


def registry_from_image(image):
    from scripts.game_data.memorypack.wrapper_members import (
        derive_from_image,DerivedTables,enum_widths_from_image,unmanaged_value_sizes_from_image)
    resolver=CandidateResolver(derive_from_image(image),DerivedTables(
        enum_widths_from_image(image),unmanaged_value_sizes_from_image(image)))
    registry=PlanRegistry.from_resolver(resolver,{},named=(ROOT,))
    need('root-candidate-plan',ROOT in registry.named_roots,resolver.blockers.get(resolver.by_type.get(ROOT)))
    return registry


class InteractiveValueReader(ValueReader):
    def __init__(self,raw,source,*,registry,strings,graph,action_owner=None):
        super().__init__(raw,source,registry=registry,strings=strings)
        self.graph=graph;self.action_owner=action_owner;self.layouts=graph.value_layouts()
        self.objects={};self.field_count=0;self.union_count=0;self.budget={'remaining':65536}
        self._direct_wrapper=False;self._leaf_projection=False

    def _charge(self,n=1):
        need('finite-shared-node-budget',type(n)is int and 0<=n<=self.budget['remaining'],n)
        self.budget['remaining']-=n

    def _bounded_count(self,limit,minimum=1,*,nullable=True):
        need('complete-count',self.pos+4<=self.limit,self.pos)
        value=struct.unpack_from('<i',self.data,self.pos)[0]
        need('source-owned-signed-count',type(limit)is int and (-1 if nullable else 0)<=value<=limit,(self.pos,value,limit))
        self._charge(1+max(value,0))
        return self.count(minimum,nullable=nullable)

    def _codec(self,callback,cap=None):
        from scripts.game_data.codecs.levelscript.param_graph import Reader
        reader=Reader(self.data,self.pos,self.strings,self.source)
        value=callback(reader,self.source,cap)if cap is not None else callback(reader,self.source)
        self.take(reader.offset-self.pos,'independently-owned-child')
        return value

    def _value_object(self,definition,depth):
        self._plan_depth_guard(depth);self._charge()
        name=self.plan_registry.wrapped_names[definition];start=self.pos
        direct=self._direct_wrapper;self._direct_wrapper=False
        if name==ACTION_MAP and not self._leaf_projection:
            from scripts.game_data.codecs.levelscript.current_action_serialized_map import decode
            if self.action_owner is None:
                # This exact Original's complete reference adapter/reader and
                # concrete FF caller have independent current native owners.
                # No positive list or union child is admitted by this path.
                self.graph.original(name)
                need('positive-ActionMap-needs-active-current-operation',self.peek()==255)
                self.take(1,'current-null-ActionSerializedMap');return None
            need('active-current-ActionMap-operation',self.action_owner is not None)
            value,end=decode(self.data,self.pos,strings=self.strings,current_owner=self.action_owner,
                budget=self.budget,native_node_decoder=self._native_action_node)
            self.take(end-self.pos,'current-ActionSerializedMap')
            return value
        if not self._leaf_projection:
            record=self.graph.record(name);source=record['source']
            if not direct:self.graph.original(name)
            members=self.plan_registry.plans[definition]
            need('same-complete-native-ordered-members',[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']]
                ==[(m.name,m.declared_type)for m in members],(name,start))
        else:members=self.plan_registry.plans[definition]
        if self.peek()==255:
            self.take(1,'source-proved-null-wrapper');return None
        self.header(len(members));value={};fields=[]
        for index,member in enumerate(members):
            at=self.pos
            if self._leaf_projection:value[member.name]=self._project_member(member,depth+1)
            else:value[member.name]=self._certified_member(member,self.graph.member(name,index),depth+1,
                source=source,index=index)
            fields.append(dict(fieldName=member.name,start=at,end=self.pos));self.field_count+=1
        self.objects[(start,self.pos)]=dict(typeName=name,fields=fields,value=value)
        return value

    def _value_member(self,member,depth):
        # Only explicitly certified callers/collection elements reach the
        # projection helper. An anonymous metadata-only child has no grammar.
        need('no-unproved-null-fallback',member.kind not in(UNPROVED,NULL_ONLY),member.declared_type)
        return self._project_member(member,depth)

    def _project_member(self,member,depth):
        need('no-unproved-plan-kind',member.kind not in(UNPROVED,NULL_ONLY),member.declared_type)
        return super()._value_member(member,depth)

    def _value_fixed(self,member):
        return self.layouts.read(member.declared_type,self.take(member.width or 0,'named-raw-value'))

    def _certified_member(self,member,certificate,depth,*,source,index):
        self._plan_depth_guard(depth);operation=certificate['operation'];typ=member.declared_type
        need('same-certified-nominal',certificate.get('typeName')==typ,(operation,typ))
        if operation=='primitive':
            read=certificate['sourceRead']
            need('same-source-owned-raw-width',member.kind==FIXED and type(member.width)is int
                and read.get('wireBytes')==member.width,(typ,member.width,read.get('wireBytes')))
            if typ.startswith('Beyond.Optional`1<'):
                layout=source['sourceScope']['valueTypeSources'][str(index)]['layout']
                raw=self.take(member.width,'raw-scalar-Optional');fields={}
                for f in layout['fields']:
                    fields[f['fieldName']]=self.layouts.read(f['declaredType'],raw[f['offset']:f['offset']+f['bytes']])
                return dict(typeName=typ,rawHex=raw.hex(),fields=fields)
            return self._value_fixed(member)
        if operation=='pooled-string':
            need('own-pooled-string-plan',member.kind==STRING and typ=='string')
            return self._value_string()
        if operation=='parameter':return self._parameter(certificate)
        if operation=='parameter-array':
            from scripts.game_data.codecs.levelscript import current_boolean_param_array as boolean
            from scripts.game_data.codecs.levelscript import current_vector_param_array as vector
            from scripts.game_data.codecs.levelscript import current_entity_param_array as entity
            need('complete-Param-array-count',self.pos+4<=self.limit)
            count=struct.unpack_from('<i',self.data,self.pos)[0]
            need('finite-Param-array-budget',-1<=count<=4096,count);self._charge(1+max(count,0))
            module=entity if certificate.get('entity')else boolean if certificate['boolean']else vector
            return self._codec(module.read,certificate['capability'])
        if operation=='game-condition':
            from scripts.game_data.codecs.levelscript.current_game_condition import read
            return self._codec(read,certificate['capability'])
        if operation=='lang-key':
            from scripts.game_data.codecs.leveldata.current_lang_key import read
            return self._codec(read,certificate['capability'])
        if operation=='collection':return self._collection(member,certificate,depth)
        if operation=='array':return self._array(member,certificate,depth)
        if operation=='managed-optional':return self._optional(certificate,depth)
        if operation=='static-dictionary':return self._dictionary(member,certificate,depth)
        if operation=='audio-dictionary':return self._audio_dictionary(certificate,depth)
        if operation=='external-reference':return self._external(member,certificate,depth)
        if operation=='object-reference':
            need('ordinary-object-plan',member.kind==OBJECT,typ)
            return self._value_object(member.ref,depth+1)
        raise ValueError('interactiveCurrentValues.unproved-operation:'+operation)

    def _parameter(self,certificate):
        from scripts.game_data.codecs.levelscript import current_condition_param as primitive
        from scripts.game_data.codecs.levelscript import current_condition_enum_param as enums
        from scripts.game_data.codecs.levelscript import current_condition_storage_param as storage
        from scripts.game_data.codecs.levelscript import current_condition_list_param as lists
        from scripts.game_data.codecs.levelscript import current_action_dedicated_param as dedicated
        from scripts.game_data.codecs.levelscript import current_action_output_param as output
        proof=certificate['proof'];name=certificate['typeName'];cap=certificate['capability']
        groups=proof['proofs'];selected=[]
        for key,codec in(('primitive',primitive),('enum',enums),('storage',storage),('list',lists),
                ('dedicated',dedicated),('output',output)):
            component=groups.get(key,{})
            if any(v.get('typeName')==name for v in component.get('capabilities',{}).values()):selected.append(codec)
        if not selected and cap.get('schema')=='endfield.levelscript-gameplay-tag-list-param-capability.v1':
            from scripts.game_data.codecs.levelscript.current_gameplay_tag_list_param import read
            return self._codec(read,cap)
        if not selected and cap.get('valueType')=='Beyond.Gameplay.View.CameraControlState':
            from scripts.game_data.codecs.levelscript.current_camera_state_param import read
            return self._codec(read,cap)
        if not selected and cap.get('valueType')=='Beyond.Gameplay.Core.ScriptTaskPtr':
            from scripts.game_data.codecs.levelscript.current_condition_script_task_param import read
            return self._codec(read,cap)
        if not selected and cap.get('valueType')=='Beyond.Gameplay.Core.SplinePtr':
            from scripts.game_data.codecs.levelscript.current_spline_param import read
            return self._codec(read,cap)
        if not selected and cap.get('valueType')=='Beyond.ObjectPtr`1<Beyond.Gameplay.Core.GlobalBuff>':
            from scripts.game_data.codecs.levelscript.current_global_buff_param import read
            return self._codec(read,cap)
        if not selected and cap.get('valueType')=='Beyond.Gameplay.Core.AirWallPtr':
            from scripts.game_data.codecs.levelscript.current_airwall_param import read
            return self._codec(lambda r,f,c:read(r,f,c,layouts=self.layouts),cap)
        if not selected and cap.get('valueType')=='Beyond.Gameplay.View.CameraControlStateInitialParam':
            from scripts.game_data.codecs.levelscript.current_camera_initial_param import read
            return self._codec(lambda r,f,c:read(r,f,c,layouts=self.layouts),cap)
        need('one-exact-independent-Param-codec',len(selected)==1,name)
        return self._codec(selected[0].read,cap)

    def _native_action_node(self,data,offset,family,decoded):
        need('same-action-source-bytes',data is self.data and type(offset)is int)
        child=InteractiveValueReader(data,self.source,registry=self.plan_registry,strings=self.strings,
            graph=self.graph,action_owner=self.action_owner)
        child.pos=offset;child.budget=self.budget
        marker=child.peek()
        if marker==250:tag=struct.unpack_from('<H',child.take(3,'native-action-extended-tag'),1)[0]
        else:
            need('nonreserved-native-action-tag',marker<250,marker);tag=child.take(1,'native-action-tag')[0]
        case=self.graph.action_case(family,tag);name=case['typeName']
        need('same-actual-native-action-case',decoded.get('wrapperName')==case['wrapperName']
            and decoded.get('unionTag')==tag,(family,tag,decoded.get('wrapperName'),case['wrapperName']))
        definition=self.graph.by_type[name].type_definition
        need('same-actual-named-action-plan',self.plan_registry.wrapped_names.get(definition)==name)
        if 'manualSource'in case:
            from scripts.game_data.memorypack.levelscript_manual_action_values import read
            value=read(child,case['manualSource'])
        else:
            if child.peek()!=255:child._prepare_action_children(name)
            child._direct_wrapper=True;value=child._value_object(definition,0)
        cursor=offset
        for span in child.ranges:
            need('whole-independent-action-byte-partition',span['start']==cursor and span['end']>cursor)
            cursor=span['end']
        need('independent-action-source-extent',cursor==child.pos)
        for span,obj in child.objects.items():
            need('one-named-action-object-per-source-span',span not in self.objects or self.objects[span]==obj,span)
            self.objects[span]=obj
        self.field_count+=child.field_count;self.union_count+=1+child.union_count
        return {'$tag':tag,'$type':name,'$value':value},child.pos

    def _prepare_action_children(self,name):
        """Report independent reached field-source gaps before reading values."""
        reads=self.graph.record(name)['source']['orderedSourceReads'];errors=[];failed=0
        for index,read in enumerate(reads):
            try:self.graph.member(name,index)
            except (ValueError,KeyError,IndexError,TypeError,RuntimeError,OSError)as error:
                failed+=1
                if len(errors)<8:errors.append(dict(memberIndex=index,fieldName=read['fieldName'],
                    typeName=read['declaredType'],errorType=type(error).__name__,detail=str(error)[:900]))
        if failed:
            diagnostic=dict(validator='interactiveCurrentValues',gate='complete-native-action-children',
                source=self.source,typeName=name,failedFields=failed,fields=errors)
            error=ValueError('interactiveCurrentValues.complete-native-action-children:'+json.dumps(diagnostic,ensure_ascii=False))
            error.diagnostic=diagnostic
            raise error

    def _collection(self,member,certificate,depth):
        proof=certificate['proof'];element=proof['elementType']
        if element=='Beyond.Gameplay.ParamKeyValue':
            from scripts.game_data.codecs.levelscript.param_graph import Reader
            self.graph.param_graph()
            # The independently proved list source limits all counts before
            # the shared graph codec sees its own larger resource bound.
            need('complete-property-count',self.pos+4<=self.limit)
            count=struct.unpack_from('<i',self.data,self.pos)[0]
            need('bounded-property-list',-1<=count<=4096,count);self._charge(1+max(count,0))
            reader=Reader(self.data,self.pos,self.strings,self.source)
            value=reader.items(self.source,reader.key_value)
            self.take(reader.offset-self.pos,'current-ParamKeyValue-list')
            return value['values']
        count=self._bounded_count(4096,4 if element in('string','int')or proof['operation']=='nominal-enum32-list'else 1)
        if count<0:return None
        if proof['operation']=='data-pair-value-list':
            return[self._data_pair(proof,depth+1)for _ in range(count)]
        need('typed-list-element-plan',member.kind==LIST and member.element is not None)
        return[self._value_member(member.element,depth+1)for _ in range(count)]

    def _array(self,member,certificate,depth):
        binding=certificate['binding'];element=binding['elementType'];limit=binding['countRange'][1]
        count=self._bounded_count(limit,4 if binding['operation']in('raw-GameplayTag-array','pooled-string-array')else 1)
        if count<0:return None
        if binding['operation']=='mount-point-value-array':
            return[self._mount(certificate['child'],depth+1)for _ in range(count)]
        need('typed-array-element-plan',member.kind==LIST and member.element is not None)
        if binding['operation']=='raw-GameplayTag-array':
            return[self.layouts.read(element,self.take(4,'raw-GameplayTag-element'))for _ in range(count)]
        return[self._value_member(member.element,depth+1)for _ in range(count)]

    def _value_union(self,base,depth):
        name=self.plan_registry.wrapped_names[base]
        need('only-owned-component-union',name=='Beyond.Gameplay.BaseComponentData',name)
        proof=self.graph.components();start=self.pos
        if self.peek()==255:
            need('own-native-FF-path',proof.get('canonicalFF',{}).get('canonicalFF')is True)
            self.take(1,'current-component-union-FF');return None
        marker=self.peek()
        if marker==250:tag=struct.unpack_from('<H',self.take(3,'wide-component-tag'),1)[0]
        else:
            need('nonreserved-component-tag',marker<250,marker)
            tag=self.take(1,'component-tag')[0]
        selected,=[p for p in proof['programs']if p['tag']==tag]
        definition=self.plan_registry.union_tag_maps[base].get(tag)
        need('same-native-component-tag-assignment',definition is not None
            and self.plan_registry.wrapped_names[definition]==selected['wrappedType'],(start,tag))
        self._direct_wrapper=True
        value=self._value_object(definition,depth+1);self.union_count+=1
        return {'$tag':tag,'$type':selected['wrappedType'],'$value':value}

    def _dictionary(self,member,certificate,depth):
        child=certificate['children']
        if self.peek()==255:
            self.take(1,'static-dictionary-FF');return None
        self.header(1);count=self._bounded_count(child['countLimit'],nullable=False)
        need('own-static-dictionary-plan',member.kind==MAP and member.key is not None and member.value is not None)
        return[dict(key=self._value_member(member.key,depth+1),value=self._value_member(member.value,depth+1))for _ in range(count)]

    def _audio_dictionary(self,certificate,depth):
        count=self._bounded_count(certificate['proof']['countLimit'],8)
        if count<0:return None
        values=[]
        for _ in range(count):
            key=self.layouts.read(certificate['proof']['keyType'],self.take(4,'audio-enum-key-bits'))
            n=self._bounded_count(4096,4)
            value=None if n<0 else[self._value_string()for _ in range(n)]
            values.append(dict(key=key,value=value))
        return values

    def _optional(self,certificate,depth):
        from scripts.game_data.memorypack.interactive_value_layouts import OPTIONAL,MOUNT
        proof=certificate['proof'];wrapper=proof['proof']['wrapperSource'];start=self.pos
        if self.peek()==255:
            self.take(1,'managed-Optional-FF-default');return dict(wasNullMarker=True,enabled=False,value=None)
        self.header(2);raw=self.take(1,'Optional.enabled')[0]
        typ=certificate['typeName'][len(OPTIONAL):-1]
        if typ=='string':
            source=wrapper['sourceScope']['events'][1]
            from scripts.game_data.memorypack.pooled_source_helper import validate_on_image
            slot=('optional-pool',source['sourceTargetRva'])
            if slot not in self.graph.leaves:self.graph.leaves[slot]=validate_on_image(self.graph.image,
                self.graph.image.pe.image_base+source['sourceTargetRva'],self.graph.pins)
            value=self._value_string()
        else:
            limit=64 if typ=='Beyond.Gameplay.Core.GameplayTag[]'else 4096
            count=self._bounded_count(limit,4 if typ in('string[]','Beyond.Gameplay.Core.GameplayTag[]')else 1)
            if count<0:value=None
            elif typ=='string[]':value=[self._value_string()for _ in range(count)]
            elif typ=='Beyond.Gameplay.Core.GameplayTag[]':value=[self.layouts.read(typ[:-2],self.take(4,'Optional.raw-tag'))for _ in range(count)]
            elif typ==MOUNT+'[]':
                from scripts.game_data.memorypack.interactive_mount_transfer_sources import derive
                key=('optional-mount-transfer',wrapper['arraySource']['arrayReaderTargetRva'])
                if key not in self.graph.leaves:self.graph.leaves[key]=derive(self.graph.image,self.graph.pins,array_source=wrapper['arraySource'])
                value=[self._mount(self.graph.leaves[key],depth+1)for _ in range(count)]
            else:raise ValueError('interactiveCurrentValues.unproved-Optional-child:'+typ)
        return dict(wasNullMarker=False,enabled=bool(raw),enabledRawByte=raw,value=value,sourceOffset=start,endOffset=self.pos)

    def _mount(self,proof,depth):
        from scripts.game_data.memorypack.pooled_source_helper import validate_on_image
        self._plan_depth_guard(depth);self._charge()
        need('own-array-dispatcher-and-value-wrapper',proof.get('actualSourceProved')is True
            and proof.get('wireGrammarAdmitted')is False and proof['proof'].get('arrayDispatcher')is not None)
        wrapper=proof['proof']['wrapperSource'];events=wrapper['sourceScope']['events']
        need('own-MC2-mount-fields',[(r['fieldName'],r['declaredType'])for r in events]==
            [('mountPoint','Beyond.Gameplay.MountPoint'),('name','string')]
            and wrapper.get('completeSelectedCallerAdmitted')is True and wrapper['sourceScope'].get('memberCount')==2
            and(events[0].get('kind'),events[0].get('wireBytes'))==('scalar32',4)
            and(events[1].get('kind'),events[1].get('wireBytes'))==('byte-payload',4))
        if self.peek()==255:
            self.take(1,'mount-point-FF-default');return dict(wasNullMarker=True,mountPoint=0,name=None)
        self.header(2);source=events[1];key=('mount-pool',source['sourceTargetRva'])
        if key not in self.graph.leaves:self.graph.leaves[key]=validate_on_image(self.graph.image,
            self.graph.image.pe.image_base+source['sourceTargetRva'],self.graph.pins)
        return dict(wasNullMarker=False,mountPoint=self.layouts.read('Beyond.Gameplay.MountPoint',self.take(4,'mount-point-enum')),
            name=self._value_string())

    def _external(self,member,certificate,depth):
        proof=certificate['proof'];caps=dict(proof['capabilities']);name=member.declared_type
        if name=='UnityEngine.AnimationCurve':
            from scripts.game_data.memorypack.skill_animation_curve_codec import read_curve
            cap=certificate['capability'];caps={'curve-profile':cap}
            oracle=self._oracle(caps);read_curve(oracle)
            record=oracle.records[-1]
            self.take(oracle.pos-self.pos,'source-owned-Unity-curve')
            if record['isNull']:return None
            keys=[]
            for key in record['keys']:
                keys.append({f['fieldName']:self.layouts.read(f['declaredType'],bytes.fromhex(f['rawHex']))for f in key['fields']})
            return dict(preWrapMode=self.layouts.read('int',bytes.fromhex(record['preWrapModeRawHex'])),
                postWrapMode=self.layouts.read('int',bytes.fromhex(record['postWrapModeRawHex'])),
                keys=None if record['keysAreNull']else keys)
        from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
        if name=='Beyond.Blackboard+BlackboardVector3':
            caps.update(proof['proof']['blackboardDouble']['capabilities'])
            oracle=self._oracle(caps);cap=certificate['capability'];at=oracle.pos
            if oracle.peek()==255:
                oracle.take(1,'blackboard-vector3.null')
                oracle.records.append(dict(start=at,end=oracle.pos,fields=[],isNull=True))
            else:
                need('own-three-nominal-blackboard-children',cap.get('memberCount')==3
                    and cap.get('orderedReads')==[dict(fieldName=f,kind='record',childCapability='skill-blackboard-double')for f in('x','y','z')])
                oracle.header(3);fields=[]
                for read in cap['orderedReads']:
                    start=oracle.pos;RootChildrenReader(oracle).record(read['childCapability'],depth+1)
                    fields.append(dict(fieldName=read['fieldName'],start=start,end=oracle.pos))
                oracle.records.append(dict(start=at,end=oracle.pos,fields=fields,isNull=False))
        else:
            need('own-independent-blackboard-double',name=='Beyond.Blackboard+BlackboardDouble')
            oracle=self._oracle(caps);RootChildrenReader(oracle).record('skill-blackboard-double',depth+1)
        return self._project_oracle_record(member.ref,depth,oracle)

    def _data_pair(self,proof,depth):
        from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
        caps=proof['proof']['capabilities'];oracle=self._oracle(caps)
        RootChildrenReader(oracle).record('skill-root-data-pair',depth+1)
        definition=next(d for d,n in self.plan_registry.wrapped_names.items()if n=='Beyond.Blackboard+DataPair')
        value=self._project_oracle_record(definition,depth,oracle)
        return dict(wasNullMarker=value is None,values=value)

    def _oracle(self,caps):
        return _LeafOracle(self.data,self.source,strings=self.strings,graph=self.graph,
            caps=caps,offset=self.pos,limit=self.limit)

    def _project_oracle_record(self,definition,depth,oracle):
        previous=self._leaf_projection;self._leaf_projection=True
        try:value=self._value_object(definition,depth+1)
        finally:self._leaf_projection=previous
        need('independent-complete-leaf-extent',self.pos==oracle.pos,(self.source,self.pos,oracle.pos))
        for record in oracle.records:
            if not record.get('fields'):continue
            obj=self.objects.get((record['start'],record['end']))
            need('independent-named-leaf-field-extents',obj is not None and obj['fields']==record['fields'],record)
        return value


class _LeafCapabilities:
    def __init__(self,graph,caps):self.graph=graph;self.caps=caps
    def child(self,name):
        self.graph._active()
        need('exact-fresh-leaf-capability',name in self.caps,name)
        return self.caps[name]


class _LeafOracle(FramingReader):
    def __init__(self,data,source,*,strings,graph,caps,offset,limit):
        super().__init__(data,source,limit=limit)
        self.pos=offset;self.strings=strings;self.operation=_LeafCapabilities(graph,caps)
    def byte_payload(self):
        index=struct.unpack('<i',self.take(4,'source-owned-pooled-string'))[0]
        return self.strings.resolve(index)


def decode_current(raw,*,source,strings,graph,registry,action_owner=None):
    graph._active()
    reader=InteractiveValueReader(raw,source,registry=registry,strings=strings,graph=graph,action_owner=action_owner)
    value=reader.read_record(registry.named_roots[ROOT])
    need('nonempty-complete-root',isinstance(value,dict)and len(value)==26)
    need('physical-EOF',reader.pos==len(raw),(source,reader.pos,len(raw)))
    need('source-id',value.get('id')==Path(source).stem.removeprefix('data_'),(source,value.get('id')))
    cursor=0
    for span in reader.ranges:
        need('every-byte-once',span['start']==cursor and span['end']>cursor)
        cursor=span['end']
    need('byte-partition-EOF',cursor==len(raw))
    return value,dict(wholeSchemaExact=True,physicalEOF=True,bytesConsumed=len(raw),
        nativeFieldExtentsChecked=reader.field_count,unionAssignmentsChecked=reader.union_count,
        namedObjectCount=len(reader.objects),sourceIdAndPhysicalEofProved=True,runtimeExecutionProved=False)
