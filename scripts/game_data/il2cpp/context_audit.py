"""Exact-build, read-only generic-instantiation audit; JSON is emitted to stdout.

No runtime MethodInfo or serialized source cursor is inferred. Native tables
are referenced PE extents, not a claim to consume the entire PE to EOF.

Run as ``python -m scripts.game_data.il2cpp.context_audit``; the generated
inventory belongs under ``reports/animestudio/``. The audit validates the
current native inputs, every registered generic instance, and reciprocal
open-parameter ownership, then joins the MemoryPack formatter identity chain
one static link at a time. Each report key carries its own ``boundary``
string, which is the maintained statement of what that link proves:

1. registration -- a pointer array of 16-byte records (``context``); the
   selected ``GetFormatter<T>`` parameter belongs to ``ReadValue<T>``. An
   earlier concrete-type probe that seemed to contradict this was an
   indirection bug, not a runtime counterexample;
2. MVAR leaf, modules and usage cells (``selectedRawArgument``,
   ``staticImageOwnership``, ``selectedUsageCell``) -- the leaf's ordinal is
   checked against the call's registered argument; method records reach
   their class, the image-range directory and a module picked by bytewise
   name comparison; the on-disk usage cell joins through the guarded lazy
   initializer and the tag-specific MethodSpec/triple resolver. The open
   formatter-check carrier joins the same MVAR through its class-inst pointer
   (``selectedFormatterTypeCarrier``); its 32-byte window's last 16 bytes stay
   opaque and certify no allocation extent or returned formatter;
3. instantiation cache, MethodSpecs and RGCTX (``selectedInstantiationCacheSeed``,
   ``selectedObjectComparison``, ``selectedSharedMethodCandidates``,
   ``selectedAdapterClassSlot``, ``selectedNestedAdapterSlots``) -- a gated
   initializer seeds the cache from the registration's pointer table and
   insertion and lookup share one storage global; the adapter's class-token
   range links its slot to a reciprocal second type parameter (VAR), and
   nested slots link DeserializeNotNull, GetFormatter and CreateInstance to
   parameters of that same adapter;
4. shared-code normalization (``selectedSharingBranch``,
   ``selectedObjectIdentity``, ``selectedMethodCompanionConstruction``) -- a
   missed original-context lookup retries with class-tag arguments replaced
   by one global ``System.Object`` carrier, whose bytes match both arguments
   of the static object/object candidate. MethodInfo construction stores the
   original instantiated class separately from the shared code pointers, so
   never substitute the shared body's object/object arguments for the
   companion's class context.

Every link is ``direct`` static evidence of a mechanism. None observes
initialization, cache contents, interned pointer identity, generic
substitution, the active formatter, a source cursor or EOF, and none
promotes the unresolved registration history or earlier nested SkillData
fields. The accepted direct-reader cursor resolves the current terminal
candidate independently of this audit.

Redirect stdout to ``reports/animestudio/il2cpp_context_current_latest.json``;
that is the default native-context input of ``memorypack.buff_1b_corpus``,
``memorypack.skill_timeline_cursor`` and ``memorypack.skill_cursor_receipt``.

Pinned values.  The selected build and every build-locked value this module
checks or reports -- registration VAs, RIP-relative reference RVAs, MethodSpec,
generic-instantiation, type and method indices, RGCTX ranges, reviewed
instruction bytes, and the list-formatter and UnityPlayer code windows -- live
in ``contracts/il2cpp_context_audit_native.json`` (``nativeInputs``,
``consumerWindows`` and ``pins``), loaded through ``context_audit_common``.
Type and method names, IL2CPP structure offsets and element-type tags stay in
code because a client update does not change them.  The audit starts with
``native_gate``, which fails closed unless the installed client is the pinned
build.  The ``context_audit_memorypack``/``_skilldata``/``_vfs`` stage modules
read their pins the same way, one ``pins`` section per report key; the
SkillData reader methods, body windows, observer callsites and source lengths
come from ``contracts/skill_cursor_observer_native.json``, which this audit
requires to pin the same build.
"""
from __future__ import annotations

from scripts.common import EXPORT_LAYOUT
import hashlib
import json
import struct
import sys
from pathlib import Path
from scripts.game_data.il2cpp.context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.memorypack.skill_corpus import verify_current_report_inputs
from scripts.game_data.memorypack.corpus_gate import verify_current_report_inputs as verify_family_report_inputs
from scripts.game_data.il2cpp.context import class_sharing_branch
from scripts.game_data.il2cpp.context import named_top_level_type
from scripts.game_data.il2cpp.context import object_type_comparison_key
from scripts.game_data.il2cpp.context import method_pointer_indices, generic_method_candidates
from scripts.game_data.il2cpp.context import type_parameter_owner, rgctx_range_entries
from scripts.game_data.il2cpp.context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.protocol import load_metadata_helper, load_native_mapper
from scripts.game_data.il2cpp.context_audit_common import AUDIT_PINS, CONSUMER_WINDOWS, CORPUS_REPORT_RELATIVE, GA_SHA, MD_SHA, NATIVE_CONTRACT_PATH, ROOT, UNITY_SHA, native_gate, require, sha, sweep, validate_selected_method_spec
from scripts.game_data.il2cpp.context_audit_memorypack import adapter_conversion_context, buff_action_read_order, buff_ifelse_forwarding, buff_ifelse_read_order, buff_sequence_read_order, buff_tag76_read_order, buff_union_routes, element_provider_state_flow, list_element_dispatch, list_element_null_probe, list_element_shared_context, list_element_value_flow, list_formatter_candidate, module_methods, nested_reader_context, reader_construction, reader_cursor_consumers, resource_carrier_consumers, serializer_return_consumers, skill_resource_context, wrapper_consumer
from scripts.game_data.il2cpp.context_audit_skilldata import IF_ELSE_TAG, OBSERVER_CONTRACT_PATH, select_skilldata_terminal_branch_samples, skilldata_action_readers_from_locals, skilldata_action_union_c9_prefix_reader_evidence, skilldata_actiongroup_branch_sample_witness, skilldata_actiongroup_branch_static_alignment, skilldata_actiongroup_c9_nested_sequence_candidate_replay, skilldata_nested_branch_static_alignment, skilldata_positive_branch_reader_replay, skilldata_static_reader_order, skilldata_terminal_branch_sample_witness
from scripts.game_data.il2cpp.context_audit_vfs import file_stream_open, native_file_read, resolver_key_comparison, resolver_prefix_query, stream_carrier_consumer, stream_source_identity, unity_conversion_exports, unity_loader_conversion, unity_loader_input, unity_module_lookup, unity_path_return, unity_registration_forwarder, unity_registration_pair, vfs_block_cursor, vfs_block_file_source, vfs_block_transform, vfs_bytebuf_consumer, vfs_descriptor_path, vfs_descriptor_producer, vfs_format_item, vfs_path_carrier, vfs_path_format_context, vfs_path_literals, vfs_root_resolver, vfs_stream_consumer, vfs_stream_identity, vfs_string_carrier
# Re-exported for scripts.game_data.memorypack.skill_timeline_cursor.
from scripts.game_data.il2cpp.context_audit_skilldata import (
    _skilldata_continue_following_play_animation_candidate,
    _skilldata_continue_timeline_parent_candidate,
    _skilldata_read_following_timeline_action_data_prefix_candidate,
    _skilldata_sequence_tail_windows,
    _skilldata_verified_byte_payload_reader,
    skilldata_action_union_static_reader_evidence,
    skilldata_timeline_branch_sample_witness,
    skilldata_timeline_branch_static_alignment,
)


def require_code_bytes(pe, rva, hex_bytes, source):
    """Require the reviewed instruction bytes recorded for ``rva``."""
    expected = bytes.fromhex(hex_bytes)
    require(pe.bytes_at_va(pe.image_base+rva, len(expected)), expected, source, rva)


