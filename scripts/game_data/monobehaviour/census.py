"""Census the exported MonoBehaviour corpus by serialized script class.

MonoBehaviour is by far the largest exported Unity type, and every object in it
decodes against an exact serialized TypeTree. What the export does *not* carry
is the class name: ``m_Script`` points into a MonoScript CAB that the WebUI
export scope never writes, so each object resolves only to an anonymous
``scriptPathId``.

That is not 1.35 million separate problems. A script PPtr is a class identity,
and every object sharing one carries the same serialized field layout, so the
corpus collapses to a few hundred classes. This module measures that collapse:
it groups the exported objects by script identity, records the field layout
each identity serializes, and reports how many objects and which source
containers each one covers.

The census is deliberately name-free. It establishes *how many* distinct
classes the corpus contains and *what layout* each one has; putting a managed
name on a row is a separate join against IL2CPP metadata, which must not be
done from a field-count coincidence. The census exists so that join has a
bounded target list instead of a file tree.

Two identity keys are reported rather than one, because collapsing them early
would hide the interesting failure:

``scriptPathId``
    The serialized MonoScript reference. This is the authoritative class key.

``layoutSignature``
    A digest of the object's serialized field paths. Two classes with byte
    identical layouts share a signature, so a signature covering more than one
    script identity is reported as such and never merged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from scripts.game_data.unity_store import UnityObjectStore, UnityStoreError, open_store, store_path
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.monobehaviour-script-census.v1"

DEFAULT_EXPORT_ROOT = REPO_ROOT / "export_full"
#: The Unity type the census sweeps in the export's object store.
MONOBEHAVIOUR_TYPE = "MonoBehaviour"


class CensusError(RuntimeError):
    """The census could not read the export root it was pointed at."""


@dataclass
class ScriptClass:
    """One serialized script identity and everything the corpus shows of it."""

    script_path_id: int | None
    script_file_id: int | None = None
    layout_signature: str = ""
    field_paths: list[str] = field(default_factory=list)
    type_tree_node_count: int = 0
    objects: int = 0
    example_file: str = ""
    example_names: list[str] = field(default_factory=list)
    source_files: set[str] = field(default_factory=set)
    type_tree_sources: dict[str, int] = field(default_factory=dict)

    def row(self, *, max_sources: int, max_fields: int) -> dict[str, Any]:
        sources = sorted(self.source_files)
        return {
            "scriptPathId": self.script_path_id,
            "scriptFileId": self.script_file_id,
            "layoutSignature": self.layout_signature,
            "objects": self.objects,
            "typeTreeNodeCount": self.type_tree_node_count,
            "serializedFieldCount": len(self.field_paths),
            # Naming reads this, not fieldPaths: only the depth-one entries
            # identify the class, and they stay complete on a layout whose full
            # path list is capped.
            "topLevelFields": top_level_field_names(self.field_paths),
            "typeTreeSources": dict(sorted(self.type_tree_sources.items())),
            "exampleFile": self.example_file,
            "exampleNames": self.example_names[:5],
            "sourceFileCount": len(sources),
            "sourceFiles": sources[:max_sources],
            "fieldPaths": self.field_paths[:max_fields],
            "fieldPathsTruncated": len(self.field_paths) > max_fields,
        }


def top_level_field_names(field_paths: list[str]) -> list[str]:
    """Reduce recorded ``path:type`` entries to the depth-one field names.

    A class is identified by the fields it declares, not by their contents, and
    this list stays small even for a layout with thousands of nested nodes.
    """

    names: list[str] = []
    for entry in field_paths:
        path = entry.split(":", 1)[0]
        if not path or "." in path:
            continue
        if not names or names[-1] != path:
            names.append(path)
    return names


def _open_store(export_root: Path) -> UnityObjectStore:
    try:
        return open_store(Path(export_root))
    except UnityStoreError as exc:
        raise CensusError(f"exported Unity object store not readable: {exc}") from exc


def _object_documents(store: UnityObjectStore) -> Iterator[tuple[str, bytes]]:
    """Every exported MonoBehaviour JSON document, streamed in name order."""

    for row, data in store.iter_documents(MONOBEHAVIOUR_TYPE, "*.json"):
        yield row.name, data


def _read_metadata(data: bytes) -> dict[str, Any] | None:
    """Return one object's ``$animestudio`` block, or None for an unreadable document."""

    try:
        document = json.loads(data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    block = document.get("$animestudio")
    return block if isinstance(block, dict) else None


def layout_signature(field_paths: list[str]) -> str:
    """Digest one object's serialized field layout, order included.

    Order is part of the layout: two classes declaring the same field names in
    a different serialization order are different classes and must not share a
    signature.
    """

    digest = hashlib.sha256()
    for entry in field_paths:
        digest.update(entry.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()[:16]


def census(
    export_root: Path = DEFAULT_EXPORT_ROOT,
    *,
    limit: int | None = None,
    progress: int = 0,
) -> dict[str, Any]:
    """Group every exported MonoBehaviour by its serialized script identity."""

    store = _open_store(export_root)
    classes: dict[tuple[int | None, str], ScriptClass] = {}
    by_signature: dict[str, set[int | None]] = {}
    scanned = 0
    unreadable = 0

    for name, data in _object_documents(store):
        if limit is not None and scanned >= limit:
            break
        scanned += 1
        if progress and scanned % progress == 0:
            print(f"  scanned {scanned} objects", file=sys.stderr, flush=True)
        block = _read_metadata(data)
        if block is None:
            unreadable += 1
            continue

        field_paths = [
            entry for entry in block.get("typeTreeFieldPaths") or [] if isinstance(entry, str)
        ]
        signature = layout_signature(field_paths)
        script_path_id = block.get("scriptPathId")
        if not isinstance(script_path_id, int):
            script_path_id = None
        key = (script_path_id, signature)

        row = classes.get(key)
        if row is None:
            row = ScriptClass(
                script_path_id=script_path_id,
                script_file_id=block.get("scriptFileId")
                if isinstance(block.get("scriptFileId"), int)
                else None,
                layout_signature=signature,
                field_paths=field_paths,
                type_tree_node_count=int(block.get("typeTreeNodeCount") or 0),
                example_file=name,
            )
            classes[key] = row
        row.objects += 1
        source = block.get("sourceFile")
        if isinstance(source, str) and source:
            row.source_files.add(source)
        tree_source = str(block.get("typeTreeSource") or "none")
        row.type_tree_sources[tree_source] = row.type_tree_sources.get(tree_source, 0) + 1
        name = block.get("name")
        if isinstance(name, str) and name and len(row.example_names) < 5:
            if name not in row.example_names:
                row.example_names.append(name)
        by_signature.setdefault(signature, set()).add(script_path_id)

    shared = {
        signature: sorted(ids, key=lambda value: (value is None, value))
        for signature, ids in by_signature.items()
        if len(ids) > 1
    }
    anonymous = sum(row.objects for row in classes.values() if row.script_path_id is None)
    return {
        "classes": classes,
        "summary": {
            "objectsScanned": scanned,
            "objectsUnreadable": unreadable,
            "objectsWithoutScriptIdentity": anonymous,
            "distinctScriptIdentities": len(
                {row.script_path_id for row in classes.values() if row.script_path_id is not None}
            ),
            "distinctLayoutSignatures": len(by_signature),
            "distinctScriptLayoutPairs": len(classes),
            "layoutSignaturesCoveringSeveralScripts": shared,
        },
    }


def build_report(
    export_root: Path = DEFAULT_EXPORT_ROOT,
    *,
    limit: int | None = None,
    max_sources: int = 20,
    max_fields: int = 4000,
    progress: int = 0,
) -> dict[str, Any]:
    result = census(export_root, limit=limit, progress=progress)
    rows = sorted(
        result["classes"].values(),
        key=lambda row: (-row.objects, row.layout_signature),
    )
    summary = dict(result["summary"])
    if rows:
        summary["largestClassObjects"] = rows[0].objects
        covered = sum(row.objects for row in rows[:50])
        total = sum(row.objects for row in rows)
        summary["objectShareOfTop50Classes"] = (
            round(covered / total, 4) if total else 0.0
        )
    return {
        "schema": SCHEMA,
        "exportRoot": str(export_root),
        "unityStore": str(store_path(export_root)),
        "unityType": MONOBEHAVIOUR_TYPE,
        "limit": limit,
        "summary": summary,
        "classes": [row.row(max_sources=max_sources, max_fields=max_fields) for row in rows],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Group the exported MonoBehaviour corpus by serialized script "
            "identity and report each class's field layout and object count."
        )
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=DEFAULT_EXPORT_ROOT,
        help="export root whose game/Unity.sqlite object store holds the MonoBehaviour documents",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="stop after this many objects; a bounded probe, not a census",
    )
    parser.add_argument("--max-sources", type=int, default=20)
    parser.add_argument(
        "--max-fields",
        type=int,
        default=4000,
        help=(
            "cap on recorded field paths per class; a truncated layout cannot "
            "be named, because the missing tail is what selects the class"
        ),
    )
    parser.add_argument(
        "--progress",
        type=int,
        default=0,
        metavar="N",
        help="print progress to stderr every N objects",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    try:
        report = build_report(
            args.export_root,
            limit=args.limit,
            max_sources=args.max_sources,
            max_fields=args.max_fields,
            progress=args.progress,
        )
    except CensusError as exc:
        print(f"MonoBehaviour census unavailable: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
        summary = report["summary"]
        print(
            f"censused {summary['objectsScanned']} MonoBehaviour objects into "
            f"{summary['distinctScriptLayoutPairs']} script/layout classes "
            f"-> {args.report}"
        )
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - documented entry point
    if not __package__:
        raise SystemExit("run as: python -m scripts.game_data.monobehaviour.census")
    raise SystemExit(main())
