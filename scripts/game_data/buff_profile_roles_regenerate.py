"""Regenerate explicitly reviewed named Buff profile-role contracts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.game_data.buff_ec_profiles_regenerate import encoded
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.levelscript_two_routes_native import open_selected_build
from scripts.repo_paths import REPO_ROOT


def owner(name):
    if name=='98':
        from scripts.game_data.memorypack import buff_98_roles_native
        return buff_98_roles_native
    if name=='23':
        from scripts.game_data.memorypack import buff_23_roles_native
        return buff_23_roles_native
    raise ValueError('buffProfileRoles.unsupported-role:'+name)


def regenerate(name,*,write=False,candidate_dir=None,opener=open_selected_build):
    if candidate_dir is not None:
        candidate_dir=Path(candidate_dir).resolve()
        if not any(candidate_dir.is_relative_to((REPO_ROOT/root).resolve()) for root in ('reports','scratch','tmp')):
            raise ValueError('buffProfileRoles.candidate-dir:must-be-local-generated-root')
    module=owner(name);paths=[module.CONTRACT_PATH,module.PROJECTION_PATH]
    original=[p.read_bytes() for p in paths]
    reviewed,projection=map(json.loads,original)
    image,inputs=opener();current,projected=module.derive(image,inputs,reviewed,projection)
    _publication_gate(image,inputs)
    if [p.read_bytes() for p in paths]!=original:
        raise ValueError('buffProfileRoles.publication:reviewed-inputs-changed-during-derivation')
    if write:
        for path,value in zip(paths,(current,projected)):path.write_bytes(encoded(value))
    if candidate_dir is not None:
        candidate_dir.mkdir(parents=True,exist_ok=True)
        for path,value in zip(paths,(current,projected)):(candidate_dir/path.name).write_bytes(encoded(value))
    return dict(status='regenerated',written=bool(write),roleContract=module.CONTRACT_PATH.name,
        projectionSchemaVersion=projected['schemaVersion'],codeWindows=len(projected['codeWindows']),
        profiles={p['profile']:len(p['events']) for p in current['proof']['profiles']})


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=('98','23'),required=True);parser.add_argument('--write',action='store_true')
    parser.add_argument('--candidate-dir',type=Path)
    args=parser.parse_args(argv)
    print(json.dumps(regenerate(args.role,write=args.write,candidate_dir=args.candidate_dir),indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
