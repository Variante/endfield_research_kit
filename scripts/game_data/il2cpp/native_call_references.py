"""Selected E8 rel32 byte candidates, never an inferred complete call graph."""
from __future__ import annotations


def selected_direct_call_candidates(image,target_rvas):
    targets=tuple(target_rvas)
    if any(type(v) is not int or not 0<=v<1<<32 for v in targets):raise ValueError('nativeCallReferences.target-rva-domain')
    targets=set(targets);rows=[]
    for section in image.sections:
        if section['name']!='.text':continue
        raw=image.buf[section['rawPointer']:section['rawPointer']+section['rawSize']];pos=0
        while True:
            pos=raw.find(b'\xe8',pos)
            if pos<0:break
            if pos+5<=len(raw):
                body=raw[pos:pos+5];site=section['virtualAddress']+pos
                target=site+5+int.from_bytes(body[1:],'little',signed=True)
                if target in targets:rows.append({'siteRva':site,'targetRva':target,'rawHex':body.hex(),
                    'instructionBoundaryAndOwnedCodeProved':False,'callerInvocationObserved':False})
            pos+=1
    return sorted(rows,key=lambda r:(r['siteRva'],r['targetRva']))
