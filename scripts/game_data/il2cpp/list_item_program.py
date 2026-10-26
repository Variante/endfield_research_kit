"""Ordinary selected fixed-width list item and its stored bounds operand."""
from scripts.game_data.il2cpp.owned_partition import BranchGrammar
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.il2cpp.memory_moves import decode_memory_move


def check_list_item_program(rows, *, entry, owned_ranges, element_kind):
    if element_kind not in ("int32","reference"):raise ValueError("listItem.element-kind")
    control=check_consumer_control(rows,entry=entry,owned_ranges=owned_ranges)
    g=BranchGrammar(rows,label='listItem')
    g.take('sub rsp, 0x28');bound=g.row();raw=bytes.fromhex(bound['bytes'])
    if raw[:2]==b'\x3b\x51' and len(raw)==3:offset=int.from_bytes(raw[2:],'little',signed=True)
    elif raw[:2]==b'\x3b\x91' and len(raw)==6:offset=int.from_bytes(raw[2:],'little',signed=True)
    else:g.fail('incoming-index-bound','Int32 EDX vs [RCX+displacement]',bound)
    if offset<16 or bound['text']!=f'cmp edx, dword [rcx+{offset:#x}]':g.fail('bound-offset','instance field',bound)
    g.branch('jae','bounds');array=g.row()
    decoded=decode_memory_move(bytes.fromhex(array['bytes']),0,int(array['va'],16))
    if decoded is None or decoded[1]!=len(bytes.fromhex(array['bytes'])):g.fail('array-load','complete move',array)
    op=decoded[0]['memoryOperation'];address=op['address']
    if (op['direction'],op['register'],op['registerBits'],op['memoryBytes'],address.get('base'),address.get('index'),address.get('ripRelative'))!=('load','rax',64,8,'rcx',None,False):
        g.fail('array-load','incoming receiver reference field',array)
    array_offset=address['displacement']
    if array_offset<16 or not (array_offset+8<=offset or offset+4<=array_offset):g.fail('field-overlap','disjoint fields',array)
    g.take('test rax, rax');g.branch('je','null')
    g.take('cmp edx, dword [rax+0x18]');g.branch('jae','arrayBounds')
    g.take('movsxd rcx, edx','mov eax, [rax+rcx*4+0x20]' if element_kind=='int32' else 'mov rax, [rax+rcx*8+0x20]','add rsp, 0x28','ret')
    g.mark('null');g.pattern(r'call 0x[0-9a-f]+');g.take('int3')
    g.mark('arrayBounds');g.pattern(r'call 0x[0-9a-f]+');g.take('int3')
    g.mark('bounds');g.take('xor ecx, ecx');g.pattern(r'call 0x[0-9a-f]+');g.take('int3');g.finish()
    return dict(elementKind=element_kind,elementBytes=4 if element_kind=="int32" else 8,boundFieldOffset=offset,arrayFieldOffset=array_offset,control=control,
        evidenceBoundary='direct',boundary='On ordinary return, incoming EDX passed unsigned bounds checks against the receiver DWORD and array length; the selected-width element at that signed-extended index becomes the selected low-32-bit/full-reference return. Exceptional helper effects and runtime storage validity remain separate.')
