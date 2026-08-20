import importlib.util
import pathlib
import struct
import tempfile
import unittest
import zlib


MODULE_PATH = pathlib.Path(__file__).with_name("validate_overview_capture_sidecar.py")
SPEC = importlib.util.spec_from_file_location("overview_sidecar", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def valid_payload():
    frames = []
    for index, (phase, clip, phase_seconds, clip_time, normalized) in enumerate([
        ("start", "start", 0.0, 0.0, 0.0),
        ("start", "start", 0.1, 0.1, 0.083333),
        ("transition", "start->loop", 0.0, 0.0, 0.0),
        ("transition", "start->loop", 0.1, 0.1, 0.5),
        ("loop", "loop", 0.0, 0.0, 0.0),
        ("loop", "loop", 0.1, 0.1, 0.125),
    ]):
        frames.append({
            "index": index,
            "phase": phase,
            "clip": clip,
            "timestamp_seconds": index * 0.1,
            "phase_seconds": phase_seconds,
            "clip_time_seconds": clip_time,
            "phase_normalized": normalized,
            "alpha_audit": {
                "width": 2,
                "height": 2,
                "transparent_pixels": 2,
                "nontransparent_pixels": 2,
            },
        })
    return {
        "schema_version": 1,
        "status": "ok",
        "actor": "Endminf",
        "fps": 10,
        "matte_verified": False,
        "secondary_dynamics_verified": False,
        "secondary_dynamics_contract": "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/secondary_dynamics_owner_recovery.json",
        "render_fidelity_status": "incomplete_missing_retail_secondary_dynamics_solver",
        "transparent_clear_requested": True,
        "transparent_pipeline_override_applied": True,
        "transparent_post_process_disabled": True,
        "transition_mode": "state_weighted_crossfade_sample",
        "controller_exit_normalized_time": 0.9,
        "controller_transition_seconds": 0.2,
        "reference_backdrop_disabled": True,
        "non_actor_renderers_disabled": True,
        "non_actor_ui_disabled": True,
        "actor_props_disabled": True,
        "clips": [
            {
                "name": "start",
                "role": "ui_overview_start",
                "duration_seconds": 1.2,
                "frame_count": 2,
                "sequence_start_seconds": 0.0,
                "sequence_end_seconds": 0.2,
                "loop_cycles": 0,
            },
            {
                "name": "start->loop",
                "role": "ui_overview_transition",
                "duration_seconds": 0.2,
                "frame_count": 2,
                "sequence_start_seconds": 0.2,
                "sequence_end_seconds": 0.4,
                "loop_cycles": 0,
            },
            {
                "name": "loop",
                "role": "ui_overview_loop",
                "duration_seconds": 0.8,
                "frame_count": 2,
                "sequence_start_seconds": 0.4,
                "sequence_end_seconds": 0.6,
                "loop_cycles": 1,
            },
        ],
        "camera_contract": {
            "path": "charinfo_overview_camera_contract.json",
            "camera_position": [0.0, 1.0, 2.0],
            "look_at_position": [0.0, 1.0, 0.0],
            "serialized_vcam_rotation": [0.0, 0.0, 0.0, 1.0],
            "field_of_view": 22.0,
            "near_clip_plane": 0.01,
            "far_clip_plane": 100.0,
        },
        "frames": frames,
        "alpha_audit": {
            "matte_verified": False,
            "frame_count": len(frames),
            "frames_with_transparent_pixels": len(frames),
            "frames_with_nontransparent_pixels": len(frames),
        },
        "limitations": [
            "matteVerified=false: alpha readback is audit only",
            "secondaryDynamicsVerified=false: retail solver not reproduced",
            "The transparent pass excludes post processing.",
        ],
    }


def rgba_png(width=2, height=2):
    """Build a tiny valid RGBA PNG without a third-party image package."""
    pixels = bytes((255, 0, 0, 0, 0, 255, 0, 0, 0, 0, 255, 255, 255, 255, 255, 128))
    assert width == height == 2
    scanlines = b"\x00" + pixels[:8] + b"\x00" + pixels[8:]

    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines))
        + chunk(b"IEND", b"")
    )


