"""Sprites as crops of exported textures (``endfield.sprite-crop.v1``).

A Unity Sprite draws a rectangle of a Texture2D. The export therefore keeps
the texture once (``game/Unity/Texture2D/<file>.png``) and each Sprite as a
crop document: one ``Sprite`` row of ``game/Unity.sqlite`` named
``<name>_p<PathID>.json``. AnimeStudio writes it (``Exporter.ExportSprite``)
from the same code that used to render the Sprite PNG, so applying it to the
exported texture reproduces that PNG pixel for pixel:

1. with ``scale``, resize the texture to ``scale.width`` x ``scale.height``;
2. cut ``crop`` (x, y, width, height) out of the top-down texture image;
3. apply ``transform``: ``none``, ``flipX``, ``flipY``, ``rotate180``,
   ``rotateCW90`` or ``rotateCCW90`` (the result is ``width`` x ``height``);
4. set every pixel listed in ``clear`` (outside a Tight mesh) to transparent
   black;
5. set every fully transparent pixel listed in ``zero`` to transparent black
   (the area AnimeStudio's mask fill passes over; only invisible color changes).

``clear`` and ``zero`` are rows ``[y, x0, length0, x1, length1, ...]`` of the
result. ``texture`` names the exported file and its identity (serialized file,
PathID, size); ``unity`` keeps the Sprite's own fields (rect, pivot, border,
packing settings) as evidence.

AnimeStudio's Sprite image is a pure function of its texture (resolved from
the Sprite's render data or its SpriteAtlas render-data entry), and it derives
``transform`` and both run lists by running its own shaping code over probe
images, so the document reproduces the former PNG by construction. Evidence:
every Sprite of the current build rendered from its document matched
AnimeStudio's image pixel for pixel, hidden color included, and matched every
previously published Sprite PNG; the service worker and this module's
renderer produce the same pixels, and ``export.bat debug`` repeats the check
each build (``--sprite-images``). The current build has no downscaled, rotated
or atlas-packed Sprite; the document and both renderers still carry those
cases, and the exporter's texture check counts each.

The texture join is the PPtr AnimeStudio resolves, carried as the texture's
exported file name (``_p<PathID>``) plus CAB, PathID and size, and checked
against the published texture after every Sprite publish. Name matching is not
identity: many Sprite names have several same-named textures, and sliced
sheets (``cs_loading_icon_<n>``) name only the sheet.

The Sprite image keeps its logical path ``game/Unity/Sprite/<name>_p<PathID>.png``:
the asset index lists it, pages link to it, ``serve.py`` answers it with the
crop document and the WebUI's service worker (``webui/sprite_worker.js``)
renders it from the texture. An export run with ``--sprite-images`` also keeps
AnimeStudio's own rendering of every Sprite in ``game/Sprite.sqlite``; serve.py
prefers that image when it is present.

    python -m scripts.game_data.sprite_crops check
    python -m scripts.game_data.sprite_crops show "icon_plusmark_*"
    python -m scripts.game_data.sprite_crops render "icon_plusmark_*" --out tmp\\study\\sprites
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

if __package__ in {None, ""}:
    raise SystemExit("Run as: python -m scripts.game_data.sprite_crops")

from scripts.game_data.unity_store import UnityObjectStore, UnityStoreError, open_store_if_present
from scripts.source_paths import ExportLayout

SPRITE_TYPE = "Sprite"
TEXTURE_TYPE = "Texture2D"
CROP_SCHEMA = "endfield.sprite-crop.v1"
CROP_DOCUMENT_SUFFIX = ".json"
IMAGE_SUFFIX = ".png"
#: AnimeStudio's own Sprite images, kept only by an export run with --sprite-images.
IMAGE_STORE_FILE = "Sprite.sqlite"
IMAGE_STORE_SCHEMA = "endfield.sprite-image-store.v1"
#: The store meta row where AnimeStudio records its crop-versus-image check.
IMAGE_CHECK_META_KEY = "spriteCheck"
TRANSFORMS = ("none", "flipX", "flipY", "rotate180", "rotateCW90", "rotateCCW90")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class SpriteCropError(ValueError):
    """A crop document that is not this schema, or a texture it cannot be applied to."""


@dataclass(frozen=True)
class SpriteCrop:
    #: The crop document's row name, ``<name>_p<PathID>.json``.
    document: str
    object_name: str
    source_file: str
    path_id: int | None
    texture_file: str
    texture_source_file: str
    texture_path_id: int | None
    texture_width: int
    texture_height: int
    scale: tuple[int, int] | None
    crop: tuple[int, int, int, int]
    transform: str
    width: int
    height: int
    clear: tuple[tuple[int, ...], ...]
    zero: tuple[tuple[int, ...], ...]

    @property
    def image_name(self) -> str:
        """The Sprite image's file name, ``<name>_p<PathID>.png``."""
        return image_name(self.document)

    @property
    def image_ref(self) -> str:
        """The image's path below ``game/``: ``Unity/Sprite/<name>_p<PathID>.png``."""
        return f"Unity/{SPRITE_TYPE}/{self.image_name}"

    @property
    def texture_ref(self) -> str:
        """The texture's path below ``game/``: ``Unity/Texture2D/<file>``."""
        return f"Unity/{TEXTURE_TYPE}/{self.texture_file}"

    @property
    def is_whole_texture(self) -> bool:
        """True when the Sprite is its texture unchanged: the same pixels, the same image."""
        return (
            self.scale is None
            and self.crop == (0, 0, self.texture_width, self.texture_height)
            and self.transform == "none"
            and not self.clear
            and not self.zero
        )

    def geometry_key(self) -> str:
        """Everything but the texture that decides the pixels, as one canonical string."""
        return json.dumps(
            [self.scale, self.crop, self.transform, self.clear, self.zero],
            separators=(",", ":"),
        )


