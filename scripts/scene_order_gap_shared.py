from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


# DialogIdTable registry: see scripts/story_builder/dialog_registry.py.
# This is Endfield's authoritative runtime dialog registry (extracted from
# Beyond.Gameplay.DialogIdTable via the binary table on disk). A sceneKey
# present in this registry is loadable by the runtime; one absent is
# unreachable cut/dead content.
_DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent
    / "export_full" / "recovered" / "dialog_id_table_index.json"
)


@lru_cache(maxsize=4)
def _load_dialog_id_registry(path_str: str) -> dict:
    p = Path(path_str)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_dialog_id_registry(path: Path | None = None) -> dict:
    """Public entry point. Returns the registry dict (sceneKey -> info)."""
    return _load_dialog_id_registry(str(path or _DEFAULT_REGISTRY_PATH))


# DialogSummaryMapTable: maps a dlg_* sceneKey to a summary_* key into
# DialogSummaryTable. A scene appearing here has authored summary text in the
# game data -- a stronger "main-story relevance" signal than DialogIdTable
# membership alone (a dialog can be runtime-registered without having a
# canonical summary). Pure evidence surfacing, no inference.
_DEFAULT_SUMMARY_MAP_PATH = (
    Path(__file__).resolve().parent.parent
    / "export_full" / "structured" / "StreamingAssets" / "Table"
    / "DialogSummaryMapTable.json"
)


@lru_cache(maxsize=4)
def _load_dialog_summary_map(path_str: str) -> dict:
    p = Path(path_str)
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Coerce to {sceneKey: summaryKey} strings.
    out: dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str) and k and v:
            out[k] = v
    return out


def load_dialog_summary_map(path: Path | None = None) -> dict:
    """Public entry point. Returns the sceneKey -> summaryKey map."""
    return _load_dialog_summary_map(str(path or _DEFAULT_SUMMARY_MAP_PATH))


def runtime_dialog_scene_key(value) -> str:
    """Map a WebUI conversation key back to the game's runtime dialog key."""
    key = str(value or "").strip()
    if key.startswith("misc_dlg_"):
        return key[len("misc_") :]
    return key


def registry_lines_by_trunk(info: dict | None) -> dict[str, list[str]]:
    """Return normalized DialogIdTable trunk -> line refs for debug output."""
    if not isinstance(info, dict):
        return {}
    raw = info.get("linesByTrunk")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for trunk, values in raw.items():
        if not isinstance(values, list):
            continue
        ids = [str(value).strip() for value in values if str(value or "").strip()]
        if ids:
            out[str(trunk)] = ids
    return out


def registry_options_by_group(info: dict | None) -> dict[str, list[str]]:
    """Return normalized DialogIdTable option group -> option ids."""
    if not isinstance(info, dict):
        return {}
    raw = info.get("optionsByGroup")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for group, values in raw.items():
        if not isinstance(values, list):
            continue
        ids = [str(value).strip() for value in values if str(value or "").strip()]
        if ids:
            out[str(group)] = ids
    return out


def _scene_registry_state(
    conv: dict, dialog_id_registry: dict | None
) -> tuple[str, dict | None, bool]:
    """Return (runtime sceneKey, registry info, registry_loaded)."""
    if dialog_id_registry is None:
        dialog_id_registry = load_dialog_id_registry()
    registry_loaded = bool(dialog_id_registry)
    scene_key = runtime_dialog_scene_key(conv.get("key"))
    if not scene_key:
        return "", None, registry_loaded
    info = dialog_id_registry.get(scene_key) if registry_loaded else None
    return scene_key, info if isinstance(info, dict) else None, registry_loaded


def build_runtime_registry_debug(
    conv: dict,
    *,
    dialog_id_registry: dict | None = None,
    dialog_summary_map: dict | None = None,
) -> dict | None:
    """Build the `_debug.runtimeRegistry` evidence block for a dialog scene."""
    scene_key, info, registry_loaded = _scene_registry_state(conv, dialog_id_registry)
    if not registry_loaded or not scene_key.startswith("dlg_"):
        return None

    if dialog_summary_map is None:
        dialog_summary_map = load_dialog_summary_map()
    summary_key = dialog_summary_map.get(scene_key) if scene_key else None

    webui_key = str(conv.get("key") or "").strip()
    line_count_webui = len(conv.get("lines") or [])
    if info is None:
        out = {
            "registered": False,
            "sceneKey": scene_key,
            "lineCountWebui": line_count_webui,
            "reason": (
                "sceneKey is not present in Beyond.Gameplay.DialogIdTable; "
                "the runtime DialogManager has no entry point for this scene, "
                "so it cannot be loaded from gameplay. The DialogTextTable rows "
                "still exist, so this looks like cut or unreferenced content."
            ),
        }
        if webui_key and webui_key != scene_key:
            out["webuiKey"] = webui_key
        # A summary entry for an unregistered scene is suspicious -- the
        # game data declares a summary for a scene that cannot be loaded.
        # Surface it as evidence; don't change the reason.
        if summary_key:
            out["hasSummary"] = True
            out["summaryKey"] = summary_key
            out["summaryNote"] = (
                "DialogSummaryMapTable references this scene even though "
                "DialogIdTable doesn't -- possible regression in the runtime "
                "registry, or summary data left behind after the scene was cut"
            )
        else:
            out["hasSummary"] = False
        return out

    out = {
        "registered": True,
        "sceneKey": scene_key,
        "trunkCount": info.get("trunkCount", 0),
        "trunkIndices": info.get("trunkIndices", []),
        "lineCount": info.get("lineCount", 0),
        "lineCountWebui": line_count_webui,
        "hasRootKey": info.get("hasRootKey", False),
        "reason": "sceneKey is registered in Beyond.Gameplay.DialogIdTable",
    }
    if summary_key:
        out["hasSummary"] = True
        out["summaryKey"] = summary_key
    else:
        out["hasSummary"] = False
    if webui_key and webui_key != scene_key:
        out["webuiKey"] = webui_key
    lines_by_trunk = registry_lines_by_trunk(info)
    if lines_by_trunk:
        out["linesByTrunk"] = lines_by_trunk
    options_by_group = registry_options_by_group(info)
    if options_by_group:
        out["optionGroupCount"] = len(options_by_group)
        out["optionCount"] = sum(len(values) for values in options_by_group.values())
        out["optionsByGroup"] = options_by_group
    runtime_lines = info.get("lineCount", 0)
    if runtime_lines and runtime_lines != line_count_webui:
        delta = line_count_webui - runtime_lines
        out["lineCountDelta"] = delta
        if delta > 0:
            # Webui shows more lines than the registry addresses by trunk id.
            # Common interpretation: the extras are summary/hint rows that
            # DialogTrunkBehaviour wouldn't address.
            out["note"] = (
                f"webui has {line_count_webui} line(s) but DialogIdTable's "
                f"per-trunk line entries total {runtime_lines}; the extra "
                f"{delta} webui line(s) may be summary/hint rows that the "
                "runtime doesn't address by trunk id"
            )
        else:
            # Webui shows fewer lines than the registry addresses. The
            # runtime expects more lines than the recovered scene shows --
            # the missing lines may live in another DialogTextTable row that
            # didn't make it into this conv (e.g. a sibling subscene), or
            # the recovery is incomplete.
            out["note"] = (
                f"webui has {line_count_webui} line(s) but DialogIdTable's "
                f"per-trunk line entries total {runtime_lines}; the runtime "
                f"addresses {-delta} more line(s) than this conv exposes -- "
                "the recovery may be incomplete or the extra lines live in a "
                "sibling subscene"
            )
    return out


AUTHORED_LINE_ORDER_MODES = {
    "authoredBlend",
    "authoredNumericStitch",
    "dialogTimeline",
    "dialogTree",
    "dialogTreeCinematicTimeline",
    "dialogTreeExtraConfig",
    "dialogTreeFragment",
}

OPTION_LAYOUT_REASON_TITLES = {
    "noTreeReference": "no AnimeStudio option reference",
    "noAuthoredGroupAnchor": "no authored group anchor",
    "partialAuthoredCoverage": "partial authored group coverage",
    "inferredOptionLayout": "inferred option placement",
    "ok": "authored option anchors",
    "notNeeded": "not needed",
}

OPTION_LAYOUT_REASON_DESCRIPTIONS = {
    "noTreeReference": (
        "no AnimeStudio tree references any option id for this scene, so every "
        "option group's position is unanchored; fallback candidates are "
        "reported only as diagnostics"
    ),
    "noAuthoredGroupAnchor": (
        "tree data exists for some options, but no group received an authored "
        "`after` or `pre` anchor; fallback candidates are reported only as diagnostics"
    ),
    "partialAuthoredCoverage": (
        "some option groups stayed on authored anchors while others only have "
        "diagnostic fallback candidates"
    ),
    "inferredOptionLayout": "option placement is inferred rather than fully anchored",
}

LINE_ORDER_PATTERN_TITLES = {
    "ok": "authored order",
    "notNeeded": "not needed",
    "partialAuthoredCoverage": "partial authored coverage",
    "numericSuffixFallback": "numeric-suffix fallback",
    "missingBlockButSuffixSortable": "missing block, suffix-sortable",
    "missingBlockNoSafeFallback": "missing block, unsafe raw ids",
    "otherFallbackMode": "other fallback mode",
    "fallbackWithoutMode": "fallback without mode",
}

LINE_ORDER_PATTERN_DESCRIPTIONS = {
    "partialAuthoredCoverage": (
        "authored line-order data exists, but it does not cover every scene "
        "line, so the uncovered lines still rely on raw table order."
    ),
    "numericSuffixFallback": (
        "authored line order is missing, so the report keeps this scene in the "
        "generic fallback-order bucket. This broad bucket covers cinematic-only "
        "trees, missing-tree scenes, and other unsupported authored-order cases."
    ),
    "missingBlockButSuffixSortable": (
        "the builder omitted `_debug.lineOrder`, but the raw line ids still look "
        "safe to sort by numeric suffix."
    ),
    "missingBlockNoSafeFallback": (
        "the builder omitted `_debug.lineOrder`, and the raw line ids do not "
        "support a safe numeric-suffix fallback."
    ),
    "otherFallbackMode": (
        "the builder recorded a fallback mode other than the standard numeric-"
        "suffix emulation."
    ),
    "fallbackWithoutMode": (
        "a fallback line-order block exists, but it does not declare which mode "
        "produced it."
    ),
}

