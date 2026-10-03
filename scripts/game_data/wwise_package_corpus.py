"""Authenticate the available AKPK roster and inventory typed entry identities.

Reads installed bytes without extracting media. The shared header reader owns
framing; this gate owns current-roster coverage, package byte joins and duplicate
identity diagnostics. It does not choose among duplicate media or decode PCM.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from scripts.common import ROOT
from scripts.game_data.memorypack.corpus_gate import (
    CensusGateError, _atomic_write_json, _chunk_selection_snapshot,
    _discover_blc_paths, _fingerprint, _guard_output_path, _read_outer_and_ledger,
    _parser_source_snapshots, _snapshot_pinned_files,
)
from scripts.game_data.wwise_package import read_bank_identity, read_header

SCHEMA = 'endfield.wwise-package-corpus.v1'
BOUNDARY = (
    'Exact available-package bytes and typed header entries from the selected '
    'current VFS roster. Bank-sector keys match the stored BKHD bank ID under '
    'the explicit offline bank-key XOR profile; only that header prefix is parsed. '
    'Excluded packages remain absent. Equal keys in separate '
    'packages are candidates, not a runtime precedence rule or a decoded-file '
    'binding. Language IDs join only their own package table under the explicit '
    'Windows UTF-16LE header profile; these stored labels do not establish spoken '
    'language or runtime language selection. No media decode, Event '
    'selection, live file handle, codec instance or audibility is established.'
)


def require(check, source, expected, actual):
    if expected != actual:
        raise CensusGateError(check, source=str(source), expected=expected, actual=actual)


def excluded_snapshot(rows, outer):
    """A formerly absent package cannot silently remain excluded after install."""
    result = []
    for row in rows:
        directory, chunk = row.get('hashDirectory'), row.get('chunkFile')
        if not isinstance(directory, str) or not re.fullmatch(r'[0-9A-Fa-f]{8}', directory):
            raise ValueError('invalid excluded package hash directory')
        if not isinstance(chunk, str) or not re.fullmatch(r'[0-9A-Fa-f]{32}\.chk', chunk):
            raise ValueError('invalid excluded package chunk name')
        paths = [Path(outer[key]) / 'VFS' / directory / chunk for key in ('primaryAssets', 'fallbackAssets')]
        require('excluded-package-now-present', row['virtualPath'], [False, False], [p.is_file() for p in paths])
        result.append({'block': row['blockName'], 'path': row['virtualPath'],
                       'status': row['boundaryStatus'], 'candidatePaths': [p.as_posix() for p in paths]})
    return result


def inspect_package(row):
    """Read a complete unencrypted VFS payload once, plus its bounded header."""
    path = Path(row['physicalChunkPath'])
    offset, length = row['offset'], row['length']
    if type(offset) is not int or type(length) is not int or offset < 0 or length < 24:
        raise ValueError(f'invalid package extent: {row["virtualPath"]}')
    require('package-vfs-encryption', row['virtualPath'], False, row.get('encrypted'))
    expected_md5 = str(row.get('recomputedFileDataMd5', '')).upper()
    if not re.fullmatch(r'[0-9A-F]{32}', expected_md5):
        raise ValueError(f'package lacks verified MD5: {row["virtualPath"]}')
    require('package-declared-md5', row['virtualPath'], expected_md5,
            str(row.get('declaredFileDataMd5LittleEndianHex', '')).upper())
    require('package-ledger-length', row['virtualPath'], length, row.get('actualBytesRead'))
    before = path.stat()
    if offset + length > before.st_size:
        raise ValueError(f'package outside physical chunk: {row["virtualPath"]}')
    with path.open('rb') as stream:
        stream.seek(offset)
        header = read_header(stream, length)
        stream.seek(offset)
        header_sha = hashlib.sha256(stream.read(header['headerBytes'])).hexdigest().upper()
        bank_identities = {ordinal: read_bank_identity(stream, offset, length, entry)
                           for ordinal, entry in enumerate(header['entries'])
                           if entry.sector == 'banks'}
        stream.seek(offset)
        md5, sha256, remaining = hashlib.md5(), hashlib.sha256(), length
        while remaining:
            raw = stream.read(min(8 << 20, remaining))
            if not raw:
                raise ValueError(f'truncated package: {row["virtualPath"]}')
            md5.update(raw); sha256.update(raw); remaining -= len(raw)
    after = path.stat()
    require('package-changed-during-read', path, [before.st_size, before.st_mtime_ns],
            [after.st_size, after.st_mtime_ns])
    require('package-current-md5', row['virtualPath'], expected_md5, md5.hexdigest().upper())
    language_labels = {row['id']: row['label'] for row in header['languageTable']['rows']}
    entries = [{'ordinal': ordinal, 'sector': entry.sector, 'key': str(entry.key),
                'language': entry.language, 'languageLabel': language_labels.get(entry.language),
                'byteLength': str(entry.byte_length),
                'byteOffset': str(entry.byte_offset), 'blockOffset': str(entry.block_offset),
                'blockBytes': entry.block_bytes,
                **({'bankHeader': bank_identities[ordinal]} if ordinal in bank_identities else {})}
               for ordinal, entry in enumerate(header['entries'])]
    return {'block': row['blockName'], 'path': row['virtualPath'],
            'physicalPath': path.resolve().as_posix(), 'payloadOffset': str(offset),
            'payloadBytes': str(length), 'payloadMd5': expected_md5,
            'payloadSha256': sha256.hexdigest().upper(), 'headerSha256': header_sha,
            'headerBytes': header['headerBytes'], 'encryptedHeader': header['encryptedHeader'],
            'counts': header['counts'], 'entries': entries, 'languageTable': header['languageTable'],
            'physicalStat': {'length': after.st_size, 'mtimeNs': str(after.st_mtime_ns)}}


def summarize(packages):
    """Keep typed and low-word collisions distinct; never pick a winner."""
    sectors, blocks, languages, sizes, bank_versions = (Counter() for _ in range(5))
    identities, low_words = defaultdict(list), defaultdict(set)
    entry_count = 0
    language_labels = Counter()
    language_unresolved = 0
    for package in packages:
        blocks[package['block']] += 1
        for entry in package['entries']:
            entry_count += 1
            sectors[entry['sector']] += 1
            languages[str(entry['language'])] += 1
            if isinstance(entry.get('languageLabel'), str):
                language_labels[entry['languageLabel']] += 1
            else:
                language_unresolved += 1
            sizes[str(entry['blockBytes'])] += 1
            if entry.get('bankHeader'):
                bank_versions[str(entry['bankHeader']['bankVersion'])] += 1
            identity = (entry['sector'], entry['key'], entry['language'])
            identities[identity].append({'block': package['block'], 'path': package['path'], 'ordinal': entry['ordinal']})
            low_words[(entry['sector'], int(entry['key']) & 0xffffffff, entry['language'])].add(entry['key'])
    duplicates = [{'sector': key[0], 'key': key[1], 'language': key[2], 'entries': refs}
                  for key, refs in sorted(identities.items()) if len(refs) > 1]
    low_collisions = [{'sector': key[0], 'keyLow': key[1], 'language': key[2], 'fullKeys': sorted(keys, key=int)}
                      for key, keys in sorted(low_words.items()) if len(keys) > 1]
    return {'packageCount': len(packages), 'entryCount': entry_count,
            'sectorCounts': dict(sorted(sectors.items())), 'packageBlockCounts': dict(sorted(blocks.items())),
            'languageValueCounts': dict(sorted(languages.items())),
            'languageLabelCounts': dict(sorted(language_labels.items())),
            'unresolvedLanguageLabelCount': language_unresolved,
            'blockBytesCounts': dict(sorted(sizes.items())),
            'bankHeaderIdentityCount': sum(bank_versions.values()),
            'bankVersionCounts': dict(sorted(bank_versions.items())),
            'distinctTypedKeyCount': len(identities), 'repeatedTypedKeyCount': len(duplicates),
            'repeatedTypedKeyEntryCount': sum(len(row['entries']) for row in duplicates),
            'lowWordCollisionCount': len(low_collisions)}, duplicates, low_collisions


def build(outer_path, ledger_path, expected_input_set_sha256):
    outer, _, rows, provenance = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected_input_set_sha256)
    selected, excluded, shadowed = [], [], []
    for row in rows:
        if not str(row.get('virtualPath', '')).lower().endswith('.pck'):
            continue
        require('package-row-input-set', row['virtualPath'], expected_input_set_sha256.upper(), row.get('inputSetSha256'))
        status = row.get('boundaryStatus')
        if status == 'boundary_verified': selected.append(row)
        elif status in ('excluded_missing_audio', 'excluded_missing_voice'): excluded.append(row)
        elif status == 'shadowed': shadowed.append({'block': row.get('blockName'), 'path': row['virtualPath']})
        else: raise ValueError(f'unadmitted package status: {row["virtualPath"]}: {status}')
    if not selected:
        raise ValueError('no available packages in authenticated roster')
    selected.sort(key=lambda row: (row['blockName'], row['virtualPath']))
    keys = [(row['blockName'], row['virtualPath']) for row in selected]
    require('duplicate-roster-identity', 'package roster', len(keys), len(set(keys)))
    resolutions = _chunk_selection_snapshot(selected, outer)
    exclusions = excluded_snapshot(excluded, outer)
    parser = _parser_source_snapshots(Path(__file__))
    # The shared closure helper follows the MemoryPack package only. AKPK's
    # byte reader lives beside this gate and must be pinned explicitly too.
    parser.append(_fingerprint(Path(__file__).with_name('wwise_package.py')))
    packages = [inspect_package(row) for row in selected]
    # Full byte hashes were computed during inspection. Recheck source selection,
    # catalog/build pins and physical metadata before publishing the inventory.
    for package in packages:
        stat = Path(package['physicalPath']).stat()
        require('package-changed-before-publication', package['path'], package['physicalStat'],
                {'length': stat.st_size, 'mtimeNs': str(stat.st_mtime_ns)})
    for role in ('sourceFingerprints', 'buildFingerprints'):
        require('package-provenance-drift', role, provenance[role],
                _snapshot_pinned_files(outer[role], label=role))
    for role in ('outer', 'ledger'):
        require('package-roster-drift', role, provenance[role], _fingerprint(Path(provenance[role]['path'])))
    require('package-catalog-set-drift', 'catalogs', provenance['blcPaths'], _discover_blc_paths(outer))
    require('package-selection-drift', 'chunks', resolutions, _chunk_selection_snapshot(selected, outer))
    require('package-exclusion-drift', 'excluded', exclusions, excluded_snapshot(excluded, outer))
    require('package-reader-drift', 'parser', parser, [_fingerprint(Path(row['path'])) for row in parser])
    summary, duplicates, collisions = summarize(packages)
    return {'schema': SCHEMA, 'status': 'complete', 'inputSetSha256': outer['inputSetSha256'],
            'evidenceBoundary': BOUNDARY, 'provenance': {**provenance, 'parser': parser,
                'selectedChunkResolution': resolutions}, 'summary': {**summary,
                'excludedPackageCount': len(exclusions), 'shadowedPackageCount': len(shadowed)},
            'packages': packages, 'excludedPackages': exclusions, 'shadowedPackages': shadowed,
            'repeatedTypedKeys': duplicates, 'lowWordCollisions': collisions}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outer', type=Path, default=ROOT / 'reports/animestudio/vfs_understanding_latest.json')
    parser.add_argument('--ledger', type=Path, default=ROOT / 'reports/animestudio/vfs_understanding_files_latest.jsonl.gz')
    parser.add_argument('--expected-input-set-sha256', required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/audio/package_corpus_current.json')
    args = parser.parse_args(argv)
    outer = json.loads(args.outer.read_bytes())
    _guard_output_path(args.output, [args.outer, args.ledger, Path(__file__),
                                   *(Path(outer[key]) for key in ('primaryAssets', 'fallbackAssets'))])
    if not any(args.output.resolve().is_relative_to(ROOT / name) for name in ('reports', 'tmp', 'scratch')):
        parser.error('generated output must be under reports/, tmp/ or scratch/')
    try:
        report = build(args.outer, args.ledger, args.expected_input_set_sha256)
    except (OSError, ValueError) as error:
        diagnostic = error.diagnostic if isinstance(error, CensusGateError) else {
            'code': type(error).__name__, 'source': str(args.outer), 'detail': str(error)[:800]}
        print(json.dumps({'status': 'failed', 'diagnostic': diagnostic}, ensure_ascii=True))
        return 1
    _atomic_write_json(args.output, report)
    print(json.dumps({'status': report['status'], **report['summary'], 'output': str(args.output)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
