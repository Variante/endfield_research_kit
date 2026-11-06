"""Data projections of current source-bound family receipts after fresh replay."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.common import canonical_json_sha256
from scripts.game_data.memorypack import current_family_evidence as current
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.webui.data_inspector.contract import source_descriptor
from scripts.webui.data_inspector.current_receipts import select_current_family_report


def _buff_value_schema(context):
    from scripts.game_data.memorypack.derived_plans import load_registry
    from scripts.game_data.memorypack.buff_values import BuffValueSchema
    from scripts.game_data.il2cpp.native_image import open_native_image
    current.need('named-Buff-active-source-operation', context is not None and context.get('buff') is not None)
    root=context['gameRoot']; assembly=root.parent/'GameAssembly.dll'
    metadata=root/'il2cpp_data/Metadata/global-metadata.dat'
    registry,audit=load_registry(gameassembly=assembly,metadata=metadata)
    current.need('named-Buff-selected-plan',audit.get('status')=='validated'
        and registry.named_roots.get('Beyond.Gameplay.Core.BuffData')is not None)
    current.need('named-Buff-same-selected-native',all(audit['nativeInputs'][k].upper()==context['nativeInputs'][k].upper()
        for k in ('GameAssembly.dll','global-metadata.dat')))
    schema=BuffValueSchema(operation=context['operation'],registry=registry,
        image=open_native_image(assembly,metadata),native=context['buff'])
    return schema,registry.named_roots['Beyond.Gameplay.Core.BuffData']


def _buff_values(row, context, schema, definition):
    data=current.source_bytes(context,row['identity']); nodes={}
    def retain(reader,_value):nodes.update(reader.objects)
    value,facts=schema.decode(data,definition=definition,source=row['virtualPath'],
        receipt=row['rootReceipt'],on_decoded=retain)
    current.need('named-Buff-source-id',value.get('id')==Path(row['exportRelativePath']).stem,row['virtualPath'])
    return value,dict(facts,sourceSha256=row['logicalSha256'],bytesConsumed=len(data),serializedMemberCount=30),nodes


def _load_buff(export_root, *, summary_path=None, ledger_path=None, current_context=None,
               include_roots=True, on_row=None):
    options = {} if summary_path is None else dict(summary_path=summary_path, ledger_path=ledger_path)
    path, selection = select_current_family_report('BuffData', export_root, **options)
    report = json.loads(path.read_bytes()); pin = _fingerprint(path)
    current.need('selected-Buff-export-root', Path(report['exportRoot']).resolve() == Path(export_root).resolve())
    current.need('selected-Buff-report-pin', all(selection['familyReport'][key] == pin[key] for key in ('path','length','sha256')))
    evidence, _ = current.load_evidence(path, family='BuffData',
        expected_input_set_sha256=selection['currentSourceReceipt']['inputSetSha256'],
        expected_paths=None, loaded_report=(report, pin), context=current_context,
        include_root_receipts=include_roots, on_row=on_row)
    after_path, after = select_current_family_report('BuffData', export_root, **options)
    current.need('Buff-registry-selection-bookend', path == after_path and after == selection)
    return report, evidence, selection, pin


def load_buff_records(export_root, *, summary_path, ledger_path, current_context=None):
    export_root = Path(export_root).resolve()
    schema,definition=_buff_value_schema(current_context); named={}
    def collect(row):
        value,facts,_nodes=_buff_values(row,current_context,schema,definition)
        named[row['virtualPath']]=(value,facts)
    report, evidence, selection, pin = _load_buff(export_root, summary_path=summary_path, ledger_path=ledger_path,
        current_context=current_context,include_roots=False,on_row=collect)
    records = []
    for source, row in sorted(evidence.items()):
        path = export_root / 'game' / source.removeprefix('Data/')
        value,facts=named[source]; names=list(value)
        records.append(dict(id=path.relative_to(export_root).as_posix(), title=path.stem,
            status='named_exact', source=source_descriptor(path, export_root=export_root, media_type='application/octet-stream'),
            tags=['buff','memorypack','current-native','named_exact'], summary=f"{len(names)} named root fields; cursor={facts['bytesConsumed']}/{row['length']}",
            facts=dict(facts, decodedFieldNames=names, currentNativeRoot=True),
            searchTerms=names, payloadKind='reader', payload=value,
            evidenceBoundary='Current source-owned root fields and independently proved children; whole root requires all30, source id and physical EOF; no runtime claim.'))
    current.need('named-Buff-complete-value-roster',named.keys()==evidence.keys())
    return records, dict(currentSourceReceipt=selection, familyReport=pin, currentNativeRoot=True,
        allStoredValuesExact=True,namedValueTypes=sorted(schema.types),
        storedValueLayouts=[v for _,v in sorted(schema.layouts.layouts.items())])


def load_action_records(receipt_path, buff_path, export_root, *, report, current_context=None):
    export_root = Path(export_root).resolve(); receipt_pin = _fingerprint(receipt_path)
    schema,definition=_buff_value_schema(current_context)
    records = []; expected = []
    def collect(row):
        _root,_facts,nodes=_buff_values(row,current_context,schema,definition)
        if row['actionReceipts']: expected.append(current.action_scope(row))
        path = export_root / 'game' / row['virtualPath'].removeprefix('Data/')
        for receipt in row['actionReceipts']:
            names = [field['fieldName'] for field in receipt['fields']]
            start=receipt['start']; end=receipt['end']
            offset=start if receipt['wireForm']=='concrete-EffectActionData' else start+(3 if receipt['unionTag']>=250 else 1)
            if receipt['nullWrapper']:
                values=None
            else:
                node=nodes.get((offset,end))
                current.need('named-Buff-action-certified-object',node is not None,(row['virtualPath'],start,end))
                current.need('named-Buff-action-certified-fields',node['fields']==[
                    {k:f[k]for k in ('fieldName','start','end')}for f in receipt['fields']],(row['virtualPath'],start,end))
                values=node['value']
            records.append(dict(id=path.relative_to(export_root).as_posix() + ':' + str(receipt['start']),
                title=receipt['wrapperName'].removeprefix('Beyond.MemoryPack.'), status='named_exact',
                source=source_descriptor(path, export_root=export_root, media_type='application/octet-stream'),
                tags=['buff','current-native','action'], summary=f"{len(names)} named action fields at {receipt['start']}..{receipt['end']}",
                facts=dict(unionTag=receipt['unionTag'], decodedFieldNames=names, wholeActionExact=True, wholeBuffDataExact=False,
                    owningBuffRootAuthenticated=True,sourceSpan=dict(start=start,end=end),sourceSha256=row['logicalSha256'],
                    namedStoredValuesExact=True,rawValueBitsPreserved=True,runtimeExecutionProved=False),
                searchTerms=names, payloadKind='reader', payload=dict(receipt,values=values),
                evidenceBoundary='Exact current named action values within the certified source span and independently owned child grammar; enclosing source-root proof is separate; no runtime claim.'))
    family, evidence, selection, buff_pin = _load_buff(export_root, current_context=current_context,
        include_roots=False,on_row=collect)
    current.need('current-action-family-pin', Path(buff_path).resolve().as_posix() == buff_pin['path']
        and report.get('schema') == 'endfield.buff-action-receipt-corpus.v9'
        and report.get('buffReportSha256') == buff_pin['sha256']
        and report.get('inputSetSha256') == family['inputSetSha256']
        and Path(report.get('exportRoot','')).resolve() == export_root
        and report.get('status') == 'complete' and report.get('publicationEligible') is True
        and report.get('wholeBuffDataExact') is False)
    current.need('canonical-current-action-replay', canonical_json_sha256(expected) == canonical_json_sha256(report['files']))
    current.need('action-report-bookend', _fingerprint(receipt_path) == receipt_pin)
    return records, dict(currentSourceReceipt=selection, actionReport=receipt_pin, familyReport=buff_pin)
