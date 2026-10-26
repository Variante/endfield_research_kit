"""Selected enum list, buffered header and matched scalar bridge programs.

The native owner authenticates registrations and complete window ownership.
Fresh scalar-pointer equality is a condition, never a provider selection.
"""
from __future__ import annotations

from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.normalization_instructions import decode_normalization_instructions
from .reference_conversion_sources import _target
from .value_list_sources import _guards


def _profile(image, proof, expected, *, fail):
    program=proof['program'];windows=proof['codeWindows']
    if len(program)!=len(expected) or not windows or program[0][0]!=windows[0]['startRva'] or program[-1][1]!='C3':
        fail('enum-list-selected-profile',len(expected),len(program))
    image.check_windows(windows,label='enumListSource')
    sp=0
    for i,((at,hexed),wanted) in enumerate(zip(program,expected,strict=True)):
        raw=bytes.fromhex(hexed)
        if wanted is not None and hexed!=wanted:fail('enum-list-transfer',{'position':i,'bytes':wanted},[at,hexed])
        if not any(w['startRva']<=at<at+len(raw)<=w['endRva'] for w in windows):
            fail('enum-list-owned-instruction',windows,[at,hexed])
        image.check_instruction_windows([[at,hexed]],label='enumListSource')
        rows=decode_normalization_instructions(image.mapper,raw,image.pe.image_base+at)
        if len(rows)!=1 or bytes.fromhex(rows[0]['bytes'])!=raw or rows[0]['text'].startswith('db '):
            fail('enum-list-complete-instruction','one understood instruction',[at,hexed])
        row=rows[0];flow=control_transfer(row);kind=flow['kind'];allowed={at+len(raw)}
        if kind in ('conditional','jump'):
            target=flow['target']-image.pe.image_base
            allowed={target} if kind=='jump' else allowed|{target}
        elif kind=='return':allowed=set()
        elif kind not in ('next','call','indirectCall','registerCall'):
            fail('enum-list-unreviewed-transfer','normal selected path',flow)
        if i+1<len(program) and program[i+1][0] not in allowed:
            fail('enum-list-selected-edge',sorted(allowed),program[i+1])
        text=row['text']
        if text.startswith('push '):sp-=8
        elif text.startswith('pop '):sp+=8
        elif text.startswith(('sub rsp, 0x','add rsp, 0x')):
            n=int(text.split(', ')[1],16);sp+=n if text.startswith('add') else -n
        if kind in ('call','indirectCall','registerCall') and ((8+sp)%16 or -sp<32):
            fail('enum-list-call-frame','aligned call with home space',sp)
        if kind=='return' and sp!=0:fail('enum-list-return-frame',0,sp)


def _call(proof,index,target,*,fail):
    at,hexed=proof['program'][index];raw=bytes.fromhex(hexed)
    if len(raw)!=5 or raw[0]!=0xe8 or _target(at,raw)!=target:
        fail('enum-list-actual-child-call',target,[at,hexed])


