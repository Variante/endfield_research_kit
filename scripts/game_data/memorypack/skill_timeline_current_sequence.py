"""Finite current-build Skill action dispatch by authenticated wrapper identity.

The old shared-sequence v2 reader is independent. This reader never translates
old tags or falls back to its action table. A selected current operation must
own each route, ordered read and child grammar before bytes are consumed.
"""
from __future__ import annotations

import struct
from typing import Any

from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT

LABEL = 'skillTimelineCurrentSequence'

# These are wire operations already owned by the structural Reader. Names in
# metadata cannot add an operation or assign a width to a generic child.
ATOMIC_KINDS = {
    'bool-byte': 1, 'anonymous-nonzero-byte': 1, 'byte': 1, 'boolean': 1,
    'int32': 4, 'enum-int32': 4, 'scalar32': 4, 'enum32': 4,
    'anonymous-scalar32': 4, 'raw4': 4, 'anonymous-raw4': 4,
    'float32-bits': 4, 'raw-float32-bits': 4, 'layer-mask-raw4': 4,
    'gameplay-tag32': 4,
    'audio-id-raw4': 4,
    'scalar64-bits': 8, 'float64-bits': 8, 'vector2-raw8':8,'ai-marker-raw8':8,
    'nullable-single-raw8':8,'unity-vector2-int-raw8':8,'unity-vector3-raw12':12,'unity-vector3-int-raw12':12,'unity-quaternion-raw16':16,'unity-color-raw16':16,
    'camera-initial-raw24':24,
    'animation-clip-raw36':36,
}
PROFILE_METHODS = {
    'gait-single-dictionary-profile':'gait_single_dictionary_profile',
    'scalar-payload': 'scalar_payload', 'blackboard-double': 'scalar_payload',
    'blackboard-scalar': 'scalar_payload', 'blackboard-vector3': 'vector_payload',
    'blackboard-vector2': 'vector2_payload',
    'buff-find-settings': 'buff_find_profile',
    'buff-filter-settings': 'buff_filter_profile',
    'root-record':'root_record_profile','root-collection':'root_collection_profile',
    'root-pooled-string-list':'root_pooled_string_list_profile',
    'curve-profile': 'curve_profile', 'target-profile': 'target_profile',
    'selector-profile':'selector_profile',
    'target-settings': 'target_profile', 'TargetSettings': 'target_profile',
    'direction-profile': 'direction_profile', 'skill-alert-profile': 'skill_alert_profile',
    'byte-payload': 'byte_payload', 'string': 'byte_payload',
    'effect-profile':'effect_profile','damage-unit-profile':'damage_unit_profile',
    'damage-union':'damage_union_profile','damage-list':'damage_list_profile',
    'hit-env-profile':'hit_env_profile',
    'action-setting-profile':'action_setting_profile',
    'action-geometry-profile':'action_geometry_profile',
    'action-nested-record-profile':'action_nested_record_profile',
    'ordinary-ability-map-profile':'ordinary_ability_map_profile',
    'target-filter-profile':'target_filter_profile',
    'special-aim-profile':'special_aim_profile',
    'camera-transition-profile':'camera_transition_profile',
    'camera-custom-profile':'camera_custom_profile',
    'look-at-target-profile':'look_at_target_profile',
    'raycast-record-profile':'raycast_record_profile',
}
LIST_METHODS = {
    'string-list': 'byte_payload',
    'selector-validator-list': 'selector_validator_profile',
    'selector-postprocessor-list': 'selector_postprocessor_profile',
    'cost-data-list': 'cost_profile',
}
ROOT_CONTINUATION_READS = (
    (1, 'aiExclusiveFrame', 'int32', None),
    (2, 'attackRangeType', 'enum32', None),
    (3, 'blackboard', 'null-empty-value-list', 'skill-root-data-pair-list'),
    (4, 'buffInputBase', 'null-reference', 'skill-root-buff-input-base'),
)


