"""Mechanically snapshot local Python import closures and literal resources.

This module is intentionally independent of a corpus publication gate.  It is
useful for development caches and diagnostics, where hashing an entire package
would make unrelated modules invalidate one another.  Publication readers must
retain their existing authenticated, start/end drift gates.

It follows repo-local Python imports, literal contract resources, transitive
contract-declared JSON/Python ``dependencies``, and literal helper paths passed
to a local ``spec_from_file_location`` loader.  It fails closed on ambiguous
basenames, conflicting assignments, missing or repository-escaping paths and
unsupported declarations.  Runtime-computed paths and dynamic contract
discovery are outside its static proof, which is why dependency-scoped replay
stays developmental: it is not equivalent to a complete family sweep until
mechanically derived transitive dependencies and merged rows are shown equal
to one under mutation tests.  Route admission has a global negative
dependency -- adding a formerly unknown route can change an old bounded row
elsewhere -- so no per-file dependency set can prove a cached row current.

Call ``dependency_snapshot(roots)`` with importable module names; it hashes the
resolved closure. The module has no command-line entry point.
"""

from __future__ import annotations

import ast
from collections import OrderedDict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Iterable

from scripts.repo_paths import REPO_ROOT


class DependencySnapshotError(ValueError):
    """A declared dependency cannot be resolved without guessing."""


class _ParseFactsCache:
    """Bounded immutable syntax facts, never paths, manifests or proof results.

    Each caller still reads current bytes. Full bytes form the key; timestamps
    and saved digests confer no freshness. Filesystem-dependent resolution and
    every ambiguity/existence/escape check remain outside this cache.
    """
    def __init__(self, *, max_bytes=128 * 1024 * 1024, max_entries=4096,
                 max_entry_bytes=8 * 1024 * 1024):
        self.max_bytes = max_bytes
        self.max_entries = max_entries
        self.max_entry_bytes = max_entry_bytes
        self.entries = OrderedDict()
        self.bytes = 0

    def get(self, kind, raw, build):
        key = (kind, raw)
        if key in self.entries:
            value, size = self.entries.pop(key)
            self.entries[key] = (value, size)
            return value
        value = build()
        pending, seen, size = [key, value], set(), 0
        while pending:
            item = pending.pop()
            if id(item) in seen:
                continue
            seen.add(id(item))
            size += sys.getsizeof(item)
            if isinstance(item, tuple):
                pending.extend(item)
        # Large reviewed contracts must not evict the whole Python syntax
        # working set merely to cache an empty dependency declaration.
        if size <= min(self.max_bytes, self.max_entry_bytes):
            while self.entries and (len(self.entries) >= self.max_entries
                                    or self.bytes + size > self.max_bytes):
                _, (_, removed) = self.entries.popitem(last=False)
                self.bytes -= removed
            if self.max_entries > 0:
                self.entries[key] = (value, size)
                self.bytes += size
        return value

    def clear(self):
        self.entries.clear()
        self.bytes = 0


_PARSE_FACTS = _ParseFactsCache()


def _freeze_ast(value):
    if isinstance(value, ast.AST):
        return ('node', type(value).__name__, tuple(
            (name, _freeze_ast(item)) for name, item in ast.iter_fields(value)))
    if isinstance(value, list):
        return ('list', tuple(_freeze_ast(item) for item in value))
    return ('value', value)


def _thaw_ast(value):
    kind, *parts = value
    if kind == 'node':
        name, fields = parts
        return getattr(ast, name)(**{key: _thaw_ast(item) for key, item in fields})
    if kind == 'list':
        return [_thaw_ast(item) for item in parts[0]]
    return parts[0]


def _python_facts(raw, source):
    def build():
        tree = ast.parse(raw.decode('utf-8-sig'), filename=str(source))
        imports, resources = [], set()
        has_loader = False
        for node in ast.walk(tree):
            if (imported := _import_fact(node)) is not None:
                imports.append(imported)
            elif (resource := _literal_json_name(node)) is not None:
                resources.add(resource)
            elif (isinstance(node, ast.Call) and len(node.args) >= 2
                  and _call_name(node).endswith('spec_from_file_location')):
                has_loader = True
        # Store immutable syntax only. Path-loaded helper expressions are
        # evaluated against the current filesystem using a new private AST.
        helper_syntax = None
        if has_loader:
            try:
                helper_syntax = _freeze_ast(tree)
            except RecursionError:
                # ast.walk accepts some trees deeper than recursive freezing.
                # Reparse those rare sources instead of adding a new refusal.
                helper_syntax = ('reparse',)
        return tuple(imports), tuple(sorted(resources)), helper_syntax
    return _PARSE_FACTS.get('python', raw, build)


