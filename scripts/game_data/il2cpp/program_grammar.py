"""Fail-closed checking of a complete selected instruction grammar.

Branch and call destinations are computed from original bytes. Local labels
must land at checked instruction boundaries. This is a static program proof;
checking a branch says nothing about its outcome during execution.
"""
from __future__ import annotations
import re
from typing import Any


class ProgramGrammar:
    def __init__(self, rows: list[dict], *, label: str):
        self.rows = rows; self.label = label; self.cursor = 0
        self.labels: dict[str, int] = {}; self.edges: list[tuple[int, str, dict]] = []
        if not rows:
            self.fail('inventory', 'nonempty contiguous original instructions', [])
        for n, row in enumerate(rows):
            raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
            if not raw or n and at != int(rows[n-1]['va'],16) + len(bytes.fromhex(rows[n-1]['bytes'])):
                self.fail('inventory', 'contiguous instruction bytes', row)

    def fail(self, check: str, expected: Any, actual: Any) -> None:
        raise ValueError(f'{self.label}.{check}: instruction={self.cursor} '
                         f'expected={str(expected)[:256]} actual={str(actual)[:384]}')

    def row(self) -> dict:
        if self.cursor >= len(self.rows):
            self.fail('program-end', 'next checked instruction', 'end')
        row = self.rows[self.cursor]; self.cursor += 1; return row

    def take(self, *texts: str) -> dict:
        row = None
        for text in texts:
            row = self.row()
            if row['text'] != text:
                self.fail('instruction', text, row)
        assert row is not None
        return row

    def pattern(self, pattern: str) -> dict:
        row = self.row()
        if not re.fullmatch(pattern, row['text']):
            self.fail('instruction-pattern', pattern, row)
        return row

    def mark(self, label: str) -> None:
        if label in self.labels:
            self.fail('label', 'unique label', label)
        self.labels[label] = int(self.rows[self.cursor]['va'],16) if self.cursor < len(self.rows) else (
            int(self.rows[-1]['va'],16) + len(bytes.fromhex(self.rows[-1]['bytes'])))

    def branch(self, condition: str, label: str | None = None) -> dict:
        row = self.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'],16)
        codes = {'je':4, 'jne':5, 'jg':15, 'ja':7, 'jbe':6}
        if condition == 'jmp' and len(raw) in (2,5) and raw[0] == (0xeb if len(raw)==2 else 0xe9):
            relative = raw[1:]
        elif condition in codes and len(raw) == 2 and raw[0] == 0x70 + codes[condition]:
            relative = raw[1:]
        elif condition in codes and len(raw) == 6 and raw[:2] == bytes((0x0f,0x80+codes[condition])):
            relative = raw[2:]
        else:
            self.fail('branch-predicate', condition, row)
        target = at + len(raw) + int.from_bytes(relative,'little',signed=True)
        if row['text'] not in (f'{condition} 0x{target:x}', f'jcc 0x{target:x}'):
            self.fail('branch-decoding', hex(target), row)
        if label is not None: self.edges.append((target,label,row))
        return {**row,'target':target,'predicate':condition}

    def call(self, pointer: int) -> dict:
        row = self.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'],16)
        target = at + 5 + int.from_bytes(raw[1:],'little',signed=True) if len(raw)==5 and raw[0]==0xe8 else None
        if target != pointer or row['text'] != f'call 0x{pointer:x}':
            self.fail('direct-call', hex(pointer), row)
        return row

    def finish(self, *, prefix: bool = False) -> None:
        if not prefix and self.cursor != len(self.rows):
            self.fail('program-tail', 'entire selected program checked', self.rows[self.cursor])
        for target,label,row in self.edges:
            if label not in self.labels or self.labels[label] != target:
                self.fail('local-edge:' + label, self.labels.get(label), row)
