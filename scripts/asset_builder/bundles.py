from __future__ import annotations

import json
import re
import textwrap
import zipfile
from collections import defaultdict
from pathlib import Path

from asset_builder.index import ASSET_LOD_SUFFIX_RE, ASSET_SINGLE_PREFIX_RE
from common import ASSET_DIR, ROOT, write_json


DEMO_BUNDLES = (
    {
        "id": "m_wpn_funnel_0015_01_blender_demo",
        "material_rel": "StreamingAssets-materials/Material/M_wpn_funnel_0015_01.json",
        "label": "Blender Demo: M_wpn_funnel_0015_01",
        "description": (
            "Downloads the recovered material JSON, matching PNG textures, OBJ LODs, "
            "and a Blender import helper for M_wpn_funnel_0015_01."
        ),
    },
    {
        "id": "m_item_widget_zhuangfy_09_blender_demo",
        "material_rel": "StreamingAssets-materials/Material/M_item_widget_zhuangfy_09.json",
        "label": "Blender Demo: M_item_widget_zhuangfy_09",
        "description": (
            "Downloads the recovered material JSON, matching PNG textures, OBJ LODs, "
            "and a Blender import helper for M_item_widget_zhuangfy_09."
        ),
    },
)

TEXTURE_SLOT_TAG_HINTS = {
    "_BaseMap": ("D", "BaseColor", "Albedo", "Diffuse"),
    "_MainTex": ("D", "BaseColor", "Albedo", "Diffuse"),
    "_BaseColorMap": ("D", "BaseColor", "Albedo", "Diffuse"),
    "_AlbedoMap": ("D", "BaseColor", "Albedo", "Diffuse"),
    "_BumpMap": ("N", "Normal"),
    "_NormalMap": ("N", "Normal"),
    "_EmissionMap": ("E", "Emission", "Emissive"),
    "_MetallicGlossMap": ("P", "Mask", "Metallic"),
    "_MaskMap": ("P", "Mask", "Metallic"),
    "_OcclusionMap": ("AO", "Occlusion"),
}
TEXTURE_TAG_SUFFIX_RE = re.compile(
    r"^(?P<base>.+?)[_-](?P<tag>d|n|e|p|ao|mask|metallic|normal|basecolor|albedo|diffuse|emission|emissive|occlusion)$",
    re.IGNORECASE,
)


def _normalize_rel(rel: str) -> str:
    return str(rel or "").replace("\\", "/").strip("/")


def _source_family(label: str) -> str:
    return str(label or "").split("-", 1)[0]


def _strip_asset_prefix(name: str) -> str:
    return ASSET_SINGLE_PREFIX_RE.sub("", str(name or ""), count=1)


def _normalize_model_base(stem: str) -> str:
    return ASSET_LOD_SUFFIX_RE.sub("", _strip_asset_prefix(stem)).lower()


def _normalize_material_base(stem: str) -> str:
    return _strip_asset_prefix(stem).lower()


def _normalize_texture_base(stem: str) -> str:
    normalized = _strip_asset_prefix(stem).lower()
    match = TEXTURE_TAG_SUFFIX_RE.match(normalized)
    return match.group("base") if match else normalized


def _extract_material_texture_refs(material_payload: dict) -> list[dict]:
    tex_envs = ((material_payload.get("m_SavedProperties") or {}).get("m_TexEnvs") or {})
    out: list[dict] = []
    for slot, tex_env in sorted(tex_envs.items()):
        texture = (tex_env or {}).get("m_Texture") or {}
        texture_name = str(texture.get("Name") or "").strip()
        if texture.get("IsNull"):
            continue
        out.append({
            "slot": slot,
            "name": texture_name,
        })
    return out


