"""Read and check all ordinary instructions owned by one unwind family."""
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory


def read_owned_consumer_instructions(mapper, pe, entry):
    table, size, raw = read_exception_directory(pe)
    base = pe.image_base
    index = UnwindChainIndex(raw, lambda r,n: pe.bytes_at_va(base+r,n), table_rva=table, image_size=size)
    family = index.family(entry-base)
    ranges = [(base+row['runtimeTriple'][0],base+row['runtimeTriple'][1]) for row in family['ranges']]
    rows = []
    for start,end in sorted(ranges):
        rows += [dict(row,offset=int(row['va'],16)-entry) for row in
            decode_type_data_initialization_instructions(mapper,pe.bytes_at_va(start,end-start),start)]
    control = check_consumer_control(rows,entry=entry,owned_ranges=ranges)
    return rows, ranges, control
