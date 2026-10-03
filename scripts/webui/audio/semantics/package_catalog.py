"""Compact static package inventory; no runtime or decoded-media joins."""
import json
import re
from pathlib import Path

from scripts.common import ROOT
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _atomic_write_json
from scripts.game_data.wwise_package_corpus import BOUNDARY, SCHEMA as CORPUS_SCHEMA, build

SCHEMA = 'endfield.audio-package-catalog.v1'


def rebuild_published(index_path: Path, *, language: str, index_schema: int) -> dict:
    """Revalidate a previously selected roster during a full semantic rebuild.

    Only its expected roster identity is reused. Package rows and counters are
    read again through the complete raw gate; a changed build cannot carry stale
    inventory forward. No prior catalog means no implicit package scan.
    """
    try:
        previous = json.loads(index_path.read_bytes())
    except FileNotFoundError:
        return {'schema': SCHEMA, 'status': 'notRequested', 'evidenceKind': 'static'}
    except (OSError, ValueError) as error:
        return {'schema': SCHEMA, 'status': 'unavailable', 'evidenceKind': 'static',
                'diagnostic': {'code': 'prior-audio-index-unreadable', 'detail': str(error)[:800]},
                'evidenceBoundary': BOUNDARY}
    if not isinstance(previous, dict) or previous.get('schemaVersion') != index_schema or previous.get('language') != language:
        return {'schema': SCHEMA, 'status': 'unavailable', 'evidenceKind': 'static',
                'diagnostic': {'code': 'prior-audio-index-schema-or-language-mismatch'},
                'evidenceBoundary': BOUNDARY}
    if 'packageCatalog' not in previous:
        return {'schema': SCHEMA, 'status': 'notRequested', 'evidenceKind': 'static'}
    prior = previous['packageCatalog']
    if isinstance(prior, dict) and prior.get('schema') == SCHEMA and prior.get('status') == 'notRequested':
        return {'schema': SCHEMA, 'status': 'notRequested', 'evidenceKind': 'static'}
    identity = prior.get('inputSetSha256') if isinstance(prior, dict) else None
    if not isinstance(prior, dict) or prior.get('schema') != SCHEMA or not isinstance(identity, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', identity):
        return {'schema': SCHEMA, 'status': 'unavailable', 'evidenceKind': 'static',
                'diagnostic': {'code': 'prior-package-roster-identity-unavailable'},
                'evidenceBoundary': BOUNDARY}
    return collect(expected_input_set_sha256=identity.upper())


def _project_language_table(table):
    """Keep IDs exact while bounding display-only label previews."""
    source_rows = table['rows']
    rows = []
    for row in source_rows[:128]:
        label = row['label']
        projected = {key: row[key] for key in ('ordinal', 'id', 'stringOffset', 'stringEnd')}
        projected['label'] = label if len(label) <= 256 else None
        if len(label) > 256:
            projected.update(labelPreview=label[:256], labelTruncated=True)
        rows.append(projected)
    ranges = table['unclaimedRanges']
    return {'encoding': table['encoding'], 'byteLength': table['byteLength'],
            'rowCount': len(source_rows), 'rows': rows, 'rowsTruncated': len(source_rows) > 128,
            'unclaimedRangeCount': len(ranges),
            'unclaimedByteCount': sum(row['end'] - row['start'] for row in ranges)}


def _project_summary(summary):
    """Retain full numerical totals without unbounded label keys."""
    result = dict(summary)
    labels = summary.get('languageLabelCounts')
    if labels is not None:
        kept = dict((key, value) for key, value in sorted(labels.items()) if len(key) <= 256)
        kept = dict(list(kept.items())[:128])
        result.update(languageLabelCounts=kept,
                      languageLabelCountsTruncated=len(kept) != len(labels),
                      omittedLabelCount=len(labels) - len(kept),
                      omittedLabelEntryCount=sum(labels.values()) - sum(kept.values()))
    return result


def project(report):
    """Bound detail while preserving the complete gate's counters."""
    if report.get('schema') != CORPUS_SCHEMA or report.get('status') != 'complete':
        raise ValueError('complete package corpus gate required')
    return {'schema': SCHEMA, 'status': 'validated', 'evidenceKind': 'static',
            'inputSetSha256': report['inputSetSha256'], 'evidenceBoundary': BOUNDARY,
            'summary': _project_summary(report['summary']),
            'packages': [{**{key: row[key] for key in ('block', 'path', 'payloadBytes', 'headerBytes', 'encryptedHeader', 'counts')},
                          **({'languageTable': _project_language_table(row['languageTable'])} if 'languageTable' in row else {})}
                         for row in report['packages'][:64]],
            'packagesTruncated': len(report['packages']) > 64,
            'repeatedTypedKeys': report['repeatedTypedKeys'][:32],
            'repeatedTypedKeysTruncated': len(report['repeatedTypedKeys']) > 32,
            'lowWordCollisions': report['lowWordCollisions'][:32],
            'lowWordCollisionsTruncated': len(report['lowWordCollisions']) > 32}


def collect(*, expected_input_set_sha256, outer_path=None, ledger_path=None):
    """Run the raw gate once and publish its complete local report plus summary."""
    try:
        report = build(outer_path or ROOT / 'reports/animestudio/vfs_understanding_latest.json',
                       ledger_path or ROOT / 'reports/animestudio/vfs_understanding_files_latest.jsonl.gz',
                       expected_input_set_sha256)
        _atomic_write_json(ROOT / 'reports/audio/package_corpus_current.json', report)
        return project(report)
    except (OSError, ValueError) as error:
        diagnostic = error.diagnostic if isinstance(error, CensusGateError) else {
            'code': type(error).__name__, 'detail': str(error)[:800]}
        return {'schema': SCHEMA, 'status': 'unavailable', 'evidenceKind': 'static',
                'diagnostic': diagnostic, 'evidenceBoundary': BOUNDARY}
