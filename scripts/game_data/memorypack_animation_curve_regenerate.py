"""Reprove the selected Unity AnimationCurve formatter and publish its contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.buff_ec_profiles_regenerate import encoded
from scripts.game_data.levelscript_two_routes_native import open_selected_build
from scripts.game_data.memorypack import animation_curve, animation_curve_source
from scripts.repo_paths import REPO_ROOT


def regenerate(*,write=False,candidate_dir=None,opener=open_selected_build):
    if candidate_dir is not None:
        candidate_dir=Path(candidate_dir).resolve()
        if not any(candidate_dir.is_relative_to((REPO_ROOT/root).resolve()) for root in ('reports','scratch','tmp')):
            raise ValueError('animationCurveSource.candidate-dir:must-be-local-generated-root')
    before=animation_curve.CONTRACT_PATH.read_bytes()
    image,inputs=opener()
    current=animation_curve_source.derive(image,inputs)
    _publication_gate(image,inputs)
    if animation_curve.CONTRACT_PATH.read_bytes()!=before:
        raise ValueError('animationCurveSource.publication:reviewed-input-changed-during-derivation')
    if write:animation_curve.CONTRACT_PATH.write_bytes(encoded(current))
    if candidate_dir is not None:
        candidate_dir.mkdir(parents=True,exist_ok=True)
        (candidate_dir/animation_curve.CONTRACT_PATH.name).write_bytes(encoded(current))
    return dict(status='regenerated',written=bool(write),sourceMethod=current['sourceMethod'],
                codeWindows=len(current['codeWindows']),keyframeBytes=current['keyframeBytes'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true');parser.add_argument('--candidate-dir',type=Path)
    args=parser.parse_args(argv)
    print(json.dumps(regenerate(write=args.write,candidate_dir=args.candidate_dir),indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
