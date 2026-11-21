"""Keep ordinary page builds independent of disposable investigation artifacts.

The export scheduler enables this boundary for its Python children, including
nested builders. Diagnostics may be written here, but never read as evidence.
Recovery commands outside that scheduler can still accept explicit probe inputs.
"""
from __future__ import annotations

import os
import sys

from scripts.repo_paths import REPO_ROOT

INPUT_BOUNDARY_ENV = "ENDFIELD_BUILD_INPUT_BOUNDARY"
_installed = False
# An isolated validation checkout also refuses disposable inputs from the
# originating workspace. Extra roots only extend the boundary; they cannot
# replace or disable this checkout's four forbidden input directories.
_workspace_roots = (REPO_ROOT, *filter(None,
    os.environ.get('ENDFIELD_BUILD_INPUT_ADDITIONAL_REPO_ROOTS', '').split(os.pathsep)))
_disposable_roots = tuple(os.path.normcase(os.path.realpath(os.path.join(root, name)))
                          for root in _workspace_roots
                          for name in ("tmp", "scratch", "reports", "report"))


# The audit hook sees every open; resolving each full path walks every
# component. A plain (non-link) leaf resolves through its parent folder, and a
# folder's resolution is reused within the process once seen as a directory.
# A link or junction leaf is always resolved in full.
_PARENT_REALPATHS: dict[str, str] = {}
_PARENT_REALPATH_LIMIT = 65536
_REPARSE_POINT = 0x400


def _resolved(value: str) -> str:
    absolute = os.path.abspath(value)
    try:
        observed = os.lstat(absolute)
    except OSError:
        observed = None
    if observed is None or os.path.islink(absolute) or (
            getattr(observed, "st_file_attributes", 0) & _REPARSE_POINT):
        return os.path.realpath(absolute)
    parent, leaf = os.path.split(absolute)
    if not leaf:
        return os.path.realpath(absolute)
    real_parent = _PARENT_REALPATHS.get(parent)
    if real_parent is None:
        real_parent = os.path.realpath(parent)
        if os.path.isdir(parent):
            if len(_PARENT_REALPATHS) >= _PARENT_REALPATH_LIMIT:
                _PARENT_REALPATHS.clear()
            _PARENT_REALPATHS[parent] = real_parent
    return os.path.join(real_parent, leaf)


def disposable_input(path) -> bool:
    if isinstance(path, int) or path is None:
        return False
    value = os.fsdecode(path)
    if value.startswith("file:"):
        from urllib.parse import unquote, urlsplit
        value = unquote(urlsplit(value).path)
        if os.name == 'nt' and value.startswith('/') and len(value) > 2 and value[2] == ':':
            value = value[1:]
    absolute = os.path.normcase(_resolved(value))
    return any(absolute == root or absolute.startswith(root + os.sep)
               for root in _disposable_roots)


def check_build_input(path) -> None:
    if disposable_input(path):
        raise FileNotFoundError(
            f"export input boundary: {path} is a disposable artifact; "
            "publish authenticated inputs inside the selected export/meta/evidence "
            "or regenerate builder-owned data under webui/data/_build"
        )


def _audit(event, args):
    if event == "open":
        path, mode, flags = args
        # Diagnostic writes (including atomic sibling .tmp files) are allowed.
        writing = (isinstance(mode, str) and any(token in mode for token in 'wax')) or (
            mode is None and (flags & (os.O_WRONLY | os.O_RDWR)) == os.O_WRONLY)
        if not writing or isinstance(mode, str) and '+' in mode:
            check_build_input(path)
    elif event in ("os.listdir", "os.scandir", "sqlite3.connect") and args:
        check_build_input(args[0])


def install_input_boundary() -> None:
    global _installed
    if not _installed:
        sys.addaudithook(_audit)
        _installed = True
