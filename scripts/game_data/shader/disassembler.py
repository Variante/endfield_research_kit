"""Bounded Windows DXBC disassembly with explicit native-tool provenance."""
import ctypes
import hashlib
import os
from pathlib import Path
from scripts.game_data.shader.dxbc import read_dxbc


class Disassembler:
    def __init__(self):
        if os.name!='nt':raise ValueError('DXBC instruction recovery requires the Windows system disassembler')
        if ctypes.sizeof(ctypes.c_void_p)!=8:raise ValueError('DXBC instruction recovery requires a 64-bit Windows Python runtime')
        self.path=Path(os.environ['SystemRoot'])/'System32/d3dcompiler_47.dll'
        self.sha256=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.dll=ctypes.WinDLL(str(self.path))
        self.call=self.dll.D3DDisassemble
        self.call.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)]
        self.call.restype=ctypes.c_long
        self.cache={}

    def check(self):
        if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.sha256:raise ValueError('DXBC system disassembler changed during recovery')

    def disassemble(self,data):
        frame=read_dxbc(data);key=frame['sha256']
        if key in self.cache:return self.cache[key]
        raw=ctypes.create_string_buffer(data);blob=ctypes.c_void_p()
        status=self.call(raw,len(data),0x80,None,ctypes.byref(blob))
        if not blob.value:raise ValueError(f'DXBC disassembler failed HRESULT {status & 0xffffffff:08x}')
        table=ctypes.cast(ctypes.cast(blob,ctypes.POINTER(ctypes.c_void_p))[0],ctypes.POINTER(ctypes.c_void_p))
        pointer=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p)(table[3])
        size=ctypes.WINFUNCTYPE(ctypes.c_size_t,ctypes.c_void_p)(table[4])
        release=ctypes.WINFUNCTYPE(ctypes.c_uint,ctypes.c_void_p)(table[2])
        try:
            if status:raise ValueError(f'DXBC disassembler failed HRESULT {status & 0xffffffff:08x}')
            length=size(blob)
            if not 0<length<=16*1024*1024:raise ValueError('DXBC disassembly output exceeds bounds')
            address=pointer(blob)
            if not address:raise ValueError('DXBC disassembly output pointer is null')
            text=ctypes.string_at(address,length).rstrip(b'\0').decode('ascii')
        finally:release(blob)
        self.cache[key]=text;return text
