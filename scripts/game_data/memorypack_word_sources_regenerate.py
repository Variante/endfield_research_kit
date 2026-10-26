"""Regenerate explicitly named atomic unmanaged source contracts."""
import argparse
import json
from pathlib import Path

from scripts.game_data.buff_ec_profiles_regenerate import encoded
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.levelscript_two_routes_native import open_selected_build
from scripts.repo_paths import REPO_ROOT


def owner(component):
    if component=='gameplay-tag':
        from scripts.game_data.memorypack import buff_gameplay_tag_native
        return buff_gameplay_tag_native
    if component=='layer-mask':
        from scripts.game_data.memorypack import buff_layer_mask_native
        return buff_layer_mask_native
    raise ValueError('wordSource.unsupported-component:'+component)


def regenerate(component,*,write=False,candidate_dir=None,opener=open_selected_build):
    if candidate_dir is not None:
        candidate_dir=Path(candidate_dir).resolve()
        if not any(candidate_dir.is_relative_to((REPO_ROOT/root).resolve()) for root in ('reports','scratch','tmp')):
            raise ValueError('wordSource.candidate-dir:must-be-local-generated-root')
    module=owner(component);before=module.CONTRACT_PATH.read_bytes()
    image,inputs=opener();current=module.derive(image,inputs,json.loads(before))
    _publication_gate(image,inputs)
    if module.CONTRACT_PATH.read_bytes()!=before:raise ValueError('wordSource.publication:reviewed-input-changed')
    if write:module.CONTRACT_PATH.write_bytes(encoded(current))
    if candidate_dir is not None:
        candidate_dir.mkdir(parents=True,exist_ok=True);(candidate_dir/module.CONTRACT_PATH.name).write_bytes(encoded(current))
    return dict(status='regenerated',written=bool(write),contract=module.CONTRACT_PATH.name,
                typeName=current['typeName'],wireBytes=current['wireBytes'],resultRegister=current['resultRegister'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--component',choices=('gameplay-tag','layer-mask'),required=True)
    parser.add_argument('--write',action='store_true');parser.add_argument('--candidate-dir',type=Path)
    args=parser.parse_args(argv);print(json.dumps(regenerate(args.component,write=args.write,candidate_dir=args.candidate_dir),indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
