"""Reprove named DynamicStreaming visibility controller paths offline.

The reviewed claims carry no build pin. The caller selects both installed
IL2CPP inputs and their expected hashes; the evaluator records current native
body identities and fails closed if any named field or call claim moves.

Run ``python -m scripts.game_data.dynamic_visibility_runtime_native
--gameassembly PATH --metadata PATH --expected-gameassembly-sha256 SHA256
--expected-metadata-sha256 SHA256``. It evaluates the build-independent field
and call claims in ``contracts/dynamic_visibility_runtime_claims.json``, in the
groups described below (scene state, conditions, MapConfig source, streaming
config and files, area selection and centers, portal destinations, placed
spawn and AOI), plus the selected enum defaults they read. A successful run
writes
``reports/animestudio/dynamic_visibility_runtime_claims_latest.json``; a failed
claim writes the separate pending-review
``dynamic_visibility_runtime_claims_failure_latest.json`` and leaves the
validated report untouched. The checks do not observe live controller
execution or condition results.

What the claims establish. Each claim states what a selected unpatched body
reads, writes, loads and calls. Every route below is direct but conditional:
cache hits, failed lookups, equal IDs, null systems, other branches and iFix
``IsPatched`` wrappers can take other paths. Simple read/call claims do not
prove full dataflow; the argument handoffs noted as inspected were read in
the selected disassembly and need reinspection when a body changes. No route
records which scene, file, state, area, portal or pipeline state was live.

Scene state to controllers. ``BaseGameScene.CalculateSceneStateMask`` reads
``sceneStates`` and the condition rows through ``m_mapConfig``, resolves each
row name in ``sceneStates``, shifts a mask bit by the index and branches on
the condition result. ``SetSceneState`` looks a supplied name up in the same
dictionary and updates mask and lists by its Boolean input, so a state
without a condition row still has a named update route. ``DoUpdateSceneState``
calls the calculation, then ``SetSceneStateMaskAndList``, which stores the
index list and passes that field to ``DynamicStreamingScene.SyncSceneStates``
(the calculation-to-setter list handoff was inspected). ``SyncSceneStates``
reads ``m_activeSceneStateIndices`` and calls the entity and resource
systems' ``UpdateStateIndex``, which call
``SceneVisibilityControllerBase.UpdateIndex`` on their typed state
controllers; ``InitSceneVisible`` in both systems calls the base
``InitActiveSet``. The area route runs through
``DynamicStreamingScene.OnAreaChanged`` and both systems' ``UpdateAreaId``.

Conditions. A state row stores a name and a ``ConditionRuntimeBase``;
``GetResult`` returns the cached Boolean while listening and otherwise
dispatches to ``GetResultWithoutListening``. ``CombinedConditionRuntime``
reads ``conditionOperator``, ``subConditions`` and ``reverse``, implements
``And``/``Or`` and optionally reverses (current authored combined rows have
paired children without reversal). Quest and mission leaves pass
``MissionSystem`` state with their stored operator and target to the
``Int32`` ``TableUtils.DoCompare``; a missing mission-data object follows the
``None`` state path. Map-variable leaves call
``MapVarSystem.TryGetMapVarInCurrentMap`` (which forwards ``m_curMapStr``);
global-variable leaves call ``GlobalVarSystem.TryGetClientVar``, not the
server getter. On success both convert the ``Int64`` value and integer target
to ``Single`` and call the ``Single`` comparer, whose equality branches use an
absolute tolerance of about ``1e-5``: not exact integer tests, and large
values can lose precision. A missing variable returns false after logging; it
does not compare a default zero. ``_RegisterSceneStateConditionChangeEvent``
walks the rows, and the four leaf types have quest, mission, map-variable and
client-global ``InnerStartListening`` paths.

MapConfig source. ``DataManager.MapConfigTable.TryGetData`` checks its typed
cache; on a miss it calls ``ResourceRouter.GetMapJsonConfigFullPath``
(``Data/Json/MapConfig/`` and ``.json`` literals, the exported JsonData path
family), the shared ``DataManager.LoadJson``, and caches a non-null result.
Enum claims recheck the compare and combined operators, quest and mission
states and ``AoiState`` members. The declared
value type is ``MapConfig``; the shared generic pointer alone names no
instantiation. Normal load: ``LoadBeginStep.DoPrepare`` gets a
``LevelConfig``, asks ``_TryLoadMapConfig`` for its map ID and stores the
result in ``m_mapConfig``; ``LoadSceneStep`` copies it to
``BaseGameScene.m_mapConfig`` when the map ID differs, unregisters old
listeners, reinitializes scene state and notifies the dynamic scene.
Seamless load: ``PrepareStep`` stores the table result and
``PreloadSceneStep`` passes it to ``TryChangeMapConfig``, which compares
``mapIdStr`` and on change unregisters listeners, replaces the config, calls
``_InitSceneState`` (listeners before ``DoUpdateSceneState``) and
``_OnMapConfigChanged``, forwarding to
``DynamicStreamingScene.OnMapConfigChanged``.

Streaming config and DynamicStreaming files. ``GameScene._ExtractSceneConfig``
reads ``streamingMapConfigPath`` through ``m_mapConfig``, builds the platform
path under ``Assets/Beyond/DynamicAssets/Scenes``, loads it and stores the
result in the typed ``BaseGameScene.streamingMapConfig``. The loader body is a
``System.Object`` instantiation, so the typed field and the original object
index (``dynamic_streaming_config_join``) supply the class.
``CreateDynamicStreamingScene`` passes ``get_mapSceneName`` to
``DynamicStreamingScene.InitScene``, which builds the DynamicStreaming root,
data-platform folder and ``Scene`` base path and passes it to
``DynamicDataLoader.SetBasePath`` and
``DynamicSceneVersionBanSet.LoadFromBasePath`` (``fb_version``, see
``dynamic_version_ban_native``); these argument-to-path handoffs were
inspected. ``SetBasePath`` initializes a ``DynamicSceneFbDataLoader`` and the
``fb_init``/``fb_streaming`` templates; ``Init`` uses an ``fb_main`` template
and ``GetPath`` fills it from a packed grid value (``dynamic_main_path_join``).
``GetGridData`` uses the ``DynamicSceneFbDataLoaderBase<UInt32,
FBDynamicSceneChunkData>`` instance and reads each chunk's grid vector and
``UniqueId``; ``AddChunkRef`` can call its ``TryLoadResource``
(``VirtualFileSystem.ReadFileByLowIO``), and the derived ``GetFbData`` reads
the handle as a FlatBuffer chunk and checks its data and streaming version
getters. A class-instantiation selector separates this body from the other
generic base instance.

Area selection and centers. ``GameSceneAreaDealer.InitData`` builds the
scene's ``FBStreamArea.bytes`` path (DynamicStreaming root, asset folder, map
scene name), reads it through VFS low IO into a typed
``FBStreamAreaTotalData``, builds a trigger quad tree and calls
``_BuildMapping``, which maps areas and triggers and inserts each indexed
``RootVisible`` value into ``m_activeAreaIds``; the indexed getter is an
unnamed clone of ``RootVisible(Int32)`` with the same field and stride.
``CreateStreamingScene`` calls ``FlushStreamingArea``, which tests each
``TotalAreas`` ID against that set and calls ``SetAreaEnable``: a nonzero area
goes to ``StreamingSceneV2.SetArea_Injected`` and ``OnAreaChanged``; zero
takes a default-area layer path. Regular-load centers come from
``SquadManager.ServerTeleportSquad(pos)`` through ``GameLevelLoader.LoadAtPos``
and ``LoadingPipeline.m_centerPos`` to ``BaseGameScene.SetStreamingCenter``;
seamless centers come from ``LoadingPortalComponent._OnInteract`` and
``SeamlessPortalComponent.StartLoading`` reading ``tpPosition`` into
``SeamlessLoadMap``, ``SeamlessLoadingPipeline.m_tpPos`` and the same setter.
The setter stores ``m_streamingCenter``, copies it to the dealer's
``m_mainCenter`` and requests a refresh; ``BaseGameScene.Update`` refreshes
when the squared distance to the last-checked center exceeds one, and
``ForceRefreshAreaMainCenter`` reuses the center. ``LoadExtraAtPos`` adds an
optional sub-center (``SetAreaSubCenter``, ``SetSubCenter``), and the
clear-extra-load path clears it. ``_UpdateIfNeeded`` copies ``m_mainCenter``
to ``m_lastCheckCenter``, gathers the centers and calls ``_UpdateActiveArea``,
which queries the tree through ``FBStreamingAreaHelper.CheckInArea``, reads
the selected areas' ``VisibleStart``/``VisibleNum`` slices, calls
``SetAreaEnable`` for changes and requests a chunk-grid refresh. The
``CheckInArea`` predicate is pinned by ``dynamic_stream_area_native``.

Portal destinations. Both portal component-data ``ApplyProperties`` bodies
bind the ``tp_position`` literal to a ``Vector3`` ``_TryAssign`` callback that
writes ``tpPosition``; each ``get_interactiveComponentType`` returns its
``LevelData.componentProperties`` key. After ``Entity.AssignLevelEntityData``,
``InteractiveRootComponent.OnLevelDataAssigned`` enumerates that map and loads
property rows into a component ``ParamBlackboard``. Both portal components
inherit through ``InteractiveCoreComponent`` from
``LogicComponentWithDynamicProperty<InteractiveCoreComponentData>``: its
``AssignData`` creates the component blackboard from template properties and
adds it to the entity blackboard, and ``InitSelf`` passes instance data and
blackboard to an unnamed helper that invokes the receiver's virtual slot,
the slot declared by ``DynamicPropertyComponentData.ApplyProperties`` and
both overrides. The shared code pointer is registered as ``System.Object``,
so the class hierarchy is checked separately. ``portal_center_join`` owns the
stored template/override relation.

Placed spawn and AOI. ``EntityManager.SpawnInLevelClientInteractive`` passes
the ``LevelInteractiveData`` returned by
``LevelData.TryGetInteractiveInLevelData`` through
``EntityDataStorage.CreateInteractiveFromLevelData`` and
``InteractiveInfo.InitFromLevelData`` to ``BaseEntityData.SetupInLevelData``;
``Commit`` can build an ``EntityNode``. ``_SpawnEntity`` passes the stored
``inLevelData`` through ``ObjectContainer.SpawnEntity`` and ``LoadEntity`` to
the placed-data ``EntityAllocator.AllocateObject``, which calls
``Entity.Construct``, positions the root, calls ``AssignLevelEntityData``,
then ``PreInit``; ``LoadEntity`` later calls ``Init``.
``EntityNode.get_dependencyGroupId`` reads the placed ID; with no group,
``SetInAoi(true)`` maps to ``AoiState.Intrested`` and ``SetAoiState`` can
launch the spawn pipeline (``_LaunchSpawnPipeline``,
``SwitchToNextPipelineState``, ``_EnterPipeline``; ``_SpawnNode`` also enters
it). ``AddToGroup`` assigns ``NotIntrested`` and an interested-group update
can assign ``Intrested``. ``GridProcessor._TryDoSetInAoi`` calls an unnamed
body with the same dependency check and state mapping; ``NodeGrid``
force-load and range-exit call it with true and false, and
``OnNodeSkipAoiCheck`` picks force-load when its runtime flag is set. The
authored ``forceLoad`` field is not proved to be that flag.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex, evaluate
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_visibility_runtime_claims.json"
SCHEMA = "endfield.dynamic-visibility-runtime-claims.v16"
FORMAT = "endfield.dynamic-visibility-runtime-claims-audit.v3"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/dynamic_visibility_runtime_claims_latest.json"
DEFAULT_FAILURE_OUTPUT = REPO_ROOT / "reports/animestudio/dynamic_visibility_runtime_claims_failure_latest.json"


class DynamicVisibilityRuntimeError(ValueError):
    """Selected inputs or reviewed claim contract cannot be evaluated."""


def audit(
    *, gameassembly: Path, metadata: Path,
    expected_gameassembly_sha256: str, expected_metadata_sha256: str,
) -> dict[str, Any]:
    contract, digest = read_reviewed_contract(
        CONTRACT, schema=SCHEMA, label="dynamic_visibility_runtime", status="validated",
    )
    methods = contract.get("methods")
    if not isinstance(methods, dict) or not methods:
        raise DynamicVisibilityRuntimeError("dynamic_visibility_runtime.contract:methods missing")
    enum_claims = contract.get("enumClaims")
    if not isinstance(enum_claims, dict) or not enum_claims:
        raise DynamicVisibilityRuntimeError("dynamic_visibility_runtime.contract:enumClaims missing")
    for name, expected in enum_claims.items():
        if not isinstance(name, str) or not isinstance(expected, dict) or not expected or any(
            not isinstance(member, str) or type(value) is not int
            for member, value in expected.items()
        ):
            raise DynamicVisibilityRuntimeError(
                f"dynamic_visibility_runtime.contract:invalid enum claim {name!r}"
            )
    gate = check_installed_native_inputs(
        expected_gameassembly_sha256, expected_metadata_sha256,
        gameassembly=gameassembly, metadata=metadata,
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicVisibilityRuntimeError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    image = open_native_image(gameassembly, metadata)
    rows, failures = evaluate(BodyIndex(image), methods)
    if len(rows) + len({failure["symbol"] for failure in failures if failure["claim"] == "resolve"}) != len(methods):
        raise DynamicVisibilityRuntimeError("dynamic_visibility_runtime:method row cardinality differs")
    defaults = field_defaults(image.metadata)
    enums = []
    for type_name, expected in enum_claims.items():
        try:
            members = native_enum_members(
                image.metadata, defaults, image.pe, image.registration, type_name,
            )
        except (RuntimeError, ValueError, KeyError, IndexError) as exc:
            failures.append({
                "symbol": type_name, "claim": "enumMembers", "reason": str(exc),
            })
            continue
        actual = {member["name"]: member["id"] for member in members}
        enums.append({"type": type_name, "members": members})
        if actual != expected:
            failures.append({
                "symbol": type_name,
                "claim": "enumMembers",
                "reason": f"expected={expected!r} actual={actual!r}",
            })
    return {
        "format": FORMAT,
        "status": "pendingReview" if failures else "validated",
        "contractSha256": digest,
        "nativeInputs": {
            "gameAssemblySha256": gate.gameassembly_sha256.upper(),
            "metadataSha256": gate.metadata_sha256.upper(),
        },
        "methods": rows,
        "enums": enums,
        "failures": failures,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--expected-gameassembly-sha256", required=True)
    parser.add_argument("--expected-metadata-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--failure-output", type=Path, default=DEFAULT_FAILURE_OUTPUT)
    args = parser.parse_args(argv)
    try:
        report = audit(
            gameassembly=args.gameassembly, metadata=args.metadata,
            expected_gameassembly_sha256=args.expected_gameassembly_sha256,
            expected_metadata_sha256=args.expected_metadata_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as exc:
        print(f"dynamic-visibility-runtime-native: {exc}", file=sys.stderr)
        return 1
    if report["status"] != "validated":
        args.failure_output.parent.mkdir(parents=True, exist_ok=True)
        args.failure_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for failure in report["failures"][:8]:
            print(
                "dynamic-visibility-runtime-native: "
                f"{failure['symbol']}: {failure['reason']}", file=sys.stderr,
            )
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DynamicStreaming visibility runtime claims passed: methods={len(report['methods'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
