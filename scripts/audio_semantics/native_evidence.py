"""Build-locked native evidence used by Audio semantic recovery.

The contracts in this module describe one installed client build.  Callers
must construct :class:`NativeAudioEvidence` from the exact metadata and
GameAssembly paths supplied by their build context before publishing any of
the mappings below.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from pathlib import Path
from typing import Any

if __package__ == "scripts.audio_semantics":
    from ..common import check_installed_native_inputs, native_evidence_required
elif __package__ == "audio_semantics":
    from common import check_installed_native_inputs, native_evidence_required
else:  # pragma: no cover - package modules are not direct-file entry points.
    raise ImportError("import as scripts.audio_semantics or audio_semantics")


EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
NATIVE_VOICE_TRIGGER_MAPPING_ID = (
    "gameassembly-2026-08-13-native-voice-response-trigger-callsites"
)
ANIMATION_VOICE_TRIGGER_MAPPING_ID = (
    "gameassembly-2026-08-13-animator-mono-trigger-voice"
)
MODEL_VIEW_STATE_AUDIO_MAPPING_ID = (
    "gameassembly-2026-08-20-model-view-state-normal-audio-event"
)
MODEL_VIEW_POSITIONED_AUDIO_MAPPING_ID = (
    "gameassembly-2026-08-20-model-view-positioned-audio-branches"
)

# This is a deliberately small, build-locked route contract.  The body
# hashes are part of the proof: a method index/address pair from a different
# client build must not be enough to publish a runtime route.  The route is
# only exposed after ``validate_native_audio_evidence`` has accepted the
# explicitly selected metadata and GameAssembly files.
MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE = {
    "nativeMappingId": MODEL_VIEW_STATE_AUDIO_MAPPING_ID,
    "consumer": {
        "type": "Beyond.Gameplay.Core.ModelViewStateController.AudioBehavior",
        "method": "Execute",
        "methodIndex": 81734,
        "token": "0x06013f47",
        "virtualAddress": "0x183281ff0",
        "bodySha256": "e0d2892930a50b5c6dbcfe27773654395631aad9a224efbf4b38bea43f88e2c8",
    },
    "directCalls": [
        {
            "targetType": "Beyond.Gameplay.Audio.AudioManager",
            "targetMethod": "PostEvent",
            "targetMethodIndex": 38956,
            "targetToken": "0x0600982d",
            "targetVirtualAddress": "0x1832811c0",
            "targetBodySha256": "7508b9f39689da91934e581b07e3b5e0bd4601bbbb3d2b6fb0f8e12cce68e958",
            "relation": "AudioBehavior.Execute direct call target",
        },
        {
            "targetType": "Beyond.Gameplay.Core.ModelViewStateController",
            "targetMethod": "RegisterAudioBehaviorHandler",
            "targetMethodIndex": 82021,
            "targetToken": "0x06014066",
            "targetVirtualAddress": "0x183281150",
            "targetBodySha256": "3be609894156661bb9c6726b4a25090d765bf61605c17679467ce62031204552",
            "relation": "AudioBehavior.Execute direct call target",
        },
    ],
    "evidence": (
        "exactCurrentBuildMethodMappingBodyHashesAndDirectCallTargets"
    ),
}

# This is intentionally a separate contract from the normal ModelView route.
# The Execute body has three mutually exclusive tag-0x0002 branches.  Only
# ``isDirectlyPlay`` reaches PlaySoundAtPosition with a normalAudioId Event;
# the other two branches are state controls and never become Event/media rows.
# Offsets are serialized in code so a changed data layout or native branch
# fails closed instead of silently promoting a control to playback.
MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE = {
    "nativeMappingId": MODEL_VIEW_POSITIONED_AUDIO_MAPPING_ID,
    "consumer": {
        "type": "Beyond.Gameplay.Core.ModelViewStateController.AudioPositionBehavior",
        "method": "Execute",
        "methodIndex": 81745,
        "token": "0x06013f52",
        "virtualAddress": "0x1870c7c3c",
        "bodyLength": 0x231,
        "bodySha256": "38d194cb51256a6e30c40f21c8996dd59c626b9f3d1a6bd58933251619a12e7e",
    },
    "fieldContract": {
        "dataPointerOffset": "0x18",
        "isCustomOffset": "0x28",
        "isDirectlyPlayOffset": "0x29",
        "normalAudioIdOffset": "0x38",
        "entityStateModelLevel": 1,
        "guards": {
            "customStateSwitch": "!isDirectlyPlay && isCustom",
            "entityStateSwitch": "!isDirectlyPlay && !isCustom",
            "directPositionEvent": "isDirectlyPlay",
        },
    },
    "directCalls": [
        {
            "offset": "0xac", "targetType": "Beyond.Gameplay.Actions.GameAction",
            "targetMethod": "TrySwitchAudioState", "targetMethodIndex": 32652,
            "targetToken": "0x06007f8d", "targetVirtualAddress": "0x184cd7ca0",
        },
        {
            "offset": "0xe8", "targetType": "Beyond.Gameplay.Actions.GameAction",
            "targetMethod": "TrySwitchAudioCustomState", "targetMethodIndex": 32651,
            "targetToken": "0x06007f8c", "targetVirtualAddress": "0x1875efc70",
        },
        {
            "offset": "0x152", "targetType": "Beyond.Gameplay.Core.Entity",
            "targetMethod": "TryGetGameObject", "targetVirtualAddress": "0x1832828f0",
        },
        {
            "offset": "0x16d", "targetType": "Beyond.Gameplay.Core.Entity",
            "targetMethod": "get_AudioId", "targetVirtualAddress": "0x183197ad0",
        },
        {
            "offset": "0x195", "targetType": "Beyond.Gameplay.Core.Entity",
            "targetMethod": "get_AudioId", "targetVirtualAddress": "0x183197ad0",
        },
        {
            "offset": "0x1a8", "targetType": "UnityEngine.Component",
            "targetMethod": "get_transform", "targetVirtualAddress": "0x183273070",
        },
        {
            "offset": "0x1bd", "targetType": "UnityEngine.Transform",
            "targetMethod": "get_position", "targetVirtualAddress": "0x183276380",
        },
        {
            "offset": "0x1f5", "targetType": "Beyond.Gameplay.Audio.AudioManager",
            "targetMethod": "PlaySoundAtPosition", "targetMethodIndex": 38869,
            "targetToken": "0x060097d6", "targetVirtualAddress": "0x183b87c60",
        },
    ],
    "endpointAudits": [
        {
            "targetMethod": "TrySwitchAudioState", "targetVirtualAddress": "0x184cd7ca0",
            "bodyLength": 0xa3,
            "bodySha256": "23ef278f4182d97f1f936149ed8b9b43b0b22ee50d831633a892181ac793f86d",
            "calls": [{"offset": "0x8c", "targetVirtualAddress": "0x183c2b050"}],
        },
        {
            "targetMethod": "TrySwitchAudioCustomState", "targetVirtualAddress": "0x1875efc70",
            "bodyLength": 0xbd,
            "bodySha256": "89c253f0f2889fad05712fedfda0f64447da28f5e412490d906d1a15c461d2bc",
        },
        {
            "targetType": "Beyond.Gameplay.Core.InteractiveAudioComponent",
            "targetMethod": "SwitchAudioState", "targetMethodIndex": 67202,
            "targetToken": "0x06010683", "targetVirtualAddress": "0x183c2b050",
            "bodyLength": 79,
            "bodySha256": "f9276c4986f27904b06697de2ef6e59c0aa4904f352bf7f1232fb344bbf0e71f",
            "calls": [{"offset": "0x3a", "targetVirtualAddress": "0x183c2b3e0"}],
        },
        {
            "targetType": "Beyond.Gameplay.Core.InteractiveAudioComponent",
            "targetMethod": "_SwitchState", "targetVirtualAddress": "0x183c2b3e0",
            "bodyLength": 71,
            "bodySha256": "245a0544e65e32dad9f0dc0a2205c0e20a5c472a40bbee0292a836f800a40361",
        },
        {
            "targetType": "Beyond.Gameplay.Audio.AudioManager",
            "targetMethod": "PlaySoundAtPosition", "targetMethodIndex": 38869,
            "targetToken": "0x060097d6", "targetVirtualAddress": "0x183b87c60",
            "bodyLength": 0x69,
            "bodySha256": "a64e5b83b1f680ab697a13ec2ed21eea0e161a477d5ee7e86ac1d9887e28fea4",
            "calls": [
                {"offset": "0x3b", "targetVirtualAddress": "0x18319b840"},
                {"offset": "0x47", "targetVirtualAddress": "0x183b896b0"},
                {"offset": "0x59", "targetVirtualAddress": "0x183b89730"},
            ],
        },
    ],
    "branchBoundary": {
        "directPositionEvent": "PlaySoundAtPosition target verified; Wwise/media selection and execution unobserved",
        "customStateSwitch": "TrySwitchAudioCustomState target/body verified; control only, no Event ownership",
        "entityStateSwitch": "TrySwitchAudioState -> InteractiveAudioComponent.SwitchAudioState -> _SwitchState verified; control only, no final Wwise/PostEvent claim",
    },
    "evidence": "exactCurrentBuildExecuteBodyFieldsGuardsAndNarrowEndpointAudits",
}


@dataclass(frozen=True)
class NativeAudioEvidence:
    """Validation result for the native facts owned by this module."""

    metadata_path: Path | None
    gameassembly_path: Path | None
    status: str
    metadata_sha256: str = ""
    gameassembly_sha256: str = ""
    reason: str = ""
    # ``False`` is retained for directly constructed synthetic contexts used
    # by unit tests.  Only validate_native_audio_evidence sets this after the
    # explicit GameAssembly + metadata gate has measured the supplied files.
    gate_verified: bool = False

    @property
    def validated(self) -> bool:
        return self.status == "validated"

    def unavailable_contract(self, native_mapping_id: str) -> dict[str, Any]:
        """Return a diagnostic without publishing unvalidated native facts."""

        return {
            "nativeMappingId": native_mapping_id,
            "status": self.status,
            "reason": self.reason,
            "expectedMetadataSha256": EXPECTED_METADATA_SHA256,
            "actualMetadataSha256": self.metadata_sha256 or None,
            "expectedGameAssemblySha256": EXPECTED_GAMEASSEMBLY_SHA256,
            "actualGameAssemblySha256": self.gameassembly_sha256 or None,
        }


def model_view_state_audio_native_route(
    native_context: NativeAudioEvidence,
    *,
    observed_route: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return the exact ModelView normal-audio route when its gate is valid.

    ``observed_route`` is an optional synthetic byte-audit result used by
    focused tests.  Production callers audit the explicitly selected PE
    automatically; every method mapping, body hash, and direct call target
    must match the pinned route.  Missing, mismatched, or drifted inputs
    return no route, never a partially trusted one.
    """

    audit = audit_model_view_state_audio_native_route(
        native_context,
        observed_route=observed_route,
    )
    if audit["status"] != "validated":
        if native_evidence_required():
            raise RuntimeError(
                "Audio native evidence required but ModelView route is unavailable: "
                + str(audit["reason"])
            )
        return None
    return audit["route"]


