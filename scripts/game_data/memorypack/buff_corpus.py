"""Current VFS BuffData provenance and anonymous suffix-candidate census.

The legacy reader's field labels are not promoted to serialization semantics.
All matching filename-string anchors are retained, including rejected anchors.

Promotion is narrow: only singleton rows with a selected-native 30-member
forward receipt from byte zero to EOF, with source-ID equality, are promoted.
The admitted cohorts are strict null/empty recursive lists, the bounded
authenticated DataPair lists, shared AttributeModifierData arrays and reviewed
GlobalModifier branch, the selected single
damage condition/processor combinations whose child receipts are the
``buff_damage_*`` modules, and the sole selected CreateBuff action (replayed
separately by ``buff_create_action_root_corpus``). Every other row keeps its
structural or nested blocker; nothing here names the whole BuffData schema.
Four distinct reviewed source paths also compose their positive-heal,
BreakPassingSmallSceneObject event-map, attribute-plus-empty-condition/tag-ten,
or recursive sword damage child receipts through all 30 fields. Their selected diagnostics stay
nonpublishable by themselves; only this complete gate admits exact rows.
The selected native audit and every helper, contract and native input are
rechecked before and after the scan.

The denominator is the complete authenticated outer ledger with decrypted
stream bytes, under the shared ``corpus_gate`` provenance guards.  Every
reader-accepted EOF suffix candidate is retained rather than inheriting the
legacy reader's anchor selection, and a unique accepted suffix still does not
establish its top-level ownership or certify its internal opaque regions.
The legacy prefix reader rejects an invalid anchor limit instead of clamping
it and receives only the bytes before the anchor, so its count, string and
scalar helpers cannot borrow suffix bytes; each accepted suffix records its
prefix endpoint or unsupported-action stop and the remaining gap, without
certifying the legacy field labels.  The residual Buff gap is nested
semantics inside structurally bounded anonymous event/action bodies, not an
outer-frame cursor failure.

Run ``python -m scripts.game_data.memorypack.buff_corpus
--expected-input-set-sha256 <VFS audit value> --output-json
reports/animestudio/buffdata_current_latest.json --output-md
reports/animestudio/buffdata_current_latest.md``. That report is the
``--buff-report`` every Buff receipt and ``jsondata_corpus`` read, and it is
the first gate of the chain vfs-audit, ``buff_corpus``, ``skill_corpus``,
``jsondata_corpus``.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import struct
from collections import Counter
from pathlib import Path

from scripts.game_data.memorypack import corpus_gate as vfs
from scripts.game_data.memorypack.buff import (
    buff_post_id_result_is_exact_tail,
    decode_buff_post_id_prefix_at,
    decode_buff_pre_id_modifier_prefix,
)
from scripts.game_data.memorypack.buff_actions import event_prefix
from scripts.game_data.memorypack.buff_icon_config import validate_current_native_contract
from scripts.game_data.memorypack import buff_named_schema
from scripts.game_data.memorypack import buff_attribute_modifier
from scripts.game_data.memorypack import buff_root_no_positive
from scripts.game_data.memorypack import buff_event_maps
from scripts.game_data.memorypack import buff_root_no_positive_native
from scripts.game_data.memorypack import buff_selected_roots
from scripts.game_data.memorypack import buff_datapair_native
from scripts.game_data.memorypack import buff_global_modifier_receipt
from scripts.game_data.memorypack import buff_damage_modifier_receipt
from scripts.game_data.memorypack import buff_damage_scale_processor_child_receipt
from scripts.game_data.memorypack import buff_damage_modify_calc_result_processor_child_receipt
from scripts.game_data.memorypack import buff_damage_instant_modify_attribute_processor_receipt
from scripts.game_data.memorypack import buff_damage_scalar_processor_child_receipt
from scripts.game_data.memorypack import buff_damage_text_processor_child_receipt
from scripts.game_data.memorypack import buff_damage_two_action_condition_receipt
from scripts.game_data.memorypack import buff_damage_sequence_action_condition_receipt
from scripts.game_data.memorypack import buff_damage_check_decorate_mask_condition_receipt
from scripts.game_data.memorypack import buff_damage_check_type_condition_receipt
from scripts.game_data.memorypack import buff_damage_check_type_mask_condition_receipt
from scripts.game_data.memorypack import buff_damage_check_tag_match_condition_receipt
from scripts.game_data.memorypack import buff_damage_check_main_character_condition_receipt
from scripts.game_data.memorypack import buff_damage_check_buff_stack_condition_receipt
from scripts.game_data.memorypack import buff_damage_check_vitals_condition_receipt
from scripts.game_data.memorypack import buff_damage_origin_or_condition_receipt
from scripts.game_data.memorypack import buff_damage_known_compound_condition_receipt
from scripts.game_data.memorypack import buff_damage_if_else_condition_receipt
from scripts.game_data.memorypack import buff_damage_not_next_main_condition_receipt
from scripts.game_data.memorypack import buff_damage_two_direction_angle_condition_receipt
from scripts.game_data.memorypack import buff_if_else_action_receipt
from scripts.game_data.memorypack import buff_target_settings_child_receipt
from scripts.game_data.memorypack import buff_direction_settings_child_receipt
from scripts.game_data.memorypack import buff_selector_data_child_receipt
from scripts.game_data.memorypack import buff_find_settings_child_receipt
from scripts.game_data.memorypack import buff_create_action_root_corpus
from scripts.game_data.memorypack import buff_create_action_root_receipt
from scripts.game_data.memorypack import buff_create_icon_duration_child_receipt
from scripts.game_data.memorypack import buff_create_input_child_receipt
from scripts.game_data.memorypack.buff_adding_cooldown import (
    CHILD_CONTRACT_PATH as ADDING_COOLDOWN_CHILD_CONTRACT_PATH,
    CONTRACT_PATH as ADDING_COOLDOWN_CONTRACT_PATH,
    DEFAULT_DUMMYDLL_ROOT as ADDING_COOLDOWN_DUMMYDLL_ROOT,
    ROOT_CONTRACT_PATH as ADDING_COOLDOWN_ROOT_CONTRACT_PATH,
    decode_adding_cooldown,
    validate_current_native_contract as validate_adding_cooldown_native_contract,
)
from scripts.game_data.memorypack.buff_dispel_config import (
    CONTRACT_PATH as DISPEL_CONFIG_CONTRACT_PATH,
    ROOT_CONTRACT_PATH as DISPEL_CONFIG_ROOT_CONTRACT_PATH,
    decode_dispel_config,
    validate_current_native_contract as validate_dispel_config_native_contract,
)
from scripts.game_data.memorypack.buff_stacking_compact_native import (
    CONTRACT_PATH as STACKING_COMPACT_CONTRACT_PATH,
    ROOT_CONTRACT_PATH as STACKING_COMPACT_ROOT_CONTRACT_PATH,
    decode_stacking_settings_compact,
    validate_current_native_contract as validate_stacking_compact_native_contract,
)
from scripts.game_data.memorypack.buff_timeline_empty_native import (
    CONTRACT_PATH as TIMELINE_EMPTY_CONTRACT_PATH,
    ROOT_CONTRACT_PATH as TIMELINE_EMPTY_ROOT_CONTRACT_PATH,
    decode_empty_timeline_suffix,
    validate_current_native_contract as validate_timeline_empty_native_contract,
)
from scripts.game_data.memorypack.buff_residual_actions import (
    frame_buff_named_middle,
    root_continuation,
    validate_current_native_contract as validate_residual_native_contract,
)
from scripts.game_data import buff_frontiers_native as buff_frontiers
from scripts.common import canonical_json_sha256

PREFIX='Data/Json/BuffData/'
PATTERN=re.compile(r'^Data/Json/BuffData/[^/]+[.]json$')
BOUNDARY=('Authenticated current VFS logical bytes and the current generated 30-field wrapper order. '
          'The first six fields and supported middle fields advance real cursors; the accepted id marker '
          'starts the named field-15-to-29 suffix that closes at EOF. The null/empty timeline list joins the '
          'following exact tail under selected native ownership; positive timeline bodies retain their structural endpoint. Most positive modifier lists and nested '
          'damage/heal modifier and action bodies remain explicit opaque or unsupported boundaries. Positive '
          'globalModifier lists attach a selected-build child receipt at field 10 while the parent BuffData '
          'row remains partial. The nested '
          '19-member iconConfig and raw-eight dispelConfig children are exact under their current-build native contracts. '
          'A strict selected-native subset of null/empty recursive-list rows, authenticated DataPair lists, shared AttributeModifierData arrays, the reviewed GlobalModifier branch, and selected damage branches with an empty condition plus tag five or ordered [5,6] processors, one CheckDamageDecorateMask or CheckDamageType action plus tag five or ten, one CheckDamageTypeMask, simple CheckTagMatch, simple CheckMainCharacterCondition, selected CheckBuffStackNumAdvanced, simple CheckHp or simple CheckPoiseValue action plus tag five, one CheckBuffStackNumAdvanced action plus tag nine, one CheckDamageDecorateMask action plus scalar tag zero, two or three, one simple CheckTagMatch action plus scalar tag zero or three, the ordered CheckDamageDecorateMask/CheckDamageTypeMask condition pair, two selected OriginSkillType compound conditions, two selected known-action compound conditions, or the selected nested IfElseAction conditions plus tag five, one NotNextCheckAction/main-character pair plus scalar tag four, and the selected two CheckTwoDirectionAngle actions plus ordered [5,6] processors receives a 30-member byte-zero-to-EOF receipt; '
          'A sole selected CreateBuff action with exact named children also admits a narrow 30-member root replay through EOF; '
          'Four distinct source-bound positive-heal, BreakPassingSmallSceneObject event-map, attribute-plus-empty-condition/tag-ten, and recursive sword damage roots also compose named children through all thirty fields under current input pins; their standalone diagnostics remain nonpublishable. '
          'only those VFS-ledger-MD5-matched rows are whole-schema exact, with their SHA256 recorded for later export replay. '
          'Runtime behavior and other BuffData files remain unresolved.')


def _profile_boundary(profile, *, file_length):
    if profile is None:return None
    if not all(key in profile for key in ('status','consumedEnd','readLimit')):return profile
    status=profile['status']
    profile['boundaryClass']={'supported-prefix':'structural-prefix',
        'unsupported':'unsupported','failed':'failed'}.get(status,'unsupported')
    cursor=profile['consumedEnd'];hard_limit=profile['readLimit']
    profile['parserCursor']=cursor;profile['hardLimit']=hard_limit
    opaque=[]
    if cursor<hard_limit:opaque.append({'start':cursor,'end':hard_limit,'kind':'opaque-before-hard-limit'})
    if hard_limit<file_length:opaque.append({'start':hard_limit,'end':file_length,'kind':'opaque-after-hard-limit'})
    profile['opaqueByteRanges']=opaque
    for record in profile.get('completedRecords',[]):
        if record.get('kind')=='union':
            record['boundaryClass']='exact-closed'
            record['hardLimit']=hard_limit
    profile['exactClosedActionRecords']=sum(
        record.get('kind')=='union' for record in profile.get('completedRecords',[]))
    return profile


def select_rows(rows, *, expected_input):
    return vfs.family_rows(rows,expected_input=expected_input,prefix=PREFIX,pattern=PATTERN,label='buff')


def decode_blackboard_datapair_list(data: bytes, start: int, end: int, *,
                                    native_validation: dict) -> dict:
    """Compatibility wrapper for the shared DataPair list reader."""
    return buff_datapair_native.decode_datapair_list(
        data, start, end, native_validation=native_validation,
    )


def frame_candidates(
    data: bytes, *, source: str,
    adding_cooldown_native_validation: dict | None = None,
    dispel_config_native_validation: dict | None = None,
    stacking_compact_native_validation: dict | None = None,
    timeline_empty_native_validation: dict | None = None,
    datapair_native_validation: dict | None = None,
    global_modifier_native_validation: dict | None = None,
) -> dict:
    result={'wholeSchemaExact':False,'candidates':[],'candidateCount':0,
            'eventPrefixStatus':'unsupported','rootContinuationStatus':'unsupported'}
    if not data or data[0]!=30:
        return {**result,'coverageStatus':'unsupported','diagnostic':{'source':source,'offset':0,'expected':30,'actual':data[0] if data else None}}
    value=Path(source).stem;encoded=value.encode('utf-8')
    marker=len(encoded).to_bytes(4,'little')+encoded
    positions=[];start=1
    while (start:=data.find(marker,start))>=0:
        positions.append(start);start+=1
        if len(positions)>64:
            return {**result,'coverageStatus':'unsupported','diagnostic':{'source':source,'offset':start-1,'expected':'at most 64 anchors; no subset selection','actual':'>64'}}
    for at in positions:
        decoded=decode_buff_post_id_prefix_at(data,value,at)
        accepted=buff_post_id_result_is_exact_tail(decoded)
        end=decoded.get('endOffset')
        if accepted and (not isinstance(end,str) or int(end,0)!=len(data)):
            vfs._fail('buff-reader-false-eof',source=source,offset=at,expected=len(data),actual=end)
        prefix_probe=None;current_prefix=None;continuation=None;named_middle=None;named_suffix=None
        if accepted:
            stacking_child = None
            tag_child = None
            timeline_empty_child = None
            if (stacking_compact_native_validation or {}).get('status') == 'validated':
                stacking = decoded.get('stackingSettings') or {}
                tags = decoded.get('tagsAfterTriggerExtendBuffAction') or {}
                if not stacking or not tags:
                    vfs._fail('buff-stacking-compact-child-missing', source=source,
                              offset=at, expected='stackingSettings and following GameplayTag array', actual=decoded.get('status'))
                stacking_child = decode_stacking_settings_compact(
                    data, int(stacking['offset'], 0),
                    native_validation=stacking_compact_native_validation,
                )
                tag_start = int(tags['offset'], 0)
                tag_end = int(tags['consumedEnd'], 0)
                timeline_start = int(decoded['timelineActionsCountOffset'], 0)
                if stacking_child['consumedEnd'] != tag_start or tag_end != timeline_start:
                    vfs._fail('buff-stacking-compact-child-join', source=source,
                              offset=stacking_child['consumedEnd'], expected=[tag_start, timeline_start], actual=tag_end)
                tag_child = {'status': 'exact-raw-array', 'startOffset': tag_start,
                             'consumedEnd': tag_end, 'count': tags['count'],
                             'tagIdsRaw': tags['tagIdsRaw'],
                             'boundary': 'Selected native raw GameplayTag array; no tag names or runtime meaning.'}
            if ((timeline_empty_native_validation or {}).get('status') == 'validated'
                    and decoded.get('timelineActionsCount') in (-1, 0)):
                timeline_start = int(decoded['timelineActionsCountOffset'], 0)
                timeline_empty_child = decode_empty_timeline_suffix(
                    data, timeline_start,
                    native_validation=timeline_empty_native_validation,
                )
                tag_end = int(decoded['tagsAfterTriggerExtendBuffAction']['consumedEnd'], 0)
                trigger_start = int(decoded['triggerInterval']['offset'], 0)
                if (tag_end != timeline_start
                        or timeline_empty_child['count'] != decoded['timelineActionsCount']
                        or timeline_empty_child['followingStart'] != trigger_start
                        or timeline_empty_child['followingEnd'] != len(data)):
                    vfs._fail('buff-timeline-empty-child-join', source=source,
                              offset=timeline_start, expected=[tag_end, trigger_start, len(data)],
                              actual=[timeline_empty_child['count'],
                                      timeline_empty_child['followingStart'],
                                      timeline_empty_child['followingEnd']])
            current_prefix=event_prefix(data,source=source,limit=at)
            _profile_boundary(current_prefix,file_length=len(data))
            if current_prefix['status']=='supported-prefix':
                continuation=root_continuation(
                    data,source=source,start=current_prefix['consumedEnd'],limit=at,
                )
                _profile_boundary(continuation,file_length=len(data))
                if (adding_cooldown_native_validation or {}).get('status') == 'validated':
                    named = next((field for field in continuation['namedFields']
                                  if field['index'] == 1 and field['name'] == 'addingCooldown'), None)
                    if named is not None:
                        try:
                            named['nestedProfile'] = decode_adding_cooldown(
                                data, named['start'], named['end'],
                                native_validation=adding_cooldown_native_validation,
                            )
                        except ValueError as exc:
                            vfs._fail('buff-adding-cooldown-child', source=source,
                                      offset=named['start'], expected='exact named child cursor',
                                      actual=str(exc))
                if continuation['status']=='supported-prefix':
                    if (datapair_native_validation or {}).get('status') == 'validated':
                        named = next((field for field in continuation['namedFields']
                                      if field['index'] == 4 and field['name'] == 'blackboard'), None)
                        if named is not None:
                            try:
                                start, end = named['start'], named['end']
                                named['nestedProfile'] = decode_blackboard_datapair_list(
                                    data, start, end,
                                    native_validation=datapair_native_validation,
                                )
                            except (ValueError, IndexError, struct.error) as exc:
                                vfs._fail('buff-datapair-child', source=source,
                                          offset=named.get('start'),
                                          expected='exact blackboard DataPair list cursor',
                                          actual=str(exc))
                    named_middle=frame_buff_named_middle(
                        data,continuation['consumedEnd'],at,
                    )
                    if (dispel_config_native_validation or {}).get('status') == 'validated':
                        named = next((field for field in named_middle.get('namedFields', [])
                                      if field['index'] == 7 and field['name'] == 'dispelConfig'), None)
                        if named is not None:
                            try:
                                named['nestedProfile'] = decode_dispel_config(
                                    data, named['start'], named['end'],
                                    native_validation=dispel_config_native_validation,
                                )
                            except ValueError as exc:
                                vfs._fail('buff-dispel-config-child', source=source,
                                          offset=named['start'], expected='exact named raw-eight child',
                                          actual=str(exc))
                    if (global_modifier_native_validation or {}).get('status') == 'validated':
                        named = next((field for field in named_middle.get('namedFields', [])
                                      if field['index'] == 10 and field['name'] == 'globalModifier'), None)
                        if named is not None and named.get('count', 0) > 0:
                            try:
                                named['nestedProfile'] = buff_global_modifier_receipt.decode_global_modifier_collection(
                                    data, named['start'], named['end'], source=source,
                                    native_validation=global_modifier_native_validation,
                                    blackboard_native_validation=adding_cooldown_native_validation,
                                )
                            except (ValueError, IndexError, struct.error) as exc:
                                vfs._fail('buff-global-modifier-child', source=source,
                                          offset=named.get('start'),
                                          expected='exact positive globalModifier child cursor',
                                          actual=str(exc))
            prefix=decode_buff_pre_id_modifier_prefix(data,at)
            prefix_end=prefix.get('endOffset')
            stop=int(prefix_end,0) if isinstance(prefix_end,str) else None
            if stop is not None and not 1<=stop<=at:
                vfs._fail('buff-prefix-range-overlap',source=source,offset=stop,expected=f'1 <= end <= {at}',actual=stop)
            prefix_probe={'readerStatus':prefix['status'],'readerEnd':stop,
                'readerAcceptedPrefix':prefix['status']=='parsed-through-attribute-modifier',
                'remainingGapRange':[stop,at] if stop is not None else None,
                'diagnostic':prefix.get('error') or prefix.get('abilityEventActionDecodeError'),
                'semanticStatus':'structural-only; legacy labels not promoted'}
            named_suffix={
                'status':'named-exact-to-eof',
                'startOffset':at,
                'endOffset':len(data),
                'namedFieldOrder':[
                    'id','igniteEventAction','ignoreCooldownWhenAdding','ignoreTagImmune',
                    'lifeType','maxTriggerCnt','onlyUseSelfTimeDilation','poiseModifier',
                    'shieldConfigs','stackingSettings','tagsAfterTriggerExtendBuffAction',
                    'timelineActions','triggerInterval','useTimeDilationDt',
                    'waitFirstTriggerInterval',
                ],
                'opaqueNestedRanges':buff_named_schema.suffix_opaque_ranges(decoded,length=len(data)),
                'fieldOrderSource':'current generated BuffDataForMemoryPack setter order',
                'stackingSettingsNativeChild':stacking_child,
                'tagArrayNativeChild':tag_child,
                'timelineEmptyNativeChild':timeline_empty_child,
                'opaqueNestedFields':[
                    name for name,key in (
                        ('igniteEventAction','igniteEventActionBodyStatus'),
                        ('poiseModifier','poiseModifierBodyStatus'),
                        ('shieldConfigs','shieldConfigsBodyStatus'),
                        ('timelineActions','timelineActionsBodyStatus'),
                    ) if decoded.get(key)
                ] + (['stackingSettings.stackEffects']
                     if (decoded.get('stackingSettings') or {}).get('stackEffectsCount', 0) > 0 else []),
                'boundary':(
                    'The unique accepted id marker and sequential named suffix reader close at EOF; '
                    'reported opaque child bodies do not gain nested field semantics.'
                ),
            }
        selected_profile=continuation or current_prefix
        candidate_class=(selected_profile or {}).get('boundaryClass','rejected-anchor')
        result['candidates'].append({'anchorOffset':at,'suffixStart':at+len(marker),
            'readerStatus':decoded.get('status'),'readerTailStatus':decoded.get('tailParseStatus'),
            'readerAcceptedThroughEof':accepted,'readerEndOffset':end,
            'opaquePrefixRange':[1,at],
            'readerInternalOpaqueRangesCertified':False,
            'boundaryClass':candidate_class,
            'startOffset':selected_profile.get('startOffset',0) if selected_profile else 0,
            'hardLimit':at,
            'parserCursor':selected_profile.get('parserCursor') if selected_profile else None,
            'byteRanges':selected_profile.get('ranges',[]) if selected_profile else [],
            'opaqueByteRanges':selected_profile.get('opaqueByteRanges',[]) if selected_profile else [],
            'exactClosedActionRecords':sum(profile.get('exactClosedActionRecords',0)
                for profile in (current_prefix,continuation) if profile),
            'prefixProbe':prefix_probe,
            'currentEventPrefix':current_prefix,
            'currentRootContinuation':continuation,
            'currentNamedMiddle':named_middle,
            'currentNamedSuffix':named_suffix,
            'diagnostic':decoded.get('tailParseError') or decoded.get('error')})
        candidate=result['candidates'][-1]
        if accepted:
            candidate['opaqueByteRanges']=buff_named_schema.compose_opaque_ranges(candidate,length=len(data))
            candidate['namedSchemaReceipt']=buff_named_schema.named_schema_receipt(
                candidate,source=source,length=len(data))
    count=sum(row['readerAcceptedThroughEof'] for row in result['candidates'])
    current=[c['currentEventPrefix'] for c in result['candidates'] if c['currentEventPrefix'] is not None]
    event_status=('failed' if any(c['status']=='failed' for c in current) else
                  'ambiguous' if count>1 else
                  'success' if count==1 and current[0]['status']=='supported-prefix' else 'unsupported')
    continuations=[c['currentRootContinuation'] for c in result['candidates'] if c['currentRootContinuation'] is not None]
    root_status=('failed' if event_status=='failed' or any(c['status']=='failed' for c in continuations) else
                 'ambiguous' if count>1 else
                 'success' if count==1 and len(continuations)==1 and continuations[0]['status']=='supported-prefix' else 'unsupported')
    boundary_class=('failed' if root_status=='failed' else 'ambiguous' if root_status=='ambiguous' else
                    'structural-prefix' if root_status=='success' else 'unsupported')
    accepted_candidates=[candidate for candidate in result['candidates'] if candidate['readerAcceptedThroughEof']]
    named_outer_frame=(
        len(accepted_candidates)==1
        and (accepted_candidates[0].get('currentNamedMiddle') or {}).get('status')=='named-through-iconConfig'
        and (accepted_candidates[0].get('currentNamedMiddle') or {}).get('iconConfigStatus')=='exact'
        and (accepted_candidates[0].get('currentNamedSuffix') or {}).get('status')=='named-exact-to-eof'
    )
    return {**result,'candidateCount':count,'anchorCount':len(positions),
        'eventPrefixStatus':event_status,
        'rootContinuationStatus':root_status,
        'namedOuterFrameStatus':'named_exact_frame' if named_outer_frame else 'bounded_partial',
        'boundaryClass':boundary_class,
        'coverageStatus':'unsupported' if count==0 else 'ambiguous' if count>1 else 'unique'}


def join_and_frame(ledger, stream, *, stderr, adding_cooldown_native_validation=None,
                   dispel_config_native_validation=None,
                   stacking_compact_native_validation=None,
                   timeline_empty_native_validation=None,
                   root_no_positive_native_validation=None,
                   positive_damage_native_validation=None,
                   single_create_native_validation=None,
                   shared_event_native_validation=None,
                   datapair_native_validation=None,
                   global_modifier_native_validation=None,
                   selected_root_context=None):
    by_path={row['virtualPath']:row for row in ledger};seen=set();results=[]
    if len(by_path)!=len(ledger):vfs._fail('duplicate-buff-ledger',source='join')
    for index,row in enumerate(stream):
        path=row.get('fileName')
        if not isinstance(path,str) or path not in by_path:vfs._fail('unexpected-stream-identity',source=f'stream[{index}]',actual=path)
        if path in seen:vfs._fail('duplicate-stream-identity',source=path)
        seen.add(path);identity=by_path[path]
        if (row.get('blockType'),row.get('blockTypeValue'))!=('JsonData',19):vfs._fail('stream-block-mismatch',source=path)
        encoded=row.get('dataBase64')
        if not isinstance(encoded,str):vfs._fail('stream-base64-missing',source=path)
        try:data=base64.b64decode(encoded,validate=True)
        except ValueError as exc:vfs._fail('stream-base64-invalid',source=path,actual=str(exc))
        length=vfs._require_int(row.get('length'),source=path+'.length',minimum=1)
        if len(data)!=length or length!=identity['length']:vfs._fail('stream-length-mismatch',source=path,expected=identity['length'],actual=[length,len(data)])
        md5=hashlib.md5(data).hexdigest().upper()
        if md5!=identity['recomputedFileDataMd5']:vfs._fail('stream-ledger-md5-mismatch',source=path,expected=identity['recomputedFileDataMd5'],actual=md5)
        try:framed=frame_candidates(
            data, source=path,
            adding_cooldown_native_validation=adding_cooldown_native_validation,
            dispel_config_native_validation=dispel_config_native_validation,
            stacking_compact_native_validation=stacking_compact_native_validation,
            timeline_empty_native_validation=timeline_empty_native_validation,
            datapair_native_validation=datapair_native_validation,
            global_modifier_native_validation=global_modifier_native_validation,
        )
        except (ValueError,IndexError,KeyError,OverflowError,struct.error) as exc:
            framed={'coverageStatus':'failed','wholeSchemaExact':False,'candidateCount':0,
                'diagnostic':getattr(exc,'diagnostic',{'source':path,'offset':None,'expected':'bounded suffix-candidate reader','actual':f'{type(exc).__name__}: {exc}'})}
        logical_sha=hashlib.sha256(data).hexdigest().upper()
        no_positive_candidate = buff_root_no_positive.is_no_positive_candidate(
            framed, length=len(data),
        )
        framed['rootNoPositiveCandidate'] = no_positive_candidate
        if (no_positive_candidate
                and (root_no_positive_native_validation or {}).get('status') == 'validated'):
            try:
                root_receipt = buff_root_no_positive.decode_no_positive_buff(
                    data, source=path, expected_sha256=logical_sha,
                    native_validation=root_no_positive_native_validation,
                )
            except (ValueError, IndexError, KeyError, OverflowError, struct.error) as exc:
                vfs._fail('buff-root-no-positive-forward-reader', source=path,
                          expected='30 contiguous selected-native fields, id equality, physical EOF',
                          actual=f'{type(exc).__name__}: {exc}')
            framed['rootNoPositiveReceipt'] = root_receipt
            framed['wholeSchemaExact'] = True
            framed['boundaryClass'] = 'exact-closed'
            framed['namedOuterFrameStatus'] = 'named_exact_full'
        positive_damage_frame = buff_root_no_positive.is_positive_damage_candidate(
            framed, length=len(data),
        )
        framed['rootPositiveDamageFrameCandidate'] = positive_damage_frame
        framed['rootPositiveDamageCandidate'] = False
        if (positive_damage_frame
                and (positive_damage_native_validation or {}).get('status') == 'validated'):
            try:
                positive_receipt = buff_root_no_positive.decode_positive_damage_buff(
                    data, source=path, expected_sha256=logical_sha,
                    native_validation=root_no_positive_native_validation,
                    positive_damage_validation=positive_damage_native_validation,
                )
            except (ValueError, IndexError, KeyError, OverflowError, struct.error) as exc:
                # The frame admits condition/action variants that the selected
                # positive child has not proved. They stay partial, with the
                # exact first refusal visible in the generated corpus report.
                framed['rootPositiveDamageRefusal'] = f'{type(exc).__name__}: {exc}'
            else:
                framed['rootPositiveDamageCandidate'] = True
                framed['rootPositiveDamageReceipt'] = positive_receipt
                framed['wholeSchemaExact'] = True
                framed['boundaryClass'] = 'exact-closed'
                framed['namedOuterFrameStatus'] = 'named_exact_full'
        _sole_create, single_create_frame = buff_create_action_root_corpus._selected_create_candidate(
            framed, length=len(data),
        )
        framed['rootSingleCreateActionFrameCandidate'] = single_create_frame
        framed['rootSingleCreateActionCandidate'] = False
        if (single_create_frame
                and (single_create_native_validation or {}).get('status') == 'validated'):
            try:
                create_receipt = buff_create_action_root_receipt.decode_single_create_action_root(
                    data, source=path, expected_sha256=logical_sha,
                    native_validation=single_create_native_validation,
                )
            except (ValueError, IndexError, KeyError, OverflowError, struct.error) as exc:
                vfs._fail('buff-root-single-create-forward-reader', source=path,
                          expected='30 contiguous selected-native fields, id equality, physical EOF',
                          actual=f'{type(exc).__name__}: {exc}')
            framed['rootSingleCreateActionCandidate'] = True
            framed['rootSingleCreateActionReceipt'] = create_receipt
            framed['wholeSchemaExact'] = True
            framed['boundaryClass'] = 'exact-closed'
            framed['namedOuterFrameStatus'] = 'named_exact_full'
        if selected_root_context is not None:
            selected_root = buff_selected_roots.admit_current_source(
                data, source=path, logical_sha256=logical_sha,
                outer_row={'identity':identity,'logicalSha256':logical_sha,**framed},
                root_validation=root_no_positive_native_validation,
                context=selected_root_context,
            )
            if selected_root is not None:
                framed['rootSelectedSourceBranch'] = selected_root['branch']
                framed['rootSelectedSourceCandidate'] = 'receipt' in selected_root
                if 'receipt' in selected_root:
                    framed['rootSelectedSourceReceipt'] = selected_root['receipt']
                    framed['wholeSchemaExact'] = True
                    framed['boundaryClass'] = 'exact-closed'
                    framed['namedOuterFrameStatus'] = 'named_exact_full'
                else:
                    framed['rootSelectedSourceDiagnostic'] = selected_root['diagnostic']
        shared_event_frame = buff_root_no_positive.is_shared_event_candidate(framed, length=len(data))
        framed['rootSharedEventFrameCandidate'] = shared_event_frame
        framed['rootSharedEventCandidate'] = False
        if (shared_event_frame
                and (shared_event_native_validation or {}).get('status') == 'validated'):
            try:
                event_receipt = buff_root_no_positive.decode_shared_event_root(
                    data, source=path, expected_sha256=logical_sha,
                    native_validation=root_no_positive_native_validation,
                    event_maps_validation=shared_event_native_validation,
                )
            except (ValueError, IndexError, KeyError, OverflowError, struct.error) as exc:
                framed['rootSharedEventRefusal'] = getattr(exc, 'diagnostic', {
                    'source': path, 'check': 'shared-event-recursive-child',
                    'actual': f'{type(exc).__name__}: {exc}',
                })
            else:
                framed['rootSharedEventCandidate'] = True
                framed['rootSharedEventReceipt'] = event_receipt
                framed['wholeSchemaExact'] = True
                framed['boundaryClass'] = 'exact-closed'
                framed['namedOuterFrameStatus'] = 'named_exact_full'
        for candidate in framed.get('candidates',[]):
            context={'inputSetSha256':identity['inputSetSha256'],
                'logicalFileIdentity':identity['virtualPath'],'logicalSha256':logical_sha,
                'startOffset':candidate['startOffset'],'hardLimit':candidate['hardLimit']}
            candidate['boundaryContext']=context
            for profile in (candidate.get('currentEventPrefix'),candidate.get('currentRootContinuation')):
                if profile is not None:
                    profile['boundaryContext']=context
                    for record in profile.get('completedRecords',[]):
                        if record.get('boundaryClass')=='exact-closed':
                            record['boundaryContext']={**context,
                                'recordRange':[record['start'],record['end']]}
        results.append({'identity':identity,'logicalSha256':logical_sha,**framed})
    missing=sorted(set(by_path)-seen)
    if missing:vfs._fail('stream-missing-identities',source='BuffData stream',actual=missing[:10])
    matches=re.findall(r'(?m)^Streamed ([0-9]+) files\s*$',stderr)
    if len(matches)!=1 or int(matches[0])!=len(stream):vfs._fail('stream-terminal-count-mismatch',source='BuffData stream',expected=len(stream),actual=matches)
    return sorted(results,key=lambda row:row['identity']['virtualPath'])


def _stream_command(cli_path: Path, outer) -> list[str]:
    """Own the BuffData stream request instead of mutating another family's."""
    return [
        str(cli_path.resolve()), 'stream',
        '--streaming-assets', str(outer['primaryAssets']),
        '--fallback-assets', str(outer['fallbackAssets']),
        '--block-type', 'json-data',
        '--verify-md5',
        '--file-regex', PATTERN.pattern,
    ]


