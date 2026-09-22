"""Selected-build marker17 body evidence, extending the shared Streaming gate."""
from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

from scripts.game_data import streaming_native as base
from scripts.game_data.streaming_marker17 import TAG5_RECORD_WIDTHS, FIXED_BODY_PROFILES
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA = 'endfield.streaming-marker17-native-contract.v2'
DEFAULT_CONTRACT = CONTRACTS_DIR / 'streaming_marker17_native.json'
CONTRACT_SHA256 = '34E915707F363B55F572D867C1CC3C1B28A76D66D132EB0E212377A730DD2891'
SELECTED_KEYS = {2: (4, 0, 0), 5: (5, 0, 0), 6: (9, 0, 0), 7: (8, 0, 0), 9: (255, 3, 0)}


def fixed_body_profiles() -> list[dict[str, Any]]:
    """Strict fixed-length policies, not a claim that native code checks EOF."""
    return [dict(selector=selector, key=list(SELECTED_KEYS[selector]), tag=tag,
                 bodyLength=length, conditionalReadCoverage=[[0, 30], [32, length]],
                 opaqueUnreadRanges=[[30, 32]])
            for (selector, _key), (tag, length) in FIXED_BODY_PROFILES.items()]


def validate_marker17_native_contract(
    *, game_root: Path, contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """An explicit Endfield_Data root is required; never infer a second root.

    The base validator invokes common.check_installed_native_inputs and verifies
    the shared lookup/registration proof. Only the new native ranges live here.
    No parser fixtures run inside the production evidence gate.
    """
    failures = []
    result = dict(status='validation_failed', profile=None, conditionalConsumer=None,
                  validationFailures=failures)

    def require(gate, expected, actual):
        if expected != actual:
            failures.append(dict(gate=gate, expected=expected, actual=actual))

    try:
        raw = Path(contract_path).read_bytes()
        contract_sha = base._sha256_bytes(raw)
        result['contractSha256'] = contract_sha
        require('contract_sha256', CONTRACT_SHA256, contract_sha)
        if failures:
            return result
        contract = json.loads(raw)
        require('schema', SCHEMA, contract.get('schema'))
        require('contract_status', 'validated-conditional-static', contract.get('status'))
        raw_base = base.DEFAULT_CONTRACT.read_bytes()
        base_document = json.loads(raw_base)
        dependency = contract['baseContract']
        require('base_contract_sha256', dependency['sha256'], base._sha256_bytes(raw_base))
        require('base_contract_schema', dependency['schema'], base_document.get('schema'))
        roles = {r['role'] for r in base_document['unityPlayerRanges']}
        require('base_contract_required_roles', [], sorted(set(dependency['requiredUnityPlayerRoles']) - roles))
        if failures:
            return result
        selected = base.validate_streaming_field2_native_contract(game_root=Path(game_root))
        require('base_native_gate', 'validated', selected.get('status'))
        if failures:
            result['baseValidationFailures'] = selected.get('validationFailures', [])
            return result
        require('validated_base_contract_sha256', dependency['sha256'], selected.get('contractSha256'))
        result['baseContractSha256'] = selected['contractSha256']
        native_inputs = contract['nativeInputs']
        for key, expected in native_inputs.items():
            require(f'native_input:{key}', expected, selected.get(key))
        image_path = Path(game_root).parent / 'UnityPlayer.dll'
        image = image_path.read_bytes()
        require('unity_image_read_sha256', native_inputs['unityPlayerSha256'], base._sha256_bytes(image))
        if failures:
            return result
        result['nativeInputs'] = {key: selected[key] for key in native_inputs}

        for row in contract['unityPlayerRanges']:
            role = row['role']
            try:
                offset, body = base._bounded_pe_range(image, row['rva'], row['size'])
                require(f'{role}.file_offset', row['fileOffset'], offset)
                require(f'{role}.body_sha256', row['bodySha256'], base._sha256_bytes(body))
                entry = bytes.fromhex(row['entryBytesHex'])
                require(f'{role}.entry_bytes', entry.hex().upper(), body[:len(entry)].hex().upper())
            except (TypeError, ValueError) as exc:
                failures.append(dict(gate=f'{role}.bounded_range', expected='bounded PE range', actual=str(exc)))
        exact = [dict(role=f"selector{r['selector']}.key", **r) for r in contract['keyLiteralRanges']]
        for row in contract['selectedDefaultSlot3']:
            exact.append(dict(role=f"selector{row['selector']}.descriptor_constructor", **row['descriptorConstructorSpan']))
            exact.append(dict(role=f"selector{row['selector']}.registration", **row['registrationSpan']))
            exact.append(dict(role=f"selector{row['selector']}.publication", **row['publicationSpan']))
            exact.extend(dict(role=f"selector{row['selector']}.consumer{i}", **span)
                         for i, span in enumerate(row['consumerSpans']))
        for row in exact:
            try:
                expected = bytes.fromhex(row['bytesHex'])
                offset, actual = base._bounded_pe_range(image, row['rva'], len(expected))
                require(f"{row['role']}.file_offset", row['fileOffset'], offset)
                require(f"{row['role']}.exact_bytes", expected.hex().upper(), actual.hex().upper())
            except (TypeError, ValueError) as exc:
                failures.append(dict(gate=f"{row['role']}.bounded_range", expected='bounded exact PE bytes', actual=str(exc)))
        for field in ('keyLiteralRanges', 'selectedDefaultSlot3'):
            rows = contract[field]
            require(f'{field}.selectors', sorted(SELECTED_KEYS), sorted(r['selector'] for r in rows))
            for row in rows:
                key = SELECTED_KEYS.get(row['selector'])
                require(f'{field}.key', key, tuple(row['key']))
                if field == 'keyLiteralRanges' and key is not None:
                    require(f'{field}.literal', struct.pack('<3I', *key).hex().upper(), row['bytesHex'])
                if field == 'selectedDefaultSlot3':
                    require(f'{field}.slot', 3, row['slot'])
        framing = contract['tag5Framing']
        offsets = [40, 44, 48, 52, 56, 60]
        require('tag5_count_offsets', offsets, [r['byteOffset'] for r in framing['counts']])
        require('tag5_record_widths', list(TAG5_RECORD_WIDTHS), [r['width'] for r in framing['counts']])
        require('tag5_segment_order', offsets, framing['segmentOrder'])
        require('tag5_discriminant', dict(byteOffset=28, storage='signed i16', requiredValue=5), framing['discriminant'])
        require('tag5_cursor_start', 64, framing['nativeEntry']['cursorStartByteOffset'])
        require('fixed_body_profiles', fixed_body_profiles(), contract['fixedBodyProfiles'])
        if not failures:
            result.update(status='validated', nativeMappingId=contract['nativeMappingId'],
                          profile=dict(tag=5, tagByteOffset=28, headerSize=64,
                                       selectedSlot3Keys=[dict(selector=s, key=list(k)) for s,k in SELECTED_KEYS.items()],
                                       countByteOffsets=offsets, recordWidths=list(TAG5_RECORD_WIDTHS),
                                       fields='opaque', evidenceLevel='structural-only',
                                       fixedBodyProfiles=contract['fixedBodyProfiles'],
                                       profileScope='tag5 framing plus explicitly selected fixed-body profiles'),
                          conditionalConsumer=contract['countedPrefixCarrier'],
                          evidenceBoundary=contract['evidenceBoundary'])
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        failures.append(dict(gate='marker17_contract_inputs', expected='readable, well-formed pinned evidence',
                             actual=f'{type(exc).__name__}: {exc}'))
    return result
