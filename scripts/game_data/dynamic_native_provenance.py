"""World native direct contract inputs and publication provenance."""
import json
import inspect
from functools import wraps
from pathlib import Path
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data import dynamic_group_components_native as groups

def json_proof_snapshots(contract_path):
    contract_path=Path(contract_path).absolute();folder=contract_path.parent.resolve()
    own=_fingerprint(contract_path)
    try:contract=json.loads(contract_path.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:raise ValueError('world-json-proof-contract:'+str(exc)[:500]) from exc
    if not isinstance(contract,dict):raise ValueError('world-json-proof-contract-object')
    dependencies=contract.get('dependencies',[])
    if not isinstance(dependencies,list) or len(dependencies)>128:raise ValueError('world-json-proof-dependency-roster')
    paths=[Path(own['path'])]
    for dependency in dependencies:
        if not isinstance(dependency,dict) or not isinstance(dependency.get('path'),str):raise ValueError('world-json-proof-dependency-entry')
        name=dependency['path'];relative=Path(name)
        if not name or relative.is_absolute() or relative.suffix.lower()!='.json' or '..' in relative.parts:raise ValueError('world-json-proof-relative-json:'+name[:250])
        path=(folder/relative).resolve()
        if not path.is_relative_to(folder) or path in paths:raise ValueError('world-json-proof-path-or-duplicate:'+name[:250])
        paths.append(path)
    snapshots=[own]+[_fingerprint(path) for path in paths[1:]]
    groups._require_unchanged([own])
    return sorted(snapshots,key=lambda row:row['path'])

def require_json_proof_unchanged(contract_path,snapshots):
    # Re-discovery also checks physical resolved targets and dependency additions/removals.
    current=json_proof_snapshots(contract_path)
    if [r['path'] for r in current]!=[r['path'] for r in snapshots]:raise ValueError('world-json-proof-pathset-drift')
    groups._require_unchanged(snapshots)


def native_proof_snapshots(gameassembly,metadata,inputs):
    """Authenticate the exact explicit native triple supplied to a public API."""
    if not isinstance(inputs,(list,tuple)) or len(inputs)!=3 or any(not isinstance(row,dict) or not {'path','length','sha256'}.issubset(row) for row in inputs):
        raise ValueError('world-native-proof-input-manifest-shape')
    snapshots=[dict(row) for row in inputs]
    selected={Path(gameassembly).resolve(),Path(metadata).resolve(),(Path(gameassembly).parent/'UnityPlayer.dll').resolve()}
    recorded=[Path(row['path']).resolve() for row in snapshots]
    if len(selected)!=3 or len(set(recorded))!=3 or set(recorded)!=selected:
        raise ValueError('world-native-proof-selected-pathset:expected='+str(sorted(str(p) for p in selected))[:700]+' actual='+str(recorded)[:700])
    groups._require_unchanged(snapshots)
    return snapshots


def authenticate_native_proof(contract_path):
    """Gate direct native APIs too; CLI publication retains its wider interval."""
    def decorate(function):
        signature=inspect.signature(function)
        @wraps(function)
        def checked(*args,**kwargs):
            bound=signature.bind(*args,**kwargs).arguments
            path=contract_path()
            sources=json_proof_snapshots(path)
            supplied=bound['inputs']
            native_sources=native_proof_snapshots(bound['gameassembly'],bound['metadata'],supplied)
            result=function(*args,**kwargs)
            require_json_proof_unchanged(path,sources)
            native_proof_snapshots(bound['gameassembly'],bound['metadata'],native_sources)
            if list(supplied)!=native_sources:raise ValueError('world-native-proof-supplied-manifest-drift')
            return result
        return checked
    return decorate
