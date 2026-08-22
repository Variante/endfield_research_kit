"""Static opt-in contract for the non-exact Endminf LitEffect visual path."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMPORTER = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfOverviewEffectImporter.cs"
SHADER = ROOT / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Shaders/Recovered/EndfieldEndminfLitEffectVisualCompatibility.shader"
OUT = ROOT / "reports/assets/endminf_liteffect_visual_compatibility.json"

def main() -> int:
    importer = IMPORTER.read_text(encoding="utf-8")
    shader = SHADER.read_text(encoding="utf-8")
    required_importer = [
        'ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT',
        '0x5A6341E8A834E421L', '0xAFCE491DD7BC5724UL',
        'LitEffectShaderPathId = 6428594484694422749L',
        'keywords.SequenceEqual(new[] { "_PARALLAX_MAP" })',
        'L.Int(row, "m_CustomRenderQueue") == 2000',
    ]
    required_shader = [
        'Hidden/Endfield/Compatibility/Endminf/LitEffectM01M38',
        'VISUAL COMPATIBILITY ONLY', '"LightMode"="ForwardOnly"',
        '_BaseColorMap', '_MROMap', '_NormalMap', '_ParallaxMap', '_ParallaxColor',
    ]
    failures = ["importer missing " + value for value in required_importer if value not in importer]
    failures += ["shader missing " + value for value in required_shader if value not in shader]
    report = {
        "schema": "endfield.endminf-liteffect-visual-compatibility.v1",
        "status": "verified_non_exact" if not failures else "failed",
        "classification": "visual_compatibility_not_source_exact",
        "defaultMode": "disabled_fail_closed",
        "optInEnvironment": "ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1",
        "scope": {"shaderPathId": 6428594484694422749,
                  "materials": ["M_fx_endminm_gfx_01", "M_fx_endminm_gfx_38"],
                  "expectedRendererCount": 10},
        "sourceInputsUsed": ["material identities", "_PARALLAX_MAP keyword", "queue 2000",
                             "recovered texture identities", "serialized colors/floats"],
        "approximated": ["converted PNG texture derivatives where native payloads are absent",
                         "forward lighting", "emission scale", "HGBuffer/deferred replacement"],
        "failures": failures,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["status"], OUT)
    return 1 if failures else 0

if __name__ == "__main__": raise SystemExit(main())
