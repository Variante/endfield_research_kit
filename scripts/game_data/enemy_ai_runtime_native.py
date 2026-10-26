"""Reprove the enemy AI graph-selection, scheduling and task-to-skill claims.

Claims contract ``contracts/enemy_ai_runtime_claims.json`` names original
method bodies by type and method; ``il2cpp/body_claims.py`` re-proves them on
whichever explicitly selected ``GameAssembly.dll`` and ``global-metadata.dat``
the caller names, gated by ``check_installed_native_inputs`` before and after
evaluation.

What it proves (``direct``) when every claim holds:

- graph selection: ``EnemyAIComponent.OnStart`` -> ``EnemyAIBrain.InitData``
  (merged AI blackboard, then ``EnemyAIMode.InitData`` per mode) ->
  ``AIGraph.AssignData`` stores the mode data's virtual ``get_graph`` result in
  ``m_graph``; the battle, settlement and defend graph-data getters read the
  serialized ``canvasGraph``; ``EnemyAIGraph.LoadGraph`` passes ``m_graph`` to
  ``AIManager.GetAIGraphDataAsync``, which starts a NodeCanvas ``GraphOwner``;
- scheduling: ``SwitchAIMode`` exits then enters a mode, ``AIGraph.Enter``
  resets then starts its graph, and ``AITick`` -> ``EnemyAIBrain.Tick`` ->
  ``AIGraph.Tick`` updates a running graph;
- task to skill: ``CastSkill.OnExecute`` reads its ``skillId`` blackboard
  parameter and feeds the resolved string to ``AbilitySystem.TryCastSkill``'s
  ``skillId``, which looks the id up in the entity skill dictionary and reports
  a ``BATTLE_SKILL_START_CAST`` op; ``CastSeqSkill.OnExecute`` enters
  ``EnemyCommonCastSkill``, whose ``Enter`` copies the ``EnemyAISkillData``
  argument into inline ``m_skillData`` and ticks, and whose tick-reached
  ``_CastSkill`` passes ``m_skillData.skillID`` as ``TryCastSkill``'s id.

With the ``extend_data_graph_ai`` corpus join (AI config ``aiBB`` -> mode
``canvasGraph`` PPtr -> compressed BehaviourTree ordinal) this makes a decoded
graph's ``CastSkill.skillId`` literal, or the AI config blackboard's
``EnemyAISkillData.skillID`` bound to a ``CastSeqSkill.skillData`` variable, a
``conditional`` enemy skill input: it is cast only if that mode is entered,
the node is reached and the entity skill dictionary holds the id.

It does not prove which mode runs first, NodeCanvas node order, the virtual
dispatch site of ``LoadGraph``, which ``EnemyCommonCastSkill`` phase runs, the entity
skill dictionary contents, or server acceptance. The SpawnerConfig library
``enemyId`` -> ``SCENE_MONSTER`` template id join stays server-authoritative:
no client body writes the template id or reads ``subgameLibraryKey``.
A failed claim leaves the report ``pendingReview`` and its rows are not a
current conclusion; a ``missing``/``mismatched`` gate publishes no rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT

CONTRACT = CONTRACTS_DIR / "enemy_ai_runtime_claims.json"
SCHEMA = "endfield.enemy-ai-runtime-claims.v1"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/enemy_ai/enemy_ai_runtime_claims.json"


def contract_methods(contract):
    methods = {}
    for group, value in contract["groups"].items():
        for symbol, spec in value["methods"].items():
            if symbol in methods:
                raise ValueError("duplicate enemy-ai claim: " + symbol)
            methods[symbol] = dict(spec, group=group)
    return methods


def audit(*, gameassembly, metadata, expected_gameassembly_sha256, expected_metadata_sha256):
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="enemy-ai-runtime")
    gate = check_installed_native_inputs(
        expected_gameassembly_sha256, expected_metadata_sha256,
        gameassembly=Path(gameassembly), metadata=Path(metadata))
    report = dict(
        schema=SCHEMA, status=gate.status, contractSha256=digest,
        nativeInputs=dict(gameAssemblySha256=gate.gameassembly_sha256, metadataSha256=gate.metadata_sha256),
        methods=[], failures=[], evidenceBoundary=contract["evidenceBoundary"])
    if gate.status != "validated":
        report["failures"] = [dict(check="installed_native_inputs", detail=gate.detail)]
        return report
    methods = contract_methods(contract)
    image = open_native_image(Path(gameassembly), Path(metadata))
    if (hashlib.sha256(image.pe.buf).hexdigest().lower() != expected_gameassembly_sha256.lower()
            or hashlib.sha256(image.metadata.buf).hexdigest().lower() != expected_metadata_sha256.lower()):
        raise ValueError("opened native images differ from the selected enemy-ai inputs")
    rows, failures = evaluate(BodyIndex(image), {k: {f: v for f, v in s.items() if f != "group"} for k, s in methods.items()})
    for row in rows:
        row["group"] = methods.get(row.get("symbol"), {}).get("group")
    if not failures and ({r["symbol"] for r in rows} != set(methods) or len(rows) != len(methods)):
        failures.append(dict(check="method_coverage", expected=len(methods), actual=len(rows)))
    after = check_installed_native_inputs(
        expected_gameassembly_sha256, expected_metadata_sha256,
        gameassembly=Path(gameassembly), metadata=Path(metadata))
    if after.status != "validated":
        report.update(status=after.status, methods=[],
                      failures=[dict(check="installed_native_inputs_after", detail=after.detail)])
        return report
    report.update(status="pendingReview" if failures else "validated", methods=rows, failures=failures)
    return report


def _output_path(path):
    resolved = Path(path).resolve()
    if not any(resolved.is_relative_to(REPO_ROOT / name) for name in ("reports", "scratch", "tmp")):
        raise ValueError("generated output must be under reports/, scratch/ or tmp/")
    return resolved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--expected-gameassembly-sha256", required=True)
    parser.add_argument("--expected-metadata-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = _output_path(args.output)
    try:
        report = audit(gameassembly=args.gameassembly, metadata=args.metadata,
                       expected_gameassembly_sha256=args.expected_gameassembly_sha256,
                       expected_metadata_sha256=args.expected_metadata_sha256)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        report = dict(schema=SCHEMA, status="pendingReview", methods=[],
                      failures=[dict(check="enemy_ai_runtime_claims", detail=str(error)[:1200])])
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(output, json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(status=report["status"], methods=len(report["methods"]), failures=report["failures"][:6])))
    return int(report["status"] != "validated")


if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.enemy_ai_runtime_native")
if __name__ == "__main__":
    raise SystemExit(main())
