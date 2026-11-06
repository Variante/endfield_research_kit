"""Maintained Endfield WebUI build and recovery tools."""
import os

if os.environ.get("ENDFIELD_BUILD_INPUT_BOUNDARY") == "1":
    from scripts.build_inputs import install_input_boundary
    install_input_boundary()
