"""Bounded original-instruction paths inside one selected native body.

Both edges of a complete local conditional branch are candidates. This proves
only compiled reachability under unspecified branch outcomes, never execution,
callee return or feasibility of a particular combination of predicate values.
"""
from __future__ import annotations
from collections import deque
from typing import Any, Iterator

MAX_LOCAL_PATH_PREFIXES = 4096
_SHORT_BRANCHES = ('jo','jno','jb','jae','je','jne','jbe','ja',
                   'js','jns','jp','jnp','jl','jge','jle','jg')


class CompiledLocalPaths:
    def __init__(self, body: Any, *, maximum: int = MAX_LOCAL_PATH_PREFIXES):
        self.body = body
        self.maximum = maximum
        self.audit: dict[str, Any] = {'method': body.symbol, 'prefixesChecked': 0,
            'maximumPrefixes': maximum, 'limitReached': False, 'inventoryValidated': False,
            'unknownInstructions': 0, 'unfollowedEdges': 0}

    def __iter__(self) -> Iterator[tuple[dict[str, Any], ...]]:
        rows = self.body.rows
        try:
            if type(self.maximum) is not int or self.maximum < 1:
                raise ValueError('positive explicit prefix bound required')
            addresses = [int(r['va'], 16) for r in rows]
            if (not rows or addresses[0] != self.body.pointer or len(set(addresses)) != len(rows)
                    or addresses != sorted(addresses)):
                raise ValueError('unique ordered incoming-body instruction inventory required')
            raw = [bytes.fromhex(r['bytes']) for r in rows]
            if (any(not b for b in raw)
                    or any(at + len(b) > self.body.pointer + self.body.size for at, b in zip(addresses, raw))
                    or any(at + len(b) != next_at for at, b, next_at in zip(addresses, raw, addresses[1:]))):
                raise ValueError('complete contiguous in-body instruction byte spans required')
        except (ValueError, KeyError, TypeError) as exc:
            self.audit['inventoryFailure'] = str(exc)[:256]
            return
        self.audit['inventoryValidated'] = True
        positions = {at: n for n, at in enumerate(addresses)}
        pending = deque([(0, (), frozenset())])
        while pending and self.audit['prefixesChecked'] < self.maximum:
            cursor, prefix, visited = pending.popleft()
            row = rows[cursor]
            program = (*prefix, row)
            self.audit['prefixesChecked'] += 1
            yield program
            if cursor in visited:
                continue
            visited = visited | {cursor}
            text = str(row.get('text') or '')
            code = raw[cursor]
            at = addresses[cursor]
            if text.startswith(('ret', 'int3', 'db')):
                if text.startswith('db'):
                    self.audit['unknownInstructions'] += 1
                continue
            relative = None
            conditional = False
            mnemonic = None
            if len(code) == 2 and code[0] == 0xeb:
                relative, mnemonic = code[1:], 'jmp'
            elif len(code) == 5 and code[0] == 0xe9:
                relative, mnemonic = code[1:], 'jmp'
            elif len(code) == 2 and 0x70 <= code[0] <= 0x7f:
                relative, mnemonic, conditional = code[1:], _SHORT_BRANCHES[code[0] - 0x70], True
            elif len(code) == 6 and code[0] == 0x0f and 0x80 <= code[1] <= 0x8f:
                relative, mnemonic, conditional = code[2:], _SHORT_BRANCHES[code[1] - 0x80], True
            elif text.startswith(('j', 'loop')):
                self.audit['unfollowedEdges'] += 1
                continue
            if relative is not None:
                target = at + len(code) + int.from_bytes(relative, 'little', signed=True)
                allowed = {f'{mnemonic} 0x{target:x}'}
                if len(code) == 6 and conditional:
                    allowed.add(f'jcc 0x{target:x}')
                if text not in allowed:
                    self.audit['unfollowedEdges'] += 1
                    continue
                if target in positions and positions[target] not in visited:
                    pending.append((positions[target], program, visited))
                else:
                    self.audit['unfollowedEdges'] += 1
                if not conditional:
                    continue
            if cursor + 1 < len(rows) and cursor + 1 not in visited:
                pending.append((cursor + 1, program, visited))
        self.audit['limitReached'] = bool(pending)


def diagnostic(audit: dict[str, Any]) -> str:
    if not audit['inventoryValidated']:
        return 'inventory=' + audit.get('inventoryFailure', 'unproved')
    return (f"prefixes={audit['prefixesChecked']}/{audit['maximumPrefixes']}; "
            f"limitReached={audit['limitReached']}; unknown={audit['unknownInstructions']}; "
            f"unfollowedEdges={audit['unfollowedEdges']}")
