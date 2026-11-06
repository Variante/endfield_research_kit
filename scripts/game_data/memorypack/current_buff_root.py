"""Current Buff root composition; every cursor step has an independent owner.

The root contract proves its thirty source reads and destinations. The active
current operation supplies independently proved nominal child grammars. Fresh
concrete record and collection proofs supply the additional Buff-only children.
Unknown positive children stop at their own field; no scan, suffix search,
historical action tag or opaque skip can establish physical EOF.
"""
from __future__ import annotations

import json
from pathlib import PurePosixPath

from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.memorypack import buff_root_no_positive_native as root_native
from scripts.game_data.memorypack import buff_dispel_config, buff_icon_config
from scripts.game_data.memorypack import generated_reader_sources
from scripts.game_data.memorypack.reference_param_profile import derive_pair
from scripts.game_data.memorypack.reference_object_sources import derive_adapter
from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
from scripts.game_data.memorypack.skill_timeline_current_sequence import CurrentSequenceReader
from scripts.game_data.skill_timeline_current_sequence_native import prepared_current_sequence


SCHEMA = 'endfield.current-buff-root-proof.v1'
RECORDS = {
    'stackingSettings': 'Beyond.Gameplay.Core.BuffStackingSettings',
    'globalModifierElement': 'Beyond.Gameplay.Core.GlobalModifier+Data',
    'buffEventElement': 'Beyond.Gameplay.Core.BuffActionMap',
    'igniteEventElement': 'Beyond.Gameplay.Core.IgniteActionMap',
    'stackEffectElement': 'Beyond.Gameplay.Core.StackBuffEffectData',
    'effectActionElement': 'Beyond.Gameplay.Core.EffectAction+EffectActionData',
    'damageModifierElement': 'Beyond.Gameplay.Core.DamageModifier+Data',
    'healModifierElement': 'Beyond.Gameplay.Core.HealModifier+Data',
    'poiseModifierElement': 'Beyond.Gameplay.Core.PoiseModifier+Data',
    'shieldElement': 'Beyond.Gameplay.Core.ShieldConfig',
    'absorptionElement': 'Beyond.Gameplay.Core.DamageAbsorptionConfig',
    'timelineElement': 'Beyond.Gameplay.Core.TimelineAction+TimelineActionData',
    'forceSyncElement': 'Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData',
}
ROOT_LISTS={name:RECORDS[key]for name,key in (
    ('globalModifier','globalModifierElement'),('buffEventAction','buffEventElement'),('igniteEventAction','igniteEventElement'),
    ('damageModifier','damageModifierElement'),('healModifier','healModifierElement'),('poiseModifier','poiseModifierElement'),
    ('shieldConfigs','shieldElement'),('timelineActions','timelineElement'))}
CHILDREN = {
    'addingCooldown': 'skill-blackboard-double', 'duration': 'skill-blackboard-double',
    'triggerInterval': 'skill-blackboard-double', 'maxTriggerCnt': 'blackboard-int',
    'attributeModifier': 'skill-root-attribute-modifier-data',
}
REFERENCE_CHILDREN = {
    'Beyond.Blackboard+BlackboardDouble': ('skill-blackboard-double', 'root_record_profile'),
    'Beyond.Gameplay.Core.TargetSettings': ('target-profile', 'target_profile'),
    'Beyond.Gameplay.EffectActionCfg': ('skill-effect-action-config', 'effect_profile'),
    'Beyond.Gameplay.Core.SequenceActionData': ('SequenceActionData', 'current-sequence'),
    'Beyond.Blackboard+BlackboardInt': ('blackboard-int', 'current-blackboard-int'),
    'Beyond.Gameplay.Core.CalculationBase': ('damage-calculation-union', 'damage_union_profile'),
}


def need(check, condition, detail=None):
    if not condition:
        raise ValueError('currentBuffRoot.' + check + ':' + str(detail)[:800])


def _join(image, field):
    source = field['source']
    return dict(fieldName=field['name'], typeName=field['declaredType'],
        sourceTargetRva=source['targetRva'],
        typedRequest=derive_typed_usage_context(image, source['context']['instructionRva'], label='currentBuffRoot'))