OPTION_POSITION_PATTERN_TITLES = {
    "ok": "authored positions",
    "notNeeded": "not needed",
    "syntheticAfterAllGroups": "all groups have fallback candidates",
    "mixedAuthoredAndSyntheticAfter": "mixed authored + fallback candidates",
    "unanchoredAllGroups": "all groups unanchored",
    "mixedSyntheticAfterAndUnanchored": "mixed fallback candidates + unanchored",
    "mixedAuthoredAndUnanchored": "mixed authored + unanchored",
    "mixedAuthoredFallbackAndUnanchored": "mixed authored + candidates + unanchored",
    "genericInferredPositions": "generic inferred positions",
}

OPTION_POSITION_PATTERN_DESCRIPTIONS = {
    "syntheticAfterAllGroups": (
        "every meaningful option group lacked an authored position, so the "
        "report lists fallback `after` candidates without treating them as authored."
    ),
    "mixedAuthoredAndSyntheticAfter": (
        "some option groups keep authored positions while the remaining groups "
        "only have fallback `after` candidates."
    ),
    "unanchoredAllGroups": (
        "no option group has a usable authored position or fallback "
        "anchor, so every group remains unanchored."
    ),
    "mixedSyntheticAfterAndUnanchored": (
        "some option groups have fallback `after` candidates, while "
        "others still remain unanchored."
    ),
    "mixedAuthoredAndUnanchored": (
        "some option groups keep authored positions, while others remain "
        "unanchored."
    ),
    "mixedAuthoredFallbackAndUnanchored": (
        "the scene mixes authored option positions, fallback `after` candidates, "
        "and fully unanchored groups."
    ),
    "genericInferredPositions": (
        "option positions were inferred, but the missing-position pattern did not "
        "fit the standard simplified buckets."
    ),
}


def has_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_line_ids(values) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text:
            out.append(text)
    return out


def _line_id_suffix(line_id: str) -> int | None:
    match = re.search(r"_(\d+)$", line_id)
    return int(match.group(1)) if match else None


def _summarize_items(values: list[str], limit: int = 5) -> str:
    clean = [str(value) for value in values if str(value).strip()]
    if not clean:
        return ""
    if len(clean) <= limit:
        return ", ".join(clean)
    return ", ".join(clean[:limit]) + f", +{len(clean) - limit} more"


def _escape_table_text(text: str) -> str:
    return str(text).replace("|", "\\|")


def _as_int(value, default: int = 0) -> int:
    return value if isinstance(value, int) else default


def _count_meaningful_lines(conv: dict) -> int:
    return sum(
        1
        for line in (conv.get("lines") or [])
        if isinstance(line, dict)
        and (
            has_text(line.get("actor"))
            or has_text(line.get("text"))
            or has_text(line.get("hint"))
        )
    )


def has_meaningful_lines(conv: dict) -> bool:
    return _count_meaningful_lines(conv) > 0 and len(conv.get("lines") or []) > 1


def _count_meaningful_options(conv: dict) -> int:
    return sum(
        1
        for group in (conv.get("optionGroups") or [])
        if isinstance(group, dict)
        for option in (group.get("options") or [])
        if isinstance(option, dict) and has_text(option.get("text"))
    )


def has_meaningful_options(conv: dict) -> bool:
    return _count_meaningful_options(conv) > 0


def _line_order_input_ids(conv: dict, line_order: dict | None) -> list[str]:
    if isinstance(line_order, dict):
        original = _normalize_line_ids(line_order.get("originalLineIds"))
        if original:
            return original
    return _normalize_line_ids([
        line.get("id")
        for line in (conv.get("lines") or [])
        if isinstance(line, dict)
    ])


def _line_order_output_ids(conv: dict, line_order: dict | None) -> list[str]:
    if isinstance(line_order, dict):
        ordered = _normalize_line_ids(line_order.get("orderedLineIds"))
        if ordered:
            return ordered
    return _line_order_input_ids(conv, line_order)


def _option_branch_line_ids(conv: dict) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(values) -> None:
        for line_id in _normalize_line_ids(values):
            if line_id not in seen:
                seen.add(line_id)
                out.append(line_id)

    for group in (conv.get("optionGroups") or []):
        if not isinstance(group, dict):
            continue
        risk = group.get("optionBranchRisk")
        if isinstance(risk, dict):
            add(risk.get("lineIds"))
            by_option = risk.get("branchLineIdsByOption")
            if isinstance(by_option, dict):
                for values in by_option.values():
                    add(values)
        for option in (group.get("options") or []):
            if not isinstance(option, dict):
                continue
            add(option.get("branchLines"))
            add(option.get("pathLineIds"))
    return out


def _moved_line_ids(original_ids: list[str], ordered_ids: list[str]) -> list[str]:
    original_index = {line_id: idx for idx, line_id in enumerate(original_ids)}
    return [
        line_id
        for idx, line_id in enumerate(ordered_ids)
        if original_index.get(line_id) != idx
    ]


def _line_id_suffix_diagnostics(line_ids: list[str]) -> dict:
    missing_suffix_ids: list[str] = []
    suffix_map: dict[int, list[str]] = {}
    for line_id in line_ids:
        suffix = _line_id_suffix(line_id)
        if suffix is None:
            missing_suffix_ids.append(line_id)
            continue
        suffix_map.setdefault(suffix, []).append(line_id)
    duplicate_suffixes = [
        {
            "suffix": suffix,
            "lineIds": ids,
        }
        for suffix, ids in sorted(suffix_map.items())
        if len(ids) > 1
    ]
    usable = bool(line_ids) and not missing_suffix_ids and not duplicate_suffixes
    return {
        "usable": usable,
        "missingSuffixLineIds": missing_suffix_ids,
        "duplicateSuffixes": duplicate_suffixes,
    }


def _summarize_line_order_source(source: dict, line_count: int) -> dict:
    kind = str(source.get("kind") or "unknown")
    source_key = str(source.get("sourceKey") or "")
    file_path = str(source.get("file") or "")
    matched_line_ids = _normalize_line_ids(source.get("matchedLineIds"))
    added_line_ids = _normalize_line_ids(source.get("addedLineIds")) or matched_line_ids
    coverage = source.get("coverage")
    if not isinstance(coverage, int):
        coverage = len(matched_line_ids)

    detail_parts = [kind]
    if source_key:
        detail_parts.append(f"source={source_key}")
    detail_parts.append(f"covers {coverage}/{line_count} line(s)")
    if added_line_ids:
        detail_parts.append(f"adds {len(added_line_ids)} line(s)")
    elif matched_line_ids:
        detail_parts.append(f"matches {len(matched_line_ids)} line id(s)")
    if file_path:
        detail_parts.append(f"file={file_path}")

    return {
        "kind": kind,
        "sourceKey": source_key,
        "file": file_path,
        "coverage": coverage,
        "matchedLineIds": matched_line_ids,
        "addedLineIds": added_line_ids,
        "detail": "; ".join(detail_parts),
    }


def _scene_registry_info(conv: dict, dialog_id_registry: dict | None) -> dict | None:
    """Look up this scene in the DialogIdTable runtime registry, if loaded."""
    _scene_key, info, _registry_loaded = _scene_registry_state(conv, dialog_id_registry)
    return info


# Tables in the game's structured data that define inherent authored line
# ordering for scenes whose lines are sourced from them. Each entry maps the
# table identifier (as it appears in `line._debug.table`) to a (mode, reason)
# pair used in the lineOrder recovery output.
#
# Evidence: every line in a webui conv carries a `_debug.table` field naming
# the source table. For scenes whose lines all come from one of these
# tables, the runtime consumes them in table-list order, and our recovery
# already emits them in that order. Citing the table is the missing step.
AUTHORED_SOURCE_TABLES: dict[str, tuple[str, str]] = {
    "RadioTable.radioSingleDataList":           ("radioTable",           "RadioTable.radioSingleDataList (explicit index ordering)"),
    "SNSDialogTable.dialogContentData":         ("snsDialogTable",       "SNSDialogTable.dialogContentData"),
    "EnvTalkTable.envTalkDataList":             ("envTalkTable",         "EnvTalkTable.envTalkDataList"),
    "RemoteCommonTable.remoteCommSingleDataList": ("remoteCommonTable",  "RemoteCommonTable.remoteCommSingleDataList"),
    "RichContentTable.contentList":             ("richContentTable",     "RichContentTable.contentList"),
    "CharacterTable.profileVoice":              ("characterProfileVoice","CharacterTable.profileVoice"),
    "CharacterTable.profileRecord":             ("characterProfileRecord","CharacterTable.profileRecord"),
    "WikiTutorialPageTable":                    ("wikiTutorialPageTable","WikiTutorialPageTable"),
    "WikiEntryDataTable":                       ("wikiEntryDataTable",   "WikiEntryDataTable"),
    "ItemTable":                                ("itemTable",            "ItemTable"),
    "TextTable":                                ("textTable",            "TextTable"),
    "LoadingTipsTable":                         ("loadingTipsTable",     "LoadingTipsTable"),
    "EnemyTemplateDisplayInfoTable":            ("enemyDisplayTable",    "EnemyTemplateDisplayInfoTable"),
    "WeaponBasicTable":                         ("weaponBasicTable",     "WeaponBasicTable"),
    "MailTemplateTable":                        ("mailTemplateTable",    "MailTemplateTable"),
    "PrtsNote":                                 ("prtsNote",             "PrtsNote"),
    "TrainingDeathTips":                        ("trainingDeathTips",    "TrainingDeathTips"),
    # `responsive_*` scenes are voice-clip enumerations keyed by gameplay
    # triggers (combat_battle_defeat etc.). Source is AIBarkText, surfaced
    # through ResponsiveDialog. There's no inherent line sequence -- each
    # line is its own trigger -- so the presented order is just the
    # AIBarkText table layout.
    "AIBarkText":                               ("aiBarkText",           "AIBarkText (ResponsiveDialog, trigger-keyed)"),
}


