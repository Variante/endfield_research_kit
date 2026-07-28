from __future__ import annotations

from .context import *
from .anime_assets import *
from .scene_graph import *
from .level_bindings import *
from .mission_flow import *
from .dialog_tree import *
from .bundle_support import *

def clean_media_id_value(value: object) -> str:
    text = html.unescape(str(value or "")).strip()
    text = text.replace(r"\"", '"').replace(r"\'", "'")
    for _ in range(3):
        unwrapped = re.sub(r'^[\'"]+|[\'"]+$', "", text).strip()
        if unwrapped == text:
            break
        text = unwrapped
    return text

def written_path_key(path: Path) -> str:
    return str(path).lower()

def norm_id(id_value) -> str:
    if id_value is None:
        return ""
    s = str(id_value)
    return "" if s == "0" else s

def pick_fields(obj: dict | None, *keys: str) -> dict:
    if not obj:
        return {}
    return {k: obj.get(k) for k in keys if k in obj}

def source_ref(table: str, row_id: str, source: dict, **extra) -> dict:
    out = {
        "table": table,
        "rowId": row_id,
        "source": source,
    }
    for k, v in extra.items():
        if is_present(v):
            out[k] = v
    return out

def inline_image_tag(image_id: str) -> str:
    clean = str(image_id or "").strip()
    return f'<image="{clean}">' if clean else ""

def text_sequence_fingerprint(nodes: list[dict]) -> tuple[str, ...]:
    rows: list[str] = []
    for node in nodes:
        text = re.sub(r"\s+", " ", str(node.get("text") or "")).strip()
        if text:
            rows.append(text)
    return tuple(rows)

def brace_text(text: str) -> str:
    """Return the content inside the first {...} when present."""
    if not text:
        return ""
    m = re.search(r"\{([^{}]+)\}", text)
    return m.group(1) if m else text

def sns_raw_title(out_key: str) -> str:
    """Show `foo_...` instead of the stored `sns_foo_...` key."""
    return out_key[4:] if out_key.startswith("sns_") else out_key

def normalize_blackbox_id(value: str) -> str:
    mission_id = re.sub(r"\s+", "", value or "")
    alias_prefixes = {
        "blackbox_storage": "blackbox_storager",
        "blackbox_xiranite_oven": "blackbox_xiraniteoven",
    }
    for src, dst in alias_prefixes.items():
        if mission_id == src or mission_id.startswith(f"{src}_"):
            return f"{dst}{mission_id[len(src):]}"
    return mission_id

def norm_template_id(value: str) -> str:
    if value.startswith("npc_tpl_"):
        return value[len("npc_tpl_"):]
    return value

def icon_basename(icon_path: str) -> str:
    if not icon_path:
        return ""
    return icon_path.rsplit("/", 1)[-1]

def env_group(env_id: str) -> str:
    """Bucket ambient-talk ids into browser groups."""
    if env_id.startswith("greetEnvTalk"):
        return "greetEnvTalk"
    if env_id.startswith("envEmoji"):
        return "envEmoji"
    if env_id.startswith("charGiftTalkid"):
        return "charGiftTalkid"
    m = re.match(r"^envTalk_([^_]+(?:_lv\d+(?:_env)?)?)(?:_|$)", env_id)
    if m:
        token = m.group(1)
        if token.startswith("base") and re.match(r"^base\d+_lv\d+(?:_env)?$", token):
            return "map" + token[len("base"):]
        return token
    return "envTalk"

def env_story_mission(env_id: str, known_missions: set[str]) -> str:
    """Return the mission bucket encoded by an env-talk id when possible.

    Supports both story-shaped ids like `envTalk_e0m2_7` and map/base ids
    like `envTalk_map01_lv001_env_11` or `envTalk_base01_lv001_env_11`.
    """
    direct = re.match(r"^envTalk_([^_]+)(?:_|$)", env_id)
    if direct:
        mission = direct.group(1)
        if mission in known_missions:
            return mission

    map_like = re.match(r"^envTalk_((?:map|base)\d+_lv\d+(?:_env)?)_\d+$", env_id)
    if not map_like:
        return ""

    mission = map_like.group(1)
    if mission in known_missions:
        return mission
    if mission.startswith("base"):
        mapped = "map" + mission[len("base"):]
        if mapped in known_missions:
            return mapped
    return ""

def line_haystack(lines: list[dict], *fields: str) -> str:
    parts: list[str] = []
    for line in lines:
        for field in fields:
            value = line.get(field)
            if value:
                parts.append(str(value))
    return " ".join(parts)

def line_identity_haystack(lines: list[dict]) -> str:
    parts: list[str] = []
    for line in lines:
        line_id = line.get("id")
        if line_id:
            parts.append(str(line_id))
        cid = line.get("cid")
        if cid is not None and cid != "":
            parts.append(f"cid:{cid}")
    return " ".join(parts)

def line_option_haystack(lines: list[dict]) -> str:
    parts: list[str] = []
    for line in lines:
        for option in line.get("options") or []:
            if not isinstance(option, dict):
                continue
            for field in ("id", "optionId", "text", "image", "emoji"):
                value = option.get(field)
                if value:
                    parts.append(str(value))
    return " ".join(parts)

def parse_level_ref_name(name: str) -> dict | None:
    if not name.endswith(".json"):
        return None
    stem = name[:-5]
    marker = "_lv_data_sub_"
    if marker not in stem:
        return None
    level_id, rest = stem.split(marker, 1)
    kind = "plain"
    if rest.startswith("mission_"):
        kind = "mission"
        rest = rest[len("mission_") :]
    rest = rest.lstrip("_")
    if not level_id or not rest:
        return None
    token = re.sub(r"_v[0-9A-Za-z]+$", "", rest)
    return {
        "level": level_id,
        "kind": kind,
        "token": token,
    }

def level_host_type(level_id: str) -> str:
    if level_id.startswith(("map", "base")):
        return "map"
    if level_id.startswith("dung"):
        return "dungeon"
    if level_id.startswith("indie"):
        return "indie"
    if level_id.startswith("blackbox"):
        return "blackbox"
    return "other"

