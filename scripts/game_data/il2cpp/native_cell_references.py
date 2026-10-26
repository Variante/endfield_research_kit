"""Find selected canonical RIP-relative QWORD references as raw candidates.

This is an overlapping byte-pattern search for REX.W MOV/LEA and MOV imm32
forms. It does not establish instruction/code ownership or discover every
writer: other widths, wider overlaps, aliases and child stores remain open.
Callers must authenticate the selected image and prove each candidate body.
"""
from __future__ import annotations
import re
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.integer_addressing import decode_lea_address

_REG=re.compile(rb'(?=([\x48-\x4f][\x89\x8b\x8d][\x05\x0d\x15\x1d\x25\x2d\x35\x3d].{4}))',re.DOTALL)
_IMM=re.compile(rb'(?=([\x48-\x4b]\xc7\x05.{8}))',re.DOTALL)


def selected_qword_reference_candidates(image,cell_rvas):
    values=tuple(cell_rvas)
    if any(type(v)!=int or v<0 for v in values):raise ValueError('nativeCellReferences.cell-rva-range')
    cells=set(values)
    result=[]
    for section in image.sections:
        if not section['characteristics']&0x20000000:continue
        raw=image.buf[section['rawPointer']:section['rawPointer']+section['rawSize']]
        for pattern in (_REG,_IMM):
            for match in pattern.finditer(raw):
                body=match.group(1);site=section['virtualAddress']+match.start();target=site+len(body)+int.from_bytes(body[3:7],'little',signed=True)
                if target not in cells:continue
                opcode=body[1]
                if opcode==0x8d:
                    decoded=decode_lea_address(body,0,image.image_base+site)
                    if decoded is None or decoded[1]!=len(body):raise ValueError('nativeCellReferences.address-encoding')
                    facts=decoded[0]['addressOperation'];kind='address'
                elif opcode!=0xc7:
                    decoded=decode_memory_move(body,0,image.image_base+site)
                    if decoded is None or decoded[1]!=len(body):raise ValueError('nativeCellReferences.move-encoding')
                    facts=decoded[0]['memoryOperation'];kind=facts['direction']
                    if facts['memoryBytes']!=8:raise ValueError('nativeCellReferences.qword-width')
                else:
                    # MOV r/m64, imm32 sign-extends its immediate. It supplies
                    # a raw-pattern candidate only; no decoder is substituted.
                    value=int.from_bytes(body[7:11],'little',signed=True)&((1<<64)-1)
                    facts={'memoryWriteBytes':8,'encodedImmediateBits':32,'immediateWord':value};kind='immediateStore'
                result.append({'siteRva':site,'cellRva':target,'kind':kind,'rawHex':body.hex(),'facts':facts,
                    'instructionBoundaryAndOwnedCodeProved':False})
    return sorted(result,key=lambda row:(row['siteRva'],row['kind']))
