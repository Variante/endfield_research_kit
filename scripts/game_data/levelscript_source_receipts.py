"""Current source-replay context: complete reader and matching StringPool receipts."""
import gzip,hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.memorypack.core import memorypack_union_header
from scripts.game_data.string_pool import export_string_pool

class SourceReader:
    def __init__(self,summary,export_root,native_inputs,*,game_root=None):
        if summary.get('status')!='complete':raise ValueError('levelscriptSource.summary:complete-corpus-required')
        self.files={};self.root=Path(export_root);self.game_root=Path(game_root) if game_root is not None else None;provenance=summary.get('provenance',{})
        self.pins=dict(native_inputs)
        if set(self.pins)=={'gameAssembly','metadata'} and all(isinstance(v,dict) and set(v)=={'sha256'} for v in self.pins.values()):self.pins={name:self.pins[key]['sha256'] for name,key in (('GameAssembly.dll','gameAssembly'),('global-metadata.dat','metadata'))}
        if set(self.pins) not in ({'GameAssembly.dll','global-metadata.dat'},{'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}):raise ValueError('levelscriptSource.nativeInputs:unsupported-pin-scope')
        self.reader_inputs=provenance.get('levelscriptReaderInputs');self.pool_inputs=provenance.get('levelscriptStringPoolInputs')
        self.check();self.strings=export_string_pool(self.root)

    def check(self):
        root=self.game_root;gate=check_installed_native_inputs(self.pins['GameAssembly.dll'],self.pins['global-metadata.dat'],gameassembly=root.parent/'GameAssembly.dll' if root else None,metadata=root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        if gate.status!='validated':raise ValueError('levelscriptSource.nativeInputs:status='+gate.status+':'+gate.detail)
        if 'UnityPlayer.dll' in self.pins:
            from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
            failed=check_unity_input(gate.gameassembly,self.pins)
            if failed:raise ValueError('levelscriptSource.nativeInputs:UnityPlayer.dll:'+str(failed)[:500])
        for label,expected,actual in (('readerInputs',self.reader_inputs,snapshot_complete_reader_inputs()),('stringPoolInputs',self.pool_inputs,snapshot_string_pool_inputs(self.root))):
            if not isinstance(expected,dict) or not isinstance(expected.get('files'),list):raise ValueError('levelscriptSource.'+label+':missing-current-corpus-receipt')
            if expected!=actual:
                change=reader_input_changes(expected,actual,limit=2);change.update(expectedRoot=expected.get('root'),actualRoot=actual.get('root'))
                raise ValueError('levelscriptSource.'+label+':root='+str(self.root)+':'+json.dumps(change,sort_keys=True)[:1500])

        for file,expected in self.files.items():
            try:actual=hashlib.sha256(file.read_bytes()).hexdigest().upper()
            except OSError as error:raise ValueError('levelscriptSource.source-file-unavailable:'+str(file)+':'+str(error)[:300]) from error
            if actual!=expected:raise ValueError('levelscriptSource.source-file-changed:'+str(file)+':expected='+expected+':actual='+actual)

    def cursor(self,data,offset,route,*,source_path):
        from scripts.game_data.codecs.levelscript.action_map import _Cursor
        file=(self.root/source_path).resolve()
        if not file.is_relative_to(self.root.resolve()):raise ValueError('levelscriptSource.outside-export-root:'+str(source_path))
        digest=hashlib.sha256(data).hexdigest().upper()
        if self.files.setdefault(file,digest)!=digest:raise ValueError('levelscriptSource.mixed-source-versions:'+str(source_path))
        return _Cursor(data,offset,game_root=self.game_root,strings=self.strings,route=route)


def replay_sources(contract,export_root,ledger_path,summary_path,*,game_root=None):
    """Replay declared spans after the owning validator proves their native routes."""
    summary_path,ledger_path=Path(summary_path),Path(ledger_path);summary_raw=summary_path.read_bytes();summary=json.loads(summary_raw);ledger_raw=ledger_path.read_bytes();output=summary.get('provenance',{}).get('outputFiles',{})
    actual_ledger=hashlib.sha256(ledger_raw).hexdigest().upper()
    if (summary.get('status'),output.get('length'),output.get('sha256','').upper())!=('complete',len(ledger_raw),actual_ledger):raise ValueError('levelscriptSource.summary-ledger-join:status='+str(summary.get('status'))+':expected='+str(output)+':actualLength='+str(len(ledger_raw))+':actualSha256='+actual_ledger)
    ledger={}
    for line in gzip.decompress(ledger_raw).decode('utf-8').splitlines():
        row=json.loads(line)
        if row.get('family')!='LevelScriptData':continue
        path=row['exportRelativePath']
        if path in ledger:raise ValueError('levelscriptSource.duplicate-ledger-row:'+path)
        ledger[path]=row
    if not ledger:raise ValueError('levelscriptSource.empty-LevelScriptData-ledger')
    source=SourceReader(summary,export_root,contract['nativeInputs'],game_root=game_root);root=Path(export_root).resolve();routes=contract.get('routes')
    if routes is None:routes=[contract['route']]
    count=0
    for route in routes:
        fields=route['fields'];members=route.get('serializedMemberCount',route.get('memberCount'))
        if type(members) is not int or members!=len(fields):raise ValueError('levelscriptSource.incomplete-reviewed-field-plan:'+str(route.get('wrapperName')))
        prefix=memorypack_union_header(route['tag'],members);receipts=route.get('sourceReceipts')
        if receipts is None:
            if len(routes)!=1:raise ValueError('levelscriptSource.per-route-receipts-required')
            receipts=contract['sourceReceipts']
        for receipt in receipts:
            if not isinstance(receipt,list) or len(receipt)!=5:raise ValueError('levelscriptSource.unsupported-receipt-shape')
            path,digest,start,end,span_digest=receipt;file=(root/path).resolve()
            if not file.is_relative_to(root):raise ValueError('levelscriptSource.outside-export-root:'+str(path))
            data=file.read_bytes();row=ledger.get(path,{})
            actual=hashlib.sha256(data).hexdigest().upper()
            if actual!=digest.upper() or row.get('logicalSha256','').upper()!=digest.upper() or row.get('length')!=len(data):raise ValueError('levelscriptSource.source-ledger-join:'+str(path)+':expected='+str(digest)+':actual='+actual+':ledgerSha256='+str(row.get('logicalSha256'))+':expectedLength='+str(row.get('length'))+':actualLength='+str(len(data)))
            if type(start) is not int or type(end) is not int or not 0<=start<end<=len(data):raise ValueError('levelscriptSource.span-bounds:'+str(path)+':expected=0<=start<end<='+str(len(data))+':actual='+str((start,end)))
            if data[start:start+len(prefix)]!=prefix:raise ValueError('levelscriptSource.union-prefix:'+str(path)+'@'+str(start)+':expected='+prefix.hex()+':actual='+data[start:start+len(prefix)].hex())
            actual_span=hashlib.sha256(data[start:end]).hexdigest().upper()
            if actual_span!=span_digest.upper():raise ValueError('levelscriptSource.span-hash:'+str(path)+'@'+str(start)+':expected='+str(span_digest)+':actual='+actual_span)
            cursor=source.cursor(data,start+len(prefix),route,source_path=path)
            for name,kind in fields:
                at=cursor.offset
                try:cursor.value(kind,'levelscriptSource.'+name)
                except (ValueError,IndexError) as error:raise ValueError('levelscriptSource.field:'+str(path)+'@'+str(at)+':wrapper='+str(route.get('wrapperName'))+':'+name+':expectedKind='+kind+':fileBytes='+str(len(data))+':sourceSha256='+actual+':'+str(error)[:800]) from error
            if cursor.offset!=end:raise ValueError('levelscriptSource.end-offset:'+str(path)+':expected='+str(end)+':actual='+str(cursor.offset))
            count+=1
    source.check()
    if summary_path.read_bytes()!=summary_raw or ledger_path.read_bytes()!=ledger_raw:raise ValueError('levelscriptSource.summary-or-ledger-changed-during-replay')
    return count
