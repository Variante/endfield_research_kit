"""Complete registered MethodSpec-index descriptor control, not cache liveness."""
from __future__ import annotations
from .owned_partition import BranchGrammar,rip_load
from .context_slot_initializer_control import validate_closed_initializer_graph


def validate_method_spec_descriptor_control(rows, *, image_base, entry_rva, globals, calls):
    g=BranchGrammar(rows,label='methodSpecDescriptorControl')
    g.take('push rdi','sub rsp, 0x20');rip_load(g,'rax',image_base+globals['cache'])
    g.take('movsxd rdi, ecx','cmp qword [rax+rdi*8], 0x0');g.branch('jne','cachedReturn')
    rip_load(g,'rax',image_base+globals['metadataRegistration'])
    g.take('lea rdx, [rdi+rdi*2]','mov [rsp+0x30], rbx','mov rcx, [rax+0x48]',
        'lea rbx, [rcx+rdx*4]','mov ecx, [rcx+rdx*4]')
    g.call(image_base+calls['definition']);g.take('xor edx, edx','mov r9, rax',
        'cmp dword [rbx+0x4], -0x1','mov r8d, edx')
    rip_load(g,'rax',image_base+globals['metadataRegistration']);g.branch('je','methodArgument')
    g.take('movsxd rdx, dword [rbx+0x4]','mov rcx, [rax+0x18]','mov rdx, [rcx+rdx*8]')
    g.mark('methodArgument');g.take('cmp dword [rbx+0x8], -0x1');g.branch('je','compose')
    g.take('movsxd rcx, dword [rbx+0x8]','mov rax, [rax+0x18]','mov r8, [rax+rcx*8]')
    g.mark('compose');g.take('mov rcx, r9');g.call(image_base+calls['composition'])
    rip_load(g,'rcx',image_base+globals['cache']);g.take('mov rbx, [rsp+0x30]','mov [rcx+rdi*8], rax')
    rip_load(g,'rax',image_base+globals['cache']);g.mark('cachedReturn')
    g.take('mov rax, [rax+rdi*8]','add rsp, 0x20','pop rdi','ret');g.finish()
    graph=validate_closed_initializer_graph(rows,entry_va=image_base+entry_rva)
    return {'completeControl':graph,'indexInputSignExtendedBits':32,'methodSpecRecordBytes':12,
        'metadataMethodSpecTablePointerOffset':72,'metadataGenericInstTablePointerOffset':24,
        'methodDefinitionIndexOffset':0,'classInstantiationIndexOffset':4,'methodInstantiationIndexOffset':8,
        'instantiationIndexSentinel':-1,'sentinelArgumentQword':0,
        'compositionArguments':{'rcx':'plain definition helper return','rdx':'class instantiation pointer or zero','r8':'method instantiation pointer or zero'},
        'cacheEntryStrideBytes':8,'coldCompositionReturnStoredToSelectedCacheSlot':True,
        'returnIsFreshCacheSlotRead':True,'cacheHitReturnGuaranteedNonzero':False,
        'inputIndexBoundsCheckedHere':False,'cacheOrRegistrationStabilityObserved':False,
        'definitionAndCompositionCalleeEffectsProved':False,
        'conditions':'Nonnegative in-range signed index; compatible selected registration/tables and valid readable/writable cache storage; normal ABI-preserving helpers. Concurrent slot/global changes can affect the fresh return read, so a stored return does not by itself establish the returned value.'}
