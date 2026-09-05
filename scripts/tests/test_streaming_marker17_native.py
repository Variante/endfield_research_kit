import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.game_data import streaming_marker17_native as marker17_native
from scripts.game_data import streaming_native as base


def _one_section_pe() -> bytearray:
    image = bytearray(0x500)
    struct.pack_into('<I', image, 0x3C, 0x80)
    image[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<H', image, 0x86, 1)
    struct.pack_into('<H', image, 0x94, 0xE0)
    section = 0x80 + 24 + 0xE0
    image[section:section + 8] = b'.text\0\0\0'
    struct.pack_into('<IIII', image, section + 8, 0x200, 0x1000, 0x200, 0x200)
    return image


class Marker17NativeContractTests(unittest.TestCase):
    def _fixture(self, root: Path):
        game_root = root / 'selected' / 'Endfield_Data'
        game_root.mkdir(parents=True)
        image = _one_section_pe()
        body = b'BODY'
        exact = {
            'key6': (0x1020, struct.pack('<3I', 9, 0, 0)),
            'key9': (0x1030, struct.pack('<3I', 255, 3, 0)),
            'registration6': (0x1040, b'R6'),
            'consumer6': (0x1050, b'C6'),
            'registration9': (0x1060, b'R9'),
            'consumer9': (0x1070, b'C9'),
            'constructor6': (0x1080, b'D6'),
            'publication6': (0x1090, b'P6'),
            'constructor9': (0x10A0, b'D9'),
            'publication9': (0x10B0, b'P9'),
            'key2': (0x10C0, struct.pack('<3I', 4, 0, 0)),
            'key5': (0x10D0, struct.pack('<3I', 5, 0, 0)),
            'key7': (0x10E0, struct.pack('<3I', 8, 0, 0)),
        }
        image[0x210:0x214] = body
        for _role, (rva, value) in exact.items():
            offset = 0x200 + rva - 0x1000
            image[offset:offset + len(value)] = value
        unity = game_root.parent / 'UnityPlayer.dll'
        unity.write_bytes(image)
        unity_hash = hashlib.sha256(image).hexdigest().upper()

        base_document = {
            'schema': 'fixture-base-v8',
            'status': 'validated',
            'unityPlayerRanges': [{'role': 'sharedLookup'}],
        }
        base_path = root / 'base.json'
        base_path.write_text(json.dumps(base_document), encoding='utf-8')
        base_hash = hashlib.sha256(base_path.read_bytes()).hexdigest().upper()

        def span(name):
            rva, value = exact[name]
            return {
                'rva': rva,
                'fileOffset': 0x200 + rva - 0x1000,
                'bytesHex': value.hex().upper(),
            }

        contract = {
            'schema': marker17_native.SCHEMA,
            'status': 'validated-conditional-static',
            'nativeMappingId': 'fixture-marker17',
            'baseContract': {
                'schema': 'fixture-base-v8',
                'sha256': base_hash,
                'requiredUnityPlayerRoles': ['sharedLookup'],
            },
            'nativeInputs': {
                'gameAssemblySha256': 'GA',
                'metadataSha256': 'MD',
                'unityPlayerSha256': unity_hash,
            },
            'unityPlayerRanges': [{
                'role': 'fixtureBody',
                'rva': 0x1010,
                'fileOffset': 0x210,
                'size': len(body),
                'bodySha256': hashlib.sha256(body).hexdigest().upper(),
                'entryBytesHex': body.hex().upper(),
            }],
            'keyLiteralRanges': [
                {'selector': 6, 'key': [9, 0, 0], **span('key6')},
                {'selector': 9, 'key': [255, 3, 0], **span('key9')},
            ],
            'selectedDefaultSlot3': [
                {'selector': 6, 'key': [9, 0, 0], 'slot': 3,
                 'readerRva': 0xE3E7A0,
                 'descriptorConstructorSpan': span('constructor6'),
                 'registrationSpan': span('registration6'),
                 'publicationSpan': span('publication6'),
                 'consumerSpans': [span('consumer6')]},
                {'selector': 9, 'key': [255, 3, 0], 'slot': 3,
                 'readerRva': 0xE3D9B0,
                 'descriptorConstructorSpan': span('constructor9'),
                 'registrationSpan': span('registration9'),
                 'publicationSpan': span('publication9'),
                 'consumerSpans': [span('consumer9')]},
            ],
            'tag5Framing': {
                'discriminant': {'byteOffset': 28, 'storage': 'signed i16', 'requiredValue': 5},
                'nativeEntry': {'cursorStartByteOffset': 64},
                'counts': [
                    {'byteOffset': offset, 'width': width}
                    for offset, width in zip(
                        [40, 44, 48, 52, 56, 60], [24, 52, 48, 28, 56, 56], strict=True
                    )
                ],
                'segmentOrder': [40, 44, 48, 52, 56, 60],
            },
            'countedPrefixCarrier': {'status': 'conditional'},
            'evidenceBoundary': {'runtimeReceipt': 'unresolved'},
        }
        contract['fixedBodyProfiles'] = marker17_native.fixed_body_profiles()
        for selector, key in ((2, [4, 0, 0]), (5, [5, 0, 0]), (7, [8, 0, 0])):
            contract['keyLiteralRanges'].append({'selector': selector, 'key': key, **span(f'key{selector}')})
            contract['selectedDefaultSlot3'].append({
                'selector': selector, 'key': key, 'slot': 3,
                'descriptorConstructorSpan': span('constructor6'),
                'registrationSpan': span('registration6'),
                'publicationSpan': span('publication6'), 'consumerSpans': [span('consumer6')],
            })
        contract_path = root / 'marker17.json'
        contract_path.write_text(json.dumps(contract), encoding='utf-8')
        selected = {
            'status': 'validated',
            'contractSha256': base_hash,
            'gameAssemblySha256': 'GA',
            'metadataSha256': 'MD',
            'unityPlayerSha256': unity_hash,
            'validationFailures': [],
        }
        return game_root, base_path, contract_path, selected

    def _validate(self, game_root, base_path, contract_path, selected, *, contract_hash=None):
        expected_contract_hash = contract_hash or hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()
        base_gate = Mock(return_value=selected)
        with (
            patch.object(marker17_native, 'CONTRACT_SHA256', expected_contract_hash),
            patch.object(base, 'DEFAULT_CONTRACT', base_path),
            patch.object(base, 'validate_streaming_field2_native_contract', base_gate),
        ):
            result = marker17_native.validate_marker17_native_contract(
                game_root=game_root, contract_path=contract_path,
            )
        return result, base_gate

    def assert_failed_closed(self, result, gate):
        self.assertEqual('validation_failed', result['status'])
        self.assertIsNone(result['profile'])
        self.assertIsNone(result['conditionalConsumer'])
        self.assertTrue(any(row['gate'] == gate for row in result['validationFailures']))

    def test_positive_synthetic_pe_and_mocked_base_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self._fixture(Path(directory))
            result, base_gate = self._validate(*args)
        self.assertEqual('validated', result['status'])
        self.assertEqual([24, 52, 48, 28, 56, 56], result['profile']['recordWidths'])
        self.assertEqual('opaque', result['profile']['fields'])
        self.assertEqual([], result['validationFailures'])
        base_gate.assert_called_once_with(game_root=args[0])

    def test_fixed_profile_tag_length_and_unread_gap_must_match_parser(self):
        for field, value in (('tag', 1), ('bodyLength', 68), ('opaqueUnreadRanges', [])):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                game_root, base_path, contract_path, selected = self._fixture(Path(directory))
                document = json.loads(contract_path.read_text())
                document['fixedBodyProfiles'][2][field] = value
                contract_path.write_text(json.dumps(document), encoding='utf-8')
                result, _ = self._validate(game_root, base_path, contract_path, selected)
                self.assert_failed_closed(result, 'fixed_body_profiles')

    def test_wrong_contract_hash_returns_before_base_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self._fixture(Path(directory))
            result, base_gate = self._validate(*args, contract_hash='WRONG')
        self.assert_failed_closed(result, 'contract_sha256')
        base_gate.assert_not_called()

    def test_missing_base_native_gate_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            selected = {'status': 'validation_failed', 'validationFailures': [{'gate': 'installed', 'actual': 'missing'}]}
            result, _ = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'base_native_gate')
        self.assertEqual('installed', result['baseValidationFailures'][0]['gate'])

    def test_wrong_base_contract_hash_fails_before_native_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            document = json.loads(contract_path.read_text())
            document['baseContract']['sha256'] = '00' * 32
            contract_path.write_text(json.dumps(document), encoding='utf-8')
            result, base_gate = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'base_contract_sha256')
        base_gate.assert_not_called()

    def test_wrong_selected_native_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            selected['metadataSha256'] = 'OTHER'
            result, _ = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'native_input:metadataSha256')

    def test_missing_explicit_unity_image_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self._fixture(Path(directory))
            (args[0].parent / 'UnityPlayer.dll').unlink()
            result, _ = self._validate(*args)
        self.assert_failed_closed(result, 'marker17_contract_inputs')

    def test_wrong_body_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            document = json.loads(contract_path.read_text())
            document['unityPlayerRanges'][0]['bodySha256'] = '00' * 32
            contract_path.write_text(json.dumps(document), encoding='utf-8')
            result, _ = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'fixtureBody.body_sha256')

    def test_wrong_file_offset_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            document = json.loads(contract_path.read_text())
            document['unityPlayerRanges'][0]['fileOffset'] += 1
            contract_path.write_text(json.dumps(document), encoding='utf-8')
            result, _ = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'fixtureBody.file_offset')

    def test_tampered_publication_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            unity = game_root.parent / 'UnityPlayer.dll'
            image = bytearray(unity.read_bytes())
            # selector6 publication RVA 0x1090 maps to raw offset 0x290.
            image[0x290] ^= 0xFF
            unity.write_bytes(image)
            changed_hash = hashlib.sha256(image).hexdigest().upper()
            document = json.loads(contract_path.read_text())
            document['nativeInputs']['unityPlayerSha256'] = changed_hash
            contract_path.write_text(json.dumps(document), encoding='utf-8')
            selected['unityPlayerSha256'] = changed_hash
            result, _ = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'selector6.publication.exact_bytes')

    def test_missing_constructor_span_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            document = json.loads(contract_path.read_text())
            del document['selectedDefaultSlot3'][1]['descriptorConstructorSpan']
            contract_path.write_text(json.dumps(document), encoding='utf-8')
            result, _ = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'marker17_contract_inputs')
        self.assertIn('descriptorConstructorSpan', result['validationFailures'][0]['actual'])

    def test_cross_section_range_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            document = json.loads(contract_path.read_text())
            document['unityPlayerRanges'][0].update(rva=0x11FE, fileOffset=0x3FE)
            contract_path.write_text(json.dumps(document), encoding='utf-8')
            result, _ = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'fixtureBody.bounded_range')

    def test_truncated_section_backing_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            game_root, base_path, contract_path, selected = self._fixture(Path(directory))
            unity = game_root.parent / 'UnityPlayer.dll'
            truncated = unity.read_bytes()[:0x212]
            unity.write_bytes(truncated)
            document = json.loads(contract_path.read_text())
            document['nativeInputs']['unityPlayerSha256'] = hashlib.sha256(truncated).hexdigest().upper()
            contract_path.write_text(json.dumps(document), encoding='utf-8')
            selected['unityPlayerSha256'] = document['nativeInputs']['unityPlayerSha256']
            result, _ = self._validate(game_root, base_path, contract_path, selected)
        self.assert_failed_closed(result, 'fixtureBody.bounded_range')


if __name__ == '__main__':
    unittest.main()