def frame_verified_payload():
    payload = valid_payload()
    payload["width"] = 2
    payload["height"] = 2
    for index, frame in enumerate(payload["frames"]):
        frame["file"] = f"frame_{index:06d}.png"
        frame["alpha_audit"].update({
            "minimum_alpha": 0,
            "maximum_alpha": 255,
            "transparent_clear_observed": True,
        })
    return payload


class ValidateOverviewCaptureSidecarTests(unittest.TestCase):
    def test_valid_start_transition_then_one_loop(self):
        self.assertEqual(MODULE.validate_payload(valid_payload()), [])

    def test_matte_cannot_be_promoted_by_alpha_readback(self):
        payload = valid_payload()
        payload["matte_verified"] = True
        self.assertTrue(any("matte_verified" in error for error in MODULE.validate_payload(payload)))

    def test_secondary_dynamics_cannot_be_promoted_without_retail_solver(self):
        payload = valid_payload()
        payload["secondary_dynamics_verified"] = True
        self.assertTrue(
            any(
                "secondary_dynamics_verified" in error
                for error in MODULE.validate_payload(payload)
            )
        )

    def test_missing_loop_is_rejected(self):
        payload = valid_payload()
        payload["frames"] = payload["frames"][:4]
        payload["clips"] = payload["clips"][:2]
        payload["alpha_audit"]["frame_count"] = 4
        errors = MODULE.validate_payload(payload)
        self.assertTrue(any("clips must contain" in error or "loop phase" in error for error in errors))

    def test_all_transparent_frame_is_fail_closed(self):
        payload = valid_payload()
        payload["frames"][2]["alpha_audit"]["transparent_pixels"] = 4
        payload["frames"][2]["alpha_audit"]["nontransparent_pixels"] = 0
        errors = MODULE.validate_payload(payload)
        self.assertTrue(any("both transparent" in error for error in errors))

    def test_pixel_counts_must_cover_target(self):
        payload = valid_payload()
        payload["frames"][0]["alpha_audit"]["transparent_pixels"] = 1
        errors = MODULE.validate_payload(payload)
        self.assertTrue(any("sum to width*height" in error for error in errors))

    def test_phase_order_and_clip_time_are_strict(self):
        payload = valid_payload()
        payload["frames"][4]["phase"] = "start"
        payload["frames"][4]["clip"] = "start"
        payload["frames"][4]["clip_time_seconds"] = 9.0
        errors = MODULE.validate_payload(payload)
        self.assertTrue(any("strict start" in error for error in errors))
        self.assertTrue(any("clip_time_seconds" in error for error in errors))

    def test_verify_frames_reads_png_and_matches_sidecar(self):
        payload = frame_verified_payload()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for frame in payload["frames"]:
                (root / frame["file"]).write_bytes(rgba_png())
            self.assertEqual(
                MODULE.validate_payload(payload, frame_root=root, verify_frames=True),
                [],
            )

    def test_verify_frames_rejects_tampered_alpha_counts(self):
        payload = frame_verified_payload()
        payload["frames"][0]["alpha_audit"]["transparent_pixels"] = 1
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for frame in payload["frames"]:
                (root / frame["file"]).write_bytes(rgba_png())
            errors = MODULE._verify_frame_files(payload, root)
        self.assertTrue(any("transparent_pixels mismatch" in error for error in errors))

    def test_verify_frames_rejects_missing_extra_and_traversal(self):
        payload = frame_verified_payload()
        payload["frames"][0]["file"] = "../outside.png"
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for frame in payload["frames"][1:]:
                (root / frame["file"]).write_bytes(rgba_png())
            (root / "frame_stale.png").write_bytes(rgba_png())
            errors = MODULE._verify_frame_files(payload, root)
        self.assertTrue(any("stay under" in error for error in errors))
        self.assertTrue(any("unreferenced frame_*.png" in error for error in errors))

    def test_verify_frames_rejects_corrupt_png(self):
        payload = frame_verified_payload()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for frame in payload["frames"]:
                (root / frame["file"]).write_bytes(b"not a png")
            errors = MODULE._verify_frame_files(payload, root)
        self.assertTrue(any("PNG audit failed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
