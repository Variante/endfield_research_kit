"""Package-safe access to shared script infrastructure.

Source-gap domain modules import this adapter instead of mutating ``sys.path``.
The fallback supports the maintained direct-script entry points while the
package migration is completed across the rest of ``scripts``.
"""
from __future__ import annotations

if __package__ == "scripts.story_builder.source_gap":
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
elif __package__ == "story_builder.source_gap":
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
else:  # pragma: no cover - invalid embedding identity
    raise ImportError(f"unsupported package identity: {__package__!r}")


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
