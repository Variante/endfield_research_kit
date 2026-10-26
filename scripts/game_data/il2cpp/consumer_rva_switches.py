"""Partition guarded owned RVA switch programs without decoding tables as code."""
from scripts.game_data.il2cpp.integer_addressing import decode_lea_address, decode_register_arithmetic
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.integer_source_operands import is_unknown_instruction


def partition_consumer_rva_switches(mapper,raw,*,entry,image_base):
    found=[]
    for offset in range(len(raw)-3):
        if raw[offset:offset+2]!=b'\x83\xf8':continue
        maximum=raw[offset+2];at=offset+3
        if maximum>=128:continue  # CMP r32, imm8 sign-extends its encoded immediate.
        if raw[at:at+1]==b'\x77':size=2
        elif raw[at:at+2]==b'\x0f\x87':size=6
        else:continue
        if at+size>len(raw):continue
        relative=raw[at+1:at+2] if size==2 else raw[at+2:at+6]
        exit_at=entry+at+size+int.from_bytes(relative,'little',signed=True);at+=size
        # The compiler may repeat the identical EAX = ECX + disp8 expression.
        if raw[at:at+2]==b'\x8d\x41':
            if offset<3 or raw[at:at+3]!=raw[offset-3:offset]:continue
            at+=3
        if raw[at:at+2]==b'\x48\x98':index_register='rax';at+=2
        elif raw[at:at+3]==b'\x48\x63\xc8':index_register='rcx';at+=3
        else:continue
        base_load=None;base_register="r15"
        lea=decode_lea_address(raw,at,entry)
        if lea and lea[0]['addressOperation'].get('absoluteAddress')==image_base:
            base_register=lea[0]['addressOperation'].get('destination')
            if base_register not in ('r15','rdx'):continue
            base_load=entry+at;at=lea[1]
        load=decode_memory_move(raw,at,entry)
        if load is None:continue
        row,end=load;op=row['memoryOperation'];address=op['address']
        if (op['direction'],op['registerBits'],op['memoryBytes'],address.get('base'),address.get('index'),address.get('scale'),address.get('ripRelative'))!=('load',32,4,base_register,index_register,4,False):continue
        destination=op['backingRegister']
        if destination not in ('rax','rdx') or destination==base_register:continue
        table_start=image_base+address['displacement']-entry;table_end=table_start+4*(maximum+1)
        add=decode_register_arithmetic(raw,end,entry)
        if add is None:continue
        fact=add[0]['integerOperation'];jump=add[1]
        if (fact['operation'],fact['bits'],fact['destination'],fact['source'])!=('add',64,destination,base_register):continue
        if raw[jump:jump+2]!=(b'\xff\xe0' if destination=='rax' else b'\xff\xe2'):continue
        if not jump+2<=table_start<table_end<=len(raw) or entry+offset<=exit_at<entry+jump+2:continue
        targets=[image_base+int.from_bytes(raw[n:n+4],'little') for n in range(table_start,table_end,4)]
        found.append(dict(guard=entry+offset,guardExit=exit_at,load=entry+at,jump=entry+jump,maximum=maximum,
            tableStart=entry+table_start,tableEnd=entry+table_end,targets=targets,baseLoad=base_load,baseRegister=base_register))
    if not found:raise ValueError('consumerRvaSwitches.no-guarded-tables')
    tables=sorted(found,key=lambda value:value['tableStart']);start=tables[0]['tableStart']
    cursor=start
    for table in tables:
        if table['tableStart']!=cursor:raise ValueError('consumerRvaSwitches.table-gap-or-overlap')
        cursor=table['tableEnd']
    if cursor!=entry+len(raw):raise ValueError('consumerRvaSwitches.unclassified-owned-tail')
    rows=decode_type_data_initialization_instructions(mapper,raw[:start-entry],entry)
    if any(is_unknown_instruction(row) for row in rows):raise ValueError('consumerRvaSwitches.unknown-code-instruction')
    if b''.join(bytes.fromhex(row['bytes']) for row in rows)!=raw[:start-entry]:raise ValueError('consumerRvaSwitches.code-byte-partition')
    padding=[]
    while len(rows)>1 and bytes.fromhex(rows[-1]['bytes']) in (b'\x90',b'\xcc',b'\x0f\x1f\x00'):
        previous=rows[-2]
        if bytes.fromhex(previous['bytes'])!=b'\xcc':break
        padding.insert(0,rows.pop())
    if sum(len(bytes.fromhex(row['bytes'])) for row in padding)>3 or (start-image_base)%4:
        raise ValueError('consumerRvaSwitches.unproved-table-alignment')
    boundaries={int(row['va'],16) for row in rows}
    jumps={}
    for table in tables:
        if table['guard'] not in boundaries or table['jump'] not in boundaries or table['guardExit'] not in boundaries or any(target not in boundaries for target in table['targets']):
            raise ValueError('consumerRvaSwitches.interior-or-data-target')
        if table['jump'] in jumps:raise ValueError('consumerRvaSwitches.duplicate-dispatch')
        jumps[table['jump']]=set(table['targets'])
    end=int(rows[-1]['va'],16)+len(bytes.fromhex(rows[-1]['bytes']))
    return dict(rows=rows,codeRange=(entry,end),padding=padding,tables=tables,computedJumpTargets=jumps,
        evidenceBoundary='conditional',condition='Complete guarded code/table byte partition and enumerated table values; the caller must separately prove each selected base register equals selected image base at every load and that no edge bypasses a dispatch guard. No live switch selection follows.')


def ordinary_entry_program(part,*,entry,tail_exits=None):
    from scripts.game_data.il2cpp.consumer_control import build_consumer_control_graph, check_consumer_control
    graph=build_consumer_control_graph(part['rows'],entry=entry,owned_ranges=[part['codeRange']],
        computed_jump_targets=part['computedJumpTargets'],tail_exits=tail_exits)
    by_at={int(row['va'],16):row for row in part['rows']}
    for table in part['tables']:
        for source,targets in graph['edges'].items():
            row=by_at[source]
            following=source+len(bytes.fromhex(row['bytes']))
            if any(table['guard']<target<=table['jump'] and
                   (not table['guard']<=source<table['jump'] or target!=following) for target in targets):
                raise ValueError('consumerRvaSwitches.guard-bypass')
    from scripts.game_data.il2cpp.consumer_entry_program import ordinary_consumer_entry
    program=ordinary_consumer_entry(part['rows'],entry=entry,owned_ranges=[part['codeRange']],computed_jump_targets=part['computedJumpTargets'],tail_exits=tail_exits)
    program['nonEntryCode']=program.pop('unenteredOwnedByteCandidates')
    program['condition']='Complete owned code/table framing. '+program['condition'].replace('Exception/resumption','exception/resumption')
    return program