def boundary_evidence_summary(rows):
    candidates=[candidate for row in rows for candidate in row.get('candidates',[])]
    exact_closed=sum(candidate.get('exactClosedActionRecords',0) for candidate in candidates)
    structural_prefix=sum(candidate.get('boundaryClass')=='structural-prefix' for candidate in candidates)
    opaque_bytes=sum(span['end']-span['start'] for candidate in candidates
        for span in candidate.get('opaqueByteRanges',[]))
    return {'exactClosedActionRecords':exact_closed,
        'structuralPrefixCandidates':structural_prefix,
        'opaqueBytesByCandidate':opaque_bytes,
        'unsupportedCandidates':sum(candidate.get('boundaryClass')=='unsupported' for candidate in candidates),
        'failedCandidates':sum(candidate.get('boundaryClass')=='failed' for candidate in candidates),
        'rejectedAnchorCandidates':sum(candidate.get('boundaryClass')=='rejected-anchor' for candidate in candidates),
        'ambiguousFiles':sum(row.get('boundaryClass')=='ambiguous' for row in rows),
        'boundary':'Ranges are zero-based and half-open. Exact closures count completed anonymous union records only. Structural-prefix candidates '
        'do not establish whole-record or whole-file completion. Opaque bytes are composed unresolved ranges after '
        'downstream cursor coverage, retaining opaque nested bodies; stage-local remainders are not added again. '
        'Anonymous framed interiors remain separate naming obligations. Alternate ambiguous candidates are counted separately. Rejected filename anchors '
        'with no current parser run are reported separately from unsupported parser results.'}


