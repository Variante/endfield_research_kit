"""Selected current pooled uint-keyed NPC dictionary; no guessed row boundaries."""
from scripts.game_data.memorypack.npc_runtime import npc_runtime_decoder,require_selected_decoder


def decode_npc_dictionary(data,offset,*,strings,gameassembly=None,metadata=None,npc_decoder=None):
    if npc_decoder is not None:
        require_selected_decoder(npc_decoder,strings=strings,gameassembly=gameassembly,metadata=metadata)
        return npc_decoder.dictionary(data,offset,key_wire='uint')
    with npc_runtime_decoder(strings=strings,gameassembly=gameassembly,metadata=metadata)as decode:
        return decode.dictionary(data,offset,key_wire='uint')
