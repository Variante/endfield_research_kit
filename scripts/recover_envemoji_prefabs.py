"""Reconstruct ENV_EMOJI_PREFABS data for the WebUI from original Unity prefabs.

Pipeline overview:

1. Locate the .ab AssetBundle files that contain each `emoji_*.prefab`
   under `assets/beyond/dynamicassets/gameplay/ui/prefabs/emoji/`.
   The mapping is built by scanning AssetBundle JSON files emitted by
   AnimeStudio.CLI in `m_Container` form.
2. Run AnimeStudio.CLI in two modes against those bundles:
   - text Dump for `MonoBehaviour`/`RectTransform` (the UI fields
     `m_AnchoredPosition`, `m_SizeDelta`, `m_Pivot`, etc. live in the
     TypeTree dump and are NOT serialized by AnimeStudio's JSON exporter).
   - JSON for `GameObject` (gives each GameObject's own PathID through
     `m_Transform.m_GameObject.m_PathID`, which the text dump does not
     expose directly).
3. Merge the two outputs to build a hierarchy keyed by GameObject PathID.
4. Walk the hierarchy from the prefab's root GameObject, propagating
   `m_LocalScale` and accumulating `m_AnchoredPosition` so each Image
   component's final position/size are in the prefab's own pixel space.
5. Cross-reference each Image's `m_Sprite` PPtr against the StreamingAssets
   asset map to recover the sprite stem name.
6. Optionally normalize the prefab by uniformly scaling all layers so the
   prefab's bounding box fits the WebUI stage width (~89.5px).

Inputs:
    - `export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json`
      (StreamingAssets asset map produced by an earlier AssetStudio run).
    - `export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AssetBundle/*.json`
      (per-bundle container manifests; same prior run).
    - `export_full/raw_vfs/StreamingAssets/files/7064D8E2/Data/Bundles/Windows/main/*.ab`
      (decrypted, raw Unity AssetBundle blobs).
    - `tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe`.

Output:
    - `webui/app.js` is NOT updated by this script. It writes a standalone JS
      snippet to `tmp/assets/emoji_extract/env_emoji_prefabs.js`. Copy the
      `ENV_EMOJI_PREFABS` body into `webui/app.js` after reviewing diffs.

Run via `python scripts/recover_envemoji_prefabs.py`. The whole pipeline takes
under a minute given the small number of emoji bundles.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO / "scripts"))

from common import path_id_export_base_stem

ASSET_MAP = REPO / "export_full" / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "maps" / "endfield_streamingassets_assets.json"
BUNDLE_DIR = REPO / "export_full" / "raw_vfs" / "StreamingAssets" / "files" / "7064D8E2" / "Data" / "Bundles" / "Windows" / "main"
ASSETBUNDLE_JSON_DIR = REPO / "export_full" / "recovered" / "AnimeStudio-cli" / "StreamingAssets" / "json_by_type" / "AssetBundle"
ANIMESTUDIO_CLI = REPO / "tools" / "AnimeStudio" / "AnimeStudio.CLI" / "bin" / "Release" / "net9.0-windows" / "AnimeStudio.CLI.exe"

WORK_ROOT = REPO / "tmp" / "assets" / "emoji_extract"
WORK_BUNDLES = WORK_ROOT / "bundles"
WORK_DUMP = WORK_ROOT / "out_dump"
WORK_JSON = WORK_ROOT / "out_json"
OUTPUT_JS = WORK_ROOT / "env_emoji_prefabs.js"

# Prefabs the WebUI cares about (line-level emojiId values for envEmoji_common_*).
TARGET_PREFABS = (
    "emoji_adaptationwork",
    "emoji_empty",
    "emoji_exhaustion",
    "emoji_love",
    "emoji_newdislike",
    "emoji_newhappy",
    "emoji_newsad",
    "emoji_newsigh",
    "emoji_newsurprise",
    "emoji_newworkhard",
    "emoji_normal",
    "emoji_think",
    "emoji_thumbsup",
    "emoji_unhappywork",
)

STAGE_TARGET_W = 89.5  # Reference width matching the hand-crafted emoji_newbg layer.


# ---------------------------------------------------------------------------
# Step 1 — locate bundles
# ---------------------------------------------------------------------------

PREFAB_LINE_RE = re.compile(
    rb"assets/beyond/dynamicassets/gameplay/ui/prefabs/emoji/(emoji_[a-z0-9_]+)\.prefab"
)


def find_bundles_for_prefabs(prefab_names):
    """Scan AssetBundle JSON manifests for the requested prefab containers.

    Returns dict: prefab_name -> bundle filename (e.g. ``main_abc.ab``).
    """
    targets = set(prefab_names)
    found = {}
    for path in ASSETBUNDLE_JSON_DIR.iterdir():
        stem = path_id_export_base_stem(path.stem)
        if not stem or not stem.endswith(".ab"):
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"prefabs/emoji/" not in data:
            continue
        for m in PREFAB_LINE_RE.finditer(data):
            name = m.group(1).decode()
            if name not in targets or name in found:
                continue
            found[name] = stem
            if len(found) == len(targets):
                return found
    return found


# ---------------------------------------------------------------------------
# Step 2 — run AnimeStudio.CLI
# ---------------------------------------------------------------------------

def stage_bundles(prefab_to_bundle):
    WORK_BUNDLES.mkdir(parents=True, exist_ok=True)
    for old in WORK_BUNDLES.iterdir():
        old.unlink()
    for prefab, bundle_filename in prefab_to_bundle.items():
        # Bundle filename has a `main_` prefix from the AssetBundle JSON naming
        # convention; the on-disk file uses the raw hash.
        raw_filename = bundle_filename.split("_", 1)[1] if bundle_filename.startswith("main_") else bundle_filename
        src = BUNDLE_DIR / raw_filename
        if not src.exists():
            raise FileNotFoundError(f"missing bundle {src} for prefab {prefab}")
        shutil.copy(src, WORK_BUNDLES / bundle_filename)


def run_animestudio(out_dir: Path, types: list[str], export_type: str):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    cmd = [
        str(ANIMESTUDIO_CLI),
        str(WORK_BUNDLES),
        str(out_dir),
        "--game", "ArknightsEndfield",
        "--types", *types,
        "--export_type", export_type,
        "--group_assets", "BySource",
        "--silent",
    ]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# Step 3 — parse dumps
# ---------------------------------------------------------------------------

def _coerce(value: str):
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value in ("True", "true"):
        return True
    if value in ("False", "false"):
        return False
    try:
        if "." in value or "e" in value.lower():
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_dump_text(text: str):
    lines = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        ind = len(raw) - len(raw.lstrip("\t"))
        lines.append((ind, raw.lstrip("\t")))
    if not lines:
        return "", {}

    pos = [1]
    root: dict = {}
    first_ind, first_line = lines[0]
    root_type = first_line.split()[0] if first_line.split() else ""

    def parse_block(parent_indent: int, parent):
        while pos[0] < len(lines):
            ind, line = lines[pos[0]]
            if ind <= parent_indent:
                return
            pos[0] += 1
            if "=" in line:
                head, val = line.rsplit("=", 1)
                tokens = head.split()
                key = tokens[-1] if tokens else head.strip()
                _assign(parent, key, _coerce(val))
            else:
                tokens = line.split()
                if not tokens:
                    continue
                if tokens[0].startswith("[") and tokens[0].endswith("]"):
                    new_elem: dict = {}
                    parent.setdefault("_items", []).append(new_elem)
                    parse_block(ind, new_elem)
                else:
                    name = tokens[-1]
                    child: dict = {}
                    _assign(parent, name, child)
                    parse_block(ind, child)

    def _assign(parent, key, value):
        if key in parent and isinstance(parent[key], list):
            parent[key].append(value)
        elif key in parent:
            parent[key] = [parent[key], value]
        else:
            parent[key] = value

    parse_block(first_ind, root)
    return root_type, root


# ---------------------------------------------------------------------------
# Step 4 — merge GameObject JSON + RectTransform/Image Dump
# ---------------------------------------------------------------------------

def cab_dir(parent: Path) -> Path:
    for p in parent.iterdir():
        if p.is_dir() and p.name.startswith("CAB-"):
            return p
    raise RuntimeError(f"no CAB under {parent}")


def load_sprite_map():
    print("Loading asset map (this is slow)...", file=sys.stderr)
    with ASSET_MAP.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {int(e["PathID"]): e.get("Name") or "" for e in data["AssetEntries"] if e.get("Type") == "Sprite"}


def parse_bundle(bundle_dump_dir: Path, bundle_json_dir: Path):
    dump_cab = cab_dir(bundle_dump_dir)
    json_cab = cab_dir(bundle_json_dir)

    gos = []
    # AnimeStudio CLI emits JSON and Dump for the same GameObject with the
    # same filename stem (e.g. emoji_love.json / emoji_love.txt and the
    # patched dedup variant emoji_love_pXXX.json / emoji_love_pXXX.txt).
    # Several emoji prefabs ship two distinct GameObjects with the same
    # m_Name, so the stem is what differentiates them — not m_Name.
    go_pid_by_stem: dict[str, int] = {}
    for path in json_cab.iterdir():
        if path.suffix != ".json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "m_Components" not in data:
            continue
        comp_pids = [int(c["m_PathID"]) for c in data.get("m_Components", []) if not c.get("IsNull")]
        tr = data.get("m_Transform") or {}
        go_pid = int((tr.get("m_GameObject") or {}).get("m_PathID", 0))
        gos.append({
            "name": data.get("m_Name") or "",
            "go_pid": go_pid,
            "comp_pids": comp_pids,
            "is_active": True,  # filled in by Dump pass below
        })
        if go_pid:
            go_pid_by_stem[path.stem] = go_pid

    rts_by_go_pid = {}
    images_by_go_pid = {}
    # Use Dump output to recover RT UI fields + GameObject m_IsActive (the JSON
    # exporter omits both).
    active_by_go_pid: dict[int, bool] = {}
    for path in dump_cab.iterdir():
        if path.suffix != ".txt":
            continue
        type_name, body = parse_dump_text(path.read_text(encoding="utf-8"))
        if type_name == "GameObject":
            go_pid = go_pid_by_stem.get(path.stem)
            if go_pid is not None:
                active_by_go_pid[go_pid] = bool(body.get("m_IsActive", True))
        elif type_name == "RectTransform":
            pid = (body.get("m_GameObject") or {}).get("m_PathID")
            father = (body.get("m_Father") or {}).get("m_PathID", 0) or 0
            if pid is not None:
                body["_father_pid"] = int(father)
                rts_by_go_pid[int(pid)] = body
        elif type_name == "MonoBehaviour":
            if "m_Sprite" in body and "m_Color" in body:
                pid = (body.get("m_GameObject") or {}).get("m_PathID")
                if pid is not None:
                    images_by_go_pid.setdefault(int(pid), []).append(body)

    for g in gos:
        g["is_active"] = active_by_go_pid.get(g["go_pid"], True)

    comp_to_go = {c: g for g in gos for c in g["comp_pids"]}
    parent_to_children: dict[int, list[int]] = {}
    for child in gos:
        rt = rts_by_go_pid.get(child["go_pid"])
        if not rt:
            continue
        father_pid = rt["_father_pid"]
        if father_pid == 0:
            continue
        parent_go = comp_to_go.get(father_pid)
        if parent_go is None:
            continue
        parent_to_children.setdefault(parent_go["go_pid"], []).append(child["go_pid"])

    return {
        "by_pid": {g["go_pid"]: g for g in gos},
        "rts_by_go_pid": rts_by_go_pid,
        "images_by_go_pid": images_by_go_pid,
        "parent_to_children": parent_to_children,
        "gos": gos,
    }


def collect_layers(info, prefab_name, sprite_map):
    root = next((g for g in info["gos"] if g["name"] == prefab_name), None)
    if root is None:
        return None

    layers = []

    # Unity UI composition: m_AnchoredPosition places the child's pivot at an
    # offset from its anchor point. The anchor is at `anchorMin * parent_size`
    # measured from parent's rect bottom-left. Parent's rect bottom-left is
    # `parent_pivot_stage - parent_pivot * parent_size`. When anchorMin ==
    # anchorMax the anchor is a single point — we assume that (the standard
    # case for prefab leaves; stretch anchors would need anchorMax handling).
    def walk(go_pid, parent_pivot_stage_x, parent_pivot_stage_y,
             parent_size_w, parent_size_h,
             parent_pivot_x, parent_pivot_y,
             parent_scale_x, parent_scale_y):
        if not info["by_pid"].get(go_pid, {}).get("is_active", True):
            return  # inactive subtree — skip self and children

        rt = info["rts_by_go_pid"].get(go_pid)
        if not rt:
            for ch in info["parent_to_children"].get(go_pid, []):
                walk(ch, parent_pivot_stage_x, parent_pivot_stage_y,
                     parent_size_w, parent_size_h,
                     parent_pivot_x, parent_pivot_y,
                     parent_scale_x, parent_scale_y)
            return

        ap = rt.get("m_AnchoredPosition", {})
        sd = rt.get("m_SizeDelta", {})
        pv = rt.get("m_Pivot", {})
        sc = rt.get("m_LocalScale", {})
        anchor_min = rt.get("m_AnchorMin", {})
        ax = float(ap.get("x", 0)); ay = float(ap.get("y", 0))
        sx = float(sd.get("x", 0)); sy = float(sd.get("y", 0))
        px = float(pv.get("x", 0.5)); py = float(pv.get("y", 0.5))
        scx = float(sc.get("x", 1)); scy = float(sc.get("y", 1))
        amin_x = float(anchor_min.get("x", 0.5)); amin_y = float(anchor_min.get("y", 0.5))

        # Compute parent's rect bottom-left in stage coords from its pivot point.
        parent_origin_x = parent_pivot_stage_x - parent_pivot_x * parent_size_w * parent_scale_x
        parent_origin_y = parent_pivot_stage_y - parent_pivot_y * parent_size_h * parent_scale_y
        anchor_stage_x = parent_origin_x + amin_x * parent_size_w * parent_scale_x
        anchor_stage_y = parent_origin_y + amin_y * parent_size_h * parent_scale_y

        eff_sx = parent_scale_x * scx
        eff_sy = parent_scale_y * scy
        pivot_stage_x = anchor_stage_x + ax * parent_scale_x
        pivot_stage_y = anchor_stage_y + ay * parent_scale_y
        w = sx * eff_sx
        h = sy * eff_sy

        for img in info["images_by_go_pid"].get(go_pid, []):
            sprite_pid = int((img.get("m_Sprite") or {}).get("m_PathID", 0))
            sprite_name = sprite_map.get(sprite_pid, "")
            color = img.get("m_Color") or {}
            layers.append({
                "stem": sprite_name,
                "x": round(pivot_stage_x, 3),
                "y": round(pivot_stage_y, 3),
                "w": round(w, 3),
                "h": round(h, 3),
                "px": round(px, 3),
                "py": round(py, 3),
                "color": (
                    round(float(color.get("r", 0)), 4),
                    round(float(color.get("g", 0)), 4),
                    round(float(color.get("b", 0)), 4),
                    round(float(color.get("a", 1)), 4),
                ),
                "flipX": eff_sx < 0,
            })

        for ch in info["parent_to_children"].get(go_pid, []):
            walk(ch, pivot_stage_x, pivot_stage_y,
                 sx, sy,  # this rect's size becomes children's parent_size
                 px, py,
                 eff_sx, eff_sy)

    walk(root["go_pid"], 0.0, 0.0, 0.0, 0.0, 0.5, 0.5, 1.0, 1.0)
    return layers


# ---------------------------------------------------------------------------
# Step 5 — JS emit
# ---------------------------------------------------------------------------

def rgba_string(c):
    R = max(0, min(255, round(c[0] * 255)))
    G = max(0, min(255, round(c[1] * 255)))
    B = max(0, min(255, round(c[2] * 255)))
    A = round(c[3], 3)
    return f"rgba({R}, {G}, {B}, {A})"


def is_default_color(c):
    return abs(c[0] - 1) < 1e-3 and abs(c[1] - 1) < 1e-3 and abs(c[2] - 1) < 1e-3 and abs(c[3] - 1) < 1e-3


def fmt_num(v):
    return f"{round(v, 2):g}"


def emit_layer(L):
    parts = [f'stem: "{L["stem"]}"']
    parts.append(f"x: {fmt_num(L['x'])}")
    parts.append(f"y: {fmt_num(L['y'])}")
    parts.append(f"w: {fmt_num(abs(L['w']))}")
    parts.append(f"h: {fmt_num(abs(L['h']))}")
    parts.append(f"px: {fmt_num(L['px'])}")
    parts.append(f"py: {fmt_num(L['py'])}")
    if L.get("color") and not is_default_color(L["color"]):
        parts.append(f'color: "{rgba_string(L["color"])}"')
    if L.get("flipX") or (L["w"] < 0):
        parts.append("flipX: true")
    return "    { " + ", ".join(parts) + " },"


def fit_scale(layers):
    if not layers:
        return 1.0
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for L in layers:
        w = abs(L["w"]); h = abs(L["h"])
        left = L["x"] - L["px"] * w
        right = L["x"] + (1 - L["px"]) * w
        bot = L["y"] - (1 - L["py"]) * h
        top = L["y"] + L["py"] * h
        minx = min(minx, left); maxx = max(maxx, right)
        miny = min(miny, bot); maxy = max(maxy, top)
    span = max(1.0, maxx - minx)
    return STAGE_TARGET_W / span if span > STAGE_TARGET_W * 1.2 else 1.0


def main():
    if not ASSET_MAP.exists():
        sys.exit(f"missing asset map: {ASSET_MAP}")
    if not ANIMESTUDIO_CLI.exists():
        sys.exit(f"missing AnimeStudio.CLI: {ANIMESTUDIO_CLI}")
    if not BUNDLE_DIR.exists():
        sys.exit(f"missing bundle dir: {BUNDLE_DIR}")

    print("Locating bundles...", file=sys.stderr)
    prefab_to_bundle = find_bundles_for_prefabs(TARGET_PREFABS)
    missing = [p for p in TARGET_PREFABS if p not in prefab_to_bundle]
    if missing:
        sys.exit(f"could not locate bundles for: {missing}")
    for p, b in prefab_to_bundle.items():
        print(f"  {p:30s} -> {b}", file=sys.stderr)

    print("Staging bundles...", file=sys.stderr)
    stage_bundles(prefab_to_bundle)

    print("Running AnimeStudio (Dump pass)...", file=sys.stderr)
    run_animestudio(
        WORK_DUMP,
        ["MonoBehaviour:Both", "RectTransform:Both", "Transform:Both",
         "GameObject:Both", "AnimationClip:Both", "Animation:Both"],
        "Dump",
    )
    print("Running AnimeStudio (JSON pass)...", file=sys.stderr)
    run_animestudio(
        WORK_JSON,
        ["GameObject:Both", "Transform:Both", "RectTransform:Both"],
        "JSON",
    )

    sprite_map = load_sprite_map()

    by_prefab = {}
    for bundle_filename in prefab_to_bundle.values():
        dump_dir = WORK_DUMP / f"{bundle_filename}_export"
        json_dir = WORK_JSON / f"{bundle_filename}_export"
        info = parse_bundle(dump_dir, json_dir)
        for name in TARGET_PREFABS:
            if name in by_prefab:
                continue
            layers = collect_layers(info, name, sprite_map)
            if layers is None:
                continue
            by_prefab[name] = layers

    out_lines = ["const ENV_EMOJI_PREFABS = {"]
    for name in TARGET_PREFABS:
        layers = by_prefab.get(name)
        if not layers:
            print(f"WARN: no layers extracted for {name}", file=sys.stderr)
            continue
        kept = [L for L in layers if (L["stem"] or "").startswith("emoji_") and L["color"][3] >= 0.01]
        s = fit_scale(kept)
        if s != 1.0:
            for L in kept:
                L["x"] = round(L["x"] * s, 3)
                L["y"] = round(L["y"] * s, 3)
                L["w"] = round(L["w"] * s, 3)
                L["h"] = round(L["h"] * s, 3)
        out_lines.append(f"  {name}: [")
        for L in kept:
            out_lines.append(emit_layer(L))
        out_lines.append("  ],")
    out_lines.append("};\n")

    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JS.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_JS}")


if __name__ == "__main__":
    main()
