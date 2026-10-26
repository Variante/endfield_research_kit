"""Selected PE32+ AMD64 load-config pointer-storage declarations.

Microsoft PE format assigns VA-valued storage fields, not loaded function
identities. Only the consumed prefix and selected on-disk cells are read.
Reference: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
"""
from __future__ import annotations
import hashlib
from .pe_imports import _directory,_read,_u

_POINTER_FIELDS=(('SecurityCookie',88),('GuardCFCheckFunctionPointer',112),
                 ('GuardCFDispatchFunctionPointer',120))


def resolve_load_config_pointer_slots(image,wanted):
    wanted=sorted(set(wanted))
    if not wanted or any(type(v) is not int or not 0<=v<=(1<<32)-8 for v in wanted):
        raise ValueError('peLoadConfig.selected-slot-domain')
    directory,size,header=_directory(image,10)
    optional=_u(image,0x3c,4)+24;image_size=_u(image,optional+56,4)
    if not image_size or image.image_base+image_size>1<<64:
        raise ValueError('peLoadConfig.image-size')
    if not directory or not 128<=size<=1<<20 or directory+size>image_size:
        raise ValueError(f'peLoadConfig.directory-range: rva={directory} bytes={size} imageBytes={image_size}')
    declared=int.from_bytes(_read(image,directory,4),'little')
    if not 128<=declared<=size:
        raise ValueError(f'peLoadConfig.structure-size: expected=128..{size} actual={declared}')
    prefix=_read(image,directory,128)
    values=[(name,offset,int.from_bytes(prefix[offset:offset+8],'little')) for name,offset in _POINTER_FIELDS]
    rows=[]
    for slot in wanted:
        matches=[(name,offset,va) for name,offset,va in values if va and va==image.image_base+slot]
        if len(matches)!=1:
            raise ValueError(f'peLoadConfig.selected-slot-ownership: expected=1 slot={slot} actual={len(matches)}')
        name,offset,va=matches[0]
        if slot+8>image_size:
            raise ValueError(f'peLoadConfig.selected-slot-outside-image: slot={slot} imageBytes={image_size}')
        raw=_read(image,slot,8)
        rows.append({'slotRva':slot,'fieldName':name,'fieldOffset':offset,'fieldRva':directory+offset,
            'fieldHex':prefix[offset:offset+8].hex(' '),'declaredStorageVa':va,
            'onDiskSlotHex':raw.hex(' '),'onDiskStoredWord':int.from_bytes(raw,'little'),
            'declaredPointerStorageOwnershipProved':True,'liveStoredWordOrTargetProved':False,
            'loadedCallbackInvocationProved':False})
    return {'loadConfigDirectoryRva':directory,'directoryBytes':size,'structureBytes':declared,
        'directoryHeader':header,'consumedPrefixBytes':len(prefix),'consumedPrefixHex':prefix.hex(' '),
        'consumedPrefixSha256':hashlib.sha256(prefix).hexdigest().upper(),'selectedPointerSlots':rows,
        'completeLoadConfigOrGuardTablesProved':False,'liveStoredWordOrTargetProved':False}