def audit():
    gate = native_gate()
    corpus_path = ROOT / CORPUS_REPORT_RELATIVE
    # The basis is a regenerated local report, so it is authenticated by its
    # live provenance (status, input set, tool/parser/chunk fingerprints), not
    # by a digest pinned in code. The digest taken here only proves the file
    # did not change while the audit ran, as for the BuffData input below.
    corpus_sha = sha(corpus_path)
    corpus = json.loads(corpus_path.read_text(encoding='utf-8'))
    verify_current_report_inputs(corpus)
    terminal_branch_selections = select_skilldata_terminal_branch_samples(
        corpus, source=str(corpus_path))
    skill_sample_path = EXPORT_LAYOUT.game_file('Data/Json/SkillData/Potential_test.json')
    skill_sample_raw = skill_sample_path.read_bytes()
    terminal_branch_sample_paths = [
        EXPORT_LAYOUT.game_file(selection['row']['virtualPath'])
        for selection in terminal_branch_selections
    ]
    actiongroup_branch_census_rows = []
    for row in corpus.get('files', []):
        record_lists = row.get('commonPrefixFraming', {}).get('recordLists', [])
        if (record_lists and type(record_lists[0].get('count')) is int and
                record_lists[0]['count'] > 0):
            actiongroup_branch_census_rows.append(row)
    actiongroup_branch_census_sample_paths = [
        EXPORT_LAYOUT.game_file(row['virtualPath'])
        for row in actiongroup_branch_census_rows
    ]
    actiongroup_branch_sample_identities = [
        'Data/Json/SkillData/eny_0045_agtrinit_state0_passive.json',
        'Data/Json/SkillData/abilityentity_int_doodad_passive.json',
        'Data/Json/SkillData/chr_0030_zhuangfy_talent1.json',
        'Data/Json/SkillData/sk_wpn_funnel_0006.json',
        'Data/Json/SkillData/sk_wpn_claym_0003.json',
        'Data/Json/SkillData/abilityentity_interact_mud_carpet_passive.json',
    ]
    actiongroup_branch_sample_paths = [
        EXPORT_LAYOUT.game_file(logical_path)
        for logical_path in actiongroup_branch_sample_identities
    ]
    skill_terminal_path = ROOT / 'scripts/game_data/memorypack' / 'skill_terminal.py'
    skill_buff_path = ROOT / 'scripts/game_data/memorypack' / 'buff.py'
    skill_core_path = ROOT / 'scripts/game_data/memorypack' / 'core.py'
    buff_actions_path = ROOT / 'scripts/game_data/memorypack' / 'buff_actions.py'
    buff_path=ROOT/'reports/animestudio/buffdata_current_latest.json'
    buff_sha=sha(buff_path);buff_corpus=json.loads(buff_path.read_text(encoding='utf-8'))
    verify_family_report_inputs(buff_corpus,expected_format='animestudio-buffdata-current-vfs-corpus',label='BuffData')
    require(buff_corpus['inputSetSha256'],corpus['inputSetSha256'],buff_path)
    require(buff_corpus['status'],'complete',buff_path)
    mapper_path = ROOT / 'tools/endfield-il2cpp/map_body_targets_to_gameassembly.py'
    catalog_path = ROOT / 'tools/endfield-il2cpp/catalog_option_flow_metadata.py'
    sources = [Path(__file__), Path(__file__).with_name('context.py'),
               Path(__file__).with_name('context_audit_common.py'),
               Path(__file__).with_name('context_audit_memorypack.py'),
               Path(__file__).with_name('context_audit_skilldata.py'),
               Path(__file__).with_name('context_audit_vfs.py'),
               NATIVE_CONTRACT_PATH, OBSERVER_CONTRACT_PATH,
               mapper_path, catalog_path, ROOT / 'scripts/common.py',
               skill_terminal_path, skill_buff_path, skill_core_path, buff_actions_path,
               skill_sample_path, *terminal_branch_sample_paths,
               *actiongroup_branch_sample_paths,
               *actiongroup_branch_census_sample_paths,
               CONTRACTS_DIR / 'buff_ec_native.json',
               CONTRACTS_DIR / 'buff_50_native.json',
               CONTRACTS_DIR / 'buff_11f_native.json',
               CONTRACTS_DIR / 'buff_b4_native.json',
               CONTRACTS_DIR / 'buff_56_native.json',
               CONTRACTS_DIR / 'buff_92_native.json',
               CONTRACTS_DIR / 'buff_57_native.json',
               CONTRACTS_DIR / 'buff_5b_native.json',
               CONTRACTS_DIR / 'buff_3c_native.json',
               CONTRACTS_DIR / 'buff_78_native.json',
               CONTRACTS_DIR / 'buff_b2_native.json',
               CONTRACTS_DIR / 'buff_68_native.json',
               CONTRACTS_DIR / 'buff_81_native.json',
               CONTRACTS_DIR / 'buff_58_native.json',
               CONTRACTS_DIR / 'buff_02_native.json',
               CONTRACTS_DIR / 'buff_9a_native.json',
               CONTRACTS_DIR / 'buff_a2_native.json',
               CONTRACTS_DIR / 'buff_65_native.json',
               CONTRACTS_DIR / 'buff_169_native.json',
               CONTRACTS_DIR / 'buff_157_native.json',
               CONTRACTS_DIR / 'buff_6e_native.json',
               CONTRACTS_DIR / 'buff_fe_native.json',
               CONTRACTS_DIR / 'buff_96_native.json',
               CONTRACTS_DIR / 'buff_fd_native.json',
               CONTRACTS_DIR / 'buff_7c_native.json',
               CONTRACTS_DIR / 'buff_b6_native.json',
               CONTRACTS_DIR / 'buff_80_native.json',
               CONTRACTS_DIR / 'buff_16e_native.json',
               CONTRACTS_DIR / 'buff_7b_native.json',
               CONTRACTS_DIR / 'buff_6d_native.json',
               CONTRACTS_DIR / 'buff_136_native.json',
               CONTRACTS_DIR / 'buff_163_native.json',
               CONTRACTS_DIR / 'buff_69_native.json',
               CONTRACTS_DIR / 'buff_44_native.json',
               CONTRACTS_DIR / 'buff_10f_native.json',
               CONTRACTS_DIR / 'buff_9b_native.json',
               CONTRACTS_DIR / 'buff_c5_native.json',
               CONTRACTS_DIR / 'buff_119_native.json',
               CONTRACTS_DIR / 'buff_0a_native.json',
               CONTRACTS_DIR / 'buff_7a_native.json',
               CONTRACTS_DIR / 'buff_88_native.json',
               CONTRACTS_DIR / 'buff_48_native.json',
               CONTRACTS_DIR / 'buff_5a_native.json',
               CONTRACTS_DIR / 'buff_c4_native.json',
               CONTRACTS_DIR / 'buff_145_native.json',
               CONTRACTS_DIR / 'buff_de_native.json',
               CONTRACTS_DIR / 'buff_bd_native.json',
               CONTRACTS_DIR / 'buff_6a_native.json',
               CONTRACTS_DIR / 'buff_24_native.json',
               CONTRACTS_DIR / 'buff_16b_native.json',
               CONTRACTS_DIR / 'buff_7e_native.json',
               CONTRACTS_DIR / 'buff_35_native.json',
               CONTRACTS_DIR / 'buff_ea_native.json',
               CONTRACTS_DIR / 'buff_61_native.json',
               CONTRACTS_DIR / 'buff_3f_native.json',
               CONTRACTS_DIR / 'buff_14d_native.json',
               CONTRACTS_DIR / 'buff_73_native.json',
               CONTRACTS_DIR / 'buff_5d_native.json',
               CONTRACTS_DIR / 'buff_42_native.json',
               CONTRACTS_DIR / 'buff_27_native.json',
               CONTRACTS_DIR / 'buff_95_native.json',
               CONTRACTS_DIR / 'buff_74_native.json',
               CONTRACTS_DIR / 'buff_16d_native.json',
               CONTRACTS_DIR / 'buff_160_native.json',
               CONTRACTS_DIR / 'buff_89_native.json',
               CONTRACTS_DIR / 'buff_171_native.json',
               CONTRACTS_DIR / 'buff_132_native.json',
               CONTRACTS_DIR / 'buff_d4_native.json',
               CONTRACTS_DIR / 'buff_d5_native.json',
               CONTRACTS_DIR / 'buff_d6_native.json',
               CONTRACTS_DIR / 'buff_60_native.json',
               CONTRACTS_DIR / 'buff_126_native.json',
               CONTRACTS_DIR / 'buff_1c_native.json',
               CONTRACTS_DIR / 'buff_06_native.json',
               CONTRACTS_DIR / 'buff_142_native.json',
               CONTRACTS_DIR / 'buff_03_native.json',
               CONTRACTS_DIR / 'buff_51_native.json',
               CONTRACTS_DIR / 'buff_5e_native.json',
               CONTRACTS_DIR / 'buff_13b_native.json',
               CONTRACTS_DIR / 'buff_84_native.json',
               CONTRACTS_DIR / 'buff_174_native.json',
               CONTRACTS_DIR / 'buff_41_native.json',
               CONTRACTS_DIR / 'buff_a9_native.json',
               CONTRACTS_DIR / 'buff_62_native.json',
               CONTRACTS_DIR / 'buff_13c_native.json',
               CONTRACTS_DIR / 'buff_90_native.json',
               CONTRACTS_DIR / 'buff_bb_native.json',
               CONTRACTS_DIR / 'buff_0b_native.json',
               CONTRACTS_DIR / 'buff_2b_native.json',
               CONTRACTS_DIR / 'buff_115_native.json',
               CONTRACTS_DIR / 'buff_151_native.json',
               CONTRACTS_DIR / 'buff_13f_native.json',
               CONTRACTS_DIR / 'buff_140_native.json',
               CONTRACTS_DIR / 'buff_98_native.json',
               CONTRACTS_DIR / 'buff_176_native.json',
               CONTRACTS_DIR / 'buff_93_native.json',
               CONTRACTS_DIR / 'buff_175_native.json',
               CONTRACTS_DIR / 'buff_fc_native.json',
               CONTRACTS_DIR / 'buff_83_native.json',
               CONTRACTS_DIR / 'buff_13a_native.json',
               CONTRACTS_DIR / 'buff_86_native.json',
               CONTRACTS_DIR / 'buff_63_native.json',
               CONTRACTS_DIR / 'buff_6b_native.json',
               CONTRACTS_DIR / 'buff_77_native.json',
               CONTRACTS_DIR / 'buff_188_native.json',
               CONTRACTS_DIR / 'buff_40_native.json',
               CONTRACTS_DIR / 'buff_187_native.json',
               CONTRACTS_DIR / 'buff_139_native.json',
               CONTRACTS_DIR / 'buff_18a_native.json',
               CONTRACTS_DIR / 'buff_135_native.json',
               CONTRACTS_DIR / 'buff_122_native.json',
               CONTRACTS_DIR / 'buff_5c_native.json',
               CONTRACTS_DIR / 'buff_183_native.json',
               CONTRACTS_DIR / 'buff_2f_native.json',
               CONTRACTS_DIR / 'buff_15c_native.json',
               CONTRACTS_DIR / 'buff_16f_native.json',
               CONTRACTS_DIR / 'buff_05_native.json',
               CONTRACTS_DIR / 'buff_3a_native.json',
               CONTRACTS_DIR / 'buff_4c_native.json',
               CONTRACTS_DIR / 'buff_150_native.json',
               CONTRACTS_DIR / 'buff_a7_native.json',
               CONTRACTS_DIR / 'buff_19e_native.json',
               CONTRACTS_DIR / 'buff_08_native.json',
               CONTRACTS_DIR / 'buff_120_native.json',
               CONTRACTS_DIR / 'buff_9f_native.json',
               CONTRACTS_DIR / 'buff_1b_native.json',
               CONTRACTS_DIR / 'buff_87_native.json',
               CONTRACTS_DIR / 'buff_52_native.json',
               CONTRACTS_DIR / 'buff_8e_native.json',
               CONTRACTS_DIR / 'finder_0a_native.json',
               CONTRACTS_DIR / 'finder_15_native.json',
               CONTRACTS_DIR / 'finder_0e_native.json',
               CONTRACTS_DIR / 'buff_125_native.json',
               CONTRACTS_DIR / 'buff_124_native.json',
               CONTRACTS_DIR / 'buff_14f_native.json',
               CONTRACTS_DIR / 'buff_71_native.json',
               CONTRACTS_DIR / 'buff_70_native.json',
               CONTRACTS_DIR / 'finder_10_native.json',
               CONTRACTS_DIR / 'finder_01_native.json',
               CONTRACTS_DIR / 'validator_01_native.json',
               CONTRACTS_DIR / 'buff_root_prefix_native.json',
               CONTRACTS_DIR / 'buff_root_fifth_native.json',
               CONTRACTS_DIR / 'buff_root_sixth_native.json',
               CONTRACTS_DIR / 'buff_159_native.json',
               CONTRACTS_DIR / 'buff_16_native.json',
               CONTRACTS_DIR / 'buff_178_native.json',
               CONTRACTS_DIR / 'buff_c1_native.json',
               CONTRACTS_DIR / 'buff_101_native.json',
               CONTRACTS_DIR / 'buff_c7_native.json',
               CONTRACTS_DIR / 'buff_19b_native.json',
               CONTRACTS_DIR / 'buff_128_native.json',
               CONTRACTS_DIR / 'buff_164_native.json',
               CONTRACTS_DIR / 'buff_cf_native.json',
               CONTRACTS_DIR / 'buff_12b_native.json',
               CONTRACTS_DIR / 'buff_2c_native.json',
               CONTRACTS_DIR / 'buff_damage_lists_native.json',
               CONTRACTS_DIR / 'buff_calc5_native.json',
               CONTRACTS_DIR / 'buff_calc1_native.json',
               CONTRACTS_DIR / 'finder_00_native.json',
               CONTRACTS_DIR / 'validator_02_native.json',
               CONTRACTS_DIR / 'postprocessor_08_native.json',
               CONTRACTS_DIR / 'buff_127_native.json',
               CONTRACTS_DIR / 'buff_ab_native.json',
               CONTRACTS_DIR / 'buff_f6_native.json',
               CONTRACTS_DIR / 'buff_17c_native.json',
               CONTRACTS_DIR / 'buff_186_native.json',
               CONTRACTS_DIR / 'buff_b9_native.json',
               CONTRACTS_DIR / 'buff_f4_native.json',
               CONTRACTS_DIR / 'buff_133_native.json',
               CONTRACTS_DIR / 'buff_14a_native.json',
               CONTRACTS_DIR / 'buff_15d_native.json',
               CONTRACTS_DIR / 'buff_37_native.json',
               CONTRACTS_DIR / 'buff_12a_native.json',
               CONTRACTS_DIR / 'buff_144_native.json',
               CONTRACTS_DIR / 'buff_15b_native.json',
               CONTRACTS_DIR / 'buff_07_native.json',
               CONTRACTS_DIR / 'buff_18b_native.json',
               CONTRACTS_DIR / 'buff_19c_native.json',
               CONTRACTS_DIR / 'buff_8a_native.json',
               CONTRACTS_DIR / 'postprocessor_01_native.json',
               CONTRACTS_DIR / 'buff_14b_native.json',
               CONTRACTS_DIR / 'buff_166_native.json',
               CONTRACTS_DIR / 'buff_16c_native.json',
               CONTRACTS_DIR / 'buff_85_native.json',
               CONTRACTS_DIR / 'buff_94_native.json',
               CONTRACTS_DIR / 'buff_179_native.json',
               CONTRACTS_DIR / 'buff_158_native.json',
               CONTRACTS_DIR / 'buff_15a_native.json',
               CONTRACTS_DIR / 'buff_192_native.json',
               CONTRACTS_DIR / 'buff_bc_native.json',
               CONTRACTS_DIR / 'buff_14e_native.json',
               CONTRACTS_DIR / 'buff_0d_native.json',
               CONTRACTS_DIR / 'buff_0c_native.json',
               CONTRACTS_DIR / 'buff_26_native.json',
               CONTRACTS_DIR / 'buff_10c_native.json',
               CONTRACTS_DIR / 'buff_e0_native.json',
               CONTRACTS_DIR / 'buff_172_native.json',
               CONTRACTS_DIR / 'buff_28_native.json',
               CONTRACTS_DIR / 'buff_102_native.json',
               CONTRACTS_DIR / 'buff_18e_native.json',
               CONTRACTS_DIR / 'buff_ce_native.json',
               CONTRACTS_DIR / 'buff_17_native.json',
               CONTRACTS_DIR / 'buff_ad_native.json',
               CONTRACTS_DIR / 'buff_198_native.json',
               CONTRACTS_DIR / 'buff_197_native.json',
               CONTRACTS_DIR / 'buff_91_native.json',
               CONTRACTS_DIR / 'buff_184_native.json',
               CONTRACTS_DIR / 'buff_df_native.json',
               CONTRACTS_DIR / 'buff_1f_native.json',
               CONTRACTS_DIR / 'buff_b7_native.json',
               CONTRACTS_DIR / 'buff_f0_native.json',
               CONTRACTS_DIR / 'buff_55_native.json',
               CONTRACTS_DIR / 'buff_36_native.json',
               CONTRACTS_DIR / 'buff_20_native.json',
               CONTRACTS_DIR / 'buff_a8_native.json',
               CONTRACTS_DIR / 'buff_23_native.json',
               CONTRACTS_DIR / 'buff_16a_native.json',
               CONTRACTS_DIR / 'buff_6f_native.json',
               CONTRACTS_DIR / 'buff_161_native.json',
               CONTRACTS_DIR / 'buff_c0_native.json',
               CONTRACTS_DIR / 'buff_11c_native.json',
               CONTRACTS_DIR / 'buff_8c_native.json',
               CONTRACTS_DIR / 'buff_4e_native.json']
    source_hashes = {str(p): sha(p) for p in dict.fromkeys(sources)}
    mapper = load_native_mapper(mapper_path)
    catalog = load_metadata_helper(catalog_path)
    pe = mapper.PeImage(gate.gameassembly)
    md = catalog.Metadata(gate.metadata)
    require(hashlib.sha256(pe.buf).hexdigest().upper(), GA_SHA, gate.gameassembly)
    require(hashlib.sha256(md.buf).hexdigest().upper(), MD_SHA, gate.metadata)
    pins = AUDIT_PINS
    registration_pins = pins['registration']
    candidates = mapper.find_code_registration_candidates(pe, {md.string(x.name_index) for x in md.images})
    require(candidates, [registration_pins['codeRegistrationVa']], gate.gameassembly)
    image_owners = type_image_owners(md.buf, len(md.types), source=str(gate.metadata))
    require(pe.u32_at_va(candidates[0]+0x68), len(md.images), gate.gameassembly, candidates[0]+0x68)
    module_pointers = pe.bytes_at_va(pe.u64_at_va(candidates[0]+0x70), len(md.images)*8)
    module_rows = [(pe.c_string_at_va(pe.u64_at_va(pointer)), pointer)
                   for (pointer,) in struct.iter_unpack('<Q', module_pointers)]
    modules = match_image_modules([md.string(item.name_index) for item in md.images],
                                  module_rows, source=str(gate.gameassembly))
    image_rows = []
    module_rgctx_bytes = {}
    rgctx_inventory = []
    for item in md.images:
        name = md.string(item.name_index)
        if name not in modules:
            raise ContextError(str(gate.metadata), item.index, 'matching CodeGenModule name', name)
        image_rows.append({'imageIndex': item.index, 'name': name, 'typeStart': item.type_start,
                           'typeCount': item.type_count, 'moduleVa': modules[name]})
        entry_count=pe.u32_at_va(modules[name]+0x50)
        entry_base=pe.u64_at_va(modules[name]+0x58)
        require(entry_count<=1_000_000,True,gate.gameassembly,modules[name]+0x50)
        entry_bytes=pe.bytes_at_va(entry_base,entry_count*16) if entry_count else b''
        decoded_entries=rgctx_range_entries(entry_bytes,0,entry_count,source=str(gate.gameassembly),offset=entry_base)
        require(len(decoded_entries),entry_count,gate.gameassembly,entry_base)
        module_rgctx_bytes[name]=(entry_base,entry_bytes)
        rgctx_inventory.append({'imageIndex':item.index,'name':name,'entryBaseVa':entry_base,
                                'success':entry_count,'failed':0,'unsupported':0,
                                'sha256':hashlib.sha256(entry_bytes).hexdigest().upper()})
    registration = mapper.find_metadata_registration(pe, candidates[0])
    require(registration, registration_pins['metadataRegistrationVa'], gate.gameassembly)
    for begin, end, expected in CONSUMER_WINDOWS:
        require(hashlib.sha256(pe.bytes_at_va(pe.image_base + begin, end-begin)).hexdigest().upper(),
                expected, gate.gameassembly, begin)
    rip_targets = {
        'codeRegistration': candidates[0],
        'codeRegistrationGlobal': pe.image_base+registration_pins['codeRegistrationGlobalRva'],
        'usageCell': pe.image_base+pins['selectedUsageCell']['rva'],
    }
    for rva, prefix, target in registration_pins['ripReferences']:
        expected = rip_targets[target]
        instruction = pe.bytes_at_va(pe.image_base+rva, 7)
        require(instruction[:3].hex().upper(), prefix, gate.gameassembly, rva)
        require(pe.image_base+rva+7+struct.unpack_from('<i', instruction, 3)[0], expected,
                gate.gameassembly, rva)
    reg = mapper.metadata_registration_summary(pe, registration)
    table = GenericInstantiationTable(pe.bytes_at_va, int(reg['genericInsts'], 16),
                                     reg['genericInstsCount'], source=str(gate.gameassembly))
    summary, rows, failures = sweep(table)
    # Explicit raw MethodSpec -> pointer-table join, not an observed invocation.
    spec_pins = pins['selectedMethodSpec']
    spec_index = spec_pins['index']
    if not 0 <= spec_index < reg['methodSpecsCount']:
        raise ContextError(str(gate.gameassembly), registration, 'bounded MethodSpec index', spec_index)
    spec_va = int(reg['methodSpecs'], 16) + spec_index * 12
    raw = pe.bytes_at_va(spec_va, 12)
    definition, class_inst, method_inst = struct.unpack('<iii', raw)
    require((definition, class_inst, method_inst), tuple(spec_pins['record']), gate.gameassembly, spec_va)
    selected = table.resolve(method_inst)
    require(len(selected.arguments), 1, gate.gameassembly, selected.record_va)
    type_raw = bytes.fromhex(selected.arguments[0].raw_type_record_hex)
    require(type_raw[10], 0x1E, gate.gameassembly, selected.arguments[0].type_pointer_va)
    owner = method_parameter_owner(md.buf, struct.unpack_from('<Q', type_raw)[0],
                                   [m.generic_container_index for m in md.methods], source=str(gate.metadata))
    require(owner['methodIndex'], spec_pins['openMethodParameterOwner'], gate.metadata, owner['containerOffset'])
    selected_method_spec={'index':spec_index,'va':spec_va,'rawHex':raw.hex().upper(),
                          'definition':definition,'methodInstantiation':selected.as_dict(),
                          'openMethodParameterOwner':owner}
    usage_pins = pins['selectedUsageCell']
    usage_va = pe.image_base+usage_pins['rva']
    usage_raw = pe.bytes_at_va(usage_va, 8)
    call_index = method_spec_usage_index(usage_raw, reg['methodSpecsCount'],
                                         source=str(gate.gameassembly), offset=usage_va)
    require(call_index, usage_pins['methodSpecIndex'], gate.gameassembly, usage_va)
    # Usage tag 6 selects one entry of the lazy resolver's switch table. The
    # pinned branch forwards the original encoding to the tag-6 path, which
    # resolves MethodSpec -> triple -> method-pointer lookup.
    resolver_pins = usage_pins['resolverSwitch']
    resolver_entry = resolver_pins['tableRva']+resolver_pins['index']*4
    require(pe.u32_at_va(pe.image_base+resolver_entry), resolver_pins['targetRva'],
            gate.gameassembly, resolver_entry)
    if not 0 <= call_index < reg['methodSpecsCount']:
        raise ContextError(str(gate.gameassembly), registration, 'bounded call MethodSpec index', call_index)
    call_va = int(reg['methodSpecs'], 16) + call_index * 12
    call_raw = pe.bytes_at_va(call_va, 12)
    call_definition, call_class, call_method = struct.unpack('<iii', call_raw)
    call_pins = pins['selectedCallMethodSpec']
    require((call_definition, call_class, call_method),
            (owner['methodIndex'], -1, call_pins['methodInstantiation']),
            gate.gameassembly, call_va)
    call_inst = table.resolve(call_method)
    ordinal = owner['ordinal']
    if not 0 <= ordinal < len(call_inst.arguments):
        raise ContextError(str(gate.gameassembly), call_inst.record_va,
                           'ordinal within selected call instantiation', ordinal)
    argument = call_inst.arguments[ordinal]
    require(argument.raw_type_record_hex, call_pins['selectedRawArgument'],
            gate.gameassembly, argument.type_pointer_va)
    formatter_pins = pins['selectedFormatterTypeCarrier']
    range_count, entry_count = formatter_pins['rgctxRangeCount'], formatter_pins['rgctxEntryCount']
    module = modules['MemoryPack.dll']
    require(pe.u32_at_va(module+0x40), range_count, gate.gameassembly, module+0x40)
    require(pe.u32_at_va(module+0x50), entry_count, gate.gameassembly, module+0x50)
    ranges_va = pe.u64_at_va(module+0x48)
    start, count = select_rgctx_range(pe.bytes_at_va(ranges_va,range_count*12),entry_count,
                                      formatter_pins['methodToken'],
                                      source=str(gate.gameassembly),offset=ranges_va)
    require((start,count),tuple(formatter_pins['rgctxRange']),gate.gameassembly,ranges_va)
    entry_va = pe.u64_at_va(module+0x58)+(start+formatter_pins['relativeEntry'])*16
    entry_raw = pe.bytes_at_va(entry_va,16)
    require(struct.unpack_from('<I',entry_raw)[0],2,gate.gameassembly,entry_va)
    type_index = pe.u32_at_va(struct.unpack_from('<Q',entry_raw,8)[0])
    require(type_index,formatter_pins['typeIndex'],gate.gameassembly,entry_va)
    require(type_index<reg['typesCount'],True,gate.gameassembly,entry_va)
    type_pointer = pe.u64_at_va(int(reg['types'],16)+type_index*8)
    formatter_type_raw = pe.bytes_at_va(type_pointer,16)
    carrier_raw = pe.bytes_at_va(struct.unpack_from('<Q',formatter_type_raw)[0],32)
    base_raw = pe.bytes_at_va(struct.unpack_from('<Q',carrier_raw)[0],16)
    formatter_carrier = generic_type_carrier(formatter_type_raw,carrier_raw,base_raw,
                                             type_pointer=type_pointer,type_count=len(md.types),source=str(gate.gameassembly))
    formatter_inst = table.resolve_pointer(formatter_carrier['classInstantiationPointerVa'])
    require(formatter_inst.index, selected.index, gate.gameassembly,formatter_inst.record_va)
    formatter_definition = formatter_pins['baseDefinitionIndex']
    require(formatter_carrier['baseDefinitionIndex'],formatter_definition,gate.metadata)
    require(md.type_full_name(md.types[formatter_definition]),'MemoryPack.MemoryPackFormatter`1',gate.metadata)
    # One switch over Il2CppType tags; its GENERICINST (0x15) and VAR (0x13)
    # entries are checked where each carrier kind is joined.
    tag_switch = pins['typeTagSwitch']
    tag_targets = dict(tag_switch['targets'])
    require(pe.u32_at_va(pe.image_base+tag_switch['tableRva']+(0x15-tag_switch['firstTag'])*4),
            tag_targets[0x15],gate.gameassembly,tag_switch['tableRva'])
    # Static immediate-registration site: identity joins only, not live state.
    adapter_pins = pins['selectedImmediateAdapter']
    adapter_cells = []
    cell_roles = {}
    for rva, opcode, tag, expected_index, role in adapter_pins['cells']:
        cell_roles.setdefault(role, []).append(len(adapter_cells))
        instruction = pe.bytes_at_va(pe.image_base+rva, 7)
        require(instruction[:3], bytes.fromhex(opcode), gate.gameassembly, rva)
        cell = rip_qword_load_target(instruction,pe.image_base+rva,source=str(gate.gameassembly))
        cell_raw = pe.bytes_at_va(cell, 8)
        index = unresolved_usage_index(cell_raw, reg['methodSpecsCount'] if tag == 6 else reg['typesCount'],
                                       tag=tag, source=str(gate.gameassembly), offset=cell)
        require(index, expected_index, gate.gameassembly, cell)
        adapter_cells.append({'instructionRva':rva, 'instructionHex':instruction.hex().upper(),
                              'cellVa':cell, 'rawHex':cell_raw.hex().upper(), 'tag':tag, 'index':index})
    # Both constructor loads must read one cell; each role names one index.
    constructor_rows = cell_roles.get('constructor', [])
    require(len(constructor_rows), 2, NATIVE_CONTRACT_PATH)
    require(adapter_cells[constructor_rows[0]]['cellVa'], adapter_cells[constructor_rows[1]]['cellVa'],
            gate.gameassembly)
    require(sorted(cell_roles), ['adapterType', 'constructor', 'keyType'], NATIVE_CONTRACT_PATH)
    adapter_type_index = adapter_cells[cell_roles['adapterType'][0]]['index']
    key_type_index = adapter_cells[cell_roles['keyType'][0]]['index']
    constructor_spec_index = adapter_cells[constructor_rows[0]]['index']
    adapter_pointer = pe.u64_at_va(int(reg['types'],16)+adapter_type_index*8)
    adapter_raw = pe.bytes_at_va(adapter_pointer,16)
    adapter_carrier_raw = pe.bytes_at_va(struct.unpack_from('<Q',adapter_raw)[0],32)
    adapter_base_raw = pe.bytes_at_va(struct.unpack_from('<Q',adapter_carrier_raw)[0],16)
    adapter = generic_type_carrier(adapter_raw,adapter_carrier_raw,adapter_base_raw,
                                   type_pointer=adapter_pointer,type_count=len(md.types),source=str(gate.gameassembly))
    adapter_definition = adapter_pins['baseDefinitionIndex']
    require(adapter['baseDefinitionIndex'],adapter_definition,gate.metadata)
    require(md.type_full_name(md.types[adapter_definition]),'Beyond.MemoryPack.GenericMemoryPackFormatter`2',gate.metadata)
    adapter_inst = table.resolve_pointer(adapter['classInstantiationPointerVa'])
    require(adapter_inst.index,adapter_pins['classInstantiation'],gate.gameassembly)
    require(len(adapter_inst.arguments),2,gate.gameassembly)
    adapter_module=modules['MemoryPack.Beyond.dll']
    require(image_owners[adapter_definition],adapter_pins['imageIndex'],gate.metadata)
    require(md.types[adapter_definition].token,adapter_pins['token'],gate.metadata)
    adapter_range_count=adapter_pins['rgctxRangeCount']
    require(pe.u32_at_va(adapter_module+0x40),adapter_range_count,gate.gameassembly,adapter_module+0x40)
    adapter_ranges=pe.u64_at_va(adapter_module+0x48)
    adapter_entry_base,adapter_entry_bytes=module_rgctx_bytes['MemoryPack.Beyond.dll']
    adapter_start,adapter_count=select_rgctx_range(pe.bytes_at_va(adapter_ranges,adapter_range_count*12),len(adapter_entry_bytes)//16,
                                                   md.types[adapter_definition].token,source=str(gate.gameassembly),offset=adapter_ranges)
    require((adapter_start,adapter_count),tuple(adapter_pins['rgctxRange']),gate.gameassembly,adapter_ranges)
    adapter_entries=rgctx_range_entries(adapter_entry_bytes,adapter_start,adapter_count,
                                        source=str(gate.gameassembly),offset=adapter_entry_base)
    adapter_conversion=adapter_conversion_context(pe,md,reg,table,adapter_entries,source=str(gate.gameassembly))
    slot_pins=pins['selectedAdapterClassSlot']
    type_slot=adapter_entries[slot_pins['relativeIndex']]
    require_code_bytes(pe,slot_pins['consumerRva'],slot_pins['consumerHex'],gate.gameassembly)
    require(type_slot['kindRaw'],1,gate.gameassembly,type_slot['entryVa'])
    slot_type_index=pe.u32_at_va(type_slot['dataPointerVa'])
    require(slot_type_index,slot_pins['typeIndex'],gate.gameassembly,type_slot['dataPointerVa'])
    require(slot_type_index<reg['typesCount'],True,gate.gameassembly,type_slot['dataPointerVa'])
    slot_type_pointer=pe.u64_at_va(int(reg['types'],16)+slot_type_index*8)
    slot_type_raw=pe.bytes_at_va(slot_type_pointer,16)
    require(slot_type_raw[10],0x13,gate.gameassembly,slot_type_pointer+10)
    slot_owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',slot_type_raw)[0],
                                    [t.generic_container_index for t in md.types],source=str(gate.metadata))
    require((slot_owner['typeIndex'],slot_owner['ordinal']),(adapter_definition,1),gate.metadata,slot_owner['containerOffset'])
    require(pe.u32_at_va(pe.image_base+tag_switch['tableRva']+(0x13-tag_switch['firstTag'])*4),
            tag_targets[0x13],gate.gameassembly,tag_switch['tableRva'])
    slot_argument=adapter_inst.arguments[slot_owner['ordinal']]
    nested_slots=[]
    for relative,expected_definition in pins['selectedNestedAdapterSlots']:
        entry=adapter_entries[relative]
        require(entry['kindRaw'],3,gate.gameassembly,entry['entryVa'])
        index=pe.u32_at_va(entry['dataPointerVa'])
        require(index<reg['methodSpecsCount'],True,gate.gameassembly,entry['dataPointerVa'])
        spec_va=int(reg['methodSpecs'],16)+index*12
        spec_raw=pe.bytes_at_va(spec_va,12)
        definition,ci,mi=method_spec_record(spec_raw,len(md.methods),reg['genericInstsCount'],
                                           source=str(gate.gameassembly),offset=spec_va)
        require(definition,expected_definition,gate.metadata)
        contexts=[]
        for kind,inst_index in (('class',ci),('method',mi)):
            inst=table.resolve(inst_index)
            arguments=[]
            for arg in inst.arguments:
                raw=bytes.fromhex(arg.raw_type_record_hex)
                require(raw[10],0x13,gate.gameassembly,arg.type_pointer_va+10)
                owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',raw)[0],
                                            [t.generic_container_index for t in md.types],source=str(gate.metadata))
                require(owner['typeIndex'],adapter_definition,gate.metadata,owner['containerOffset'])
                require(owner['ordinal']<len(adapter_inst.arguments),True,gate.metadata,owner['parameterOffset'])
                concrete=adapter_inst.arguments[owner['ordinal']]
                arguments.append({'rawHex':arg.raw_type_record_hex,'owner':owner,
                                  'conditionalArgumentRawHex':concrete.raw_type_record_hex})
            contexts.append({'kind':kind,'instantiationIndex':inst_index,'arguments':arguments})
        nested_slots.append({'relativeIndex':relative,'moduleEntryIndex':entry['moduleEntryIndex'],
                             'methodSpecIndex':index,'methodSpecRawHex':spec_raw.hex().upper(),
                             'definition':definition,'methodName':md.string(md.methods[definition].name_index),'contexts':contexts})
    nested_relatives=[str(row['relativeIndex']) for row in nested_slots]
    nested_slot_names=', '.join(nested_relatives[:-1])+' and '+nested_relatives[-1]
    companion_pins=pins['selectedMethodCompanionConstruction']
    require_code_bytes(pe,*companion_pins['classStore'],gate.gameassembly)
    require_code_bytes(pe,*companion_pins['resolverCall'],gate.gameassembly)
    require([a.raw_type_record_hex for a in adapter_inst.arguments],
            adapter_pins['argumentRawTypes'],gate.gameassembly)
    require(md.type_full_name(md.types[adapter_pins['wrapperTypeDefinition']]),'Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack',gate.metadata)
    key_pointer = pe.u64_at_va(int(reg['types'],16)+key_type_index*8)
    require(key_pointer,adapter_inst.arguments[0].type_pointer_va,gate.gameassembly)
    ctor_va = int(reg['methodSpecs'],16)+constructor_spec_index*12
    ctor_raw = pe.bytes_at_va(ctor_va,12)
    ctor_definition = adapter_pins['constructorDefinition']
    require(struct.unpack('<iii',ctor_raw),(ctor_definition,adapter_pins['classInstantiation'],-1),gate.gameassembly,ctor_va)
    require(md.methods[ctor_definition].declaring_type,adapter_definition,gate.metadata)
    require(md.string(md.methods[ctor_definition].name_index),'.ctor',gate.metadata)
    for rva,hex_bytes in adapter_pins['registrationJumps']:
        require_code_bytes(pe,rva,hex_bytes,gate.gameassembly)
    storage_pins = pins['selectedProviderStorage']
    storage_references = []
    for rva in storage_pins['references']:
        instruction = pe.bytes_at_va(pe.image_base+rva,7)
        target = rip_qword_load_target(instruction,pe.image_base+rva,source=str(gate.gameassembly))
        require(target,pe.image_base+storage_pins['storageRva'],gate.gameassembly,rva)
        storage_references.append({'instructionRva':rva,'instructionHex':instruction.hex().upper(),'targetVa':target})
    storage_raw = pe.bytes_at_va(storage_references[0]['targetVa'],8)
    sharing_pins = pins['selectedSharingBranch']
    sharing_instruction = pe.bytes_at_va(pe.image_base+sharing_pins['loadRva'],7)
    sharing_global = class_sharing_branch(pe.bytes_at_va(pe.image_base+sharing_pins['compareRva'],10),
                                          pe.image_base+sharing_pins['compareRva'],
                                          sharing_instruction,pe.image_base+sharing_pins['loadRva'],
                                          pe.bytes_at_va(pe.image_base+sharing_pins['advanceRva'],4),
                                          source=str(gate.gameassembly))
    require(sharing_global,pe.image_base+sharing_pins['canonicalCarrierGlobalRva'],gate.gameassembly,
            sharing_pins['loadRva'])
    require([bytes.fromhex(a.raw_type_record_hex)[10] for a in adapter_inst.arguments],[0x12,0x12],gate.gameassembly)
    object_pins = pins['selectedObjectIdentity']
    object_identity = named_top_level_type(md.buf,b'mscorlib.dll',b'System',b'Object',source=str(gate.metadata))
    require((object_identity['imageIndex'],object_identity['typeDefinitionIndex'],object_identity['byvalTypeIndex']),
            tuple(object_pins['metadata']),gate.metadata,object_identity['typeDefinitionOffset'])
    require(object_identity['byvalTypeIndex']<reg['typesCount'],True,gate.metadata)
    object_pointer=pe.u64_at_va(int(reg['types'],16)+object_identity['byvalTypeIndex']*8)
    object_raw=pe.bytes_at_va(object_pointer,16)
    require(object_raw.hex().upper(),object_pins['rawTypeHex'],gate.gameassembly,object_pointer)
    object_pair=table.resolve(object_pins['objectPairInstantiation'])
    require([a.raw_type_record_hex for a in object_pair.arguments],[object_raw.hex().upper()]*2,gate.gameassembly)
    # The code window ends before this separately read switch-data entry; the
    # object (0x1C) tag selects it.
    comparison_pins=pins['selectedObjectComparison']
    switch_entry=pe.image_base+comparison_pins['switchTableRva']+(0x1C-comparison_pins['firstTag'])*4
    require(pe.u32_at_va(switch_entry),comparison_pins['switchTargetRva'],gate.gameassembly,switch_entry)
    object_key=object_type_comparison_key(object_raw,source=str(gate.gameassembly),offset=object_pointer)
    require(summary['failed'],0,'complete generic-instantiation sweep before candidate enumeration')
    object_candidates=[]
    for row in rows:
        arguments=row['arguments']
        if len(arguments)!=2:
            continue
        raw_arguments=[bytes.fromhex(a['raw_type_record_hex']) for a in arguments]
        if any(raw[10]!=0x1C for raw in raw_arguments):
            continue
        keys=[object_type_comparison_key(raw,source=str(gate.gameassembly),offset=a['type_pointer_va'])
              for raw,a in zip(raw_arguments,arguments)]
        if keys==[object_key,object_key]:
            object_candidates.append(row['index'])
    shared_definition=pins['selectedSharedMethodCandidates']['definition']
    require(md.methods[shared_definition].declaring_type,adapter_definition,gate.metadata)
    require(md.string(md.methods[shared_definition].name_index),'Deserialize',gate.metadata)
    specs_base=int(reg['methodSpecs'],16)
    specs_raw=pe.bytes_at_va(specs_base,reg['methodSpecsCount']*12)
    spec_records=[method_spec_record(specs_raw[index*12:(index+1)*12],len(md.methods),reg['genericInstsCount'],
                                     source=str(gate.gameassembly),offset=specs_base+index*12)
                  for index in range(reg['methodSpecsCount'])]
    validate_selected_method_spec(selected_method_spec,specs_raw,specs_base,len(md.methods),
                                   reg['genericInstsCount'],source=str(gate.gameassembly))
    shared_specs=[index for index,(definition,ci,mi) in enumerate(spec_records)
                  if definition==shared_definition and ci in object_candidates and mi==-1]
    code=mapper.code_registration_summary(pe,candidates[0])
    methods_base=int(reg['genericMethodTable'],16)
    methods_raw=pe.bytes_at_va(methods_base,reg['genericMethodTableCount']*16)
    shared_rows=[]
    for index,(spec_index,_,_,_) in enumerate(struct.iter_unpack('<iiii',methods_raw)):
        if spec_index not in shared_specs:
            continue
        triple_raw=methods_raw[index*16+4:index*16+16]
        method,invoker,adjustor=method_pointer_indices(triple_raw,code['genericMethodPointersCount'],
                                                       code['invokerPointersCount'],source=str(gate.gameassembly),
                                                       offset=methods_base+index*16+4)
        pointer=pe.u64_at_va(int(code['genericMethodPointers'],16)+method*8)
        invoker_pointer=pe.u64_at_va(int(code['invokerPointers'],16)+invoker*8)
        require(pointer!=0 and invoker_pointer!=0,True,gate.gameassembly,methods_base+index*16)
        shared_rows.append({'tableIndex':index,'methodSpecIndex':spec_index,
                            'indices':[method,invoker,adjustor],'indicesRawHex':triple_raw.hex().upper(),
                            'methodPointerVa':pointer,'invokerPointerVa':invoker_pointer})
    producer_names=[]
    for rva,prefix,name in object_pins['producerNames']:
        expected=name.encode('ascii')
        instruction=pe.bytes_at_va(pe.image_base+rva,7)
        require(instruction[:3],bytes.fromhex(prefix),gate.gameassembly,rva)
        pointer=pe.image_base+rva+7+struct.unpack_from('<i',instruction,3)[0]
        require(pe.bytes_at_va(pointer,len(expected)+1),expected+b'\0',gate.gameassembly,pointer)
        producer_names.append({'instructionRva':rva,'stringVa':pointer,'ascii':expected.decode('ascii')})
    require_code_bytes(pe,*object_pins['producerStore'],gate.gameassembly)
    # Independently connect the registration producer to the cache seeding loop.
    # These are reviewed instruction boundaries inside the pinned consumers.
    seed_pins=pins['selectedInstantiationCacheSeed']
    producer_rva,producer_prefix=seed_pins['registrationProducer']
    producer=pe.bytes_at_va(pe.image_base+producer_rva,7)
    require(producer[:3],bytes.fromhex(producer_prefix),gate.gameassembly,producer_rva)
    require(pe.image_base+producer_rva+7+struct.unpack_from('<i',producer,3)[0],registration,gate.gameassembly,producer_rva)
    require_code_bytes(pe,*seed_pins['registrationStore'],gate.gameassembly)
    seed_load=seed_pins['seedGlobalLoadRva']
    seed_global=rip_qword_load_target(pe.bytes_at_va(pe.image_base+seed_load,7),pe.image_base+seed_load,source=str(gate.gameassembly))
    require(seed_global,pe.image_base+seed_pins['registrationGlobalRva'],gate.gameassembly,seed_load)
    cache_storage=[]
    for rva in seed_pins['storageReferences']:
        target=rip_qword_load_target(pe.bytes_at_va(pe.image_base+rva,7),pe.image_base+rva,source=str(gate.gameassembly))
        require(target,pe.image_base+seed_pins['storageRva'],gate.gameassembly,rva)
        cache_storage.append({'instructionRva':rva,'storageGlobalVa':target})
    return_evidence=serializer_return_consumers(pe,source=str(gate.gameassembly))
    return_evidence['methodIdentities']=module_methods(pe,md,modules,image_owners,
        [tuple(row) for row in pins['serializerMethodIdentities']],
        source=str(gate.gameassembly))
    construction_evidence=reader_construction(pe,md,modules,image_owners,source=str(gate.gameassembly))
    cursor_evidence=reader_cursor_consumers(pe,source=str(gate.gameassembly))
    wrapper_evidence=wrapper_consumer(pe,md,modules,image_owners,reg,table,
                                      source=str(gate.gameassembly))
    nested_context=nested_reader_context(pe,md,modules,image_owners,reg,table,
                                         source=str(gate.gameassembly),metadata_source=str(gate.metadata))
    list_candidate=list_formatter_candidate(pe,md,modules,image_owners,reg,code,table,spec_records,methods_raw,
                                            source=str(gate.gameassembly))
    skilldata_reader_order=skilldata_static_reader_order(
        pe,md,modules,image_owners,table,reg,specs_raw,corpus,skill_sample_raw,
        wrapper_evidence,source=str(gate.gameassembly))
    branch_sample_rows = []
    for selection, path in zip(terminal_branch_selections,
                               terminal_branch_sample_paths):
        raw = path.read_bytes()
        source_name = str(path.relative_to(ROOT))
        sample = skilldata_terminal_branch_sample_witness(
            corpus, selection, raw, source=source_name)
        nested_replay = skilldata_positive_branch_reader_replay(
            sample, raw, source=source_name)
        native_alignment = skilldata_nested_branch_static_alignment(
            nested_replay,
            skilldata_reader_order['nestedTerminalReaders'],
            skilldata_reader_order['representativeTerminalTailLayout']['gameplayTagListWrapper'],
            list_formatter=list_candidate,
            source=source_name)
        sample['nestedReaderReplay'] = nested_replay
        sample['nativeNestedReaderAlignment'] = native_alignment
        branch_sample_rows.append(sample)
    skilldata_reader_order['representativeTerminalBranchSamples'] = branch_sample_rows
    skilldata_reader_order['terminalListBranchSampleCoverage'] = [
        {
            'fieldName': selection['fieldName'],
            'memberIndex': selection['memberIndex'],
            'count': selection['count'],
            'logicalFileIdentity': selection['row']['virtualPath'],
            'logicalSha256': selection['row']['logicalSha256'],
            'hardLimit': selection['row']['hardLimit'],
            'candidateRange': selection['row']['framing']['candidates'][0].get('candidateRange'),
        }
        for selection in terminal_branch_selections
    ]
    list_dispatch=list_element_dispatch(pe,source=str(gate.gameassembly))
    list_shared=list_element_shared_context(pe,table,reg,code,spec_records,methods_raw,source=str(gate.gameassembly))
    list_null_probe=list_element_null_probe(pe,source=str(gate.gameassembly))
    list_value_flow=list_element_value_flow(pe,source=str(gate.gameassembly))
    element_provider=element_provider_state_flow(pe,source=str(gate.gameassembly))
    buff_routes=buff_union_routes(pe,md,reg,modules,image_owners,source=str(gate.gameassembly))
    buff_forwarding=buff_ifelse_forwarding(pe,md,reg,table,source=str(gate.gameassembly))
    buff_order=buff_ifelse_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly))
    buff_c9_prefix_evidence = skilldata_action_union_c9_prefix_reader_evidence(
        buff_order, buff_routes, gameassembly_image_base=pe.image_base,
        source=str(gate.gameassembly))
    buff_sequence=buff_sequence_read_order(pe,md,modules,image_owners,source=str(gate.gameassembly))
    buff_tag76=buff_tag76_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly))
    buff_ec=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_ec_native.json')
    buff_50=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_50_native.json')
    buff_11f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_11f_native.json')
    buff_b4=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_b4_native.json')
    buff_56=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_56_native.json')
    buff_92=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_92_native.json')
    buff_57=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_57_native.json')
    buff_9a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_9a_native.json')
    buff_a2=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_a2_native.json')
    buff_65=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_65_native.json')
    buff_169=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_169_native.json')
    buff_157=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_157_native.json')
    buff_6e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_6e_native.json')
    buff_fe=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_fe_native.json')
    buff_96=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_96_native.json')
    buff_fd=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_fd_native.json')
    buff_7c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_7c_native.json')
    buff_b6=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_b6_native.json')
    buff_80=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_80_native.json')
    buff_16e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_16e_native.json')
    buff_119=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_119_native.json')
    buff_0a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_0a_native.json')
    buff_7a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_7a_native.json')
    buff_88=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_88_native.json')
    buff_48=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_48_native.json')
    buff_5a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_5a_native.json')
    buff_7e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_7e_native.json')
    buff_35=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_35_native.json')
    buff_ea=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_ea_native.json')
    buff_61=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_61_native.json')
    buff_3f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_3f_native.json')
    buff_14d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_14d_native.json')
    buff_73=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_73_native.json')
    buff_5d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_5d_native.json')
    buff_42=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_42_native.json')
    buff_27=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_27_native.json')
    buff_95=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_95_native.json')
    buff_74=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_74_native.json')
    buff_16d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_16d_native.json')
    buff_160=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_160_native.json')
    buff_89=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_89_native.json')
    buff_171=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_171_native.json')
    buff_132=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_132_native.json')
    buff_d4=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_d4_native.json')
    buff_60=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_60_native.json')
    buff_126=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_126_native.json')
    buff_1c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_1c_native.json')
    buff_06=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_06_native.json')
    buff_142=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_142_native.json')
    buff_03=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_03_native.json')
    buff_51=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_51_native.json')
    buff_5e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_5e_native.json')
    buff_13b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_13b_native.json')
    buff_84=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_84_native.json')
    buff_174=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_174_native.json')
    buff_41=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_41_native.json')
    buff_a9=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_a9_native.json')
    buff_62=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_62_native.json')
    buff_13c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_13c_native.json')
    buff_90=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_90_native.json')
    buff_bb=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_bb_native.json')
    buff_0b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_0b_native.json')
    buff_0c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_0c_native.json')
    buff_26=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_26_native.json')
    buff_10c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_10c_native.json')
    buff_2b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_2b_native.json')
    buff_115=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_115_native.json')
    buff_151=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_151_native.json')
    buff_13f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_13f_native.json')
    buff_140=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_140_native.json')
    buff_98=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_98_native.json')
    buff_176=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_176_native.json')
    buff_93=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_93_native.json')
    buff_175=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_175_native.json')
    buff_fc=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_fc_native.json')
    buff_83=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_83_native.json')
    buff_13a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_13a_native.json')
    buff_86=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_86_native.json')
    buff_63=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_63_native.json')
    buff_6b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_6b_native.json')
    buff_77=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_77_native.json')
    buff_188=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_188_native.json')
    buff_40=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_40_native.json')
    buff_187=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_187_native.json')
    buff_139=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_139_native.json')
    buff_18a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_18a_native.json')
    buff_135=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_135_native.json')
    buff_122=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_122_native.json')
    buff_5c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_5c_native.json')
    buff_183=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_183_native.json')
    buff_2f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_2f_native.json')
    buff_15c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_15c_native.json')
    buff_16f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_16f_native.json')
    buff_05=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_05_native.json')
    buff_3a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_3a_native.json')
    buff_4c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_4c_native.json')
    buff_150=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_150_native.json')
    buff_a7=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_a7_native.json')
    buff_19e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_19e_native.json')
    buff_08=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_08_native.json')
    buff_120=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_120_native.json')
    buff_9f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_9f_native.json')
    buff_1b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_1b_native.json')
    buff_87=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_87_native.json')
    buff_52=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_52_native.json')
    buff_8e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_8e_native.json')
    finder_0a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'finder_0a_native.json')
    finder_15=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'finder_15_native.json')
    finder_0e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'finder_0e_native.json')
    buff_125=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_125_native.json')
    buff_124=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_124_native.json')
    buff_14f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_14f_native.json')
    buff_71=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_71_native.json')
    buff_70=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_70_native.json')
    finder_10=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'finder_10_native.json')
    finder_00=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'finder_00_native.json')
    finder_01=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'finder_01_native.json')
    postprocessor_01=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'postprocessor_01_native.json')
    postprocessor_08=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'postprocessor_08_native.json')
    validator_02=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'validator_02_native.json')
    validator_01=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'validator_01_native.json')
    buff_root_prefix=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_root_prefix_native.json')
    buff_root_fifth=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_root_fifth_native.json')
    buff_root_sixth=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_root_sixth_native.json')
    buff_159=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_159_native.json')
    buff_16=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_16_native.json')
    buff_178=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_178_native.json')
    buff_c1=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_c1_native.json')
    buff_101=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_101_native.json')
    buff_c7=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_c7_native.json')
    buff_19b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_19b_native.json')
    buff_128=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_128_native.json')
    buff_164=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_164_native.json')
    buff_cf=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_cf_native.json')
    buff_12b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_12b_native.json')
    buff_calc1=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_calc1_native.json')
    buff_calc5=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_calc5_native.json')
    buff_damage_lists=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_damage_lists_native.json')
    buff_2c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_2c_native.json')
    buff_127=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_127_native.json')
    buff_ab=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_ab_native.json')
    buff_f6=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_f6_native.json')
    buff_17c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_17c_native.json')
    buff_186=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_186_native.json')
    buff_b9=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_b9_native.json')
    buff_f4=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_f4_native.json')
    buff_133=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_133_native.json')
    buff_14a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_14a_native.json')
    buff_15d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_15d_native.json')
    buff_37=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_37_native.json')
    buff_12a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_12a_native.json')
    buff_144=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_144_native.json')
    buff_15b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_15b_native.json')
    buff_07=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_07_native.json')
    buff_18b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_18b_native.json')
    buff_19c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_19c_native.json')
    buff_8a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_8a_native.json')
    buff_14b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_14b_native.json')
    buff_166=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_166_native.json')
    buff_16c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_16c_native.json')
    buff_85=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_85_native.json')
    buff_94=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_94_native.json')
    buff_179=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_179_native.json')
    buff_158=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_158_native.json')
    buff_15a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_15a_native.json')
    buff_192=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_192_native.json')
    buff_bc=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_bc_native.json')
    buff_14e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_14e_native.json')
    buff_e0=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_e0_native.json')
    buff_0d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_0d_native.json')
    buff_172=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_172_native.json')
    buff_28=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_28_native.json')
    buff_102=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_102_native.json')
    buff_18e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_18e_native.json')
    buff_ce=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_ce_native.json')
    buff_17=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_17_native.json')
    buff_ad=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_ad_native.json')
    buff_d5=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_d5_native.json')
    buff_d6=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_d6_native.json')
    buff_198=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_198_native.json')
    buff_197=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_197_native.json')
    buff_91=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_91_native.json')
    buff_184=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_184_native.json')
    buff_df=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_df_native.json')
    buff_1f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_1f_native.json')
    buff_b7=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_b7_native.json')
    buff_f0=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_f0_native.json')
    buff_55=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_55_native.json')
    buff_36=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_36_native.json')
    buff_20=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_20_native.json')
    buff_a8=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_a8_native.json')
    buff_23=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_23_native.json')
    buff_16a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_16a_native.json')
    buff_6f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_6f_native.json')
    buff_161=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_161_native.json')
    buff_c0=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_c0_native.json')
    buff_11c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_11c_native.json')
    buff_8c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_8c_native.json')
    buff_4e=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_4e_native.json')
    buff_16b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_16b_native.json')
    buff_24=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_24_native.json')
    buff_6a=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_6a_native.json')
    buff_bd=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_bd_native.json')
    buff_de=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_de_native.json')
    buff_145=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_145_native.json')
    buff_c4=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_c4_native.json')
    buff_c5=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_c5_native.json')
    buff_9b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_9b_native.json')
    buff_10f=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_10f_native.json')
    buff_44=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_44_native.json')
    buff_69=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_69_native.json')
    buff_163=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_163_native.json')
    buff_136=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_136_native.json')
    buff_6d=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_6d_native.json')
    buff_7b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_7b_native.json')
    buff_02=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_02_native.json')
    buff_58=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_58_native.json')
    buff_81=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_81_native.json')
    buff_68=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_68_native.json')
    buff_b2=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_b2_native.json')
    buff_78=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_78_native.json')
    buff_3c=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_3c_native.json')
    buff_5b=buff_action_read_order(pe,md,reg,table,modules,image_owners,source=str(gate.gameassembly),
        contract_path=CONTRACTS_DIR / 'buff_5b_native.json')
    buff_action_readers = skilldata_action_readers_from_locals(
        locals(), source=str(gate.gameassembly))
    verified_action_tags = set(buff_action_readers)
    buff_action_prefixes = {IF_ELSE_TAG: buff_c9_prefix_evidence}
    verified_action_prefix_tags = set(buff_action_prefixes)
    for reader in buff_action_readers.values():
        contract_path = Path(reader['contractPath']).resolve()
        source_hashes[str(contract_path)] = sha(contract_path)

    actiongroup_branch_census_files = []
    actiongroup_branch_class_counts = {}
    actiongroup_branch_status_counts = {}
    actiongroup_completed_tag_counts = {}
    actiongroup_first_unverified_tag_counts = {}
    actiongroup_prefix_stop_tag_counts = {}
    actiongroup_reader_evidence_by_tag = {}
    actiongroup_opaque_bytes_after_cursor = 0
    actiongroup_c9_candidate_status_counts = {}
    actiongroup_c9_candidate_file_count = 0
    actiongroup_c9_candidate_sequence_range_count = 0
    for row, path in zip(actiongroup_branch_census_rows,
                         actiongroup_branch_census_sample_paths):
        logical_path = row['virtualPath']
        raw = path.read_bytes()
        source_name = str(path.relative_to(ROOT))
        witness = skilldata_actiongroup_branch_sample_witness(
            corpus, logical_path, raw, source=source_name,
            verified_action_tags=verified_action_tags,
            verified_action_prefix_tags=verified_action_prefix_tags)
        alignment = skilldata_actiongroup_branch_static_alignment(
            witness, skilldata_reader_order, buff_ad, buff_b4, buff_sequence,
            buff_d5, buff_d6, buff_routes, source=source_name,
            buff_action_readers=buff_action_readers,
            buff_action_prefixes=buff_action_prefixes,
            gameassembly_image_base=pe.image_base)
        c9_candidate = None
        if witness['status'] == 'stopped-after-verified-action-prefix':
            c9_candidate = skilldata_actiongroup_c9_nested_sequence_candidate_replay(
                witness, raw, buff_c9_prefix_evidence, buff_sequence,
                buff_action_readers, buff_routes, source=source_name,
                gameassembly_image_base=pe.image_base)
            actiongroup_c9_candidate_file_count += 1
            actiongroup_c9_candidate_status_counts[c9_candidate['status']] = (
                actiongroup_c9_candidate_status_counts.get(c9_candidate['status'], 0) + 1)
            actiongroup_c9_candidate_sequence_range_count += len(
                c9_candidate['candidateSequenceRanges'])
        actiongroup_branch_class_counts[witness['boundaryClass']] = (
            actiongroup_branch_class_counts.get(witness['boundaryClass'], 0) + 1)
        actiongroup_branch_status_counts[witness['status']] = (
            actiongroup_branch_status_counts.get(witness['status'], 0) + 1)
        actiongroup_opaque_bytes_after_cursor += sum(
            byte_range['end'] - byte_range['start']
            for byte_range in witness.get('opaqueByteRanges', []))
        for union_range in alignment['completedActionUnionRanges']:
            tag_label = f"0x{union_range['tag']:X}"
            actiongroup_completed_tag_counts[tag_label] = (
                actiongroup_completed_tag_counts.get(tag_label, 0) + 1)
        first_unconsumed = witness.get('firstUnconsumedActionUnionByte')
        if isinstance(first_unconsumed, dict):
            tag_label = f"0x{first_unconsumed['tag']:X}"
            actiongroup_first_unverified_tag_counts[tag_label] = (
                actiongroup_first_unverified_tag_counts.get(tag_label, 0) + 1)
        prefix_stop = witness.get('actionUnionPrefixStop')
        if isinstance(prefix_stop, dict):
            tag_label = f"0x{prefix_stop['tag']:X}"
            actiongroup_prefix_stop_tag_counts[tag_label] = (
                actiongroup_prefix_stop_tag_counts.get(tag_label, 0) + 1)
        for evidence in alignment['abilityActionUnionReaderEvidence']:
            actiongroup_reader_evidence_by_tag.setdefault(evidence['tag'], evidence)
        actiongroup_branch_census_files.append({
            'inputSetSha256': witness['inputSetSha256'],
            'logicalFileIdentity': witness['logicalFileIdentity'],
            'logicalSha256': witness['logicalSha256'],
            'hardLimit': witness['hardLimit'],
            'parserCursor': witness['parserCursor'],
            'status': witness['status'],
            'boundaryClass': witness['boundaryClass'],
            'consumedByteRanges': witness['consumedByteRanges'],
            'completedActionUnionRanges': alignment['completedActionUnionRanges'],
            'actionUnionPrefixStop': witness['actionUnionPrefixStop'],
            'firstUnconsumedActionUnionByte': witness['firstUnconsumedActionUnionByte'],
            'opaqueByteRanges': witness['opaqueByteRanges'],
            'wholeSkillDataClassification': witness['wholeSkillDataClassification'],
            'wholeSkillDataExactClosedRecords': witness['wholeSkillDataExactClosedRecords'],
            'conditionalReaderTags': alignment['verifiedActionUnionReaderTags'],
            'conditionalPrefixReaderTags': alignment['verifiedActionUnionPrefixTags'],
            'conditionalC9NestedSequenceCandidate': c9_candidate,
        })

    actiongroup_branch_census = {
        'inputSetSha256': corpus['inputSetSha256'],
        'sampleSelection': 'current SkillData corpus rows whose first common-prefix record list count is positive',
        'selectedFiles': len(actiongroup_branch_census_rows),
        'hashMatchedCurrentVfsFiles': len(actiongroup_branch_census_files),
        'boundaryClassCounts': actiongroup_branch_class_counts,
        'parserStatusCounts': actiongroup_branch_status_counts,
        'conditionalPassiveEventActionsListEnds': actiongroup_branch_status_counts.get(
            'passive-list-consumed-to-conditional-static-end', 0),
        'stoppedAtUnverifiedUnion': actiongroup_branch_status_counts.get(
            'stopped-before-first-nonnull-action-union', 0),
        'unsupported': actiongroup_branch_status_counts.get('unsupported-structural-prefix', 0),
        'ambiguousWholeSkillDataFiles': len(actiongroup_branch_census_files),
        'exactClosedActionGroupDataRecords': 0,
        'exactClosedWholeSkillDataRecords': 0,
        'opaqueBytesAfterConditionalCursor': actiongroup_opaque_bytes_after_cursor,
        'completedActionUnionTagCounts': dict(sorted(actiongroup_completed_tag_counts.items())),
        'firstUnverifiedActionUnionTagCounts': dict(sorted(actiongroup_first_unverified_tag_counts.items())),
        'stoppedAfterActionUnionPrefixTagCounts': dict(
            sorted(actiongroup_prefix_stop_tag_counts.items())),
        'candidateOnlyC9Files': actiongroup_c9_candidate_file_count,
        'candidateOnlyC9SequenceStatusCounts': dict(
            sorted(actiongroup_c9_candidate_status_counts.items())),
        'candidateOnlyC9SequenceRanges': actiongroup_c9_candidate_sequence_range_count,
        'exactClosedC9UnionRecords': 0,
        'exactClosedSequenceRecords': 0,
        'verifiedActionReaderContractsAvailable': len(buff_action_readers),
        'verifiedActionReaderPrefixEvidenceAvailable': [buff_c9_prefix_evidence],
        'verifiedActionReaderEvidenceUsed': [
            actiongroup_reader_evidence_by_tag[tag]
            for tag in sorted(actiongroup_reader_evidence_by_tag)],
        'files': actiongroup_branch_census_files,
        'boundary': ('This bounded subcorpus follows only the first ActionGroupData passiveEventActions list. '
                     'A list-end count means its child maps and sequences align to the selected static readers; '
                     'the following timelineActions member remains a non-advancing peek. Where a current C9 '
                     'header-eight normal path is selected, only its tag/member-header/14-byte scalar prefix '
                     'is consumed, stopping before its first generic SequenceActionData call. Unknown other '
                     'tags remain opaque at their first byte. Every enclosing ActionGroupData and whole SkillData '
                     'file remains ambiguous; no exact closed parent record is counted.'),
    }
    actiongroup_branch_sample_rows = []
    for logical_path, path in zip(actiongroup_branch_sample_identities,
                                  actiongroup_branch_sample_paths):
        raw = path.read_bytes()
        source_name = str(path.relative_to(ROOT))
        witness = skilldata_actiongroup_branch_sample_witness(
            corpus, logical_path, raw, source=source_name,
            verified_action_tags=verified_action_tags,
            verified_action_prefix_tags=verified_action_prefix_tags)
        witness['nativeReaderAlignment'] = skilldata_actiongroup_branch_static_alignment(
            witness, skilldata_reader_order, buff_ad, buff_b4, buff_sequence,
            buff_d5, buff_d6, buff_routes, source=source_name,
            buff_action_readers=buff_action_readers,
            buff_action_prefixes=buff_action_prefixes,
            gameassembly_image_base=pe.image_base)
        witness['conditionalC9NestedSequenceCandidate'] = (
            skilldata_actiongroup_c9_nested_sequence_candidate_replay(
                witness, raw, buff_c9_prefix_evidence, buff_sequence,
                buff_action_readers, buff_routes, source=source_name,
                gameassembly_image_base=pe.image_base)
            if witness['status'] == 'stopped-after-verified-action-prefix' else None)
        actiongroup_branch_sample_rows.append(witness)
    skilldata_reader_order['representativeActionGroupBranchSamples'] = actiongroup_branch_sample_rows
    skilldata_reader_order['actionGroupBranchSampleCensus'] = actiongroup_branch_census
    skilldata_reader_order['actionGroupBranchSampleBoundary'] = (
        'The current positive-list subcorpus is replayed through every hash-pinned direct action reader whose '
        'registered wrapper route and root member header match. For C9, only the exact header-eight scalar '
        'prefix through the first generic SequenceActionData callsite is consumed. A separate candidate-only '
        'replay records the three nested sequence call ranges against the current sequence and child-action '
        'reader windows; C9 provider/cache selection remains unobserved, so those ranges never advance the '
        'authoritative parser cursor. timelineActions is only peeked after a conditional list end; the parent '
        'ActionGroupData and whole SkillData records remain ambiguous.'
    )
    list_candidate['bodyWindows']=[]
    for start,end,digest in pins['listFormatterBodyWindows']:
        require(hashlib.sha256(pe.bytes_at_va(pe.image_base+start,end-start)).hexdigest().upper(),digest,gate.gameassembly,start)
        list_candidate['bodyWindows'].append({'rva':start,'byteLength':end-start,'sha256':digest})
    resource_evidence=skill_resource_context(pe,md,modules,image_owners,table,reg,code,
        spec_records,specs_raw,methods_raw,source=str(gate.gameassembly))
    carrier_evidence=resource_carrier_consumers(pe,source=str(gate.gameassembly))
    stream_identity=stream_source_identity(pe,md,modules,image_owners,reg,code,spec_records,methods_raw,source=str(gate.gameassembly))
    stream_consumer=stream_carrier_consumer(pe,source=str(gate.gameassembly))
    vfs_identity=vfs_stream_identity(pe,md,modules,image_owners,reg,source=str(gate.gameassembly))
    vfs_consumer=vfs_stream_consumer(pe,source=str(gate.gameassembly))
    file_open=file_stream_open(pe,md,modules,image_owners,reg,source=str(gate.gameassembly))
    descriptor_path=vfs_descriptor_path(pe,md,modules,image_owners,source=str(gate.gameassembly))
    descriptor_producer=vfs_descriptor_producer(pe,md,modules,image_owners,reg,table,source=str(gate.gameassembly))
    bytebuf_consumer=vfs_bytebuf_consumer(pe,md,modules,image_owners,reg,source=str(gate.gameassembly))
    block_cursor=vfs_block_cursor(pe,md,modules,image_owners,source=str(gate.gameassembly))
    block_transform=vfs_block_transform(pe,md,modules,image_owners,source=str(gate.gameassembly))
    block_file_source=vfs_block_file_source(pe,md,modules,image_owners,source=str(gate.gameassembly))
    file_read=native_file_read(pe,md,modules,image_owners,source=str(gate.gameassembly))
    path_carrier=vfs_path_carrier(pe,md,modules,image_owners,source=str(gate.gameassembly))
    path_format=vfs_path_format_context(pe,md,modules,image_owners,reg,table,source=str(gate.gameassembly))
    path_literals=vfs_path_literals(pe,md,source=str(gate.gameassembly),metadata_source=str(gate.metadata))
    format_item=vfs_format_item(pe,source=str(gate.gameassembly))
    string_carrier=vfs_string_carrier(pe,source=str(gate.gameassembly))
    root_resolver=vfs_root_resolver(pe,source=str(gate.gameassembly))
    prefix_query=resolver_prefix_query(pe,source=str(gate.gameassembly))
    key_comparison=resolver_key_comparison(pe,source=str(gate.gameassembly))
    unity_path=gate.gameassembly.with_name('UnityPlayer.dll')
    unity_pe=mapper.PeImage(unity_path)
    require(hashlib.sha256(unity_pe.buf).hexdigest().upper(),UNITY_SHA,unity_path)
    unity_forwarder=unity_registration_forwarder(unity_pe,source=str(unity_path))
    unity_pair=unity_registration_pair(unity_pe,source=str(unity_path))
    unity_path_evidence=unity_path_return(unity_pe,source=str(unity_path))
    unity_exports=unity_conversion_exports(pe,unity_pe,source=str(gate.gameassembly),unity_source=str(unity_path))
    unity_lookup=unity_module_lookup(unity_pe,source=str(unity_path))
    unity_input=unity_loader_input(unity_pe,source=str(unity_path))
    unity_conversion=unity_loader_conversion(unity_pe,source=str(unity_path))
    for start,end,expected in pins['unityPlayerWindows']:
        require(hashlib.sha256(unity_pe.bytes_at_va(unity_pe.image_base+start,end-start)).hexdigest().upper(),expected,unity_path,start)
    require(sha(unity_path),UNITY_SHA,unity_path)
    native_gate()
    require(sha(corpus_path), corpus_sha, corpus_path)
    verify_current_report_inputs(corpus)
    require(sha(buff_path),buff_sha,buff_path)
    verify_family_report_inputs(buff_corpus,expected_format='animestudio-buffdata-current-vfs-corpus',label='BuffData')
    for path, expected in source_hashes.items():
        require(sha(path), expected, path)
    return {
        'schemaVersion': 1, 'status': 'failed' if failures else 'structural-only',
        'inputSetSha256': corpus['inputSetSha256'],
        'buffCorpusReference':{'path':str(buff_path),'sha256':buff_sha,'summary':buff_corpus['summary'],
                               'inputSetSha256':buff_corpus['inputSetSha256']},
        'corpusReference': {'path': str(corpus_path), 'sha256': corpus_sha,
                            'boundary': 'Authenticated corpus reference; this native audit does not restream VFS bytes.'},
        'nativeInputs': {'gameassembly': str(gate.gameassembly), 'gameassemblySha256': GA_SHA,
                         'metadata': str(gate.metadata), 'metadataSha256': MD_SHA,
                         'unityplayer':str(unity_path),'unityplayerSha256':UNITY_SHA},
        'sourceHashes': source_hashes, 'registration': reg,
        'methodSpecSweep':{'success':len(spec_records),'failed':0,'unsupported':0,
                           'sourceVa':specs_base,'byteLength':len(specs_raw),
                           'sha256':hashlib.sha256(specs_raw).hexdigest().upper(),
                           'boundary':'All referenced 12-byte MethodSpecs have bounded definition and class/method instantiation indices. This is not runtime inflation or whole-PE EOF.'},
        'selectedSerializerReturnConsumers':return_evidence,
        'selectedSkillResourceContext':resource_evidence,
        'selectedResourceCarrierConsumers':carrier_evidence,
        'selectedStreamSourceIdentity':stream_identity,
        'selectedStreamCarrierConsumer':stream_consumer,
        'selectedVfsStreamIdentity':vfs_identity,
        'selectedVfsStreamConsumer':vfs_consumer,
        'selectedFileStreamOpen':file_open,
        'selectedVfsDescriptorPath':descriptor_path,
        'selectedVfsDescriptorProducer':descriptor_producer,
        'selectedVfsByteBufConsumer':bytebuf_consumer,
        'selectedVfsBlockCursor':block_cursor,
        'selectedVfsBlockTransform':block_transform,
        'selectedVfsBlockFileSource':block_file_source,
        'selectedNativeFileRead':file_read,
        'selectedVfsPathCarrier':path_carrier,
        'selectedVfsPathFormatContext':path_format,
        'selectedVfsPathLiterals':path_literals,
        'selectedVfsFormatItem':format_item,
        'selectedVfsStringCarrier':string_carrier,
        'selectedVfsRootResolver':root_resolver,
        'selectedResolverPrefixQuery':prefix_query,
        'selectedResolverKeyComparison':key_comparison,
        'selectedUnityRegistrationForwarder':unity_forwarder,
        'selectedUnityRegistrationPair':unity_pair,
        'selectedUnityPathReturn':unity_path_evidence,
        'selectedUnityConversionExports':unity_exports,
        'selectedUnityModuleLookup':unity_lookup,
        'selectedUnityLoaderInput':unity_input,
        'selectedUnityLoaderConversion':unity_conversion,
        'selectedReaderConstruction':construction_evidence,
        'selectedReaderCursorConsumers':cursor_evidence,
        'selectedWrapperConsumer':wrapper_evidence,
        'selectedNestedReaderContext':nested_context,
        'selectedSkillDataReaderOrder':skilldata_reader_order,
        'selectedListFormatterCandidate':list_candidate,
        'selectedListElementDispatch':list_dispatch,
        'selectedListElementSharedContext':list_shared,
        'selectedListElementNullProbe':list_null_probe,
        'selectedListElementValueFlow':list_value_flow,
        'selectedAdapterConversionContext':adapter_conversion,
        'selectedElementProviderStateFlow':element_provider,
        'selectedBuffUnionRoutes':buff_routes,
        'selectedBuffIfElseForwarding':buff_forwarding,
        'selectedBuffIfElseReadOrder':buff_order,
        'selectedBuffSequenceReadOrder':buff_sequence,
        'selectedBuffTag76ReadOrder':buff_tag76,
        'selectedBuffEcReadOrder':buff_ec,
        'selectedBuff50ReadOrder':buff_50,
        'selectedBuff11fReadOrder':buff_11f,
        'selectedBuffB4ReadOrder':buff_b4,
        'selectedBuff56ReadOrder':buff_56,
        'selectedBuff92ReadOrder':buff_92,
        'selectedBuff57ReadOrder':buff_57,
        'selectedBuff5bReadOrder':buff_5b,
        'selectedBuff3cReadOrder':buff_3c,
        'selectedBuff78ReadOrder':buff_78,
        'selectedBuffB2ReadOrder':buff_b2,
        'selectedBuff68ReadOrder':buff_68,
        'selectedBuff81ReadOrder':buff_81,
        'selectedBuff58ReadOrder':buff_58,
        'selectedBuff02ReadOrder':buff_02,
        'selectedBuff9AReadOrder':buff_9a,
        'selectedBuffA2ReadOrder':buff_a2,
        'selectedBuff65ReadOrder':buff_65,
        'selectedBuff169ReadOrder':buff_169,
        'selectedBuff157ReadOrder':buff_157,
        'selectedBuff6EReadOrder':buff_6e,
        'selectedBuffFEReadOrder':buff_fe,
        'selectedBuff96ReadOrder':buff_96,
        'selectedBuffFDReadOrder':buff_fd,
        'selectedBuff7CReadOrder':buff_7c,
        'selectedBuffB6ReadOrder':buff_b6,
        'selectedBuff80ReadOrder':buff_80,
        'selectedBuff16EReadOrder':buff_16e,
        'selectedBuff7BReadOrder':buff_7b,
        'selectedBuff6DReadOrder':buff_6d,
        'selectedBuff136ReadOrder':buff_136,
        'selectedBuff163ReadOrder':buff_163,
        'selectedBuff69ReadOrder':buff_69,
        'selectedBuff44ReadOrder':buff_44,
        'selectedBuff10FReadOrder':buff_10f,
        'selectedBuff9BReadOrder':buff_9b,
        'selectedBuffC5ReadOrder':buff_c5,
        'selectedBuff119ReadOrder':buff_119,
        'selectedBuff0AReadOrder':buff_0a,
        'selectedBuff7AReadOrder':buff_7a,
        'selectedBuff88ReadOrder':buff_88,
        'selectedBuff48ReadOrder':buff_48,
        'selectedBuff5AReadOrder':buff_5a,
        'selectedBuffC4ReadOrder':buff_c4,
        'selectedBuff145ReadOrder':buff_145,
        'selectedBuffDEReadOrder':buff_de,
        'selectedBuffBDReadOrder':buff_bd,
        'selectedBuff6AReadOrder':buff_6a,
        'selectedBuff24ReadOrder':buff_24,
        'selectedBuff16BReadOrder':buff_16b,
        'selectedBuff7EReadOrder':buff_7e,
        'selectedBuff35ReadOrder':buff_35,
        'selectedBuffEAReadOrder':buff_ea,
        'selectedBuff61ReadOrder':buff_61,
        'selectedBuff3FReadOrder':buff_3f,
        'selectedBuff14DReadOrder':buff_14d,
        'selectedBuff73ReadOrder':buff_73,
        'selectedBuff5DReadOrder':buff_5d,
        'selectedBuff42ReadOrder':buff_42,
        'selectedBuff27ReadOrder':buff_27,
        'selectedBuff95ReadOrder':buff_95,
        'selectedBuff74ReadOrder':buff_74,
        'selectedBuff16DReadOrder':buff_16d,
        'selectedBuff160ReadOrder':buff_160,
        'selectedBuff89ReadOrder':buff_89,
        'selectedBuff171ReadOrder':buff_171,
        'selectedBuff132ReadOrder':buff_132,
        'selectedBuffD4ReadOrder':buff_d4,
        'selectedBuff60ReadOrder':buff_60,
        'selectedBuff126ReadOrder':buff_126,
        'selectedBuff1CReadOrder':buff_1c,
        'selectedBuff06ReadOrder':buff_06,
        'selectedBuff142ReadOrder':buff_142,
        'selectedBuff03ReadOrder':buff_03,
        'selectedBuff51ReadOrder':buff_51,
        'selectedBuff5EReadOrder':buff_5e,
        'selectedBuff13BReadOrder':buff_13b,
        'selectedBuff84ReadOrder':buff_84,
        'selectedBuff174ReadOrder':buff_174,
        'selectedBuff41ReadOrder':buff_41,
        'selectedBuffA9ReadOrder':buff_a9,
        'selectedBuff62ReadOrder':buff_62,
        'selectedBuff13CReadOrder':buff_13c,
        'selectedBuff90ReadOrder':buff_90,
        'selectedBuffBBReadOrder':buff_bb,
        'selectedBuff0BReadOrder':buff_0b,
        'selectedBuff0CReadOrder':buff_0c,
        'selectedBuff26ReadOrder':buff_26,
        'selectedBuff10CReadOrder':buff_10c,
        'selectedBuff2BReadOrder':buff_2b,
        'selectedBuff115ReadOrder':buff_115,
        'selectedBuff151ReadOrder':buff_151,
        'selectedBuff13FReadOrder':buff_13f,
        'selectedBuff140ReadOrder':buff_140,
        'selectedBuff98ReadOrder':buff_98,
        'selectedBuff176ReadOrder':buff_176,
        'selectedBuff93ReadOrder':buff_93,
        'selectedBuff175ReadOrder':buff_175,
        'selectedBuffFCReadOrder':buff_fc,
        'selectedBuff83ReadOrder':buff_83,
        'selectedBuff13AReadOrder':buff_13a,
        'selectedBuff86ReadOrder':buff_86,
        'selectedBuff63ReadOrder':buff_63,
        'selectedBuff6BReadOrder':buff_6b,
        'selectedBuff77ReadOrder':buff_77,
        'selectedBuff188ReadOrder':buff_188,
        'selectedBuff40ReadOrder':buff_40,
        'selectedBuff187ReadOrder':buff_187,
        'selectedBuff139ReadOrder':buff_139,
        'selectedBuff18AReadOrder':buff_18a,
        'selectedBuff135ReadOrder':buff_135,
        'selectedBuff122ReadOrder':buff_122,
        'selectedBuff5CReadOrder':buff_5c,
        'selectedBuff183ReadOrder':buff_183,
        'selectedBuff2FReadOrder':buff_2f,
        'selectedBuff15CReadOrder':buff_15c,
        'selectedBuff16FReadOrder':buff_16f,
        'selectedBuff05ReadOrder':buff_05,
        'selectedBuff3AReadOrder':buff_3a,
        'selectedBuff4CReadOrder':buff_4c,
        'selectedBuff150ReadOrder':buff_150,
        'selectedBuffA7ReadOrder':buff_a7,
        'selectedBuff19EReadOrder':buff_19e,
        'selectedBuff08ReadOrder':buff_08,
        'selectedBuff120ReadOrder':buff_120,
        'selectedBuff9FReadOrder':buff_9f,
        'selectedBuff1BReadOrder':buff_1b,
        'selectedBuff87ReadOrder':buff_87,
        'selectedBuff52ReadOrder':buff_52,
        'selectedBuff8EReadOrder':buff_8e,
        'selectedFinder0AReadOrder':finder_0a,
        'selectedFinder15ReadOrder':finder_15,
        'selectedFinder0EReadOrder':finder_0e,
        'selectedBuff125ReadOrder':buff_125,
        'selectedBuff124ReadOrder':buff_124,
        'selectedBuff14FReadOrder':buff_14f,
        'selectedBuff71ReadOrder':buff_71,
        'selectedBuff70ReadOrder':buff_70,
        'selectedFinder10ReadOrder':finder_10,
        'selectedFinder01ReadOrder':finder_01,
        'selectedFinder00ReadOrder':finder_00,
        'selectedValidator01ReadOrder':validator_01,
        'selectedValidator02ReadOrder':validator_02,
        'selectedPostprocessor08ReadOrder':postprocessor_08,
        'selectedPostprocessor01ReadOrder':postprocessor_01,
        'selectedBuffRootPrefixReadOrder':buff_root_prefix,
        'selectedBuffRootFifthReadOrder':buff_root_fifth,
        'selectedBuffRootSixthReadOrder':buff_root_sixth,
        'selectedBuff159ReadOrder':buff_159,
        'selectedBuff16ReadOrder':buff_16,
        'selectedBuff178ReadOrder':buff_178,
        'selectedBuffC1ReadOrder':buff_c1,
        'selectedBuff101ReadOrder':buff_101,
        'selectedBuffC7ReadOrder':buff_c7,
        'selectedBuff19BReadOrder':buff_19b,
        'selectedBuff128ReadOrder':buff_128,
        'selectedBuff164ReadOrder':buff_164,
        'selectedBuffCFReadOrder':buff_cf,
        'selectedBuff12BReadOrder':buff_12b,
        'selectedBuff2CReadOrder':buff_2c,
        'selectedBuffABReadOrder':buff_ab,
        'selectedBuffF6ReadOrder':buff_f6,
        'selectedBuff17CReadOrder':buff_17c,
        'selectedBuff186ReadOrder':buff_186,
        'selectedBuffB9ReadOrder':buff_b9,
        'selectedBuffF4ReadOrder':buff_f4,
        'selectedBuff133ReadOrder':buff_133,
        'selectedBuff14AReadOrder':buff_14a,
        'selectedBuff15DReadOrder':buff_15d,
        'selectedBuff37ReadOrder':buff_37,
        'selectedBuff12AReadOrder':buff_12a,
        'selectedBuff144ReadOrder':buff_144,
        'selectedBuff15BReadOrder':buff_15b,
        'selectedBuff07ReadOrder':buff_07,
        'selectedBuff18BReadOrder':buff_18b,
        'selectedBuff19CReadOrder':buff_19c,
        'selectedBuff8AReadOrder':buff_8a,
        'selectedBuff14BReadOrder':buff_14b,
        'selectedBuff166ReadOrder':buff_166,
        'selectedBuff16CReadOrder':buff_16c,
        'selectedBuff85ReadOrder':buff_85,
        'selectedBuff94ReadOrder':buff_94,
        'selectedBuff179ReadOrder':buff_179,
        'selectedBuff158ReadOrder':buff_158,
        'selectedBuff15AReadOrder':buff_15a,
        'selectedBuff192ReadOrder':buff_192,
        'selectedBuffBCReadOrder':buff_bc,
        'selectedBuff14EReadOrder':buff_14e,
        'selectedBuff0DReadOrder':buff_0d,
        'selectedBuffE0ReadOrder':buff_e0,
        'selectedBuff172ReadOrder':buff_172,
        'selectedBuff28ReadOrder':buff_28,
        'selectedBuff102ReadOrder':buff_102,
        'selectedBuff18eReadOrder':buff_18e,
        'selectedBuffCeReadOrder':buff_ce,
        'selectedBuff17ReadOrder':buff_17,
        'selectedBuffAdReadOrder':buff_ad,
        'selectedBuffD5ReadOrder':buff_d5,
        'selectedBuffD6ReadOrder':buff_d6,
        'selectedBuff198ReadOrder':buff_198,
        'selectedBuff197ReadOrder':buff_197,
        'selectedBuff91ReadOrder':buff_91,
        'selectedBuff184ReadOrder':buff_184,
        'selectedBuffDfReadOrder':buff_df,
        'selectedBuff1fReadOrder':buff_1f,
        'selectedBuffB7ReadOrder':buff_b7,
        'selectedBuffF0ReadOrder':buff_f0,
        'selectedBuff55ReadOrder':buff_55,
        'selectedBuff36ReadOrder':buff_36,
        'selectedBuff20ReadOrder':buff_20,
        'selectedBuffA8ReadOrder':buff_a8,
        'selectedBuff23ReadOrder':buff_23,
        'selectedBuff16AReadOrder':buff_16a,
        'selectedBuff6FReadOrder':buff_6f,
        'selectedBuff161ReadOrder':buff_161,
        'selectedBuffC0ReadOrder':buff_c0,
        'selectedBuff11CReadOrder':buff_11c,
        'selectedBuff8CReadOrder':buff_8c,
        'selectedBuff4EReadOrder':buff_4e,
        'selectedBuff127ReadOrder':buff_127,
        'selectedBuffDamageListsReadOrder':buff_damage_lists,
        'selectedBuffCalc5ReadOrder':buff_calc5,
        'selectedBuffCalc1ReadOrder':buff_calc1,
        'selectedNestedAdapterSlots':{'rows':nested_slots,'level':'exact static MethodSpec/VAR relation',
                                      'boundary':f'Relative slots {nested_slot_names} independently join DeserializeNotNull<T0,T1>, GetFormatter<T1> and CreateInstance<T1>. Every VAR reciprocally belongs to the adapter type; conditional concrete arguments come from the separately authenticated immediate registration. Method names do not establish serialization order, actual nested dispatch or source cursor.'},
        'selectedMethodCompanionConstruction': {'lookupRva':companion_pins['lookupRva'],'constructorRva':companion_pins['constructorRva'],
                                                 'classStoreRva':companion_pins['classStore'][0],
                                                 'methodPointerResolverCallRva':companion_pins['methodPointerResolverCallRva'],
                                                 'classFieldOffset':0x20,'pointerFieldOffsets':[0,8,16],
                                                 'level':'direct conditional native construction path',
                                                 'boundary':'On the reviewed cache-miss construction path, the original definition class and class-instantiation feed the generic-class carrier lookup/construction, then the class pointer is stored at MethodInfo+0x20. The pointer resolver receives the original definition and context pair separately, writes a stack result, and its code/adjustor/invoker pointers are copied to MethodInfo+0/+8/+0x10. Normalizing arguments for a shared code lookup therefore does not itself replace the already stored original class pointer. This is not a live MethodInfo receipt, proof of cache contents, actual target invocation, source extent or EOF.'},
        'rgctxDefinitionSweep': {'images':rgctx_inventory,
                                  'summary':{'success':sum(x['success'] for x in rgctx_inventory),'failed':0,'unsupported':0},
                                  'boundary':'Exact referenced 16-byte definitions for every matched module; numeric kinds, padding and payload pointers are preserved, not resolved runtime slots or a partition of the PE.'},
        'selectedAdapterClassSlot': {'typeDefinition':adapter_definition,'token':md.types[adapter_definition].token,
                                     'rangeStart':adapter_start,'rangeCount':adapter_count,'entries':adapter_entries,
                                     'selectedRelativeIndex':slot_pins['relativeIndex'],'selectedModuleEntryIndex':type_slot['moduleEntryIndex'],
                                     'consumerRva':slot_pins['consumerRva'],'runtimeSlotByteOffset':slot_pins['relativeIndex']*8,
                                     'typeIndex':slot_type_index,'typePointerVa':slot_type_pointer,
                                     'typeRawHex':slot_type_raw.hex().upper(),'parameterOwner':slot_owner,
                                     'conditionalContextArgument':{'pointerVa':slot_argument.type_pointer_va,'rawHex':slot_argument.raw_type_record_hex},
                                     'level':'exact static slot/VAR identity; direct conditional class-context connection',
                                     'boundary':f'The class initializer reads class+0x118 token and image+0x38 module, uses 12-byte token ranges and 16-byte definitions, emits eight-byte slots at class+0xC0, and supplies generic-carrier+8 context to substitution. Relative slot {slot_pins["relativeIndex"]} is module entry {type_slot["moduleEntryIndex"]}, kind 1, a reciprocal ordinal-1 VAR of the adapter type. The VAR branch uses the class instantiation, whose second argument at the immediate registration is the wrapper type. This does not certify initialized class contents, actual method companion, formatter cache selection, source length or EOF.'},
        'selectedSharedMethodCandidates': {'definition':shared_definition,'methodSpecIndices':shared_specs,
                                           'rows':shared_rows,'level':'exact static table relation; conditional index consumer',
                                           'boundary':'All matching MethodSpecs and generic-method table rows are preserved. The separately pinned index reader checks method/invoker indices, loads their pointer slots, and with adjustor -1 reuses the method pointer. Non-sentinel adjustors remain unsupported by this bounded decoder. This does not certify the runtime triple-map population, query success, target invocation, actual reader ABI, source length or final cursor.'},
        'selectedObjectComparison': {'key':object_key,'matchingRegisteredInstantiations':object_candidates,
                                     'switchEntryVa':switch_entry,'switchTargetRva':comparison_pins['switchTargetRva'],
                                     'level':'direct conditional native equality/hash projection',
                                     'boundary':'For object-tag records the reviewed comparator checks the tag and bit 29 of the word at +8, then returns equal; the reviewed hash branch depends on those same two values. Record addresses and other bytes do not participate in this branch. The complete registered-instance sweep enumerates every matching two-argument candidate without selecting one. Even a singleton does not prove cache execution, returned interned pointer, method lookup success, active formatter or file cursor.'},
        'selectedInstantiationCacheSeed': {'registrationGlobalVa':seed_global,
                                          'seedCallRva':seed_pins['seedCallRva'],'insertRva':seed_pins['insertRva'],
                                          'lookupRva':seed_pins['lookupRva'],'storageReferences':cache_storage,
                                          'level':'direct conditional native producer/consumer connection',
                                          'boundary':'The initializer stores the selected MetadataRegistration and calls the seed routine. Its normal loop reads count+0x10 and pointer-table+0x18, passes each eight-byte slot to insertion, and insertion dereferences that slot to a record pointer. Insertion and lookup access the identical cache storage global and compare argument counts plus native type comparisons. This establishes a static registration-to-cache seed path, not successful initialization, cold-path completion, actual cache contents, interned pointer selection or active formatter dispatch.'},
        'selectedObjectIdentity': {'metadata':object_identity,'producerNames':producer_names,
                                   'registeredTypePointerVa':object_pointer,'rawTypeHex':object_raw.hex().upper(),
                                   'objectPairInstantiation':object_pair.as_dict(),
                                   'level':'exact static identity; direct conditional producer/class-copy connection',
                                   'boundary':'The initializer supplies mscorlib.dll/System/Object to the lookup chain and stores its return in the sharing global. Name-cache construction uses metadata namespace/name and lookup compares both strings, not only hashes. The matched TypeDef reaches the class cache; the miss constructor copies the registered byval type record to class+0x20. This links the normal producer to System.Object record bytes and the static object/object candidate pair. Runtime image/name/class-cache population, initialization execution and interned pointer identity remain unobserved; no active Deserialize or file-cursor selection follows.'},
        'selectedSharingBranch': {'argumentTags':[0x12,0x12], 'normalizerRva':sharing_pins['normalizerRva'],
                                  'canonicalCarrierGlobalVa':sharing_global,'carrierTypeOffset':0x20,
                                  'level':'direct conditional native branch; producer identity recorded separately',
                                  'boundary':'On an original-context lookup miss, the reviewed method-pointer resolver transforms class and method argument vectors and retries the triple lookup. Each non-null class-tag argument directly becomes the same global carrier+0x20, preserving vector order/count before interning. The normal producer links to System.Object bytes, but initialization execution, interned vector identity, lookup-table population, cold paths and actual invocation are not established; this does not select the object/object Deserialize candidate. The normalizer code ends before its separately located eight-dword switch table.'},
        'selectedProviderStorage': {'references':storage_references,'cellRawHex':storage_raw.hex().upper(),
                                    'level':'direct conditional consumer connection',
                                    'boundary':'Registration and GetFormatter read the identical RIP cell, then class+0xB8 and static-carrier+0x18. Direct lookup traverses that storage and returns a matched node+0x18 through the local result slot. A miss can invoke lazy callbacks, retry lookup, or construct and register other values. Static storage identity does not establish live contents, comparer results, initialization/replacement history or selected adapter dispatch.'},
        'selectedImmediateAdapter': {'cells':adapter_cells, 'typeCarrier':adapter,
                                    'argumentTypeNames':['Beyond.Gameplay.Core.GameplayTagList','Beyond.MemoryPack.Beyond_Gameplay_Core_GameplayTagListForMemoryPack'],
                                    'classInstantiation':adapter_inst.as_dict(),
                                    'constructorMethodSpecVa':ctor_va,'constructorRawHex':ctor_raw.hex().upper(),
                                    'level':'exact static identity; direct conditional registration callsite',
                                    'boundary':'The type carrier and constructor share the ordered Core/ForMemoryPack instance, and the Core key uses the identical registered type pointer. The reviewed callsite passes the constructed-object stack slot and type-derived key to a registration function which forwards them to static-carrier+0x18 storage. This does not establish execution, allocation/constructor ABI completion, live cache selection, adapter Deserialize dispatch, source length or final cursor.'},
        'selectedFormatterTypeCarrier': {**formatter_carrier,'rgctxEntryVa':entry_va,
                                         'rgctxEntryRawHex':entry_raw.hex().upper(),
                                         'classInstantiationIndex':formatter_inst.index,
                                         'baseName':md.type_full_name(md.types[formatter_definition]),
                                         'boundary':'Exact static pointer/range/MVAR identity; the 32-byte carrier window is not a certified allocation extent and its last 16 bytes remain opaque. Native generic inflation iterates the class-inst arguments using the supplied context. This is the open formatter check type, not the active formatter object or proof that runtime inflation/caches executed.'},
        'selectedUsageCell': {'va': usage_va, 'rawHex': usage_raw.hex().upper(),
                              'methodSpecIndex': call_index, 'resolverSwitchEntryRva': resolver_entry,
                              'boundary': 'Direct static initialization mechanism: the guarded wrapper passes this cell address to the lazy resolver; tag 6 routes through MethodSpec/triple lookup and a non-null result is exchanged into the cell. The callsite reads the same cell. Initialization execution, cache history, active formatter and source cursor remain unobserved.'},
        'staticImageOwnership': {'typeCount': len(image_owners), 'images': image_rows,
                                 'selectedReadValueImage': image_owners[md.methods[spec_pins['openMethodParameterOwner']].declaring_type],
                                 'registrationGlobalRva': registration_pins['codeRegistrationGlobalRva'],
                                 'matchingRule': 'Native bytewise name matching continues after a match; duplicate names could overwrite a prior result. This gate requires unique module names before accepting a static join.',
                                 'boundary': 'Exact metadata type partition and unique module-name joins. Native normal-path directory stores and name comparisons are separately pinned; initialization execution, cold paths and live invocation remain unobserved.'},
        'consumerWindows': CONSUMER_WINDOWS, 'summary': summary,
        'selectedMethodSpec': selected_method_spec,
        'selectedCallMethodSpec': {'index': call_index, 'va': call_va, 'rawHex': call_raw.hex().upper(),
                                   'methodInstantiation': call_inst.as_dict()},
        'conditionalSubstitution': {
            'ordinal': ordinal, 'selectedRawArgument': argument.raw_type_record_hex,
            'level': 'exact static joins; conditional runtime application',
            'boundary': 'The open parameter belongs to the selected call definition and its ordinal indexes this registered argument. The native leaf applies that ordinal to its supplied live context. This report does not establish that the actual invocation supplies this context.'},
        'boundary': 'Pointer array -> 16-byte record -> argument pointer array -> raw 16-byte type records only. No live generic context, formatter, field order, source cursor or EOF claim.',
        'failures': failures, 'rows': rows,
    }


def main():
    try:
        report = audit()
    except (ContextError, OSError, ValueError) as error:
        def diagnostic_default(value):
            if isinstance(value, bytes):
                return {'byteLength': len(value), 'hex': value.hex().upper()}
            if isinstance(value, Path):
                return str(value)
            return repr(value)
        print(json.dumps(
            {'status': 'failed',
             'diagnostic': getattr(error, 'diagnostics',
                                   getattr(error, 'diagnostic', str(error)))},
            default=diagnostic_default), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return int(report['status'] == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
