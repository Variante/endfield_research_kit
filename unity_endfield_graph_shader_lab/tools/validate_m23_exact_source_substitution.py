#!/usr/bin/env python3
"""Join source identity, exact shader substitution, and DXCap draw outcome."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

SCHEMA = "endfield.lizhiyan-m23-exact-source-substitution-join.v1"

def validate(runtime: dict[str, Any], substitution: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    checks = []
    def add(name, passed, expected, actual):
        checks.append({"name": name, "passed": bool(passed), "expected": expected, "actual": actual})
    add("runtime.status", runtime.get("status") == "pass", "pass", runtime.get("status"))
    add("runtime.source_identity", runtime.get("exactIdentityClosed") is True, True, runtime.get("exactIdentityClosed"))
    add("runtime.no_proxy", runtime.get("noBakeMeshContract") is True and runtime.get("noProxyContract") is True, True, [runtime.get("noBakeMeshContract"), runtime.get("noProxyContract")])
    add("runtime.authored_streams", runtime.get("activeVertexStreamIds") == [0, 1, 3, 4, 5, 34], [0, 1, 3, 4, 5, 34], runtime.get("activeVertexStreamIds"))
    add("substitution.schema", substitution.get("schema") == "endfield.lizhiyan-m23-exact-source-substitution.v1", "endfield.lizhiyan-m23-exact-source-substitution.v1", substitution.get("schema"))
    add("substitution.shader_objects", substitution.get("status") == "pass" and substitution.get("callback_count") == 2 and substitution.get("shell_input_observed_count") == 2 and substitution.get("vertex_swap_count") == 1 and substitution.get("pixel_swap_count") == 1 and substitution.get("failure_count") == 0 and substitution.get("last_hresult") == 0, "two successful shell callbacks and one VS/PS replacement", substitution)
    draws = evidence.get("draw_calls") if isinstance(evidence.get("draw_calls"), list) else []
    target = [d for d in draws if d.get("parameters", {}).get("index_count") in (1728, 3456)]
    exact = [d for d in draws if d.get("m23_candidate", {}).get("exact_m23_candidate") is True]
    source_exact = []
    for draw in target:
        candidate = draw.get("m23_candidate", {})
        streams = draw.get("ia_vertex_buffers", [])
        stride0 = streams[0].get("stride") if streams else None
        if (candidate.get("variant") == "blob1277_non_instanced"
                and candidate.get("vs_bytecode_length") == 10720
                and candidate.get("ps_bytecode_length") == 8100
                and stride0 == 60):
            source_exact.append(draw)
    add("dxcap.single_target_draw", len(target) == 1, 1, len(target))
    add("dxcap.exact_shader_on_source_stride", len(source_exact) == 1, 1, len(source_exact))
    add("dxcap.no_stride136_claim", len(exact) == 0, 0, len(exact))
    add("dxcap.other_draw_present", len(draws) > 0, ">0", len(draws))
    failures = [c for c in checks if not c["passed"]]
    shader_closed = all(c["passed"] for c in checks if c["name"].startswith(("runtime.", "substitution.")))
    draw_admitted = len(source_exact) == 1
    return {"schema": SCHEMA, "status": "pass" if not failures else "fail", "checks": checks,
        "summary": {"checks": len(checks), "failures": len(failures), "firstFailure": failures[0]["name"] if failures else None},
        "classification": {"shaderObjectReplacementClosed": shader_closed, "automaticParticleRendererDrawAdmission": draw_admitted, "exactShaderAtSourceDraw": draw_admitted, "sourceIaStride": 60 if draw_admitted else None, "stride136ProducerResolved": False, "inputLayoutFailureDirectlyObserved": False, "retailShaderSelectionClaim": False},
        "interpretation": "the source-identity-preserving ParticleSystemRenderer submitted its 3456-index draw with substituted exact 0138/0139 shader objects while IA slot 0 remained the authored 60-byte stream; this closes shader-object admission but does not recover the retail 136-byte producer, missing blend-lane semantics, or retail shader selection"}

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("runtime",type=Path); p.add_argument("substitution",type=Path); p.add_argument("evidence",type=Path); p.add_argument("-o","--output",type=Path); a=p.parse_args()
    try: report=validate(*[json.loads(x.read_text(encoding="utf-8")) for x in (a.runtime,a.substitution,a.evidence)])
    except (OSError,UnicodeError,json.JSONDecodeError) as exc: report={"schema":SCHEMA,"status":"fail","summary":{"firstFailure":"input.read"},"error":str(exc)}
    payload=json.dumps(report,indent=2)+"\n"
    if a.output: a.output.write_text(payload,encoding="utf-8",newline="\n")
    else: print(payload,end="")
    return 0 if report["status"]=="pass" else 2
if __name__ == "__main__": raise SystemExit(main())
