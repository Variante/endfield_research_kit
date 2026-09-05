from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from scripts.game_data.streaming_marker13_corpus import (
    protected_input_paths,
    validate_output_isolation,
)


class OutputIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.report = self.root / "root.json"
        self.outer = self.root / "outer.json"
        self.ledger = self.root / "ledger.jsonl.gz"
        self.source = self.root / "parser.py"
        self.fingerprint = self.root / "source.blc"
        self.chunk = self.root / "physical.chk"
        self.game_root = self.root / "game/Endfield_Data"
        self.metadata = self.game_root / "il2cpp_data/Metadata/global-metadata.dat"
        self.game_root.mkdir(parents=True)
        self.metadata.parent.mkdir(parents=True)
        for path in (
            self.report, self.outer, self.ledger, self.source, self.fingerprint, self.chunk,
            self.metadata, self.game_root.parent / "GameAssembly.dll",
            self.game_root.parent / "UnityPlayer.dll",
        ):
            path.write_bytes(path.name.encode())
        self.protected = protected_input_paths(
            repo_root=self.root,
            root_report_path=self.report,
            outer_summary_path=self.outer,
            ledger_path=self.ledger,
            outer={"sourceFingerprints": [{"path": str(self.fingerprint)}]},
            game_root=self.game_root,
            source_paths={"parserSha256": self.source},
            ledger_rows=[{"physicalChunkPath": str(self.chunk)}],
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_distinct_outputs_are_accepted(self):
        validate_output_isolation(
            outputs={
                "outputJson": self.root / "out/report.json",
                "outputMarkdown": self.root / "out/report.md",
                "outputInventory": self.root / "out/inventory.gz",
            },
            protected=self.protected,
        )

    def test_inventory_cannot_replace_outer_ledger(self):
        before = self.ledger.read_bytes()
        with self.assertRaisesRegex(ValueError, r"outputInventory=.*conflicts with outerLedger="):
            validate_output_isolation(
                outputs={"outputInventory": self.ledger}, protected=self.protected
            )
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_outputs_must_be_mutually_distinct(self):
        shared = self.root / "out/shared"
        with self.assertRaisesRegex(ValueError, r"expected distinct outputs"):
            validate_output_isolation(
                outputs={"outputJson": shared, "outputInventory": shared},
                protected=self.protected,
            )

    def test_resolved_parent_alias_is_rejected(self):
        aliased = self.root / "nested/../ledger.jsonl.gz"
        with self.assertRaisesRegex(ValueError, r"conflicts with outerLedger"):
            validate_output_isolation(
                outputs={"outputInventory": aliased}, protected=self.protected
            )

    def test_existing_hardlink_alias_is_rejected(self):
        alias = self.root / "ledger-hardlink.gz"
        try:
            os.link(self.ledger, alias)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, r"conflicts with outerLedger"):
            validate_output_isolation(
                outputs={"outputInventory": alias}, protected=self.protected
            )

    def test_existing_physical_chunk_hardlink_alias_is_rejected(self):
        alias = self.root / "chunk-hardlink.chk"
        try:
            os.link(self.chunk, alias)
        except OSError as exc:
            self.skipTest(f"hard links unavailable: {exc}")
        with self.assertRaisesRegex(ValueError, r"conflicts with physicalChunk"):
            validate_output_isolation(
                outputs={"outputInventory": alias}, protected=self.protected
            )

    def test_source_native_and_fingerprint_collisions_are_rejected(self):
        cases = {
            "source": self.source,
            "native": self.game_root.parent / "UnityPlayer.dll",
            "fingerprint": self.fingerprint,
            "physicalChunk": self.chunk,
        }
        for name, path in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError, r"disjoint from authenticated inputs"
            ):
                validate_output_isolation(
                    outputs={"outputJson": path}, protected=self.protected
                )

    def test_missing_output_is_ignored_for_sweep_inventory_only_guard(self):
        validate_output_isolation(
            outputs={"outputJson": None, "outputInventory": self.root / "safe.gz"},
            protected=self.protected,
        )


if __name__ == "__main__":
    unittest.main()