def image_name(document: str) -> str:
    """``x_p<ID>.json`` -> ``x_p<ID>.png``."""
    if not document.lower().endswith(CROP_DOCUMENT_SUFFIX):
        raise SpriteCropError(f"not a Sprite crop document name: {document!r}")
    return document[: -len(CROP_DOCUMENT_SUFFIX)] + IMAGE_SUFFIX


def document_name(image: str) -> str:
    """``x_p<ID>.png`` -> ``x_p<ID>.json``."""
    if not image.lower().endswith(IMAGE_SUFFIX):
        raise SpriteCropError(f"not a Sprite image name: {image!r}")
    return image[: -len(IMAGE_SUFFIX)] + CROP_DOCUMENT_SUFFIX


def _int(payload: dict[str, Any], key: str, where: str, *, minimum: int = 0) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SpriteCropError(f"{where}: {key} must be an integer >= {minimum}, got {value!r}")
    return value


def _runs(value: Any, key: str, where: str, width: int, height: int) -> tuple[tuple[int, ...], ...]:
    if not isinstance(value, list):
        raise SpriteCropError(f"{where}: {key} must be a list of rows")
    rows: list[tuple[int, ...]] = []
    for row in value:
        if (
            not isinstance(row, list)
            or len(row) < 3
            or len(row) % 2 == 0
            or any(isinstance(item, bool) or not isinstance(item, int) for item in row)
        ):
            raise SpriteCropError(f"{where}: {key} row {row!r} is not [y, x0, length0, ...]")
        y = row[0]
        if not 0 <= y < height:
            raise SpriteCropError(f"{where}: {key} row y={y} is outside the {height}-row image")
        for x, length in zip(row[1::2], row[2::2]):
            if x < 0 or length <= 0 or x + length > width:
                raise SpriteCropError(f"{where}: {key} run ({x}, {length}) on row {y} is outside the {width}-pixel row")
        rows.append(tuple(row))
    return tuple(rows)


