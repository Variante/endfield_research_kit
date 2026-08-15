# Endminm playable Viewer prefab repair

Date: 2026-08-15

The playable catalog, exact manifest, meshes, materials, and 24 UI clips were
present, but `Generated/Characters/Playable/Endminm/Prefabs/Endminm.prefab`
was absent. The first fail-closed rebuild identified the missing source input:
no installed `FacialMorph/Avatar/Boy/endminm` object existed in the maintained
MonoBehaviour JSON export.

A broad isolated AnimeStudio MonoBehaviour load with the logical name produced
zero rows. The actual Unity object-name convention was recovered from the
existing Zhuang Fanyi sample and verified by a second broad load:

```text
logical key: FacialMorph/Avatar/Boy/endminm
Unity object: data_facemorph_avatar_endminm
exported JSON: data_facemorph_avatar_endminm_pA1EFF8302DF1AA49.json
SHA-256: 475CB9D22EE4278E95D1B77DB81421D9BED2237038990DEA44C58095166461A6
```

After publishing that exact generated input to the maintained MonoBehaviour
export root, the single-character builder produced Endminm with 11 skinned
meshes, 410 transforms, and 24 clips. The full native Overview verifier now
passes `actors=31`, `prefabs=31`, `fixed=4`, `normalized=27`, and
`widgetStates=636`; the former 30/31 prefab gate is closed.

The maintained narrow repair entry point is
`EndfieldEndminmPrefabRepair.BuildAndValidate`. It does not broaden to other
actors and still fails closed if the facial Avatar source is missing.
