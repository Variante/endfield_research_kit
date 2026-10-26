"""Complete legacy memory prefetch hints, without a memory-value result.

The selected 0F0D /0 and /1 memory forms preserve general registers and
EFLAGS. They do not architecturally store a value or supply a loaded value;
cache effects, execution support and normal continuation remain conditions.
Other groups, register operands, prefixes and trailing bytes are not admitted.
"""
from scripts.game_data.il2cpp.integer_addressing import _prefix,_address


def memory_prefetch_address(raw):
    """Return the complete address for the existing exact memory-only forms."""
    at,rex=_prefix(raw,0)
    if rex&4 or raw[at:at+2]!=b'\x0f\x0d' or at+2>=len(raw):return None
    modrm=raw[at+2];at+=3
    if modrm>>6==3 or (modrm>>3)&7 not in(0,1):return None
    address,end=_address(raw,at,modrm,rex,0,'memory-prefetch')
    return address if end==len(raw) else None