def _fresh_helper_tree(syntax, raw, source):
    if syntax != ('reparse',):
        try:
            return _thaw_ast(syntax)
        except RecursionError:
            pass
    return ast.parse(raw.decode('utf-8-sig'), filename=str(source))


def _json_dependency_declarations(raw, path):
    def build():
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DependencySnapshotError(f"cannot parse JSON dependency source {path}: {exc}") from exc
        if not isinstance(value, dict) or 'dependencies' not in value:
            return ()
        dependencies = value['dependencies']
        if not isinstance(dependencies, list):
            raise DependencySnapshotError(f"{path}: dependencies must be an array")
        result = []
        for index, dependency in enumerate(dependencies):
            declared = dependency if isinstance(dependency, str) else (
                dependency.get('path') if isinstance(dependency, dict) else None)
            # Keep invalid declarations in order, so an earlier path escape
            # still refuses before a later invalid declaration as before.
            result.append(declared if isinstance(declared, str) and declared else None)
        return tuple(result)
    return _PARSE_FACTS.get('json', raw, build)


def _inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return False
    return True


def _module_source(module_name: str) -> Path | None:
    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, AttributeError, ValueError):
        return None
    if spec is None or not spec.origin or spec.origin in {"built-in", "frozen"}:
        return None
    path = Path(spec.origin).resolve()
    return path if path.suffix == ".py" and path.is_file() and _inside_repo(path) else None


def _resolve_imports(module_name: str, tree: ast.AST) -> set[str]:
    return _imports_from_facts(module_name,
        tuple(fact for node in ast.walk(tree) if (fact := _import_fact(node)) is not None),
        selected_source=_module_source(module_name))


def _import_fact(node):
    if isinstance(node, ast.Import):
        return 'import', tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return 'from', node.level, node.module, tuple(alias.name for alias in node.names)
    return None


def _imports_from_facts(module_name, facts, *, selected_source):
    result: set[str] = set()
    package = module_name if Path(selected_source or "").name == "__init__.py" else module_name.rpartition(".")[0]
    for row in facts:
        if row[0] == 'import':
            result.update(row[1])
            continue
        _, level, module, names = row
        if level:
            try:
                base = importlib.util.resolve_name('.' * level + (module or ''), package)
            except (ImportError, ValueError):
                continue
        else:
            base = module or ''
        if base:
            result.add(base)
            # An imported attribute may also be a real submodule.
            result.update(base + '.' + name for name in names if name != '*')
    return result


def _literal_json_resources(
    tree: ast.AST,
    resources_by_name: dict[str, list[Path]],
) -> set[Path]:
    names = {name for node in ast.walk(tree) if (name := _literal_json_name(node)) is not None}
    return _json_resources_from_names(names, resources_by_name)


def _literal_json_name(node):
    if (isinstance(node, ast.Constant) and isinstance(node.value, str)
            and node.value.lower().endswith('.json') and Path(node.value).name == node.value):
        return node.value
    return None


def _json_resources_from_names(names, resources_by_name):
    result: set[Path] = set()
    for name in names:
        matches = resources_by_name.get(name, [])
        if len(matches) > 1:
            raise DependencySnapshotError(
                f"ambiguous literal JSON resource {name!r}: "
                + ", ".join(path.as_posix() for path in sorted(matches))
            )
        if matches:
            result.add(matches[0])
    return result


