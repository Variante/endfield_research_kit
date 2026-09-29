"""Authenticate one already generated Buff formatter audit row for a selected build.

The IL2CPP context audit is expensive and covers many families. A focused
selected-source receipt may consume one of its prior rows only when the
installed-native gate has independently passed and the report still names the
same native inputs and reviewed action contract bytes. This module does not
run the context audit or grant a source-byte receipt by itself.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath
from typing import Any


def validated_action_row(
    report: dict[str, Any], *, expected_inputs: dict[str, str],
    contract_path: Path, report_key: str, union_tag: int, wrapper_name: str,
    read_order_key: str,
) -> dict[str, Any]:
    """Check a single audited formatter, context set and dispatcher route."""
    reported_inputs = report.get("nativeInputs", {})
    if (
        report.get("status") != "structural-only"
        or report.get("failures") != []
        or {key: reported_inputs.get(key) for key in (
            "gameassemblySha256", "metadataSha256", "unityplayerSha256",
        )} != {
            "gameassemblySha256": expected_inputs["GameAssembly.dll"],
            "metadataSha256": expected_inputs["global-metadata.dat"],
            "unityplayerSha256": expected_inputs["UnityPlayer.dll"],
        }
    ):
        raise ValueError("buffSelectedNativeAudit.native-inputs-or-failures")
    raw = Path(contract_path).read_bytes()
    contract = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest().upper()
    source_hashes = [value for name, value in report.get("sourceHashes", {}).items()
                     if PureWindowsPath(name).name == contract_path.name]
    selected = report.get(report_key, {})
    if (
        contract.get("schemaVersion") != 1
        or source_hashes != [digest]
        or selected.get("contractSha256") != digest
        or PureWindowsPath(selected.get("contractPath", "")).name != contract_path.name
        or selected.get("anonymousReadOrder") != contract.get("anonymousReadOrder")
        or selected.get("codeWindows") != contract.get("codeWindows")
        or selected.get("dataWindows") != contract.get("dataWindows", [])
        or selected.get("nestedContexts") != contract.get("nestedContexts")
        or len(selected.get("methods", [])) != len(contract.get("methods", []))
        or not selected.get("level", "").startswith("direct selected consumer order")
        or read_order_key not in contract.get("anonymousReadOrder", {})
    ):
        raise ValueError("buffSelectedNativeAudit.contract-drift")
    routes = report.get("selectedBuffUnionRoutes", {}).get("rows", [])
    selected_route = [row for row in routes if row.get("tag") == union_tag]
    if len(selected_route) != 1 or selected_route[0].get("wrapperName") != wrapper_name:
        raise ValueError("buffSelectedNativeAudit.dispatcher-route")
    return {
        "status": "validated", "contractSha256": digest,
        "unionTag": union_tag, "wrapperName": wrapper_name,
        "anonymousReadOrder": contract["anonymousReadOrder"],
    }
