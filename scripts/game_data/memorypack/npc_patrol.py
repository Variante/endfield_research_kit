"""One freshly proved current pooled NPC Patrol decode operation."""
import hashlib
from pathlib import Path
from scripts.source_paths import ExportLayout
from contextlib import contextmanager
from scripts.game_data import leveldata_npc_patrol_native as native
from scripts.game_data.codecs.leveldata.patrol import _decode_npc_patrol_list,NpcPatrolFramingError
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.string_pool import StringPool
from scripts.game_data.memorypack.levelscript_current_source import CurrentLevelScriptSource


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
 """Current pooled Patrol projection of the shared whole LevelData operation."""
 def __init__(self,json_root,*,gameassembly,metadata,summary_path=None,ledger_path=None):
  self.root=Path(json_root).resolve();self.gameassembly=gameassembly;self.metadata=metadata
  if summary_path is None or ledger_path is None:
   layout=ExportLayout(self.root.parent.parent)
   if self.root!=layout.json_dir.resolve():
    raise NpcPatrolFramingError('selected-json-root-required',str(self.root),None,'<export>/game/Json')
   evidence=layout.evidence_dir/'animestudio'
   if summary_path is None:summary_path=evidence/'jsondata_source_current.json'
   if ledger_path is None:ledger_path=evidence/'jsondata_source_files_current.jsonl.gz'
  self.summary=Path(summary_path);self.ledger=Path(ledger_path);self.active=False;self._audit=None
 def __enter__(self):
  if self.active:raise NpcPatrolFramingError('operation-active','npcPatrol',None)
  if self.gameassembly is None or self.metadata is None:raise NpcPatrolFramingError('explicit-native-pair-required','npcPatrol',None)
  self._audit=None
  self.scope=CurrentLevelScriptSource.from_receipt(self.root,gameassembly=self.gameassembly,metadata=self.metadata,
   summary_path=self.summary,ledger_path=self.ledger)
  self.owner=self.scope.__enter__();self.strings=self.owner.strings;self.game_root=self.owner.game_root
  self.active=True;return self
 def frame(self,path,data):
  if not self.active:raise NpcPatrolFramingError('operation-closed','npcPatrol',None)
  framed=self.owner.frame_leveldata(path,data)
  if(framed.get('schemaStatus'),framed.get('serializedMemberCount'),framed.get('bytesConsumed'))!=('named_exact',43,len(data)):
   raise NpcPatrolFramingError('owning-eof-required',str(path),framed.get('bytesConsumed'),
    dict(schemaStatus='named_exact',serializedMemberCount=43,bytesConsumed=len(data)),
    {k:framed.get(k)for k in('schemaStatus','serializedMemberCount','bytesConsumed')})
  # Preserve the Patrol consumer's named field view while keeping all ranges
  # from the one authenticated 43-field source cursor.
  return dict(framed,fields={name:row['value']for name,row in framed['fields'].items()},
   fieldRanges={name:dict(startOffset=row['startOffset'],endOffset=row['endOffset'])for name,row in framed['fields'].items()})
 def audit(self):
  if not self.active:raise NpcPatrolFramingError('operation-closed','npcPatrol',None)
  audit=self.owner.audit()
  self._audit=dict(audit['leveldata'],status='conditional-current-patrol-source',
   audioActionAbsenceProved=False,eventRequestsProved=False,summary=audit['summary'],
   sourceInventoryAuthenticated=audit.get('sourceInventoryAuthenticated',False),
   nativeSourcePoolExitBookendsPassed=False)
  return self._audit
 def __exit__(self,*error):
  try:
   result=self.scope.__exit__(*error)
   if (not error or error[0]is None)and self._audit is not None:
    reuse=self.owner.native_validation_reuse
    if reuse.get('entryExitBookendsPassed')is not True:
     raise NpcPatrolFramingError('native-exit-bookends-required','npcPatrol',None)
    self._audit.update(nativeSourcePoolExitBookendsPassed=True,nativeValidationReuse=dict(reuse))
   return result
  finally:
   self.active=False
