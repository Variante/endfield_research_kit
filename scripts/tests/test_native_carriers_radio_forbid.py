from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery.native_carriers import radio_forbid


class RadioForbidBoundaryTests(unittest.TestCase):
    def test_retained_contract_is_versioned_and_bounded(self) -> None:
        contract = radio_forbid.load_contract()

        self.assertEqual(contract["schema"], "radioForbidNegativeBoundary.v1")
        self.assertEqual(
            contract["classification"],
            "no_current_offline_nonempty_radio_id_producer",
        )
        self.assertEqual(contract["nativeSurface"]["defaultFactory"]["radioIdArgument"], "null")
        self.assertEqual(contract["nativeSurface"]["setForbidExecute"]["forbidParamsArgument"], "null")
        self.assertIn("future builds remain open", contract["evidenceBoundary"])

    def test_contract_rejects_a_nonempty_producer_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            contract = radio_forbid.load_contract()
            contract["observations"]["nonEmptySerializedRadioIds"] = 1
            path.write_text(json.dumps(contract), encoding="utf-8")

            with self.assertRaisesRegex(
                radio_forbid.ContractError,
                "empty serialized value set",
            ):
                radio_forbid.load_contract(path)


if __name__ == "__main__":
    unittest.main()
