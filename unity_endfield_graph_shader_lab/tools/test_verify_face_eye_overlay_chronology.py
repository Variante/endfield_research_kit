#!/usr/bin/env python3
"""Focused regression tests for the transparent renderer-list contract."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("verify_face_eye_overlay_chronology.py")
SPEC = importlib.util.spec_from_file_location("face_eye_overlay_chronology", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TransparentRendererListContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.forward = (
            MODULE.FRACTAL_ROOT / "ForwardPassUtils.cs"
        ).read_text(encoding="utf-8-sig", errors="replace")
        cls.renderer_lists = (
            MODULE.FRACTAL_ROOT / "HGRendererListUtils.cs"
        ).read_text(encoding="utf-8-sig", errors="replace")

    def test_installed_decompiled_queue_selector_is_complete(self) -> None:
        MODULE.require_tokens(
            self.forward,
            list(MODULE.FORWARD_TRANSPARENT_QUEUE_TOKENS),
            "test queue selector",
        )

    def test_missing_queue_branch_fails_closed(self) -> None:
        changed = self.forward.replace(
            "k_RenderQueue_AllTransparentWithLowRes", "k_RenderQueue_REMOVED"
        )
        with self.assertRaisesRegex(
            AssertionError,
            r"test queue selector: missing token 'k_RenderQueue_AllTransparentWithLowRes'",
        ):
            MODULE.require_tokens(
                changed,
                list(MODULE.FORWARD_TRANSPARENT_QUEUE_TOKENS),
                "test queue selector",
            )

    def test_installed_transparent_descriptor_preserves_fields(self) -> None:
        MODULE.require_tokens(
            self.renderer_lists,
            list(MODULE.TRANSPARENT_DESCRIPTOR_TOKENS),
            "test transparent descriptor",
        )

    def test_missing_descriptor_field_fails_closed(self) -> None:
        changed = self.renderer_lists.replace(
            "v54.sortingCriteria = 87;", "v54.sortingCriteria = 0;"
        )
        with self.assertRaisesRegex(
            AssertionError,
            r"test transparent descriptor: missing token 'v54.sortingCriteria = 87;'",
        ):
            MODULE.require_tokens(
                changed,
                ["v54.sortingCriteria = 87;"],
                "test transparent descriptor",
            )


if __name__ == "__main__":
    unittest.main()