def _extract_material_settings(material_payload: dict) -> dict:
    saved = material_payload.get("m_SavedProperties") or {}
    colors = saved.get("m_Colors") or {}
    floats = saved.get("m_Floats") or {}

    def color_value(name: str, fallback: tuple[float, float, float, float]) -> list[float]:
        value = colors.get(name) or {}
        return [
            float(value.get("r", fallback[0])),
            float(value.get("g", fallback[1])),
            float(value.get("b", fallback[2])),
            float(value.get("a", fallback[3])),
        ]

    def float_value(name: str, fallback: float) -> float:
        value = floats.get(name)
        if value is None:
            return fallback
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    smoothness = max(0.0, min(1.0, float_value("_Smoothness", 0.5)))
    return {
        "baseColor": color_value("_BaseColor", (1.0, 1.0, 1.0, 1.0)),
        "emissionColor": color_value("_EmissionColor", (0.0, 0.0, 0.0, 1.0)),
        "emissionStrength": float_value("_EmissionBrightness", 1.0),
        "metallic": max(0.0, min(1.0, float_value("_Metallic", 0.0))),
        "smoothness": smoothness,
        "roughness": 1.0 - smoothness,
    }


def _load_asset_index(index_path: Path) -> dict:
    with index_path.open(encoding="utf-8") as f:
        return json.load(f)


def _resolve_export_path(rel: str, asset_index: dict) -> Path:
    rel = _normalize_rel(rel)
    if not rel:
        raise ValueError("Cannot resolve an empty asset relative path.")

    source, _, rel_suffix = rel.partition("/")
    source_roots = asset_index.get("sourceRoots") or {}
    source_root = str(source_roots.get(source) or "").strip()
    if not source_root:
        raise KeyError(f"Missing source root for {source!r} while resolving {rel!r}")

    path = ROOT / Path(source_root)
    if rel_suffix:
        path = path / Path(rel_suffix)
    return path


def _build_asset_lookup(entries: list[dict]) -> dict:
    image_rels_by_source_stem: dict[tuple[str, str], list[str]] = defaultdict(list)
    image_rels_by_stem: dict[str, list[str]] = defaultdict(list)
    image_rels_by_source_base: dict[tuple[str, str], list[str]] = defaultdict(list)
    image_rels_by_base: dict[str, list[str]] = defaultdict(list)
    model_rels_by_source_base: dict[tuple[str, str], list[str]] = defaultdict(list)
    model_rels_by_base: dict[str, list[str]] = defaultdict(list)

    for entry in entries:
        rel = _normalize_rel(entry.get("r") or "")
        if not rel:
            continue
        source, _, _ = rel.partition("/")
        source_family = _source_family(source).lower()
        stem = Path(rel).stem
        kind = entry.get("k")
        if kind == "image":
            image_rels_by_source_stem[(source_family, stem.lower())].append(rel)
            image_rels_by_stem[stem.lower()].append(rel)
            texture_base = _normalize_texture_base(stem)
            image_rels_by_source_base[(source_family, texture_base)].append(rel)
            image_rels_by_base[texture_base].append(rel)
        elif kind == "model":
            model_base = _normalize_model_base(stem)
            model_rels_by_source_base[(source_family, model_base)].append(rel)
            model_rels_by_base[model_base].append(rel)

    return {
        "image_rels_by_source_stem": image_rels_by_source_stem,
        "image_rels_by_stem": image_rels_by_stem,
        "image_rels_by_source_base": image_rels_by_source_base,
        "image_rels_by_base": image_rels_by_base,
        "model_rels_by_source_base": model_rels_by_source_base,
        "model_rels_by_base": model_rels_by_base,
    }


def _choose_preferred_rel(candidates: list[str], source: str) -> str:
    normalized = sorted({_normalize_rel(candidate) for candidate in candidates if candidate})
    if not normalized:
        return ""

    source_lower = str(source or "").lower()
    same_source = [candidate for candidate in normalized if candidate.split("/", 1)[0].lower() == source_lower]
    if same_source:
        return same_source[0]

    source_family = _source_family(source).lower()
    same_family = [
        candidate
        for candidate in normalized
        if _source_family(candidate.split("/", 1)[0]).lower() == source_family
    ]
    return same_family[0] if same_family else normalized[0]


