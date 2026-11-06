"""Prepare the Data page's classified Buff/Skill evidence in dependency order.

The selected native proof has no corpus dependency. Family censuses precede
the classified registry and action receipts; the source-only inventory never
stands in for any of these proofs. Every child inherits explicit selected paths.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from scripts.game_data.extraction.build_evidence import audit_paths, publish, read_json
from scripts.game_data import jsondata_corpus
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import corpus_gate, buff_selected_roots
from scripts.game_data.memorypack import current_family_evidence
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_receipt
from scripts.repo_paths import REPO_ROOT


def fingerprints(paths):
    return [corpus_gate._fingerprint(path) for path in sorted(set(map(Path, paths)))]


def implementation_paths():
    # Dynamic codec/contract dispatch is part of family admission. Enumerate
    # its full maintained source set so newly added declarations invalidate the
    # build cache as well as changed or deleted declarations.
    paths = set(corpus_gate._package_import_closure(Path(__file__)))
    paths.update(buff_selected_roots._contract_source_paths(list(paths)))
    paths.update(REPO_ROOT / "tools/endfield-il2cpp" / name for name in
                 ("map_body_targets_to_gameassembly.py", "catalog_option_flow_metadata.py"))
    return sorted(paths)


def launch(module, arguments, *, layout, game_root, cli):
    command = [sys.executable, "-m", module, *map(str, arguments)]
    environment = {**os.environ, "ENDFIELD_EXPORT_ROOT": str(layout.root),
                   "ENDFIELD_GAME_ROOT": str(game_root), "ENDFIELD_ANIMESTUDIO": str(cli),
                   "ENDFIELD_BUILD_INPUT_BOUNDARY": "1"}
    print("[build-evidence] " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, env=environment, cwd=REPO_ROOT, check=True)


def require_current_family_native(game_root):
    summary = {"primaryAssets": str(Path(game_root) / "Persistent")}
    gates = {name: jsondata_corpus._family_native_input_gate(name, summary)
             for name in ("BuffData", "SkillData")}
    for name, gate in gates.items():
        if gate["status"] != "validated":
            raise ValueError(f"{name}: required native evidence {gate['status']}: {gate['detail']}; "
                             f"contract={gate.get('source')}")
    return gates


def prepare(layout, game_root, cli, summary):
    root = layout.evidence_dir / "animestudio"
    outer, ledger = audit_paths(layout)
    gates = require_current_family_native(game_root)
    shared = [outer, ledger, root / "jsondata_source_current.json",
              root / "jsondata_source_files_current.jsonl.gz"]
    implementation = implementation_paths()
    declaration_paths = sorted(CONTRACTS_DIR.glob("*.json"))
    before = fingerprints([*implementation, *shared])
    state_path = root / "jsondata_build_cache.json"
    try:
        state = read_json(state_path)
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    expected = summary["inputSetSha256"]

    def current(path):
        report = read_json(path)
        if report.get("status") != "complete" or report.get("inputSetSha256") != expected:
            raise ValueError(f"{path}: expected a complete receipt for input set {expected}")
        return report

    def family(path, name):
        report = current(path)
        if (report.get('format') != current_family_evidence.FORMATS[name]
                or report.get('publicationEligible') is not True
                or report.get('wholeSchemaExact') is not False
                or report.get('sourceIdentityComplete') is not True
                or report['provenance']['readerInputs'] != snapshot_complete_reader_inputs()
                or Path(report['exportRoot']).resolve() != layout.root.resolve()
                or Path(report['gameRoot']).resolve() != game_root):
            raise ValueError(f'{name}: current native family receipt inputs differ')
        actual = corpus_gate._fingerprint(current_family_evidence.ledger_path(layout,name))
        if report.get('filesLedger') != actual:
            raise ValueError(f'{name}: current family row ledger differs')

    def stage(name, module, arguments, outputs, inputs, validate):
        signature = {"sources": before, "inputs": fingerprints(inputs),
                     "nativeGates": gates,
                     "gameRoot": str(game_root), "exportRoot": str(layout.root), "cli": str(cli),
                     "command": [module, *map(str, arguments)]}
        try:
            previous = state[name]
            if previous["signature"] == signature and previous["outputs"] == fingerprints(outputs):
                validate()
                print(f"[build-evidence] {name}: current", flush=True)
                return
        except (OSError, ValueError, KeyError, TypeError):
            pass
        launch(module, arguments, layout=layout, game_root=game_root, cli=cli)
        if (fingerprints([*implementation, *shared]) != before
                or fingerprints(inputs) != signature["inputs"]):
            raise ValueError(f"{name}: source inputs changed during generation")
        validate()
        state[name] = {"signature": signature, "outputs": fingerprints(outputs)}
        publish(state_path, state)

    base = ["--outer-summary", outer, "--outer-ledger", ledger,
            "--expected-input-set-sha256", expected]
    buff = root / "buffdata_current_latest.json"
    skill = root / "skilldata_current_latest.json"
    actions = root / 'buff_action_receipts_current_latest.json'

    def validate_actions():
        report = current(actions)
        if (report.get('schema') != 'endfield.buff-action-receipt-corpus.v9'
                or report.get('publicationEligible') is not True or report.get('wholeBuffDataExact') is not False
                or Path(report.get('exportRoot', '')).resolve() != layout.root.resolve()
                or report.get('buffReportSha256') != corpus_gate._fingerprint(buff)['sha256']):
            raise ValueError('Current Buff action receipt source/publication gates failed')

    def validate_families():
        family(buff, 'BuffData'); family(skill, 'SkillData'); validate_actions()

    stage('Current Buff/Skill roots', current_family_evidence.__name__,
        ['--game-root', game_root, '--export-root', layout.root],
        [buff, skill, actions, *(current_family_evidence.ledger_path(layout,name)
            for name in ('BuffData','SkillData'))], [], validate_families)

    registry = root / "jsondata_current_latest.json"
    registry_rows = root / "jsondata_current_files_latest.jsonl.gz"

    def validate_registry():
        report = current(registry)
        if Path(report["exportRoot"]).resolve() != layout.json_dir.resolve():
            raise ValueError("classified registry does not name the selected exported Json directory")
        native = {"GameAssembly.dll": game_root.parent / "GameAssembly.dll",
                  "global-metadata.dat": game_root / "il2cpp_data/Metadata/global-metadata.dat"}
        authenticate_current_jsondata_receipt(summary_path=registry, ledger_path=registry_rows,
            expected_summary_sha256=corpus_gate._fingerprint(registry)["sha256"],
            native_sources={name: str(path) for name, path in native.items()},
            native_inputs={name: corpus_gate._fingerprint(path)["sha256"] for name, path in native.items()})
        for name, path in (("BuffData", buff), ("SkillData", skill)):
            if gates[name]["status"] != "validated":
                if name in report["provenance"]["familyReports"]:
                    raise ValueError(f"classified registry admitted unavailable {name}")
                continue
            pin = report["provenance"]["familyReports"][name]
            actual = corpus_gate._fingerprint(path)
            if any(pin.get(key) != actual[key] for key in ("path", "length", "sha256")):
                raise ValueError(f"classified registry: {name} report pin differs")

    stage("JsonData registry", "scripts.game_data.jsondata_corpus",
          [*base, "--export-root", layout.json_dir, "--buff-report", buff, "--skill-report", skill,
           "--output-json", registry, "--output-files", registry_rows,
           "--output-md", registry.with_suffix(".md"), "--progress"],
          [registry, registry_rows, registry.with_suffix(".md")],
          [path for name, path in (("BuffData", buff), ("SkillData", skill))
           if gates[name]["status"] == "validated"], validate_registry)
    # Changed imports are detected by their importing source's hash; a newly
    # added dispatcher declaration is detected by the directory path set.
    # Avoid parsing the entire import graph a second time just for this check.
    if (sorted(CONTRACTS_DIR.glob("*.json")) != declaration_paths
            or fingerprints([*implementation, *shared]) != before):
        raise ValueError("JsonData evidence implementation or source set changed during generation")
    publish(root / "jsondata_build_status.json", {"inputSetSha256": expected, "nativeGates": gates,
        "registry": str(registry), "status": "complete" if all(
            gate["status"] == "validated" for gate in gates.values()) else "native-evidence-unavailable"})