def _line_source_identifier(line: dict) -> str:
    """
    Return the best authored-source identifier for a line.

    Most lines carry `_debug.table` directly (e.g. RadioTable.radioSingleDataList).
    Some kinds of lines stash the table in `_debug.source.source` instead -- for
    example, ResponsiveDialog scenes synthesise lines from AIBarkText and put
    the source name under `_debug.source.source`. Either form counts.
    """
    if not isinstance(line, dict):
        return ""
    dbg = line.get("_debug")
    if not isinstance(dbg, dict):
        return ""
    table = dbg.get("table")
    if isinstance(table, str) and table:
        return table
    src = dbg.get("source")
    if isinstance(src, dict):
        nested = src.get("source")
        if isinstance(nested, str) and nested:
            return nested
        nested_table = src.get("table")
        if isinstance(nested_table, str) and nested_table:
            return nested_table
    return ""


def _detect_authored_source_table(conv: dict) -> dict | None:
    """
    If every line in the scene comes from a known authored source table or
    set of authored source tables, return a dict describing the recovery.
    Otherwise return None.

    Result shape:
      {
        "mode":          str,                       # reasonCode to emit
        "reason":        str,                       # human-readable reason
        "lineCount":     int,                       # number of lines covered
        "sourceTables":  list[str],                 # authored tables involved
      }
    """
    lines = conv.get("lines") or []
    if not lines:
        return None
    tables: list[str] = []
    for line in lines:
        ident = _line_source_identifier(line)
        if not ident:
            return None  # any line without an identifiable source disqualifies
        if ident not in AUTHORED_SOURCE_TABLES:
            return None  # unknown source -- can't claim authored order
        tables.append(ident)
    unique = list(dict.fromkeys(tables))  # preserve first-seen order
    if len(unique) == 1:
        mode, reason = AUTHORED_SOURCE_TABLES[unique[0]]
    else:
        mode = "multiTableAuthored"
        labels = ", ".join(AUTHORED_SOURCE_TABLES[t][1] for t in unique)
        reason = f"authored sources combined ({labels})"
    return {
        "mode": mode,
        "reason": reason,
        "lineCount": len(lines),
        "sourceTables": unique,
    }


def analyze_line_order(conv: dict, *, dialog_id_registry: dict | None = None) -> dict:
    total_line_count = len(conv.get("lines") or [])
    meaningful_line_count = _count_meaningful_lines(conv)
    debug = conv.get("_debug") or {}
    line_order = debug.get("lineOrder") if isinstance(debug, dict) else None
    input_line_ids = _line_order_input_ids(conv, line_order if isinstance(line_order, dict) else None)
    ordered_line_ids = _line_order_output_ids(conv, line_order if isinstance(line_order, dict) else None)
    registry_scene_key, registry_info, registry_loaded = _scene_registry_state(
        conv, dialog_id_registry
    )

    if not has_meaningful_lines(conv):
        return {
            "status": "direct",
            "statusLabel": "not needed",
            "reasonCode": "notNeeded",
            "reason": "not needed (no multi-line spoken content)",
            "detail": (
                f"scene has {meaningful_line_count} meaningful line(s) across "
                f"{total_line_count} stored line(s), so explicit line-order recovery "
                "is not needed"
            ),
            "evidence": [],
            "mode": "",
            "sources": [],
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
        }

    if not isinstance(line_order, dict):
        # Upgrade path: when every line in this conv comes from a known
        # authored source table (RadioTable, SNSDialogTable, EnvTalkTable,
        # etc.), the runtime consumes them in that table's natural order
        # and our recovery emits them in the same order. Each line's
        # `_debug.table` cites the source -- we just need to read it.
        authored_source = _detect_authored_source_table(conv)
        if authored_source is not None:
            mode = authored_source["mode"]
            reason = authored_source["reason"]
            line_count = authored_source["lineCount"]
            sources_evidence = ", ".join(authored_source["sourceTables"])
            return {
                "status": "direct",
                "statusLabel": "has line order",
                "reasonCode": mode,
                "reason": f"authored line order via {reason}",
                "detail": (
                    f"every line cites an authored source table ({sources_evidence}) "
                    f"in its `_debug` block; the runtime consumes those entries in "
                    f"the order they appear in the source table(s)"
                ),
                "evidence": [
                    f"{meaningful_line_count} meaningful line(s) across {total_line_count} stored line(s)",
                    f"all {line_count} lines sourced from authored table(s): {sources_evidence}",
                ],
                "mode": mode,
                "sources": [{
                    "kind": mode,
                    "sourceKey": tbl,
                    "coverage": sum(1 for line in (conv.get("lines") or []) if _line_source_identifier(line) == tbl),
                    "matchedLineIds": [line.get("id", "") for line in (conv.get("lines") or []) if _line_source_identifier(line) == tbl],
                    "addedLineIds": [],
                    "detail": f"lines sourced from {tbl}",
                } for tbl in authored_source["sourceTables"]],
                "orderedLineIds": ordered_line_ids,
                "originalLineIds": input_line_ids,
                "coveredLineIds": list(input_line_ids),
                "uncoveredLineIds": [],
                "coveredLineCount": line_count,
                "uncoveredLineCount": 0,
            }

        suffix_diag = _line_id_suffix_diagnostics(input_line_ids)
        evidence = [
            f"{meaningful_line_count} meaningful line(s) across {total_line_count} stored line(s)",
        ]
        if suffix_diag["missingSuffixLineIds"]:
            evidence.append(
                "numeric suffix fallback unavailable because some line ids lack "
                "an `_NNN` suffix"
            )
        if suffix_diag["duplicateSuffixes"]:
            evidence.append(
                "numeric suffix fallback unavailable because suffixes are not unique"
            )
        if input_line_ids and suffix_diag["usable"]:
            evidence.append(
                "raw line ids appear suffix-sortable, so the missing line-order "
                "block is unexpected"
            )
            detail = (
                "builder produced no `_debug.lineOrder` even though the raw line ids "
                "look compatible with numeric suffix fallback"
            )
        else:
            detail = (
                "builder produced no `_debug.lineOrder`, and the raw line ids do not "
                "provide a safe numeric suffix fallback"
            )
        return {
            "status": "missing",
            "statusLabel": "missing line order",
            "reasonCode": "noLineOrderBlock",
            "reason": "no recovered line-order block",
            "detail": detail,
            "evidence": evidence,
            "mode": "",
            "sources": [],
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
        }

    mode = str(line_order.get("mode") or "")
    line_count = len(ordered_line_ids)
    sources = [
        _summarize_line_order_source(source, line_count)
        for source in (line_order.get("sources") or [])
        if isinstance(source, dict)
    ]
    moved_line_ids = _moved_line_ids(input_line_ids, ordered_line_ids)
    evidence = [
        f"{meaningful_line_count} meaningful line(s) across {total_line_count} stored line(s)",
        f"builder emitted {line_count} ordered line id(s)",
    ]
    if moved_line_ids:
        evidence.append(
            f"{len(moved_line_ids)} line(s) moved relative to the raw table order"
        )
    elif input_line_ids and ordered_line_ids:
        evidence.append("final order matches the raw line table order")
    for source in sources:
        evidence.append(source["detail"])

    covered_line_ids: list[str] = []
    seen_covered: set[str] = set()
    for source in sources:
        for line_id in _normalize_line_ids(source.get("matchedLineIds")):
            if line_id not in seen_covered:
                seen_covered.add(line_id)
                covered_line_ids.append(line_id)
    uncovered_line_ids = [
        line_id
        for line_id in input_line_ids
        if line_id and line_id not in seen_covered
    ]
    branch_line_ids = set(_option_branch_line_ids(conv))
    branch_covered_line_ids = [
        line_id for line_id in uncovered_line_ids if line_id in branch_line_ids
    ]
    if branch_covered_line_ids:
        for line_id in branch_covered_line_ids:
            if line_id not in seen_covered:
                seen_covered.add(line_id)
                covered_line_ids.append(line_id)
        uncovered_line_ids = [
            line_id for line_id in uncovered_line_ids if line_id not in branch_line_ids
        ]
        evidence.append(
            f"{len(branch_covered_line_ids)} line(s) are covered by option branch payloads: "
            f"{_summarize_items(branch_covered_line_ids, limit=8)}"
        )
    if uncovered_line_ids:
        evidence.append(
            f"{len(uncovered_line_ids)} line(s) not covered by authored sources: "
            f"{_summarize_items(uncovered_line_ids, limit=8)}"
        )

    if mode in AUTHORED_LINE_ORDER_MODES:
        if uncovered_line_ids:
            detail = (
                f"authored line order recovered through `{mode}`, but "
                f"{len(uncovered_line_ids)} line(s) were not covered: "
                f"{_summarize_items(uncovered_line_ids, limit=8)}"
            )
            return {
                "status": "partial",
                "statusLabel": "partial authored line order",
                "reasonCode": "partialAuthoredCoverage",
                "reason": "partial authored line order",
                "detail": detail,
                "evidence": evidence,
                "mode": mode,
                "sources": sources,
                "orderedLineIds": ordered_line_ids,
                "originalLineIds": input_line_ids,
                "coveredLineIds": covered_line_ids,
                "uncoveredLineIds": uncovered_line_ids,
                "branchCoveredLineIds": branch_covered_line_ids,
                "coveredLineCount": len(covered_line_ids),
                "uncoveredLineCount": len(uncovered_line_ids),
            }
        reason = "direct dialogTree order" if mode == "dialogTree" else f"authored order via {mode}"
        detail = (
            "own AnimeStudio tree supplies the full line order"
            if mode == "dialogTree"
            else f"authored line order recovered through `{mode}`"
        )
        return {
            "status": "direct",
            "statusLabel": "has line order",
            "reasonCode": mode,
            "reason": reason,
            "detail": detail,
            "evidence": evidence,
            "mode": mode,
            "sources": sources,
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
            "coveredLineIds": covered_line_ids,
            "uncoveredLineIds": uncovered_line_ids,
            "branchCoveredLineIds": branch_covered_line_ids,
            "coveredLineCount": len(covered_line_ids),
            "uncoveredLineCount": len(uncovered_line_ids),
        }

    # `lineIdSuffix` and `compoundNumericSuffix` are both "DialogTextTable
    # row-order" fallbacks emitted by the Story builder when no Timeline / dialogTree
    # source covers the scene. The same evidence chain upgrades both:
    # - if the rows in this scene weren't reordered relative to raw table
    #   order, then *any* iteration strategy DialogTrunkBehaviour might use
    #   (suffix-sort or raw walk) produces the same sequence;
    # - DialogIdTable presence/absence then tells us whether this scene can
    #   even be loaded by the runtime.
    if mode in ("lineIdSuffix", "compoundNumericSuffix"):
        upgrade_ok = not moved_line_ids and input_line_ids and ordered_line_ids

        if (
            upgrade_ok
            and registry_loaded
            and registry_scene_key.startswith("dlg_")
            and registry_info is None
        ):
            # Scene is absent from DialogIdTable (the runtime's authoritative
            # dialog registry). The runtime has no entry point for this scene
            # -- DialogManager looks every dialog up through this registry. So
            # the scene's text rows in DialogTextTable are dead/unreachable
            # content. The presented order is just data layout; there is no
            # runtime order to be wrong about.
            evidence.append(
                "scene is not in DialogIdTable -- runtime never loads it; "
                "presented order is DialogTextTable layout only"
            )
            if registry_scene_key != conv.get("key"):
                evidence.append(
                    f"webui key {conv.get('key')} maps to runtime sceneKey {registry_scene_key}"
                )
            return {
                "status": "direct",
                "statusLabel": "has line order",
                "reasonCode": "unregisteredScene",
                "reason": "scene not registered with runtime (cut/dead content)",
                "detail": (
                    "scene is absent from DialogIdTable (Endfield's runtime "
                    "dialog registry); DialogManager has no entry point to "
                    "load it, so the order is academic and matches "
                    "DialogTextTable layout"
                ),
                "evidence": evidence,
                "mode": mode,
                "sources": sources,
                "orderedLineIds": ordered_line_ids,
                "originalLineIds": input_line_ids,
                "coveredLineIds": covered_line_ids,
                "uncoveredLineIds": uncovered_line_ids,
                "coveredLineCount": len(covered_line_ids),
                "uncoveredLineCount": len(uncovered_line_ids),
            }

        if upgrade_ok and registry_info is not None:
            # Scene IS in DialogIdTable but no Timeline / dialogTree source
            # was found. DialogManager / DialogTrunkBehaviour is the only
            # runtime path, and it iterates DialogTextTable rows by sceneKey
            # prefix. Since suffix order equals raw table order here, that
            # iteration produces exactly this sequence.
            trunk_count = registry_info.get("trunkCount", 0)
            line_count_in_table = registry_info.get("lineCount", 0)
            evidence.append(
                "scene IS in DialogIdTable "
                f"({trunk_count} trunk(s), {line_count_in_table} runtime line ref(s)); "
                "DialogTrunkBehaviour iterates DialogTextTable rows by prefix"
            )
            if registry_scene_key != conv.get("key"):
                evidence.append(
                    f"webui key {conv.get('key')} maps to runtime sceneKey {registry_scene_key}"
                )
            return {
                "status": "direct",
                "statusLabel": "has line order",
                "reasonCode": "dialogTrunkRowIteration",
                "reason": "runtime row iteration (DialogTrunkBehaviour)",
                "detail": (
                    "scene is registered in DialogIdTable but has no Timeline "
                    "asset or dialogTree source; DialogTrunkBehaviour walks "
                    "DialogTextTable rows by sceneKey prefix in table order, "
                    "which equals the suffix-sorted order here"
                ),
                "evidence": evidence,
                "mode": mode,
                "sources": sources,
                "orderedLineIds": ordered_line_ids,
                "originalLineIds": input_line_ids,
                "coveredLineIds": covered_line_ids,
                "uncoveredLineIds": uncovered_line_ids,
                "coveredLineCount": len(covered_line_ids),
                "uncoveredLineCount": len(uncovered_line_ids),
            }
        return {
            "status": "fallback",
            "statusLabel": "fallback line order",
            "reasonCode": mode,
            "reason": "fallback line order",
            "detail": "no authored line-order source matched this scene",
            "evidence": evidence,
            "mode": mode,
            "sources": sources,
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
            "coveredLineIds": covered_line_ids,
            "uncoveredLineIds": uncovered_line_ids,
            "coveredLineCount": len(covered_line_ids),
            "uncoveredLineCount": len(uncovered_line_ids),
        }

    if mode:
        return {
            "status": "fallback",
            "statusLabel": "fallback line order",
            "reasonCode": f"fallback:{mode}",
            "reason": f"fallback order via {mode}",
            "detail": f"line-order block exists, but it uses fallback mode `{mode}`",
            "evidence": evidence,
            "mode": mode,
            "sources": sources,
            "orderedLineIds": ordered_line_ids,
            "originalLineIds": input_line_ids,
            "coveredLineIds": covered_line_ids,
            "uncoveredLineIds": uncovered_line_ids,
            "coveredLineCount": len(covered_line_ids),
            "uncoveredLineCount": len(uncovered_line_ids),
        }

    return {
        "status": "fallback",
        "statusLabel": "fallback line order",
        "reasonCode": "fallback:unknown",
        "reason": "fallback order",
        "detail": "line-order block exists, but it does not declare a recovery mode",
        "evidence": evidence,
        "mode": "",
        "sources": sources,
        "orderedLineIds": ordered_line_ids,
        "originalLineIds": input_line_ids,
        "coveredLineIds": covered_line_ids,
        "uncoveredLineIds": uncovered_line_ids,
        "coveredLineCount": len(covered_line_ids),
        "uncoveredLineCount": len(uncovered_line_ids),
    }


