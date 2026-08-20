import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("validate_overview_capture_sidecar.py")
SPEC = importlib.util.spec_from_file_location("overview_sidecar", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def valid_payload():
    return {
        "schema_version": 1,
        "status": "ok",
        "actor": "Endminf",
        "fps": 10,
        "matte_verified": False,
        "transparent_clear_requested": True,
        "reference_backdrop_disabled": True,
        "non_actor_renderers_disabled": True,
        "non_actor_ui_disabled": True,
        "actor_props_disabled": True,
        "clips": [
            {
                "role": "ui_overview_start",
                "duration_seconds": 1.2,
                "frame_count": 13,
                "loop_cycles": 0,
            },
            {
                "role": "ui_overview_loop",
                "duration_seconds": 0.8,
                "frame_count": 8,
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
        "frames": [
            {
                "index": 0,
                "phase": "start",
                "timestamp_seconds": 0.0,
                "phase_seconds": 0.0,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 4, "nontransparent_pixels": 0},
            },
            {
                "index": 1,
                "phase": "start",
                "timestamp_seconds": 0.1,
                "phase_seconds": 0.1,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
            {
                "index": 2,
                "phase": "loop",
                "timestamp_seconds": 1.2,
                "phase_seconds": 0.0,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
            {
                "index": 3,
                "phase": "loop",
                "timestamp_seconds": 1.3,
                "phase_seconds": 0.1,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
            {
                "index": 4,
                "phase": "loop",
                "timestamp_seconds": 1.4,
                "phase_seconds": 0.2,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
            {
                "index": 5,
                "phase": "loop",
                "timestamp_seconds": 1.5,
                "phase_seconds": 0.3,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
            {
                "index": 6,
                "phase": "loop",
                "timestamp_seconds": 1.6,
                "phase_seconds": 0.4,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
            {
                "index": 7,
                "phase": "loop",
                "timestamp_seconds": 1.7,
                "phase_seconds": 0.5,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
            {
                "index": 8,
                "phase": "loop",
                "timestamp_seconds": 1.8,
                "phase_seconds": 0.6,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
            {
                "index": 9,
                "phase": "loop",
                "timestamp_seconds": 1.9,
                "phase_seconds": 0.7,
                "alpha_audit": {"width": 2, "height": 2, "transparent_pixels": 2, "nontransparent_pixels": 2},
            },
        ],
        "alpha_audit": {"matte_verified": False, "frame_count": 10},
        "limitations": ["matteVerified=false: alpha readback is audit only"],
    }


class ValidateOverviewCaptureSidecarTests(unittest.TestCase):
    def test_valid_start_then_one_loop(self):
        self.assertEqual(MODULE.validate_payload(valid_payload()), [])

    def test_matte_cannot_be_promoted_by_alpha_readback(self):
        payload = valid_payload()
        payload["matte_verified"] = True
        self.assertTrue(any("matte_verified" in error for error in MODULE.validate_payload(payload)))

    def test_missing_loop_is_rejected(self):
        payload = valid_payload()
        payload["frames"] = payload["frames"][:2]
        payload["alpha_audit"]["frame_count"] = 2
        errors = MODULE.validate_payload(payload)
        self.assertTrue(any("loop phase" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
