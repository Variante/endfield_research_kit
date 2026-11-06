"""Selected-native complete CharInteract operation and independent sparse readers."""
from contextlib import contextmanager
from pathlib import Path

from scripts.common import canonical_json_sha256, resolve_installed_native_inputs
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs, snapshot_string_pool_inputs
from scripts.game_data.memorypack.char_perform_sparse import frame,SparsePerformDecodeError
from scripts.game_data.char_interact_perform_sparse_native import validate

class CharInteractPerformDecodeError(ValueError):pass


class _CompletePerformReader:
 def __init__(self,operation):self.operation=operation
 def __call__(self,data,*,prefix=False):
  if type(prefix)is not bool or prefix:
   raise CharInteractPerformDecodeError('CharInteract complete operation requires a whole root; prefix admission is disabled')
  try:
   result=self.operation.char_interact(data)
   if(result.get('wholeSchemaExact')is not True or result.get('physicalEOF')is not True
      or result.get('serializedMemberCount')!=28 or len(result.get('fields',[]))!=28
      or result.get('bytesConsumed')!=len(data)):
    raise CharInteractPerformDecodeError('CharInteract complete operation: incomplete root or physical EOF')
   return result
  except ValueError as error:raise CharInteractPerformDecodeError(str(error))from error
 @property
 def receipt(self):return self.operation.receipt


@contextmanager
def complete_perform_reader(*,game_root=None,gameassembly=None,metadata=None,strings=None):
 """Prove the whole current graph once; retain values only after successful exit.

 A configured pair is authoritative. Its canonical selected root must agree
 with an explicit root, and neither a missing pair nor an unavailable grammar
 falls back to another installation or the sparse reader.
 """
 from scripts.game_data.animation_current_native import current_animation
 if(gameassembly is None)!=(metadata is None):
  raise CharInteractPerformDecodeError('CharInteract complete operation: both native paths required')
 if gameassembly is None:
  if game_root is None:gameassembly,metadata=resolve_installed_native_inputs()
  else:
   selected=Path(game_root).resolve();gameassembly=selected.parent/'GameAssembly.dll';metadata=selected/'il2cpp_data/Metadata/global-metadata.dat'
 ga,md=Path(gameassembly).resolve(),Path(metadata).resolve()
 selected=Path(game_root).resolve()if game_root is not None else md.parents[2]
 if ga!=selected.parent/'GameAssembly.dll'or md!=selected/'il2cpp_data/Metadata/global-metadata.dat':
  raise CharInteractPerformDecodeError('CharInteract complete operation: explicit root/native pair disagree')
 try:
  with current_animation(game_root=selected,strings=strings,families=('char-interact',))as operation:
   yield _CompletePerformReader(operation)
 except ValueError as error:raise CharInteractPerformDecodeError(str(error))from error

def _frame(data,game_root,prefix,gameassembly,metadata,strings):
 if not isinstance(data,(bytes,bytearray,memoryview)):raise CharInteractPerformDecodeError('input: expected bytes-like payload')
 gate=validate(game_root=game_root,gameassembly=gameassembly,metadata=metadata)
 if gate['status']!='validated':raise CharInteractPerformDecodeError('CharInteract native gate: '+str(gate))
 return _frame_validated(data,gate,prefix,strings)

def _frame_validated(data,gate,prefix,strings):
 if not isinstance(data,(bytes,bytearray,memoryview)):raise CharInteractPerformDecodeError('input: expected bytes-like payload')
 try:result=frame(bytes(data),gate['fields'],prefix=prefix,actor_fields=gate.get('actorFields'),action_fields=gate.get('actionFields'),strings=strings)
 except SparsePerformDecodeError as error:raise CharInteractPerformDecodeError(str(error))from error
 result['evidenceBoundary']=gate['evidenceBoundary'];return result


@contextmanager
def sparse_perform_reader(*, game_root=None, gameassembly=None, metadata=None, strings=None):
 """Share one fresh proof only inside a bookended corpus/page operation.

 Direct readers still validate independently. This scope accepts no saved gate,
 pins the explicit native pair, and re-proves the same program at exit before
 callers may publish. Its callable expires on every exit, including failures.
 """
 if (gameassembly is None)!=(metadata is None):
  raise CharInteractPerformDecodeError('CharInteract operation: both native paths required')
 if gameassembly is None:
  if game_root is None:gameassembly,metadata=resolve_installed_native_inputs()
  else:
   folder=Path(game_root).resolve();gameassembly=folder.parent/'GameAssembly.dll';metadata=folder/'il2cpp_data/Metadata/global-metadata.dat'
 pair=dict(gameassembly=Path(gameassembly).resolve(),metadata=Path(metadata).resolve())
 before=snapshot_complete_reader_inputs()
 pool=snapshot_string_pool_inputs(strings.root.parent)if strings is not None else None
 gate=validate(**pair)
 if gate.get('status')!='validated':raise CharInteractPerformDecodeError('CharInteract operation native gate: '+str(gate))
 identity=canonical_json_sha256(gate);active=True
 def decode(data,*,prefix=False):
  if not active:raise CharInteractPerformDecodeError('CharInteract operation has closed')
  if type(prefix)is not bool:raise CharInteractPerformDecodeError('CharInteract operation: prefix must be bool')
  return _frame_validated(data,gate,prefix,strings)
 try:yield decode
 finally:active=False
 after=validate(**pair)
 if after.get('status')!='validated' or canonical_json_sha256(after)!=identity or canonical_json_sha256(gate)!=identity:
  raise CharInteractPerformDecodeError('CharInteract operation native proof changed: '+str(after)[:900])
 if snapshot_complete_reader_inputs()!=before:
  raise CharInteractPerformDecodeError('CharInteract operation reader sources changed')
 if pool is not None and snapshot_string_pool_inputs(strings.root.parent)!=pool:
  raise CharInteractPerformDecodeError('CharInteract operation StringPool changed')

def decode_char_interact_complete_frame(data,*,game_root=None,gameassembly=None,metadata=None,strings=None):return _frame(data,game_root,False,gameassembly,metadata,strings)
def frame_char_interact_prefix(data,*,game_root=None,gameassembly=None,metadata=None,strings=None):return _frame(data,game_root,True,gameassembly,metadata,strings)
def decode_char_interact_audio_actions(data,*,game_root=None,gameassembly=None,metadata=None,strings=None):return decode_char_interact_complete_frame(data,game_root=game_root,gameassembly=gameassembly,metadata=metadata,strings=strings)['audioActions']


def decode_char_interact_current_animation(data,*,operation):
 """Explicit whole-current opt-in; the caller must finish the native operation."""
 from scripts.game_data.animation_current_native import prepared_current_animation
 return prepared_current_animation(operation).char_interact(data)
