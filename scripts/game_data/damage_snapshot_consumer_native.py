"""Re-prove the damage snapshot's named consumer claims on the selected client.

Claims carry no build-specific addresses. Unsupported current bodies become
pendingReview, and every failed input or claim gate supplies no consumer rows.
"""
from __future__ import annotations
if __name__ == '__main__' and not __package__:
    raise SystemExit('Run python -m scripts.game_data.damage_snapshot_consumer_native')
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.damage_snapshot_cache_flow import check_cache_return
from scripts.game_data.damage_snapshot_append_flow import check_simple_append
from scripts.game_data.damage_snapshot_append_helper import check_compiled_append_helper
from scripts.game_data.damage_snapshot_getter_flow import check_cache_getter
from scripts.game_data.damage_snapshot_clear_flow import check_cache_clear
from scripts.game_data.damage_snapshot_oncreate_flow import check_oncreate
from scripts.game_data.damage_snapshot_constructor_flow import check_cache_constructor
from scripts.game_data.damage_snapshot_slot_helper import check_constructor_slot_helper
from scripts.game_data.damage_snapshot_skip_flow import check_snapshot_skip
from scripts.game_data.damage_snapshot_counter_flow import check_snapshot_counter
from scripts.game_data.damage_snapshot_count_flow import check_snapshot_count
from scripts.game_data.damage_snapshot_unit_flow import check_snapshot_unit
from scripts.game_data.damage_snapshot_iteration_flow import check_snapshot_iteration
from scripts.game_data.damage_snapshot_compact_flow import check_snapshot_compact
from scripts.game_data.damage_snapshot_forward_flow import check_snapshot_forward
from scripts.game_data.damage_snapshot_probe_flow import check_snapshot_probe
from scripts.game_data.damage_snapshot_process_flow import check_process_local
from scripts.game_data.damage_snapshot_process_loop_flow import check_process_loop
from scripts.game_data.damage_snapshot_process_provider_flow import check_process_provider
from scripts.game_data.damage_snapshot_process_context_flow import check_process_context
from scripts.game_data.damage_snapshot_process_bound_flow import check_process_bound
from scripts.game_data.damage_snapshot_process_unit_slot_flow import check_process_unit_slot
from scripts.game_data.damage_snapshot_process_zero_return_flow import check_process_zero_return
from scripts.game_data.damage_snapshot_normal_formula_flow import check_normal_formula
from scripts.game_data.damage_snapshot_normal_attack_poise_flow import check_normal_attack_poise
from scripts.game_data.damage_snapshot_definite_value_flow import check_definite_value
from scripts.game_data.damage_snapshot_primary_attr_flow import check_primary_attr
from scripts.game_data.damage_snapshot_breaking_attack_flow import check_breaking_attack
from scripts.game_data.damage_snapshot_atk_scale_flow import check_atk_scale
from scripts.game_data.damage_snapshot_primary_selector_flow import check_primary_selector
from scripts.game_data.damage_snapshot_calculation_dispatch_flow import check_calculation_dispatch
from scripts.game_data.damage_snapshot_calculation_inline_flow import check_calculation_inline
from scripts.game_data.damage_snapshot_poise_delta_flow import check_poise_delta
from scripts.game_data.damage_snapshot_poise_setter_flow import check_poise_setter
from scripts.game_data.damage_snapshot_max_poise_flow import check_max_poise
from scripts.game_data.damage_snapshot_damage_scale_fold import check_fold
from scripts.game_data.damage_snapshot_final_attack_flow import check_final_attack
from scripts.game_data.damage_snapshot_damage_type_selector import check_damage_type_selector
from scripts.game_data.damage_snapshot_dump_attributes_flow import check_dump_attributes
from scripts.game_data.damage_snapshot_process_pack_copy_flow import check_process_pack_copy
from scripts.game_data.damage_snapshot_multiply_formula_flow import check_multiply_formula, check_multiply_defender_bridge
from scripts.game_data.damage_snapshot_poise_copy_flow import check_poise_copy
from scripts.game_data.damage_snapshot_poise_constructor_flow import check_poise_constructor_caller
from scripts.game_data.damage_snapshot_poise_attribute_flow import check_poise_attribute_store, check_poise_attribute_guard, check_poise_attribute_bridge
from scripts.game_data.damage_snapshot_poise_defender_flow import check_second_factory, check_defender_store, check_defender_bridge, check_constructor_footer
from scripts.game_data.damage_snapshot_poise_constructor_setup_flow import check_poise_constructor_setup
from scripts.game_data.damage_snapshot_poise_constructor_entry_flow import check_poise_constructor_entry
from scripts.game_data.damage_snapshot_poise_array_publication_flow import check_poise_array_publication
from scripts.game_data.damage_snapshot_attribute_cached_second_read_flow import check_attribute_cached_second_read
from scripts.game_data.damage_snapshot_attribute_cache_second_half_flow import check_attribute_cache_second_half
from scripts.game_data.damage_snapshot_attribute_cache_return_flow import check_attribute_cache_return_bridge
from scripts.game_data.damage_snapshot_attribute_cache_store_flow import check_attribute_cache_store
from scripts.game_data.damage_snapshot_poise_value_copy_flow import check_poise_value_copy
from scripts.game_data.damage_snapshot_attribute_cached_flow import check_poise_cached_attribute, check_poise_cached_entry
from scripts.game_data.il2cpp.native_image import (open_native_image, read_reviewed_contract,
    NATIVE_MAPPER_PATH, METADATA_HELPER_PATH)
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots

CONTRACT_PATH = CONTRACTS_DIR / 'damage_snapshot_consumers_native.json'
SCHEMA = 'endfield.damage-snapshot-consumer-claims.v61'


