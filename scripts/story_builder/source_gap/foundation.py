"""Package-safe access to shared script infrastructure.

Source-gap domain modules import this adapter instead of mutating ``sys.path``.
The fallback supports the maintained direct-script entry points while the
package migration is completed across the rest of ``scripts``.
"""
from __future__ import annotations

try:
    from ...common import (
        combined_non_mission_content_keys,
        md_escape,
        non_mission_content_keys,
        read_json,
        resolve_installed_native_inputs,
        safe_key,
        sha256_file,
        write_report_json,
        write_text_if_changed,
    )
except ImportError:  # loaded as top-level ``story_builder`` from scripts/
    from common import (
        combined_non_mission_content_keys,
        md_escape,
        non_mission_content_keys,
        read_json,
        resolve_installed_native_inputs,
        safe_key,
        sha256_file,
        write_report_json,
        write_text_if_changed,
    )


__all__ = [
    "combined_non_mission_content_keys",
    "md_escape",
    "non_mission_content_keys",
    "read_json",
    "resolve_installed_native_inputs",
    "safe_key",
    "sha256_file",
    "write_report_json",
    "write_text_if_changed",
]
