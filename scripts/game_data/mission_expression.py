"""Bounded ASCII model of the Mission native lexer and stack AST parser.

The native review is authenticated separately by mission_expression_native.
This module models successful normal parser calls, not live IFix selection,
allocation, culture-dependent Unicode lowercasing, or cached condition values.
"""
from __future__ import annotations

from typing import Any

MAX_LENGTH = 8192
MAX_DEPTH = 64


def lex_expression(text: str) -> list[tuple[str, int | None]]:
    if not isinstance(text, str) or len(text) > MAX_LENGTH:
        raise ValueError("mission_expression.length: bounded string required")
    if not text.isascii():
        raise ValueError("mission_expression.character: Unicode culture semantics withheld")
    lowered = text.lower()
    tokens, at = [], 0
    while at < len(lowered):
        char = lowered[at]
        if char in " \t":
            at += 1
            continue
        for word in ("not", "and", "or"):
            if lowered.startswith(word, at):
                tokens.append((word, None))
                at += len(word)
                break
        else:
            if char in "()":
                tokens.append((char, None))
                at += 1
                continue
            if char != "{":
                raise ValueError(f"mission_expression.token: at={at} actual={char!r}")
            end = at+1
            while end < len(lowered) and "0" <= lowered[end] <= "9":
                end += 1
            if end == at+1 or end >= len(lowered) or lowered[end] != "}":
                raise ValueError(f"mission_expression.index: malformed index at={at}")
            value = 0
            for digit in lowered[at+1:end]:
                value = value*10+ord(digit)-ord("0")
                if value > 0x7fffffff:
                    raise ValueError(f"mission_expression.index: Int32 overflow at={at}")
            tokens.append(("index", value))
            at = end+1
            continue
        continue
    return tokens


def parse_expression(text: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    """Immediate reductions give AND and OR equal, left-associative precedence.

    The native parser validates a contiguous *distinct* index set. It does not
    require every supplied child to be referenced; the outer evaluator still
    waits on all children. This source model additionally rejects out-of-range
    references, which would fail when the native evaluator indexes its array.
    """
    stack: list[dict[str, Any]] = []
    indices: set[int] = set()
    depth = 0

    def reduce() -> None:
        while len(stack) >= 2 and stack[-1]["done"]:
            right = stack.pop()
            parent = stack[-1]
            if parent["op"] not in {"not", "and", "or"}:
                stack.append(right)
                return
            if parent["done"]:
                raise ValueError("mission_expression.stack: completed operator reused")
            parent["right"] = right
            parent["done"] = True

    for token, value in lex_expression(text):
        if token == "index":
            if value is None or not 0 <= value < len(children):
                raise ValueError(f"mission_expression.index: child count={len(children)} actual={value}")
            indices.add(value)
            stack.append({"op": "index", "index": value, "done": True})
            reduce()
        elif token in {"not", "("}:
            stack.append({"op": token, "done": False})
            if token == "(":
                depth += 1
        elif token in {"and", "or"}:
            if not stack or not stack[-1]["done"]:
                raise ValueError("mission_expression.stack: binary operator lacks completed left operand")
            left = stack.pop()
            stack.append({"op": token, "left": left, "done": False})
        else:
            if len(stack) < 2:
                raise ValueError("mission_expression.stack: closing parenthesis lacks pair")
            child = stack.pop()
            parent = stack[-1]
            if not child["done"] or parent["op"] != "(" or parent["done"]:
                raise ValueError("mission_expression.stack: invalid parenthesis contents")
            parent.update(right=child, done=True)
            depth -= 1
            reduce()
        if depth > MAX_DEPTH or len(stack) > MAX_DEPTH:
            raise ValueError("mission_expression.depth: stack or parenthesis budget exceeded")
    reduce()
    if len(stack) != 1 or not stack[0]["done"]:
        raise ValueError("mission_expression.stack: exactly one completed root required")
    if indices != set(range(len(indices))):
        raise ValueError(f"mission_expression.indices: noncontiguous distinct set={sorted(indices)[:32]}")

    def prune(node: dict[str, Any], level: int) -> dict[str, Any]:
        if level > MAX_DEPTH:
            raise ValueError("mission_expression.depth: resulting tree budget exceeded")
        if node["op"] == "index":
            return children[node["index"]]
        if node["op"] == "(":
            return prune(node["right"], level+1)
        if node["op"] == "not":
            return {"op": "not", "child": prune(node["right"], level+1)}
        return {"op": node["op"], "left": prune(node["left"], level+1),
                "right": prune(node["right"], level+1)}

    return prune(stack[0], 0)