def _pick_models_for_material(material_rel: str, lookup: dict) -> list[str]:
    source, _, _ = _normalize_rel(material_rel).partition("/")
    material_name = Path(material_rel).stem
    material_base = _normalize_material_base(material_name)
    source_family = _source_family(source)

    matches = lookup["model_rels_by_source_base"].get((source_family.lower(), material_base)) or []
    if matches:
        return sorted(matches)
    return sorted(lookup["model_rels_by_base"].get(material_base) or [])


def _candidate_texture_stems(material_rel: str, slot: str, texture_name: str) -> list[str]:
    candidates: list[str] = []
    explicit_name = str(texture_name or "").strip()
    if explicit_name:
        candidates.append(explicit_name)

    material_base = _normalize_material_base(Path(material_rel).stem)
    # Some recovered materials keep non-null texture refs but lose the texture Name field.
    for tag in TEXTURE_SLOT_TAG_HINTS.get(str(slot or ""), ()):
        candidates.append(f"T_{material_base}_{tag}")
        candidates.append(f"{material_base}_{tag}")
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def _resolve_texture_rel(material_rel: str, slot: str, texture_name: str, lookup: dict) -> str:
    source, _, _ = _normalize_rel(material_rel).partition("/")
    source_lower = _source_family(source).lower()
    for candidate_stem in _candidate_texture_stems(material_rel, slot, texture_name):
        candidate_key = candidate_stem.lower()
        source_matches = lookup["image_rels_by_source_stem"].get((source_lower, candidate_key)) or []
        any_matches = lookup["image_rels_by_stem"].get(candidate_key) or []
        resolved_rel = _choose_preferred_rel(source_matches or any_matches, source)
        if resolved_rel:
            return resolved_rel

    material_base = _normalize_material_base(Path(material_rel).stem)
    source_base_matches = lookup["image_rels_by_source_base"].get((source_lower, material_base)) or []
    any_base_matches = lookup["image_rels_by_base"].get(material_base) or []
    relaxed_candidates = sorted({
        _normalize_rel(candidate)
        for candidate in (source_base_matches or any_base_matches)
        if candidate
    })
    if len(relaxed_candidates) == 1:
        return relaxed_candidates[0]
    return ""


def _pick_textures_for_material(material_rel: str, material_payload: dict, lookup: dict) -> list[dict]:
    textures: list[dict] = []
    for ref in _extract_material_texture_refs(material_payload):
        resolved_rel = _resolve_texture_rel(material_rel, ref["slot"], ref["name"], lookup)
        resolved = {
            "slot": ref["slot"],
            "name": ref["name"] or Path(resolved_rel).stem,
        }
        if resolved_rel:
            resolved["rel"] = resolved_rel
        textures.append(resolved)
    return textures


def _archive_folder_for_kind(kind: str) -> str:
    return {
        "material": "material",
        "model": "models",
        "texture": "textures",
        "doc": "",
        "script": "blender",
        "manifest": "",
    }.get(kind, "files")


