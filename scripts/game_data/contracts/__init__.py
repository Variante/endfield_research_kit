"""The reviewed, byte-pinned contract JSON that the game-data readers load.

Every file here records a data structure of one installed build -- a
MemoryPack formatter window, a named JSON schema, a streaming field layout --
together with the addresses and hashes that let its reader prove the layout
against the selected ``GameAssembly.dll`` and ``global-metadata.dat``. The
reader that owns a file pins its digest and fails closed on a mismatch, so
editing a file here is a code change: re-pin the digest in the owning module
and never let a tool rewrite the line endings (``.gitattributes`` keeps git
from doing so). Contracts whose loader lives beside them stay in
``native_contracts/``; per-record codec layouts stay in ``codecs/``.
"""
from pathlib import Path

CONTRACTS_DIR: Path = Path(__file__).resolve().parent
