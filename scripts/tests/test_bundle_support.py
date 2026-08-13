from __future__ import annotations

import ast
import inspect
import unittest

from scripts.story_builder import bundle_support


class BundleSupportTests(unittest.TestCase):
    def test_language_bundle_imports_the_path_loader_explicitly(self) -> None:
        from scripts.story_builder import language_bundle

        self.assertIs(language_bundle.load_json_path, bundle_support.load_json_path)

    def test_language_bundle_has_no_internal_manual_option_override_path(self) -> None:
        from scripts.story_builder import language_bundle

        tree = ast.parse(inspect.getsource(language_bundle))
        names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        }
        strings = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertNotIn("_manual_option_group_override", names)
        self.assertNotIn("_MANUAL_OPTION_OVERRIDES_PATH", names)
        self.assertNotIn("manual_option_overrides.json", strings)
        self.assertNotIn("manualOptionResponseOverride", strings)

    def test_language_selection_normalizes_and_rejects_unknown_codes(self) -> None:
        available = ["CN", "EN", "JP"]
        self.assertEqual(
            bundle_support.normalize_language_selection(["cn,en", "JP", "EN"], available),
            ["CN", "EN", "JP"],
        )
        with self.assertRaisesRegex(SystemExit, "Unknown language code"):
            bundle_support.normalize_language_selection(["XX"], available)

    def test_mission_and_misc_slots_are_domain_values(self) -> None:
        self.assertEqual(bundle_support.parse_mission("c13m2d5"), ("c", 13))
        self.assertEqual(
            bundle_support.slot_misc("dlg_c13m3_3d5"),
            ("c", 13, "c13m3", 3),
        )
        self.assertEqual(
            bundle_support.slot_misc("timeline_blackbox"),
            ("timeline", 0, "blackbox", 0),
        )

    def test_public_surface_does_not_reexport_context_or_stdlib_names(self) -> None:
        self.assertNotIn("ROOT", bundle_support.__all__)
        self.assertNotIn("json", bundle_support.__all__)
        self.assertEqual(set(bundle_support.__all__), {
            "discover_languages",
            "normalize_language_selection",
            "language_info",
            "load",
            "load_optional_table_json",
            "load_json_path",
            "load_json_path_uncached",
            "load_story_source_links",
            "parse_mission",
            "scene_sort_value",
            "slot_misc",
            "preview",
            "safe_mission_data_filename",
        })


if __name__ == "__main__":
    unittest.main()
