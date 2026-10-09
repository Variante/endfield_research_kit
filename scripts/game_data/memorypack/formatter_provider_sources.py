"""Complete selected physical formatter query and typed return ownership.

The selected cache guards and initialized stable MethodInfo/class/provider
state are conditions, as are normal callee returns and the Win64 ABI. The
physical body is bound by call bytes independently of the supplied method
name. Direct stack-only stores do not prove purity of calls or global state.
"""
from __future__ import annotations

from typing import Any, Callable
from scripts.game_data.memorypack.read_value_reference_sources import _profile


def validate_provider_transfer(image: Any, proof: dict, calls: dict, *, fail: Callable) -> dict:
    """Own the hidden MethodInfo, key/result slots, cast and full RAX return."""
    expected = ['4053','55','56','57','4154','4155','4156','4157','4883EC68','488BE9','4883793800',None,
        '488B5D38','488B1B',None,'83B9E000000000',None,'4885DB',None,'83B9E000000000',None,'B201','488BCB',None,
        '4C8D6020',None,'488B8B80000000',None,'90','488B4340','49C7C0FFFFFFFF','4C898424C0000000','483B4338',None,
        '4533ED','4C8B7348','49FFCE','498BCC',None,'488BF8','4C898424B0000000','488B7368','448B7B50','4923FE','488D0C7F',
        '443B3CCE',None,'48837B3800',None,'488D047F','833CC600',None,'488B54C608','498BCC',None,'85C0',None,
        '4883FFFF',None,'488D0C7F','488D14CE','488B4348','488D0C40','488B4368','488D0CC8','483BD1',None,
        '488B4A10','488B4370','4C8B34C8','488B8B80000000',None,'90',None,'83B9E000000000',None,None,None,None,
        '83B9E000000000',None,'498BCE',None,'488BD8','488B4538','488B4008','F6803801000001',None,'4885DB',None,
        '488BD0','488B0B',None,'84C0',None,'488BC3','4883C468','415F','415E','415D','415C','5F','5E','5D','5B','C3']
    branches = {n:(opcode,taken)for n,opcode,taken in (
        (11,'0F84',False),(16,'0F84',False),(18,'0F84',False),(20,'0F84',False),(33,'0F84',False),
        (46,'75',True),(48,'0F87',False),(51,'0F85',False),(56,'0F85',False),(58,'0F84',False),
        (66,'0F84',False),(75,'0F84',False),(77,'0F84',False),(80,'0F84',False),(87,'0F84',False),(89,'0F84',False),(94,'0F84',False))}
    _profile(image,proof,expected,branches,
        {23:'typeKey',38:'cacheHash',54:'cacheCompare',82:'formatterResult',92:'formatterClassPredicate'},
        {14:'488B0D',25:'488B1D',73:'488B0D',76:'803D',78:'488B0D'},(),(27,71),calls,fail=fail)
    return {'entryRva':proof['program'][0][0],'companionRegister':'rcx','savedCompanionRegister':'rbp',
        'providerKeyContextSlot':0,'expectedFormatterContextSlot':1,
        'actualCandidateRegister':'r14','selectedFormatterResultRegister':'rbx','returnRegister':'rax',
        'sameMethodInfoPreserved':True,'sameNonNullFormatterResultReturned':True,
        'expectedClassFromSameContext':True,'runtimeResultBits':64,'completeReturnProved':True,
        'directStores':'two caller-home stack slots only','directObjectFieldStores':0,
        'globalIndirectCalls':2,'calleeEffectsProved':False,'runtimeSelectionObserved':False,
        'physicalBodyIdentityProved':False}