def inferred_option_warning(conv: dict) -> dict | None:
    if not has_meaningful_options(conv):
        return None
    for warning in (conv.get("warnings") or []):
        if isinstance(warning, dict) and warning.get("code") == "inferredOptionLayout":
            return warning
    return None


def inferred_option_response_warning(conv: dict) -> dict | None:
    if not has_meaningful_options(conv):
        return None
    for warning in (conv.get("warnings") or []):
        if isinstance(warning, dict) and warning.get("code") == "inferredOptionResponse":
            return warning
    return None


def _normalize_group_details(conv: dict, warning: dict | None) -> list[dict]:
    if isinstance(warning, dict):
        raw_group_details = warning.get("groupDetails") or []
        normalized: list[dict] = []
        for raw in raw_group_details:
            if not isinstance(raw, dict):
                continue
            group_value = raw.get("group")
            label = f"g{group_value}" if isinstance(group_value, int) else "g?"
            normalized.append({
                "group": group_value,
                "label": label,
                "status": str(raw.get("status") or "unknown"),
                "after": str(raw.get("after") or raw.get("fallbackAnchorId") or ""),
                "position": str(raw.get("position") or ""),
                "inferredAnchorMode": str(raw.get("inferredAnchorMode") or ""),
                "optionIds": _normalize_line_ids(raw.get("optionIds")),
                "authoredOptionIds": _normalize_line_ids(raw.get("authoredOptionIds")),
                "unauthoredOptionIds": _normalize_line_ids(raw.get("unauthoredOptionIds")),
                "treeAfterOptionIds": _normalize_line_ids(raw.get("treeAfterOptionIds")),
                "sceneLinkAfterOptionIds": _normalize_line_ids(raw.get("sceneLinkAfterOptionIds")),
                "timelineAfterOptionIds": _normalize_line_ids(raw.get("timelineAfterOptionIds")),
                "cinematicAfterOptionIds": _normalize_line_ids(raw.get("cinematicAfterOptionIds")),
                "textAliasAfterOptionIds": _normalize_line_ids(raw.get("textAliasAfterOptionIds")),
                "textAliasPreOptionIds": _normalize_line_ids(raw.get("textAliasPreOptionIds")),
                "textAliasSourceOptionIds": _normalize_line_ids(raw.get("textAliasSourceOptionIds")),
                "preOptionIds": _normalize_line_ids(raw.get("preOptionIds")),
                "timelinePreOptionIds": _normalize_line_ids(raw.get("timelinePreOptionIds")),
                "cinematicSources": _normalize_line_ids(raw.get("cinematicSources")),
                "textAliasSources": _normalize_line_ids(raw.get("textAliasSources")),
            })
        if normalized:
            return normalized

    fallback_labels = {
        str(label)
        for label in ((warning or {}).get("fallbackGroups") or [])
        if str(label).strip()
    }
    details: list[dict] = []
    for group in (conv.get("optionGroups") or []):
        if not isinstance(group, dict):
            continue
        group_value = group.get("g")
        label = f"g{group_value}" if isinstance(group_value, int) else "g?"
        option_ids = [
            str(option.get("id") or "")
            for option in (group.get("options") or [])
            if isinstance(option, dict) and option.get("id")
        ]
        if label in fallback_labels and group.get("after"):
            status = "fallbackAfter"
        elif label in fallback_labels:
            status = "unanchored"
        elif group.get("position") == "pre":
            status = "authoredPre"
        elif group.get("after"):
            status = "authoredAfter"
        else:
            status = "unanchored"
        details.append({
            "group": group_value,
            "label": label,
            "status": status,
            "after": str(group.get("after") or ""),
            "position": str(group.get("position") or ""),
            "inferredAnchorMode": "",
            "optionIds": option_ids,
            "authoredOptionIds": [],
            "unauthoredOptionIds": [],
            "treeAfterOptionIds": [],
            "sceneLinkAfterOptionIds": [],
            "timelineAfterOptionIds": [],
            "cinematicAfterOptionIds": [],
            "textAliasAfterOptionIds": [],
            "textAliasPreOptionIds": [],
            "textAliasSourceOptionIds": [],
            "preOptionIds": [],
            "timelinePreOptionIds": [],
            "cinematicSources": [],
            "textAliasSources": [],
        })
    return details


