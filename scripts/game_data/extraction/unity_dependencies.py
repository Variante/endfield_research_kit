"""Selected-player serialized dependencies outside the two VFS layers."""
from pathlib import Path
from scripts.common import sha256_file

BUILTIN_FILES=('unity default resources','unity_builtin_extra')
MODEL_TYPES=frozenset(('Animator','GameObject'))


def builtin_files(game_root):
    return [path for name in BUILTIN_FILES if (path:=Path(game_root)/'Resources'/name).is_file()]


def builtin_inputs(game_root):
    return [dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha256_file(path)) for path in builtin_files(game_root)]


def files_for_source(input_root,source):
    root=Path(input_root).resolve()
    selected=next((p for p in (root,*root.parents) if p.name.casefold()==source.casefold()),None)
    return builtin_files(selected.parent) if selected is not None else []


def auxiliary_drift(records,game_root):
    """Bounded expected/actual diagnostics; never hash an unselected path."""
    if not isinstance(records,list):return {'status':'invalid','detail':'auxiliaryInputs must be a list'}
    allowed=(Path(game_root)/'Resources').resolve();failures=[];seen=set()
    for row in records:
        try:
            path=Path(row['path']).resolve()
            if (path.parent!=allowed or path.name not in BUILTIN_FILES or path in seen
                    or type(row.get('bytes'))!=int or row['bytes']<0
                    or not isinstance(row.get('sha256'),str) or len(row['sha256'])!=64):
                raise ValueError('invalid or unselected auxiliary input')
            seen.add(path)
            if not path.is_file():failures.append(dict(path=str(path),status='missing',expected=row));continue
            actual=dict(bytes=path.stat().st_size,sha256=sha256_file(path))
            if any(actual[k]!=row[k] for k in actual):failures.append(dict(path=str(path),status='mismatched',expected=row,actual=actual))
        except (KeyError,TypeError,ValueError,OSError) as error:
            failures.append(dict(status='invalid',detail=str(error)[:240]))
    return {'status':'stale','files':failures} if failures else {}
