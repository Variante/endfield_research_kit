"""Check a bounded call-entry graph with only GP operations and RET exits.

This proves vector registers are untouched on covered paths. It does not
claim a pdata-owned whole function, valid memory or loop termination.
"""
from __future__ import annotations
import re
from .stack_argument_flow import decode_stack_flow,_edge


def prove_vector_neutral_entry(mapper,raw,start):
    rows=decode_stack_flow(mapper,raw,start);by_va={int(r['va'],16):n for n,r in enumerate(rows)}
    pending=[0];seen=set();returns=[]
    allowed={'cmp','test','mov','movzx','movsx','movsxd','lea','sub','add','and','or','xor',
             'shr','shl','sar','inc','dec','bts','prefetch','nop'}
    while pending:
        n=pending.pop()
        if n in seen:continue
        if not 0<=n<len(rows):raise ValueError('vector-neutral: fallthrough outside bounded entry')
        seen.add(n);r=rows[n];text=r['text'];b=bytes.fromhex(r['bytes'])
        if b==b'\xc3':returns.append(n);continue
        edge=_edge(r)
        if edge:
            target,conditional=edge
            if target not in by_va:raise ValueError('vector-neutral: branch outside entry or instruction interior')
            pending.append(by_va[target])
            if conditional:pending.append(n+1)
            continue
        mnemonic=text.split(' ',1)[0]
        if (mnemonic not in allowed and not text.startswith('lock cmpxchg ') or
                re.search(r'\b(?:[xyz]mm\d+|mm\d+)\b',text)):
            raise ValueError(f'vector-neutral: unproved instruction at {r["offset"]}: {text}')
        pending.append(n+1)
    if not returns:raise ValueError('vector-neutral: no RET exit')
    extent=max(rows[n]['offset']+len(bytes.fromhex(rows[n]['bytes'])) for n in seen)
    return {'evidenceBoundary':'conditional','preservesVectorRegisters':True,'visitedInstructions':len(seen),
        'coveredEntryBytes':extent,'ownedWholeFunction':False,
        'condition':'Bounded call-entry graph, valid memory and returning execution; no external transfers or vector operations. Loop termination and whole-function ownership are separate.'}
