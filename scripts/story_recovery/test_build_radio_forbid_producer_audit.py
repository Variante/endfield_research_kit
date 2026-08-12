from __future__ import annotations

import unittest

from scripts.story_recovery import build_radio_forbid_producer_audit as audit


def instructions(*texts: str) -> list[dict[str, str]]:
    return [{"va": f"0x{index:x}", "text": text} for index, text in enumerate(texts)]


class RadioForbidProducerAuditTests(unittest.TestCase):
    def test_default_factory_requires_null_radio_id(self) -> None:
        row = audit.extract_default_radio_factory_branch(
            instructions(
                "cmp ebx, 0x19", "jne 0x20", "call 0x100",
                "xor r8d, r8d", "xor edx, edx", "mov rcx, rax", "call 0x200",
            ),
            25,
            0x200,
        )
        self.assertEqual(row["radioIdArgument"], "null")

    def test_default_factory_fails_closed_without_zeroed_string(self) -> None:
        with self.assertRaisesRegex(audit.AuditError, "nullRadioIdFactoryArguments"):
            audit.extract_default_radio_factory_branch(
                instructions(
                    "cmp ebx, 0x19", "xor r8d, r8d", "mov rcx, rax", "call 0x200"
                ),
                25,
                0x200,
            )

    def test_set_forbid_requires_null_optional_params(self) -> None:
        row = audit.extract_set_forbid_null_params(
            instructions(
                "and [rsp+0x30], 0x0", "and [rsp+0x28], 0x0",
                "mov [rsp+0x20], al", "call 0x300",
            ),
            0x300,
        )
        self.assertEqual(row["forbidParamsArgument"], "null")


if __name__ == "__main__":
    unittest.main()
