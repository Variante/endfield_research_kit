"""Complete Interactive owners from the selected authenticated export.

The source-only inventory closes extraction identity without supplying a
schema. Fresh native field/child proofs, the shared current ActionMap operation,
source id, byte partition and EOF close each owner independently. Publication
may use the exit receipt only after every selected source and all bookends pass.
"""
from contextlib import contextmanager,ExitStack
import gzip
import hashlib
import json
from pathlib import Path
import re

from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_source_inventory
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack.interactive_current_values import decode_current
from scripts.game_data.memorypack.levelscript_current_source import CurrentLevelScriptSource,require_current_owner
from scripts.source_paths import ExportLayout

PATTERN=re.compile(r'^Interactive/InteractiveData/[^/\\]+[.]json$')
SCHEMA='endfield.complete-interactive-operation.v1'


def need(check,condition,detail=''):
    if not condition:raise ValueError('completeInteractive.'+check+':'+str(detail)[:1800])


class _InteractiveReader:
    def __init__(self,layout,operation,graph,registry,rows):
        self.layout=layout;self.operation=operation;self.graph=graph;self.registry=registry;self.rows=rows
        self.files={};self.attempted=set();self.closed=set();self.active=True;self._receipt=None

    def __call__(self,path,data):
        need('active-selected-operation',self.active and self.graph.active and self.operation.active)
        path=Path(path)
        if not path.is_absolute():path=self.layout.json_dir/path
        path=path.resolve()
        try:key=path.relative_to(self.layout.json_dir.resolve()).as_posix()
        except ValueError as error:raise ValueError('completeInteractive.source-outside-selected-export:'+str(path))from error
        need('selected-owner-source',key in self.rows,key);row=self.rows[key]
        need('bytes-like-source',isinstance(data,(bytes,bytearray,memoryview)))
        data=bytes(data)
        actual=(len(data),hashlib.sha256(data).hexdigest().upper(),hashlib.md5(data).hexdigest().upper())
        expected=(row['length'],row['logicalSha256'].upper(),row['logicalMd5'].upper())
        need('authenticated-logical-source-bytes',actual==expected,(key,expected,actual))
        need('one-source-version',self.files.setdefault(path,data)==data,key)
        self.attempted.add(key)
        try:
            value,facts=decode_current(data,source=key,strings=self.operation.strings,graph=self.graph,
                registry=self.registry,action_owner=self.operation)
        except (ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:
            raise ValueError('completeInteractive.decode:'+json.dumps(dict(source=key,
                logicalSha256=row['logicalSha256'],errorType=type(error).__name__,detail=str(error)[:1800]),
                ensure_ascii=False))from error
        need('whole-named-owner',facts.get('wholeSchemaExact')is True and facts.get('physicalEOF')is True
            and facts.get('bytesConsumed')==len(data)and facts.get('sourceIdAndPhysicalEofProved')is True
            and isinstance(value,dict)and len(value)==26,key)
        self.closed.add(key)
        return dict(schemaStatus='named_exact',schemaMappingId=SCHEMA,serializedMemberCount=26,
            reader='scripts.game_data.memorypack.interactive_current_source',
            bytesConsumed=len(data),wholeSchemaExact=True,physicalEOF=True,fields=value,facts=facts,
            closedFields=list(value),openField=None,currentNativeRoot=True,
            runtimeActivationProved=False,playbackProved=False)

    @property
    def receipt(self):
        need('successful-complete-operation-exit',not self.active and self._receipt is not None)
        return self._receipt


@contextmanager
def complete_interactive_reader(export_root,*,game_root=None,gameassembly=None,metadata=None,action_operation=None):
    from scripts.common import resolve_installed_native_inputs,native_game_data_root
    layout=ExportLayout(Path(export_root).resolve()).require()
    need('both-explicit-native-paths',(gameassembly is None)==(metadata is None))
    if gameassembly is None:
        if game_root is None:
            gameassembly,metadata=resolve_installed_native_inputs(export_summary_path=layout.root/'meta/extraction/summary.json')
        else:
            selected=Path(game_root).resolve();gameassembly=selected.parent/'GameAssembly.dll'
            metadata=selected/'il2cpp_data/Metadata/global-metadata.dat'
    gameassembly,metadata=Path(gameassembly).resolve(),Path(metadata).resolve()
    selected=native_game_data_root(gameassembly=gameassembly,metadata=metadata)
    need('explicit-selected-root-and-pair-agree',game_root is None or selected==Path(game_root).resolve())
    directory=layout.evidence_dir/'animestudio';summary_path=directory/'jsondata_source_current.json'
    ledger_path=directory/'jsondata_source_files_current.jsonl.gz'
    before_readers=snapshot_complete_reader_inputs();summary_raw=summary_path.read_bytes()
    summary=json.loads(summary_raw)
    need('selected-source-inventory-root',Path(summary.get('exportRoot','')).resolve()==layout.root.resolve()
        and Path(summary.get('jsonRoot','')).resolve()==layout.json_dir.resolve())
    rows={}
    with gzip.open(ledger_path,'rt',encoding='utf-8')as stream:
        for line in stream:
            row=json.loads(line);key=row.get('exportRelativePath','')
            if not PATTERN.fullmatch(key):continue
            need('unique-source-identity',key not in rows,key);rows[key]=row
    need('nonempty-owner-universe',bool(rows))
    actual={p.resolve().relative_to(layout.json_dir.resolve()).as_posix()
        for p in (layout.json_dir/'Interactive/InteractiveData').glob('*.json')if p.is_file()}
    need('complete-physical-owner-roster',actual==set(rows),dict(
        missing=sorted(set(rows)-actual)[:4],extra=sorted(actual-set(rows))[:4]))
    decoder=None;owns_action_operation=action_operation is None
    with ExitStack()as stack:
        if owns_action_operation:
            operation=stack.enter_context(CurrentLevelScriptSource.from_source_inventory(layout.json_dir,
                gameassembly=gameassembly,metadata=metadata,summary_path=summary_path,ledger_path=ledger_path))
            operation.prepare_template()
        else:
            operation=action_operation;require_current_owner(operation,strings=operation.strings)
            need('same-active-selected-export',operation.root==layout.json_dir.resolve())
            need('same-active-selected-native-pair',Path(operation.proof['nativeSources']['GameAssembly.dll']).resolve()==gameassembly
                and Path(operation.proof['nativeSources']['global-metadata.dat']).resolve()==metadata)
            operation.require_template(strings=operation.strings)
        options=dict(summary_path=summary_path,ledger_path=ledger_path,
            expected_summary_sha256=hashlib.sha256(summary_raw).hexdigest().upper(),
            native_sources=operation.proof['nativeSources'],native_inputs=operation.proof['nativeInputs'])
        before=authenticate_current_jsondata_source_inventory(**options)
        need('authenticated-selected-json-root',Path(before['jsonRoot']).resolve()==layout.json_dir.resolve())
        graph,registry=operation.action_value_context()
        decoder=_InteractiveReader(layout,operation,graph,registry,rows)
        try:
            yield decoder
            need('all-selected-owners-attempted-and-closed',decoder.attempted==decoder.closed==set(rows),dict(
                universe=len(rows),attempted=len(decoder.attempted),closed=len(decoder.closed),
                unattempted=sorted(set(rows)-decoder.attempted)[:4],unclosed=sorted(set(rows)-decoder.closed)[:4]))
            for path,data in decoder.files.items():need('source-byte-exit-bookend',path.read_bytes()==data,str(path))
            after=authenticate_current_jsondata_source_inventory(**options)
            need('authenticated-source-exit-bookend',before==after and summary_path.read_bytes()==summary_raw)
            after_readers=snapshot_complete_reader_inputs()
            need('reader-source-exit-bookend',before_readers==after_readers,
                reader_input_changes(before_readers,after_readers))
            receipt=dict(schema=SCHEMA,status='validated-current-interactive-operation',
                nativeInputs=dict(operation.proof['nativeInputs']),nativeSources=dict(operation.proof['nativeSources']),
                sourceInventory=before,sourceUniverse=len(rows),sourcesAttempted=len(decoder.attempted),
                ownersClosed=len(decoder.closed),allSelectedOwnersClosed=True,
                sourceIdentitySetSha256=summary['summary']['identitySetSha256'],
                nativeConcreteSources=len(graph.records),nativeMemberBindings=len(graph.members),
                sourceReaderNativeBookendsPassed=True,sharedActionOperation=not owns_action_operation,
                runtimeActivationProved=False,playbackProved=False)
        finally:decoder.active=False
    if owns_action_operation:
        need('owned-action-native-source-pool-exit',operation.native_validation_reuse.get('entryExitBookendsPassed')is True)
    # A shared enclosing operation still owns its later native/pool exit. Its
    # publisher must retain that separate complete-reader exit receipt too.
    decoder._receipt=receipt