def merge_search_text(base: str, extra: str) -> str:
    base = base.strip()
    extra = extra.strip()
    if not base:
        return extra
    if not extra:
        return base
    return f"{base} {extra}"

def format_webui_timeline_seconds(value: float) -> str:
    seconds = max(0.0, float(value))
    minutes = int(seconds // 60)
    remaining = seconds - minutes * 60
    return f"{minutes}:{remaining:04.1f}"

def graph_fragments_text(fragments: list[dict]) -> str:
    parts: list[str] = []
    for fragment in fragments or []:
        if fragment.get("sourceKey"):
            parts.append(str(fragment["sourceKey"]))
        if fragment.get("lineIds"):
            parts.extend(str(line_id) for line_id in fragment["lineIds"] if line_id)
        terminals = fragment.get("terminalCounts") or {}
        for label, count in terminals.items():
            if count:
                parts.append(f"{label}:{count}")
        for group in fragment.get("optionGroups") or []:
            if group.get("after"):
                parts.append(str(group["after"]))
            parts.extend(str(opt_id) for opt_id in group.get("optionIds") or [] if opt_id)
            for branch_lines in (group.get("branches") or {}).values():
                parts.extend(str(line_id) for line_id in branch_lines if line_id)
            parts.extend(
                str(line_id)
                for line_id in (group.get("merge") or {}).values()
                if line_id
            )
    return " ".join(parts)

def scene_links_text(links: list[dict]) -> str:
    parts: list[str] = []
    for link in links or []:
        if link.get("sourceKey"):
            parts.append(str(link["sourceKey"]))
        if link.get("after"):
            parts.append(str(link["after"]))
        for opt in link.get("options") or []:
            if opt.get("optionId"):
                parts.append(str(opt["optionId"]))
            if opt.get("firstLineId"):
                parts.append(str(opt["firstLineId"]))
            if opt.get("firstSceneKey"):
                parts.append(str(opt["firstSceneKey"]))
            if opt.get("terminal"):
                parts.append(str(opt["terminal"]))
            if opt.get("outcomeKind"):
                parts.append(str(opt["outcomeKind"]))
            loop = opt.get("loop") or {}
            if isinstance(loop, dict):
                if loop.get("kind"):
                    parts.append(str(loop["kind"]))
                parts.extend(str(scene_key) for scene_key in (loop.get("sceneKeys") or []) if scene_key)
            parts.extend(str(line_id) for line_id in (opt.get("pathLineIds") or []) if line_id)
            parts.extend(str(scene_key) for scene_key in (opt.get("sceneKeys") or []) if scene_key)
            parts.extend(str(scene_key) for scene_key in (opt.get("submenuSceneKeys") or []) if scene_key)
            for target in opt.get("submenuTargets") or []:
                if not isinstance(target, dict):
                    continue
                parts.extend(
                    str(target.get(key) or "")
                    for key in ("sceneKey", "optionId", "text")
                    if target.get(key)
                )
    return " ".join(parts)

def scene_link_option_payload(raw_option: dict) -> dict:
    entry = {
        "optionId": raw_option.get("optionId") or "",
    }
    for key in ("firstLineId", "firstSceneKey", "terminal"):
        if raw_option.get(key):
            entry[key] = raw_option[key]
    for key in ("pathLineIds", "sceneKeys", "submenuSceneKeys"):
        if raw_option.get(key):
            entry[key] = raw_option[key]
    if raw_option.get("conditionalOutcomes"):
        entry["conditionalOutcomes"] = raw_option["conditionalOutcomes"]
    if raw_option.get("loop"):
        entry["loop"] = raw_option["loop"]
    if raw_option.get("outcomeKind"):
        entry["outcomeKind"] = raw_option["outcomeKind"]
    if raw_option.get("_debug"):
        entry["_debug"] = raw_option["_debug"]
    return entry


def timeline_option_index_pattern(values: list[object]) -> str:
    ints = [value for value in values if isinstance(value, int)]
    if not ints:
        return "missing"
    if len(ints) < len(values):
        return "partialMissing"
    has_zero = any(value == 0 for value in ints)
    has_nonzero = any(value != 0 for value in ints)
    if has_zero and has_nonzero:
        return "mixedZeroNonzero"
    if has_zero:
        return "allZero"
    if has_nonzero:
        return "strictNonzero"
    return "other"


def classify_zero_index_timeline_continuation(
    option_indices: list[object],
    candidate_clip_indices: list[object],
    *,
    candidate_window_start: object,
    candidate_window_end: object,
    runtime_jump_clips: object,
) -> dict:
    """Classify an all-zero adjacent trunk window using runtime semantics.

    Native ``TryTriggerTrunkBindingOption`` selects only active trunk clips
    whose runtime option field is positive. Adjacent trunk clips whose
    serialized ``TimelineClip.optionIndex`` values are all zero are therefore
    shared continuation, not one reply per UI option. A raw Runtime Jump may
    still alter the later route; completed routes are handled by the
    higher-priority route classifier, while incomplete overlaps remain attached
    as route uncertainty instead of reviving a one-line-per-option guess.
    """
    candidate_pattern = timeline_option_index_pattern(candidate_clip_indices)
    if candidate_pattern != "allZero" or not candidate_clip_indices:
        return {"status": "notApplicable"}
    option_pattern = timeline_option_index_pattern(option_indices)
    if not isinstance(runtime_jump_clips, list):
        return {
            "status": "unverified",
            "reason": "runtimeJumpEvidenceMissing",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
        }
    try:
        window_start = float(candidate_window_start)
        window_end = float(candidate_window_end)
    except (TypeError, ValueError):
        return {
            "status": "unverified",
            "reason": "candidateWindowTimingMissing",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
        }
    if window_end <= window_start:
        return {
            "status": "unverified",
            "reason": "candidateWindowTimingInvalid",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
        }

    overlaps: list[dict] = []
    malformed = False
    for raw in runtime_jump_clips:
        if not isinstance(raw, dict):
            malformed = True
            continue
        try:
            clip_start = float(raw.get("start"))
            clip_end = float(
                raw.get("end")
                if raw.get("end") is not None
                else clip_start + float(raw.get("duration"))
            )
        except (TypeError, ValueError):
            malformed = True
            continue
        if clip_end > window_start + 1e-6 and clip_start < window_end - 1e-6:
            overlaps.append(raw)
    if malformed:
        return {
            "status": "blocked",
            "reason": "runtimeJumpEvidenceMalformed",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
            "overlappingRuntimeJumpClips": overlaps,
        }
    if overlaps:
        return {
            "status": "shared",
            "reason": "defaultTrunkClipContinuationWithRuntimeJump",
            "runtimeJumpRouteStatus": "overlapUnresolved",
            "optionIndexPattern": option_pattern,
            "candidateLineClipOptionIndexPattern": candidate_pattern,
            "overlappingRuntimeJumpClips": overlaps,
        }
    return {
        "status": "shared",
        "reason": (
            "rawOptionIndexConverges"
            if option_pattern == "allZero"
            else "defaultTrunkClipContinuation"
        ),
        "optionIndexPattern": option_pattern,
        "candidateLineClipOptionIndexPattern": candidate_pattern,
    }


def classify_timeline_clip_option_index_routes(
    option_ids: list[str],
    option_indices: list[object],
    branch_line_ids_by_option: dict[str, list[str]],
    branch_clip_indices_by_option: dict[str, list[int]],
    line_timing_by_id: dict[str, dict],
    runtime_jump_clips: object,
    common_continuation_line_id: str,
) -> dict:
    """Validate exact nonzero Timeline option-index branch ownership.

    A selected dialog option is written into the runtime option field, and
    option-bound Timeline clips are enabled by that value. Distinct positive
    option indices therefore identify branch clips directly. Runtime Jumps in
    the same window are accepted only when they occur after that option's last
    response clip and converge forward to the shared continuation.
    """
    if (
        len(option_ids) < 2
        or len(option_ids) != len(option_indices)
        or not all(isinstance(value, int) and value > 0 for value in option_indices)
        or len(set(option_indices)) != len(option_indices)
        or not isinstance(runtime_jump_clips, list)
        or not common_continuation_line_id
    ):
        return {
            "status": "incomplete",
            "reason": "routeCardinalityOrRuntimeEvidence",
        }

    continuation_timing = line_timing_by_id.get(common_continuation_line_id) or {}
    continuation_start = continuation_timing.get("start")
    if not isinstance(continuation_start, (int, float)):
        return {"status": "incomplete", "reason": "continuationTimingMissing"}
    continuation_start = float(continuation_start)

    branch_end_by_index: dict[int, float] = {}
    branch_starts: list[float] = []
    for option_id, option_index in zip(option_ids, option_indices):
        branch_lines = branch_line_ids_by_option.get(option_id) or []
        clip_indices = branch_clip_indices_by_option.get(option_id) or []
        if (
            not branch_lines
            or len(branch_lines) != len(clip_indices)
            or any(value != option_index for value in clip_indices)
        ):
            return {"status": "incomplete", "reason": "branchClipIndexCoverage"}
        ends: list[float] = []
        for line_id in branch_lines:
            timing = line_timing_by_id.get(line_id) or {}
            start = timing.get("start")
            duration = timing.get("duration")
            if not isinstance(start, (int, float)) or not isinstance(
                duration, (int, float)
            ):
                return {"status": "incomplete", "reason": "branchTimingMissing"}
            start = float(start)
            end = start + float(duration)
            if end < start or start >= continuation_start + 1e-6:
                return {"status": "blocked", "reason": "branchTimingInvalid"}
            branch_starts.append(start)
            ends.append(end)
        branch_end_by_index[int(option_index)] = max(ends)

    branch_window_start = min(branch_starts)
    convergence_jumps: list[dict] = []
    option_index_set = {int(value) for value in option_indices}
    for raw in runtime_jump_clips:
        if not isinstance(raw, dict):
            return {"status": "blocked", "reason": "runtimeJumpEvidenceMalformed"}
        start = raw.get("start")
        end = raw.get("end")
        if end is None and isinstance(start, (int, float)) and isinstance(
            raw.get("duration"), (int, float)
        ):
            end = float(start) + float(raw["duration"])
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            return {"status": "blocked", "reason": "runtimeJumpTimingMissing"}
        start = float(start)
        end = float(end)
        if end <= branch_window_start + 1e-6 or start >= continuation_start - 1e-6:
            continue
        option_index = raw.get("optionIndex")
        if (
            not isinstance(option_index, int)
            or option_index not in option_index_set
            or raw.get("isReverseJump") not in (None, 0, False)
            or raw.get("needChangeOptionAfterJump") not in (None, 0, False)
            or start + 1e-6 < branch_end_by_index[option_index]
            or end > continuation_start + 1e-6
            or end <= start
        ):
            return {
                "status": "blocked",
                "reason": "runtimeJumpDoesNotConvergeAfterBranch",
                "runtimeJump": raw,
            }
        convergence_jumps.append(raw)

    return {
        "status": "exact",
        "reason": "runtimeClipOptionIndex",
        "commonContinuationLineId": common_continuation_line_id,
        "convergenceRuntimeJumps": convergence_jumps,
    }


def classify_runtime_jump_option_routes(
    option_ids: list[str],
    routes: list[dict],
    ordered_line_ids: list[str],
    *,
    after_line_id: str = "",
) -> dict:
    """Reduce complete Runtime Jump paths to option-exclusive line spans.

    Timeline recovery deliberately keeps each option's complete path until the
    next option slot.  That path can contain a long shared suffix, while a
    route marked ``terminatesSlot`` can contain no line because it skips the
    option-response window and resumes at the shared continuation.  This
    classifier removes the common suffix and names direct-continuation options
    explicitly so callers do not require a fake response line for every
    choice.
    """
    if len(option_ids) < 2 or len(option_ids) != len(routes):
        return {"status": "incomplete", "reason": "optionRouteCardinality"}

    valid_line_ids = {
        str(line_id)
        for line_id in ordered_line_ids
        if str(line_id or "").strip()
    }
    paths: dict[str, list[str]] = {}
    terminates_slot: list[str] = []
    for option_id, route in zip(option_ids, routes):
        if not option_id or not isinstance(route, dict):
            return {"status": "incomplete", "reason": "missingOptionRoute"}
        path = []
        for raw_line_id in route.get("pathLineIds") or []:
            line_id = str(raw_line_id or "")
            if line_id in valid_line_ids and line_id not in path:
                path.append(line_id)
        if not path and not route.get("terminatesSlot"):
            return {"status": "incomplete", "reason": "emptyOptionRoute"}
        paths[option_id] = path
        if route.get("terminatesSlot"):
            terminates_slot.append(option_id)

    nonempty_paths = [path for path in paths.values() if path]
    common_suffix: list[str] = []
    if len(nonempty_paths) == len(paths):
        suffix_length = 0
        min_length = min(len(path) for path in nonempty_paths)
        while suffix_length < min_length:
            candidate = nonempty_paths[0][-suffix_length - 1]
            if not all(path[-suffix_length - 1] == candidate for path in nonempty_paths):
                break
            suffix_length += 1
        if suffix_length:
            common_suffix = nonempty_paths[0][-suffix_length:]

    exclusive_paths = {
        option_id: (
            path[:-len(common_suffix)]
            if common_suffix
            else list(path)
        )
        for option_id, path in paths.items()
    }
    direct_continuation_ids = [
        option_id
        for option_id in option_ids
        if not exclusive_paths.get(option_id)
    ]
    signatures = {
        tuple(exclusive_paths.get(option_id) or [])
        for option_id in option_ids
    }
    if len(signatures) < 2:
        return {
            "status": "shared",
            "reason": "identicalRuntimeJumpPaths",
            "commonContinuationLineIds": common_suffix,
        }

    common_continuation = common_suffix[0] if common_suffix else ""
    if not common_continuation and terminates_slot:
        line_index = {
            line_id: index
            for index, line_id in enumerate(ordered_line_ids)
        }
        covered_indexes = [
            line_index[line_id]
            for path in paths.values()
            for line_id in path
            if line_id in line_index
        ]
        if covered_indexes:
            continuation_index = max(covered_indexes) + 1
        else:
            continuation_index = line_index.get(after_line_id, -1) + 1
        if 0 <= continuation_index < len(ordered_line_ids):
            common_continuation = ordered_line_ids[continuation_index]

    return {
        "status": "branched",
        "reason": "runtimeJumpExclusivePaths",
        "branchLineIdsByOption": exclusive_paths,
        "directContinuationOptionIds": direct_continuation_ids,
        "commonContinuationLineId": common_continuation,
        "commonContinuationLineIds": common_suffix,
        "terminatingOptionIds": terminates_slot,
        "fullPathLineIdsByOption": paths,
    }


def dialog_story_issue_codes(payload: dict) -> list[str]:
    codes: list[str] = []
    debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
    runtime_registry = (
        debug.get("runtimeRegistry")
        if isinstance(debug.get("runtimeRegistry"), dict)
        else {}
    )
    is_unregistered_scene = runtime_registry.get("registered") is False
    warning = next(
        (
            item
            for item in (payload.get("warnings") or [])
            if isinstance(item, dict) and item.get("code") == "sceneOrderDisorder"
        ),
        None,
    )
    if isinstance(warning, dict):
        line_order = warning.get("lineOrder") if isinstance(warning.get("lineOrder"), dict) else {}
        option_layout = warning.get("optionLayout") if isinstance(warning.get("optionLayout"), dict) else {}
        problematic_aspects = {
            str(aspect)
            for aspect in (warning.get("problematicAspects") or [])
            if str(aspect)
        }

        line_order_status = str(line_order.get("status") or "")
        if "lineOrder" in problematic_aspects:
            if line_order_status == "missing":
                codes.append("missingLineOrder")
            elif line_order_status == "fallback":
                codes.append("fallbackLineOrder")
            if int(line_order.get("uncoveredLineCount") or 0) > 0:
                codes.append("uncoveredLines")
        if str(option_layout.get("status") or "") == "inferred":
            layout_warning = next(
                (
                    item
                    for item in (payload.get("warnings") or [])
                    if isinstance(item, dict) and item.get("code") == "inferredOptionLayout"
                ),
                None,
            )
            group_details = (
                layout_warning.get("groupDetails")
                if isinstance(layout_warning, dict)
                and isinstance(layout_warning.get("groupDetails"), list)
                else []
            )
            modes = {
                str(detail.get("inferredAnchorMode") or "")
                for detail in group_details
                if isinstance(detail, dict) and not detail.get("manualLayoutOverride")
            }
            statuses = {
                str(detail.get("status") or "")
                for detail in group_details
                if isinstance(detail, dict) and not detail.get("manualLayoutOverride")
            }
            if is_unregistered_scene:
                # A DialogOptionTable row can survive without any executable
                # DialogIdTable root. Its suffix/gap still provides a useful
                # display placement, but there is no live runtime layout to
                # recover or validate. Keep this queue separate from active
                # key/gap placement work.
                codes.append("tableOnlyOptionLayout")
            else:
                if "lineNumber" in modes:
                    codes.append("keyedOptionLayout")
                if modes.intersection({"sparseGap", "siblingTimelinePosition"}):
                    codes.append("gapOptionLayout")
                if "lastLine" in modes:
                    codes.append("lastLineOptionLayout")
                if "unanchored" in statuses or any(
                    isinstance(detail, dict)
                    and not detail.get("manualLayoutOverride")
                    and not (detail.get("after") or detail.get("position"))
                    for detail in group_details
                ):
                    codes.append("unanchoredOptionLayout")
            # Older payloads did not expose per-group placement modes. Keep a
            # compatibility issue only for those files instead of incorrectly
            # calling every recovered table-key anchor "missing".
            if not group_details and not is_unregistered_scene:
                codes.append("inferredOptionLayout")
    if any(
        isinstance(item, dict) and item.get("code") == "duplicateTimestamps"
        for item in (payload.get("warnings") or [])
    ):
        codes.append("duplicateTimestamps")
    if any(
        isinstance(item, dict) and item.get("code") == "timelineTimestampRegression"
        for item in (payload.get("warnings") or [])
    ):
        codes.append("timelineTimestampRegression")
    if any(
        isinstance(item, dict) and item.get("code") == "inferredOptionResponse"
        for item in (payload.get("warnings") or [])
    ):
        codes.append("inferredOptionResponse")
    if dialog_has_manual_option_override(payload):
        codes.append("overrided")
    return codes

def dialog_option_issue_targets(payload: dict) -> dict:
    """Return compact per-issue targets for runtime WebUI override coverage.

    Option overrides intentionally stay outside generated conversation JSON so
    they can be edited without rebuilding Story data.  The index still needs
    to say which generated groups/options each issue covers; otherwise the
    frontend can only detect that a scene has *some* override and cannot tell a
    complete correction from a partial one.
    """
    warnings = [
        warning
        for warning in (payload.get("warnings") or [])
        if isinstance(warning, dict)
    ]
    layout_warning = next(
        (warning for warning in warnings if warning.get("code") == "inferredOptionLayout"),
        None,
    )
    response_warning = next(
        (warning for warning in warnings if warning.get("code") == "inferredOptionResponse"),
        None,
    )
    issue_codes = set(dialog_story_issue_codes(payload))
    out: dict[str, object] = {}

    if isinstance(layout_warning, dict):
        details = [
            detail
            for detail in (layout_warning.get("groupDetails") or [])
            if isinstance(detail, dict) and not detail.get("manualLayoutOverride")
        ]
        if not details and "inferredOptionLayout" in issue_codes:
            details = [
                {"group": group.get("g")}
                for group in (payload.get("optionGroups") or [])
                if isinstance(group, dict) and group.get("g") is not None
            ]

        def groups_matching(predicate) -> list[str]:
            values: list[str] = []
            for detail in details:
                if not predicate(detail) or detail.get("group") is None:
                    continue
                group_id = str(detail.get("group"))
                if group_id and group_id not in values:
                    values.append(group_id)
            return values

        layout_targets: dict[str, list[str]] = {}
        if "tableOnlyOptionLayout" in issue_codes:
            layout_targets["tableOnlyOptionLayout"] = groups_matching(lambda _detail: True)
        if "keyedOptionLayout" in issue_codes:
            layout_targets["keyedOptionLayout"] = groups_matching(
                lambda detail: str(detail.get("inferredAnchorMode") or "") == "lineNumber"
            )
        if "gapOptionLayout" in issue_codes:
            layout_targets["gapOptionLayout"] = groups_matching(
                lambda detail: str(detail.get("inferredAnchorMode") or "")
                in {"sparseGap", "siblingTimelinePosition"}
            )
        if "lastLineOptionLayout" in issue_codes:
            layout_targets["lastLineOptionLayout"] = groups_matching(
                lambda detail: str(detail.get("inferredAnchorMode") or "") == "lastLine"
            )
        if "unanchoredOptionLayout" in issue_codes:
            layout_targets["unanchoredOptionLayout"] = groups_matching(
                lambda detail: (
                    str(detail.get("status") or "") == "unanchored"
                    or not (detail.get("after") or detail.get("position"))
                )
            )
        if "inferredOptionLayout" in issue_codes:
            layout_targets["inferredOptionLayout"] = groups_matching(lambda _detail: True)
        layout_targets = {
            code: group_ids
            for code, group_ids in layout_targets.items()
            if group_ids
        }
        if layout_targets:
            out["layoutGroupsByCode"] = layout_targets

    if isinstance(response_warning, dict) and "inferredOptionResponse" in issue_codes:
        option_ids: list[str] = []
        raw_option_ids = list(response_warning.get("optionIds") or [])
        if not raw_option_ids:
            raw_option_ids = [
                option_id
                for group in (response_warning.get("groups") or [])
                if isinstance(group, dict)
                for option_id in (group.get("optionIds") or [])
            ]
        for raw_option_id in raw_option_ids:
            option_id = str(raw_option_id or "")
            if option_id and option_id not in option_ids:
                option_ids.append(option_id)
        if option_ids:
            out["responseOptionIds"] = option_ids

    return out

def dialog_has_manual_option_override(payload: dict) -> bool:
    for group in (payload.get("optionGroups") or []):
        if not isinstance(group, dict):
            continue
        if isinstance(group.get("manualOverride"), dict) and group.get("manualOverride"):
            return True
        for option in (group.get("options") or []):
            if isinstance(option, dict) and isinstance(option.get("manualOverride"), dict) and option.get("manualOverride"):
                return True
    for warning in (payload.get("warnings") or []):
        if not isinstance(warning, dict):
            continue
        if isinstance(warning.get("manualOverride"), dict) and warning.get("manualOverride"):
            return True
        for detail in (warning.get("groupDetails") or []):
            if isinstance(detail, dict) and isinstance(detail.get("manualOverride"), dict) and detail.get("manualOverride"):
                return True
        for group in (warning.get("groups") or []):
            if isinstance(group, dict) and isinstance(group.get("manualOverride"), dict) and group.get("manualOverride"):
                return True
    return False

def _line_id_list_equal(left: object, right: object) -> bool:
    if not isinstance(left, list) or not isinstance(right, list):
        return False
    return [str(value or "") for value in left] == [str(value or "") for value in right]

def normalize_cutscene_text_group(group: str) -> str:
    match = re.match(r"^(.*_)(0+)(\d+)$", group)
    if not match:
        return group
    return f"{match.group(1)}{int(match.group(3))}"

def merge_duplicate_cutscene_rows(rows: list[tuple[tuple[int, int, int, str, str], dict]]) -> list[dict]:
    merged: list[dict] = []
    seen: dict[tuple[str, str, str], dict] = {}
    for _sort_key, line in sorted(rows, key=lambda item: item[0]):
        dedupe_key = (
            str(line.get("cid") or ""),
            str(line.get("gender") or ""),
            str(line.get("text") or ""),
        )
        existing = seen.get(dedupe_key)
        if existing is None:
            seen[dedupe_key] = line
            merged.append(line)
            continue

        duplicate = {"id": line.get("id") or ""}
        if line.get("textGroup"):
            duplicate["textGroup"] = line["textGroup"]
        if line.get("sub"):
            duplicate["sub"] = line["sub"]
        if line.get("gender"):
            duplicate["gender"] = line["gender"]
        existing.setdefault("mergedDuplicateRows", []).append(duplicate)
        existing_debug = existing.setdefault("_debug", {})
        existing_debug.setdefault("mergedDuplicateRows", []).append(duplicate)
        existing_source = existing_debug.setdefault("source", {})
        merged_row_ids = existing_source.setdefault("mergedDuplicateRowIds", [])
        if duplicate["id"] and duplicate["id"] not in merged_row_ids:
            merged_row_ids.append(duplicate["id"])
        if duplicate.get("textGroup"):
            merged_groups = existing_source.setdefault("mergedDuplicateTextGroups", [])
            if duplicate["textGroup"] not in merged_groups:
                merged_groups.append(duplicate["textGroup"])
    return merged

def cutscene_line_text_groups(cutscene_key: str, lines: list[dict]) -> list[str]:
    groups: list[str] = []
    for line in lines:
        for group in [
            str(line.get("textGroup") or cutscene_key),
            *[
                str(duplicate.get("textGroup") or "")
                for duplicate in (line.get("mergedDuplicateRows") or [])
                if isinstance(duplicate, dict)
            ],
        ]:
            if group and group not in groups:
                groups.append(group)
    return groups

def fold_padded_group_into_pair(canonical_line: dict, padded_line: dict) -> None:
    """Record `padded_line` as a `mergedDuplicateRows` entry on `canonical_line`.

    Used when the leading-zero textgroup row is treated as the M sibling of an
    unpadded F row that already carries the canonical text.
    """
    duplicate = {"id": padded_line.get("id") or ""}
    if padded_line.get("text"):
        duplicate["text"] = padded_line["text"]
    if padded_line.get("textGroup"):
        duplicate["textGroup"] = padded_line["textGroup"]
    if padded_line.get("sub"):
        duplicate["sub"] = padded_line["sub"]
    canonical_line.setdefault("mergedDuplicateRows", []).append(duplicate)
    debug = canonical_line.setdefault("_debug", {})
    debug.setdefault("mergedDuplicateRows", []).append(duplicate)
    source = debug.setdefault("source", {})
    row_ids = source.setdefault("mergedDuplicateRowIds", [])
    if duplicate["id"] and duplicate["id"] not in row_ids:
        row_ids.append(duplicate["id"])
    if padded_line.get("textGroup"):
        groups = source.setdefault("mergedDuplicateTextGroups", [])
        if padded_line["textGroup"] not in groups:
            groups.append(padded_line["textGroup"])

def cutscene_pair_normalize(text: str) -> str:
    """Strip whitespace, punctuation, and symbols so that F and M variants
    differing only in cosmetic markers (leading space, halfwidth/fullwidth
    punctuation, smart quotes) compare equal. Letters and digits survive."""
    if not text:
        return ""
    out = []
    for ch in str(text):
        cat = unicodedata.category(ch)
        if cat and cat[0] in ("L", "N"):
            out.append(ch)
    return "".join(out)

def tag_paired_gender(line: dict, gender: str) -> None:
    line["gender"] = gender
    line.setdefault("_debug", {}).setdefault("source", {})["gender"] = gender

def append_reference_line(
    lines: list[dict],
    seen_texts: set[tuple[str, str, str]],
    line_id: str,
    text: str,
    *,
    hint: str = "",
    actor: str = "",
    aid: str = "",
    debug: dict | None = None,
) -> None:
    normalized = (text or "").strip()
    if not normalized:
        return
    key = (hint, actor, normalized)
    if key in seen_texts:
        return
    seen_texts.add(key)
    line = {"id": line_id, "text": normalized}
    if hint:
        line["hint"] = hint
    if actor:
        line["actor"] = actor
    if aid:
        line["aid"] = aid
    if debug:
        line["_debug"] = debug
    lines.append(line)

def reference_kind_from_tags(tags: list[str] | None = None) -> str:
    for tag in tags or []:
        value = str(tag or "")
        if value.startswith("table_"):
            return value
    return "wiki"

def normalized_reference_tags(tags: list[str] | None, mission_id: str) -> list[str]:
    move_to_other = {"loadingTip", "task", "tip"}
    normalized_mission_id = str(mission_id or "").lower()
    if normalized_mission_id.startswith("wiki_collection_"):
        move_to_other.update({"collection", "worldtext"})
    if normalized_mission_id == "snschattable":
        move_to_other.add("snsChat")
    out: list[str] = []
    for raw_tag in tags or ["wiki"]:
        tag = str(raw_tag or "")
        if not tag:
            continue
        if tag in move_to_other:
            tag = "other"
        if tag not in out:
            out.append(tag)
    return out or ["wiki"]

def collection_slug(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z]+", "_", str(value or ""))
    return value.strip("_").lower() or "misc"

def collection_display_name(value: str) -> str:
    raw = str(value or "").strip().replace("_", " ")
    if not raw:
        return "Misc"
    raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw.isupper():
        return raw
    words = raw.split(" ")
    return " ".join(word[:1].upper() + word[1:] if word else "" for word in words)

def collection_bucket_from_key(row_id: str) -> str:
    value = str(row_id or "")
    if not value:
        return "misc"
    if value.isupper() and "_" in value:
        parts = [part for part in value.split("_") if part]
        return "_".join(parts[:2]) if len(parts) >= 2 else parts[0]
    if "_" in value:
        parts = [part for part in value.split("_") if part]
        if len(parts) >= 2 and parts[0] in {"activity", "battle", "bp", "char", "chr", "dung", "item", "npc", "radio", "skill", "sns", "system", "task", "wiki"}:
            return "_".join(parts[:2])
        return parts[0]
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", value)
    if words:
        return "_".join(words[:2])
    return value[:24]

def collection_scene_suffix(value: str) -> int:
    match = re.search(r"_(\d+)$", str(value or ""))
    return int(match.group(1)) if match else 0

def collection_scene_value(row: dict | None, fallback: int = 0) -> int:
    if not isinstance(row, dict):
        return fallback
    for field in ("order", "sortId", "sortOrder", "level", "priority", "stage", "step", "index"):
        value = row.get(field)
        if isinstance(value, int | float):
            return int(value)
    return fallback

def collection_source_label(table_source: str) -> str:
    return {
        "streaming": "StreamingAssets/Table",
        "persistent": "Persistent/Table",
    }.get(table_source, table_source)

def collection_text_fingerprint(text_nodes: list[dict]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for node in text_nodes:
        text = re.sub(r"\s+", " ", str(node.get("text") or "")).strip()
        if not text:
            continue
        rows.append((str(node.get("field") or ""), text))
    return tuple(rows)

def collection_table_name_tokens(table_name: str) -> list[str]:
    stem = table_name.removesuffix(".json")
    return [
        token.lower()
        for token in re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", stem)
        if token
    ]

def reference_row_texts(text_nodes: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for node in text_nodes:
        raw = node.get("raw") if isinstance(node, dict) else None
        item = {
            "field": str(node.get("field") or "text"),
            "path": str(node.get("path") or "$"),
            "text": str(node.get("text") or ""),
        }
        if node.get("hint"):
            item["hint"] = str(node["hint"])
        if isinstance(raw, dict) and raw.get("id") is not None:
            item["i18nId"] = str(raw.get("id"))
        rows.append(item)
    return rows

def prts_attachment_aliases(value: str) -> set[str]:
    raw = str(value or "").strip()
    if not raw:
        return set()
    aliases = {raw}
    lowered = raw.lower()
    if lowered.startswith("prts_") and lowered.endswith("_sns"):
        aliases.add(f"sns_{raw[5:-4]}")
    if lowered.startswith("reading_") and lowered.endswith("_sns"):
        aliases.add(f"sns_{raw[8:-4]}")
    return aliases

def responsive_sort_values(values: set[str] | list[str]) -> list[str]:
    tokens = [str(value) for value in values if str(value)]
    return sorted(
        tokens,
        key=lambda value: (0, int(value)) if value.lstrip("-").isdigit() else (1, value),
    )

def responsive_preview_values(values: list[str], *, limit: int = 4) -> str:
    tokens = [str(value) for value in values if str(value)]
    if not tokens:
        return ""
    if len(tokens) <= limit:
        return ", ".join(tokens)
    return ", ".join(tokens[:limit]) + f" +{len(tokens) - limit}"

def responsive_summary_rows(label: str, values: list[str], *, chunk_size: int = 8) -> list[dict]:
    tokens = [str(value) for value in values if str(value)]
    rows: list[dict] = []
    for idx, start in enumerate(range(0, len(tokens), chunk_size), start=1):
        prefix = label if idx == 1 else f"{label} (cont.)"
        rows.append({"text": f"{prefix}: {', '.join(tokens[start:start + chunk_size])}"})
    return rows

def sim_duplicate_actor_from_key(key: str) -> str:
    raw = str(key or "")
    if m := re.match(r"^misc_sim_(?:gift|talk|rest|work)_([^_]+)", raw):
        return str(m.group(1) or "").lower()
    if m := re.match(r"^env_greetEnvTalk_([^_]+)", raw):
        return str(m.group(1) or "").lower()
    return ""

def normalized_duplicate_line_texts(payload: dict) -> list[str]:
    out: list[str] = []
    for line in payload.get("lines") or []:
        text = " ".join(str(line.get("text") or "").split()).strip()
        if text:
            out.append(text)
    return out

def compact_story_source_link(link: dict) -> dict:
    source = str(link.get("source") or "")
    file_ref = str(link.get("file") or "")
    path_ref = str(link.get("path") or "")
    raw = str(link.get("raw") or "")
    context = link.get("context") if isinstance(link.get("context"), dict) else {}
    compact = {
        "source": source,
        "file": file_ref,
        "path": path_ref,
        "raw": raw,
        "kind": str(link.get("kind") or ""),
        "context": context,
        "_debug": {
            "source": {
                "source": source,
                "file": file_ref,
                "path": path_ref,
                "raw": raw,
                "kind": str(link.get("kind") or ""),
                "matchKind": str(link.get("matchKind") or ""),
                "context": context,
            },
        },
    }
    for optional in ("sourceKey", "mission", "levelId", "scriptId", "templateGroup", "templateId"):
        if link.get(optional):
            compact[optional] = link[optional]
            compact["_debug"]["source"][optional] = link[optional]
    return compact

def story_source_link_search_text(links: list[dict]) -> str:
    parts: list[str] = []
    for link in links:
        for field in ("raw", "source", "file", "path", "mission", "levelId", "scriptId", "templateId"):
            value = link.get(field)
            if value:
                parts.append(str(value))
        context = link.get("context") if isinstance(link.get("context"), dict) else {}
        owner = context.get("owner") if isinstance(context.get("owner"), dict) else {}
        for value in owner.values():
            if value:
                parts.append(str(value))
    return " ".join(parts)

def story_source_link_index_summary(links: list[dict]) -> dict:
    source_counts = Counter(str(link.get("source") or "") for link in links)
    files = _unique_preserve(str(link.get("file") or "") for link in links if link.get("file"))
    return {
        "n": len(links),
        "sources": {
            key: source_counts[key]
            for key in sorted(source_counts)
            if key
        },
        "files": files[:5],
    }

def compact_narrative_video_ref(ref: dict) -> dict:
    compact = {
        "name": str(ref.get("name") or ""),
        "rel": str(ref.get("rel") or ""),
        "source": str(ref.get("source") or ""),
        "format": str(ref.get("format") or ""),
        "size": int(ref.get("size") or 0),
        "stem": str(ref.get("stem") or ""),
        "baseStem": str(ref.get("baseStem") or ""),
        "kind": str(ref.get("kind") or ""),
        "_debug": {
            "source": {
                "rel": str(ref.get("rel") or ""),
                "source": str(ref.get("source") or ""),
                "name": str(ref.get("name") or ""),
                "kind": str(ref.get("kind") or ""),
                "keyCandidates": list(ref.get("keyCandidates") or []),
            },
        },
    }
    if ref.get("gender"):
        compact["gender"] = str(ref["gender"])
        compact["_debug"]["source"]["gender"] = str(ref["gender"])
    if ref.get("resolvedKey"):
        compact["_debug"]["source"]["resolvedKey"] = str(ref["resolvedKey"])
    binding = ref.get("binding")
    if isinstance(binding, dict):
        compact["binding"] = binding
        compact["_debug"]["source"]["binding"] = binding
    if ref.get("authoritativeKeys"):
        compact["_debug"]["source"]["authoritativeKeys"] = list(ref["authoritativeKeys"])
    attachment_override = ref.get("attachmentOverride")
    if isinstance(attachment_override, dict):
        compact["_debug"]["source"]["attachmentOverride"] = attachment_override
    return compact

def narrative_video_sort_key(ref: dict) -> tuple:
    source = str(ref.get("source") or "")
    fmt = str(ref.get("format") or "")
    source_rank = {
        "StreamingAssets-structured": 0,
        "Persistent-structured": 1,
        "raw_vfs": 2,
    }.get(source, 9)
    format_rank = {
        "mp4": 0,
        "webm": 1,
        "ogv": 2,
        "mov": 3,
        "m4v": 4,
        "avi": 5,
        "usm": 6,
    }.get(fmt, 9)
    gender = str(ref.get("gender") or "")
    gender_rank = {"": 0, "m": 1, "f": 2}.get(gender, 9)
    return (
        str(ref.get("baseStem") or ""),
        gender_rank,
        format_rank,
        source_rank,
        str(ref.get("rel") or ""),
    )

def narrative_video_search_text(refs: list[dict]) -> str:
    parts: list[str] = []
    for ref in refs:
        for field in ("name", "rel", "source", "stem", "baseStem", "gender", "format", "kind"):
            value = ref.get(field)
            if value:
                parts.append(str(value))
    return " ".join(parts)

def narrative_video_index_summary(refs: list[dict]) -> dict:
    source_counts = Counter(str(ref.get("source") or "") for ref in refs)
    format_counts = Counter(str(ref.get("format") or "") for ref in refs)
    names = _unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
    return {
        "n": len(refs),
        "sources": {
            key: source_counts[key]
            for key in sorted(source_counts)
            if key
        },
        "formats": {
            key: format_counts[key]
            for key in sorted(format_counts)
            if key
        },
        "files": names[:5],
    }

def build_mission_map_pins(flow: dict | None) -> list[dict]:
    if not flow:
        return []
    merged: dict[tuple, dict] = {}
    for quest in flow.get("quests") or []:
        for pin in quest.get("pins") or []:
            position = pin.get("position") or {}
            key = (
                pin.get("scene") or "",
                pin.get("sourceType") or "",
                pin.get("trackingType") or "",
                pin.get("missionAreaId") or "",
                pin.get("npcProxyId") or "",
                round(float(position.get("x", 0.0)), 3),
                round(float(position.get("y", 0.0)), 3),
                round(float(position.get("z", 0.0)), 3),
            )
            row = merged.get(key)
            if row is None:
                row = {
                    "scene": pin.get("scene") or "",
                    "sourceType": pin.get("sourceType") or "",
                    "trackingType": pin.get("trackingType") or "",
                    "position": {
                        "x": float(position.get("x", 0.0)),
                        "y": float(position.get("y", 0.0)),
                        "z": float(position.get("z", 0.0)),
                    },
                    "questIds": [],
                    "flowIndices": [],
                }
                if pin.get("missionAreaId"):
                    row["missionAreaId"] = pin["missionAreaId"]
                if pin.get("npcProxyId"):
                    row["npcProxyId"] = pin["npcProxyId"]
                if pin.get("radius") is not None:
                    row["radius"] = pin["radius"]
                if pin.get("routePointCount") is not None:
                    row["routePointCount"] = pin["routePointCount"]
                merged[key] = row
            quest_id = quest.get("id") or ""
            if quest_id and quest_id not in row["questIds"]:
                row["questIds"].append(quest_id)
            flow_index = quest.get("flowIndex")
            if flow_index is not None and flow_index not in row["flowIndices"]:
                row["flowIndices"].append(flow_index)
    return sorted(
        merged.values(),
        key=lambda row: (
            min(row.get("flowIndices") or [10**9]),
            row.get("scene") or "",
            row.get("sourceType") or "",
            row["position"]["x"],
            row["position"]["z"],
        ),
    )

def build_mission_timeline_recovery_report(
    scene_graphs: dict[str, dict],
    mission_flows: dict[str, dict] | None = None,
) -> dict:
    timeline_index, timeline_meta = load_mission_timeline_index(
        timeline_recovery_order_out(EXPORT_ROOT)
    )
    recovered: list[dict] = []
    files = mission_timeline_files(MRA_DIR, set()) if MRA_DIR.is_dir() else []
    script_condition_ownership = build_mission_script_condition_ownership(files)
    mission_flows = mission_flows or {}
    for path in files:
        mission_id = path.stem
        recovered.append(
            recover_source_mission_timeline(
                path,
                timeline_index,
                None,
                source_backed_scene_edges_from_scene_graph(
                    scene_graphs.get(mission_id)
                ),
                source_backed_story_call_contexts_from_scene_graph(
                    scene_graphs.get(mission_id)
                ),
                source_backed_hash_terminals_from_scene_graph(
                    scene_graphs.get(mission_id)
                ),
                source_backed_call_server_callbacks_from_scene_graph(
                    scene_graphs.get(mission_id)
                ),
                script_condition_ownership=script_condition_ownership,
                mission_flow=mission_flows.get(mission_id),
            )
        )
    return {
        "evidencePolicy": MISSION_TIMELINE_EVIDENCE_POLICY,
        "summary": summarize_mission_timeline_recovery(
            recovered,
            timeline_meta,
            generated_by="scripts/story_builder/build.py",
        ),
        "missions": recovered,
    }

def safe_mission_data_filename(mission_id: str, used_names: set[str]) -> str:
    stem = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(mission_id or "")).strip("._")
    if not stem:
        stem = "mission"
    name = f"{stem}.json"
    if name.lower() not in used_names:
        used_names.add(name.lower())
        return name
    index = 2
    while True:
        candidate = f"{stem}_{index}.json"
        if candidate.lower() not in used_names:
            used_names.add(candidate.lower())
            return candidate
        index += 1

__all__ = [name for name in globals() if not name.startswith("__")]