def validate_continuation(claim):
    """Accept a finite source-owned prefix, never infer the remaining root."""
    last = claim.get('lastMemberIndex')
    if (type(claim.get('memberCount')) is not int or claim['memberCount'] != 49
            or type(claim.get('startMemberIndex')) is not int or claim['startMemberIndex'] != 1
            or type(last) is not int or not 1 <= last <= 48
            or claim.get('wholeSkillDataAdmitted') is not False):
        raise ValueError(LABEL + '.root:unproved-continuation-scope')
    declared = claim.get('orderedReads')
    # The earlier current-build null-only subset retains its own exact shape.
    # This does not authenticate an old contract: the native gate separately
    # rederives and bidirectionally compares the complete selected declaration.
    subset = [dict(memberIndex=i, fieldName=n, kind=k, childCapability=c)
              for i, n, k, c in ROOT_CONTINUATION_READS[:last]]
    if last<=len(ROOT_CONTINUATION_READS)and declared==subset:expected=subset
    else:
        from scripts.game_data.memorypack.skill_root_components import root_reads
        expected=root_reads()[:last]
    if (declared != expected or not isinstance(declared, list)
            or any(type(r.get('memberIndex')) is not int for r in declared)):
        raise ValueError(LABEL + '.root:unproved-continuation-order')
    return expected


def encoded_tag(tag: int) -> bytes:
    if type(tag) is not int or not 0 <= tag <= 65535:
        raise ValueError(LABEL + '.tag:range')
    return bytes((tag,)) if tag < 250 else b'\xfa' + struct.pack('<H', tag)


def validate_program(row: dict[str, Any]) -> None:
    """Check a finite declared program; this grants no native admission."""
    required = {'family', 'tag', 'wrapperName', 'wrappedType', 'memberCount',
                'sourceOwner', 'reads', 'wrapperNullAdmitted'}
    if set(row) != required or row['family'] not in ('AbilityActionData', 'SelectorFinder',
            'SelectorValidator', 'SelectorPostProcessor'):
        raise ValueError(LABEL + '.program:shape')
    encoded_tag(row['tag'])
    if (type(row['memberCount']) is not int or not 0 <= row['memberCount'] < 250
            or type(row['wrapperNullAdmitted']) is not bool
            or not all(isinstance(row[k], str) and row[k] for k in ('wrapperName', 'wrappedType', 'sourceOwner'))
            or not isinstance(row['reads'], list) or len(row['reads']) != row['memberCount']):
        raise ValueError(LABEL + '.program:identity-or-count')
    for index, read in enumerate(row['reads']):
        if (set(read) != {'memberIndex', 'fieldName', 'kind', 'childCapability'}
                or type(read['memberIndex']) is not int or read['memberIndex'] != index or not isinstance(read['fieldName'], str)
                or not read['fieldName']):
            raise ValueError(LABEL + '.program:ordered-read')
        kind = read['kind']
        if not isinstance(kind, str) or kind not in ATOMIC_KINDS and kind not in PROFILE_METHODS and kind not in LIST_METHODS and kind not in ('sequence-profile', 'SequenceActionData'):
            raise ValueError(LABEL + '.program:unreviewed-kind=' + str(kind))
        atomic = kind in ATOMIC_KINDS
        if (read['childCapability'] is not None if atomic else
                not isinstance(read['childCapability'], str) or not read['childCapability']):
            raise ValueError(LABEL + '.program:child-capability')


