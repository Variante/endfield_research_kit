from __future__ import annotations

import html
import re

if __package__ == "story_builder":
    from common import is_present
elif __package__ == "scripts.story_builder":
    from ..common import is_present
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("import this module as scripts.story_builder.bundle_primitives")


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

__all__ = [
    "clean_media_id_value",
    "written_path_key",
    "norm_id",
    "pick_fields",
    "source_ref",
    "inline_image_tag",
    "text_sequence_fingerprint",
    "brace_text",
    "sns_raw_title",
    "normalize_blackbox_id",
    "norm_template_id",
    "icon_basename",
    "env_group",
    "env_story_mission",
    "line_haystack",
    "line_identity_haystack",
    "line_option_haystack",
    "merge_search_text",
    "format_webui_timeline_seconds",
]