def _read_stream_rows(command: list[str]) -> tuple[list[dict], str]:
    process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', check=False)
    rows = []
    for line_number, line in enumerate(process.stdout.splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            vfs._fail('stream-json-invalid', source='AnimeStudio stream stdout', offset=line_number, actual=str(exc))
        if not isinstance(row, dict):
            vfs._fail('stream-row-not-object', source='AnimeStudio stream stdout', offset=line_number, actual=type(row).__name__)
        rows.append(row)
    if process.returncode != 0:
        vfs._fail('stream-process-failed', source=command[0], expected=0,
                  actual={'returnCode': process.returncode, 'stderr': process.stderr[-4000:]})
    return rows, process.stderr


def _check_stream_cli_build(cli_path: Path, provenance: dict) -> None:
    cli_key = os.path.normcase(str(cli_path.resolve()))
    recorded = provenance['buildFingerprints']
    authenticated_paths = {
        os.path.normcase(str(Path(row['path']).resolve())) for row in recorded
    }
    if cli_key not in authenticated_paths:
        actual = (vfs._fingerprint(cli_path) if cli_path.is_file()
                  else {'path': cli_path.resolve().as_posix(), 'status': 'missing'})
        expected = {'recordedBuildInputs': [
            {key: row[key] for key in ('path', 'length', 'sha256')}
            for row in recorded[:16]], 'totalBuildInputs': len(recorded)}
        vfs._fail('stream-cli-not-in-outer-build-fingerprints',
                  source=str(cli_path.resolve()), expected=expected, actual=actual)


def build_current_census(*,outer_path,ledger_path,cli_path,expected_input_set_sha256,outputs=(),
                         selected_native_audit_path=buff_selected_roots.DEFAULT_NATIVE_AUDIT):
    expected=expected_input_set_sha256.upper()
    outer,_,files,provenance=vfs._read_outer_and_ledger(outer_path,ledger_path,expected_input_set_sha256=expected)
    _check_stream_cli_build(cli_path, provenance)
    selected=select_rows(files,expected_input=expected)
    native_validation=validate_current_native_contract()
    residual_validation=validate_residual_native_contract()
    adding_cooldown_validation=validate_adding_cooldown_native_contract()
    dispel_config_validation=validate_dispel_config_native_contract()
    stacking_compact_validation=validate_stacking_compact_native_contract()
    timeline_empty_validation=validate_timeline_empty_native_contract()
    root_no_positive_validation=buff_root_no_positive.validate_current_native_contract()
    positive_damage_validation=buff_root_no_positive.validate_positive_damage_native_contract(
        root_validation=root_no_positive_validation,
    )
    shared_event_validation=buff_event_maps.validate_current_native_contract()
    single_create_validation=buff_create_action_root_receipt.validate_current_native_contract(
        recursive_validation=shared_event_validation.get('recursiveActions', {}),
    )
    selected_root_context=buff_selected_roots.prepare_native_context(
        audit_path=selected_native_audit_path, root_validation=root_no_positive_validation,
    )

    datapair_validation=buff_datapair_native.validate_current_native_contract()
    global_modifier_validation=buff_global_modifier_receipt.validate_current_native_contract()
    if stacking_compact_validation.get('status') != 'validated':
        vfs._fail('buff-stacking-compact-native-validation', source=str(STACKING_COMPACT_CONTRACT_PATH),
                  expected='validated', actual=stacking_compact_validation)
    if datapair_validation.get('status') != 'validated':
        vfs._fail('buff-datapair-native-validation', source=str(buff_datapair_native.CONTRACT_PATH),
                  expected='validated', actual=datapair_validation)
    if global_modifier_validation.get('status') != 'validated':
        vfs._fail('buff-global-modifier-native-validation',
                  source=str(buff_global_modifier_receipt.CONTRACT_PATH),
                  expected='validated', actual=global_modifier_validation)
    expected_frontier_rows={
        'residual':[0x21,0x100,0x15F],
        'frontier6':[0x2A,0x9E,0xD7,0xE4,0x111,0x12F,0x18D],
        'frontier7':[0xFF,0x106,0x109,0x149,0x162,0x170,0x173,0x195],
        'frontier8':[0x09,0x14,0x1E,0x2D,0x4D,0x5F,0xAF,0xC2,0xD9,0x107,0x10D,0x114],
        'frontier9':[0x1D,0x82,0x97,0xB5,0xB8,0xBE,0xC8,0xD1,0xDD,
                     0xE5,0xE9,0x104,0x108,0x11B,0x141,0x143,0x17D,0x17E,0x191],
    }
    frontier_validations={}
    for name,expected_rows in expected_frontier_rows.items():
        source=str(buff_frontiers.contract_path(name))
        rows,validation=buff_frontiers.load_rows(name)
        frontier_validations[name]=validation
        if validation.get('status')!='validated':
            vfs._fail(f'buff-{name}-native-validation',source=source,expected='validated',actual=validation)
        if sorted(rows)!=expected_rows:
            vfs._fail(f'buff-{name}-row-set',source=source,expected=expected_rows,actual=sorted(rows))
    def snapshot():
        adding_cooldown_sources = (
            ADDING_COOLDOWN_CONTRACT_PATH,
            ADDING_COOLDOWN_ROOT_CONTRACT_PATH,
            ADDING_COOLDOWN_CHILD_CONTRACT_PATH,
            ADDING_COOLDOWN_DUMMYDLL_ROOT / 'generation.json',
            ADDING_COOLDOWN_DUMMYDLL_ROOT / 'MemoryPack.Beyond.dll',
        )
        dispel_config_sources = (
            DISPEL_CONFIG_CONTRACT_PATH,
            DISPEL_CONFIG_ROOT_CONTRACT_PATH,
            Path(decode_dispel_config.__code__.co_filename),
        )
        stacking_compact_sources = (
            STACKING_COMPACT_CONTRACT_PATH,
            STACKING_COMPACT_ROOT_CONTRACT_PATH,
            Path(decode_stacking_settings_compact.__code__.co_filename),
        )
        timeline_empty_sources = (
            TIMELINE_EMPTY_CONTRACT_PATH,
            TIMELINE_EMPTY_ROOT_CONTRACT_PATH,
            Path(decode_empty_timeline_suffix.__code__.co_filename),
        )
        root_no_positive_sources = (
            Path(buff_root_no_positive.__file__),
            Path(buff_root_no_positive_native.__file__),
            buff_root_no_positive_native.CONTRACT_PATH,
            buff_root_no_positive_native.ROOT_CONTRACT_PATH,
            buff_root_no_positive_native.INT_CONTRACT_PATH,
            buff_root_no_positive_native.PROVIDER_CONTRACT_PATH,
            buff_datapair_native.CONTRACT_PATH,
            buff_datapair_native.ROOT_CONTRACT_PATH,
            buff_global_modifier_receipt.CONTRACT_PATH,
            Path(buff_attribute_modifier.__file__),
            buff_attribute_modifier.CONTRACT_PATH,
            buff_attribute_modifier.PREFIX_PATH,
            buff_attribute_modifier.ATTRIBUTE_PATH,
        )
        positive_damage_sources = (
            Path(buff_damage_modifier_receipt.__file__),
            buff_damage_modifier_receipt.CONTRACT_PATH,
            Path(buff_damage_scale_processor_child_receipt.__file__),
            buff_damage_scale_processor_child_receipt.CONTRACT_PATH,
            Path(buff_damage_modify_calc_result_processor_child_receipt.__file__),
            buff_damage_modify_calc_result_processor_child_receipt.CONTRACT_PATH,
            Path(buff_damage_instant_modify_attribute_processor_receipt.__file__),
            buff_damage_instant_modify_attribute_processor_receipt.CONTRACT_PATH,
            buff_damage_instant_modify_attribute_processor_receipt.CONTRACT_PATH.parent / 'buff_root_prefix_native.json',
            Path(buff_damage_scalar_processor_child_receipt.__file__),
            buff_damage_scalar_processor_child_receipt.CONTRACT_PATH,
            Path(buff_damage_text_processor_child_receipt.__file__),
            buff_damage_text_processor_child_receipt.CONTRACT_PATH,
            Path(buff_damage_two_action_condition_receipt.__file__),
            buff_damage_two_action_condition_receipt.CONTRACT_PATH,
            buff_damage_scale_processor_child_receipt.CONTRACT_PATH.parent / 'buff_damage_lists_native.json',
            Path(buff_damage_sequence_action_condition_receipt.__file__),
            buff_damage_sequence_action_condition_receipt.CONTRACT_PATH,
            Path(buff_damage_check_decorate_mask_condition_receipt.__file__),
            buff_damage_check_decorate_mask_condition_receipt.CONTRACT_PATH,
            buff_damage_check_decorate_mask_condition_receipt.CONTRACT_PATH.parent / 'buff_5b_native.json',
            buff_damage_check_decorate_mask_condition_receipt.CONTRACT_PATH.parent / 'levelscript_union_tags.json',
            Path(buff_damage_check_type_condition_receipt.__file__),
            buff_damage_check_type_condition_receipt.CONTRACT_PATH,
            buff_damage_check_type_condition_receipt.CONTRACT_PATH.parent / 'buff_5d_native.json',
            Path(buff_damage_check_type_mask_condition_receipt.__file__),
            buff_damage_check_type_mask_condition_receipt.CONTRACT_PATH,
            buff_damage_check_type_mask_condition_receipt.CONTRACT_PATH.parent / 'buff_5e_native.json',
            Path(buff_damage_check_tag_match_condition_receipt.__file__),
            buff_damage_check_tag_match_condition_receipt.CONTRACT_PATH,
            buff_damage_check_tag_match_condition_receipt.CONTRACT_PATH.parent / 'buff_7c_native.json',
            Path(buff_damage_check_main_character_condition_receipt.__file__),
            buff_damage_check_main_character_condition_receipt.CONTRACT_PATH,
            buff_damage_check_main_character_condition_receipt.CONTRACT_PATH.parent / 'buff_68_native.json',
            Path(buff_damage_check_buff_stack_condition_receipt.__file__),
            buff_damage_check_buff_stack_condition_receipt.CONTRACT_PATH,
            buff_damage_check_buff_stack_condition_receipt.CONTRACT_PATH.parent / 'buff_3c_native.json',
            Path(buff_damage_check_vitals_condition_receipt.__file__),
            buff_damage_check_vitals_condition_receipt.CONTRACT_PATH,
            buff_damage_check_vitals_condition_receipt.CONTRACT_PATH.parent / 'buff_65_native.json',
            buff_damage_check_vitals_condition_receipt.CONTRACT_PATH.parent / 'buff_6e_native.json',
            Path(buff_damage_origin_or_condition_receipt.__file__),
            buff_damage_origin_or_condition_receipt.CONTRACT_PATH,
            Path(buff_damage_known_compound_condition_receipt.__file__),
            buff_damage_known_compound_condition_receipt.CONTRACT_PATH,
            Path(buff_damage_if_else_condition_receipt.__file__),
            buff_damage_if_else_condition_receipt.CONTRACT_PATH,
            Path(buff_damage_not_next_main_condition_receipt.__file__),
            buff_damage_not_next_main_condition_receipt.CONTRACT_PATH,
            Path(buff_damage_two_direction_angle_condition_receipt.__file__),
            buff_damage_two_direction_angle_condition_receipt.CONTRACT_PATH,
            buff_damage_two_direction_angle_condition_receipt.CONTRACT_PATH.parent / 'buff_frontier9.json',
            Path(buff_if_else_action_receipt.__file__),
            buff_if_else_action_receipt.CONTRACT_PATH,
            buff_damage_if_else_condition_receipt.CONTRACT_PATH.parent / 'buff_residual_actions_native.json',
            buff_damage_not_next_main_condition_receipt.CONTRACT_PATH.parent / 'buff_fd_native.json',
            buff_damage_check_tag_match_condition_receipt.CONTRACT_PATH.parent / 'buff_find_settings_child_native.json',
            buff_damage_check_tag_match_condition_receipt.CONTRACT_PATH.parent / 'buff_b4_native.json',
            buff_damage_check_tag_match_condition_receipt.CONTRACT_PATH.parent / 'buff_ec_native.json',
            buff_damage_check_tag_match_condition_receipt.CONTRACT_PATH.parent / 'buff_b2_native.json',
            Path(buff_target_settings_child_receipt.__file__),
            Path(buff_direction_settings_child_receipt.__file__),
            Path(buff_selector_data_child_receipt.__file__),
            Path(buff_find_settings_child_receipt.__file__),
        )
        single_create_sources = (
            Path(buff_create_action_root_corpus.__file__),
            Path(buff_create_action_root_receipt.__file__),
            Path(buff_create_icon_duration_child_receipt.__file__),
            buff_create_icon_duration_child_receipt.CONTRACT_PATH,
            Path(buff_create_input_child_receipt.__file__),
            buff_create_input_child_receipt.CONTRACT_PATH,
        )
        datapair_sources = (
            Path(buff_datapair_native.__file__),
            buff_datapair_native.CONTRACT_PATH,
            buff_datapair_native.ROOT_CONTRACT_PATH,
        )
        global_modifier_sources = (
            Path(buff_global_modifier_receipt.__file__),
            buff_global_modifier_receipt.CONTRACT_PATH,
        )
        return {'selectedChunkFingerprints':vfs._chunk_fingerprints(selected),
            'selectedChunkResolution':vfs._chunk_selection_snapshot(selected,outer),
            'streamToolFingerprints':vfs._stream_tool_snapshot(cli_path),
            'parser':vfs._parser_source_snapshots(Path(__file__)),
            'buffFrontiersNative':[vfs._fingerprint(Path(buff_frontiers.__file__))]+[
                vfs._fingerprint(spec.path) for spec in buff_frontiers.FRONTIERS.values()],
            'buffAddingCooldownSources':[
                vfs._fingerprint(path) if path.is_file() else {'path':str(path),'status':'missing'}
                for path in adding_cooldown_sources],
            'buffDispelConfigSources':[vfs._fingerprint(path) for path in dispel_config_sources],
            'buffStackingCompactSources':[vfs._fingerprint(path) for path in stacking_compact_sources],
            'buffTimelineEmptySources':[vfs._fingerprint(path) for path in timeline_empty_sources],
            'buffRootNoPositiveSources':[vfs._fingerprint(path) for path in root_no_positive_sources],
            'buffSharedEventSources':[vfs._fingerprint(path) for path in buff_event_maps.contract_source_paths()],
            'buffPositiveDamageSources':[vfs._fingerprint(path) for path in positive_damage_sources],
            'buffSingleCreateSources':[vfs._fingerprint(path) for path in single_create_sources],
            'buffSelectedRootSources':buff_selected_roots.recheck_sources(selected_root_context),
            'buffDataPairSources':[vfs._fingerprint(path) for path in datapair_sources],
            'buffGlobalModifierSources':[vfs._fingerprint(path) for path in global_modifier_sources],
            'buffNamedSchema':vfs._fingerprint(Path(buff_named_schema.__file__)),
            'corpusGate':vfs._fingerprint(Path(__file__))}
    before=snapshot()
    protected=[outer_path,ledger_path,Path(outer['primaryAssets']),Path(outer['fallbackAssets'])]
    protected.append(Path(buff_named_schema.__file__))
    protected.extend(Path(row['path']) for row in before['buffAddingCooldownSources']
                     if row.get('status') != 'missing')
    protected.extend(Path(row['path']) for row in before['buffDispelConfigSources'])
    protected.extend(Path(row['path']) for row in before['buffStackingCompactSources'])
    protected.extend(Path(row['path']) for row in before['buffTimelineEmptySources'])
    protected.extend(Path(row['path']) for row in before['buffRootNoPositiveSources'])
    protected.extend(Path(row['path']) for row in before['buffPositiveDamageSources'])
    protected.extend(Path(row['path']) for row in before['buffSingleCreateSources'])
    protected.extend(Path(row['path']) for row in before['buffSharedEventSources'])
    protected.extend(Path(row['path']) for row in before['buffSelectedRootSources'])
    protected.extend(Path(row['path']) for row in before['buffDataPairSources'])
    protected.extend(Path(row['path']) for row in before['buffGlobalModifierSources'])
    # Many logical files share a chunk; protect every distinct physical input once.
    protected += [Path(path) for path in sorted({r['physicalChunkPath'] for r in files if r.get('physicalChunkPath')})]
    for group in (provenance['sourceFingerprints'],provenance['buildFingerprints'],before['streamToolFingerprints'],before['parser']):
        protected += [Path(r['path']) for r in group]
    def guard():
        for output in outputs:vfs._guard_output_path(output,protected+[p for p in outputs if p!=output])
        if len({str(p.resolve()) for p in outputs})!=len(outputs):vfs._fail('duplicate-output',source='BuffData outputs')
    guard()
    stream,stderr=_read_stream_rows(_stream_command(cli_path,outer))
    rows=join_and_frame(
        selected,stream,stderr=stderr,
        adding_cooldown_native_validation=adding_cooldown_validation,
        dispel_config_native_validation=dispel_config_validation,
        stacking_compact_native_validation=stacking_compact_validation,
        timeline_empty_native_validation=timeline_empty_validation,
        root_no_positive_native_validation=root_no_positive_validation,
        positive_damage_native_validation=positive_damage_validation,
        single_create_native_validation=single_create_validation,
        shared_event_native_validation=shared_event_validation,
        datapair_native_validation=datapair_validation,
        global_modifier_native_validation=global_modifier_validation,
        selected_root_context=selected_root_context,
    )
    _,_,end_files,end_provenance=vfs._read_outer_and_ledger(outer_path,ledger_path,expected_input_set_sha256=expected)
    after=snapshot()
    comparisons={'outer':(provenance,end_provenance),'selectedLedger':(selected,select_rows(end_files,expected_input=expected))}
    comparisons.update({key:(value,after[key]) for key,value in before.items()})
    for role,(old,new) in comparisons.items():
        if old!=new:
            vfs._fail('buff-corpus-input-drift',source='BuffData census.'+role,
                expected=canonical_json_sha256(old),actual=canonical_json_sha256(new))
    guard();counts=Counter(row['coverageStatus'] for row in rows)
    prefix_counts=Counter(c['prefixProbe']['readerStatus'] for row in rows for c in row.get('candidates',[])
        if c.get('prefixProbe') is not None)
    event_counts=Counter(row.get('eventPrefixStatus','failed') for row in rows)
    categories={status:Counter(c['currentEventPrefix']['diagnostic']['category']
        for row in rows for c in row.get('candidates',[])
        if c.get('currentEventPrefix') and c['currentEventPrefix']['status']==status)
        for status in ('failed','unsupported')}
    event_summary={'total':len(rows),**{s:event_counts[s] for s in ('success','failed','unsupported','ambiguous')},
        'failureCategories':{s:dict(sorted(v.items())) for s,v in categories.items()},
        'boundary':'Success means the supported anonymous first collection ended before its candidate anchor. Scalar spans plus an explicit physical-file remainder tile EOF; the remainder is opaque, not decoded. Unknown unions stop at their first byte. No legacy names or whole-schema success.'}
    root_counts=Counter(row.get('rootContinuationStatus','failed') for row in rows)
    root_categories={status:Counter((c.get('currentRootContinuation') or c.get('currentEventPrefix'))['diagnostic']['category']
        for row in rows for c in row.get('candidates',[])
        if (c.get('currentRootContinuation') or c.get('currentEventPrefix'))
        and (c.get('currentRootContinuation') or c.get('currentEventPrefix'))['status']==status)
        for status in ('failed','unsupported')}
    root_summary={'total':len(rows),**{s:root_counts[s] for s in ('success','failed','unsupported','ambiguous')},
        'failureCategories':{s:dict(sorted(v.items())) for s,v in root_categories.items()},
        'boundary':'Success means only a structural prefix: a supported first collection followed by selected root members 2-6. '
        'Continuation ranges begin at currentEventPrefix.consumedEnd. The remaining physical-file bytes '
        'stay opaque; neither suffix-anchor ownership nor whole-schema EOF is established.'}
    named_middle_counts=Counter(
        (candidate.get('currentNamedMiddle') or {}).get('status','not-reached')
        for row in rows for candidate in row.get('candidates',[])
        if candidate.get('readerAcceptedThroughEof')
    )
    named_middle_stops=Counter(
        (candidate.get('currentNamedMiddle') or {}).get('diagnostic','unknown').split('=')[0]
        for row in rows for candidate in row.get('candidates',[])
        if candidate.get('readerAcceptedThroughEof')
        and (candidate.get('currentNamedMiddle') or {}).get('status')=='unsupported'
    )
    named_middle_summary={
        'total':len(rows),
        'namedThroughIconConfig':named_middle_counts['named-through-iconConfig'],
        'exactIconConfig':sum(
            (candidate.get('currentNamedMiddle') or {}).get('iconConfigStatus')=='exact'
            for row in rows for candidate in row.get('candidates',[])
            if candidate.get('readerAcceptedThroughEof')
        ),
        'unsupported':named_middle_counts['unsupported'],
        'notReached':named_middle_counts['not-reached'],
        'stopCategories':dict(sorted(named_middle_stops.items())),
        'boundary':(
            'Supported rows name fields 6-14. Every reached field advances an exact cursor; iconConfig '
            'uses its authenticated current-build 19-member reader and ends at the independently accepted id marker.'
        ),
    }
    failed=bool(counts['failed'] or event_counts['failed'] or root_counts['failed'])
    root_no_positive_rows=[row for row in rows if row.get('rootNoPositiveCandidate')]
    root_no_positive_exact=[row for row in rows if row.get('rootNoPositiveReceipt')]
    positive_damage_frames=[row for row in rows if row.get('rootPositiveDamageFrameCandidate')]
    positive_damage_exact=[row for row in rows if row.get('rootPositiveDamageReceipt')]
    single_create_frames=[row for row in rows if row.get('rootSingleCreateActionFrameCandidate')]
    single_create_exact=[row for row in rows if row.get('rootSingleCreateActionReceipt')]
    return {'format':'animestudio-buffdata-current-vfs-corpus','schemaVersion':1,
        'inputSetSha256':expected,'status':'failed' if failed else 'complete',
        'publicationEligible':not failed,'wholeSchemaExact':False,
        'provenance':{**provenance,**before,
            'buffIconConfigNativeValidation':native_validation,
            'buffResidualActionsNativeValidation':residual_validation,
            'buffAddingCooldownNativeValidation':adding_cooldown_validation,
            'buffDispelConfigNativeValidation':dispel_config_validation,
            'buffStackingCompactNativeValidation':stacking_compact_validation,
            'buffTimelineEmptyNativeValidation':timeline_empty_validation,
            'buffRootNoPositiveNativeValidation':root_no_positive_validation,
            'buffSelectedRootNativeAudit':selected_root_context['audit'],
            'buffSelectedRootNativeValidation':selected_root_context['validations'],
            'buffPositiveDamageNativeValidation':positive_damage_validation,
            'buffSingleCreateActionNativeValidation':{
                'status':single_create_validation['status'],
                'nativeInputs':single_create_validation['nativeInputs'],
            },
            'buffSharedEventNativeValidation':buff_event_maps.recorded_native_validation(shared_event_validation),
            'buffDataPairNativeValidation':datapair_validation,
            'buffGlobalModifierNativeValidation':global_modifier_validation,
            'buffFrontiersNativeValidation':frontier_validations},'evidenceBoundary':BOUNDARY,
        'summary':{'filesSelected':len(selected),'filesSucceeded':counts['unique']+counts['ambiguous'],
            'filesFailed':counts['failed'],'filesUnsupported':counts['unsupported'],
            'filesUnique':counts['unique'],'filesAmbiguous':counts['ambiguous'],
            'filesWithMultipleAnchors':sum(row.get('anchorCount',0)>1 for row in rows),
             'filesWithNamedOuterFrame':sum(
                 row.get('namedOuterFrameStatus') in ('named_exact_frame','named_exact_full')
                 for row in rows
             ),
             'acceptedSuffixPrefixStatusCounts':dict(sorted(prefix_counts.items())),
             'currentEventPrefix':event_summary,
             'currentRootContinuation':root_summary,
             'currentNamedMiddle':named_middle_summary,
             'byteBoundaryEvidence':boundary_evidence_summary(rows),
             'namedSchemaReceipts':buff_named_schema.summarize_receipts(rows),
             'filesWholeSchemaExact':sum(row.get('wholeSchemaExact') is True for row in rows),
             'selectedSourceRoots':buff_selected_roots.summarize(rows),
             'rootNoPositive':{
                 'candidates':len(root_no_positive_rows),
                 'wholeSchemaExact':len(root_no_positive_exact),
                 'logicalBytes':sum(row['identity']['length'] for row in root_no_positive_exact),
             'boundary':'Only singleton rows with selected-native 30-member forward receipts are promoted: null/empty recursive lists plus authenticated DataPair lists, AttributeModifierData arrays and the reviewed GlobalModifier positive branch; other recursive lists remain partial.',
             },
             'rootPositiveDamage':{
                 'frameCandidates':len(positive_damage_frames),
                 'wholeSchemaExact':len(positive_damage_exact),
                 'logicalBytes':sum(row['identity']['length'] for row in positive_damage_exact),
                 'boundary':'Only one positive DamageModifier child with an empty condition and tag five or ordered [5,6] processors, one selected CheckDamageDecorateMask or CheckDamageType action with tag five or ten, one CheckDamageTypeMask, simple CheckTagMatch, simple CheckMainCharacterCondition, selected CheckBuffStackNumAdvanced, simple CheckHp or simple CheckPoiseValue action with tag five, one CheckBuffStackNumAdvanced action with tag nine, one CheckDamageDecorateMask action with scalar tag zero, two or three, one simple CheckTagMatch action with scalar tag zero or three, selected OriginSkillType, OrConditionAction, known-action compound or nested IfElseAction condition routes with tag five, the selected NotNextCheckAction/main-character pair with scalar tag four, or two selected CheckTwoDirectionAngle actions with ordered [5,6] processors can rejoin the 30-member root reader through physical EOF. Unsupported variants remain partial.',
             },
             'rootSharedEvent':{
                 'frameCandidates':sum(row.get('rootSharedEventFrameCandidate') is True for row in rows),
                 'wholeSchemaExact':sum(row.get('rootSharedEventReceipt') is not None for row in rows),
                 'logicalBytes':sum(row['identity']['length'] for row in rows if row.get('rootSharedEventReceipt')),
                 'boundary':'Distinct native-typed AbilityActionMap and BuffActionMap lists compose named SequenceActionData, bounded CreateBuff input lists and EffectAction child receipts. Every accepted source replays all thirty original root fields through source-ID equality and physical EOF; unproved child variants remain partial.',
             },
             'rootSingleCreateAction':{
                 'frameCandidates':len(single_create_frames),
                 'wholeSchemaExact':len(single_create_exact),
                 'logicalBytes':sum(row['identity']['length'] for row in single_create_exact),
                 'boundary':'A sole selected CreateBuff ability action with named direct nested children rejoins the thirty-member root through source ID equality and physical EOF. Other action lists remain partial.',
             },
             'blackboardDataPairs':{
                 'listsReached':sum(
                     any(field.get('name') == 'blackboard' and field.get('nestedProfile') is not None
                         for field in (candidate.get('currentRootContinuation') or {}).get('namedFields', []))
                     for row in rows for candidate in row.get('candidates', [])
                 ),
                 'positiveLists':sum(
                     (field.get('nestedProfile') or {}).get('count', 0) > 0
                     for row in rows for candidate in row.get('candidates', [])
                     for field in (candidate.get('currentRootContinuation') or {}).get('namedFields', [])
                     if field.get('name') == 'blackboard'
                 ),
                 'zeroLists':sum(
                     (field.get('nestedProfile') or {}).get('count') == 0
                     for row in rows for candidate in row.get('candidates', [])
                     for field in (candidate.get('currentRootContinuation') or {}).get('namedFields', [])
                     if field.get('name') == 'blackboard'
                 ),
                 'nullLists':sum(
                     (field.get('nestedProfile') or {}).get('count') == -1
                     for row in rows for candidate in row.get('candidates', [])
                     for field in (candidate.get('currentRootContinuation') or {}).get('namedFields', [])
                     if field.get('name') == 'blackboard'
                 ),
                 'childCount':sum(
                     len((field.get('nestedProfile') or {}).get('children', []))
                     for row in rows for candidate in row.get('candidates', [])
                     for field in (candidate.get('currentRootContinuation') or {}).get('namedFields', [])
                     if field.get('name') == 'blackboard'
                 ),
                 'boundary':'Native-gated root field-4 DataPair lists cover null, empty, and positive lists; whole BuffData remains partial.',
             },
             'globalModifiers':{
                 'listsReached':sum(
                     any(field.get('name') == 'globalModifier' and field.get('nestedProfile') is not None
                         for field in (candidate.get('currentNamedMiddle') or {}).get('namedFields', []))
                     for row in rows for candidate in row.get('candidates', [])
                 ),
                 'positiveLists':sum(
                     (field.get('nestedProfile') or {}).get('count', 0) > 0
                     for row in rows for candidate in row.get('candidates', [])
                     for field in (candidate.get('currentNamedMiddle') or {}).get('namedFields', [])
                     if field.get('name') == 'globalModifier'
                 ),
                 'childCount':sum(
                     len((field.get('nestedProfile') or {}).get('elements', []))
                     for row in rows for candidate in row.get('candidates', [])
                     for field in (candidate.get('currentNamedMiddle') or {}).get('namedFields', [])
                     if field.get('name') == 'globalModifier'
                 ),
                 'boundary':'Native-gated positive field-10 GlobalModifier.Data children only; whole BuffData remains partial.',
             },
             'logicalBytes':sum(row['length'] for row in selected)},
        'identitySetSha256':canonical_json_sha256([{'identity':r['identity'],'logicalSha256':r['logicalSha256']} for r in rows]),'files':rows}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outer-summary',type=Path,default=vfs.DEFAULT_OUTER)
    parser.add_argument('--outer-ledger',type=Path,default=vfs.DEFAULT_LEDGER)
    parser.add_argument('--cli',type=Path,default=vfs.DEFAULT_CLI)
    parser.add_argument('--expected-input-set-sha256',required=True)
    parser.add_argument('--selected-native-audit',type=Path,default=buff_selected_roots.DEFAULT_NATIVE_AUDIT,
                        help='current IL2CPP context audit for selected root routes; rechecked without rerunning it')
    parser.add_argument('--output-json',type=Path,required=True)
    parser.add_argument('--output-md',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        report=build_current_census(outer_path=args.outer_summary,ledger_path=args.outer_ledger,
            cli_path=args.cli,expected_input_set_sha256=args.expected_input_set_sha256,
            outputs=(args.output_json,args.output_md),selected_native_audit_path=args.selected_native_audit)
    except vfs.CensusGateError as exc:
        print(json.dumps({'status':'failed','diagnostic':exc.diagnostic}));return 1
    vfs._atomic_write_json(args.output_json,report)
    args.output_md.parent.mkdir(parents=True,exist_ok=True)
    args.output_md.write_text('# BuffData current VFS corpus\n\n'+report['inputSetSha256']+'\n\n'+
        json.dumps(report['summary'],ensure_ascii=False)+'\n\n'+BOUNDARY+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'summary':report['summary']}))
    return int(report['status']=='failed')


if __name__=='__main__':raise SystemExit(main())
