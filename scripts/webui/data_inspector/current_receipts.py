"""Select a published family receipt through the authenticated source registry."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import ROOT, resolve_installed_native_inputs, sha256_file
from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_receipt
from scripts.source_paths import ExportLayout

DEFAULT_SUMMARY = ROOT / "reports/animestudio/jsondata_current_latest.json"
DEFAULT_LEDGER = ROOT / "reports/animestudio/jsondata_current_files_latest.jsonl.gz"


def select_current_family_report(
    family: str, export_root: Path, *, summary_path: Path = DEFAULT_SUMMARY,
    ledger_path: Path = DEFAULT_LEDGER,
) -> tuple[Path, dict[str, Any]]:
    """Verify current source pins before following, and after reading, a report pin."""
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