def _blender_helper_text(bundle: dict) -> str:
    config_json = json.dumps(bundle["blenderConfig"], ensure_ascii=False, indent=2)
    config_block = textwrap.indent(config_json, " " * 8)
    return textwrap.dedent(
        f"""\
        import json
        from pathlib import Path

        import bpy

        CONFIG = json.loads(r'''
{config_block}
        ''')


        def resolve_bundle_dir():
            candidates = []

            raw_file = globals().get("__file__")
            if raw_file:
                candidates.append(Path(raw_file))

            space = getattr(bpy.context, "space_data", None)
            text = getattr(space, "text", None)
            text_filepath = getattr(text, "filepath", "") if text else ""
            if text_filepath:
                candidates.append(Path(bpy.path.abspath(text_filepath)))

            for candidate in candidates:
                try:
                    resolved = candidate.expanduser().resolve()
                except Exception:
                    try:
                        resolved = candidate.expanduser()
                    except Exception:
                        resolved = candidate

                script_dir = resolved if resolved.is_dir() else resolved.parent
                search_dirs = [script_dir]
                if script_dir.name.lower() == "blender":
                    search_dirs.append(script_dir.parent)
                else:
                    search_dirs.append(script_dir / "..")

                for search_dir in search_dirs:
                    try:
                        normalized = search_dir.resolve()
                    except Exception:
                        normalized = search_dir
                    if (normalized / "models").exists() and (normalized / "textures").exists():
                        return normalized

            return Path.cwd()


        BUNDLE_DIR = resolve_bundle_dir()
        MODELS_DIR = BUNDLE_DIR / "models"
        TEXTURES_DIR = BUNDLE_DIR / "textures"


        def load_image(path, *, non_color=False):
            if not path.exists():
                print(f"[bundle] Missing texture: {{path}}")
                return None
            image = bpy.data.images.load(str(path), check_existing=True)
            if non_color:
                try:
                    image.colorspace_settings.name = "Non-Color"
                except Exception:
                    pass
            return image


        def ensure_material():
            material_name = CONFIG["materialName"]
            material = bpy.data.materials.get(material_name)
            if material is None:
                material = bpy.data.materials.new(material_name)
            material.use_nodes = True

            nodes = material.node_tree.nodes
            links = material.node_tree.links
            nodes.clear()

            output = nodes.new("ShaderNodeOutputMaterial")
            output.location = (720, 0)

            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
            bsdf.location = (420, 0)
            links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

            base_color = CONFIG.get("baseColor") or [1.0, 1.0, 1.0, 1.0]
            bsdf.inputs["Base Color"].default_value = base_color
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = float(CONFIG.get("metallic", 0.0))
            if "Roughness" in bsdf.inputs:
                bsdf.inputs["Roughness"].default_value = float(CONFIG.get("roughness", 0.5))

            emission_color = CONFIG.get("emissionColor") or [0.0, 0.0, 0.0, 1.0]
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = emission_color
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = float(CONFIG.get("emissionStrength", 1.0))
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = emission_color

            maps = CONFIG.get("maps") or {{}}

            base_map = maps.get("_BaseMap")
            if base_map:
                tex = nodes.new("ShaderNodeTexImage")
                tex.label = "_BaseMap"
                tex.location = (-260, 220)
                tex.image = load_image(TEXTURES_DIR / base_map["file"])
                if tex.image:
                    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])

            normal_map = maps.get("_BumpMap")
            if normal_map:
                tex = nodes.new("ShaderNodeTexImage")
                tex.label = "_BumpMap"
                tex.location = (-620, -180)
                tex.image = load_image(TEXTURES_DIR / normal_map["file"], non_color=True)
                normal = nodes.new("ShaderNodeNormalMap")
                normal.location = (-260, -160)
                if tex.image:
                    links.new(tex.outputs["Color"], normal.inputs["Color"])
                    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])

            emission_map = maps.get("_EmissionMap")
            if emission_map:
                tex = nodes.new("ShaderNodeTexImage")
                tex.label = "_EmissionMap"
                tex.location = (-260, 0)
                tex.image = load_image(TEXTURES_DIR / emission_map["file"])
                if tex.image:
                    target_socket = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
                    links.new(tex.outputs["Color"], bsdf.inputs[target_socket])

            metallic_map = maps.get("_MetallicGlossMap")
            if metallic_map:
                tex = nodes.new("ShaderNodeTexImage")
                tex.label = "_MetallicGlossMap"
                tex.location = (-620, 420)
                tex.image = load_image(TEXTURES_DIR / metallic_map["file"], non_color=True)
                if tex.image and "Metallic" in bsdf.inputs:
                    links.new(tex.outputs["Color"], bsdf.inputs["Metallic"])
                if tex.image and "Roughness" in bsdf.inputs:
                    invert = nodes.new("ShaderNodeMath")
                    invert.location = (-260, 460)
                    invert.operation = "SUBTRACT"
                    invert.inputs[0].default_value = 1.0
                    links.new(tex.outputs["Alpha"], invert.inputs[1])
                    links.new(invert.outputs["Value"], bsdf.inputs["Roughness"])

            return material


        def import_obj(filepath):
            before = set(bpy.data.objects)
            if hasattr(bpy.ops.wm, "obj_import"):
                bpy.ops.wm.obj_import(filepath=str(filepath))
            else:
                bpy.ops.import_scene.obj(filepath=str(filepath))
            return [obj for obj in bpy.data.objects if obj not in before]


        def assign_material(objects, material):
            for obj in objects:
                if getattr(obj, "type", None) != "MESH":
                    continue
                if obj.data.materials:
                    obj.data.materials[0] = material
                else:
                    obj.data.materials.append(material)


        def choose_primary_model():
            models = list(CONFIG.get("models") or [])
            if not models:
                return None

            for model in models:
                model_name = str(model.get("file") or "").lower()
                if "_lod0." in model_name or "_lod0" in model_name:
                    return model
            return models[0]


        def main():
            material = ensure_material()
            model = choose_primary_model()
            if not model:
                print("[bundle] No model file was configured for this bundle.")
                return

            model_path = MODELS_DIR / model["file"]
            if not model_path.exists():
                print(f"[bundle] Missing model: {{model_path}}")
                return

            imported = import_obj(model_path)
            assign_material(imported, material)
            print(f"[bundle] Imported {{model_path.name}} -> {{len(imported)}} object(s)")


        if __name__ == "__main__":
            main()
        """
    ).lstrip()


