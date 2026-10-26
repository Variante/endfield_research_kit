"""Selected frameless guard tails and signed-index pointer arithmetic.

Imports identify declarations only. Valid initialized critical sections and
standard live API bindings are conditions, not evidence that locks were taken.
"""
from __future__ import annotations
from .method_carrier_control import _Grammar
from .integer_addressing import decode_lea_address

LABEL='nameCacheHandlerGuardControl'


def guard_pointer(array_base,index_word):
    if type(array_base) is not int or not 0<=array_base<1<<64 or type(index_word) is not int or not 0<=index_word<1<<32:
        raise ValueError(LABEL+'.pointer-domain')
    signed=index_word if index_word<1<<31 else index_word-(1<<32)
    return (array_base+40*signed)&((1<<64)-1)


def validate_name_cache_handler_guards(programs,*,image_base,contract):
    c=contract;base=image_base
    if set(programs)!={'guardEnter','guardLeave'} or set(c['functions'])!=set(programs):raise ValueError(LABEL+'.function-membership')
    if c['strideBytes']!=40:raise ValueError(LABEL+'.stride')
    imports={r['slotRva']:r for r in c['importDeclaration']['selectedImports']}
    for role,symbol in (('guardEnter','EnterCriticalSection'),('guardLeave','LeaveCriticalSection')):
        rows=programs[role];g=_Grammar(rows,label=LABEL+'.'+role)
        g.take('movsxd rax, ecx','lea rcx, [rax+rax*4]')
        row=g.row();raw=bytes.fromhex(row['bytes']);parsed=decode_lea_address(raw,0,int(row['va'],16))
        f=parsed[0]['addressOperation'] if parsed and parsed[1]==len(raw) else {}
        if (f.get('destination'),f.get('destinationBits'),f.get('ripRelative'),f.get('absoluteAddress'))!=('rax',64,True,base+c['arrayBaseRva']):g.fail('common-array-address',c['arrayBaseRva'],row)
        g.take('lea rcx, [rax+rcx*8]');row=g.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
        slot=c['functions'][role]['tailImportSlotRva']
        if len(raw)!=7 or raw[:3]!=bytes.fromhex('48FF25') or at+7+int.from_bytes(raw[3:],'little',signed=True)!=base+slot:g.fail('whole-import-tail',slot,row)
        g.finish();decl=imports.get(slot,{})
        if (decl.get('libraryName'),decl.get('symbolName'))!=('KERNEL32.dll',symbol):raise ValueError(LABEL+'.static-import-identity:'+role)
    return {'status':'signed-index-shared-storage-and-static-guard-tail-control-proved',
        'codeInstructions':sum(len(rr) for rr in programs.values()),'signedIndexBits':32,'strideBytes':40,
        'bothHelpersPassSameIndexedStorageAddressProved':True,'zeroIndexSelectsCommonArrayBaseProved':True,
        'wholeTailProgramsPreserveStackAndDoNotStoreMemoryProved':True,
        'staticEnterLeaveCriticalSectionImportsProved':True,
        'arbitraryIndexBoundsOrNoWrapGuaranteed':False,'criticalSectionInitializedProved':False,
        'liveImportBindingOrMutexAcquisitionProved':False,'allHandlerWritersUseSameGuardProved':False,
        'cookieAndEncodedWordSameEpochProved':False,'cacheNoninterferenceProved':False,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'conditions':c['conditionalDomain']}
