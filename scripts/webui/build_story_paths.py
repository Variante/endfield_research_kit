from __future__ import annotations

from pathlib import Path


def _resolve_structured_source_dir(export_root: Path, source: str) -> Path:
    return export_root / "structured" / source


def _resolve_recovered_dir(export_root: Path, parts: tuple[str, ...]) -> Path:
    return export_root.joinpath(*parts)


def _existing_unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        key = str(path).lower()
        if key in seen or not path.exists():
            continue
        seen.add(key)
        out.append(path)
    return out


def _asset_source_family(label: str) -> str:
    return str(label or "").split("-", 1)[0]


def _append_labeled_root(
    roots: list[tuple[str, Path]],
    label: str,
    path: Path,
    *,
    dedupe_path: bool = True,
) -> None:
    if not path.exists():
        return

    path_key = str(path.resolve()).lower()
    for existing_label, existing_path in roots:
        if existing_label == label:
            return
        if dedupe_path and str(existing_path.resolve()).lower() == path_key:
            return
    roots.append((label, path))


def _resolve_asset_source_dir(export_root: Path, source: str) -> Path:
    recovered_convert = export_root / "recovered" / "AnimeStudio-cli" / source / "convert_by_type"
    structured = export_root / "structured" / source
    if recovered_convert.exists():
        return recovered_convert
    return structured


def _resolve_material_source_dir(export_root: Path, source: str) -> Path:
    recovered_json = export_root / "recovered" / "AnimeStudio-cli" / source / "json_by_type"
    if (recovered_json / "Material").exists():
        return recovered_json

    recovered_convert = export_root / "recovered" / "AnimeStudio-cli" / source / "convert_by_type"
    if (recovered_convert / "Material").exists():
        return recovered_convert

    return _resolve_asset_source_dir(export_root, source)


def resolve_asset_source_roots(export_root: Path) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []

    for source in ("StreamingAssets", "Persistent"):
        primary_root = _resolve_asset_source_dir(export_root, source)
        _append_labeled_root(roots, source, primary_root)

        recovered_root = export_root / "recovered" / "AnimeStudio-cli" / source
        _append_labeled_root(roots, f"{source}-maps", recovered_root / "maps")

        structured_root = export_root / "structured" / source
        if structured_root.exists() and str(structured_root.resolve()).lower() != str(primary_root.resolve()).lower():
            _append_labeled_root(roots, f"{source}-structured", structured_root)

    for extra_root in ("inventory", "raw_vfs", "unresolved"):
        _append_labeled_root(roots, extra_root, export_root / extra_root)

    return roots


def resolve_material_source_roots(export_root: Path) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    for source in ("StreamingAssets", "Persistent"):
        _append_labeled_root(
            roots,
            f"{source}-materials",
            _resolve_material_source_dir(export_root, source),
            dedupe_path=False,
        )
    return roots