def _readme_text(bundle: dict) -> str:
    textures = bundle["textures"]
    models = bundle["models"]
    return textwrap.dedent(
        f"""\
        # {bundle["label"]}

        This demo bundle was generated from `{bundle["materialRel"]}`.

        Included:
        - `{Path(bundle["materialRel"]).name}` material JSON
        - `{len(textures)}` linked texture map(s)
        - `{len(models)}` matching model file(s)
        - `import_into_blender.py` at the bundle root for a quick Blender demo

        Texture slots in this bundle:
        {chr(10).join(f"- `{item['slot']}` -> `{Path(item['rel']).name}`" for item in textures) or "- (none)"}

        Blender demo:
        1. Extract the zip anywhere.
        2. Open Blender.
        3. Open the Scripting workspace.
        4. Run `import_into_blender.py`.

        Notes:
        - The importer keeps the recovered OBJ geometry as-is and builds a best-effort Principled BSDF material.
        - The helper imports only the `lod0` mesh when one is available.
        - `_MetallicGlossMap` is treated as non-color data and its alpha is inverted into roughness when available.
        - If you prefer manual setup, the raw files are already organized into `models/`, `textures/`, and `material/`.
        """
    )


def _create_bundle_archive(bundle: dict, asset_index: dict, out_dir: Path) -> dict:
    material_rel = bundle["materialRel"]
    material_path = _resolve_export_path(material_rel, asset_index)
    if not material_path.exists():
        raise FileNotFoundError(f"Material file not found: {material_path}")

    material_payload = json.loads(material_path.read_text(encoding="utf-8"))
    lookup = _build_asset_lookup(asset_index.get("entries") or [])
    models = _pick_models_for_material(material_rel, lookup)
    textures = [item for item in _pick_textures_for_material(material_rel, material_payload, lookup) if item.get("rel")]

    bundle_dir = out_dir
    bundle_dir.mkdir(parents=True, exist_ok=True)
    zip_path = bundle_dir / f"{bundle['id']}.zip"

    material_settings = _extract_material_settings(material_payload)
    blender_config = {
        "bundleId": bundle["id"],
        "materialName": Path(material_rel).stem,
        "baseColor": material_settings["baseColor"],
        "emissionColor": material_settings["emissionColor"],
        "emissionStrength": material_settings["emissionStrength"],
        "metallic": material_settings["metallic"],
        "roughness": material_settings["roughness"],
        "models": [{"file": Path(rel).name, "rel": rel} for rel in models],
        "maps": {
            item["slot"]: {"file": Path(item["rel"]).name, "rel": item["rel"], "name": item["name"]}
            for item in textures
        },
    }

    archive_manifest = {
        "bundleId": bundle["id"],
        "label": bundle["label"],
        "description": bundle["description"],
        "materialRel": material_rel,
        "materialFile": f"material/{material_path.name}",
        "models": [{"rel": rel, "file": f"models/{Path(rel).name}"} for rel in models],
        "textures": [
            {"slot": item["slot"], "name": item["name"], "rel": item["rel"], "file": f"textures/{Path(item['rel']).name}"}
            for item in textures
        ],
        "blenderScript": "import_into_blender.py",
    }

    bundle["textures"] = textures
    bundle["models"] = models
    bundle["blenderConfig"] = blender_config

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(material_path, arcname=f"material/{material_path.name}")
        for rel in models:
            src = _resolve_export_path(rel, asset_index)
            if src.exists():
                zf.write(src, arcname=f"models/{src.name}")
        for item in textures:
            src = _resolve_export_path(item["rel"], asset_index)
            if src.exists():
                zf.write(src, arcname=f"textures/{src.name}")
        zf.writestr("bundle_manifest.json", json.dumps(archive_manifest, ensure_ascii=False, indent=2))
        zf.writestr("README.md", _readme_text(bundle))
        zf.writestr("import_into_blender.py", _blender_helper_text(bundle))

    return {
        "id": bundle["id"],
        "label": bundle["label"],
        "description": bundle["description"],
        "materialRel": material_rel,
        "download": f"data/assets/bundles/{zip_path.name}",
        "bytes": zip_path.stat().st_size,
        "fileCount": 1 + len(models) + len(textures) + 3,
        "assetRels": sorted(set([material_rel] + models + [item["rel"] for item in textures])),
        "includes": {
            "models": len(models),
            "textures": len(textures),
            "materialJson": 1,
            "blenderScript": True,
        },
    }


