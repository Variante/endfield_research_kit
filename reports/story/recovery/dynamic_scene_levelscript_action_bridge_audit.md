# DynamicScene to LevelScript Action Bridge Audit

## Result

- Story-bearing identity roots inspected: `72`
- Roots with an exact typed DynamicScene target action: `1`
- Roots sharing an exact LevelScript control path with Story: `1`
- Story occurrences on those shared paths: `1`
- Mission activation bridge found: `false`
- Mission graph action: `none`

## Exact bridge rows

| Scene | Logic id | Mission conditions | Typed action | Story on shared path | Classification |
| --- | ---: | --- | --- | --- | --- |
| map02 | 10100282001 | c27m3 != 3, c27m3_q#3 = 3 | ShowSceneDecorationNew@284 visible=false | dlg_c27m3_6 | exact_dynamic_scene_target_and_shared_levelscript_control_path |

## Evidence boundary

The target parameter is an authored `DynamicSceneEntityPtr`, so an admitted equality is a direct LevelScript-to-DynamicScene identity edge. When both actions share one serialized event/action path, the Story and decoration action also share exact local LevelScript control flow.

The DynamicScene `MissionControlComp` still controls the root's state/availability. No decoded field or runtime call yet proves that this mission condition starts the LevelScript event header. Therefore mission owner, Story binding, and order remain unresolved.

Promotion requirement: a typed serialized or runtime edge must show that the DynamicScene mission condition activates the matched LevelScript header/action chain
