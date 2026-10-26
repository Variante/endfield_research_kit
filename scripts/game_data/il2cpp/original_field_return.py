"""Original typed field-return suffix; replacement paths remain separate."""
from scripts.game_data.il2cpp.owned_consumer_instructions import read_owned_consumer_instructions
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.integer_source_operands import decode_byte_memory_zero_extension
from scripts.game_data.il2cpp.initializer_control import control_transfer


def _read_move(row,width):
    raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    decoded=(decode_byte_memory_zero_extension if width==1 else decode_memory_move)(raw,0,at)
    if decoded is None or decoded[1]!=len(raw):return None
    if width==1:
        op=decoded[0]['byteMemoryZeroExtensionOperation']
        if (op['destinationRegister'],op['destinationBits'],op['sourceBits'],op['memoryReadBytes'])!=('eax',32,8,1):return None
        return op['sourceAddress']
    op=decoded[0]['memoryOperation']
    if (op['direction'],op['backingRegister'],op['registerBits'],op['memoryBytes'])!=('load','rax',width*8,width):return None
    return op['address']


def check_original_field_return(index,body,offset,width,*,data_offset=None):
    image=index.image;rows,ranges,_=read_owned_consumer_instructions(image.mapper,image.pe,body.pointer)
    refs=check_reference_origins(rows,entry=body.pointer,owned_ranges=ranges,
        incoming_registers={'rcx':'this'},incoming_stack_slots={},selected_call_returns={})
    by_at={int(row['va'],16):row for row in rows};matches=[]
    def next_row(row):return by_at.get(int(row['va'],16)+len(bytes.fromhex(row['bytes'])))
    for row in rows:
        address=_read_move(row,8 if data_offset is not None else width)
        wanted=data_offset if data_offset is not None else offset
        if (address is None or address.get('index') is not None or address.get('ripRelative')
                or address.get('displacement')!=wanted or refs['registerOrigins'][int(row['va'],16)].get(address.get('base'))!=['this']):continue
        value=row
        if data_offset is not None:
            test=next_row(row);branch=next_row(test) if test else None
            if not test or test['bytes']!='48 85 c0' or branch is None:continue
            edge=control_transfer(branch)
            if edge.get('kind')!='conditional' or edge.get('conditionCode')!=4:continue
            value=next_row(branch)
            if value is None:continue
            selected=_read_move(value,width)
            if (selected is None or selected.get('base')!='rax' or selected.get('index') is not None
                    or selected.get('ripRelative') or selected.get('displacement')!=offset):continue
            trap=by_at.get(edge['target']);stop=next_row(trap) if trap else None
            if not trap or control_transfer(trap)['kind']!='call' or not stop or stop['bytes']!='cc':continue
        restore=next_row(value);end=next_row(restore) if restore else None
        if restore and end and restore['bytes']=='48 83 c4 28' and end['bytes']=='c3':
            matches.append(dict(receiverRead=row,returnRead=value,restore=restore))
    if len(matches)!=1:raise ValueError('originalFieldReturn.unique-original-getter-field-return:'+body.symbol)
    return matches[0]

