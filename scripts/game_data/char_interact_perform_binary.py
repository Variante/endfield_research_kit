"""Current typed CharInteract sparse owner and prefix, with selected native source gates."""
from scripts.game_data.memorypack.char_perform_sparse import frame,SparsePerformDecodeError
from scripts.game_data.char_interact_perform_sparse_native import validate

class CharInteractPerformDecodeError(ValueError):pass

def _frame(data,game_root,prefix,gameassembly,metadata,strings):
 if not isinstance(data,(bytes,bytearray,memoryview)):raise CharInteractPerformDecodeError('input: expected bytes-like payload')
 gate=validate(game_root=game_root,gameassembly=gameassembly,metadata=metadata)
 if gate['status']!='validated':raise CharInteractPerformDecodeError('CharInteract native gate: '+str(gate))
 try:result=frame(bytes(data),gate['fields'],prefix=prefix,actor_fields=gate.get('actorFields'),action_fields=gate.get('actionFields'),strings=strings)
 except SparsePerformDecodeError as error:raise CharInteractPerformDecodeError(str(error))from error
 result['evidenceBoundary']=gate['evidenceBoundary'];return result

def decode_char_interact_complete_frame(data,*,game_root=None,gameassembly=None,metadata=None,strings=None):return _frame(data,game_root,False,gameassembly,metadata,strings)
def frame_char_interact_prefix(data,*,game_root=None,gameassembly=None,metadata=None,strings=None):return _frame(data,game_root,True,gameassembly,metadata,strings)
def decode_char_interact_audio_actions(data,*,game_root=None,gameassembly=None,metadata=None,strings=None):return decode_char_interact_complete_frame(data,game_root=game_root,gameassembly=gameassembly,metadata=metadata,strings=strings)['audioActions']