def model_view_positioned_audio_native_route(
    native_context: NativeAudioEvidence,
    *,
    observed_route: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return the build-locked tag-0x0002 branch route, or no route.

    Controls may still be published as authored control evidence when this
    route is unavailable.  The route itself is never partially trusted.
    """

    audit = audit_model_view_positioned_audio_native_route(
        native_context,
        observed_route=observed_route,
    )
    if audit["status"] != "validated":
        if native_evidence_required():
            raise RuntimeError(
                "Audio native evidence required but positioned ModelView route is unavailable: "
                + str(audit["reason"])
            )
        return None
    return audit["route"]


_MODEL_VIEW_EXECUTE_METHOD = (81734, "0x06013f47", "0x183281ff0")
_MODEL_VIEW_DIRECT_CALLS = (
    (38956, "0x0600982d", "0x1832811c0"),
    (82021, "0x06014066", "0x183281150"),
)
_PE_BODY_SCAN_LIMIT = 0x10000


def _bounded_reason(*parts: str) -> str:
    """Make native-audit diagnostics deterministic and bounded."""

    return "; ".join(str(part).replace("\n", " ")[:240] for part in parts if part)[:1000]


def _catalog_row_errors(route: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(route, dict):
        return ["route catalog is not an object"]
    if route.get("nativeMappingId") != MODEL_VIEW_STATE_AUDIO_MAPPING_ID:
        errors.append("nativeMappingId catalog drift")
    consumer = route.get("consumer")
    if not isinstance(consumer, dict):
        errors.append("consumer catalog row missing")
    else:
        values = (
            ("type", consumer.get("type"), "Beyond.Gameplay.Core.ModelViewStateController.AudioBehavior"),
            ("method", consumer.get("method"), "Execute"),
            ("methodIndex", consumer.get("methodIndex"), _MODEL_VIEW_EXECUTE_METHOD[0]),
            ("token", consumer.get("token"), _MODEL_VIEW_EXECUTE_METHOD[1]),
            ("virtualAddress", consumer.get("virtualAddress"), _MODEL_VIEW_EXECUTE_METHOD[2]),
        )
        errors.extend(
            f"consumer {name} expected {expected} got {actual}"
            for name, actual, expected in values
            if actual != expected
        )
        if not isinstance(consumer.get("bodySha256"), str):
            errors.append("consumer bodySha256 catalog row missing")
    calls = route.get("directCalls")
    if not isinstance(calls, list) or len(calls) != len(_MODEL_VIEW_DIRECT_CALLS):
        errors.append("directCalls catalog row count drift")
    else:
        for index, (row, expected) in enumerate(zip(calls, _MODEL_VIEW_DIRECT_CALLS)):
            if not isinstance(row, dict):
                errors.append(f"directCalls[{index}] catalog row missing")
                continue
            for name, actual, expected_value in (
                ("targetType", row.get("targetType"), (
                    "Beyond.Gameplay.Audio.AudioManager"
                    if index == 0
                    else "Beyond.Gameplay.Core.ModelViewStateController"
                )),
                ("targetMethod", row.get("targetMethod"), (
                    "PostEvent" if index == 0 else "RegisterAudioBehaviorHandler"
                )),
                ("targetMethodIndex", row.get("targetMethodIndex"), expected[0]),
                ("targetToken", row.get("targetToken"), expected[1]),
                ("targetVirtualAddress", row.get("targetVirtualAddress"), expected[2]),
            ):
                if actual != expected_value:
                    errors.append(
                        f"directCalls[{index}] {name} expected {expected_value} got {actual}"
                    )
            if not isinstance(row.get("targetBodySha256"), str):
                errors.append(f"directCalls[{index}] targetBodySha256 catalog row missing")
    return errors[:8]


def _pe_file_bounds_for_va(data: bytes, virtual_address: int) -> tuple[int, int]:
    """Map an x64 PE VA (or RVA) to a bounded raw-file offset."""

    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("GameAssembly.dll is not a DOS PE")
    nt_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if nt_offset < 0 or nt_offset + 24 > len(data) or data[nt_offset:nt_offset + 4] != b"PE\0\0":
        raise ValueError("GameAssembly.dll PE header is invalid")
    coff = nt_offset + 4
    section_count = struct.unpack_from("<H", data, coff + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff + 16)[0]
    optional = coff + 20
    if optional + optional_size > len(data) or optional_size < 64:
        raise ValueError("GameAssembly.dll optional PE header is truncated")
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, optional + 24)[0]
    elif magic == 0x10B:
        image_base = struct.unpack_from("<I", data, optional + 28)[0]
    else:
        raise ValueError(f"unsupported PE optional-header magic 0x{magic:x}")
    rva = virtual_address - image_base if virtual_address >= image_base else virtual_address
    section_table = optional + optional_size
    for index in range(section_count):
        section = section_table + index * 40
        if section + 40 > len(data):
            break
        virtual_size, section_rva, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, section + 8
        )
        span = max(virtual_size, raw_size)
        if section_rva <= rva < section_rva + span:
            file_offset = raw_offset + (rva - section_rva)
            if file_offset >= len(data):
                break
            raw_end = min(len(data), raw_offset + raw_size)
            if file_offset < raw_end:
                return file_offset, raw_end
    raise ValueError(f"VA 0x{virtual_address:x} has no PE section mapping")


def _pe_file_offset_for_va(data: bytes, virtual_address: int) -> int:
    """Return only the raw offset for callers that do not need section bounds."""

    return _pe_file_bounds_for_va(data, virtual_address)[0]


def _read_pe_method_body(
    gameassembly_path: Path,
    virtual_address: str | int,
    expected_sha256: str,
) -> bytes:
    """Read the bounded method body whose digest is in the route catalog.

    Method sizes are intentionally not guessed from a disassembler.  The
    expected digest identifies the exact prefix, while the PE mapper keeps
    the search inside the owning section and at most 64 KiB.
    """

    data = Path(gameassembly_path).read_bytes()
    va = int(virtual_address, 0) if isinstance(virtual_address, str) else int(virtual_address)
    offset, section_end = _pe_file_bounds_for_va(data, va)
    available = data[offset:min(section_end, offset + _PE_BODY_SCAN_LIMIT)]
    expected = str(expected_sha256 or "").casefold()
    if len(expected) != 64:
        raise ValueError(f"invalid body SHA256 catalog value for VA 0x{va:x}")
    # Hash every bounded prefix.  This is deliberately small (three methods)
    # and supports minimal PE fixtures as well as methods with multiple RETs.
    digest = hashlib.sha256()
    for length, byte in enumerate(available, 1):
        digest.update(bytes((byte,)))
        if digest.hexdigest() == expected:
            return available[:length]
    raise ValueError(f"body SHA256 drift at VA 0x{va:x}")


def _direct_call_targets(body: bytes, method_va: int) -> set[int]:
    targets: set[int] = set()
    for index in range(max(0, len(body) - 4)):
        if body[index] != 0xE8:
            continue
        displacement = struct.unpack_from("<i", body, index + 1)[0]
        targets.add(method_va + index + 5 + displacement)
    return targets


def _direct_call_sites(body: bytes, method_va: int) -> dict[int, int]:
    """Return relative E8 offsets and targets for exact callsite contracts."""

    targets: dict[int, int] = {}
    for index in range(max(0, len(body) - 4)):
        if body[index] != 0xE8:
            continue
        displacement = struct.unpack_from("<i", body, index + 1)[0]
        targets[index] = method_va + index + 5 + displacement
    return targets


def _positioned_catalog_errors(route: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(route, dict):
        return ["positioned route catalog is not an object"]
    if route.get("nativeMappingId") != MODEL_VIEW_POSITIONED_AUDIO_MAPPING_ID:
        errors.append("positioned nativeMappingId catalog drift")
    consumer = route.get("consumer")
    expected_consumer = MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE["consumer"]
    if not isinstance(consumer, dict):
        errors.append("positioned consumer catalog row missing")
    else:
        for name in ("type", "method", "methodIndex", "token", "virtualAddress", "bodyLength"):
            if consumer.get(name) != expected_consumer.get(name):
                errors.append(
                    f"positioned consumer {name} expected {expected_consumer.get(name)} got {consumer.get(name)}"
                )
        if not isinstance(consumer.get("bodySha256"), str):
            errors.append("positioned consumer bodySha256 catalog row missing")
    expected_calls = MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE["directCalls"]
    calls = route.get("directCalls")
    if not isinstance(calls, list) or len(calls) != len(expected_calls):
        errors.append("positioned directCalls catalog row count drift")
    else:
        for index, (actual, expected) in enumerate(zip(calls, expected_calls)):
            if not isinstance(actual, dict):
                errors.append(f"positioned directCalls[{index}] catalog row missing")
                continue
            for name in ("offset", "targetMethod", "targetVirtualAddress"):
                if actual.get(name) != expected.get(name):
                    errors.append(
                        f"positioned directCalls[{index}] {name} expected {expected.get(name)} got {actual.get(name)}"
                    )
    endpoints = route.get("endpointAudits")
    if not isinstance(endpoints, list) or len(endpoints) != len(
        MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE["endpointAudits"]
    ):
        errors.append("positioned endpointAudits catalog row count drift")
    return errors[:8]


def _audit_positioned_endpoint(
    data_path: Path,
    endpoint: dict[str, Any],
) -> tuple[bytes, dict[int, int]]:
    body = _read_pe_method_body(
        data_path,
        endpoint["targetVirtualAddress"],
        endpoint["bodySha256"],
    )
    expected_length = int(endpoint["bodyLength"])
    if len(body) != expected_length:
        raise ValueError(
            f"{endpoint.get('targetMethod')} body length drift: "
            f"expected 0x{expected_length:x} got 0x{len(body):x}"
        )
    method_va = int(endpoint["targetVirtualAddress"], 0)
    sites = _direct_call_sites(body, method_va)
    for call in endpoint.get("calls") or ():
        offset = int(call["offset"], 0)
        target = int(call["targetVirtualAddress"], 0)
        if sites.get(offset) != target:
            actual = sites.get(offset)
            raise ValueError(
                f"{endpoint.get('targetMethod')} E8 drift at +0x{offset:x}: "
                f"expected 0x{target:x} got {('0x%x' % actual) if actual is not None else 'missing'}"
            )
    return body, sites


def audit_model_view_positioned_audio_native_route(
    native_context: NativeAudioEvidence,
    *,
    observed_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audit the exact tag-0x0002 consumer and narrow endpoint chain."""

    if not native_context.validated:
        return {"status": native_context.status, "reason": native_context.reason[:1000], "route": None}
    if (
        native_context.metadata_sha256.casefold() != EXPECTED_METADATA_SHA256
        or native_context.gameassembly_sha256.casefold() != EXPECTED_GAMEASSEMBLY_SHA256
    ):
        return {"status": "mismatched", "reason": "native input fingerprint mismatch", "route": None}
    expected = MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE
    catalog_errors = _positioned_catalog_errors(
        expected if observed_route is None else observed_route
    )
    if observed_route is not None:
        if observed_route != expected:
            catalog_errors.append("synthetic observed positioned route differs from catalog")
        if catalog_errors:
            return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
        return {
            "status": "validated",
            "reason": "synthetic positioned route catalog validated",
            "route": _route_with_fingerprints(native_context, expected),
        }
    if not native_context.gate_verified:
        if catalog_errors:
            return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
        return {
            "status": "validated",
            "reason": "synthetic positioned route catalog validated",
            "route": _route_with_fingerprints(native_context, expected),
        }
    gameassembly = native_context.gameassembly_path
    if gameassembly is None or not gameassembly.is_file():
        return {"status": "missing", "reason": "GameAssembly.dll missing for positioned route body audit", "route": None}
    if catalog_errors:
        return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
    consumer = expected["consumer"]
    try:
        consumer_body = _read_pe_method_body(
            gameassembly, consumer["virtualAddress"], consumer["bodySha256"]
        )
        if len(consumer_body) != int(consumer["bodyLength"]):
            raise ValueError("positioned Execute body length drift")
        consumer_sites = _direct_call_sites(consumer_body, int(consumer["virtualAddress"], 0))
        expected_sites = {
            int(row["offset"], 0): int(row["targetVirtualAddress"], 0)
            for row in expected["directCalls"]
        }
        for offset, target in expected_sites.items():
            if consumer_sites.get(offset) != target:
                actual = consumer_sites.get(offset)
                raise ValueError(
                    f"positioned Execute E8 drift at +0x{offset:x}: expected "
                    f"0x{target:x} got {('0x%x' % actual) if actual is not None else 'missing'}"
                )
        endpoint_results = []
        for endpoint in expected["endpointAudits"]:
            _audit_positioned_endpoint(gameassembly, endpoint)
            endpoint_results.append(str(endpoint.get("targetMethod") or "unknown"))
    except (OSError, ValueError, struct.error) as exc:
        return {
            "status": "mismatched",
            "reason": _bounded_reason("positioned native body/call audit failed", str(exc)),
            "route": None,
        }
    return {
        "status": "validated",
        "reason": "exact positioned catalog, body SHA256, and E8 calls validated",
        "route": _route_with_fingerprints(native_context, expected),
        "checks": {
            "catalog": "validated",
            "consumerBodySha256": "validated",
            "consumerDirectCalls": "validated",
            "endpointBodiesAndCalls": "validated",
        },
    }


def audit_model_view_state_audio_native_route(
    native_context: NativeAudioEvidence,
    *,
    observed_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audit the production ModelView route and return a bounded diagnostic."""

    if not native_context.validated:
        return {"status": native_context.status, "reason": native_context.reason[:1000], "route": None}
    if (
        native_context.metadata_sha256.casefold() != EXPECTED_METADATA_SHA256
        or native_context.gameassembly_sha256.casefold() != EXPECTED_GAMEASSEMBLY_SHA256
    ):
        return {"status": "mismatched", "reason": "native input fingerprint mismatch", "route": None}
    expected = MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE
    catalog_errors = _catalog_row_errors(expected)
    if observed_route is not None:
        if observed_route != expected:
            catalog_errors.append("synthetic observed route differs from catalog")
        if catalog_errors:
            return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
        return {"status": "validated", "reason": "synthetic observed route validated", "route": _route_with_fingerprints(native_context, expected)}
    # Directly constructed NativeAudioEvidence is the existing synthetic test
    # contract.  The production builder always receives gate_verified=True.
    if not native_context.gate_verified:
        if catalog_errors:
            return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
        return {"status": "validated", "reason": "synthetic route catalog validated", "route": _route_with_fingerprints(native_context, expected)}
    if native_context.gameassembly_path is None or not native_context.gameassembly_path.is_file():
        return {"status": "missing", "reason": "GameAssembly.dll missing for production route body audit", "route": None}
    if catalog_errors:
        return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
    consumer = expected["consumer"]
    bodies: list[tuple[int, bytes, str]] = []
    try:
        bodies.append((int(consumer["virtualAddress"], 0), _read_pe_method_body(
            native_context.gameassembly_path, consumer["virtualAddress"], consumer["bodySha256"]
        ), "consumer"))
        for row in expected["directCalls"]:
            bodies.append((int(row["targetVirtualAddress"], 0), _read_pe_method_body(
                native_context.gameassembly_path, row["targetVirtualAddress"], row["targetBodySha256"]
            ), str(row["targetMethod"])))
    except (OSError, ValueError, struct.error) as exc:
        return {"status": "mismatched", "reason": _bounded_reason("native body audit failed", str(exc)), "route": None}
    actual_targets = _direct_call_targets(bodies[0][1], bodies[0][0])
    expected_targets = {
        int(row["targetVirtualAddress"], 0) for row in expected["directCalls"]
    }
    missing_targets = sorted(expected_targets - actual_targets)
    if missing_targets:
        text = ", ".join(f"0x{value:x}" for value in missing_targets[:4])
        return {"status": "mismatched", "reason": _bounded_reason("Execute direct-call target drift", f"missing {text}"), "route": None}
    return {
        "status": "validated",
        "reason": "exact catalog, body SHA256, and Execute direct calls validated",
        "route": _route_with_fingerprints(native_context, expected),
        "checks": {
            "catalog": "validated",
            "bodySha256": "validated",
            "executeDirectCalls": "validated",
        },
    }


def _route_with_fingerprints(
    native_context: NativeAudioEvidence,
    expected: dict[str, Any],
) -> dict[str, Any]:
    route = {
        **expected,
        "metadataSha256": native_context.metadata_sha256,
        "gameAssemblySha256": native_context.gameassembly_sha256,
    }
    route["consumer"] = dict(expected["consumer"])
    route["directCalls"] = [dict(row) for row in expected["directCalls"]]
    return route


def validate_native_audio_evidence(
    metadata_path: Path | None,
    gameassembly_path: Path | None,
) -> NativeAudioEvidence:
    """Validate the two exact installed inputs once for every native consumer."""

    missing = [
        label
        for label, path in (
            ("global-metadata.dat", metadata_path),
            ("GameAssembly.dll", gameassembly_path),
        )
        if path is None or not path.is_file()
    ]
    if missing:
        result = NativeAudioEvidence(
            metadata_path,
            gameassembly_path,
            "missing",
            reason="missing native input(s): " + ", ".join(missing),
        )
        if native_evidence_required():
            raise RuntimeError(
                "Audio native evidence required but unavailable: " + result.reason
            )
        return result

    assert metadata_path is not None and gameassembly_path is not None
    result = check_installed_native_inputs(
        EXPECTED_GAMEASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly_path,
        metadata=metadata_path,
    )
    result = NativeAudioEvidence(
        result.metadata,
        result.gameassembly,
        result.status,
        result.metadata_sha256,
        result.gameassembly_sha256,
        result.detail,
        True,
    )
    if not result.validated and native_evidence_required():
        raise RuntimeError(
            "Audio native evidence required but not validated: "
            f"{result.status}: {result.reason}"
        )
    return result


ANIMATION_VOICE_TRIGGER_NATIVE = {
    "consumerType": "Beyond.Gameplay.Core.AnimatorMono",
    "consumerMethod": "TriggerVoice(AnimationEvent) / TriggerVoice(string,int,float)",
    "methodIndex": 53421,
    "methodVa": "0x186c9c8a8",
    "additionalMethodIndex": 53422,
    "additionalMethodVa": "0x183abf9f0",
    "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
    "playbackCallMethodIndex": 40534,
    "playbackCallVa": "0x183abfb10",
    "playbackInvocationVa": "0x186c9c9b2",
    "additionalPlaybackInvocationVa": "0x183abfacc",
}

AI_BARK_NATIVE_RUNTIME = {
    "nativeMappingId": "gameassembly-2026-08-13-ai-bark-table-runtime",
    "metadataSha256": EXPECTED_METADATA_SHA256,
    "gameAssemblySha256": EXPECTED_GAMEASSEMBLY_SHA256,
    "barkSystemMethod": "Beyond.Gameplay.AI.BarkSystem.Bark",
    "barkSystemMethodIndex": 45313,
    "barkSystemMethodVa": "0x1841957b0",
    "postActionMethod": "Beyond.Gameplay.Actions.GameAction.PostAIBarkEvent",
    "postActionMethodIndex": 32673,
    "postActionInvocationVa": "0x184195889",
    "managerPostMethod": "Beyond.Gameplay.AIBarkManager.PostAIBarkEvent",
    "managerPostMethodIndex": 6883,
    "managerPostMethodVa": "0x184194720",
    "managerDispatchMethod": "Beyond.Gameplay.AIBarkManager._DoPostAIBarkVoiceEvent",
    "managerDispatchMethodIndex": 6881,
    "managerDispatchMethodVa": "0x184197400",
    "voicePostMethod": "Beyond.Gameplay.Audio.VoiceManager.PostAIBarkVoiceEvent",
    "voicePostMethodIndex": 40531,
    "voicePostMethodVa": "0x184197cc0",
    "voicePostInvocationVa": "0x184197735",
    "voiceBarkEntryMethod": "Beyond.Gameplay.Audio.VoiceBarkProcessor.AIBark",
    "voiceBarkEntryMethodIndex": 40233,
    "voiceBarkEntryMethodVa": "0x186aef414",
}

ENEMY_TRIGGER_VOICE_ACTION_NATIVE = {
    "nativeMappingId": "gameassembly-2026-08-13-enemy-trigger-voice-action",
    "metadataSha256": EXPECTED_METADATA_SHA256,
    "gameAssemblySha256": EXPECTED_GAMEASSEMBLY_SHA256,
    "consumerType": "Beyond.Gameplay.AI.Action.EnemyTriggerVoiceAction",
    "consumerMethod": "OnExecute",
    "methodIndex": 46749,
    "methodVa": "0x186bc67f0",
    "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
    "playbackCallMethodIndex": 40534,
    "playbackCallVa": "0x183abfb10",
    "playbackInvocationVa": "0x186bc695e",
    "mappingConstructorMethod": ".cctor",
    "mappingConstructorMethodIndex": 46751,
    "mappingConstructorMethodVa": "0x186bc69b0",
    "voiceTypes": [
        {"voiceType": 0, "triggerKey": "combat_alarm", "literalLoadVa": "0x186bc6a64", "mappingAddInvocationVa": "0x186bc6a6e"},
        {"voiceType": 1, "triggerKey": "combat_intobattle", "literalLoadVa": "0x186bc6a7f", "mappingAddInvocationVa": "0x186bc6a89"},
        {"voiceType": 2, "triggerKey": "combat_fighting", "literalLoadVa": "0x186bc6a9a", "mappingAddInvocationVa": "0x186bc6aa4"},
        {"voiceType": 3, "triggerKey": "combat_outbattle_flee", "literalLoadVa": "0x186bc6ab5", "mappingAddInvocationVa": "0x186bc6abf"},
        {"voiceType": 4, "triggerKey": "combat_kill", "literalLoadVa": "0x186bc6ad0", "mappingAddInvocationVa": "0x186bc6ada"},
    ],
    "evidenceBoundary": (
        "The current binary exactly maps EnemyTriggerVoiceAction voiceType values 0-4 "
        "to five trigger keys and passes the selected key to ResponseOnEntity. Action "
        "instance ownership and live execution remain unobserved; common_attack and "
        "common_escape are not members of this dictionary."
    ),
}

NATIVE_VOICE_TRIGGER_ROWS = {
    "combat_dead": {
        "consumerType": "Beyond.Gameplay.Audio.VoiceTempSpeakerProcessor",
        "consumerMethod": "ResponseDeath", "methodIndex": 40440,
        "methodVa": "0x183abdf70", "literalLoadVa": "0x183abe172",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceResponseProcessor.Response",
        "playbackCallVa": "0x183abfbc0", "playbackInvocationVa": "0x183abe18f",
        "triggerRole": "temporarySpeakerDeathResponse",
        "targetBinding": "temporarySpeakerEntityAndSpeakerType",
    },
    "explocomm_switch": {
        "consumerType": "Beyond.Gameplay.Core.AbilitySystem",
        "consumerMethod": "SwitchCenterBySkill / _PlayFxWhenSwitchKeepSkill",
        "methodIndex": 54302, "methodVa": "0x186cb060c",
        "additionalMethodIndex": 54304, "additionalMethodVa": "0x186cb4ca8",
        "literalLoadVa": "0x186cb1f64", "additionalLiteralLoadVa": "0x186cb4d5d",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186cb1f6b",
        "additionalPlaybackInvocationVa": "0x186cb4d64",
        "triggerRole": "centerCharacterSkillSwitchResponse",
        "targetBinding": "selectedCenterCharacterEntity",
    },
    "combat_hurt_heavy": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnPhysicalInflictionApplied",
        "methodIndex": 59749, "methodVa": "0x186d75f38",
        "literalLoadVa": "0x186d75fa6",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186d75fb3",
        "triggerRole": "physicalInflictionHeavyHurtResponse",
        "targetBinding": "physicallyInflictedEntity",
    },
    "combat_hurt_lowhp": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnHurt",
        "methodIndex": 59747, "methodVa": "0x1846fcf50",
        "literalLoadVa": "0x1846fd0a0",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x1846fd0ad",
        "triggerRole": "lowHpThresholdCrossingResponse",
        "targetBinding": "hurtEntity",
    },
    "combat_hurt_break": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnPoiseBroken",
        "methodIndex": 59750, "methodVa": "0x186d75ff0",
        "literalLoadVa": "0x186d7605e",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186d7606b",
        "triggerRole": "poiseBrokenResponse",
        "targetBinding": "poiseBrokenEntity",
    },
    "combat_hurt_interrupt": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnWeaknessTriggered",
        "methodIndex": 59751, "methodVa": "0x186d76160",
        "literalLoadVa": "0x186d761ce",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186d761db",
        "triggerRole": "weaknessTriggeredInterruptResponse",
        "targetBinding": "weaknessTriggeredEntity",
    },
    "combat_hurt_stun": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnStunned",
        "methodIndex": 59748, "methodVa": "0x186d760a8",
        "literalLoadVa": "0x186d76116",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186d76123",
        "triggerRole": "stunnedResponse",
        "targetBinding": "stunnedEntity",
    },
    "combat_alarm_yell": {
        "consumerType": "Beyond.Gameplay.AI.EnemyBattleGraph",
        "consumerMethod": "OnEnter",
        "methodIndex": 43420, "methodVa": "0x184134080",
        "literalLoadVa": "0x184135c7e",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x183abfb10", "playbackInvocationVa": "0x184135c88",
        "triggerRole": "enemyBattleGraphEntryAlarmYellResponse",
        "targetBinding": "enemyBattleGraphOwnerEntity",
    },
    "defence_running": {
        "consumerType": "Beyond.Gameplay.AI.EnemySinglePatrolBehavior+PatrolWalkState",
        "consumerMethod": "OnUpdate / _TryPlayTowerWalkAudio",
        "methodIndex": 43146, "methodVa": "0x184649080",
        "additionalMethodIndex": 43161, "additionalMethodVa": "0x186b46a7c",
        "literalLoadVa": "0x18464a5a7", "additionalLiteralLoadVa": "0x186b46b6c",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x183abfb10", "playbackInvocationVa": "0x18464a5c0",
        "additionalPlaybackInvocationVa": "0x186b46b7d",
        "triggerRole": "enemyPatrolTowerRunningResponse",
        "targetBinding": "patrollingEnemyEntity",
    },
    "defence_reachcore": {
        "consumerType": "Beyond.Gameplay.AI.EnemySettlementBattleBehavior+EnemyCastSkillState",
        "consumerMethod": "OnUpdate",
        "methodIndex": 43000, "methodVa": "0x186b3d158",
        "literalLoadVa": "0x186b3d4aa",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x183abfb10", "playbackInvocationVa": "0x186b3d4b4",
        "triggerRole": "enemySettlementCastSkillReachCoreResponse",
        "targetBinding": "settlementEnemyEntity",
    },
    "combat_outbattle_flee": {
        "consumerType": "Beyond.Gameplay.AI.EnemyLeaveBattleBehavior",
        "consumerMethod": "OnEnter",
        "methodIndex": 42873, "methodVa": "0x186b3d7c0",
        "literalLoadVa": "0x186b3d9bf",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x183abfb10", "playbackInvocationVa": "0x186b3d9d8",
        "triggerRole": "enemyLeaveBattleFleeResponse",
        "targetBinding": "leavingBattleEnemyEntity",
    },
}


__all__ = [
    "AI_BARK_NATIVE_RUNTIME",
    "ANIMATION_VOICE_TRIGGER_MAPPING_ID",
    "ANIMATION_VOICE_TRIGGER_NATIVE",
    "ENEMY_TRIGGER_VOICE_ACTION_NATIVE",
    "EXPECTED_GAMEASSEMBLY_SHA256",
    "EXPECTED_METADATA_SHA256",
    "MODEL_VIEW_POSITIONED_AUDIO_MAPPING_ID",
    "MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE",
    "MODEL_VIEW_STATE_AUDIO_MAPPING_ID",
    "MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE",
    "NATIVE_VOICE_TRIGGER_MAPPING_ID",
    "NATIVE_VOICE_TRIGGER_ROWS",
    "NativeAudioEvidence",
    "audit_model_view_state_audio_native_route",
    "audit_model_view_positioned_audio_native_route",
    "model_view_positioned_audio_native_route",
    "model_view_state_audio_native_route",
    "validate_native_audio_evidence",
]
