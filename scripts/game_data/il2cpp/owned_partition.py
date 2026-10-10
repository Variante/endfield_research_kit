"""Shared owned-byte partition checks for selected anonymous native bodies.

A contract names the owned windows of one entry, plus the code, padding and
table pieces that must tile them exactly. These helpers authenticate each
window against its recorded SHA256, check the owned windows against the
image's entry extent and chained fragments, check that decoded instructions
cover a code window byte-for-byte, and check that the pieces partition the
owned bytes with no gap, overlap or outside piece. Every failure carries the
caller's diagnostic label prefix, so a refusal names the validator that
raised it. What the decoded instructions mean is the caller's proof, not
this module's.
"""
from __future__ import annotations
import hashlib
from scripts.game_data.il2cpp.integer_source_operands import is_unknown_instruction
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar


class BranchGrammar(ProgramGrammar):
    """ProgramGrammar that also decodes jb/jae/jl/jge from their original bytes."""

    def branch(self, condition, label=None):
        codes={'jb':2,'jae':3,'jl':12,'jge':13}
        if condition not in codes:return super().branch(condition,label)
        row=self.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16);code=codes[condition]
        if len(raw)==2 and raw[0]==0x70+code:relative=raw[1:]
        elif len(raw)==6 and raw[:2]==bytes((0x0f,0x80+code)):relative=raw[2:]
        else:self.fail('branch-predicate',condition,row)
        target=at+len(raw)+int.from_bytes(relative,'little',signed=True)
        if row['text'] not in (f'{condition} 0x{target:x}',f'jcc 0x{target:x}'):
            self.fail('branch-decoding',hex(target),row)
        if label is not None:self.edges.append((target,label,row))
        return {**row,'target':target,'predicate':condition}


def window_bytes(index,start,end,digest,label):
    """Return image bytes [start, end) after checking them against ``digest``."""
    if end<=start:raise ValueError(f'{label}.window-range')
    raw=index.pe.bytes_at_va(start,end-start)
    if len(raw)!=end-start or hashlib.sha256(raw).hexdigest().upper()!=digest.upper():
        raise ValueError(f'{label}.code-window')
    return raw


def checked_rows(rows,raw,label):
    """Refuse unknown instructions and decoded rows that do not cover ``raw`` exactly."""
    if any(is_unknown_instruction(r) for r in rows):raise ValueError(f'{label}.unknown-instruction')
    if b''.join(bytes.fromhex(r['bytes']) for r in rows)!=raw:raise ValueError(f'{label}.instruction-coverage')
    return rows


def owned_windows(index,c,label):
    """Check the contract's owned windows against the image extent and fragments.

    Returns ``(owned, pieces, windows)``: the owned ``(start, end)`` ranges, the
    authenticated code/padding pieces as ``(start, end, category)``, and
    ``(category, window, start, raw)`` for each of those windows in contract order.
    """
    base=index.pe.image_base;entry=base+c['entryRva']
    if entry not in index.extents:raise ValueError(f'{label}.owned-entry-missing')
    actual=sorted(set([(entry,index.extents[entry])]+[(a,a+n) for a,n in index.chained_fragments.get(entry,[])]))
    owned=[(base+w['startRva'],base+w['endRva']) for w in c['ownedWindows']]
    if actual!=owned or len(set(owned))!=len(owned):raise ValueError(f'{label}.owned-fragments: expected={owned} actual={actual}')
    for w in c['ownedWindows']:window_bytes(index,base+w['startRva'],base+w['endRva'],w['sha256'],label)
    pieces=[];windows=[]
    for category in ('codeWindows','paddingWindows'):
        for w in c[category]:
            start,end=base+w['startRva'],base+w['endRva'];raw=window_bytes(index,start,end,w['sha256'],label)
            pieces.append((start,end,category));windows.append((category,w,start,raw))
    return owned,pieces,windows


def check_byte_partition(owned,pieces,label):
    """Refuse unless ``pieces`` tile every owned range exactly and lie inside one."""
    used=set()
    for start,end in owned:
        cursor=start
        for a,b,kind in sorted(pieces):
            if not start<=a<end:continue
            if a!=cursor or b>end:raise ValueError(f'{label}.byte-partition: cursor={cursor} piece={(a,b,kind)}')
            used.add((a,b,kind));cursor=b
        if cursor!=end:raise ValueError(f'{label}.byte-partition-tail')
    if len(used)!=len(pieces):raise ValueError(f'{label}.byte-partition-outside')


def rip_load(g,register,target):
    """Take one complete 64-bit RIP-relative load of ``target`` into ``register``."""
    row=g.row();raw=bytes.fromhex(row['bytes']);decoded=decode_memory_move(raw,0,int(row['va'],16))
    if decoded is None or decoded[1]!=len(raw):g.fail('global-load','complete memory move',row)
    f=decoded[0]['memoryOperation'];a=f['address']
    if (f['direction'],f['register'],f['registerBits'],f['memoryBytes'],a['ripRelative'],a.get('absoluteAddress'))!=('load',register,64,8,True,target):
        g.fail('global-load',(register,target),f)
