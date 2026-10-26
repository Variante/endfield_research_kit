"""Generated formatter argument paths with explicit external-call boundaries."""
from typing import Any, Callable
from scripts.game_data.memorypack.buffered_wrapper_lifecycle_sources import _match, _branch, _call


def authenticate(image: Any, proof: dict, expected: list, *, taken: set[int], fail: Callable) -> list:
    rows=proof['program']
    image.check_windows(proof['codeWindows'],label='generatedFormatterRoute')
    image.check_instruction_windows(rows,label='generatedFormatterRoute')
    _match(rows,expected,fail=fail)
    for n,(at,h) in enumerate(rows[:-1]):
        if n not in taken and rows[n+1][0]!=at+len(bytes.fromhex(h)):
            fail('formatter-route-linear-edge',at+len(bytes.fromhex(h)),rows[n+1][0])
    return rows


def ready_flag(row: list, *, fail: Callable) -> int:
    at,h=row;raw=bytes.fromhex(h)
    if len(raw)!=7 or raw[:2]!=b'\x80\x3d' or raw[-1]!=0:
        fail('formatter-route-ready-flag','CMP byte [RIP+disp32], zero',row)
    return at+7+int.from_bytes(raw[2:6],'little',signed=True)


def initializer_tail(image: Any, proof: dict, registrar_entry: int, *, fail: Callable) -> dict:
    rows=authenticate(image,proof,['33C9',None],taken=set(),fail=fail)
    _call(rows,1,registrar_entry,tail=True,fail=fail)
    return {'nullRegistrarMethodInfo':True,'frameUnchanged':True,'registrationEffectsProved':False}


def constructor_ready(image: Any, proof: dict, *, fail: Callable) -> dict:
    rows=authenticate(image,proof,['4883EC28',None,None,'4883C428','C3'],taken={2},fail=fail)
    flag=ready_flag(rows[1],fail=fail);_branch(rows,2,b'\x75',True,fail=fail)
    return {'readyFlagRva':flag,'completeReturnProved':True,'heapOrGlobalWrites':0,
            'savedAllocationRegisterUntouched':True,'initializationSlowPathEffectsProved':False}


def first_registration(image: Any, proof: dict, calls: dict, *, usage: Callable, fail: Callable) -> dict:
    """Complete method entry to its first Register call, not the whole registrar."""
    rows=authenticate(image,proof,['4053','4883EC20',None,None,None,None,'488BD8','4885C0',None,
        '33D2','488BC8',None,None,'83B9E000000000',None,None,'488BCB',None],taken={3,14},fail=fail)
    flag=ready_flag(rows[2],fail=fail)
    entry_branch=b'\x75' if len(bytes.fromhex(rows[3][1]))==2 else b'\x0f\x85'
    _branch(rows,3,entry_branch,True,fail=fail);_branch(rows,8,b'\x0f\x84',False,fail=fail)
    _branch(rows,14,b'\x75',True,fail=fail)
    for n,name in ((5,'allocation'),(11,'formatterConstructor'),(17,'register')):
        _call(rows,n,calls[name],fail=fail)
    usage(rows[4],'formatterClass','488B0D')
    usage(rows[12],'providerClass','488B0D')
    usage(rows[15],'closedRegisterMethodInfo','488B15')
    return {'readyFlagRva':flag,'sameAllocatedFormatterPassedToConstructorAndRegister':True,
            'registerFormatterRegister':'rcx','registerMethodInfoRegister':'rdx',
            'proofStopsAtFirstRegisterCall':True,'remainingRegistrarAndRegisterEffectsProved':False}


def deserialize_tail(image: Any, proof: dict, reader_entry: int, *, usage: Callable, fail: Callable) -> dict:
    rows=authenticate(image,proof,['48895C2408','57','4883EC20',None,'498BD8','488BFA',None,None,
        '83B9E000000000',None,'4533C0','488BD3','488BCF','488B5C2430','4883C420','5F',None],taken=set(),fail=fail)
    flag=ready_flag(rows[3],fail=fail)
    _branch(rows,6,b'\x74',False,fail=fail);_branch(rows,9,b'\x74',False,fail=fail)
    usage(rows[7],'wrapperClass','488B0D')
    _call(rows,16,reader_entry,tail=True,fail=fail)
    return {'readyFlagRva':flag,'sameReaderReferenceForwarded':True,'sameOutputReferenceForwarded':True,
            'staticReaderMethodInfoIsNull':True,'completeCallerFrameRestoredBeforeTail':True,
            'readerEntryRva':reader_entry,'readerReturnAndEffectsOwnedByReaderValidation':True,
            'actualFormatterVtableSelectionObserved':False}
