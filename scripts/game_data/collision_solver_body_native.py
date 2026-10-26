"""Reprove named original physics-body activation claims on selected binaries.

Evidence and admission boundary
-------------------------------
Named compiled claims are direct conditional activation routes: destruction init
sets kinematic, break clears it and applies force, and kickable launch enables
simulation, wakes a present body and forces that frame's simulation. IFix, body
presence, budgets, scene/filter flags and eventual solving remain unresolved.

The tracked stored-source interpretation is a bombable breakable-box postmodel:
current Bundle prefab-root/TRS and reciprocal enabled non-trigger convex collider
joins accompany dormant Rigidbody positive mass, gravity and unfrozen constraints.
Missing production Rigidbody exports were a scope omission, not game absence.
Authenticated external MonoScript identity and the independent destructible
physics-settings prefix identify selected debris colliders; effect/curve tails
stay opaque. The full resource-path model join and exact detail-keyed Interactive
variant select that model and override the physics node to the authenticated Mono.
Authored defaults allow bomb damage but disable physical/interactive damage, with
no variant override; a freeze interval is requested. These structuralOnly stored
defaults and conditional compiled requests select a better activation control
than disappearing loot crates, without proving live damage policy or accessibility.
The Interactive format/union remains owned by memorypack.interactive; these claims
do not widen it. Runtime level overrides, changes and actual branch need observation.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import BodyIndex,evaluate
from scripts.repo_paths import REPO_ROOT

CONTRACT=CONTRACTS_DIR/'collision_solver_body_claims.json'
SCHEMA='endfield.collision-solver-body-claims.v1'


def audit(*,gameassembly,metadata,expected_gameassembly_sha256,expected_metadata_sha256):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,label='collision-solver-body')
    gate=check_installed_native_inputs(expected_gameassembly_sha256,expected_metadata_sha256,
        gameassembly=Path(gameassembly),metadata=Path(metadata))
    report=dict(schema=SCHEMA,status=gate.status,nativeInputs=dict(gameAssemblySha256=gate.gameassembly_sha256,
        metadataSha256=gate.metadata_sha256),methods=[],failures=[],evidenceBoundary=contract['evidenceBoundary'])
    if gate.status!='validated':
        report['failures']=[dict(check='installed_native_inputs',detail=gate.detail)];return report
    methods={}
    for group in contract['groups'].values():
        for symbol,spec in group['methods'].items():
            if symbol in methods:raise ValueError('duplicate body-activation claim:'+symbol)
            methods[symbol]=spec
    image=open_native_image(Path(gameassembly),Path(metadata))
    if (hashlib.sha256(image.pe.buf).hexdigest().lower()!=expected_gameassembly_sha256.lower() or
            hashlib.sha256(image.metadata.buf).hexdigest().lower()!=expected_metadata_sha256.lower()):
        raise ValueError('opened native images differ from the selected body-activation inputs')
    rows,failures=evaluate(BodyIndex(image),methods)
    if not failures and ({r['symbol'] for r in rows}!=set(methods) or len(rows)!=len(methods)):
        failures.append(dict(check='method_coverage',expected=len(methods),actual=len(rows)))
    after=check_installed_native_inputs(expected_gameassembly_sha256,expected_metadata_sha256,
        gameassembly=Path(gameassembly),metadata=Path(metadata))
    if after.status!='validated':
        report.update(status=after.status,methods=[],failures=[dict(check='installed_native_inputs_after',detail=after.detail)])
        return report
    report.update(status='pendingReview' if failures else 'validated',methods=rows,failures=failures)
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gameassembly',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--expected-gameassembly-sha256',required=True);p.add_argument('--expected-metadata-sha256',required=True)
    p.add_argument('--output',type=Path,default=REPO_ROOT/'reports/runtime_capture/collision/body-activation-claims.json')
    args=p.parse_args(argv)
    from scripts.game_data.collision_runtime_mesh import _output_path
    try:
        report=audit(gameassembly=args.gameassembly,metadata=args.metadata,
            expected_gameassembly_sha256=args.expected_gameassembly_sha256,expected_metadata_sha256=args.expected_metadata_sha256)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError) as error:
        report=dict(schema=SCHEMA,status='pendingReview',methods=[],failures=[dict(check='body_activation_claims',detail=str(error)[:1200])])
    atomic_write_text(_output_path(args.output),json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],methods=len(report['methods']),failures=report['failures'][:4])))
    return int(report['status']!='validated')


if __name__=='__main__':raise SystemExit(main())
