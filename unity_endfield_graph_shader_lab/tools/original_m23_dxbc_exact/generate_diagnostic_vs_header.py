"""Embed the pinned diagnostic VS source for the native validator."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    # The generated source is deliberately a literal byte string: the native
    # compiler receives exactly the bytes whose hash is reported.
    escaped = ", ".join(f"0x{byte:02x}" for byte in source)
    args.output.write_text(
        "#pragma once\n"
        "static const unsigned char g_EndfieldM23DiagnosticVsSource[] = {"
        + escaped
        + "};\n"
        "static constexpr unsigned int g_EndfieldM23DiagnosticVsSourceSize = "
        + str(len(source))
        + ";\n"
        "static constexpr char g_EndfieldM23DiagnosticVsSourceSha256[] = \""
        + digest
        + "\";\n",
        encoding="ascii",
        newline="\n",
    )


if __name__ == "__main__":
    main()