def _render_group_detail(group_detail: dict) -> str:
    label = group_detail.get("label") or "g?"
    status = str(group_detail.get("status") or "unknown")
    after = str(group_detail.get("after") or "")
    inferred_anchor_mode = str(group_detail.get("inferredAnchorMode") or "")
    option_ids = _normalize_line_ids(group_detail.get("optionIds"))
    unauthored_option_ids = _normalize_line_ids(group_detail.get("unauthoredOptionIds"))
    tree_after_option_ids = _normalize_line_ids(group_detail.get("treeAfterOptionIds"))
    scene_link_after_option_ids = _normalize_line_ids(group_detail.get("sceneLinkAfterOptionIds"))
    timeline_after_option_ids = _normalize_line_ids(group_detail.get("timelineAfterOptionIds"))
    cinematic_after_option_ids = _normalize_line_ids(group_detail.get("cinematicAfterOptionIds"))
    text_alias_after_option_ids = _normalize_line_ids(group_detail.get("textAliasAfterOptionIds"))
    text_alias_pre_option_ids = _normalize_line_ids(group_detail.get("textAliasPreOptionIds"))
    text_alias_source_option_ids = _normalize_line_ids(group_detail.get("textAliasSourceOptionIds"))
    pre_option_ids = _normalize_line_ids(group_detail.get("preOptionIds"))
    timeline_pre_option_ids = _normalize_line_ids(group_detail.get("timelinePreOptionIds"))

    if status == "authoredAfter":
        detail = f"{label} authored after `{after}`" if after else f"{label} authored after anchor"
    elif status == "keyedAfter":
        detail = f"{label} keyed after `{after}`" if after else f"{label} keyed after matching line"
    elif status == "siblingSceneText":
        detail = (
            f"{label} matched sibling SceneGraph text after `{after}`"
            if after
            else f"{label} matched sibling SceneGraph text"
        )
    elif status == "authoredPre":
        detail = f"{label} authored before scene"
    elif status == "fallbackAfter":
        mode_labels = {
            "sparseGap": "sparse-gap fallback",
            "siblingTimelinePosition": "sibling-timeline fallback",
            "lineNumber": "line-number fallback",
            "lastLine": "last-line fallback",
        }
        fallback_label = mode_labels.get(inferred_anchor_mode, "fallback candidate")
        detail = f"{label} {fallback_label} near `{after}`" if after else f"{label} {fallback_label}"
    elif status == "unanchored":
        detail = f"{label} unanchored"
    else:
        detail = f"{label} {status}"

    extra_bits: list[str] = []
    if option_ids:
        extra_bits.append(f"options: {_summarize_items(option_ids)}")
    if tree_after_option_ids:
        extra_bits.append(f"tree-after: {_summarize_items(tree_after_option_ids)}")
    if scene_link_after_option_ids:
        extra_bits.append(f"scene-link after: {_summarize_items(scene_link_after_option_ids)}")
    if timeline_after_option_ids:
        extra_bits.append(f"timeline after: {_summarize_items(timeline_after_option_ids)}")
    if cinematic_after_option_ids:
        extra_bits.append(f"cinematic-finish after: {_summarize_items(cinematic_after_option_ids)}")
    if text_alias_after_option_ids:
        extra_bits.append(f"text-alias after: {_summarize_items(text_alias_after_option_ids)}")
    if text_alias_source_option_ids:
        extra_bits.append(f"text-alias source: {_summarize_items(text_alias_source_option_ids)}")
    if pre_option_ids:
        extra_bits.append(f"tree-pre: {_summarize_items(pre_option_ids)}")
    if timeline_pre_option_ids:
        extra_bits.append(f"timeline-pre: {_summarize_items(timeline_pre_option_ids)}")
    if text_alias_pre_option_ids:
        extra_bits.append(f"text-alias pre: {_summarize_items(text_alias_pre_option_ids)}")
    if unauthored_option_ids:
        extra_bits.append(f"no authored signal: {_summarize_items(unauthored_option_ids)}")
    if extra_bits:
        detail += " (" + "; ".join(extra_bits) + ")"
    return detail


def analyze_option_layout(
    conv: dict, *, dialog_id_registry: dict | None = None
) -> dict:
    meaningful_option_count = _count_meaningful_options(conv)
    option_groups = [
        group
        for group in (conv.get("optionGroups") or [])
        if isinstance(group, dict)
    ]

    if not has_meaningful_options(conv):
        return {
            "status": "notNeeded",
            "statusLabel": "not needed",
            "reasonCode": "notNeeded",
            "reason": "not needed (no meaningful options)",
            "detail": (
                f"scene has {meaningful_option_count} meaningful option(s) across "
                f"{len(option_groups)} option group(s), so option-position analysis "
                "is not needed"
            ),
            "evidence": [],
            "warning": None,
        }

    warning = inferred_option_warning(conv)
    if warning is None:
        return {
            "status": "authored",
            "statusLabel": "authored option anchors",
            "reasonCode": "ok",
            "reason": "all option groups anchored from authored evidence",
            "detail": (
                f"all {len(option_groups)} option group(s) keep explicit authored "
                "positions in the built scene data"
            ),
            "evidence": [],
            "warning": None,
        }

    reason_code = str(warning.get("reason") or "inferredOptionLayout")
    reason = OPTION_LAYOUT_REASON_TITLES.get(reason_code, reason_code)
    detail = str(
        warning.get("detail")
        or OPTION_LAYOUT_REASON_DESCRIPTIONS.get(
            reason_code,
            "option placement inferred from fallback anchors",
        )
    )
    breakdown = warning.get("groupBreakdown") or {}
    group_details = _normalize_group_details(conv, warning)
    tree_sources = [
        str(source)
        for source in (warning.get("treeSources") or [])
        if str(source).strip()
    ]
    scene_link_sources = [
        str(source)
        for source in (warning.get("sceneLinkSources") or [])
        if str(source).strip()
    ]
    timeline_sources = [
        str(source)
        for source in (warning.get("timelineSources") or [])
        if str(source).strip()
    ]
    cinematic_sources = [
        str(source)
        for source in (warning.get("cinematicSources") or [])
        if str(source).strip()
    ]
    text_alias_sources = [
        str(source)
        for source in (warning.get("textAliasSources") or [])
        if str(source).strip()
    ]
    fallback_anchor_ids = _normalize_line_ids(warning.get("fallbackAnchorIds"))

    evidence: list[str] = [
        f"{meaningful_option_count} meaningful option(s) across {len(option_groups)} option group(s)",
    ]
    registry_scene_key, registry_info, registry_loaded = _scene_registry_state(
        conv, dialog_id_registry
    )
    if (
        registry_loaded
        and registry_scene_key.startswith("dlg_")
        and registry_info is None
    ):
        evidence.append(
            "scene is not in DialogIdTable -- runtime never loads it through "
            "DialogManager; option rows are still source-backed but placement "
            "cannot be confirmed by a runtime entry point"
        )
        if registry_scene_key != conv.get("key"):
            evidence.append(
                f"webui key {conv.get('key')} maps to runtime sceneKey {registry_scene_key}"
            )
    if isinstance(breakdown, dict) and breakdown:
        evidence.append(
            "group breakdown: "
            f"total={int(breakdown.get('total', len(option_groups)))}, "
            f"authoredAfter={int(breakdown.get('authoredAfter', 0))}, "
            f"authoredPre={int(breakdown.get('authoredPre', 0))}, "
            f"keyedAfter={int(breakdown.get('keyedAfter', 0))}, "
            f"siblingSceneText={int(breakdown.get('siblingSceneText', 0))}, "
            f"fallbackAfter={int(breakdown.get('fallbackAfter', 0))}, "
            f"unanchored={int(breakdown.get('unanchored', 0))}"
        )
    if tree_sources:
        evidence.append(f"authored tree sources: {_summarize_items(tree_sources, limit=4)}")
    if scene_link_sources:
        evidence.append(
            f"scene-link sources: {_summarize_items(scene_link_sources, limit=4)}"
        )
    if timeline_sources:
        evidence.append(
            f"timeline sources: {_summarize_items(timeline_sources, limit=4)}"
        )
    if cinematic_sources:
        evidence.append(
            f"cinematic-finish sources: {_summarize_items(cinematic_sources, limit=4)}"
        )
    if text_alias_sources:
        evidence.append(
            f"text-alias sources: {_summarize_items(text_alias_sources, limit=4)}"
        )
    if fallback_anchor_ids:
        evidence.append(
            f"fallback candidate anchors: {_summarize_items(fallback_anchor_ids)}"
        )

    rendered_group_details = [_render_group_detail(detail_row) for detail_row in group_details]
    for rendered in rendered_group_details[:8]:
        evidence.append(rendered)
    if len(rendered_group_details) > 8:
        evidence.append(f"+{len(rendered_group_details) - 8} more group detail(s)")

    return {
        "status": "inferred",
        "statusLabel": "inferred option placement",
        "reasonCode": reason_code,
        "reason": reason,
        "detail": detail,
        "evidence": evidence,
        "warning": warning,
    }


def classify_line_order_failure(analysis: dict) -> dict:
    status = str(analysis.get("status") or "")
    mode = str(analysis.get("mode") or "")

    if status == "direct":
        label = LINE_ORDER_PATTERN_TITLES["ok"]
        return {
            "status": "ok",
            "code": "ok",
            "label": label,
            "summary": str(analysis.get("reason") or "line order comes from authored evidence"),
            "detail": f"mode={mode or 'direct'}",
        }

    if status == "partial":
        uncovered_line_ids = _normalize_line_ids(analysis.get("uncoveredLineIds"))
        detail = (
            f"mode={mode or 'direct'}; "
            f"uncovered={len(uncovered_line_ids)}"
        )
        if uncovered_line_ids:
            detail += f"; lines={_summarize_items(uncovered_line_ids, limit=6)}"
        return {
            "status": "problem",
            "code": "partialAuthoredCoverage",
            "label": LINE_ORDER_PATTERN_TITLES["partialAuthoredCoverage"],
            "summary": LINE_ORDER_PATTERN_DESCRIPTIONS["partialAuthoredCoverage"],
            "detail": detail,
        }

    if status == "missing":
        original_ids = _normalize_line_ids(analysis.get("originalLineIds"))
        suffix_diag = _line_id_suffix_diagnostics(original_ids)
        code = (
            "missingBlockButSuffixSortable"
            if suffix_diag["usable"]
            else "missingBlockNoSafeFallback"
        )
        return {
            "status": "problem",
            "code": code,
            "label": LINE_ORDER_PATTERN_TITLES[code],
            "summary": LINE_ORDER_PATTERN_DESCRIPTIONS[code],
            "detail": (
                f"{len(original_ids)} raw line id(s) inspected; "
                f"mode={mode or 'missing'}"
            ),
        }

    if mode in ("lineIdSuffix", "compoundNumericSuffix"):
        code = "numericSuffixFallback"
    elif mode:
        code = "otherFallbackMode"
    else:
        code = "fallbackWithoutMode"

    detail = f"mode={mode or 'missing'}"
    return {
        "status": "problem",
        "code": code,
        "label": LINE_ORDER_PATTERN_TITLES[code],
        "summary": LINE_ORDER_PATTERN_DESCRIPTIONS[code],
        "detail": detail,
    }


