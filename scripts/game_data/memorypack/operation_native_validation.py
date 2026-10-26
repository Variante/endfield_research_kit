"""Reuse successful native proofs only inside one freshly gated source scope.

Payload decoders never enter this helper. Outside the private lexical scope,
validators execute directly. Entry and exit gates run with reuse suspended.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import copy
import inspect
from pathlib import Path,PurePath,PosixPath,WindowsPath,PurePosixPath,PureWindowsPath
import struct
import sys


_CURRENT=ContextVar('levelscript_operation_native_validation',default=None)
_READER_CALL=ContextVar('levelscript_owned_validator_reader_call',default=None)
_PATH_TYPES={Path,PurePath,PosixPath,WindowsPath,PurePosixPath,PureWindowsPath}


class _Uncacheable(ValueError):pass


def _argument(value,active=None):
    """Preserve literal types, float bits, container order and complete values."""
    kind=type(value)
    if kind in(None.__class__,bool,int,str,bytes):return kind,value
    if kind is float:return kind,struct.pack('!d',value)
    if kind in _PATH_TYPES:return kind,str(value)
    if kind not in(dict,list,tuple,set,frozenset):raise _Uncacheable('argument-type')
    active=set()if active is None else active
    if id(value)in active or len(active)>128:raise _Uncacheable('cyclic-or-deep-argument')
    active.add(id(value))
    try:
        if kind is dict:return kind,tuple((_argument(k,active),_argument(v,active))for k,v in value.items())
        items=(_argument(v,active)for v in value)
        return kind,frozenset(items)if kind in(set,frozenset)else tuple(items)
    finally:active.remove(id(value))


def _selected_call(function,args,kwargs,scope):
    try:
        signature=inspect.signature(function);bound=signature.bind(*args,**kwargs).arguments
        supplied=dict(bound)
        for name,parameter in signature.parameters.items():
            if parameter.kind is inspect.Parameter.VAR_KEYWORD:supplied.update(bound.get(name,{}))
        ga=supplied.get('gameassembly');md=supplied.get('metadata',supplied.get('metadata_path'))
        root=supplied.get('game_root')
        if root is not None:
            root=Path(root).resolve()
            if(root.parent/'GameAssembly.dll',root/'il2cpp_data/Metadata/global-metadata.dat')!=scope.paths:return False
        if supplied.get('metadata_path')is not None and Path(supplied['metadata_path']).resolve()!=scope.paths[1]:return False
        if ga is not None or md is not None:
            return ga is not None and md is not None and(Path(ga).resolve(),Path(md).resolve())==scope.paths
        return root is not None
    except(TypeError,ValueError,OSError):return False


def _proof_identity(audit,scope):
    """A reported foreign identity never becomes an operation cache entry."""
    pins=audit.get('nativeInputs')
    if pins is not None:
        if not isinstance(pins,dict)or not pins:return False
        if set(pins)<={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:
            selected=pins
        elif set(pins)=={'gameAssembly','metadata'}and all(isinstance(v,dict)and set(v)=={'sha256'}for v in pins.values()):
            selected={name:pins[key]['sha256']for name,key in(('GameAssembly.dll','gameAssembly'),('global-metadata.dat','metadata'))}
        elif set(pins)=={'gameAssemblySha256','metadataSha256'}:
            selected={name:pins[key]for name,key in(('GameAssembly.dll','gameAssemblySha256'),('global-metadata.dat','metadataSha256'))}
        else:return False
        if not {'GameAssembly.dll','global-metadata.dat'}<=set(selected):return False
        if any(type(value)is not str or value.upper()!=scope.pins.get(name)for name,value in selected.items()):return False
    sources=audit.get('nativeSources')
    if sources is not None:
        try:
            if not isinstance(sources,dict)or set(sources)!={'GameAssembly.dll','global-metadata.dat'}:return False
            if tuple(Path(sources[name]).resolve()for name in('GameAssembly.dll','global-metadata.dat'))!=scope.paths:return False
        except(TypeError,ValueError,OSError):return False
    return True


class _ValidationScope:
    def __init__(self,gameassembly,metadata,native_inputs,reader_inputs=None):
        self.paths=Path(gameassembly).resolve(),Path(metadata).resolve()
        self.pins={key:value.upper()for key,value in native_inputs.items()}
        self.cache={};self.calls=self.hits=self.misses=self.entries=self.bypasses=0;self.closed=False
        # Only the enclosing public operation supplies its freshly captured
        # entry identity. Unsupported private/test scopes keep fresh scans.
        valid=(type(reader_inputs)is dict and reader_inputs.get('schema')=='endfield.levelscript-complete-reader-inputs.v1'
            and reader_inputs.get('scope')=='complete-raw-package-plus-external-reader-dependencies'
            and type(reader_inputs.get('files'))is list)
        self._reader_inputs=copy.deepcopy(reader_inputs)if valid else None
        self._reader_source_rows=None
        if valid:
            rows=reader_inputs['files']
            if all(type(row)is dict and type(row.get('path'))is str
                    and type(row.get('length'))is int and row['length']>=0
                    and type(row.get('sha256'))is str and len(row['sha256'])==64 for row in rows):
                selected={row['path']:(row['path'],row['length'],row['sha256'])for row in rows}
                if len(selected)==len(rows):self._reader_source_rows=selected
        self.reader_snapshot_copies=0

    def statistics(self):
        result=dict(calls=self.calls,hits=self.hits,misses=self.misses,entries=self.entries,
            bypasses=self.bypasses,closed=self.closed,entryExitBookendsPassed=False)
        if self.reader_snapshot_copies:
            result['readerSnapshotDelegation']=dict(copies=self.reader_snapshot_copies,
                freshOuterBookendsRequired=True,completedReceiptGranted=False)
        return result

    def close(self):
        self.cache.clear();self._reader_inputs=None;self._reader_source_rows=None;self.closed=True


@contextmanager
def _suspend_native_validation():
    token=_CURRENT.set(None)
    try:yield
    finally:_CURRENT.reset(token)


@contextmanager
def _native_validation_scope(*,gameassembly,metadata,native_inputs,reader_inputs=None):
    scope=_ValidationScope(gameassembly,metadata,native_inputs,reader_inputs);token=_CURRENT.set(scope)
    try:yield scope
    finally:
        scope.close();_CURRENT.reset(token)


def _invoke_selected(scope,function,args,kwargs):
    # The live parent frame is the authority for a direct validator snapshot.
    # A helper, recursive/direct/foreign call or copied context cannot borrow
    # it by merely inheriting a ContextVar or sharing the callable's code.
    invocation=[scope,getattr(function,'__code__',None),sys._getframe()]
    token=_READER_CALL.set(invocation)
    try:return function(*args,**kwargs)
    finally:
        _READER_CALL.reset(token)
        invocation.clear()  # do not retain a frame, arguments or code object


def _owned_reader_snapshot(fresh):
    """Delegate only a direct selected call; outer entry/exit always scan afresh."""
    invocation=_READER_CALL.get();scope=_CURRENT.get()
    if(type(invocation)is list and len(invocation)==3 and scope is invocation[0]
            and scope is not None and not scope.closed and scope._reader_inputs is not None):
        caller=sys._getframe(2)
        if caller.f_code is invocation[1] and caller.f_back is invocation[2]:
            scope.reader_snapshot_copies+=1
            return copy.deepcopy(scope._reader_inputs)
    return fresh()


def _owned_reader_source_inputs(paths):
    """Immutable declaration identities only inside a complete reader scope.

    A profile validator checks the actual bytes before publishing its selected
    native result. Private scopes without source bookends and foreign paths
    cannot reuse a declaration projection through this helper.
    """
    scope=_CURRENT.get()
    if scope is None or scope.closed or scope._reader_source_rows is None:return None
    try:
        selected=tuple(Path(path).resolve().as_posix()for path in paths)
        if not selected or len(set(selected))!=len(selected):return None
        return tuple(scope._reader_source_rows[path]for path in selected)
    except(KeyError,TypeError,ValueError,OSError):return None


def validate_native(function,*args,**kwargs):
    """Call a native validator; reuse only an exact successful selected call."""
    scope=_CURRENT.get()
    if scope is None or scope.closed:return function(*args,**kwargs)
    scope.calls+=1
    try:
        if not _selected_call(function,args,kwargs,scope):raise _Uncacheable('unselected-call')
        key=id(function),_argument(args),_argument(kwargs)
    except _Uncacheable:
        scope.bypasses+=1;return function(*args,**kwargs)
    cached=scope.cache.get(key)
    if cached is not None and cached[0]is function:
        scope.hits+=1;return copy.deepcopy(cached[1])
    scope.misses+=1
    result=_invoke_selected(scope,function,args,kwargs)
    # This is a pure-validator API; a call that changes its own arguments or
    # closes/replaces the lexical scope cannot publish a reusable result.
    try:unchanged=key==(id(function),_argument(args),_argument(kwargs))
    except _Uncacheable:unchanged=False
    if not unchanged or scope.closed or _CURRENT.get()is not scope:return result
    audit=result if isinstance(result,dict)else result[1]if type(result)is tuple and len(result)==2 and isinstance(result[1],dict)else None
    if not isinstance(audit,dict)or audit.get('status')!='validated'or not _proof_identity(audit,scope):return result
    try:stored=copy.deepcopy(result);returned=copy.deepcopy(stored)
    except Exception:
        scope.bypasses+=1;return result
    scope.cache[key]=function,stored;scope.entries+=1
    return returned