class CurrentSequenceReader(Reader):
    """The operation supplies exact current route and child capability joins."""

    def __init__(self, data, source, limit, *, operation):
        super().__init__(data, source, limit)
        self.operation = operation

    def _capability(self, name):
        return self.operation.child(name)

    def _sequence(self, depth):
        claim = self._capability('SequenceActionData')
        if self.peek() == 255 and claim.get('nullAdmitted') is True:
            self.take(1, 'null-sequence')
            return
        if claim.get('wholeGrammarAdmitted') is not True:
            raise ValueError(LABEL + '.child:unproved-positive=SequenceActionData')
        if depth > SEQUENCE_RECURSION_LIMIT:
            raise ValueError(LABEL + '.sequence:depth-limit')
        self.header(3)
        if self.pos+4>self.limit:raise ValueError(LABEL+'.sequence:truncated-count')
        count=struct.unpack_from('<i',self.data,self.pos)[0]
        if claim.get('positiveCountsAdmitted')is True:
            maximum=claim.get('countLimit')
            if (type(maximum)is not int or not 17<=maximum<=10000
                    or claim.get('freshArrayCountInductionProved')is not True or count>maximum):
                raise ValueError(LABEL+'.sequence:unproved-count-bound')
        if count not in claim.get('collectionCounts',[])and not(count>0 and claim.get('positiveCountsAdmitted')is True):
            raise ValueError(LABEL+'.sequence:unproved-count='+str(count))
        actual=self.count(1,reserve=2,nullable=True)
        for _ in range(max(0,actual)):self.action(depth+1)
        self.take(1,'sequence-guard-flag');self.take(1,'sequence-main-character-flag')

    def _profile(self, method, capability,depth=0):
        claim = self._capability(capability)
        if method=='look_at_target_profile':
            from scripts.game_data.memorypack.skill_look_at_target_sources import CAPABILITY
            from scripts.game_data.memorypack.skill_look_at_target_codec import LookAtTargetReader
            if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-look-at-target-capability')
            LookAtTargetReader(self).record(depth)
            return
        if method=='camera_custom_profile':
            from scripts.game_data.memorypack.skill_camera_custom_components import CAPABILITY
            from scripts.game_data.memorypack.skill_camera_custom_codec import read
            if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-camera-custom-capability')
            read(self,capability,depth)
            return
        if method=='gait_single_dictionary_profile':
            from scripts.game_data.memorypack.skill_gait_dictionary_sources import CAPABILITY
            from scripts.game_data.memorypack.skill_gait_dictionary_codec import read
            if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-gait-dictionary-capability')
            read(self,depth)
            return
        if method=='raycast_record_profile':
            from scripts.game_data.memorypack.skill_raycast_record_codec import RaycastRecordReader
            RaycastRecordReader(self).record(capability,depth)
            return
        if method=='target_filter_profile':
            from scripts.game_data.memorypack.skill_target_filter_codec import TargetFilterReader,CAPABILITY
            if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-TargetFilter-capability')
            TargetFilterReader(self).read(depth)
            return
        if method=='camera_transition_profile':
            from scripts.game_data.memorypack.skill_camera_transition_codec import CameraTransitionReader
            from scripts.game_data.memorypack.skill_camera_transition_sources import CAPABILITY
            if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-camera-transition-capability')
            CameraTransitionReader(self).record(depth)
            return
        if method=='special_aim_profile':
            from scripts.game_data.memorypack.skill_special_aim_codec import SpecialAimReader,CAPABILITY
            if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-SpecialAim-capability')
            SpecialAimReader(self).union(depth)
            return
        if method=='ordinary_ability_map_profile':
            from scripts.game_data.memorypack.skill_ordinary_ability_map_codec import OrdinaryMapReader
            from scripts.game_data.memorypack.skill_ordinary_ability_map_sources import CAPABILITY
            if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-ordinary-ability-map-capability')
            OrdinaryMapReader(self).record(depth)
            return
        if method=='action_nested_record_profile':
            from scripts.game_data.memorypack.skill_action_nested_record_codec import NestedRecordReader
            NestedRecordReader(self).record(capability,depth)
            return
        if method=='action_geometry_profile':
            from scripts.game_data.memorypack.skill_action_geometry_codec import GeometryReader
            GeometryReader(self).record(capability,depth)
            return
        if method=='action_setting_profile':
            from scripts.game_data.memorypack.skill_action_setting_codec import ActionSettingReader
            ActionSettingReader(self).record(capability,depth)
            return
        if method=='hit_env_profile':
            from scripts.game_data.memorypack.skill_hit_env_codec import HitEnvReader,CAPABILITY
            if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-HitEnv-capability')
            HitEnvReader(self).read(depth)
            return
        if method in('effect_profile','damage_unit_profile','damage_union_profile','damage_list_profile'):
            if method=='effect_profile':
                from scripts.game_data.memorypack.skill_effect_codec import EffectReader,CAPABILITY
                if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-Effect-capability')
                EffectReader(self).effect(depth)
            elif method=='damage_unit_profile':
                from scripts.game_data.memorypack.skill_damage_codec import DamageUnitReader,CAPABILITY
                if capability!=CAPABILITY:raise ValueError(LABEL+'.child:wrong-DamageUnit-capability')
                DamageUnitReader(self).damage(depth)
            else:
                from scripts.game_data.memorypack.skill_damage_children_codec import DamageChildrenReader
                reader=DamageChildrenReader(self)
                (reader.union if method=='damage_union_profile'else reader.collection)(capability,depth)
            return
        if method=='curve_profile':
            if capability!='curve-profile':
                raise ValueError(LABEL+'.child:wrong-Unity-curve-capability')
            from scripts.game_data.memorypack.skill_animation_curve_codec import read_curve
            read_curve(self,capability)
            return
        if method in('root_record_profile','root_collection_profile','root_pooled_string_list_profile'):
            from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
            reader=RootChildrenReader(self)
            # Collection FF is part of a signed four-byte count; it must never
            # pass through the ordinary one-byte reference-null shortcut.
            if method=='root_record_profile':reader.record(capability,depth)
            elif method=='root_collection_profile':reader.collection(capability,depth)
            else:reader.pooled_strings(capability,depth)
            return
        if method != 'byte_payload' and self.peek() == 255:
            if claim.get('nullAdmitted')is not True:
                raise ValueError(LABEL+'.child:unproved-null='+capability)
            self.take(1, capability + '.null');return
        if claim.get('wholeGrammarAdmitted') is not True:
            raise ValueError(LABEL + '.child:unproved-positive=' + capability)
        if method == 'byte_payload':
            self.byte_payload()
            return
        if method == 'direction_profile':
            self._direction_body()
            return
        if method == 'selector_profile':
            self.selector_profile()
            return
        if method == 'buff_find_profile':
            if capability!='skill-root-buff-find-settings':
                raise ValueError(LABEL+'.child:wrong-BuffFind-capability')
            from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
            RootChildrenReader(self).record(capability)
            return
        if method == 'buff_filter_profile':
            from scripts.game_data.memorypack.skill_selector_buff_filter_components import CAPABILITY,TYPE,ORDER,CHILD_CAPABILITY
            if (capability!=CAPABILITY or claim.get('typeName')!=TYPE or type(claim.get('memberCount'))is not int
                    or claim['memberCount']!=2 or claim.get('orderedReads')!=ORDER):
                raise ValueError(LABEL+'.child:wrong-BuffFilter-program')
            self.header(2)
            self._profile('buff_find_profile',CHILD_CAPABILITY)
            self.take(4,'BuffFilterSettings.buffStackNumType.scalar32')
            return
        getattr(super(), method)()

    def _list(self, method, capability):
        claim = self._capability(capability)
        if self.pos + 4 > self.limit:
            raise ValueError(LABEL + '.list:truncated-count=' + capability)
        count = struct.unpack_from('<i', self.data, self.pos)[0]
        counts = claim.get('collectionCounts')
        if not isinstance(counts, list) or -1 not in counts and claim.get('nullable') is True:
            raise ValueError(LABEL + '.list:missing-count-capability=' + capability)
        if count not in counts and not (count > 0 and claim.get('positiveCountsAdmitted') is True):
            raise ValueError(LABEL + '.list:unproved-count=' + capability + ':' + str(count))
        if count > 10000:
            raise ValueError(LABEL + '.list:resource-bound=' + capability)
        if claim.get('positiveCountsAdmitted')is True:
            maximum=claim.get('countLimit')
            if type(maximum)is not int or not 0<=maximum<=10000 or count>maximum:
                raise ValueError(LABEL+'.list:unproved-count-bound='+capability)
        element = claim.get('elementCapability')
        if count > 0:
            if not isinstance(element, str) or not element:
                raise ValueError(LABEL + '.list:unproved-element=' + capability)
            self._capability(element)
        actual = self.count(1, nullable=claim.get('nullable') is True)
        for _ in range(max(0, actual)):
            if method.startswith('selector_'):
                getattr(self, method)()
            else:
                self._profile(method, element)

    def _run(self, row, depth, tag, width):
        validate_program(row)
        expected = encoded_tag(row['tag'])
        if tag != row['tag'] or width != len(expected) or self.data[self.pos:self.pos + width] != expected:
            raise ValueError(LABEL + '.route:tag-or-width')
        self.take(width, 'union-tag')
        if self.peek() == 255:
            if row['wrapperNullAdmitted'] is not True:
                raise ValueError(LABEL + '.route:unproved-wrapper-null')
            self.take(1, 'null-wrapper')
            return
        self.header(row['memberCount'])
        for read in row['reads']:
            kind = read['kind']; child = read['childCapability']
            if kind in ATOMIC_KINDS:
                self.take(ATOMIC_KINDS[kind], row['wrappedType'] + '.' + read['fieldName'] + '.' + kind)
            elif kind in PROFILE_METHODS:
                self._profile(PROFILE_METHODS[kind], child,depth+1)
            elif kind in LIST_METHODS:
                self._list(LIST_METHODS[kind], child)
            else:
                claim = self._capability(child)
                if self.peek() == 255 and claim.get('nullAdmitted') is True:
                    self.take(1, child + '.null')
                    continue
                if claim.get('wholeGrammarAdmitted') is not True:
                    raise ValueError(LABEL + '.child:unproved-positive=' + child)
                self.sequence(depth + 1)

    def _action(self, depth, tag, width):
        if depth > SEQUENCE_RECURSION_LIMIT:
            raise ValueError(LABEL + '.route:depth-limit')
        if tag == 255 and width == 1:
            self.operation.null_action()
            self.take(1, 'null-union')
            return
        row = self.operation.route('AbilityActionData', tag)
        self._run(row, depth, tag, width)

    def _selector(self, family):
        tag = self.peek()
        if tag == 255:
            self.operation.null_selector(family)
            self.take(1, 'null-selector-union')
            return
        if tag == 250:
            if self.pos + 3 > self.limit:
                raise ValueError(LABEL + '.selector:truncated-tag')
            tag = struct.unpack_from('<H', self.data, self.pos + 1)[0]
        width = len(encoded_tag(tag))
        row = self.operation.route(family, tag)
        self._run(row, 0, tag, width)

    def selector_finder_profile(self):
        self._selector('SelectorFinder')

    def selector_validator_profile(self):
        self._selector('SelectorValidator')

    def selector_postprocessor_profile(self):
        self._selector('SelectorPostProcessor')

    # Nested structural Reader calls cannot escape the selected child gates.
    def scalar_payload(self): self._profile('scalar_payload', 'scalar-payload')
    def vector_payload(self): self._profile('vector_payload', 'blackboard-vector3')
    def curve_profile(self): self._profile('curve_profile', 'curve-profile')
    def target_profile(self): self._profile('target_profile', 'target-profile')
    def direction_profile(self): self._profile('direction_profile', 'direction-profile')
    def skill_alert_profile(self): self._profile('skill_alert_profile', 'skill-alert-profile')
    def cost_profile(self): self._profile('cost_profile', 'cost-data')

    def byte_payload(self, *, reserve=0):
        claim = self._capability('byte-payload')
        if claim.get('wholeGrammarAdmitted') is not True:
            raise ValueError(LABEL + '.child:unproved-positive=byte-payload')
        start = self.pos
        if self.pos + 4 > self.limit:
            raise ValueError(LABEL + '.string:truncated-pool-index')
        index = struct.unpack_from('<i', self.data, self.pos)[0]
        # The operation owns the actual selected export pool, including the
        # distinct empty/null sentinels. A nominal string type is insufficient.
        value=self.operation.pool_index(index)
        self.take(4, 'string-pool-index-i32')
        self.records.append(dict(start=start, end=self.pos, kind='anonymous-byte-payload',
            poolIndex=index, isNull=index == -2))
        return value

    def selector_profile(self):
        claim = self._capability('selector-profile')
        if self.peek() == 255 and claim.get('nullAdmitted') is True:
            self.take(1, 'null-selector-profile')
            return
        if claim.get('wholeGrammarAdmitted') is not True:
            raise ValueError(LABEL + '.child:unproved-positive=selector-profile')
        self.header(3)
        self.selector_finder_profile()
        self._list('selector_postprocessor_profile', 'target-postprocessor-list')
        self._list('selector_validator_profile', 'target-validator-list')

    def _direction_body(self):
        start=self.pos;self.header(8)
        self.take(2,'direction-leading-flags');self.take(4,'direction-kind');self.take(1,'direction-extra-flag')
        for _ in range(2):
            # Both FF and nonnull targets pass the selected child capability.
            self.target_profile();self.take(4,'direction-target-kind')
        self.records.append(dict(start=start,end=self.pos,kind='anonymous-direction-profile'))

    def force_sync(self):
        claim=self._capability('ForceSyncAnimData');start=self.pos
        if self.peek()==255 and claim.get('nullAdmitted')is True:self.take(1,'null-force-sync')
        else:
            if claim.get('wholeGrammarAdmitted')is not True:raise ValueError(LABEL+'.child:unproved-positive=ForceSyncAnimData')
            self.header(4);self.take(1,'force-sync-flag');self.byte_payload()
            self.take(4,'force-sync-playback-speed');self.take(4,'force-sync-target-frame')
        self.records.append(dict(start=start,end=self.pos,kind='force-sync'))

    def timeline_record(self):
        claim=self._capability('TimelineActionData');start=self.pos
        if self.peek()==255 and claim.get('nullAdmitted')is True:self.take(1,'null-timeline-record')
        else:
            if claim.get('wholeGrammarAdmitted')is not True:raise ValueError(LABEL+'.child:unproved-positive=TimelineActionData')
            self.header(4);self.take(4,'timeline-end-frame');self.sequence()
            self.take(4,'timeline-start-frame');self.force_sync()
        self.records.append(dict(start=start,end=self.pos,kind='timeline-record'))

    def _bounded_count(self,counts,label,*,positive=False,maximum=None,induction=False):
        if self.pos+4>self.limit:raise ValueError(LABEL+'.'+label+':truncated-count')
        count=struct.unpack_from('<i',self.data,self.pos)[0]
        if positive:
            if (type(maximum)is not int or not 17<=maximum<=10000 or induction is not True
                    or counts!=[-1,0]or any(type(n)is not int for n in counts)or count>maximum):
                raise ValueError(LABEL+'.'+label+':unproved-count-bound')
        if count not in counts and not(count>0 and positive):raise ValueError(LABEL+'.'+label+':unproved-count='+str(count))
        return self.count(1,nullable=True)

    def action_group(self):
        claim=self._capability('ActionGroupData');start=self.pos
        if self.peek()==255 and claim.get('nullAdmitted')is True:
            self.take(1,'null-action-group');return dict(start=start,end=self.pos,passiveEventActionsCount=None,timelineActionsCount=None)
        if claim.get('wholeGrammarAdmitted')is not True:raise ValueError(LABEL+'.child:unproved-positive=ActionGroupData')
        self.header(2)
        passive=self._bounded_count(claim.get('passiveCounts',[]),'passive-list',
            positive=claim.get('passivePositiveCountsAdmitted')is True,maximum=claim.get('passiveCountLimit'),
            induction=claim.get('passiveListCountInductionProved'))
        if passive>0 and claim.get('passiveElementsAdmitted')is not True:
            raise ValueError(LABEL+'.child:unproved-positive=AbilityActionMap')
        for _ in range(max(0,passive)):self.passive_map()
        timeline=self._bounded_count(claim.get('timelineCounts',[]),'timeline-list',
            positive=claim.get('timelinePositiveCountsAdmitted')is True,maximum=claim.get('timelineCountLimit'),
            induction=claim.get('timelineListCountInductionProved'))
        for _ in range(max(0,timeline)):self.timeline_record()
        self.records.append(dict(start=start,end=self.pos,kind='action-group'))
        return dict(start=start,end=self.pos,passiveEventActionsCount=passive,timelineActionsCount=timeline)

    def passive_map(self):
        claim=self._capability('AbilityActionMap');start=self.pos
        if self.peek()==255:
            if claim.get('nullAdmitted')is not True:
                raise ValueError(LABEL+'.child:unproved-null=AbilityActionMap')
            self.take(1,'null-passive-map')
            self.records.append(dict(start=start,end=self.pos,kind='passive-map',isNull=True))
            return
        if claim.get('wholeGrammarAdmitted')is not True or claim.get('memberCount')!=2:
            raise ValueError(LABEL+'.child:unproved-positive=AbilityActionMap')
        self.header(2)
        event=struct.unpack('<i',self.take(4,'AbilityActionMap.abilityEvent.enum32'))[0]
        name=claim.get('sequenceArrayCapability');array=self._capability(name)
        if (array.get('elementType')!='Beyond.Gameplay.Core.SequenceActionData'
                or array.get('elementCapability')!='SequenceActionData'
                or array.get('nullable')is not True):
            raise ValueError(LABEL+'.child:unproved-array='+str(name))
        count=self._bounded_count(array.get('collectionCounts',[]),'passive-sequence-array')
        for _ in range(max(0,count)):self.sequence(0)
        self.records.append(dict(start=start,end=self.pos,kind='passive-map',
            isNull=False,abilityEvent=event,sequenceCount=count))

    def root_continuation(self, fields):
        claim = self._capability('SkillDataContinuation')
        reads = validate_continuation(claim)
        for read in reads:
            index, name, kind, child = (read[k] for k in
                ('memberIndex', 'fieldName', 'kind', 'childCapability'))
            start = self.pos
            if kind in ('int32', 'enum32'):
                value = struct.unpack('<i', self.take(4, 'SkillData.' + name + '.' + kind))[0]
            elif kind=='bool-byte':value=bool(self.take(1,'SkillData.'+name+'.bool-byte')[0])
            elif kind in('single-bits','vector3-raw12'):
                value=dict(bitsHex=self.take(4 if kind=='single-bits'else 12,'SkillData.'+name+'.'+kind).hex())
            elif kind=='pooled-string':
                try:value=self.byte_payload()
                except ValueError as error:
                    raise ValueError(f'{LABEL}.root:member={index}:field={name}:offset={start}:source={self.source}:{error}')from error
            elif kind in('value-list','record-list','record','record-union'):
                from scripts.game_data.memorypack.skill_root_children_codec import RootChildrenReader
                children=RootChildrenReader(self)
                try:
                    if kind=='record-union':result=children.union(child)
                    elif kind=='record':result=children.record(child)
                    else:result=children.collection(child)
                except ValueError as error:
                    raise ValueError(f'{LABEL}.root:member={index}:field={name}:offset={start}:source={self.source}:{error}')from error
                value=result.get('count')if kind in('value-list','record-list')else None
            elif kind=='sequence-profile':
                try:self.sequence()
                except ValueError as error:
                    raise ValueError(f'{LABEL}.root:member={index}:field={name}:offset={start}:source={self.source}:{error}')from error
                value=None
            elif kind == 'null-empty-value-list':
                cap = self._capability(child)
                if (cap.get('closedListType') != 'System.Collections.Generic.List`1<Beyond.Blackboard+DataPair>'
                        or cap.get('elementType') != 'Beyond.Blackboard+DataPair'
                        or cap.get('elementValueType') is not True
                        or cap.get('collectionCounts') != [-1, 0]
                        or any(type(n) is not int for n in cap['collectionCounts'])
                        or cap.get('nullable') is not True
                        or cap.get('positiveCountsAdmitted') is not False
                        or cap.get('elementGrammarAdmitted') is not False):
                    raise ValueError(LABEL + '.root:unproved-list-capability=' + child)
                value = self._bounded_count(cap['collectionCounts'], 'root-' + name)
            elif kind=='null-reference':
                cap = self._capability(child)
                if (cap.get('typeName') != 'Beyond.Gameplay.Core.BuffInputBase'
                        or cap.get('nullAdmitted') is not True
                        or cap.get('positiveGrammarAdmitted') is not False
                        or type(cap.get('marker')) is not int or cap['marker'] != 255
                        or type(cap.get('wireBytes')) is not int or cap['wireBytes'] != 1):
                    raise ValueError(LABEL + '.root:unproved-null-capability=' + child)
                if self.peek() != 255:
                    raise ValueError(LABEL + '.root:unproved-positive=' + child)
                self.take(1, 'SkillData.' + name + '.null')
                value = None
            else:raise ValueError(LABEL+'.root:unproved-kind='+str(kind))
            fields.append(dict(memberIndex=index, fieldName=name, kind=kind,
                start=start, end=self.pos, value=value))