def classify_option_position_failure(conv: dict, analysis: dict) -> dict:
    status = str(analysis.get("status") or "")

    if status == "notNeeded":
        label = OPTION_POSITION_PATTERN_TITLES["notNeeded"]
        return {
            "status": "notNeeded",
            "code": "notNeeded",
            "label": label,
            "summary": "scene has no meaningful options",
            "detail": "",
        }

    if status != "inferred":
        label = OPTION_POSITION_PATTERN_TITLES["ok"]
        return {
            "status": "ok",
            "code": "ok",
            "label": label,
            "summary": "positions come from authored evidence",
            "detail": "",
        }

    warning = analysis.get("warning") if isinstance(analysis.get("warning"), dict) else None
    breakdown = warning.get("groupBreakdown") if isinstance(warning, dict) else {}
    group_details = _normalize_group_details(conv, warning)
    total = _as_int(breakdown.get("total"), len(group_details))
    authored_after = _as_int(breakdown.get("authoredAfter"))
    authored_pre = _as_int(breakdown.get("authoredPre"))
    fallback_after = _as_int(breakdown.get("fallbackAfter"))
    keyed_after = _as_int(breakdown.get("keyedAfter"))
    sibling_scene_text = _as_int(breakdown.get("siblingSceneText"))
    unanchored = _as_int(breakdown.get("unanchored"))
    authored_total = authored_after + authored_pre + keyed_after + sibling_scene_text

    if total and fallback_after == total and not authored_total and not unanchored:
        code = "syntheticAfterAllGroups"
        summary = (
            f"all {total} option group(s) lack authored positions, so the report "
            "lists fallback `after` candidates without treating them as authored"
        )
    elif authored_total and fallback_after and not unanchored:
        code = "mixedAuthoredAndSyntheticAfter"
        summary = (
            f"{authored_total} group(s) keep authored positions; {fallback_after} "
            "group(s) only have fallback `after` candidates"
        )
    elif total and unanchored == total and not authored_total and not fallback_after:
        code = "unanchoredAllGroups"
        summary = (
            f"all {total} option group(s) are missing both authored positions and "
            "usable fallback anchors"
        )
    elif fallback_after and unanchored and not authored_total:
        code = "mixedSyntheticAfterAndUnanchored"
        summary = (
            f"{fallback_after} group(s) have fallback `after` candidates; "
            f"{unanchored} group(s) remain unanchored"
        )
    elif authored_total and unanchored and not fallback_after:
        code = "mixedAuthoredAndUnanchored"
        summary = (
            f"{authored_total} group(s) keep authored positions; {unanchored} "
            "group(s) remain unanchored"
        )
    elif authored_total and fallback_after and unanchored:
        code = "mixedAuthoredFallbackAndUnanchored"
        summary = (
            f"{authored_total} group(s) keep authored positions; {fallback_after} "
            f"group(s) only have fallback `after` candidates; {unanchored} "
            "group(s) remain unanchored"
        )
    else:
        code = "genericInferredPositions"
        summary = OPTION_POSITION_PATTERN_DESCRIPTIONS[code]

    detail = (
        "groups: "
        f"authoredAfter={authored_after}, "
        f"authoredPre={authored_pre}, "
        f"keyedAfter={keyed_after}, "
        f"siblingSceneText={sibling_scene_text}, "
        f"fallbackAfter={fallback_after}, "
        f"unanchored={unanchored}"
    )

    return {
        "status": "problem",
        "code": code,
        "label": OPTION_POSITION_PATTERN_TITLES[code],
        "summary": summary,
        "detail": detail,
    }


def _build_scene_order_disorder_warning_from_analysis(
    conv: dict,
    line_order_analysis: dict,
    option_layout_analysis: dict,
) -> dict | None:
    conv_key = str(conv.get("key") or "")
    accepts_fallback_line_order = conv_key.startswith((
        "misc_sim",
        "misc_blackbox",
        "misc_timeline",
    ))
    problematic_aspects: list[str] = []
    if line_order_analysis["status"] != "direct" and not (
        accepts_fallback_line_order and line_order_analysis["status"] == "fallback"
    ):
        problematic_aspects.append("lineOrder")
    if option_layout_analysis["status"] == "inferred":
        problematic_aspects.append("optionLayout")
    if not problematic_aspects:
        return None

    return {
        "code": "sceneOrderDisorder",
        "problematicAspects": problematic_aspects,
        "summary": (
            "scene order relies on fallback or incomplete authored evidence"
            if len(problematic_aspects) > 1
            else (
                "line order relies on fallback or incomplete authored evidence"
                if problematic_aspects[0] == "lineOrder"
                else "option placement relies on fallback or incomplete authored evidence"
            )
        ),
        "lineOrder": {
            "status": line_order_analysis["status"],
            "statusLabel": line_order_analysis["statusLabel"],
            "reasonCode": line_order_analysis["reasonCode"],
            "summary": line_order_analysis["reason"],
            "detail": line_order_analysis["detail"],
            "evidence": line_order_analysis["evidence"],
            "mode": line_order_analysis["mode"],
            "coveredLineCount": _as_int(line_order_analysis.get("coveredLineCount")),
            "uncoveredLineCount": _as_int(line_order_analysis.get("uncoveredLineCount")),
            "coveredLineIds": _normalize_line_ids(line_order_analysis.get("coveredLineIds")),
            "uncoveredLineIds": _normalize_line_ids(line_order_analysis.get("uncoveredLineIds")),
            "branchCoveredLineIds": _normalize_line_ids(line_order_analysis.get("branchCoveredLineIds")),
        },
        "optionLayout": {
            "status": option_layout_analysis["status"],
            "statusLabel": option_layout_analysis["statusLabel"],
            "reasonCode": option_layout_analysis["reasonCode"],
            "summary": option_layout_analysis["reason"],
            "detail": option_layout_analysis["detail"],
            "evidence": option_layout_analysis["evidence"],
        },
    }


def analyze_scene_order_disorder(
    conv: dict, *, dialog_id_registry: dict | None = None
) -> dict:
    """Return line/order analyses plus the warning payload, computed once."""
    line_order_analysis = analyze_line_order(
        conv, dialog_id_registry=dialog_id_registry
    )
    option_layout_analysis = analyze_option_layout(
        conv, dialog_id_registry=dialog_id_registry
    )
    return {
        "lineOrder": line_order_analysis,
        "optionLayout": option_layout_analysis,
        "warning": _build_scene_order_disorder_warning_from_analysis(
            conv,
            line_order_analysis,
            option_layout_analysis,
        ),
    }


def build_scene_order_disorder_warning(
    conv: dict, *, dialog_id_registry: dict | None = None
) -> dict | None:
    return analyze_scene_order_disorder(
        conv, dialog_id_registry=dialog_id_registry
    )["warning"]


_PLACEMENT_COUNT_FIELDS = {
    "storyRefCount",
    "clientActionCount",
    "sourceBackedEdgeCount",
    "incomingEdgeCount",
    "outgoingEdgeCount",
    "sourceBackedSequenceCount",
    "sequenceNeighborCount",
    "sourceBackedStoryCallContextCount",
    "sourceBackedHashTerminalCount",
    "timelineEvidenceCount",
}

_PLACEMENT_LIST_FIELDS = {
    "evidenceKinds",
    "questIds",
    "storyRefKinds",
    "storyRefSources",
    "clientActionTypes",
    "clientActionSources",
    "incomingEdges",
    "outgoingEdges",
    "sequenceNeighbors",
    "storyCallContexts",
    "hashTerminals",
    "timelines",
    "timelineEvidence",
    "missions",
    "missionFiles",
}


def _append_unique_values(bucket: list, values: list, limit: int = 32) -> None:
    seen = {
        json.dumps(value, ensure_ascii=False, sort_keys=True)
        for value in bucket
    }
    for value in values:
        signature = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if signature in seen:
            continue
        seen.add(signature)
        bucket.append(value)
        if len(bucket) >= limit:
            return


def _merge_scene_placement_row(existing: dict, incoming: dict) -> dict:
    out = dict(existing)
    out.setdefault("sceneKey", incoming.get("sceneKey") or existing.get("sceneKey") or "")
    out.setdefault("kind", incoming.get("kind") or existing.get("kind") or "")
    for field in _PLACEMENT_COUNT_FIELDS:
        out[field] = _as_int(out.get(field)) + _as_int(incoming.get(field))
    for field in _PLACEMENT_LIST_FIELDS:
        values = incoming.get(field)
        if values in (None, "", [], {}):
            continue
        if not isinstance(values, list):
            values = [values]
        bucket = out.setdefault(field, [])
        if not isinstance(bucket, list):
            bucket = [bucket]
            out[field] = bucket
        _append_unique_values(bucket, values)
    return {
        key: value
        for key, value in out.items()
        if value not in (None, "", [], {}, 0)
        or key in {"sceneKey", "kind", "evidenceKinds"}
    }


def _add_scene_placement_rows(
    out: dict[str, dict],
    scene_placement: dict,
    *,
    mission: str,
    mission_file: str | Path | None = None,
) -> None:
    if not isinstance(scene_placement, dict):
        return
    for scene_key, placement in scene_placement.items():
        if not isinstance(placement, dict):
            continue
        key = runtime_dialog_scene_key(scene_key)
        row = dict(placement)
        row.setdefault("sceneKey", key)
        if mission:
            row["missions"] = [mission]
        if mission_file:
            row["missionFiles"] = [str(mission_file).replace("\\", "/")]
        if key in out:
            out[key] = _merge_scene_placement_row(out[key], row)
        else:
            out[key] = row


def build_scene_placement_index_from_timelines(
    mission_timelines: dict[str, dict] | list[dict],
    *,
    mission_files: dict[str, str | Path] | None = None,
) -> dict[str, dict]:
    """Build the scene placement lookup from in-memory mission timelines."""
    out: dict[str, dict] = {}
    if isinstance(mission_timelines, dict):
        iterable = mission_timelines.items()
    else:
        iterable = (
            (str(row.get("mission") or ""), row)
            for row in mission_timelines
            if isinstance(row, dict)
        )
    mission_files = mission_files or {}
    for mission, timeline in iterable:
        if not isinstance(timeline, dict):
            continue
        mission = str(mission or timeline.get("mission") or "")
        _add_scene_placement_rows(
            out,
            timeline.get("scenePlacement") or {},
            mission=mission,
            mission_file=mission_files.get(mission),
        )
    return out


