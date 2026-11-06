"""Current Buff/Skill source-bound root receipts and canonical replay.

Source completeness is authenticated by the independent inventory, never used
as a schema grant. Every named root field is replayed under a fresh current
native operation. Only all root fields plus the original source id (Buff) and
physical EOF grant a whole-root receipt. Unproved positive children stay partial.
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
import gzip
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath

from scripts.common import canonical_json_sha256
from scripts.game_data import jsondata_source_inventory as inventory
from scripts.game_data.extraction.build_evidence import publish
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.levelscript_reader_inputs import reader_input_changes, snapshot_complete_reader_inputs
from scripts.game_data.memorypack.corpus_gate import (
    _fingerprint, _snapshot_pinned_files, _read_outer_and_ledger,
    _chunk_fingerprints, _chunk_selection_snapshot, family_rows,
)
from scripts.game_data.memorypack import current_buff_root
from scripts.game_data.memorypack.current_action_receipts import receipts_from_root
from scripts.game_data.memorypack.skill_timeline_current_sequence import decode_current_skill_prefix
from scripts.game_data.skill_timeline_current_sequence_native import current_sequence
from scripts.game_data.string_pool import StringPool
from scripts.source_paths import ExportLayout


FORMATS = {family: 'endfield.current-' + family.lower() + '-family-corpus.v3'
           for family in ('BuffData', 'SkillData')}
MAX_ROW_BYTES = 256 << 20


def need(check, condition, detail=None):
    if not condition:
        raise ValueError('currentFamilyEvidence.' + check + ':' + str(detail)[:900])


def source_inventory(layout):
    root = layout.evidence_dir / 'animestudio'
    summary_path = root / 'jsondata_source_current.json'
    ledger_path = root / 'jsondata_source_files_current.jsonl.gz'
    summary = json.loads(summary_path.read_bytes())
    need('selected-export', Path(summary['exportRoot']).resolve() == layout.root.resolve())
    inventory.verify_saved_inventory(summary, ledger_path=ledger_path)
    with gzip.open(ledger_path, 'rt', encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream]
    return summary, rows, [_fingerprint(summary_path), _fingerprint(ledger_path)]


def verify_audited_chunks(chunks, ledger_path, input_set):
    selected = {os.path.normcase(str(Path(row['path']).resolve())): row for row in chunks}
    found = set()
    with gzip.open(ledger_path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row.get('recordType') != 'chunk' or not row.get('physicalChunkPath'): continue
            key = os.path.normcase(str(Path(row['physicalChunkPath']).resolve()))
            if key not in selected: continue
            actual = selected[key]
            need('audited-physical-chunk', row.get('status') == 'verified'
                and row.get('inputSetSha256') == input_set
                and row.get('actualPhysicalLength') == actual['length']
                and str(row.get('recomputedContentMd5','')).upper() == actual['rawMd5'], row['physicalChunkPath'])
            found.add(key)
    need('complete-audited-physical-chunk-set', found == selected.keys())


@contextmanager
def reader_context(layout, game_root, *, buff=True):
    game_root = Path(game_root).resolve()
    before = snapshot_complete_reader_inputs()
    summary, rows, pins = source_inventory(layout)
    outer, _header, ledger, _provenance = _read_outer_and_ledger(
        Path(summary['provenance']['outer']['path']), Path(summary['provenance']['ledger']['path']),
        expected_input_set_sha256=summary['inputSetSha256'])
    need('selected-installed-source-roots', Path(outer['primaryAssets']).resolve() == game_root / 'Persistent'
        and Path(outer['fallbackAssets']).resolve() == game_root / 'StreamingAssets')
    selected = []
    for family in FORMATS:
        selected.extend(family_rows(ledger, expected_input=summary['inputSetSha256'],
            prefix='Data/Json/' + family + '/', pattern=re.compile(r'^Data/Json/' + family + r'/[^/]+[.]json$'), label=family))
    del ledger
    need('inventory-physical-ledger-family-set', {row['virtualPath'] for row in selected}
        == {row['virtualPath'] for row in rows if row['family'] in FORMATS})
    chunks = _chunk_fingerprints(selected)
    verify_audited_chunks(chunks, Path(summary['provenance']['ledger']['path']), summary['inputSetSha256'])
    print('[current-family] inventory and physical chunks authenticated', flush=True)
    audit_pins = [summary['provenance']['outer'], summary['provenance']['ledger']]
    _snapshot_pinned_files(audit_pins, label='current family authenticated VFS publication')
    resolution = _chunk_selection_snapshot(selected, outer)
    strings = StringPool(layout.json_dir / 'StringPool')
    with current_sequence(game_root=game_root, strings=strings) as operation:
        print('[current-family] current root/action native operation validated', flush=True)
        proof = operation.proof
        image = open_native_image(game_root.parent / 'GameAssembly.dll',
            game_root / 'il2cpp_data/Metadata/global-metadata.dat')
        native = current_buff_root.prepare(image, proof['nativeInputs'], operation) if buff else None
        print('[current-family] selected concrete component proofs validated', flush=True)
        context=dict(layout=layout, gameRoot=game_root, operation=operation, buff=native,
            inputSetSha256=summary['inputSetSha256'], inventoryRows=rows, inventoryPins=pins,
            readerInputs=before, nativeInputs=proof['nativeInputs'],
            selectedChunkFingerprints=chunks, selectedChunkResolution=resolution,replayPins={})
        yield context
        if context['replayPins']:
            _snapshot_pinned_files(list(context['replayPins'].values()),label='family replay inputs at operation exit')
        need('physical-chunk-bookend', _chunk_fingerprints(selected) == chunks)
        need('physical-overlay-bookend', _chunk_selection_snapshot(selected, outer) == resolution)
        _snapshot_pinned_files(pins, label='current family source inventory after replay')
        _snapshot_pinned_files(audit_pins, label='current family VFS publication after replay')
        require_current_report_inputs(dict(readerInputs=before, nativeInputs=context['nativeInputs']),
            dict(context, readerInputs=snapshot_complete_reader_inputs()), '/'.join(FORMATS),
            check='reader-source-bookend')


def family_sources(context, family):
    rows = [row for row in context['inventoryRows'] if row['family'] == family]
    paths = [row['virtualPath'] for row in rows]
    need('unique-complete-family-source-set', len(paths) == len(set(paths)) and bool(paths), family)
    return sorted(rows, key=lambda row: row['virtualPath'])


def source_bytes(context, row):
    relative = Path(row['exportRelativePath'])
    need('safe-source-relative-path', not relative.is_absolute() and '..' not in relative.parts)
    path = context['layout'].json_dir / relative
    data = path.read_bytes()
    need('current-source-byte-join', (len(data), hashlib.md5(data).hexdigest().upper(),
        hashlib.sha256(data).hexdigest().upper()) ==
        (row['length'], row['logicalMd5'].upper(), row['logicalSha256'].upper()), row['virtualPath'])
    return data


def decode(context, family, row, data):
    if family == 'BuffData':
        receipt = current_buff_root.decode_current_buff_root(data, source=row['virtualPath'],
            operation=context['operation'], native=context['buff'])
        whole = receipt['wholeBuffDataExact']
    else:
        receipt = decode_current_skill_prefix(data, source=row['virtualPath'], operation=context['operation'])
        whole = receipt['wholeSkillDataExact']
        if whole:
            ids = [field.get('value') for field in receipt['rootFields'] if field['fieldName'] == 'skillId']
            if ids != [PurePosixPath(row['virtualPath']).stem]:
                receipt = dict(receipt, wholeSkillDataExact=False, status='current-skill-root-id-refused',
                    stopReason='currentFamilyEvidence.SkillData.source-id-differs:' + str(ids)[:160])
                whole = False
    expected_count = 30 if family == 'BuffData' else 49
    if whole:
        need('whole-root-field-and-EOF-join', receipt['parserCursor'] == receipt['hardLimit'] == len(data)
            and receipt['stopReason'] is None
            and [field['memberIndex'] for field in receipt['rootFields']] == list(range(expected_count)), row['virtualPath'])
    identity = {key:row[key] for key in ('virtualPath','exportRelativePath','family','length','logicalMd5','logicalSha256','packed')}
    actions = receipts_from_root(data, operation=context['operation'], source=row['virtualPath'],
        logical_sha256=row['logicalSha256'], root=receipt) if family == 'BuffData' else []
    return dict(**identity, identity=dict(row), rootReceipt=receipt, actionReceipts=actions,
        wholeSchemaExact=whole, status='schema_decoded' if whole else 'bounded_partial' if receipt['rootFields'] else 'unsupported')


def ledger_path(layout, family):
    return layout.evidence_dir / 'animestudio' / (family.lower() + '_current_rows.jsonl.gz')


def action_scope(row):
    return dict(source=row['virtualPath'], logicalSha256=row['logicalSha256'],
                actionCount=len(row['actionReceipts']))


def build_family(context, family, *, write_path=None):
    selected = family_sources(context, family)
    final = ledger_path(context['layout'], family)
    target = final if write_path is None else Path(write_path)
    need('retained-row-ledger-path', target.resolve().is_relative_to(context['layout'].evidence_dir.resolve()))
    target.parent.mkdir(parents=True, exist_ok=True)
    identities = []; exact = 0; actions = []
    with target.open('wb') as output, gzip.GzipFile(filename='',fileobj=output,mode='wb',mtime=0) as stream:
        for number, source in enumerate(selected, 1):
            try:
                row = decode(context, family, source, source_bytes(context, source))
                encoded = json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8') + b'\n'
                need('bounded-family-row', len(encoded) <= MAX_ROW_BYTES, source['virtualPath'])
                stream.write(encoded)
            except (ValueError,KeyError,TypeError,RuntimeError) as error:
                raise ValueError(f"currentFamilyEvidence.decode:family={family};source={source['virtualPath']};"
                    f"sha256={source['logicalSha256']};{type(error).__name__}:{error}") from error
            identities.append({key:row[key]for key in ('virtualPath','length','logicalMd5','logicalSha256')})
            exact += row['wholeSchemaExact']
            if family == 'BuffData' and row['actionReceipts']: actions.append(action_scope(row))
            if number % 250 == 0 or number == len(selected):
                print(f'[current-family] {family}: {number}/{len(selected)} sources joined', flush=True)
    pin = dict(_fingerprint(target), path=final.resolve().as_posix())
    report = dict(format=FORMATS[family], schemaVersion=3, family=family, status='complete',
        publicationEligible=True, wholeSchemaExact=False, sourceIdentityComplete=True,
        inputSetSha256=context['inputSetSha256'], exportRoot=context['layout'].root.as_posix(),
        gameRoot=context['gameRoot'].as_posix(), identitySetSha256=canonical_json_sha256(identities),
        provenance=dict(inventory=context['inventoryPins'], readerInputs=context['readerInputs'],
            nativeInputs=context['nativeInputs'], selectedChunkFingerprints=context['selectedChunkFingerprints'],
            selectedChunkResolution=context['selectedChunkResolution']),
        summary=dict(filesSelected=len(selected), filesSucceeded=len(selected), filesWholeSchemaExact=exact),
        filesLedger=pin)
    if family == 'BuffData': report['actionSources'] = actions
    return report


def build(layout, game_root):
    """Publish both families only after all source/native exit gates pass."""
    pending = {family:Path(str(ledger_path(layout,family))+'.pending') for family in FORMATS}
    try:
        with reader_context(layout, game_root) as context:
            reports = {family: build_family(context, family, write_path=pending[family]) for family in FORMATS}
        # All source/native bookends closed before any published ledger changes.
        del context
        for family, path in pending.items(): os.replace(path,ledger_path(layout,family))
    finally:
        for path in pending.values():
            if path.is_file():path.unlink()
    root = layout.evidence_dir / 'animestudio'
    for family, report in reports.items():
        path = root / ('buffdata_current_latest.json' if family == 'BuffData' else 'skilldata_current_latest.json')
        publish(path, report)
    buff = root / 'buffdata_current_latest.json'
    report = reports['BuffData']
    publish(root / 'buff_action_receipts_current_latest.json', dict(
        schema='endfield.buff-action-receipt-corpus.v9', status='complete', publicationEligible=True,
        wholeBuffDataExact=False, inputSetSha256=report['inputSetSha256'], exportRoot=layout.root.as_posix(),
        buffReportPath=buff.as_posix(), buffReportSha256=_fingerprint(buff)['sha256'],
        files=report['actionSources'],
        provenance=report['provenance']))
    return reports


def report_rows(report, layout, *, max_row_bytes=MAX_ROW_BYTES):
    """Bounded I/O only; recorded rows grant no native/schema authority."""
    need('row-byte-limit', type(max_row_bytes)is int and 0 < max_row_bytes <= MAX_ROW_BYTES)
    pin = report['filesLedger']; path = Path(pin['path']).resolve()
    need('retained-row-ledger-path', path.is_relative_to(layout.evidence_dir.resolve()))
    _snapshot_pinned_files([pin],label='current family row ledger before read')
    try:
        with gzip.open(path,'rb') as stream:
            while True:
                line = stream.readline(max_row_bytes+1)
                if not line: break
                need('bounded-complete-row', len(line)<=max_row_bytes and line.endswith(b'\n'),path)
                row = json.loads(line)
                need('row-object', isinstance(row,dict),path)
                yield row
    finally:
        _snapshot_pinned_files([pin],label='current family row ledger after read')


def root_summary(row):
    root=row['rootReceipt']; fields=root['rootFields']
    return dict(rootFieldCount=len(fields),lastCompleteMemberIndex=fields[-1]['memberIndex']if fields else None,
        parserCursor=root['parserCursor'],hardLimit=root['hardLimit'],stopReason=root['stopReason'],
        sourceIdAndPhysicalEofProved=row['wholeSchemaExact'],runtimeExecutionProved=False)


def require_current_report_inputs(provenance, context, family, *, check='current-reader-and-native-inputs', source=None):
    """Reject drift before replay, with bounded source/native diagnostics."""
    recorded_reader, current_reader = provenance['readerInputs'], context['readerInputs']
    recorded_native, current_native = provenance['nativeInputs'], context['nativeInputs']
    if recorded_reader == current_reader and recorded_native == current_native:
        return
    diagnostic = dict(validator='current-family-evidence', check=check,
        family=family, exportRoot=context['layout'].root.as_posix(),
        gameRoot=context['gameRoot'].as_posix())
    if source is not None:
        diagnostic['sourcePath'] = str(source)
    if recorded_reader != current_reader:
        valid = lambda value: isinstance(value, dict) and isinstance(value.get('files'), list) and all(
            isinstance(row, dict) and isinstance(row.get('path'), str) for row in value['files'])
        diagnostic['readerInputs'] = reader_input_changes(recorded_reader, current_reader) if (
            valid(recorded_reader) and valid(current_reader)) else dict(
                expectedShape=type(recorded_reader).__name__, actualShape=type(current_reader).__name__,
                expectedSha256=canonical_json_sha256(recorded_reader),
                actualSha256=canonical_json_sha256(current_reader))
    if recorded_native != current_native:
        if isinstance(recorded_native, dict) and isinstance(current_native, dict):
            keys = sorted(recorded_native.keys() | current_native.keys())
            changed = [key for key in keys if recorded_native.get(key) != current_native.get(key)]
            diagnostic['nativeInputs'] = dict(changedInputs=len(changed), changes=[dict(
                name=key, expectedSha256=recorded_native.get(key), actualSha256=current_native.get(key))
                for key in changed[:8]])
        else:
            diagnostic['nativeInputs'] = dict(expectedShape=type(recorded_native).__name__,
                actualShape=type(current_native).__name__)
    error = ValueError('currentFamilyEvidence.' + check + ':' +
                       json.dumps(diagnostic, ensure_ascii=False, sort_keys=True)[:8000])
    error.diagnostic = diagnostic
    raise error


def verify_report(report, context, family, *, expected_paths=None, replay=True, on_row=None):
    need('fresh-replay-required', replay is True)
    need('family-envelope', report.get('format') == FORMATS[family] and report.get('schemaVersion') == 3
        and report.get('family') == family and report.get('status') == 'complete'
        and report.get('publicationEligible') is True and report.get('wholeSchemaExact') is False
        and report.get('sourceIdentityComplete') is True)
    need('source-input-set', report['inputSetSha256'] == context['inputSetSha256'])
    need('selected-family-export', Path(report['exportRoot']).resolve() == context['layout'].root.resolve()
        and Path(report['gameRoot']).resolve() == context['gameRoot'])
    provenance = report['provenance']
    require_current_report_inputs(provenance, context, family, source=report['filesLedger']['path'])
    need('inventory-pins', provenance['inventory'] == context['inventoryPins'])
    for role in ('selectedChunkFingerprints','selectedChunkResolution'):
        need('current-physical-source:' + role, provenance[role] == context[role])
    selected = family_sources(context, family)
    if expected_paths is not None:
        need('registry-ledger-source-set', set(expected_paths) == {r['virtualPath'] for r in selected})
    identities=[]; exact=0; actions=[]; count=0
    for index, recorded in enumerate(report_rows(report,context['layout'])):
        need('family-source-set', index<len(selected),recorded.get('virtualPath'))
        source=selected[index]; number=index+1; count=number
        need('family-source-set', recorded.get('virtualPath')==source['virtualPath'])
        need('family-source-identity', recorded.get('identity') == source, source['virtualPath'])
        data = source_bytes(context, source)
        fresh = decode(context, family, source, data)
        need('fresh-canonical-root-replay', canonical_json_sha256(fresh) == canonical_json_sha256(recorded), source['virtualPath'])
        identities.append({key:recorded[key]for key in ('virtualPath','length','logicalMd5','logicalSha256')})
        exact+=recorded['wholeSchemaExact']
        if family=='BuffData' and recorded['actionReceipts']: actions.append(action_scope(recorded))
        if on_row is not None:on_row(recorded)
        if number % 500 == 0 or number == len(selected):
            print(f'[current-family] canonical {family}: {number}/{len(selected)} sources replayed', flush=True)
    need('family-source-set',count==len(selected))
    need('family-identity-set',canonical_json_sha256(identities)==report['identitySetSha256'])
    summary=dict(filesSelected=count,filesSucceeded=count,filesWholeSchemaExact=exact)
    need('family-summary',report['summary']==summary)
    if family=='BuffData':need('family-action-source-set',report['actionSources']==actions)
    return summary


def load_evidence(path, *, family, expected_input_set_sha256, expected_paths, loaded_report=None, context=None,
                  include_root_receipts=False, on_row=None):
    report, pin = loaded_report if loaded_report is not None else (
        json.loads(Path(path).read_bytes()), _fingerprint(Path(path)))
    need('selected-preloaded-report-path', pin.get('path') == Path(path).resolve().as_posix())
    _snapshot_pinned_files([pin], label='current family report before replay')
    layout = ExportLayout(Path(report['exportRoot'])).require()
    manager = reader_context(layout, Path(report['gameRoot']), buff=family == 'BuffData') if context is None else nullcontext(context)
    evidence = {}
    def collect(row):
        detail=dict(currentNativeRoot=True,wholeSchemaExact=row['wholeSchemaExact'],
            rootProofSummary=root_summary(row),canonicalStatus=row['status'])
        if include_root_receipts:detail['rootReceipt']=row['rootReceipt']
        evidence[row['virtualPath']]=dict(length=row['length'],logicalMd5=row['logicalMd5'],
            logicalSha256=row['logicalSha256'],detail=detail,
            **{key:None for key in ('rootNoPositiveReceipt','rootPositiveDamageReceipt',
                'rootSingleCreateActionReceipt','rootSharedEventReceipt','rootSelectedSourceReceipt')})
        if on_row is not None:on_row(row)
    with manager as context:
        need('expected-input-set', context['inputSetSha256'] == expected_input_set_sha256)
        for item in (pin,report['filesLedger']):
            retained={key:item[key]for key in ('path','length','sha256')}
            previous=context.setdefault('replayPins',{}).setdefault(retained['path'],retained)
            need('conflicting-live-replay-pin',previous==retained,retained['path'])
        verify_report(report, context, family, expected_paths=expected_paths,on_row=collect)
    _snapshot_pinned_files([pin], label='current family report after replay')
    return evidence, {**pin, 'format':report['format'], 'identitySetSha256':report['identitySetSha256'],
                      'filesLedger':report['filesLedger']}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--export-root', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print('[current-family] proving current native root and child programs', flush=True)
        build(ExportLayout(args.export_root.resolve()).require(), args.game_root.resolve())
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        import traceback
        diagnostic = dict(status='failed', validator=__name__, gameRoot=str(args.game_root),
            exportRoot=str(args.export_root), errorType=type(error).__name__, detail=str(error)[:2000],
            frames=[dict(path=frame.filename,line=frame.lineno,function=frame.name)
                for frame in traceback.extract_tb(error.__traceback__)[-5:]])
        print('[current-family] failed: ' + json.dumps(diagnostic,ensure_ascii=False), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
