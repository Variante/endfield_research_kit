"""One freshly proved current pooled NPC Patrol decode operation."""
import gzip,hashlib,json,sys
from pathlib import Path
from contextlib import contextmanager
from scripts.game_data import leveldata_npc_patrol_native as native
from scripts.game_data.codecs.leveldata.patrol import _decode_npc_patrol_list,NpcPatrolFramingError
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.string_pool import StringPool
from scripts.game_data.string_pool import export_string_pool
from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_receipt


@contextmanager
def npc_patrol_decoder(*,strings,game_root=None,gameassembly=None,metadata=None):
 if not isinstance(strings,StringPool):raise NpcPatrolFramingError('string-pool-required','npcPatrol',None,'matching StringPool',type(strings).__name__)
 sources=snapshot_complete_reader_inputs();pool=snapshot_string_pool_inputs(Path(strings.root).parent);strings=StringPool(strings.root)
 proof=native.validate(game_root=game_root,gameassembly=gameassembly,metadata=metadata)
 if proof.get('status')!='validated':raise NpcPatrolFramingError('native-enter','npcPatrol',None,'validated',proof)
 active=True
 def decode(data,offset):
  if not active:raise NpcPatrolFramingError('operation-closed','npcPatrol',offset)
  try:return _decode_npc_patrol_list(data,offset,strings=strings,layout=proof['layout'])
  except ValueError as error:
   if isinstance(error,NpcPatrolFramingError):error.diagnostic['sourceSha256']=hashlib.sha256(data).hexdigest().upper();raise
   raise NpcPatrolFramingError('value','npcPatrol',offset,'current pooled value',str(error))from error
 decode.native_sources=proof['nativeSources'];decode.native_inputs=proof['nativeInputs']
 try:yield decode
 finally:
  active=False;selected=proof['nativeSources'];after=native.validate(gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
  if after.get('status')!='validated':raise NpcPatrolFramingError('native-exit','npcPatrol',None,'validated',after)
  if(proof['layout'],proof['nativeInputs'],proof['nativeSources'])!=(after['layout'],after['nativeInputs'],after['nativeSources']):raise NpcPatrolFramingError('native-drift','npcPatrol',None)
  changed=snapshot_complete_reader_inputs()
  if sources!=changed:raise NpcPatrolFramingError('reader-source-drift','npcPatrol',None,'unchanged',reader_input_changes(sources,changed))
  if pool!=snapshot_string_pool_inputs(Path(strings.root).parent):raise NpcPatrolFramingError('string-pool-drift','npcPatrol',None,'unchanged')


class CurrentNpcPatrolSource:
 """Selected complete LevelData owners in one lexical native/source/pool scope."""
 def __init__(self,json_root,*,gameassembly,metadata,summary_path=Path('reports/animestudio/jsondata_current_latest.json'),ledger_path=Path('reports/animestudio/jsondata_current_files_latest.jsonl.gz')):
  self.root=Path(json_root).resolve();self.gameassembly=gameassembly;self.metadata=metadata;self.summary=Path(summary_path);self.ledger=Path(ledger_path);self.active=False
 def receipt(self):
  return authenticate_current_jsondata_receipt(summary_path=self.summary,ledger_path=self.ledger,expected_summary_sha256=self.summary_sha,native_sources=self.decode.native_sources,native_inputs=self.decode.native_inputs)
 def __enter__(self):
  if self.active:raise NpcPatrolFramingError('operation-active','npcPatrol',None)
  if self.gameassembly is None or self.metadata is None:raise NpcPatrolFramingError('explicit-native-pair-required','npcPatrol',None)
  self.strings=export_string_pool(self.root);self.scope=npc_patrol_decoder(strings=self.strings,gameassembly=self.gameassembly,metadata=self.metadata);self.decode=self.scope.__enter__()
  try:
   self.summary_raw=self.summary.read_bytes();self.summary_sha=hashlib.sha256(self.summary_raw).hexdigest().upper();self.before=self.receipt();self.files={};self.closed=set();self.rows={}
   with gzip.open(self.ledger,'rt',encoding='utf-8')as stream:
    for line in stream:
     row=json.loads(line);key=row.get('exportRelativePath','')
     if key.startswith(('LevelData/','StringPool/')):
      if key in self.rows:raise NpcPatrolFramingError('duplicate-logical-source',key,None)
      self.rows[key]=row
   pool=snapshot_string_pool_inputs(self.root)
   for row in pool['files']:
    path=Path(row['path']);self._join(path,path.read_bytes())
   self.game_root=Path(self.decode.native_sources['global-metadata.dat']).parents[2];self.universe={key for key in self.rows if key.startswith('LevelData/')};self.active=True;return self
  except BaseException:
   self.scope.__exit__(*sys.exc_info());raise
 def _join(self,path,data):
  key=Path(path).resolve().relative_to(self.root).as_posix();row=self.rows.get(key);actual=[len(data),hashlib.sha256(data).hexdigest().upper()]
  if row is None or actual!=[row['length'],row['logicalSha256'].upper()]:raise NpcPatrolFramingError('logical-source-byte-join',key,None,None if row is None else[row['length'],row['logicalSha256']],actual)
  return key
 def frame(self,path,data):
  if not self.active:raise NpcPatrolFramingError('operation-closed','npcPatrol',None)
  path=Path(path).resolve();key=self._join(path,data)
  if key not in self.universe:raise NpcPatrolFramingError('owner-family',key,None,'LevelData')
  if self.files.setdefault(path,data)!=data:raise NpcPatrolFramingError('mixed-source-versions',key,None)
  from scripts.game_data.leveldata_binary import frame_leveldata_named_prefix
  frame=frame_leveldata_named_prefix(data,strings=self.strings,game_root=self.game_root,patrol_decoder=self.decode)
  if(frame.get('schemaStatus'),frame.get('bytesConsumed'))!=('named_exact',len(data)):raise NpcPatrolFramingError('owning-eof-required',key,frame.get('bytesConsumed'),dict(schemaStatus='named_exact',bytesConsumed=len(data)),{k:frame.get(k)for k in('schemaStatus','bytesConsumed','openField')})
  self.closed.add(key);return frame
 def audit(self):
  if not self.active:raise NpcPatrolFramingError('operation-closed','npcPatrol',None)
  return dict(status='conditional-current-patrol-source',sourceUniverse=len(self.universe),sourcesAttempted=len(self.files),ownersClosed=len(self.closed),allSourcesAttempted=len(self.files)==len(self.universe),allOwnersClosed=len(self.closed)==len(self.universe),audioActionAbsenceProved=False,eventRequestsProved=False,summary=dict(path=str(self.summary),sha256=self.summary_sha))
 def __exit__(self,*error):
  try:
   if self.summary.read_bytes()!=self.summary_raw or self.before!=self.receipt():raise NpcPatrolFramingError('source-receipt-drift','npcPatrol',None)
   for path,raw in self.files.items():
    if path.read_bytes()!=raw:raise NpcPatrolFramingError('owner-source-drift',str(path),None)
  finally:
   self.active=False;self.scope.__exit__(*error)
