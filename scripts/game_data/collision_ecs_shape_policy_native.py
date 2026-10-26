"""Authenticate ECS shape eligibility and the typed original body-flags getter.

Declarations are reviewed data. Validation supplies no live body mode, flags,
pair policy or solver-contact claim.
"""
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.collision_runtime_mesh_native import load_layout

SCHEMA='endfield.collision-ecs-shape-policy-native.v1'
CONTRACT=CONTRACTS_DIR/'collision_ecs_shape_policy_native.json'


def load(*,gameassembly,metadata,unityplayer):
    return load_layout(gameassembly=Path(gameassembly),metadata=Path(metadata),unityplayer=Path(unityplayer),
                       contract_path=CONTRACT,schema=SCHEMA,validator='collision_ecs_shape_policy_native')


def main(argv=None):
    import argparse,json
    from scripts.game_data.collision_runtime_mesh import _output_path
    from scripts.game_data.corpus_common import atomic_write_text
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv);root=args.game_root.resolve()
    if root.name=='Endfield_Data':root=root.parent
    contract,gate=load(gameassembly=root/'GameAssembly.dll',metadata=root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',unityplayer=root/'UnityPlayer.dll')
    result=dict(schema='endfield.collision-ecs-shape-policy-validation.v1',status=gate['status'],nativeGate=gate,
                representation=contract['representation'] if contract else None,
                evidenceBoundary=contract['evidenceBoundary'] if contract else None)
    output=_output_path(args.output);atomic_write_text(output,json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=gate['status'],detail=gate.get('detail'),diagnostics=gate['diagnostics'],output=str(output))))
    return int(contract is None)


if __name__=='__main__':raise SystemExit(main())