def parse_sprite_crop(document: str, payload: Any) -> SpriteCrop:
    """Validate one crop document; raises SpriteCropError naming the first problem."""
    where = f"{SPRITE_TYPE}/{document}"
    if not isinstance(payload, dict) or payload.get("schema") != CROP_SCHEMA:
        found = payload.get("schema") if isinstance(payload, dict) else type(payload).__name__
        raise SpriteCropError(f"{where}: schema {found!r}, expected {CROP_SCHEMA!r}")
    texture = payload.get("texture")
    if not isinstance(texture, dict) or not isinstance(texture.get("file"), str) or not texture["file"]:
        raise SpriteCropError(f"{where}: texture.file is missing")
    texture_width = _int(texture, "width", f"{where} texture", minimum=1)
    texture_height = _int(texture, "height", f"{where} texture", minimum=1)
    scale = None
    if payload.get("scale") is not None:
        scale_payload = payload["scale"]
        if not isinstance(scale_payload, dict):
            raise SpriteCropError(f"{where}: scale must be an object")
        scale = (_int(scale_payload, "width", f"{where} scale", minimum=1), _int(scale_payload, "height", f"{where} scale", minimum=1))
    crop_payload = payload.get("crop")
    if not isinstance(crop_payload, dict):
        raise SpriteCropError(f"{where}: crop is missing")
    crop = (
        _int(crop_payload, "x", f"{where} crop"),
        _int(crop_payload, "y", f"{where} crop"),
        _int(crop_payload, "width", f"{where} crop", minimum=1),
        _int(crop_payload, "height", f"{where} crop", minimum=1),
    )
    source_width, source_height = scale or (texture_width, texture_height)
    if crop[0] + crop[2] > source_width or crop[1] + crop[3] > source_height:
        raise SpriteCropError(f"{where}: crop {crop} leaves the {source_width}x{source_height} texture")
    transform = payload.get("transform")
    if transform not in TRANSFORMS:
        raise SpriteCropError(f"{where}: transform {transform!r} is not one of {', '.join(TRANSFORMS)}")
    width = _int(payload, "width", where, minimum=1)
    height = _int(payload, "height", where, minimum=1)
    expected = (crop[3], crop[2]) if transform in ("rotateCW90", "rotateCCW90") else (crop[2], crop[3])
    if (width, height) != expected:
        raise SpriteCropError(f"{where}: size {width}x{height} does not follow from crop {crop} and {transform}")
    header = payload.get("$animestudio") if isinstance(payload.get("$animestudio"), dict) else {}
    return SpriteCrop(
        document=document,
        object_name=str(header.get("name") or ""),
        source_file=str(header.get("sourceFile") or ""),
        path_id=header.get("pathId") if isinstance(header.get("pathId"), int) else None,
        texture_file=texture["file"],
        texture_source_file=str(texture.get("sourceFile") or ""),
        texture_path_id=texture.get("pathId") if isinstance(texture.get("pathId"), int) else None,
        texture_width=texture_width,
        texture_height=texture_height,
        scale=scale,
        crop=crop,
        transform=transform,
        width=width,
        height=height,
        clear=_runs(payload.get("clear", []), "clear", where, width, height),
        zero=_runs(payload.get("zero", []), "zero", where, width, height),
    )


def iter_sprite_crops(store: UnityObjectStore, pattern: str | None = None) -> Iterator[SpriteCrop]:
    """Every Sprite crop document of a store, by name; an invalid one raises."""
    for row, payload in store.iter_json(SPRITE_TYPE, pattern or f"*{CROP_DOCUMENT_SUFFIX}"):
        yield parse_sprite_crop(row.name, payload)


def read_sprite_crop(store: UnityObjectStore, image: str) -> SpriteCrop | None:
    """The crop behind one Sprite image name, or None when the store has none."""
    name = document_name(image)
    try:
        payload = store.read_json(SPRITE_TYPE, name)
    except KeyError:
        return None
    return parse_sprite_crop(name, payload)


def png_size(path: Path) -> tuple[int, int] | None:
    """A PNG's (width, height) from its IHDR, or None when the file is not a PNG."""
    try:
        with path.open("rb") as handle:
            head = handle.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != _PNG_SIGNATURE or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def check_sprite_textures(export_root: Path, *, limit: int = 50) -> dict[str, Any]:
    """Whether every Sprite crop names an exported texture of the size it records.

    The texture's file name carries its PathID and the IHDR must show the
    recorded size, so a crop is never applied to an unrelated image. Returns
    counts and the first ``limit`` problems (``document``, ``texture``,
    ``problem``); ``ok`` is true only when there is none.
    """
    layout = ExportLayout(export_root)
    store = open_store_if_present(layout.root)
    report: dict[str, Any] = {"checked": 0, "problemCount": 0, "problems": [], "scaled": 0, "transformed": 0}
    if store is None:
        report["ok"] = True
        return report
    texture_dir = layout.unity_type_dir(TEXTURE_TYPE)
    sizes: dict[str, tuple[int, int] | None] = {}

    def problem(document: str, texture: str, text: str) -> None:
        report["problemCount"] += 1
        if len(report["problems"]) < limit:
            report["problems"].append({"document": document, "texture": texture, "problem": text})

    for row, payload in store.iter_json(SPRITE_TYPE, f"*{CROP_DOCUMENT_SUFFIX}"):
        report["checked"] += 1
        try:
            crop = parse_sprite_crop(row.name, payload)
        except SpriteCropError as exc:
            problem(row.name, "", str(exc))
            continue
        report["scaled"] += crop.scale is not None
        report["transformed"] += crop.transform != "none"
        key = crop.texture_file.casefold()
        if key not in sizes:
            sizes[key] = png_size(texture_dir / crop.texture_file)
        size = sizes[key]
        if size is None:
            problem(row.name, crop.texture_ref, "texture file is missing or not a PNG")
        elif size != (crop.texture_width, crop.texture_height):
            problem(row.name, crop.texture_ref, f"texture is {size[0]}x{size[1]}, the crop records {crop.texture_width}x{crop.texture_height}")
    report["ok"] = report["problemCount"] == 0
    return report