def _declared_dependency_paths(path: Path, *, allowed_root: Path) -> set[Path]:
    """Resolve one contract's explicit JSON/Python dependency edges exactly."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DependencySnapshotError(f"cannot parse JSON dependency source {path}: {exc}") from exc
    result: set[Path] = set()
    for index, declared in enumerate(_json_dependency_declarations(raw, path)):
        if declared is None:
            raise DependencySnapshotError(
                f"{path}: dependencies[{index}] must be a path string or declare one string path")
        candidate = Path(declared)
        if candidate.is_absolute() or candidate.suffix.lower() not in {".json", ".py"}:
            raise DependencySnapshotError(
                f"{path}: dependencies[{index}] is not a relative JSON/Python path: {declared!r}"
            )
        resolved = (path.parent / candidate).resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError as exc:
            raise DependencySnapshotError(
                f"{path}: dependencies[{index}] escapes dependency root: {declared!r}"
            ) from exc
        if not resolved.is_file():
            raise DependencySnapshotError(
                f"{path}: dependencies[{index}] is missing: {declared!r}"
            )
        result.add(resolved)
    return result


def _call_name(node: ast.Call) -> str:
    parts: list[str] = []
    value: ast.AST = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return ".".join(reversed(parts))


def _literal_python_helpers(tree: ast.AST, source: Path) -> set[Path]:
    """Find repo-local helpers passed to a local ``spec_from_file_location`` loader.

    The evaluator accepts only paths composed from ``__file__``, ``REPO_ROOT``,
    literal strings, ``parent``/``parents[N]``, ``/``, ``with_name``,
    ``with_suffix`` and ``resolve``. Dynamic arguments remain outside this
    development snapshot rather than being guessed.
    """
    if not any(isinstance(node, ast.Call) and len(node.args) >= 2
               and _call_name(node).endswith("spec_from_file_location") for node in ast.walk(tree)):
        return set()
    assignments: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if value is None:
                continue
            for target in targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(value)

    def evaluate(node: ast.AST, resolving: frozenset[str] = frozenset()) -> set[Path]:
        if isinstance(node, ast.Name):
            if node.id == "__file__":
                return {source.resolve()}
            if node.id == "REPO_ROOT":
                return {REPO_ROOT.resolve()}
            if node.id in resolving:
                return set()
            values: set[Path] = set()
            for expression in assignments.get(node.id, []):
                values.update(evaluate(expression, resolving | {node.id}))
            return values
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = Path(node.value)
            if value.is_absolute():
                return {value.resolve()}
            # Bare literals in loader calls use the repository working-root
            # convention; source-relative paths should use __file__ explicitly.
            return {(REPO_ROOT / value).resolve()}
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in {"Path", "pathlib.Path"} and len(node.args) == 1:
                return evaluate(node.args[0], resolving)
            if isinstance(node.func, ast.Attribute):
                base = evaluate(node.func.value, resolving)
                if node.func.attr == "resolve" and not node.args:
                    return {path.resolve() for path in base}
                if node.func.attr == "with_name" and len(node.args) == 1:
                    names = evaluate_string(node.args[0])
                    return {path.with_name(name).resolve() for path in base for name in names}
                if node.func.attr == "with_suffix" and len(node.args) == 1:
                    suffixes = evaluate_string(node.args[0])
                    return {path.with_suffix(suffix).resolve() for path in base for suffix in suffixes}
            return set()
        if isinstance(node, ast.Attribute) and node.attr == "parent":
            return {path.parent for path in evaluate(node.value, resolving)}
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "parents"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, int)
            and node.slice.value >= 0
        ):
            result = set()
            for path in evaluate(node.value.value, resolving):
                try:
                    result.add(path.parents[node.slice.value])
                except IndexError:
                    pass
            return result
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left = evaluate(node.left, resolving)
            right = evaluate_string(node.right)
            return {(base / part).resolve() for base in left for part in right}
        return set()

    def evaluate_string(node: ast.AST) -> set[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        return set()

    loaders: dict[str, int] = {}
    for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
        positional = [*function.args.posonlyargs, *function.args.args]
        positions = {argument.arg: index for index, argument in enumerate(positional)}
        for call in (node for node in ast.walk(function) if isinstance(node, ast.Call)):
            if _call_name(call).endswith("spec_from_file_location") and len(call.args) >= 2:
                path_argument = call.args[1]
                if isinstance(path_argument, ast.Name) and path_argument.id in positions:
                    loaders[function.name] = positions[path_argument.id]

    candidates: list[tuple[str, ast.AST]] = []
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        name = _call_name(call)
        if name.endswith("spec_from_file_location") and len(call.args) >= 2:
            candidates.append((name, call.args[1]))
        short_name = name.rsplit(".", 1)[-1]
        if short_name in loaders and len(call.args) > loaders[short_name]:
            candidates.append((short_name, call.args[loaders[short_name]]))

    result: set[Path] = set()
    for loader, expression in candidates:
        paths = evaluate(expression)
        if len(paths) > 1:
            raise DependencySnapshotError(
                f"{source}: ambiguous Python helper passed to {loader}: "
                + ", ".join(path.as_posix() for path in sorted(paths))
            )
        if not paths:
            continue
        path = next(iter(paths))
        if path.suffix.lower() != ".py":
            continue
        if not _inside_repo(path):
            raise DependencySnapshotError(f"{source}: Python helper escapes repository: {path}")
        if not path.is_file():
            raise DependencySnapshotError(f"{source}: Python helper is missing: {path}")
        result.add(path)
    return result


def _module_name_for_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        # Explicit test/development roots may live outside the checkout.  The
        # path itself is still hashed; this synthetic name only supplies a
        # package context for any absolute imports the helper declares.
        return path.stem
    parts = list(relative.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def local_dependency_paths(
    roots: Iterable[str],
    *,
    resource_search_root: Path | None = None,
) -> list[Path]:
    """Return the transitive repo-local Python closure and literal JSON inputs."""
    pending_modules = list(dict.fromkeys(roots))
    pending_sources: list[tuple[Path, str]] = []
    visited_modules: set[str] = set()
    visited_sources: set[Path] = set()
    visited_json: set[Path] = set()
    module_sources: dict[str, Path | None] = {}

    def module_source(name):
        # Resolution is invocation-local. A newly added/importable module or
        # changed search path must be resolved again by the next snapshot.
        if name not in module_sources:
            module_sources[name] = _module_source(name)
        return module_sources[name]

    paths: set[Path] = set()
    resource_root = (resource_search_root or (REPO_ROOT / "scripts/game_data")).resolve()
    resources_by_name: dict[str, list[Path]] = {}
    for path in resource_root.rglob("*.json"):
        resources_by_name.setdefault(path.name, []).append(path.resolve())
    while pending_modules or pending_sources:
        if pending_sources:
            source, module_name = pending_sources.pop()
            source = source.resolve()
        else:
            module_name = pending_modules.pop()
            if module_name in visited_modules:
                continue
            visited_modules.add(module_name)
            source = module_source(module_name)
            if source is None:
                continue
        if source in visited_sources:
            continue
        visited_sources.add(source)
        paths.add(source)
        raw = source.read_bytes()
        imports, resource_names, helper_tree = _python_facts(raw, source)
        json_resources = _json_resources_from_names(resource_names, resources_by_name)
        paths.update(json_resources)
        pending_json = list(json_resources)
        while pending_json:
            resource = pending_json.pop().resolve()
            if resource in visited_json:
                continue
            visited_json.add(resource)
            dependencies = _declared_dependency_paths(resource, allowed_root=resource_root)
            paths.update(dependencies)
            pending_json.extend(path for path in dependencies if path.suffix.lower() == ".json")
            for dependency in dependencies:
                if dependency.suffix.lower() == ".py" and dependency not in visited_sources:
                    pending_sources.append((dependency, _module_name_for_path(dependency)))
        helpers = _literal_python_helpers(_fresh_helper_tree(helper_tree, raw, source), source) if helper_tree is not None else ()
        for helper in helpers:
            paths.add(helper)
            if helper not in visited_sources:
                pending_sources.append((helper, _module_name_for_path(helper)))
        for imported in _imports_from_facts(module_name, imports, selected_source=module_source(module_name)):
            if imported not in visited_modules and module_source(imported) is not None:
                pending_modules.append(imported)
    return sorted(paths, key=lambda path: path.as_posix().lower())


def dependency_snapshot(
    roots: Iterable[str],
    *,
    resource_search_root: Path | None = None,
) -> dict[str, Any]:
    """Return a deterministic manifest plus a digest of its exact contents."""
    files = []
    for path in local_dependency_paths(roots, resource_search_root=resource_search_root):
        raw = path.read_bytes()
        files.append({
            "path": path.resolve().as_posix(),
            "length": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
        })
    encoded = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "roots": list(dict.fromkeys(roots)),
        "files": files,
        "sha256": hashlib.sha256(encoded).hexdigest().upper(),
    }