def decode_current_action(data, offset, *, operation, limit=None):
    """Decode one selected action; the operation owns native freshness bookends."""
    from scripts.game_data.skill_timeline_current_sequence_native import prepared_current_sequence
    selected = prepared_current_sequence(operation)
    end = len(data) if limit is None else limit
    if type(offset) is not int or type(end) is not int or not 0 <= offset < end <= len(data):
        raise ValueError(LABEL + '.cursor:bounds')
    reader = CurrentSequenceReader(data, LABEL, end, operation=selected)
    reader.pos = offset; reader.action(0)
    return dict(start=offset, end=reader.pos, records=reader.records, ranges=reader.ranges), reader.pos


def decode_current_skill_prefix(data,*,operation,source=LABEL):
    """Finite source-owned root49; only all fields plus physical EOF can close it."""
    from scripts.game_data.skill_timeline_current_sequence_native import prepared_current_sequence
    selected=prepared_current_sequence(operation);claim=selected.child('SkillDataPrefix')
    reader=CurrentSequenceReader(data,source,len(data),operation=selected)
    whole_group=False;whole_root=False;group=None;reason=None;fields=[]
    try:
        if claim.get('wholeGrammarAdmitted')is not True or claim.get('memberCount')!=49:
            raise ValueError(LABEL+'.root:unproved-current-root49')
        reader.header(49);group=reader.action_group();whole_group=True
        fields.append(dict(memberIndex=0,fieldName='actionGroupData',kind='ActionGroupData',
            start=1,end=reader.pos))
        reader.root_continuation(fields)
        if len(fields)==49 and [field['memberIndex']for field in fields]==list(range(49)):
            complete=selected.child('SkillDataComplete')
            expected=dict(memberCount=49,firstMemberIndex=0,lastMemberIndex=48,
                completeSelectedReturnProved=True,allRootChildSourceJoinsProved=True,
                actionGroupUsesSelectedFinitePrograms=True,physicalEofRequired=True,
                existingRootWrapperRequired=True,newOrNullRootAdmitted=False,
                runtimeSelectionObserved=False,wholeTypeAllPossibleRoutesAdmitted=False)
            if complete!=expected or any(type(complete.get(k))is not type(v)for k,v in expected.items()):
                raise ValueError(LABEL+'.root:unproved-complete-source-capability')
            if reader.pos!=reader.limit:
                raise ValueError(f'{LABEL}.root:physical-EOF-required:offset={reader.pos}:remaining={reader.limit-reader.pos}:source={source}')
            whole_root=True
        else:
            reason=LABEL+'.tail:unproved-current-SkillData-member'+str(fields[-1]['memberIndex']+1)+'-through48'
    except ValueError as error:reason=str(error)
    return dict(status='exact-current-skill'if whole_root else('exact-current-prefix' if len(fields)>1 else 'exact-field0-prefix')if whole_group else'unsupported-current-prefix',
        skillDataMemberCount=49,parserCursor=reader.pos,hardLimit=len(data),
        byteRanges=reader.ranges,records=reader.records,actionGroup=group,
        rootFields=fields,lastCompleteMemberIndex=fields[-1]['memberIndex']if fields else None,
        timelineRecordsExact=sum(r['kind']=='timeline-record'for r in reader.records),
        wholeActionGroupDataExact=whole_group,wholeSkillDataExact=whole_root,stopReason=reason,
        evidenceBoundary='structuralOnly')
