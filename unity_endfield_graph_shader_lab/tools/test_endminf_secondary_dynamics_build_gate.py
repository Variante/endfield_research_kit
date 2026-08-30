from __future__ import annotations

import unittest
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
SETUP = (
    LAB / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldManifestCharacterSetup.cs"
)


class EndminfSecondaryDynamicsBuildGateTests(unittest.TestCase):
    def test_canonical_all_character_build_verifies_generated_binding(self) -> None:
        source = SETUP.read_text(encoding="utf-8")
        start = source.index("public static void BuildAllCharacterModelViewer()")
        end = source.index("[MenuItem(", start + 1)
        body = source[start:end]
        build = body.index("BuildCharacterViewer(")
        verify = body.index(
            "EndfieldSecondaryDynamicsBindingBuilder."
            "VerifyGeneratedEndminfBinding();"
        )
        complete_log = body.index("All-character model viewer complete")
        self.assertLess(build, verify)
        self.assertLess(verify, complete_log)

    def test_builder_and_runtime_captured_replay_defaults_are_off(self) -> None:
        builder = (
            LAB / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
            / "EndfieldSecondaryDynamicsBindingBuilder.cs"
        ).read_text(encoding="utf-8")
        runtime = (
            LAB / "Assets/EndfieldGraphShaderLab/Runtime/Animation"
            / "EndfieldCapturedSecondaryDynamicsReplay.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("replay.useCapturedReplay = false;", builder)
        self.assertIn("public bool useCapturedReplay = false;", runtime)


if __name__ == "__main__":
    unittest.main()
