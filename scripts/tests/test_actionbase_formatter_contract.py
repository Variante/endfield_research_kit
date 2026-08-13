from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts.story_builder.native_contracts import actionbase_formatter


class ActionBaseFormatterContractTest(unittest.TestCase):
    def test_canonical_contract_recovers_every_tag(self):
        names, audit = actionbase_formatter.load_actionbase_formatter_names()

        self.assertEqual("validated", audit["status"])
        self.assertEqual(1313, len(names))
        self.assertEqual("AbilitySystemReset", names[0])
        self.assertEqual("CallServer", names[0x0034])
        self.assertEqual("SendLuaEvent2", names[0x0520])

    def test_contract_fails_closed_on_table_drift(self):
        canonical = json.loads(
            actionbase_formatter.DEFAULT_CONTRACT.read_text(encoding="utf-8")
        )
        malformed = copy.deepcopy(canonical)
        malformed["actionNames"][42] = ""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.json"
            path.write_text(json.dumps(malformed), encoding="utf-8")
            names, audit = actionbase_formatter.load_actionbase_formatter_names(path)

        self.assertEqual({}, names)
        self.assertEqual("validation_failed", audit["status"])
        self.assertEqual(
            "nonempty_action_name",
            audit["validationFailures"][0]["gate"],
        )

    def test_contract_fails_closed_on_installed_build_drift(self):
        mismatched = SimpleNamespace(
            status="mismatched",
            detail="GameAssembly.dll hash differs",
        )
        with mock.patch.object(
            actionbase_formatter,
            "check_installed_native_inputs",
            return_value=mismatched,
        ):
            names, audit = actionbase_formatter.load_actionbase_formatter_names()

        self.assertEqual({}, names)
        self.assertEqual("mismatched", audit["status"])
        self.assertEqual(
            "installed_native_inputs",
            audit["validationFailures"][0]["gate"],
        )


if __name__ == "__main__":
    unittest.main()