def validate_enum_list_sources(image, programs, offsets, entries, *, fail):
    if set(programs)!={'singleElement','twoElements','emptyExisting','nullList','bufferedHeader','enumBridge','spareCapacityAdd','bufferedScalar'}:
        fail('enum-list-program-membership','eight selected traces',sorted(programs))
    if set(offsets)!={'currentPtr','bufferLength','advancedCount','consumed','totalLength'} or any(type(v)!=int or not 0<=v<128 for v in offsets.values()) or len(set(offsets.values()))!=5:
        fail('enum-list-reader-fields','five distinct bounded named offsets',offsets)
    pointer,remaining,advanced,consumed,total=(offsets[k] for k in ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    header=['48895C2408','4889742410','57','4883EC20',f'8379{remaining:02X}04','488BF2','488BD9',None,
        f'488B43{pointer:02X}','8B08','890E',f'8B7B{remaining:02X}','83EF04',None,
        f'488343{pointer:02X}04',f'8343{advanced:02X}04',f'8343{consumed:02X}04',f'897B{remaining:02X}',
        f'486343{consumed:02X}',f'488B4B{total:02X}','486316','482BC8','448B06','483BCA',None,
        '488B5C2430','4183F8FF','488B742438','0F95C0','4883C420','5F','C3']
    _profile(image,programs['bufferedHeader'],header,fail=fail)
    _guards(programs['bufferedHeader'],[(7,b'\x0f\x8c',False),(13,b'\x0f\x88',False),(24,b'\x0f\x8c',False)],fail=fail)
    prefix=['4053','57','4154','4157','4883EC38','4C8BFA','4533E4','498BCF','4489642468','488D542468',
        '498BD9','498BF8',None,'84C0',None,'4889742470','48896C2460','4C896C2478','4C89742430',
        '488B4320','8B742468','488B88C0000000','4C3927',None,'488B4110','488B2F','4C396020',None,
        'FF451C','44896518',None,None,'4439A1E0000000',None,'488B4320','488B88C0000000','488B4918',None,
        '488BE8','458BF4','85F6',None]
    loop=['4489642420','4885ED',None,'4C8D4C2420','4D8BC7','488BD5',None,'4C8B27','448B6C2420','4D85E4',None,
        '488B4320','4C8B80C0000000','498B4030','4883782000',None,'488B4320','418BD5','498BCC',
        '4C8B80C0000000','4D8B4030',None,'41FFC6','41BC00000000','443BF6',None]
    suffix=['4C8B6C2478','488B6C2460','4C8B742430','488B742470','4883C438','415F','415C','5F','5B','C3']
    one=programs['singleElement'];p=one['program']
    _profile(image,one,prefix+loop+[None]+suffix,fail=fail)
    _profile(image,programs['twoElements'],prefix+loop+loop+[None]+suffix,fail=fail)
    _profile(image,programs['emptyExisting'],prefix+suffix,fail=fail)
    if programs['twoElements']['program']!=p[:42]+p[42:68]*2+p[68:] or programs['emptyExisting']['program']!=p[:42]+p[69:]:
        fail('enum-list-identical-loop-and-empty','same complete repeated loop and restored exit',programs)
    _guards(one,[(14,b'\x0f\x84',False),(23,b'\x0f\x85',True),(27,b'\x75',True),
        (33,b'\x0f\x84',False),(41,b'\x7f',True),(44,b'\x74',False),(52,b'\x74',False),(57,b'\x0f\x84',False)],fail=fail)
    _guards(programs['emptyExisting'],[(41,b'\x7f',False)],fail=fail)
    back_at,back_hex=p[67];back=bytes.fromhex(back_hex)
    if back[:1]!=b'\x7c' or _target(back_at,back)!=p[42][0] or p[68][0]!=back_at+len(back):
        fail('enum-list-back-edge','signed incremented index < saved count',p[64:69])
    for index in (30,68):
        at,hexed=p[index];raw=bytes.fromhex(hexed)
        if raw[0]!=0xe9 or len(raw)!=5 or _target(at,raw)!=p[index+1][0]:fail('enum-list-join','actual jump',p[index])
    usage=bytes.fromhex(p[31][1])
    if len(usage)!=7 or usage[:3]!=b'\x48\x8b\x0d':fail('enum-list-provider-usage','complete RIP QWORD load',p[31])
    _call(one,12,entries['header'],fail=fail);_call(one,37,entries['provider'],fail=fail)
    _call(one,48,entries['bridge'],fail=fail);_call(one,63,entries['add'],fail=fail)
    null=programs['nullList'];_profile(image,null,prefix[:15]+['488BCF','4C8927',None,'90',None]+suffix[4:],fail=fail)
    if null['program'][:15]!=p[:15]:fail('enum-list-null-prefix','same actual count call',null)
    _guards(null,[(14,b'\x0f\x84',True)],fail=fail)
    _call(null,17,entries['barrier'],fail=fail)
    bridge=['48895C2408','4889742410','57','4883EC20','488B0A','498BF1','498BD8','488BFA',None,
        '488B07','4C8B9090010000','4C8B8898010000',None,'4C3BD0',None,None,'4C3BD0',None,
        f'837B{remaining:02X}04',None,f'488B43{pointer:02X}','8B00','8906',f'8B7B{remaining:02X}','83EF04',None,
        f'488343{pointer:02X}04',f'8343{advanced:02X}04',f'8343{consumed:02X}04',f'897B{remaining:02X}',
        '488B5C2430','488B742438','4883C420','5F','C3']
    b=programs['enumBridge'];_profile(image,b,bridge,fail=fail)
    _guards(b,[(14,b'\x75',True),(17,b'\x74',True),(19,b'\x0f\x8c',False),(25,b'\x0f\x88',False)],fail=fail)
    pointers=[]
    for index in (12,15):
        at,hexed=b['program'][index];raw=bytes.fromhex(hexed)
        if len(raw)!=7 or raw[:3]!=b'\x48\x8d\x05':fail('enum-list-scalar-pointer','actual RIP LEA',b['program'][index])
        pointers.append(at+7+int.from_bytes(raw[3:],'little',signed=True))
    if pointers[1]!=entries['scalar'] or pointers[0]==pointers[1]:fail('enum-list-selected-scalar-identity',entries['scalar'],pointers)
    _call(b,8,entries['classPrepare'],fail=fail)
    add=['48895C2408','4889742410','57','4883EC20','FF411C','498BF0','488B4110','8BFA','4C634918','488BD9',
        '4885C0',None,'443B4818',None,'418D4901','894B18','443B4818',None,'4289548820',
        '488B5C2430','488B742438','4883C420','5F','C3']
    _profile(image,programs['spareCapacityAdd'],add,fail=fail)
    _guards(programs['spareCapacityAdd'],[(11,b'\x74',False),(13,b'\x73',False),(17,b'\x73',False)],fail=fail)
    # Reuse the existing exact scalar transfer, with this independent entry's bytes.
    from .value_list_sources import validate_buffered_dword_output_formatter
    scalar=validate_buffered_dword_output_formatter(image,programs['bufferedScalar'],offsets,fail=fail)
    for role,key in (('list','singleElement'),('header','bufferedHeader'),('bridge','enumBridge'),('add','spareCapacityAdd'),('scalar','bufferedScalar')):
        if programs[key]['program'][0][0]!=entries[role]:fail('enum-list-actual-entry',entries[role],programs[key]['program'][0])
    return {'status':'selected-enum-list-header-matched-bridge-and-output-control-proved',
        'selectedPathInstructions':{k:len(v['program']) for k,v in programs.items()},
        'headerWireBytes':4,'headerReturnALIsCountNotMinusOne':True,'headerGuardMultiplier':1,
        'headerAloneGuaranteesAllElementBytesAvailable':False,'otherNegativeCountsRejected':False,
        'countSavedInNonvolatileRegister':'rsi','loopIndexRegister':'r14d','loopInstructions':26,
        'freshBridgePointerComparisonRvas':pointers,'freshMatchedScalarEntryRva':entries['scalar'],
        'bridgeMatchedPathWireBytes':4,'scalarTransfer':scalar,
        'addPreservesOutputDwordBits':True,'arrayStrideBytes':4,'arrayDataOffset':32,
        'positiveCountIterationsConditionallyEqualCount':True,'zeroOrOtherNegativeCountSkipsLoop':True,
        'wireBytesForPositiveCountConditionally':'4 + 4 * count',
        'nullOutputStoreBeforeBarrierCallProved':True,'nullOutputAtReturnUnconditionallyProved':False,
        'concreteDamageTypeSharingSelected':False,'runtimeProviderObserved':False,
        'positiveStoredGrammarAdmitted':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