def _load_scene_placement_index(root: Path, conv_dir: Path) -> dict[str, dict]:
    """Load per-scene mission placement signals emitted by the Story builder."""
    mission_dir = conv_dir.parent / "mission"
    if not mission_dir.is_dir():
        return {}
    out: dict[str, dict] = {}
    for path in sorted(mission_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        timeline = payload.get("timelineRecovery")
        if not isinstance(timeline, dict):
            continue
        scene_placement = timeline.get("scenePlacement")
        if not isinstance(scene_placement, dict):
            continue
        mission = str(payload.get("mission") or timeline.get("mission") or path.stem)
        try:
            mission_file = path.relative_to(root)
        except ValueError:
            mission_file = path
        _add_scene_placement_rows(
            out,
            scene_placement,
            mission=mission,
            mission_file=mission_file,
        )
    return out


def _placement_has_story_ref(placement: dict | None) -> bool:
    if not isinstance(placement, dict):
        return False
    return bool(
        int(placement.get("storyRefCount") or 0)
        or int(placement.get("clientActionCount") or 0)
    )


def _placement_has_source_edge(placement: dict | None) -> bool:
    if not isinstance(placement, dict):
        return False
    return bool(int(placement.get("sourceBackedEdgeCount") or 0))


def _placement_has_source_sequence(placement: dict | None) -> bool:
    if not isinstance(placement, dict):
        return False
    return bool(int(placement.get("sourceBackedSequenceCount") or 0))


def _placement_has_story_call_context(placement: dict | None) -> bool:
    if not isinstance(placement, dict):
        return False
    return bool(int(placement.get("sourceBackedStoryCallContextCount") or 0))


def _placement_has_hash_terminal(placement: dict | None) -> bool:
    if not isinstance(placement, dict):
        return False
    return bool(int(placement.get("sourceBackedHashTerminalCount") or 0))


def _placement_has_timeline(placement: dict | None) -> bool:
    if not isinstance(placement, dict):
        return False
    return bool(int(placement.get("timelineEvidenceCount") or 0))


def build_scene_order_gap_row(
    root: Path,
    path: Path,
    conv: dict,
    *,
    scene_placement_index: dict[str, dict] | None = None,
    dialog_id_registry: dict | None = None,
    analyses: dict | None = None,
) -> dict | None:
    analyses = analyses or analyze_scene_order_disorder(
        conv, dialog_id_registry=dialog_id_registry
    )
    line_order_analysis = analyses.get("lineOrder") or analyze_line_order(
        conv, dialog_id_registry=dialog_id_registry
    )
    option_layout_analysis = analyses.get("optionLayout") or analyze_option_layout(
        conv, dialog_id_registry=dialog_id_registry
    )
    line_order_pattern = classify_line_order_failure(line_order_analysis)
    option_position_pattern = classify_option_position_failure(conv, option_layout_analysis)
    inferred_options = option_layout_analysis["status"] == "inferred"
    inferred_responses = inferred_option_response_warning(conv) is not None
    if line_order_analysis["status"] == "direct" and not inferred_options and not inferred_responses:
        return None
    scene_key = runtime_dialog_scene_key(conv.get("key") or path.stem)
    scene_placement = (scene_placement_index or {}).get(scene_key) or {}
    option_groups = [
        group
        for group in (conv.get("optionGroups") or [])
        if isinstance(group, dict)
    ]
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        rel_path = path
    return {
        "key": conv.get("key") or path.stem,
        "mission": conv.get("mission") or "",
        "kind": conv.get("kind") or "",
        "title": ((conv.get("_debug") or {}).get("title") or {}).get("value") or "",
        "lineOrderStatus": line_order_analysis["status"],
        "lineOrderReasonCode": line_order_analysis["reasonCode"],
        "lineOrderReason": line_order_analysis["reason"],
        "lineOrderDetail": line_order_analysis["detail"],
        "lineOrderEvidence": line_order_analysis["evidence"],
        "lineOrderAnalysis": line_order_analysis,
        "lineOrderPatternCode": line_order_pattern["code"],
        "lineOrderPattern": line_order_pattern,
        "scenePlacement": scene_placement,
        "scenePlacementEvidenceKinds": scene_placement.get("evidenceKinds") or [],
        "scenePlacementHasStoryRef": _placement_has_story_ref(scene_placement),
        "scenePlacementHasSourceEdge": _placement_has_source_edge(scene_placement),
        "scenePlacementHasSourceSequence": _placement_has_source_sequence(scene_placement),
        "scenePlacementHasStoryCallContext": _placement_has_story_call_context(scene_placement),
        "scenePlacementHasHashTerminal": _placement_has_hash_terminal(scene_placement),
        "scenePlacementHasTimeline": _placement_has_timeline(scene_placement),
        "inferredOptionLayout": inferred_options,
        "inferredOptionResponse": inferred_responses,
        "optionLayoutStatus": option_layout_analysis["status"],
        "optionLayoutReason": option_layout_analysis["reasonCode"],
        "optionLayoutSummary": option_layout_analysis["reason"],
        "optionLayoutDetail": option_layout_analysis["detail"],
        "optionLayoutEvidence": option_layout_analysis["evidence"],
        "optionLayoutAnalysis": option_layout_analysis,
        "optionPositionPatternCode": option_position_pattern["code"],
        "optionPositionPattern": option_position_pattern,
        "warningCodes": [
            warning.get("code")
            for warning in (conv.get("warnings") or [])
            if isinstance(warning, dict) and warning.get("code")
        ],
        "lineCount": len(conv.get("lines") or []),
        "meaningfulLineCount": _count_meaningful_lines(conv),
        "optionGroupCount": len(option_groups),
        "optionCount": sum(
            len(group.get("options") or [])
            for group in option_groups
        ),
        "meaningfulOptionCount": _count_meaningful_options(conv),
        "hasMeaningfulLines": has_meaningful_lines(conv),
        "hasMeaningfulOptions": has_meaningful_options(conv),
        "path": str(rel_path).replace("\\", "/"),
    }


def collect_scene_order_gap_rows_from_payloads(
    root: Path,
    payloads: list[tuple[Path, dict, dict | None]] | list[tuple[Path, dict]],
    *,
    scene_placement_index: dict[str, dict] | None = None,
    dialog_id_registry: dict | None = None,
) -> list[dict]:
    if dialog_id_registry is None:
        dialog_id_registry = load_dialog_id_registry()
    rows: list[dict] = []
    for item in payloads:
        path = item[0]
        conv = item[1]
        analyses = item[2] if len(item) > 2 else None
        if not isinstance(conv, dict) or not path.stem.startswith("dlg_"):
            continue
        row = build_scene_order_gap_row(
            root,
            path,
            conv,
            scene_placement_index=scene_placement_index,
            dialog_id_registry=dialog_id_registry,
            analyses=analyses,
        )
        if row is not None:
            rows.append(row)
    return sort_scene_order_gap_rows(rows)


def sort_scene_order_gap_rows(rows: list[dict]) -> list[dict]:
    rows.sort(
        key=lambda row: (
            0 if row["lineOrderStatus"] == "missing" else 1,
            0 if row["inferredOptionLayout"] else 1,
            0 if row["inferredOptionResponse"] else 1,
            row["mission"],
            row["key"],
        )
    )
    return rows


def collect_scene_order_gap_rows(root: Path, conv_dir: Path) -> list[dict]:
    dialog_id_registry = load_dialog_id_registry()
    scene_placement_index = _load_scene_placement_index(root, conv_dir)
    payloads: list[tuple[Path, dict]] = []
    for path in sorted(conv_dir.glob("dlg_*.json")):
        try:
            conv = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        payloads.append((path, conv))
    return collect_scene_order_gap_rows_from_payloads(
        root,
        payloads,
        scene_placement_index=scene_placement_index,
        dialog_id_registry=dialog_id_registry,
    )


def build_scene_order_gap_summary(rows: list[dict], language: str) -> dict:
    line_reason_counts: dict[str, int] = {}
    option_reason_counts: dict[str, int] = {}
    line_pattern_counts: dict[str, int] = {}
    option_pattern_counts: dict[str, int] = {}
    placement_kind_counts: dict[str, int] = {}
    for row in rows:
        if row.get("lineOrderStatus") != "direct":
            reason = str(row.get("lineOrderReasonCode") or "unknown")
            line_reason_counts[reason] = line_reason_counts.get(reason, 0) + 1
            pattern = str(row.get("lineOrderPatternCode") or "unknown")
            line_pattern_counts[pattern] = line_pattern_counts.get(pattern, 0) + 1
        if row.get("inferredOptionLayout"):
            reason = str(row.get("optionLayoutReason") or "unknown")
            option_reason_counts[reason] = option_reason_counts.get(reason, 0) + 1
            pattern = str(row.get("optionPositionPatternCode") or "unknown")
            option_pattern_counts[pattern] = option_pattern_counts.get(pattern, 0) + 1
        for kind in row.get("scenePlacementEvidenceKinds") or []:
            kind = str(kind or "")
            if kind:
                placement_kind_counts[kind] = placement_kind_counts.get(kind, 0) + 1
    return {
        "language": language,
        "totalFlaggedScenes": len(rows),
        "missingLineOrder": sum(1 for row in rows if row["lineOrderStatus"] == "missing"),
        "partialLineOrder": sum(1 for row in rows if row["lineOrderStatus"] == "partial"),
        "fallbackLineOrder": sum(1 for row in rows if row["lineOrderStatus"] == "fallback"),
        "inferredOptionLayout": sum(1 for row in rows if row["inferredOptionLayout"]),
        "inferredOptionResponse": sum(1 for row in rows if row.get("inferredOptionResponse")),
        "lineOrderReasonCounts": line_reason_counts,
        "lineOrderPatternCounts": line_pattern_counts,
        "optionLayoutReasonCounts": option_reason_counts,
        "optionPositionPatternCounts": option_pattern_counts,
        "scenePlacementEvidenceCounts": placement_kind_counts,
        "scenePlacementStoryRef": sum(1 for row in rows if row.get("scenePlacementHasStoryRef")),
        "scenePlacementSourceEdge": sum(1 for row in rows if row.get("scenePlacementHasSourceEdge")),
        "scenePlacementSourceSequence": sum(1 for row in rows if row.get("scenePlacementHasSourceSequence")),
        "scenePlacementStoryCallContext": sum(1 for row in rows if row.get("scenePlacementHasStoryCallContext")),
        "scenePlacementHashTerminal": sum(1 for row in rows if row.get("scenePlacementHasHashTerminal")),
        "scenePlacementTimeline": sum(1 for row in rows if row.get("scenePlacementHasTimeline")),
        "scenePlacementAny": sum(1 for row in rows if row.get("scenePlacementEvidenceKinds")),
        "bothMissingOrderAndInferredOptions": sum(
            1
            for row in rows
            if row["lineOrderStatus"] == "missing" and row["inferredOptionLayout"]
        ),
        "bothFallbackOrderAndInferredOptions": sum(
            1
            for row in rows
            if row["lineOrderStatus"] == "fallback" and row["inferredOptionLayout"]
        ),
    }

def _describe_pattern(pattern_code: str, titles: dict[str, str], descriptions: dict[str, str]) -> str:
    label = titles.get(pattern_code, pattern_code)
    description = descriptions.get(pattern_code, "additional simplified failure pattern")
    return f"`{pattern_code}` - {label}: {description}"


def _render_pattern_cell(pattern: dict) -> str:
    status = str(pattern.get("status") or "unknown")
    code = str(pattern.get("code") or "")
    parts = [f"**{pattern.get('label') or status}**"]
    if code and code not in {"ok", "notNeeded"}:
        parts.append(f"`{code}`")
    summary = str(pattern.get("summary") or "").strip()
    detail = str(pattern.get("detail") or "").strip()
    if summary:
        parts.append(summary)
    if detail and detail != summary:
        parts.append(detail)
    return "<br>".join(_escape_table_text(part) for part in parts if part)


def _render_scene_placement_cell(row: dict) -> str:
    placement = row.get("scenePlacement")
    if not isinstance(placement, dict) or not placement:
        return ""
    parts: list[str] = []
    kinds = [str(kind) for kind in (placement.get("evidenceKinds") or []) if str(kind or "")]
    if kinds:
        parts.append(", ".join(f"`{kind}`" for kind in kinds))
    quest_ids = [str(value) for value in (placement.get("questIds") or []) if str(value or "")]
    if quest_ids:
        shown = ", ".join(f"`{value}`" for value in quest_ids[:4])
        if len(quest_ids) > 4:
            shown += f", +{len(quest_ids) - 4}"
        parts.append(f"quests: {shown}")
    story_ref_count = _as_int(placement.get("storyRefCount"))
    client_action_count = _as_int(placement.get("clientActionCount"))
    if story_ref_count or client_action_count:
        bits = []
        if story_ref_count:
            bits.append(f"MRA refs={story_ref_count}")
        if client_action_count:
            bits.append(f"client actions={client_action_count}")
        parts.append(", ".join(bits))
    source_edge_count = _as_int(placement.get("sourceBackedEdgeCount"))
    if source_edge_count:
        parts.append(
            "edges: "
            f"in={_as_int(placement.get('incomingEdgeCount'))}, "
            f"out={_as_int(placement.get('outgoingEdgeCount'))}"
        )
    source_sequence_count = _as_int(placement.get("sourceBackedSequenceCount"))
    if source_sequence_count:
        parts.append(f"sequences: {source_sequence_count}")
        for neighbor in (placement.get("sequenceNeighbors") or [])[:2]:
            if not isinstance(neighbor, dict):
                continue
            window = [
                str(value)
                for value in (neighbor.get("window") or [])
                if str(value or "")
            ]
            if window:
                parts.append("seq: " + " -> ".join(f"`{value}`" for value in window))
    story_call_count = _as_int(placement.get("sourceBackedStoryCallContextCount"))
    if story_call_count:
        parts.append(f"story calls: {story_call_count}")
        for context in (placement.get("storyCallContexts") or [])[:2]:
            if not isinstance(context, dict):
                continue
            window = [
                str(value)
                for value in (context.get("window") or [])
                if str(value or "")
            ]
            if window:
                parts.append("calls: " + " -> ".join(f"`{value}`" for value in window))
    hash_terminal_count = _as_int(placement.get("sourceBackedHashTerminalCount"))
    if hash_terminal_count:
        parts.append(f"hash terminals: {hash_terminal_count}")
        for terminal in (placement.get("hashTerminals") or [])[:2]:
            if not isinstance(terminal, dict):
                continue
            hash_key = str(terminal.get("hash") or "")
            direction = str(terminal.get("direction") or "")
            hash_step = terminal.get("hashStep")
            if not isinstance(hash_step, dict):
                hash_step = {}
            source = hash_step.get("source")
            if not isinstance(source, dict):
                source = {}
            bits = []
            if direction:
                bits.append(direction)
            if hash_key:
                bits.append(f"`{hash_key}`")
            for label, key in (("code", "code"), ("kind", "kind")):
                value = source.get(key)
                if value not in (None, "", [], {}):
                    bits.append(f"{label}={value}")
            next_id = hash_step.get("nextId")
            if next_id not in (None, "", [], {}):
                bits.append(f"next={next_id}")
            if bits:
                parts.append("hash: " + " ".join(str(bit) for bit in bits))
    timelines = [str(value) for value in (placement.get("timelines") or []) if str(value or "")]
    if timelines:
        shown = ", ".join(f"`{value}`" for value in timelines[:3])
        if len(timelines) > 3:
            shown += f", +{len(timelines) - 3}"
        parts.append(f"timelines: {shown}")
    return "<br>".join(parts)


def render_scene_order_gap_markdown(summary: dict, rows: list[dict]) -> str:
    lines = [
        f"# Scene Order Gaps ({summary['language']})",
        "",
        "Scope: `dlg_*` conversation scenes in the built WebUI data.",
        "",
        "## Summary",
        "",
        f"- flagged scenes: `{summary['totalFlaggedScenes']}`",
        f"- missing line-order block: `{summary['missingLineOrder']}`",
        f"- partial authored line order: `{summary.get('partialLineOrder', 0)}`",
        f"- fallback line order: `{summary['fallbackLineOrder']}`",
        f"- inferred option placement: `{summary['inferredOptionLayout']}`",
        f"- inferred option response: `{summary.get('inferredOptionResponse', 0)}`",
        f"- missing line order + inferred option placement: `{summary['bothMissingOrderAndInferredOptions']}`",
        f"- fallback line order + inferred option placement: `{summary['bothFallbackOrderAndInferredOptions']}`",
        f"- scenes with mission/story-ref placement evidence: `{summary.get('scenePlacementStoryRef', 0)}`",
        f"- scenes with source-backed scene-edge evidence: `{summary.get('scenePlacementSourceEdge', 0)}`",
        f"- scenes with source-backed scene-sequence evidence: `{summary.get('scenePlacementSourceSequence', 0)}`",
        f"- scenes with source-backed story-call context: `{summary.get('scenePlacementStoryCallContext', 0)}`",
        f"- scenes with source-backed hash-terminal evidence: `{summary.get('scenePlacementHashTerminal', 0)}`",
        f"- scenes with timeline evidence: `{summary.get('scenePlacementTimeline', 0)}`",
    ]

    line_pattern_counts = summary.get("lineOrderPatternCounts") or {}
    if line_pattern_counts:
        lines.extend([
            "",
            "### Line-Order Failure Patterns",
            "",
        ])
        for pattern, count in sorted(line_pattern_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{pattern}`: `{count}`")

    option_pattern_counts = summary.get("optionPositionPatternCounts") or {}
    if option_pattern_counts:
        lines.extend([
            "",
            "### Option-Position Failure Patterns",
            "",
        ])
        for pattern, count in sorted(option_pattern_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{pattern}`: `{count}`")

    placement_counts = summary.get("scenePlacementEvidenceCounts") or {}
    if placement_counts:
        lines.extend([
            "",
            "### Scene Placement Evidence",
            "",
        ])
        for kind, count in sorted(placement_counts.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{kind}`: `{count}`")

    lines.extend([
        "",
        "## Pattern Guide",
        "",
        "### Line Order",
        "",
    ])
    line_pattern_docs = (
        sorted(line_pattern_counts)
        if line_pattern_counts
        else ["numericSuffixFallback", "missingBlockButSuffixSortable", "missingBlockNoSafeFallback"]
    )
    for pattern_code in line_pattern_docs:
        lines.append(
            f"- {_describe_pattern(pattern_code, LINE_ORDER_PATTERN_TITLES, LINE_ORDER_PATTERN_DESCRIPTIONS)}"
        )

    lines.extend([
        "",
        "### Option Position",
        "",
    ])
    option_pattern_docs = (
        sorted(option_pattern_counts)
        if option_pattern_counts
        else ["syntheticAfterAllGroups", "mixedAuthoredAndSyntheticAfter", "unanchoredAllGroups"]
    )
    for pattern_code in option_pattern_docs:
        lines.append(
            f"- {_describe_pattern(pattern_code, OPTION_POSITION_PATTERN_TITLES, OPTION_POSITION_PATTERN_DESCRIPTIONS)}"
        )

    lines.extend([
        "",
        "## Scenes",
        "",
        "| Scene | Mission | Scene Placement | Line-Order Pattern | Option-Position Pattern | Option Response | Lines | Opt Groups | Path |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ])

    for row in rows:
        placement_cell = _render_scene_placement_cell(row)
        line_cell = _render_pattern_cell(row.get("lineOrderPattern") or {})
        option_cell = _render_pattern_cell(row.get("optionPositionPattern") or {})
        response_cell = (
            "**inferred**<br>`optionTargetsMissing`"
            if row.get("inferredOptionResponse")
            else ""
        )
        lines.append(
            f"| `{row['key']}` | `{row['mission']}` | {placement_cell} | {line_cell} | {option_cell} | {response_cell} | "
            f"{row['lineCount']} | {row['optionGroupCount']} | `{_escape_table_text(row['path'])}` |"
        )

    return "\n".join(lines)
