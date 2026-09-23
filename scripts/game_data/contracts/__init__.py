"""The reviewed contract JSON that the game-data readers load.

Every file here records a data structure of one installed build -- a
MemoryPack formatter window, a named JSON schema, a streaming field layout --
together with the addresses and hashes that let its reader prove the layout
against the selected ``GameAssembly.dll`` and ``global-metadata.dat``. Git owns
the files' integrity, so no module pins a contract's own bytes; what a reader
checks is the recorded build and the native code the rows were read from.
Per-record codec layouts stay in ``codecs/``.
"""
from pathlib import Path

CONTRACTS_DIR: Path = Path(__file__).resolve().parent
