"""Sweep STMG framing from an authenticated available-package receipt.

Reads bounded bank section headers and settings bytes, never media sections.
The VFS audit's input-set fingerprint and source/build pins must still match.
Results are generated reports; no effective runtime parameters are published.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

from scripts.common import sha256_file_upper
from scripts.game_data.corpus_common import atomic_write_text, validate_provenance
from scripts.game_data.wwise_bank_settings import BankSettingsError, read_settings
from scripts.game_data.wwise_package import decrypt_vfs_bytes, read_header
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.wwise-bank-settings-corpus.v1'


def _require(check, source, expected, actual):
    if actual != expected:
        error = ValueError(f'{check}: {source}: expected {expected}; actual {actual}')
        error.diagnostic = dict(check=check, source=str(source), expected=expected, actual=actual)
        raise error


def _fingerprint(row):
    path = Path(row['path'])
    _require('source-length', path, row['length'], path.stat().st_size)
    _require('source-sha256', path, row['sha256'].upper(), sha256_file_upper(path))


def validate_receipt(receipt, expected_input_set):
    expected = expected_input_set.upper()
    if len(expected) != 64 or any(c not in '0123456789ABCDEF' for c in expected):
        raise ValueError('expected input-set SHA256 must be 64 hexadecimal characters')
    _require('package-receipt-schema', 'receipt', 'endfield.wwise-package-corpus.v1', receipt.get('schema'))
    _require('package-receipt-status', 'receipt', 'complete', receipt.get('status'))
    _require('package-input-set', 'receipt', expected, str(receipt.get('inputSetSha256', '')).upper())
    p = receipt['provenance']
    for key in ['outer', 'ledger']:
        _fingerprint(p[key])
    outer = json.loads(Path(p['outer']['path']).read_bytes())
    with gzip.open(p['ledger']['path'], 'rt', encoding='utf-8') as stream:
        header = json.loads(stream.readline())
    failures, _ = validate_provenance(outer, header, Path(p['ledger']['path']), expected)
    if failures:
        error = ValueError('VFS provenance failed')
        error.diagnostic = failures[0]
        raise error
    for key in ['sourceFingerprints', 'buildFingerprints']:
        normalized = lambda rows: [(row['path'], row['length'], row['sha256'].upper(), row.get('role')) for row in rows]
        _require('package-source-pins', key, normalized(outer[key]), normalized(p[key]))
        for row in p[key]:
            _fingerprint(row)
    catalogs = set()
    for key in ['primaryAssets', 'fallbackAssets']:
        root = Path(outer[key]) / 'VFS'
        catalogs.update(str(path.resolve()).casefold() for path in root.glob('*/*.blc'))
    _require('catalog-roster', 'VFS', sorted(p['blcPaths']), sorted(catalogs))
    for row in receipt.get('excludedPackages', []):
        _require('excluded-package-now-present', row.get('path'), [False]*len(row['candidatePaths']),
                 [Path(path).is_file() for path in row['candidatePaths']])
    return outer


def _read_clear(stream, entry, package_offset, relative, length):
    if relative < 0 or length < 0 or relative + length > entry.byte_length:
        raise ValueError('bank read exceeds selected entry')
    stream.seek(package_offset + entry.byte_offset + relative)
    raw = bytearray(stream.read(length))
    if len(raw) != length:
        raise ValueError('short physical bank read')
    decrypt_vfs_bytes(raw, 0, length, entry.key & 0xffffffff, data_offset=relative)
    return bytes(raw)


def inspect_bank(stream, entry, *, package_offset):
    at, version, settings = 0, None, []
    count = 0
    while at < entry.byte_length:
        tag, size = struct.unpack('<4sI', _read_clear(stream, entry, package_offset, at, 8))
        if size > entry.byte_length-at-8:
            raise ValueError(f'section {tag!r} exceeds bank entry at {at}')
        if at == 0:
            if tag != b'BKHD' or size < 8:
                raise ValueError('bank does not begin with a complete BKHD identity')
            version, bank_id = struct.unpack('<2I', _read_clear(stream, entry, package_offset, 8, 8))
            _require('bank-key-identity', str(entry.key), entry.key, bank_id)
        if tag == b'STMG':
            body = _read_clear(stream, entry, package_offset, at+8, size)
            settings.append(dict(sectionOffset=at, bytes=size, sha256=hashlib.sha256(body).hexdigest(),
                                 settings=read_settings(body, bank_version=version)))
        at += 8+size
        count += 1
        if count > 65535:
            raise ValueError('section count exceeds bounded reader limit')
    return dict(bankKey=entry.key, bankVersion=version, bytesFramed=at,
                sectionCount=count, settingsSections=settings)


def sweep(receipt_path: Path, *, expected_input_set: str):
    receipt = json.loads(receipt_path.read_bytes())
    receipt_start = sha256_file_upper(receipt_path)
    outer = validate_receipt(receipt, expected_input_set)
    output = dict(schema=SCHEMA, status='complete', inputSetSha256=expected_input_set.upper(),
                  packageReceipt=dict(path=str(receipt_path), sha256=receipt_start),
                  bankCount=0, sectionCount=0, settingsSectionCount=0, entries=[])
    for package in receipt['packages']:
        if not package['counts']['banks']:
            continue
        path = Path(package['physicalPath'])
        offset, length = int(package['payloadOffset']), int(package['payloadBytes'])
        before = path.stat()
        with path.open('rb') as stream:
            stream.seek(offset)
            digest, remaining = hashlib.sha256(), length
            while remaining:
                raw = stream.read(min(8 << 20, remaining))
                if not raw:
                    raise ValueError(f'short package payload: {path}')
                digest.update(raw);remaining -= len(raw)
            _require('package-payload-sha256', package['path'], package['payloadSha256'].upper(), digest.hexdigest().upper())
            stream.seek(offset)
            header = read_header(stream, length)
            actual = [(r.sector, str(r.key), r.language, str(r.byte_length), str(r.byte_offset)) for r in header['entries']]
            expected = [(r['sector'], r['key'], r['language'], r['byteLength'], r['byteOffset']) for r in package['entries']]
            _require('package-entries', package['path'], expected, actual)
            for entry in header['entries']:
                if entry.sector != 'banks':
                    continue
                bank = inspect_bank(stream, entry, package_offset=offset)
                output['bankCount'] += 1;output['sectionCount'] += bank['sectionCount']
                for section in bank['settingsSections']:
                    output['settingsSectionCount'] += 1
                    output['entries'].append(dict(package=package['path'], physicalPath=str(path),
                        bankKey=entry.key, bankVersion=bank['bankVersion'], **section))
        after = path.stat()
        _require('package-changed-during-read', path, (before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))
    _require('bank-roster-count', 'corpus', receipt['summary']['sectorCounts']['banks'], output['bankCount'])
    _require('package-receipt-changed', receipt_path, receipt_start, sha256_file_upper(receipt_path))
    for key in ['sourceFingerprints', 'buildFingerprints']:
        for row in outer[key]:
            _fingerprint(row)
    output['evidenceBoundary'] = 'Authenticated available bank-sector roster and exact v150 settings framing; '
    output['evidenceBoundary'] += 'stored parameter/transition/binding rows do not establish current runtime values or output topology.'
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-receipt', required=True, type=Path)
    parser.add_argument('--expected-input-set-sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    dest = args.output.resolve()
    if REPO_ROOT / 'reports' not in dest.parents:
        parser.error('--output must be under reports/')
    try:
        report = sweep(args.package_receipt, expected_input_set=args.expected_input_set_sha256)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = dict(schema=SCHEMA, status='failed', entries=[],
                      diagnostic=getattr(error, 'diagnostic', dict(check='bankSettingsCorpus', actual=str(error)[:320])))
    atomic_write_text(dest, json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['entries']}, indent=2))
    return 0 if report['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