def build_asset_bundles(index_path: Path = ASSET_DIR / "index.json", out_dir: Path = ASSET_DIR / "bundles") -> dict:
    asset_index = _load_asset_index(index_path)
    bundles: list[dict] = []
    by_asset_rel: dict[str, list[str]] = defaultdict(list)
    errors: list[str] = []

    for config in DEMO_BUNDLES:
        bundle = {
            "id": config["id"],
            "materialRel": config["material_rel"],
            "label": config["label"],
            "description": config["description"],
        }
        try:
            built = _create_bundle_archive(bundle, asset_index, out_dir)
        except Exception as exc:  # pragma: no cover - surfaced in CLI output
            errors.append(f"{bundle['id']}: {exc}")
            continue

        bundles.append(built)
        for rel in built["assetRels"]:
            if built["id"] not in by_asset_rel[rel]:
                by_asset_rel[rel].append(built["id"])

    out_dir.mkdir(parents=True, exist_ok=True)
    index_payload = {
        "generated": asset_index.get("generated"),
        "bundles": bundles,
        "byAssetRel": {rel: ids for rel, ids in sorted(by_asset_rel.items())},
    }
    index_path_out = out_dir / "index.json"
    write_json(index_path_out, index_payload)

    print(
        "Asset bundle index written:",
        index_path_out,
        f"({len(bundles)} bundle(s); {sum(bundle['bytes'] for bundle in bundles)} bytes total)"
    )
    for error in errors:
        print("Bundle skipped:", error)

    return {
        "bundles": len(bundles),
        "bytes": sum(bundle["bytes"] for bundle in bundles),
        "errors": errors,
        "indexBytes": index_path_out.stat().st_size if index_path_out.exists() else 0,
    }
