"""One freshly proved current pooled NPC operation, with late refusal on drift."""
from contextlib import contextmanager
from pathlib import Path
import hashlib,struct
from scripts.game_data import npc_runtime_native as native
from scripts.game_data.codecs.leveldata.npc_runtime import _Reader,LevelNpcCodecError
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.string_pool import StringPool


@contextmanager
def npc_runtime_decoder(*,strings,game_root=None,gameassembly=None,metadata=None):
    if not isinstance(strings,StringPool):raise LevelNpcCodecError('matching-StringPool-required',None,'StringPool',type(strings).__name__)
    sources=snapshot_complete_reader_inputs();pool=snapshot_string_pool_inputs(Path(strings.root).parent);strings=StringPool(strings.root)
    proof=native.validate(game_root=game_root,gameassembly=gameassembly,metadata=metadata)
    if proof.get('status')!='validated':raise LevelNpcCodecError('native-enter',None,'validated',proof)
    reader=_Reader(strings,proof['layout']);active=True
    def decode(data,offset,index=0):
        if not active:raise LevelNpcCodecError('operation-closed',offset)
        try:return reader.row(data,offset,index)
        except LevelNpcCodecError as error:error.diagnostic['sourceSha256']=hashlib.sha256(data).hexdigest().upper();raise
    def count(data,offset,kind):
        if not active:raise LevelNpcCodecError('operation-closed',offset)
        if kind not in proof['layout']['containerKinds']:raise LevelNpcCodecError('container-source-unproved',offset,None,kind)
        value,end=reader.number(data,offset,kind+'.count',lambda b,o:(struct.unpack_from('<i',b,o)[0],o+4)if 0<=o<=len(b)-4 else None)
        if value < -1 or value>len(data)-end:raise LevelNpcCodecError(kind+'.count',offset,'-1 or bounded nonnegative count',value)
        return value,end
    def collection(data,offset):
        start=offset;n,offset=count(data,offset,'list');rows=[]
        for i in range(max(0,n)):
            row,offset=decode(data,offset,i);rows.append(row)
        return dict(startOffset=start,endOffset=offset,count=n,value=None if n==-1 else rows,rows=rows,memberPartition=proof['layout']['memberPartition'],evidenceBoundary='Conditional current pooled NPC source; authored values, not observed runtime spawning.')
    def dictionary(data,offset,*,key_wire):
        start=offset;n,offset=count(data,offset,key_wire+'-dictionary');entries=[];seen=set()
        try:
            for i in range(max(0,n)):
                key_at=offset
                if key_wire=='pool':key,offset=reader.string(data,offset,f'npcs[{i}].key')
                elif key_wire=='uint':key,offset=reader.number(data,offset,f'npcs[{i}].key',lambda b,o:(struct.unpack_from('<I',b,o)[0],o+4)if 0<=o<=len(b)-4 else None)
                else:raise LevelNpcCodecError('dictionary-key-wire',offset,None,key_wire)
                if key is None or key in seen:raise LevelNpcCodecError('npc-dictionary-key',key_at,'nonnull unique key',key)
                seen.add(key)
                row,offset=decode(data,offset,i)
                entries.append(dict(key=key,keyOffset=key_at,valueOffset=row['startOffset'],value=row))
        except LevelNpcCodecError as error:error.partial_entries=entries;error.entry_count=n;raise
        return dict(startOffset=start,endOffset=offset,count=n,entries=None if n==-1 else entries,status='null'if n==-1 else'present'),offset
    decode.collection=collection;decode.dictionary=dictionary;decode.pool_root=Path(strings.root).resolve();decode.native_inputs=proof['nativeInputs'];decode.native_sources=proof['nativeSources']
    try:yield decode
    finally:
        active=False;selected=proof['nativeSources'];after=native.validate(gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
        if after.get('status')!='validated':raise LevelNpcCodecError('native-exit',None,'validated',after)
        if(proof['layout'],proof['nativeInputs'],proof['nativeSources'])!=(after['layout'],after['nativeInputs'],after['nativeSources']):raise LevelNpcCodecError('native-drift')
        changed=snapshot_complete_reader_inputs()
        if sources!=changed:raise LevelNpcCodecError('reader-source-drift',None,'unchanged',reader_input_changes(sources,changed))
        if pool!=snapshot_string_pool_inputs(Path(strings.root).parent):raise LevelNpcCodecError('string-pool-drift')


def require_selected_decoder(decode,*,strings,game_root=None,gameassembly=None,metadata=None):
    if not isinstance(strings,StringPool)or Path(strings.root).resolve()!=Path(decode.pool_root).resolve():raise LevelNpcCodecError('selected-pool-root')
    if(gameassembly is None)!=(metadata is None):raise LevelNpcCodecError('both-native-paths-required')
    root=Path(game_root)if game_root is not None else None
    selected={name:Path(path).resolve()for name,path in(('GameAssembly.dll',gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None),('global-metadata.dat',metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None))if path is not None}
    if any(Path(decode.native_sources[name]).resolve()!=path for name,path in selected.items()):raise LevelNpcCodecError('selected-native-root')
    return decode
