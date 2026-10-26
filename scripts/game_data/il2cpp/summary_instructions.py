"""Bounded diagnostic scans with current operand framing and explicit EOF gaps."""
import re
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions


def decode_summary_instructions(mapper, data, start_va):
    try:
        rows=decode_type_data_initialization_instructions(mapper,data,start_va)
    except ValueError as error:
        truncated=re.fullmatch(r'x64\.[\w-]+\.truncated: offset=(\d+) requiredEnd=\d+ bytes=\d+',str(error))
        if not truncated or not 0 < len(data)-int(truncated[1]) <= 15:
            raise
        offset=int(truncated[1])
        rows=decode_type_data_initialization_instructions(mapper,data[:offset],start_va)
        rows.append(dict(offset=offset,va=hex(start_va+offset),bytes=data[offset:].hex(' '),
                         text='db '+data[offset:].hex(' '),truncatedScanBoundary=True))
    result=[]
    for row in rows:
        if row.get('truncatedScanBoundary'):
            result.append(row)
            continue
        low,end=mapper.decode_one_x64(data,row['offset'],start_va)
        result.append(low if not low['text'].startswith('db') and end==row['offset']+len(bytes.fromhex(row['bytes'])) else row)
    return result
