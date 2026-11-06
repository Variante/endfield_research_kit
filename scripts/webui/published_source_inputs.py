"""Read the source identity of selected published outputs, without run reports."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.source_paths import ExportLayout
from scripts.game_data.extraction.export_full_from_game import (
    EXTRACTION_PROVENANCE_SCHEMA,
    normalize_animestudio_object_index_source_fingerprint,
)
from scripts.game_data.extraction.verify_export_freshness import output_stamp


def output_source_fingerprints(
    output_root: Path,
    outputs: tuple[tuple[str, str], ...],
    *,
    summary_path: Path | None = None,
) -> tuple[dict, Path]:
    """Use per-output stamps; only pre-provenance exports use their summary.

    A last-run summary may be absent or describe a different extraction scope.
    Existing malformed provenance never falls back to another authority.
    """
    layout = ExportLayout(output_root)
    authority = layout.extraction_provenance_path
    provenance = None
    summary = {}
    if authority.exists() or authority.is_symlink():
        provenance = json.loads(authority.read_text(encoding="utf-8"))
        if not isinstance(provenance, dict) or provenance.get("schema") != EXTRACTION_PROVENANCE_SCHEMA:
            raise ValueError(f"invalid extraction provenance: {authority}")
    else:
        authority = summary_path if summary_path is not None else layout.export_summary_path
        summary = json.loads(authority.read_text(encoding="utf-8"))
        if not isinstance(summary, dict):
            raise ValueError(f"invalid extraction summary: {authority}")
    if not outputs:
        raise ValueError("published source check requires explicit outputs")
    fingerprints = None
    for section, key in outputs:
        stamp = output_stamp(provenance, summary, section, key)
        sources = stamp.get("sources") if isinstance(stamp, dict) else None
        if not isinstance(sources, dict) or not sources:
            raise ValueError(f"{authority}: no source fingerprints for {section}/{key}")
        current = {}
        for source, row in sources.items():
            try:
                current[source] = normalize_animestudio_object_index_source_fingerprint(row)
                current[source]["fingerprint"] = current[source]["fingerprint"].lower()
            except ValueError as error:
                raise ValueError(f"{authority}: {section}/{key} source {source}: {error}; "
                                 f"actual={str(row)[:320]}") from error
        if fingerprints is not None and current != fingerprints:
            source = next(name for name in sorted(fingerprints.keys() | current.keys())
                          if fingerprints.get(name) != current.get(name))
            raise ValueError(f"{authority}: source fingerprints differ between published outputs at {section}/{key}; "
                             f"source={source}; expected={str(fingerprints.get(source))[:320]}; "
                             f"actual={str(current.get(source))[:320]}")
        fingerprints = current
    return fingerprints, authority
