"""Select a published family receipt through the authenticated source registry."""
from __future__ import annotations

import hashlib
import json
import gzip
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import ROOT, resolve_installed_native_inputs, sha256_file
from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_receipt
from scripts.game_data.game_file_store import iter_game_tree, read_game_file
from scripts.source_paths import ExportLayout

DEFAULT_SUMMARY = ExportLayout.configured().evidence_dir / 'animestudio/jsondata_current_latest.json'
DEFAULT_LEDGER = ExportLayout.configured().evidence_dir / 'animestudio/jsondata_current_files_latest.jsonl.gz'


def require_complete_jsondata(export_root:Path)->dict[str,Any]:
    """A complete Data publication owns the entire authenticated source roster."""
    layout=ExportLayout(export_root);directory=(layout.evidence_dir/'animestudio')
    summary_path=directory/'jsondata_current_latest.json';ledger_path=directory/'jsondata_current_files_latest.jsonl.gz'
    raw=summary_path.read_bytes();summary=json.loads(raw);root=layout.json_dir.resolve()
    if Path(summary.get('exportRoot','')).resolve()!=root:
        raise ValueError('Data completeness: selected export root differs from JsonData registry')
    ga,md=resolve_installed_native_inputs()
    options=dict(summary_path=summary_path,ledger_path=ledger_path,
        expected_summary_sha256=hashlib.sha256(raw).hexdigest().upper(),
        native_sources={'GameAssembly.dll':str(ga),'global-metadata.dat':str(md)},
        native_inputs={'GameAssembly.dll':sha256_file(ga).upper(),'global-metadata.dat':sha256_file(md).upper()})
    before=authenticate_current_jsondata_receipt(**options);seen=set();statuses=Counter();failures=[]
    with gzip.open(ledger_path,'rt',encoding='utf-8')as stream:
        for line in stream:
            row=json.loads(line);relative=row['exportRelativePath'];path=(root/relative).resolve()
            try:path.relative_to(root)
            except ValueError as error:raise ValueError('Data completeness: source outside selected export: '+relative)from error
            if path in seen:raise ValueError('Data completeness: duplicate source: '+relative)
            seen.add(path);statuses[row['status']]+=1
            if row['status']!='schema_decoded':
                if len(failures)<8:failures.append(dict(source=relative,status=row['status'],diagnostic=str(row.get('diagnostic')or'')[:500]))
            data=read_game_file(layout.root,'Json/'+relative.replace('\\','/'))
            if len(data)!=row['length']or hashlib.sha256(data).hexdigest().upper()!=row['logicalSha256']:
                raise ValueError('Data completeness: source byte identity differs from authenticated ledger: '+relative)
    declared=summary['summary']
    if not seen or declared.get('filesSelected')!=len(seen)or declared.get('filesJoined')!=len(seen)or declared.get('statusCounts')!=dict(statuses):
        raise ValueError('Data completeness: summary and complete ledger disagree')
    actual={(layout.game/entry.path).resolve()for entry in iter_game_tree(layout.root,'Json')}
    if actual!=seen:
        raise ValueError('Data completeness: selected source roster changed: '+str(dict(
            missing=[str(p)for p in sorted(seen-actual)[:3]],extra=[str(p)for p in sorted(actual-seen)[:3]])))
    if failures:
        raise ValueError('Data completeness: incomplete sources refuse publication: '+json.dumps(
            dict(statusCounts=dict(statuses),firstFailures=failures),ensure_ascii=False))
    after=authenticate_current_jsondata_receipt(**options)
    if after!=before or raw!=summary_path.read_bytes():
        raise ValueError('Data completeness: authenticated source registry changed during validation')
    return dict(files=len(seen),statusCounts=dict(statuses),currentSourceReceipt=after)


def select_current_family_report(
    family: str, export_root: Path, *, summary_path: Path | None = None,
    ledger_path: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Verify current source pins before following, and after reading, a report pin."""
    evidence = ExportLayout(Path(export_root)).evidence_dir / 'animestudio'
    summary_path = evidence / 'jsondata_current_latest.json' if summary_path is None else Path(summary_path)
    ledger_path = evidence / 'jsondata_current_files_latest.jsonl.gz' if ledger_path is None else Path(ledger_path)
    raw = summary_path.read_bytes()
    summary = json.loads(raw)
    if Path(summary.get("exportRoot", "")).resolve() != ExportLayout(export_root).json_dir.resolve():
        raise ValueError("current family receipt: selected export root differs from registry")
    gameassembly, metadata = resolve_installed_native_inputs()
    native_sources = {"GameAssembly.dll": str(gameassembly), "global-metadata.dat": str(metadata)}
    native_inputs = {name: sha256_file(Path(path)).upper() for name, path in native_sources.items()}
    args = {"summary_path": summary_path, "ledger_path": ledger_path,
            "expected_summary_sha256": hashlib.sha256(raw).hexdigest().upper(),
            "native_sources": native_sources, "native_inputs": native_inputs}
    before = authenticate_current_jsondata_receipt(**args)
    pin = summary.get("provenance", {}).get("familyReports", {}).get(family)
    if not isinstance(pin, dict) or not isinstance(pin.get("path"), str) or not pin["path"]:
        raise ValueError(f"current family receipt: no pinned {family} report")
    path = Path(pin["path"])
    if not path.is_absolute():
        path = ROOT / path
    if path.stat().st_size != pin.get("length") or sha256_file(path).upper() != str(pin.get("sha256", "")).upper():
        raise ValueError(f"current family receipt: {family} report byte join failed: {path}")
    after = authenticate_current_jsondata_receipt(**args)
    if after != before:
        raise ValueError("current family receipt: source provenance drifted during selection")
    return path, {"currentSourceReceipt": after, "familyReport": pin}