def prepare(image, pins, operation):
    """Derive Buff-only source proofs on the same explicitly selected image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_derive
    from scripts.game_data.memorypack.skill_action_reference_list_sources import bind_reference_reader, compose_reference_list
    selected = prepared_current_sequence(operation)
    active = selected.proof
    need('same-active-native-inputs', active['nativeInputs'] == pins)
    root = root_native.validate_current_native_contract(gameassembly=image.gameassembly, metadata=image.metadata_path)
    need('root-source', root.get('status') == 'validated' and root.get('nativeInputs') == pins, root.get('detail'))
    declaration = root_native._contract()
    fields = declaration['fields']
    need('root-thirty-distinct-fields', len(fields) == 30 and [f['index'] for f in fields] == list(range(30)))
    inventory = list(image.memorypack_wrappers.values())
    need('unique-selected-record-wrappers', all(sum(w.wrapped_type == typename for w in inventory) == 1
        for typename in RECORDS.values()))
    wrappers = {w.wrapped_type: w for w in inventory if w.wrapped_type in RECORDS.values()}
    from scripts.game_data.memorypack.buff_timeline_factory_sources import prove as timeline_factory
    from scripts.game_data.memorypack import buff_modifier_union_sources
    from scripts.game_data.memorypack.skill_damage_list_components import bind_list
    modifiers=buff_modifier_union_sources.derive(image,pins,active)
    sources = generated_reader_sources.derive_many(image, pins, [wrappers[t].name for t in RECORDS.values()],
        direct_factory_prover=timeline_factory)
    records = {}
    abi = reference_reader_abi(image, pins)
    from scripts.game_data.memorypack.skill_sequence_components import derive as sequence_derive
    from scripts.game_data.memorypack.skill_ordinary_ability_map_sources import compose_array
    sequence = sequence_derive(image, pins)
    sequence_cap = selected.child('SequenceActionData')
    need('same-fresh-Sequence-grammar', all(sequence_cap.get(k) == v
        for k, v in sequence['capabilities']['SequenceActionData'].items()))
    for item in sources['owners']:
        need('complete-concrete-child-source', item['status'] == 'complete-reader-source-proved', item.get('reason'))
        source = item['proof']; typename = source['wrappedType']; wrapper = wrappers[typename]
        pair = derive_pair(image, typename, wrapper.name)
        adapter = derive_adapter(image, pins, pair, wrapper)
        need('same-concrete-getter', source['lifecycle']['GetValue']['method'] == adapter['getterMethod'])
        need('same-concrete-reader', source['method'] == adapter['pairForwarder']['readerMethod'])
        arrays = {}
        for read in source['orderedSourceReads']:
            if read['declaredType'] == 'Beyond.Gameplay.Core.SequenceActionData[]':
                request = derive_typed_usage_context(image, read['context']['instructionRva'], label='currentBuffRoot.map')
                array = source['sourceScope']['arraySources'][str(read['memberIndex'])]
                arrays[str(read['memberIndex'])] = compose_array(pins, request, read['sourceTargetRva'], array, sequence)
        records[typename] = dict(source=source, pair=pair, adapter=adapter, referenceABI=abi, arrays=arrays)
    record_caps={typename:dict(typeName=typename,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,**abi)for typename in records}
    child_caps={**active['capabilities'],**record_caps,**modifiers['capabilities']}
    processor_caps={'Beyond.Gameplay.Core.DamageProcessorBase':'damage-processor-union',
        'Beyond.Gameplay.Core.HealProcessorBase':'buff-heal-processor-union',
        'Beyond.Gameplay.Core.PoiseProcessorBase':'buff-poise-processor-union'}
    for typename, record in records.items():
        record['lists'] = {}
        for read in record['source']['orderedSourceReads']:
            declared = read['declaredType']; index = str(read['memberIndex'])
            if declared in REFERENCE_CHILDREN:
                capability, _method = REFERENCE_CHILDREN[declared]
                join = dict(fieldName=read['fieldName'], typeName=declared, sourceTargetRva=read['sourceTargetRva'],
                    typedRequest=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentBuffRoot.record'))
                bind_read_value(pins,join,active,capability)
            elif declared in records:
                join=dict(fieldName=read['fieldName'],typeName=declared,sourceTargetRva=read['sourceTargetRva'],
                    typedRequest=derive_typed_usage_context(image,read['context']['instructionRva'],label='currentBuffRoot.recordChild'))
                bind_read_value(pins,join,dict(nativeInputs=pins,capabilities=record_caps),declared)
            elif declared.endswith('[]') and declared[:-2] in records:
                element = declared[:-2]; array = record['source']['sourceScope']['arraySources'][index]
                nominal = array['elementNominalReference']; child = records[element]
                need('array-owned-concrete-element', array['status'] == 'validated-conditional-reference-array-component'
                    and array['nativeInputs'] == pins and array['elementType'] == element
                    and array['closedArrayType'] == declared and array['elementValueType'] is False
                    and array['nullable'] is True and array['collectionCounts'] == [-1,0]
                    and array['positiveCountsAdmitted'] is True and array['countLimit'] == 10000
                    and array['elementGrammarAdmitted'] is False and array['wholeOwnerAdmitted'] is False
                    and nominal['typeName'] == element and nominal['wrapperName'] == child['source']['wrapperName']
                    and nominal['referenceReaderMethodDefinition'] == abi['referenceReaderMethodDefinition']
                    and nominal['referenceReaderTargetRva'] == abi['referenceReaderTargetRva']
                    and nominal['callbackBinding']['canonicalTargetRva'] == child['adapter']['callbackBinding']['canonicalTargetRva'])
                record['arrays'][index] = dict(array, elementGrammarAdmitted=True)
            elif declared.startswith('System.Collections.Generic.List`1<'):
                element = declared.removeprefix('System.Collections.Generic.List`1<').removesuffix('>')
                need('record-list-known-element', element in records or element in processor_caps, declared)
                request = derive_typed_usage_context(image,read['context']['instructionRva'],label='currentBuffRoot.recordList')
                collection = list_derive(image,pins,typed_request=request,
                    call_target=image.pe.image_base+read['sourceTargetRva'],element_type=element,count_limit=10000)
                capability=processor_caps.get(element,element);cap=child_caps[capability]
                child = dict(nativeInputs=pins,capabilities={capability:cap})
                binding=bind_reference_reader(image,pins,collection,child,element_capability=capability,label='BuffRecord.'+typename)
                join=dict(typeName=declared,typedRequest=request,sourceTargetRva=read['sourceTargetRva'])
                record['lists'][index]=bind_list(pins,join,dict(collection,referenceReaderTargetRva=binding['actualOptimizedReaderTargetRva']),
                    cap,capability=capability)
            else:
                need('record-source-owned-member-grammar', read['kind'] in
                    ('byte','raw-byte','scalar16','scalar32','scalar64','raw4','float64','byte-payload')
                    or index in record['arrays'], declared)
    joins = {}; collections = {}
    for field in fields:
        name = field['name']; kind = field['source']['kind']
        if name in CHILDREN:
            join = _join(image, field)
            joins[name] = bind_read_value(pins, join, active, CHILDREN[name])
        elif kind == 'list':
            join = _join(image, field); joins[name] = join
            if name == 'blackboard':
                cap = selected.child('skill-root-data-pair-list-positive')
                need('DataPair-list-source', cap['closedListType'] == field['declaredType']
                    and cap['packableReaderMethodDefinition'] == join['typedRequest']['methodSpec'][0]
                    and cap['packableReaderTargetRva'] == join['sourceTargetRva'])
            elif name == 'abilityEventAction':
                from scripts.game_data.memorypack.skill_ordinary_ability_map_sources import LIST
                cap = selected.child(LIST)
                need('AbilityActionMap-list-source', cap['closedListType'] == field['declaredType']
                    and cap['packableReaderMethodDefinition'] == join['typedRequest']['methodSpec'][0]
                    and cap['packableReaderTargetRva'] == join['sourceTargetRva'])
            else:
                typename = field['declaredType'].removeprefix('System.Collections.Generic.List`1<').removesuffix('>')
                collections[name] = list_derive(image, pins, typed_request=join['typedRequest'],
                    call_target=image.pe.image_base + join['sourceTargetRva'], element_type=typename, count_limit=10000)
                need('actual-root-list-element',ROOT_LISTS.get(name)==typename and typename in records,name)
                if typename in records:
                    cap=record_caps[typename]
                    child = dict(nativeInputs=pins, capabilities={typename:cap})
                    records[typename]['listReaderBinding'] = bind_reference_reader(image,pins,collections[name],child,
                        element_capability=typename,label='BuffData.'+name)
                    records[typename]['listCapability'] = compose_reference_list(collections[name],child,pins,
                        element_type=typename,element_capability=typename,label='BuffData.'+name)
        elif kind == 'packed-gameplay-tag-array':
            join = _join(image, field); cap = selected.child('skill-root-gameplay-tag-array')
            need('packed-Tag-array-source', cap['closedArrayType'] == field['declaredType']
                and cap['arrayReaderMethodDefinition'] == join['typedRequest']['methodSpec'][0]
                and cap['arrayReaderTargetRva'] == join['sourceTargetRva'])
            joins[name] = join
        elif name == 'stackingSettings':
            join = _join(image, field); joins[name] = join
            need('stacking-ordinary-reference-source', join['typeName'] == RECORDS[name]
                and join['typedRequest']['methodSpec'][0] == abi['referenceReaderMethodDefinition']
                and join['sourceTargetRva'] == abi['referenceReaderTargetRva'])
    dispel = buff_dispel_config.validate_current_native_contract(
        gameassembly=image.gameassembly, metadata=image.metadata_path)
    icon = buff_icon_config.validate_current_native_contract(
        gameassembly=image.gameassembly, metadata=image.metadata_path)
    need('dispel-own-source', dispel.get('status') == 'validated', dispel.get('detail'))
    need('icon-own-source', icon.get('status') == 'validated', icon.get('detail'))
    _publication_gate(image, pins)
    return dict(schema=SCHEMA, nativeInputs=pins, fields=fields, records=records, _operation=selected,
                root=root, joins=joins, collections=collections, dispel=dispel, icon=icon,modifierUnions=modifiers)


class BuffReader(CurrentSequenceReader):
    def __init__(self, data, source, *, operation, native):
        super().__init__(data, source, len(data), operation=operation)
        self.native = native
        self.children = RootChildrenReader(self)

    def blackboard_int(self):
        cap=self.operation.child('blackboard-int')
        need('BlackboardInt-program',cap.get('wholeGrammarAdmitted')is True
            and cap.get('orderedReads')==[dict(fieldName=n,kind=k,childCapability=c)
                for n,k,c in(('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),('value','int32',None))])
        if self.peek()==255:
            need('BlackboardInt-null',cap.get('nullAdmitted')is True);self.take(1,'BlackboardInt.null')
        else:
            self.header(3);self.byte_payload();self.take(1,'BlackboardInt.useBlackboardKey');self.take(4,'BlackboardInt.value')

    def reference(self,declared,depth):
        capability,method=REFERENCE_CHILDREN[declared]
        if method=='current-sequence':self._sequence(depth)
        elif method=='current-blackboard-int':self.blackboard_int()
        else:self._profile(method,capability,depth)

    def concrete(self, typename, depth=0):
        need('record-depth', type(depth)is int and 0<=depth<=64)
        component = self.native['records'][typename]; source = component['source']
        start = self.pos
        if self.peek() == 255:
            self.take(1, typename + '.null'); return
        reads = source['orderedSourceReads']; self.header(len(reads))
        fields = []
        for read in reads:
            at = self.pos; kind = read['kind']; declared = read['declaredType']
            if kind in ('byte', 'raw-byte', 'scalar16', 'scalar32', 'scalar64', 'raw4', 'float64'):
                width = {'byte': 1, 'raw-byte': 1, 'scalar16': 2, 'scalar32': 4, 'scalar64': 8, 'raw4': 4, 'float64': 8}[kind]
                need('actual-primitive-width', read.get('wireBytes') == width)
                self.take(width, typename + '.' + read['fieldName'])
            elif kind == 'byte-payload':
                self.byte_payload()
            elif declared in REFERENCE_CHILDREN:
                self.reference(declared,depth+1)
            elif declared in self.native['records']:
                self.concrete(declared,depth+1)
            elif read.get('mode') == 'typed-reference-array':
                array = source['sourceScope']['arraySources'][str(read['memberIndex'])]
                need('actual-owned-array-source', array['nativeInputs'] == self.native['nativeInputs']
                    and array.get('status') == 'validated-conditional-reference-array-component')
                # No element grammar is implied by the collection proof.
                count = self.count(1, nullable=True)
                if declared == 'Beyond.Gameplay.Core.SequenceActionData[]':
                    cap = component['arrays'][str(read['memberIndex'])]
                    need('map-actual-Sequence-array', cap['elementGrammarAdmitted'] is True and count <= cap['countLimit'])
                    for _ in range(max(0, count)): self._sequence(depth + 1)
                elif declared[:-2] in self.native['records']:
                    cap = component['arrays'][str(read['memberIndex'])]
                    need('owned-record-array-count', cap['elementGrammarAdmitted'] is True and count <= cap['countLimit'])
                    for _ in range(max(0, count)): self.concrete(declared[:-2],depth+1)
                else:
                    need('positive-array-child-not-yet-composed', count <= 0, declared)
            elif str(read['memberIndex']) in component['lists']:
                cap = component['lists'][str(read['memberIndex'])]; count = self.count(1,nullable=True)
                need('owned-record-list-count', count <= cap['countLimit'])
                for _ in range(max(0,count)):
                    if cap['elementType']in self.native['records']:self.concrete(cap['elementType'],depth+1)
                    elif cap['elementCapability']=='damage-processor-union':
                        self._profile('damage_union_profile',cap['elementCapability'],depth+1)
                    else:
                        from scripts.game_data.memorypack.buff_modifier_union_sources import read_union
                        read_union(self,self.native['modifierUnions'],cap['elementCapability'],depth+1)
            else:
                raise ValueError('currentBuffRoot.unproved-record-child:' + declared)
            fields.append(dict(fieldName=read['fieldName'], start=at, end=self.pos))
        self.records.append(dict(kind=typename, start=start, end=self.pos, fields=fields))


def decode_current_buff_root(data, *, source, operation, native):
    selected = prepared_current_sequence(operation)
    need('current-native-receipt', native.get('schema') == SCHEMA and native.get('_operation') is selected)
    reader = BuffReader(data, source, operation=selected, native=native)
    fields = []; reason = None
    try:
        reader.header(30)
        for field in native['fields']:
            at = reader.pos; name = field['name']; kind = field['source']['kind']; value = None
            if name in CHILDREN:
                if name == 'maxTriggerCnt':
                    reader.blackboard_int()
                else:
                    reader.children.record(CHILDREN[name])
            elif kind in ('bool', 'byte'):
                value = reader.take(1, 'BuffData.' + name).hex()
            elif kind == 'pooled-string':
                value = reader.byte_payload()
                need('root-id-source-identity', value == PurePosixPath(source).stem)
            elif kind == 'packed-gameplay-tag-array':
                reader.children.primitive_array('skill-root-gameplay-tag-array')
            elif name == 'dispelConfig':
                child = buff_dispel_config.decode_dispel_config(data, at, at + 8, native_validation=native['dispel'])
                reader.take(8, 'BuffData.dispelConfig')
                reader.records.append(dict(kind=field['declaredType'],start=at,end=reader.pos,receipt=child))
            elif name == 'iconConfig':
                child = buff_icon_config.decode_icon_config(data, at, len(data), require_limit_end=False, strings=selected.strings)
                reader.take(child['consumedEnd'] - at, 'BuffData.iconConfig')
                reader.records.append(dict(kind=field['declaredType'],start=at,end=reader.pos,receipt=child))
            elif name == 'stackingSettings':
                reader.concrete(RECORDS[name])
            elif name == 'blackboard':
                reader.children.collection('skill-root-data-pair-list-positive')
            elif name == 'abilityEventAction':
                from scripts.game_data.memorypack.skill_ordinary_ability_map_sources import LIST
                from scripts.game_data.memorypack.skill_ordinary_ability_map_codec import OrdinaryMapReader
                OrdinaryMapReader(reader).collection()
            elif kind == 'list':
                count = reader.count(1, nullable=True)
                if count > 0:
                    need('root-list-element-grammar',name in ROOT_LISTS and ROOT_LISTS[name]in native['records']
                        and name in native.get('collections',{}),name)
                    cap = native['collections'][name]
                    bounds = cap['countRange']
                    need('root-list-induction-domain', isinstance(bounds,list) and len(bounds)==2
                        and bounds[0] == -1 and type(bounds[1]) is int and 3 <= bounds[1] <= 10000, name)
                    need('root-list-owned-count-limit', count <= bounds[1], name)
                for _ in range(max(0,count)):reader.concrete(ROOT_LISTS[name])
            else:
                raise ValueError('currentBuffRoot.unproved-root-operation:' + name)
            named = dict(memberIndex=field['index'],fieldName=name,kind=kind,
                declaredType=field['declaredType'],start=at,end=reader.pos)
            if kind == 'pooled-string': named['value'] = value
            elif kind in ('bool','byte'): named['rawBitsHex'] = value
            fields.append(named)
        need('physical-EOF', reader.pos == len(data), (reader.pos, len(data)))
    except ValueError as error:
        reason = str(error)
    whole = len(fields) == 30 and reason is None and reader.pos == len(data)
    return dict(schema='endfield.current-buff-root-receipt.v1', source=source,
        rootFields=fields, parserCursor=reader.pos, hardLimit=len(data), records=reader.records,
        byteRanges=reader.ranges, wholeBuffDataExact=whole, stopReason=reason,
        status='exact-current-buff' if whole else 'current-buff-root-prefix', runtimeExecutionProved=False)
