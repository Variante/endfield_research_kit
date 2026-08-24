#!/usr/bin/env python3
"""Verify current original-data evidence for the Character Info Overview route."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from audit_ui_controller_recovery import build_audit  # noqa: E402


EVIDENCE_PATH = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "OriginalData"
    / "CharInfoPresentation"
    / "overview_animator_native_recovery.json"
)
PLAYBACK_PATH = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Animation"
    / "EndfieldOverviewPlayback.cs"
)
SETUP_PATH = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Editor"
    / "CharacterRecovery"
    / "EndfieldManifestCharacterSetup.cs"
)
PLAYABLE_ROOT = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Playable"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PeImage:
    def __init__(self, path: Path):
        self.path = path
        self.data = path.read_bytes()
        pe_offset = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe_offset : pe_offset + 4] != b"PE\0\0":
            raise AssertionError(f"not a PE image: {path}")
        coff = pe_offset + 4
        section_count = struct.unpack_from("<H", self.data, coff + 2)[0]
        optional_size = struct.unpack_from("<H", self.data, coff + 16)[0]
        optional = coff + 20
        self.image_base = struct.unpack_from("<Q", self.data, optional + 24)[0]
        section_offset = optional + optional_size
        self.sections: list[tuple[int, int, int]] = []
        for index in range(section_count):
            offset = section_offset + index * 40
            virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
                "<IIII", self.data, offset + 8
            )
            self.sections.append(
                (virtual_address, max(virtual_size, raw_size), raw_pointer)
            )

    def bytes_at_rva(self, rva: int, count: int) -> bytes:
        for start, size, raw_pointer in self.sections:
            if start <= rva < start + size:
                file_offset = raw_pointer + rva - start
                return self.data[file_offset : file_offset + count]
        raise AssertionError(f"RVA outside PE sections: 0x{rva:x}")


def controller_shape(source_json: str) -> tuple[int, int, int]:
    document = json.loads(Path(source_json).read_text(encoding="utf-8"))
    controller = document["m_Controller"]
    machines = controller["m_StateMachineArray"]
    assert len(machines) == 1
    states = machines[0]["data"]["m_StateConstantArray"]
    state_transitions = sum(
        len(state["data"].get("m_TransitionConstantArray") or [])
        for state in states
    )
    return len(controller["m_LayerArray"]), len(states), state_transitions


def main() -> int:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    build = evidence["source_build"]
    game_assembly = Path(build["game_assembly"]["path"])
    metadata = Path(build["global_metadata"]["path"])
    for path, expected in (
        (game_assembly, build["game_assembly"]),
        (metadata, build["global_metadata"]),
    ):
        assert path.is_file(), path
        assert path.stat().st_size == int(expected["bytes"]), path
        assert sha256(path) == str(expected["sha256"]).lower(), path

    pe = PeImage(game_assembly)
    assert pe.image_base == 0x180000000
    methods = evidence["method_bodies"]
    assert len(methods) == 8
    assert len({int(item["method_index"]) for item in methods}) == 8
    for method in methods:
        data = pe.bytes_at_rva(int(method["rva"], 16), int(method["bytes"]))
        assert hashlib.sha256(data).hexdigest() == method["sha256"], method

    # These byte-level gates pin the semantic branches that the evidence uses,
    # in addition to the full bounded-method hashes above.
    by_index = {int(item["method_index"]): item for item in methods}
    play_hash = pe.bytes_at_rva(int(by_index[49720]["rva"], 16), 436)
    assert play_hash[0x72:0x79] == bytes.fromhex("48 8b 8f c8 00 00 00")
    assert play_hash[0xBE:0xC4] == bytes.fromhex("48 83 64 24 20 00")
    assert play_hash[0x130:0x136] == bytes.fromhex("48 83 64 24 20 00")
    visibility = pe.bytes_at_rva(int(by_index[49755]["rva"], 16), 240)
    assert visibility[0x4A:0x52] == bytes.fromhex("f3 0f 10 35 6a db d2 04")
    assert visibility[0x8B:0x94] == bytes.fromhex("0f 2f f0 48 8b ce 0f 97 c2")
    constant_rva = 0xB95929C
    threshold = struct.unpack("<f", pe.bytes_at_rva(constant_rva, 4))[0]
    assert abs(threshold - float(evidence["native_semantics"]["deco_visibility_threshold"])) < 1e-8

    audit = build_audit()
    serialized = evidence["serialized_controller_semantics"]
    assert audit["actor_count"] == int(serialized["actor_count"]) == 31
    assert audit["main_overview_exact_count"] == 31
    assert audit["fixed_duration_overview_handoff_count"] == int(
        serialized["fixed_duration_overview_handoffs"]
    )
    assert audit["normalized_duration_overview_handoff_count"] == int(
        serialized["normalized_duration_overview_handoffs"]
    )
    assert audit["controller_proven_widget_state_count"] == int(
        serialized["controller_proven_body_widget_state_compositions"]
    )
    expected_conditions = serialized["overview_entry_conditions_each"]
    fixed_counts: Counter[bool] = Counter()
    for actor in audit["actors"]:
        overview = actor["main_overview"]
        assert overview["entry_transition_conditions"] == expected_conditions, actor
        assert overview["interruption_source"] == int(
            serialized["interruption_source_each"]
        )
        assert overview["ordered_interruption"] is bool(
            serialized["ordered_interruption_each"]
        )
        assert overview["blend_root_motion"] is bool(
            serialized["blend_root_motion_each"]
        )
        assert controller_shape(overview["source_json"]) == (
            int(serialized["layer_count_each"]),
            int(serialized["state_count_each"]),
            int(serialized["state_transition_count_each"]),
        )
        fixed_counts[bool(overview["transition_duration_fixed"])] += 1
    assert fixed_counts == Counter({False: 27, True: 4})

    playback_source = PLAYBACK_PATH.read_text(encoding="utf-8")
    setup_source = SETUP_PATH.read_text(encoding="utf-8")
    for token in (
        "EndfieldOverviewTransitionCondition",
        "orderedInterruption",
        "blendRootMotion",
        "entryTransitionConditions",
    ):
        assert token in playback_source, token
        assert token in setup_source, token

    for token in (
        "private void OnAnimatorMove()",
        "animatorSource.deltaRotation",
        "transform.rotation = transform.rotation * deltaRotation",
        "RootMotionPositionDelta",
    ):
        assert token in playback_source, token
    assert "animatorSource.deltaPosition" not in playback_source

    prefab_paths = sorted(PLAYABLE_ROOT.glob("*/Prefabs/*.prefab"))
    assert len(prefab_paths) == int(serialized["actor_count"]), len(prefab_paths)
    for prefab_path in prefab_paths:
        prefab_source = prefab_path.read_text(encoding="utf-8")
        for token in (
            "  orderedInterruption: 1",
            "  blendRootMotion: 1",
            "  entryTransitionConditions:",
            "    parameter: FromIndex",
            "    parameter: ToIndex",
            "    parameter: EnableSwitch",
        ):
            assert token in prefab_source, (prefab_path, token)

    print(
        "verified Overview native recovery: "
        f"methods={len(methods)} actors={audit['actor_count']} "
        f"fixed={fixed_counts[True]} normalized={fixed_counts[False]} "
        f"widgetStates={audit['controller_proven_widget_state_count']} "
        f"prefabs={len(prefab_paths)} "
        f"visibilityThreshold={threshold:.9g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
