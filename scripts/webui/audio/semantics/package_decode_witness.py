"""Selected AKPK entry to existing decoded-file comparisons, entirely offline.

This is a library used by recovery probes, not a second Audio command. Explicit
decoder paths and one supplied indexed word-match row define the comparison.
It never identifies a live file handle or promotes Event selection evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import wave

from scripts.game_data.wwise_package import decrypt_vfs_bytes, read_entry_bytes, read_header

SCHEMA = 'endfield.audio-package-selected-decode-witness.v1'
OBSERVATION_SCHEMA = 'endfield.audio-package-offline-decode-observations.v1'
BOUNDARY = ('Offline selected-entry decode compared with an explicitly selected decoded file. '
            'The AKPK header and current sampled encoded words bind this candidate to the supplied word witness; '
            'no full-package authentication or complete overlay sweep is claimed. PCM equality binds only these '
            'offline bytes, not the live backing filename, game codec instance, Event selection or audible output.')


def _fingerprint(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def _file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def read_matched_entry(match, *, max_entry_bytes=64 << 20):
    """Recheck the header, unique typed row and all compared words before reading.

    A sparse match remains conditional even though the selected offline entry
    can now be read in full. Matching samples do not authenticate its remainder.
    """
    if (not match.get('sampleCount') or match.get('matchedWordCount') != match['sampleCount']
            or len(match.get('comparisons', [])) != match['sampleCount']):
        raise ValueError('selected entry requires a complete encoded-word comparison')
    path = Path(match['physicalPath'])
    offset, length = int(match['payloadOffset']), int(match['payloadBytes'])
    before = _fingerprint(path)
    if offset < 0 or length < 0 or offset + length > before[0]:
        raise ValueError('selected logical payload outside physical source')
    with path.open('rb') as stream:
        stream.seek(offset)
        header = read_header(stream, length)
        stream.seek(offset)
        if hashlib.sha256(stream.read(header['headerBytes'])).hexdigest() != match['headerSha256']:
            raise ValueError('selected package header differs from word witness')
        rows = [entry for entry in header['entries']
                if entry.sector == match['sector'] and entry.key == int(match['key'])
                and entry.byte_length == int(match['byteLength'])
                and entry.byte_offset == int(match['byteOffset'])
                and entry.block_bytes == match['blockBytes'] and entry.language == match['language']]
        if len(rows) != 1:
            raise ValueError(f'selected package row is not unique: matches={len(rows)}')
        entry = rows[0]
        if entry.key & 0xffffffff != match['keyLow']:
            raise ValueError('selected entry low key differs from word witness')
        encoded = read_entry_bytes(stream, offset, length, entry, max_entry_bytes=max_entry_bytes)
    if _fingerprint(path) != before:
        raise ValueError('selected package changed during entry read')
    for comparison in match['comparisons']:
        at = int(comparison['relativeOffset'])
        if at < 0 or at + 4 > len(encoded):
            raise ValueError('selected word comparison outside entry')
        word = f'{int.from_bytes(encoded[at:at + 4], "little"):08x}'
        if comparison['comparison'] != 'matched' or word != comparison['observedWord'] or word != comparison['indexedWord']:
            raise ValueError('selected encoded bytes differ from word witness')
    return encoded


def _run(command):
    result = subprocess.run([str(value) for value in command], capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise ValueError(f'offline decoder failed: exit={result.returncode}, detail={result.stderr[:400]}')
    return result.stdout


def pcm_receipt(path):
    """Hash interleaved PCM frames, independent of WAV metadata/chunk layout."""
    digest, byte_count = hashlib.sha256(), 0
    with wave.open(str(path), 'rb') as source:
        if source.getcomptype() != 'NONE':
            raise ValueError('comparison WAV is not uncompressed PCM')
        info = {'channels': source.getnchannels(), 'sampleRate': source.getframerate(),
                'samples': source.getnframes(), 'sampleBytes': source.getsampwidth()}
        while data := source.readframes(65536):
            digest.update(data)
            byte_count += len(data)
    if byte_count != info['channels'] * info['samples'] * info['sampleBytes']:
        raise ValueError('comparison WAV has truncated PCM frames')
    return {**info, 'pcmBytes': byte_count, 'pcmSha256': digest.hexdigest()}


def compare_selected_entry(match, decoded_file, decoder, comparison_decoder, work_dir,
                           *, encryption='keyLowXor', max_entry_bytes=64 << 20,
                           retain_entry_bytes=False):
    """Decode one bounded current candidate and compare its existing-file PCM.

    ``encryption`` is an explicit offline selection, not inferred live flags.
    vgmstream's ``-i`` decodes the complete stream once, ignoring loop replay.
    ffmpeg preserves channels/rate while converting the existing file to PCM16.
    """
    if encryption not in ('keyLowXor', 'none'):
        raise ValueError('unsupported selected-entry encryption mode')
    decoded_file, decoder, comparison_decoder, work_dir = map(Path, (decoded_file, decoder, comparison_decoder, work_dir))
    source_before = _fingerprint(decoded_file)
    tools_before = [(path, _fingerprint(path), _file_hash(path)) for path in (decoder, comparison_decoder)]
    encoded = read_matched_entry(match, max_entry_bytes=max_entry_bytes)
    clear = bytearray(encoded)
    if encryption == 'keyLowXor':
        decrypt_vfs_bytes(clear, 0, len(clear), match['keyLow'])
    if len(clear) < 12 or clear[:4] != b'RIFF' or clear[8:12] != b'WAVE' or int.from_bytes(clear[4:8], 'little') + 8 != len(clear):
        raise ValueError('selected decrypted entry is not a complete RIFF/WAVE extent')
    work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='selected-decode-', dir=work_dir) as temporary:
        temporary = Path(temporary)
        wem, fresh, existing = (temporary / name for name in ('entry.wem', 'fresh.wav', 'existing.wav'))
        wem.write_bytes(clear)
        metadata = json.loads(_run([decoder, '-I', wem]))
        _run([decoder, '-i', '-o', fresh, wem])
        _run([comparison_decoder, '-v', 'error', '-nostdin', '-y', '-i', decoded_file,
              '-map', '0:a:0', '-c:a', 'pcm_s16le', '-f', 'wav', existing])
        fresh_pcm, existing_pcm = pcm_receipt(fresh), pcm_receipt(existing)
    source_sha = _file_hash(decoded_file)
    if _fingerprint(decoded_file) != source_before:
        raise ValueError('existing decoded file changed during comparison')
    if any(_fingerprint(path) != before for path, before, _ in tools_before):
        raise ValueError('offline decoder executable changed during comparison')
    receipt = {'schema': SCHEMA, 'status': 'offlineSelectedEntryComparison',
               'fileName': match['fileName'], 'sector': match['sector'], 'key': match['key'],
               'keyLow': match['keyLow'], 'byteLength': match['byteLength'], 'byteOffset': match['byteOffset'],
               'blockBytes': match['blockBytes'], 'language': match['language'],
               'physicalPath': match['physicalPath'], 'payloadOffset': match['payloadOffset'],
               'payloadBytes': match['payloadBytes'], 'headerSha256': match['headerSha256'],
               'sampledWordCount': match['sampleCount'], 'encryption': encryption,
               'encodedSha256': hashlib.sha256(encoded).hexdigest(), 'wemSha256': hashlib.sha256(clear).hexdigest(),
               'decodedFile': str(decoded_file), 'decodedFileSha256': source_sha,
               'decoder': str(decoder), 'decoderSha256': tools_before[0][2],
               'comparisonDecoder': str(comparison_decoder), 'comparisonDecoderSha256': tools_before[1][2],
               'decoderMetadata': metadata, 'selectedEntryPcm': fresh_pcm, 'existingDecodedPcm': existing_pcm,
               'pcmBytesEqual': fresh_pcm == existing_pcm, 'evidenceBoundary': BOUNDARY}
    if retain_entry_bytes:
        base = work_dir / f'{match["sector"]}-{match["key"]}'
        encoded_path, wem_path = base.with_suffix('.encoded'), base.with_suffix('.wem')
        encoded_path.write_bytes(encoded)
        wem_path.write_bytes(clear)
        receipt.update(encodedPath=str(encoded_path), wemPath=str(wem_path))
    return receipt


class _ReceiptError(ValueError):
    def __init__(self, check, detail):
        super().__init__(detail)
        self.check = check


def _require(condition, check, detail):
    if not condition:
        raise _ReceiptError(check, detail)


def _json_file(path, max_bytes=8 << 20):
    before = _fingerprint(path)
    _require(before[0] <= max_bytes, 'receiptJsonBound', f'JSON bytes={before[0]}, limit={max_bytes}')
    raw = path.read_bytes()
    _require(_fingerprint(path) == before, 'receiptJsonContinuity', 'JSON input changed while reading')
    return raw, json.loads(raw)


def _match_identity(match):
    names = ('fileName', 'physicalPath', 'payloadOffset', 'payloadBytes', 'headerSha256', 'sector',
             'key', 'keyLow', 'byteLength', 'byteOffset', 'blockBytes', 'language', 'sampleCount',
             'matchedWordCount', 'distinctSampledByteCount', 'comparisons')
    return json.dumps({name: match[name] for name in names}, sort_keys=True, separators=(',', ':'))


def project_decode_receipt(current_word_witness, report_path, *, max_rows=32,
                           max_entry_bytes=64 << 20, max_total_bytes=256 << 20):
    """Admit a historical offline decode receipt against current exact inputs.

    This checks receipt/source-witness continuity and the complete selected
    encoded/WEM/decoded-file bytes. It does not invoke either decoder again.
    PCM metadata and equality are the historical decoder result in the receipt;
    the explicit status keeps that result distinct from captured game output.
    A failure empties only this optional child, never the current word witness.
    """
    boundary = (BOUNDARY + ' Decoder results are historical recorded results; this refresh checks their '
                'selected inputs and does not repeat decoding or observe game-side PCM.')
    base = {'schema': OBSERVATION_SCHEMA, 'evidenceBoundary': boundary}
    try:
        _require(current_word_witness.get('schema') == 'endfield.audio-package-read-word-witness.v1'
                 and current_word_witness.get('status') == 'conditionalIndexedComparison',
                 'currentWordWitnessAdmission', 'current admitted indexed-word witness required')
        raw_report, report = _json_file(Path(report_path))
        _require(report.get('schema') == SCHEMA and isinstance(report.get('entries'), list),
                 'receiptSchema', 'selected-decode receipt schema/entries differ')
        raw_source, source = _json_file(Path(report['sourceWordWitness']))
        _require(hashlib.sha256(raw_source).hexdigest() == report['sourceWordWitnessSha256'],
                 'sourceWordWitnessDigest', 'referenced generated word-witness bytes differ from receipt digest')
        _require(source.get('schema') == current_word_witness['schema']
                 and source.get('status') == current_word_witness['status']
                 and source.get('indexSha256') == current_word_witness.get('indexSha256'),
                 'sourceWordWitnessIdentity', 'referenced word-witness schema/status/index differs from current witness')
        current_matches = {_match_identity(match): match for match in current_word_witness['matches']}
        _require(set(_match_identity(match) for match in source['matches']) == set(current_matches),
                 'sourceWordWitnessRows', 'referenced candidate geometry/header/sample rows differ from current witness')
        entries = report['entries']
        _require(0 < len(entries) <= max_rows, 'receiptRowBound', f'rows={len(entries)}, limit={max_rows}')
        consumed, rows, seen = 0, [], set()

        def checked_file(path, digest, *, load=False, expected_length=None):
            nonlocal consumed
            path = Path(path)
            before = _fingerprint(path)
            consumed += before[0]
            _require(consumed <= max_total_bytes, 'selectedInputByteBudget', f'bytes={consumed}, limit={max_total_bytes}')
            if expected_length is not None:
                _require(before[0] == expected_length <= max_entry_bytes, 'selectedEntryLength',
                         f'{path.name}: actual={before[0]}, expected={expected_length}, limit={max_entry_bytes}')
            data = path.read_bytes() if load else None
            actual = hashlib.sha256(data).hexdigest() if load else _file_hash(path)
            _require(actual == digest, 'selectedInputDigest', f'{path.name}: expected={digest}, actual={actual}')
            _require(_fingerprint(path) == before, 'selectedInputContinuity', f'{path.name} changed while reading')
            return data

        for receipt in entries:
            _require(receipt.get('schema') == SCHEMA and receipt.get('status') == 'offlineSelectedEntryComparison',
                     'entryReceiptSchema', 'entry is not an offline selected-entry comparison')
            names = ('fileName', 'physicalPath', 'payloadOffset', 'payloadBytes', 'headerSha256',
                     'sector', 'key', 'keyLow', 'byteLength', 'byteOffset', 'blockBytes', 'language')
            matches = [match for match in current_matches.values()
                       if all(receipt[name] == match[name] for name in names)]
            _require(len(matches) == 1, 'entryCandidateIdentity', f'key={receipt.get("key")}: candidates={len(matches)}')
            match = matches[0]
            identity = _match_identity(match)
            _require(identity not in seen, 'entryReceiptUniqueness', 'duplicate selected candidate receipt')
            seen.add(identity)
            _require(receipt['sampledWordCount'] == match['sampleCount'] == match['matchedWordCount']
                     and len(match['comparisons']) == match['sampleCount'],
                     'entrySampleIdentity', 'sample count/comparison completeness differs')
            length = int(receipt['byteLength'])
            encoded = checked_file(receipt['encodedPath'], receipt['encodedSha256'], load=True, expected_length=length)
            wem = checked_file(receipt['wemPath'], receipt['wemSha256'], load=True, expected_length=length)
            for comparison in match['comparisons']:
                at = int(comparison['relativeOffset'])
                _require(0 <= at <= length - 4, 'entrySampleExtent', 'sample DWORD outside selected entry')
                word = f'{int.from_bytes(encoded[at:at + 4], "little"):08x}'
                _require(comparison['comparison'] == 'matched'
                         and word == comparison['observedWord'] == comparison['indexedWord'],
                         'entrySampleBytes', 'retained encoded bytes differ from current compared DWORD')
            clear = bytearray(encoded)
            _require(receipt['encryption'] in ('none', 'keyLowXor'), 'entryEncryption', 'unsupported recorded encryption mode')
            if receipt['encryption'] == 'keyLowXor':
                decrypt_vfs_bytes(clear, 0, length, receipt['keyLow'])
            _require(clear == wem, 'entryDecryption', 'retained WEM differs from selected-entry decrypt')
            _require(length >= 12 and wem[:4] == b'RIFF' and wem[8:12] == b'WAVE'
                     and int.from_bytes(wem[4:8], 'little') + 8 == length,
                     'entryWaveExtent', 'retained WEM RIFF/WAVE extent does not close')
            checked_file(receipt['decodedFile'], receipt['decodedFileSha256'])
            fresh, existing = receipt['selectedEntryPcm'], receipt['existingDecodedPcm']
            for pcm in (fresh, existing):
                for name in ('channels', 'sampleRate', 'samples', 'sampleBytes', 'pcmBytes'):
                    _require(type(pcm[name]) is int and pcm[name] > 0, 'recordedPcmMetadata', f'invalid recorded {name}')
                _require(pcm['channels'] * pcm['samples'] * pcm['sampleBytes'] == pcm['pcmBytes']
                         and len(pcm['pcmSha256']) == 64, 'recordedPcmMetadata', 'recorded PCM extent/digest is invalid')
            _require(type(receipt['pcmBytesEqual']) is bool and receipt['pcmBytesEqual'] == (fresh == existing),
                     'recordedPcmEquality', 'recorded equality differs from recorded PCM metadata/digests')
            metadata = receipt['decoderMetadata']
            _require(metadata['channels'] == fresh['channels'] and metadata['sampleRate'] == fresh['sampleRate']
                     and metadata['numberOfSamples'] == fresh['samples'],
                     'recordedDecoderMetadata', 'decoder metadata differs from recorded PCM')
            rows.append({'fileName': receipt['fileName'], 'sector': receipt['sector'], 'key': receipt['key'],
                         'byteLength': receipt['byteLength'], 'sampledWordCount': receipt['sampledWordCount'],
                         'decodedFile': receipt['decodedFile'], 'encoding': metadata.get('encoding'),
                         'channels': fresh['channels'], 'sampleRate': fresh['sampleRate'], 'samples': fresh['samples'],
                         'sampleBytes': fresh['sampleBytes'], 'duration': fresh['samples'] / fresh['sampleRate'],
                         'pcmBytesEqual': receipt['pcmBytesEqual'], 'encodedSha256': receipt['encodedSha256'],
                         'wemSha256': receipt['wemSha256'], 'decodedFileSha256': receipt['decodedFileSha256']})
        return {**base, 'status': 'historicalOfflineSelectedEntryComparison', 'currentInputsMatch': True,
                'receiptSha256': hashlib.sha256(raw_report).hexdigest(), 'selectedInputBytesChecked': consumed,
                'entryCount': len(rows), 'pcmEqualEntryCount': sum(row['pcmBytesEqual'] for row in rows),
                'rows': rows, 'rowsTruncated': False, 'rowLimit': max_rows}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {**base, 'status': 'unavailable', 'currentInputsMatch': False, 'entryCount': 0, 'rows': [],
                'diagnostics': [{'check': getattr(error, 'check', 'receiptInput'), 'detail': str(error)[:400]}]}