# ---------------------------------------------------------------------------
# Rendering (stdlib PNG, for tools that need real files)
# ---------------------------------------------------------------------------


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    distance_left, distance_up, distance_up_left = abs(estimate - left), abs(estimate - up), abs(estimate - up_left)
    if distance_left <= distance_up and distance_left <= distance_up_left:
        return left
    return up if distance_up <= distance_up_left else up_left


def decode_png_rgba(data: bytes) -> tuple[int, int, bytearray]:
    """(width, height, RGBA bytes) of an 8-bit, non-interlaced PNG."""
    if data[:8] != _PNG_SIGNATURE:
        raise SpriteCropError("not a PNG")
    position = 8
    idat = bytearray()
    palette = b""
    transparency = b""
    width = height = depth = color = interlace = None
    while position + 8 <= len(data):
        (length,) = struct.unpack(">I", data[position:position + 4])
        kind = data[position + 4:position + 8]
        body = data[position + 8:position + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color, _compression, _filter, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            palette = body
        elif kind == b"tRNS":
            transparency = body
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        position += 12 + length
    if width is None or depth != 8 or interlace != 0 or color not in (0, 2, 3, 4, 6):
        raise SpriteCropError(f"unsupported PNG (depth {depth}, color type {color}, interlace {interlace})")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    pixels = bytearray(width * height * 4)
    previous = bytearray(stride)
    offset = 0
    for y in range(height):
        kind = raw[offset]
        line = bytearray(raw[offset + 1:offset + 1 + stride])
        offset += 1 + stride
        if kind == 1:
            for x in range(channels, stride):
                line[x] = (line[x] + line[x - channels]) & 255
        elif kind == 2:
            for x in range(stride):
                line[x] = (line[x] + previous[x]) & 255
        elif kind == 3:
            for x in range(stride):
                left = line[x - channels] if x >= channels else 0
                line[x] = (line[x] + ((left + previous[x]) >> 1)) & 255
        elif kind == 4:
            for x in range(stride):
                left = line[x - channels] if x >= channels else 0
                up_left = previous[x - channels] if x >= channels else 0
                line[x] = (line[x] + _paeth(left, previous[x], up_left)) & 255
        elif kind != 0:
            raise SpriteCropError(f"unsupported PNG filter {kind}")
        base = y * width * 4
        if color == 6:
            pixels[base:base + width * 4] = line
        else:
            for x in range(width):
                if color == 2:
                    r, g, b = line[x * 3:x * 3 + 3]
                    a = 255
                elif color == 0:
                    r = g = b = line[x]
                    a = 255
                elif color == 4:
                    r = g = b = line[x * 2]
                    a = line[x * 2 + 1]
                else:
                    index = line[x]
                    r, g, b = palette[index * 3:index * 3 + 3]
                    a = transparency[index] if index < len(transparency) else 255
                pixels[base + x * 4:base + x * 4 + 4] = bytes((r, g, b, a))
        previous = line
    return width, height, pixels


def encode_png_rgba(width: int, height: int, pixels: bytes | bytearray) -> bytes:
    """An 8-bit RGBA PNG of ``pixels`` (unfiltered rows, zlib level 6)."""
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    stride = width * 4
    raw = b"".join(b"\x00" + bytes(pixels[y * stride:(y + 1) * stride]) for y in range(height))
    return (
        _PNG_SIGNATURE
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def apply_crop(crop: SpriteCrop, texture_width: int, texture_height: int, texture: bytes | bytearray) -> bytearray:
    """The Sprite's RGBA pixels from its texture's top-down RGBA pixels."""
    if crop.scale is not None:
        raise SpriteCropError(f"{crop.document}: a scaled Sprite needs AnimeStudio's resampler; open its game/Sprite.sqlite image")
    if (texture_width, texture_height) != (crop.texture_width, crop.texture_height):
        raise SpriteCropError(
            f"{crop.document}: texture is {texture_width}x{texture_height}, the crop records {crop.texture_width}x{crop.texture_height}"
        )
    x0, y0, cut_width, cut_height = crop.crop

    def source(u: int, v: int) -> tuple[int, int]:
        if crop.transform == "flipX":
            return cut_width - 1 - u, v
        if crop.transform == "flipY":
            return u, cut_height - 1 - v
        if crop.transform == "rotate180":
            return cut_width - 1 - u, cut_height - 1 - v
        if crop.transform == "rotateCW90":
            return v, cut_height - 1 - u
        if crop.transform == "rotateCCW90":
            return cut_width - 1 - v, u
        return u, v

    out = bytearray(crop.width * crop.height * 4)
    if crop.transform == "none":
        for v in range(cut_height):
            start = ((y0 + v) * texture_width + x0) * 4
            out[v * cut_width * 4:(v + 1) * cut_width * 4] = texture[start:start + cut_width * 4]
    else:
        for v in range(crop.height):
            for u in range(crop.width):
                sx, sy = source(u, v)
                start = ((y0 + sy) * texture_width + x0 + sx) * 4
                out[(v * crop.width + u) * 4:(v * crop.width + u) * 4 + 4] = texture[start:start + 4]
    for row in crop.clear:
        y = row[0]
        for x, length in zip(row[1::2], row[2::2]):
            start = (y * crop.width + x) * 4
            out[start:start + length * 4] = bytes(length * 4)
    for row in crop.zero:
        y = row[0]
        for x, length in zip(row[1::2], row[2::2]):
            for pixel in range(y * crop.width + x, y * crop.width + x + length):
                if out[pixel * 4 + 3] == 0:
                    out[pixel * 4:pixel * 4 + 4] = b"\x00\x00\x00\x00"
    return out


def render_sprite_png(crop: SpriteCrop, texture_png: bytes) -> bytes:
    """The Sprite as PNG bytes, rendered from its exported texture's PNG bytes."""
    width, height, pixels = decode_png_rgba(texture_png)
    return encode_png_rgba(crop.width, crop.height, apply_crop(crop, width, height, pixels))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect, check and render the export's Sprite crop documents.")
    parser.add_argument("--export-root", type=Path, default=None, help="Default: the configured export root.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Check that every crop names an exported texture of its recorded size.")
    show = sub.add_parser("show", help="Print the crops whose document name matches a glob.")
    show.add_argument("pattern")
    render = sub.add_parser("render", help="Write the Sprite PNGs whose document name matches a glob.")
    render.add_argument("pattern")
    render.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    layout = ExportLayout(args.export_root) if args.export_root is not None else ExportLayout.configured()
    try:
        if args.command == "check":
            report = check_sprite_textures(layout.root)
            print(json.dumps(report, indent=2))
            return 0 if report["ok"] else 1
        store = open_store_if_present(layout.root)
        if store is None:
            print(f"sprite_crops: no Unity store under {layout.root}", file=sys.stderr)
            return 2
        pattern = args.pattern if args.pattern.lower().endswith(CROP_DOCUMENT_SUFFIX) else args.pattern + CROP_DOCUMENT_SUFFIX
        written = 0
        for crop in iter_sprite_crops(store, pattern):
            if args.command == "show":
                print(f"{crop.image_ref}\t{crop.texture_ref}\tcrop={crop.crop}\t{crop.transform}\t"
                      f"{crop.width}x{crop.height}\tclear={len(crop.clear)} rows\tzero={len(crop.zero)} rows")
                continue
            texture = layout.unity_type_dir(TEXTURE_TYPE) / crop.texture_file
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / crop.image_name).write_bytes(render_sprite_png(crop, texture.read_bytes()))
            written += 1
        if args.command == "render":
            print(f"wrote {written} Sprite PNG(s) under {args.out}")
    except (UnityStoreError, SpriteCropError, OSError) as exc:
        print(f"sprite_crops: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