def _unity_hash(path: Path) -> str | None:
    if not path.is_file(): return None
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def _proof_sources() -> list[dict[str, Any]]:
    return _parser_source_snapshots(Path(__file__)) + [_fingerprint(path)
        for path in (CONTRACT_PATH, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH)]


def load_consumer_claims(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    sources = _proof_sources()
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='reviewed', label='damageSnapshotConsumers')
    gate = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
    result = {'schema': 'endfield.damage-snapshot-consumer-audit.v62', 'status': gate.status,
        'detail': gate.detail, 'rows': [], 'failures': [], 'contract': CONTRACT_PATH.as_posix(),
        'evidenceBoundary': contract['evidenceBoundary'], 'liveDamageOrFinalOutputObserved': False,
        'selectedNativePaths': {'gameassembly': str(gate.gameassembly) if gate.gameassembly else None,
                                'metadata': str(gate.metadata) if gate.metadata else None},
        'storedRootAdmitted': False, 'provenance': {'inputs': sources}}
    if gate.status != 'validated': return result
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    result['selectedNativePaths']['unityPlayer'] = str(unity)
    unity_hash = _unity_hash(unity)
    if unity_hash is None:
        return {**result, 'status': 'missing', 'detail': 'UnityPlayer.dll missing'}
    pins = {'GameAssembly.dll': gate.gameassembly_sha256,
        'global-metadata.dat': gate.metadata_sha256, 'UnityPlayer.dll': unity_hash}
    result['nativeInputs'] = pins
    index = BodyIndex(open_native_image(gate.gameassembly, gate.metadata))
    rows, failures = evaluate(index, contract['methods'])
    probe_proof = None
    try:
        probe_proof = check_snapshot_probe(index, contract['probeProgram'])
        rows.append(probe_proof)
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures.append({'symbol': 'DamageAction.ProcessDamage actual probe', 'claim': 'snapshotActualProcessProbeRaxAndConditionalFrame', 'reason': str(exc)})
    except Exception as exc:
        failures.append({'symbol': 'DamageAction.ProcessDamage actual probe', 'claim': 'snapshotActualProcessProbeRaxAndConditionalFrame', 'kind': 'toolingFailure',
            'check': 'stage-execution', 'stage': 'check_snapshot_probe', 'source': str(Path(__file__).with_name('damage_snapshot_probe_flow.py')),
            'exceptionType': type(exc).__name__, 'reason': str(exc)})
    consumer_proof = None
    try:
        consumer_proof = check_cache_return(index, contract['cacheReturnProgram'])
        rows.append(consumer_proof)
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures.append({'symbol': 'normalConsumer', 'claim': 'snapshotCacheIndexToReturn', 'reason': str(exc)})
    except Exception as exc:
        failures.append({'symbol': 'normalConsumer', 'claim': 'snapshotCacheIndexToReturn', 'kind': 'toolingFailure',
            'check': 'stage-execution', 'stage': 'check_cache_return', 'source': str(Path(__file__).with_name('damage_snapshot_cache_flow.py')),
            'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    formula_proof = None
    if consumer_proof is not None:
        try:
            formula_proof = check_normal_formula(index, consumer_proof, contract['normalFormulaProgram'])
            rows.append(formula_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction normal simple formula', 'claim': 'snapshotNormalSimpleFloatScaleTimesDoubleCarrierToResult', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction normal simple formula', 'claim': 'snapshotNormalSimpleFloatScaleTimesDoubleCarrierToResult', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_normal_formula', 'source': str(Path(__file__).with_name('damage_snapshot_normal_formula_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if consumer_proof is not None:
        try:
            rows.append(check_normal_attack_poise(index, consumer_proof, contract['normalAttackPoiseProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'NormalAttackPoiseCalculation.Evaluate', 'claim': 'normalAttackPoiseSingleOperandMultiplyThenDoubleResult', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'NormalAttackPoiseCalculation.Evaluate', 'claim': 'normalAttackPoiseSingleOperandMultiplyThenDoubleResult', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_normal_attack_poise', 'source': str(Path(__file__).with_name('damage_snapshot_normal_attack_poise_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if consumer_proof is not None:
        try:
            rows.append(check_definite_value(index, consumer_proof, contract['definiteValueProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DefiniteValueCalculation.Evaluate', 'claim': 'definiteValueNamedDoubleTimesWidenedSingleScaleToResult', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DefiniteValueCalculation.Evaluate', 'claim': 'definiteValueNamedDoubleTimesWidenedSingleScaleToResult', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_definite_value', 'source': str(Path(__file__).with_name('damage_snapshot_definite_value_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if consumer_proof is not None:
        try:
            rows.append(check_primary_attr(index, consumer_proof, contract['primaryAttrProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'PrimaryAttrCalculation.Evaluate', 'claim': 'primaryAttributeDoubleRoundedSingleScaleThenPackedLowLaneResult', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'PrimaryAttrCalculation.Evaluate', 'claim': 'primaryAttributeDoubleRoundedSingleScaleThenPackedLowLaneResult', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_primary_attr', 'source': str(Path(__file__).with_name('damage_snapshot_primary_attr_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if consumer_proof is not None:
        try:
            rows.append(check_breaking_attack(index, consumer_proof, contract['breakingAttackProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'BreakingAttackCalculation.Evaluate', 'claim': 'breakingAttackTypedAttributesAndSingleFactorsMixedPrecisionResult', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'BreakingAttackCalculation.Evaluate', 'claim': 'breakingAttackTypedAttributesAndSingleFactorsMixedPrecisionResult', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_breaking_attack', 'source': str(Path(__file__).with_name('damage_snapshot_breaking_attack_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if consumer_proof is not None:
        try:
            rows.append(check_atk_scale(index, consumer_proof, contract['atkScaleProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'AtkScaleCalculation.Evaluate', 'claim': 'atkScaleNullOverrideNamedAttackDoubleTimesWidenedSingleResult', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'AtkScaleCalculation.Evaluate', 'claim': 'atkScaleNullOverrideNamedAttackDoubleTimesWidenedSingleResult', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_atk_scale', 'source': str(Path(__file__).with_name('damage_snapshot_atk_scale_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if consumer_proof is not None:
        try:
            rows.append(check_primary_selector(index, consumer_proof, contract['primarySelectorProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'PrimaryAttrCalculation.Evaluate selector', 'claim': 'primaryAttributeTypeNeitherMainNorSubPositiveZeroResult', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'PrimaryAttrCalculation.Evaluate selector', 'claim': 'primaryAttributeTypeNeitherMainNorSubPositiveZeroResult', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_primary_selector', 'source': str(Path(__file__).with_name('damage_snapshot_primary_selector_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    dispatch_proof = None
    if consumer_proof is not None:
        try:
            dispatch_proof = check_calculation_dispatch(index, consumer_proof, contract['calculationDispatchProgram'])
            rows.append(dispatch_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction calculation callback selector', 'claim': 'calculationIndirectCallbackAndNamedDefiniteEntrySelection', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction calculation callback selector', 'claim': 'calculationIndirectCallbackAndNamedDefiniteEntrySelection', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_calculation_dispatch', 'source': str(Path(__file__).with_name('damage_snapshot_calculation_dispatch_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if dispatch_proof is not None:
        try:
            rows.extend(check_calculation_inline(index, dispatch_proof, contract['calculationInlineProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction equal-entry inline selector', 'claim': 'calculationDefiniteEntryEqualInlineSelectedResults', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction equal-entry inline selector', 'claim': 'calculationDefiniteEntryEqualInlineSelectedResults', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_calculation_inline', 'source': str(Path(__file__).with_name('damage_snapshot_calculation_inline_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    try:
        rows.extend(check_poise_delta(index, contract['poiseDeltaProgram']))
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures.append({'symbol': 'Modifier.get_finalDelta and explicit-ref caller', 'claim': 'poiseModifierSelectedRawNumericalReturns', 'stage': 'check_poise_delta', 'source': str(Path(__file__).with_name('damage_snapshot_poise_delta_flow.py')), 'reason': str(exc)})
    except Exception as exc:
        failures.append({'symbol': 'Modifier.get_finalDelta and explicit-ref caller', 'claim': 'poiseModifierSelectedRawNumericalReturns', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_delta', 'source': str(Path(__file__).with_name('damage_snapshot_poise_delta_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    setter_proof = None
    try:
        setter_rows = check_poise_setter(index, contract['poiseSetterProgram'])
        rows.extend(setter_rows)
        setter_proof = setter_rows[0] if setter_rows else None
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures.append({'symbol': 'AbilitySystem.set_poise', 'claim': 'poiseSetterSelectedCandidateLocalWriteChoice', 'stage': 'check_poise_setter', 'source': str(Path(__file__).with_name('damage_snapshot_poise_setter_flow.py')), 'reason': str(exc)})
    except Exception as exc:
        failures.append({'symbol': 'AbilitySystem.set_poise', 'claim': 'poiseSetterSelectedCandidateLocalWriteChoice', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_setter', 'source': str(Path(__file__).with_name('damage_snapshot_poise_setter_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    if setter_proof is not None:
        try:
            rows.extend(check_max_poise(index, setter_proof, contract['maxPoiseProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'AbilitySystem.get_maxPoise and setter input carry', 'claim': 'maxPoiseTypedAttributeRequestDoubleToSingleNormalReturn', 'stage': 'check_max_poise', 'source': str(Path(__file__).with_name('damage_snapshot_max_poise_flow.py')), 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'AbilitySystem.get_maxPoise and setter input carry', 'claim': 'maxPoiseTypedAttributeRequestDoubleToSingleNormalReturn', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_max_poise', 'source': str(Path(__file__).with_name('damage_snapshot_max_poise_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    fold_proof = None
    try:
        fold_rows = check_fold(index, contract['damageScaleFoldProgram'])
        rows.extend(fold_rows)
        fold_proof = fold_rows[-1] if fold_rows else None
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures.append({'symbol': 'DamagePackData._GetFinalDamageScale', 'claim': 'damageScaleOrderedDoubleFold', 'stage': 'check_fold', 'source': str(Path(__file__).with_name('damage_snapshot_damage_scale_fold.py')), 'reason': str(exc)})
    except Exception as exc:
        failures.append({'symbol': 'DamagePackData._GetFinalDamageScale', 'claim': 'damageScaleOrderedDoubleFold', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_fold', 'source': str(Path(__file__).with_name('damage_snapshot_damage_scale_fold.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    if fold_proof is not None:
        try:
            rows.append(check_final_attack(index, fold_proof, contract['finalAttackProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamagePackData.GetFinalAttackValue', 'claim': 'finalAttackAfterCalculationFoldTimesPostCallValueNormalResult', 'stage': 'check_final_attack', 'source': str(Path(__file__).with_name('damage_snapshot_final_attack_flow.py')), 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamagePackData.GetFinalAttackValue', 'claim': 'finalAttackAfterCalculationFoldTimesPostCallValueNormalResult', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_final_attack', 'source': str(Path(__file__).with_name('damage_snapshot_final_attack_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    selector_proof = None
    try:
        selector_proof = check_damage_type_selector(index, contract['damageTypeSelectorProgram'])
        rows.append(selector_proof)
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures.append({'symbol': 'DamagePackData._GetAttackerDamageScaleIncreaseFromDamageType', 'claim': 'damageTypeSelectedAttackerDoubleArraySlotNormalReturn', 'stage': 'check_damage_type_selector', 'source': str(Path(__file__).with_name('damage_snapshot_damage_type_selector.py')), 'reason': str(exc)})
    except Exception as exc:
        failures.append({'symbol': 'DamagePackData._GetAttackerDamageScaleIncreaseFromDamageType', 'claim': 'damageTypeSelectedAttackerDoubleArraySlotNormalReturn', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_damage_type_selector', 'source': str(Path(__file__).with_name('damage_snapshot_damage_type_selector.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    if selector_proof is not None:
        try:
            rows.append(check_dump_attributes(index, selector_proof, contract['dumpAttributesProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamagePackData._DumpAttributes', 'claim': 'dumpAttributesTwoOrderedEnumDoubleArrayLoopsNormalReturn', 'stage': 'check_dump_attributes', 'source': str(Path(__file__).with_name('damage_snapshot_dump_attributes_flow.py')), 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamagePackData._DumpAttributes', 'claim': 'dumpAttributesTwoOrderedEnumDoubleArrayLoopsNormalReturn', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_dump_attributes', 'source': str(Path(__file__).with_name('damage_snapshot_dump_attributes_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    multiply_proof = None
    if consumer_proof is not None:
        try:
            multiply_proof = check_multiply_formula(index, consumer_proof, contract['multiplyFormulaProgram'])
            rows.append(multiply_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'MultiplyAttributeCalculation.Evaluate', 'claim': 'multiplyAttributeSelectedFloatAffineToCalcResult', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'MultiplyAttributeCalculation.Evaluate', 'claim': 'multiplyAttributeSelectedFloatAffineToCalcResult', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_multiply_formula', 'source': str(Path(__file__).with_name('damage_snapshot_multiply_formula_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if multiply_proof is not None:
        try:
            rows.append(check_multiply_defender_bridge(index, multiply_proof, contract['multiplyFormulaProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'MultiplyAttributeCalculation.Evaluate defender bridge', 'claim': 'multiplyAttributeNonzeroSourceDefenderBridge', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'MultiplyAttributeCalculation.Evaluate defender bridge', 'claim': 'multiplyAttributeNonzeroSourceDefenderBridge', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_multiply_defender_bridge', 'source': str(Path(__file__).with_name('damage_snapshot_multiply_formula_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    poise_proof = None
    if consumer_proof is not None:
        try:
            poise_proof = check_poise_copy(index, consumer_proof, contract['poiseCopyProgram'])
            rows.append(poise_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process Poise bit transfer', 'claim': 'poiseOpaqueResultLowHalfToTypedPackViewAndCopy', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process Poise bit transfer', 'claim': 'poiseOpaqueResultLowHalfToTypedPackViewAndCopy', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_copy', 'source': str(Path(__file__).with_name('damage_snapshot_poise_copy_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    poise_ctor_proof = None
    if poise_proof is not None:
        try:
            poise_ctor_proof = check_poise_constructor_caller(index, poise_proof, contract['poiseConstructorProgram'])
            rows.append(poise_ctor_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process Poise constructor request', 'claim': 'poiseConstructorRequestAndNormalPackTransfer', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process Poise constructor request', 'claim': 'poiseConstructorRequestAndNormalPackTransfer', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_constructor_caller', 'source': str(Path(__file__).with_name('damage_snapshot_poise_constructor_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    attribute_store_proof = None
    if poise_ctor_proof is not None:
        try:
            attribute_store_proof = check_poise_attribute_store(index, poise_ctor_proof, contract['poiseAttributeProgram'])
            rows.append(attribute_store_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'PoisePackData attribute store', 'claim': 'poiseAttributeNormalDoubleToOldIndexStore', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'PoisePackData attribute store', 'claim': 'poiseAttributeNormalDoubleToOldIndexStore', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_attribute_store', 'source': str(Path(__file__).with_name('damage_snapshot_poise_attribute_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    attribute_guard_proof = None
    attribute_cached_proof = None
    if attribute_store_proof is not None:
        for checker, program, claim, label, source, stage in (
                (check_poise_attribute_guard, 'poiseAttributeProgram', 'poiseAttributeZeroIndexAndSignedGuard', 'PoisePackData attribute guard', 'damage_snapshot_poise_attribute_flow.py', 'check_poise_attribute_guard'),
                (check_poise_cached_attribute, 'attributeCachedProgram', 'poiseAttributeSelectedCachedDoubleReturn', 'Attributes cached return', 'damage_snapshot_attribute_cached_flow.py', 'check_poise_cached_attribute')):
            try:
                stage_proof = checker(index, attribute_store_proof, contract[program])
                rows.append(stage_proof)
                if stage == 'check_poise_attribute_guard':
                    attribute_guard_proof = stage_proof
                elif stage == 'check_poise_cached_attribute':
                    attribute_cached_proof = stage_proof
            except (ValueError, RuntimeError, KeyError, IndexError) as exc:
                failures.append({'symbol': label, 'claim': claim, 'reason': str(exc)})
            except Exception as exc:
                failures.append({'symbol': label, 'claim': claim, 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': stage, 'source': str(Path(__file__).with_name(source)), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    poise_entry_proof = None
    if poise_ctor_proof is not None:
        try:
            poise_entry_proof = check_poise_constructor_entry(index, poise_ctor_proof, contract['poiseConstructorProgram'])
            rows.append(poise_entry_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise constructor entry', 'claim': 'poiseConstructorEntryFullWidthArgumentCarriersAndFrame', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise constructor entry', 'claim': 'poiseConstructorEntryFullWidthArgumentCarriersAndFrame', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_constructor_entry', 'source': str(Path(__file__).with_name('damage_snapshot_poise_constructor_entry_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    attribute_bridge_proof = None
    if attribute_store_proof is not None and attribute_guard_proof is not None:
        try:
            attribute_bridge_proof = check_poise_attribute_bridge(index, attribute_store_proof, attribute_guard_proof, contract['poiseAttributeProgram'])
            rows.append(attribute_bridge_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise attribute guard/store bridge', 'claim': 'poiseAttributeGuardArrayCarrierAndSelectedLoopJoin', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise attribute guard/store bridge', 'claim': 'poiseAttributeGuardArrayCarrierAndSelectedLoopJoin', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_attribute_bridge', 'source': str(Path(__file__).with_name('damage_snapshot_poise_attribute_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    attribute_publication_proof = None
    if attribute_guard_proof is not None and attribute_bridge_proof is not None:
        try:
            attribute_publication_proof = check_poise_array_publication(index, attribute_guard_proof, attribute_bridge_proof, contract['poiseAttributeProgram']['anonymousProgram'])
            rows.append(attribute_publication_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise opaque pointer publication', 'claim': 'poiseOpaqueNormalPointerPublicationToSelectedArrayCarrier', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise opaque pointer publication', 'claim': 'poiseOpaqueNormalPointerPublicationToSelectedArrayCarrier', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_array_publication', 'source': str(Path(__file__).with_name('damage_snapshot_poise_array_publication_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    poise_setup_proof = None
    if poise_entry_proof is not None and attribute_publication_proof is not None:
        try:
            poise_setup_proof = check_poise_constructor_setup(index, poise_entry_proof, attribute_publication_proof, attribute_guard_proof, attribute_bridge_proof, attribute_store_proof, contract['poiseConstructorSetupProgram'], contract['poiseAttributeProgram']['anonymousProgram'])
            rows.append(poise_setup_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise selected constructor setup', 'claim': 'poiseSelectedConstructorSetupToFirstAttributeStoreAndCountSource', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise selected constructor setup', 'claim': 'poiseSelectedConstructorSetupToFirstAttributeStoreAndCountSource', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_constructor_setup', 'source': str(Path(__file__).with_name('damage_snapshot_poise_constructor_setup_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    second_factory_proof = None
    defender_store_proof = None
    defender_bridge_proof = None
    if poise_setup_proof is not None:
        try:
            second_factory_proof = check_second_factory(index, attribute_guard_proof, poise_setup_proof, contract['poiseDefenderProgram'], contract['poiseAttributeProgram']['anonymousProgram'])
            rows.append(second_factory_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise second opaque pointer/guard', 'claim': 'poiseSecondOpaquePointerPublicationAndSignedGuard', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise second opaque pointer/guard', 'claim': 'poiseSecondOpaquePointerPublicationAndSignedGuard', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_second_factory', 'source': str(Path(__file__).with_name('damage_snapshot_poise_defender_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if second_factory_proof is not None:
        try:
            defender_store_proof = check_defender_store(index, attribute_store_proof, second_factory_proof, contract['poiseAttributeProgram'], contract['poiseAttributeProgram']['anonymousProgram'])
            rows.append(defender_store_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise defender Double/store', 'claim': 'poiseDefenderOrdinaryDoubleToOldIndexSecondArrayStore', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise defender Double/store', 'claim': 'poiseDefenderOrdinaryDoubleToOldIndexSecondArrayStore', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_defender_store', 'source': str(Path(__file__).with_name('damage_snapshot_poise_defender_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if defender_store_proof is not None:
        try:
            defender_bridge_proof = check_defender_bridge(index, second_factory_proof, defender_store_proof, contract['poiseDefenderProgram'], contract['poiseAttributeProgram']['anonymousProgram'])
            rows.append(defender_bridge_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise defender selected loop', 'claim': 'poiseDefenderSecondArrayCarrierAndSelectedCycle', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise defender selected loop', 'claim': 'poiseDefenderSecondArrayCarrierAndSelectedCycle', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_defender_bridge', 'source': str(Path(__file__).with_name('damage_snapshot_poise_defender_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
        try:
            rows.append(check_constructor_footer(index, poise_entry_proof, attribute_guard_proof, second_factory_proof, defender_store_proof))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise constructor selected void RET', 'claim': 'poiseConstructorSelectedVoidRetAndSavedFrameRestore', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise constructor selected void RET', 'claim': 'poiseConstructorSelectedVoidRetAndSavedFrameRestore', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_constructor_footer', 'source': str(Path(__file__).with_name('damage_snapshot_poise_defender_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    attribute_entry_proof = None
    if attribute_store_proof is not None and attribute_cached_proof is not None:
        try:
            attribute_entry_proof = check_poise_cached_entry(index, attribute_store_proof, attribute_cached_proof, contract['attributeCachedProgram'])
            rows.append(attribute_entry_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Attributes selected entry/cached return', 'claim': 'poiseAttributeSelectedEntryCachedReturnAndSavedState', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Attributes selected entry/cached return', 'claim': 'poiseAttributeSelectedEntryCachedReturnAndSavedState', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_cached_entry', 'source': str(Path(__file__).with_name('damage_snapshot_attribute_cached_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if attribute_store_proof is not None and attribute_entry_proof is not None:
        try:
            rows.append(check_poise_value_copy(attribute_store_proof, attribute_entry_proof, contract['attributeCachedProgram'], contract['poiseAttributeProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Poise same-index cached bits/store', 'claim': 'poiseAttributeSelectedCachedBitsToSameOldIndexStore', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Poise same-index cached bits/store', 'claim': 'poiseAttributeSelectedCachedBitsToSameOldIndexStore', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_poise_value_copy', 'source': str(Path(__file__).with_name('damage_snapshot_poise_value_copy_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    attribute_cache_store_proof = None
    if attribute_entry_proof is not None:
        try:
            attribute_cache_store_proof = check_attribute_cache_store(index, attribute_entry_proof, contract['attributeCachedProgram'])
            rows.append(attribute_cache_store_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Attributes anonymous cached publication', 'claim': 'attributeAnonymousArrayEightBytePublicationAndRestoringReturn', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Attributes anonymous cached publication', 'claim': 'attributeAnonymousArrayEightBytePublicationAndRestoringReturn', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_attribute_cache_store', 'source': str(Path(__file__).with_name('damage_snapshot_attribute_cache_store_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    attribute_cache_return_proof = None
    if attribute_cache_store_proof is not None:
        try:
            attribute_cache_return_proof = check_attribute_cache_return_bridge(index, attribute_cache_store_proof, contract['attributeCacheReturnBridgeProgram'], contract['attributeCachedProgram']['anonymousProgram'])
            rows.append(attribute_cache_return_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Attributes opaque-return/cache bridge', 'claim': 'attributeOpaqueNormalReturnBitsThroughCachePublication', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Attributes opaque-return/cache bridge', 'claim': 'attributeOpaqueNormalReturnBitsThroughCachePublication', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_attribute_cache_return_bridge', 'source': str(Path(__file__).with_name('damage_snapshot_attribute_cache_return_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if attribute_cache_return_proof is not None:
        try:
            rows.append(check_attribute_cache_second_half(index, attribute_cache_return_proof, contract['attributeCachedProgram']['anonymousProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Attributes second anonymous-word cache branch', 'claim': 'attributeSecondAnonymousWordBitClearAndSameCacheReturnTail', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Attributes second anonymous-word cache branch', 'claim': 'attributeSecondAnonymousWordBitClearAndSameCacheReturnTail', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_attribute_cache_second_half', 'source': str(Path(__file__).with_name('damage_snapshot_attribute_cache_second_half_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if attribute_entry_proof is not None:
        try:
            rows.append(check_attribute_cached_second_read(index, attribute_entry_proof, contract['attributeCachedProgram']['anonymousProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'Attributes second anonymous-word cached read', 'claim': 'attributeSelectedEntrySecondAnonymousWordCachedReturn', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'Attributes second anonymous-word cached read', 'claim': 'attributeSelectedEntrySecondAnonymousWordCachedReturn', 'kind': 'toolingFailure', 'check': 'stage-execution', 'stage': 'check_attribute_cached_second_read', 'source': str(Path(__file__).with_name('damage_snapshot_attribute_cached_second_read_flow.py')), 'exceptionType': type(exc).__name__, 'reason': str(exc)})
    process_proof = None
    if consumer_proof is not None:
        try:
            process_proof = check_process_local(index, consumer_proof, contract['processLocalProgram'])
            rows.append(process_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process local normal request', 'claim': 'snapshotProcessLocalIndexNormalRequestAndTemporary', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process local normal request', 'claim': 'snapshotProcessLocalIndexNormalRequestAndTemporary', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_process_local', 'source': str(Path(__file__).with_name('damage_snapshot_process_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if process_proof is not None and formula_proof is not None:
        try:
            rows.append(check_process_pack_copy(index, process_proof, formula_proof, contract['processPackCopyProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process pack byte copy', 'claim': 'snapshotProcessAnonymousPackBytesCopyToNormalArgument', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process pack byte copy', 'claim': 'snapshotProcessAnonymousPackBytesCopyToNormalArgument', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_process_pack_copy', 'source': str(Path(__file__).with_name('damage_snapshot_process_pack_copy_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if process_proof is not None and probe_proof is not None:
        try:
            rows.append(check_process_zero_return(index, process_proof, probe_proof, contract['processZeroReturnProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process Bool zero return', 'claim': 'snapshotProcessBoolProxyZeroToCompleteFalseReturn', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process Bool zero return', 'claim': 'snapshotProcessBoolProxyZeroToCompleteFalseReturn', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_process_zero_return', 'source': str(Path(__file__).with_name('damage_snapshot_process_zero_return_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    loop_proof = None
    if process_proof is not None:
        try:
            loop_proof = check_process_loop(index, process_proof, contract['processLoopProgram'])
            rows.append(loop_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process local loop', 'claim': 'snapshotProcessLocalIncrementGuardAndProviderRequest', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process local loop', 'claim': 'snapshotProcessLocalIncrementGuardAndProviderRequest', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_process_loop', 'source': str(Path(__file__).with_name('damage_snapshot_process_loop_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    provider_proof = None
    if loop_proof is not None:
        try:
            provider_proof = check_process_provider(index, loop_proof, contract['processProviderProgram'])
            rows.append(provider_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process actual provider', 'claim': 'snapshotProcessActualProviderEightByteNormalReturn', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process actual provider', 'claim': 'snapshotProcessActualProviderEightByteNormalReturn', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_process_provider', 'source': str(Path(__file__).with_name('damage_snapshot_process_provider_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if provider_proof is not None and process_proof is not None:
        try:
            rows.append(check_process_unit_slot(index, loop_proof, provider_proof, process_proof, contract['processUnitSlotProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process unit temporary', 'claim': 'snapshotProcessProviderBitsToUnitTemporaryAndReload', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process unit temporary', 'claim': 'snapshotProcessProviderBitsToUnitTemporaryAndReload', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_process_unit_slot', 'source': str(Path(__file__).with_name('damage_snapshot_process_unit_slot_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if provider_proof is not None:
        try:
            rows.append(check_process_context(index, loop_proof, provider_proof, contract['processContextProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process static context', 'claim': 'snapshotProcessStaticClosedUnitGetterRequest', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process static context', 'claim': 'snapshotProcessStaticClosedUnitGetterRequest', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_process_context', 'source': str(Path(__file__).with_name('damage_snapshot_process_context_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    if consumer_proof is not None:
        try:
            rows.append(check_snapshot_forward(index, consumer_proof, contract['forwardProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.ByType index forwarding', 'claim': 'snapshotByTypeIndexUnitAndResultForward', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.ByType index forwarding', 'claim': 'snapshotByTypeIndexUnitAndResultForward', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_snapshot_forward', 'source': str(Path(__file__).with_name('damage_snapshot_forward_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    append_proof = None
    try:
        append_proof = check_simple_append(index, contract['simpleAppendProgram'])
        rows.append(append_proof)
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures.append({'symbol': 'snapshotProducer', 'claim': 'snapshotSimpleValueToAppendRequest', 'reason': str(exc)})
    except Exception as exc:
        failures.append({'symbol': 'snapshotProducer', 'claim': 'snapshotSimpleValueToAppendRequest', 'kind': 'toolingFailure',
            'check': 'stage-execution', 'stage': 'check_simple_append', 'source': str(Path(__file__).with_name('damage_snapshot_append_flow.py')),
            'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    writer_proof = None
    if append_proof is not None:
        try:
            writer_proof = check_compiled_append_helper(index, append_proof, contract['compiledHelperProgram'])
            rows.append(writer_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'compiled snapshot append helper', 'claim': 'snapshotCompiledHelperRawStore', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'compiled snapshot append helper', 'claim': 'snapshotCompiledHelperRawStore', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_compiled_append_helper', 'source': str(Path(__file__).with_name('damage_snapshot_append_helper.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    if consumer_proof is not None and writer_proof is not None:
        try:
            rows.append(check_cache_getter(index, consumer_proof, writer_proof, contract['getterProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'closed Double cache getter', 'claim': 'snapshotPhysicalGetterAndConditionalElementJoin', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'closed Double cache getter', 'claim': 'snapshotPhysicalGetterAndConditionalElementJoin', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_cache_getter', 'source': str(Path(__file__).with_name('damage_snapshot_getter_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    clear_proof = None
    if writer_proof is not None:
        try:
            clear_proof = check_cache_clear(index, writer_proof, contract['clearProgram'])
            rows.append(clear_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'snapshotProducer', 'claim': 'snapshotIncomingThisCacheReset', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'snapshotProducer', 'claim': 'snapshotIncomingThisCacheReset', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_cache_clear', 'source': str(Path(__file__).with_name('damage_snapshot_clear_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    if clear_proof is not None:
        try:
            rows.append(check_oncreate(index, clear_proof, contract['onCreateProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.OnCreate', 'claim': 'snapshotOnCreateIncomingThisTail', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.OnCreate', 'claim': 'snapshotOnCreateIncomingThisTail', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_oncreate', 'source': str(Path(__file__).with_name('damage_snapshot_oncreate_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    skip_proof = None
    if append_proof is not None and clear_proof is not None:
        try:
            skip_proof = check_snapshot_skip(index, append_proof, clear_proof, contract['skipProgram'])
            rows.append(skip_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'snapshot skip/append continuation', 'claim': 'snapshotFlagSkipAppendContinuation', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'snapshot skip/append continuation', 'claim': 'snapshotFlagSkipAppendContinuation', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_snapshot_skip', 'source': str(Path(__file__).with_name('damage_snapshot_skip_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    counter_proof = None
    if clear_proof is not None:
        try:
            counter_proof = check_snapshot_counter(index, clear_proof, contract['counterProgram'])
            rows.append(counter_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'snapshot counter initialization', 'claim': 'snapshotResetZeroToCounterInitialization', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'snapshot counter initialization', 'claim': 'snapshotResetZeroToCounterInitialization', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_snapshot_counter', 'source': str(Path(__file__).with_name('damage_snapshot_counter_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    count_proof = None
    if clear_proof is not None and counter_proof is not None:
        try:
            count_proof = check_snapshot_count(index, clear_proof, counter_proof, contract['countProgram'])
            rows.append(count_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'snapshot count null-return graph', 'claim': 'snapshotCountRequestNullHelperToProducerReturn', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'snapshot count null-return graph', 'claim': 'snapshotCountRequestNullHelperToProducerReturn', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_snapshot_count', 'source': str(Path(__file__).with_name('damage_snapshot_count_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    if loop_proof is not None and count_proof is not None:
        try:
            rows.append(check_process_bound(index, loop_proof, count_proof, contract['countProgram'], contract['processBoundProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction.Process count bound', 'claim': 'snapshotProcessCountResultToSignedBound', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction.Process count bound', 'claim': 'snapshotProcessCountResultToSignedBound', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_process_bound', 'source': str(Path(__file__).with_name('damage_snapshot_process_bound_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)})
    unit_proof = None
    if count_proof is not None and skip_proof is not None:
        try:
            unit_proof = check_snapshot_unit(index, count_proof, skip_proof, contract['unitProgram'])
            rows.append(unit_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'snapshot indexed unit graph', 'claim': 'snapshotRawIndexedUnitPointerToFlag', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'snapshot indexed unit graph', 'claim': 'snapshotRawIndexedUnitPointerToFlag', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_snapshot_unit', 'source': str(Path(__file__).with_name('damage_snapshot_unit_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    iteration_proof = None
    if all(proof is not None for proof in (counter_proof, count_proof, unit_proof, skip_proof, append_proof)):
        try:
            iteration_proof = check_snapshot_iteration(index, counter_proof, count_proof, unit_proof, skip_proof, append_proof, contract['iterationProgram'])
            rows.append(iteration_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'snapshot iteration connection graph', 'claim': 'snapshotZeroCounterPositiveBoundIterationConnections', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'snapshot iteration connection graph', 'claim': 'snapshotZeroCounterPositiveBoundIterationConnections', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_snapshot_iteration', 'source': str(Path(__file__).with_name('damage_snapshot_iteration_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    if all(proof is not None for proof in (clear_proof, writer_proof, append_proof, skip_proof, iteration_proof)):
        try:
            rows.append(check_snapshot_compact(index, clear_proof, writer_proof, append_proof, skip_proof, iteration_proof, contract['compactProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'snapshot conditional compact-cache model', 'claim': 'snapshotConditionalCompactCacheRecurrence', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'snapshot conditional compact-cache model', 'claim': 'snapshotConditionalCompactCacheRecurrence', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_snapshot_compact', 'source': str(Path(__file__).with_name('damage_snapshot_compact_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    constructor_proof = None
    if writer_proof is not None:
        try:
            constructor_proof = check_cache_constructor(index, writer_proof, contract['constructorProgram'])
            rows.append(constructor_proof)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'DamageAction..ctor', 'claim': 'snapshotConstructorCachePointerStore', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'DamageAction..ctor', 'claim': 'snapshotConstructorCachePointerStore', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_cache_constructor', 'source': str(Path(__file__).with_name('damage_snapshot_constructor_flow.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    if constructor_proof is not None:
        try:
            rows.append(check_constructor_slot_helper(index, constructor_proof, contract['slotHelperProgram']))
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'symbol': 'constructor slot helper entry', 'claim': 'snapshotConstructorSlotHelperNoninterference', 'reason': str(exc)})
        except Exception as exc:
            failures.append({'symbol': 'constructor slot helper entry', 'claim': 'snapshotConstructorSlotHelperNoninterference', 'kind': 'toolingFailure',
                'check': 'stage-execution', 'stage': 'check_constructor_slot_helper', 'source': str(Path(__file__).with_name('damage_snapshot_slot_helper.py')),
                'exceptionType': type(exc).__name__, 'reason': str(exc)[:512]})
    diagnostics = [{**failure, 'validator': 'damageSnapshotConsumers',
        'source': failure.get('source', CONTRACT_PATH.as_posix()), 'nativeInputs': pins} for failure in failures]
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    unity_after = _unity_hash(unity)
    if after.status != 'validated' or unity_after != unity_hash:
        return {**result, 'status': after.status if after.status != 'validated' else 'missing' if unity_after is None else 'mismatched',
            'detail': 'native inputs changed during consumer validation',
            'failures': diagnostics + [{'validator': 'damageSnapshotConsumers', 'check': 'native-inputs-after',
                'source': str(gate.gameassembly), 'expected': pins,
                'actual': {'selectedGate': after.detail, 'UnityPlayer.dll': unity_after}}]}
    drift = [{'validator': 'damageSnapshotConsumers', 'check': 'proof-source-after',
        'source': source['path'], 'expected': source, 'actual': actual}
        for source in sources if (actual := _fingerprint(Path(source['path']))) != source]
    if drift:
        return {**result, 'status': 'pendingReview', 'detail': 'proof sources changed during consumer validation',
            'failures': diagnostics + drift}
    return {**result, 'status': 'toolingFailure' if any(f.get('kind') == 'toolingFailure' for f in failures) else 'pendingReview' if failures else 'validated',
        'detail': f'{len(failures)} failed claim(s)' if failures else '',
        'rows': [] if failures else rows, 'failures': diagnostics}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path); parser.add_argument('--metadata', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    target = args.output.resolve()
    if not any(target.is_relative_to(REPO_ROOT / root) for root in ('reports', 'scratch', 'tmp')):
        parser.error('--output must be under reports/, scratch/ or tmp/')
    explicit_inputs = [args.gameassembly, args.metadata, CONTRACT_PATH, Path(__file__), NATIVE_MAPPER_PATH, METADATA_HELPER_PATH]
    def refuse_output_alias(destination, paths):
        resolved = destination.resolve()
        if not any(resolved.is_relative_to(REPO_ROOT / root) for root in ('reports', 'scratch', 'tmp')):
            parser.error('audit output must resolve under reports/, scratch/ or tmp/')
        for path in paths:
            if path is None:
                continue
            candidate = Path(path).resolve()
            if resolved == candidate or (resolved.exists() and candidate.exists() and resolved.samefile(candidate)):
                parser.error('audit output must not alias a selected native input or proof source')
    refuse_output_alias(target, explicit_inputs)
    result = load_consumer_claims(gameassembly=args.gameassembly, metadata=args.metadata)
    protected = explicit_inputs + list((result.get('selectedNativePaths') or {}).values())
    protected.extend(source['path'] for source in (result.get('provenance') or {}).get('inputs', []) if isinstance(source, dict) and source.get('path'))
    refuse_output_alias(target, protected)
    if result['status'] != 'validated':
        diagnostic = target.with_name(target.stem + '.diagnostics.json')
        refuse_output_alias(diagnostic, protected + [target])
        atomic_write_text(diagnostic, json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        if result['status'] in ('missing', 'mismatched'):
            print(f"damageSnapshotConsumers: {result['status']}: {result['detail']}; report left untouched; diagnostics={diagnostic}", file=sys.stderr, flush=True)
        else:
            print(json.dumps({'validator': 'damageSnapshotConsumers', 'status': result['status'], 'failures': result.get('failures', []), 'detail': result.get('detail', ''), 'diagnostics': str(diagnostic), 'publishedReportUntouched': str(target)}, ensure_ascii=False), file=sys.stderr, flush=True)
        return 1
    refuse_output_alias(target, protected)
    atomic_write_text(target, json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'rows': len(result['rows']),
        'failures': result['failures'], 'detail': result['detail']}, ensure_ascii=False), flush=True)
    return 0 if result['status'] == 'validated' else 1


if __name__ == '__main__':
    raise SystemExit(main())

