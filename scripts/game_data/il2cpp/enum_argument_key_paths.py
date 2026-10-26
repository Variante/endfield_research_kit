"""Exact current kind17 argument hash and equality source paths.

The complete selected interner entry-to-hash prefix owns its actual argument
hash call. Its two raw comparison-call candidates select a separate compared
body, without claiming their enclosing control or argument origins here.
Ordinary kind17 inputs with the same raw byref bit hash
the first data QWORD with the same literal polynomial; their selected equality
path returns zero exactly when that QWORD is equal. No pointer-address identity
between type records is required by those source paths. Both complete normal
frames and the owned dispatch-table word remain explicit.

This does not establish what data QWORD a live placeholder/class record holds,
whether an initialized interner cache contains a particular instantiation, or
which provider/MethodInfo/callback receives it. Stable disjoint input records,
coherent class/registration state and compatible normal helpers remain
conditions. Concrete enum sharing, collection framing and whole owners stay
unresolved; an equal key is not an admitted formatter callback.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-argument-key-paths.v1'
LABEL='enumArgumentKeyPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def key_hash(data,byref,prime):
    need('literal-key-hash-domain',type(data)is int and 0<=data<1<<64 and type(byref)is int and byref in(0,1)
        and type(prime)is int and 0<prime<1<<31)
    return((17*prime+byref)*prime+data)&((1<<64)-1)


def hash_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('4053','4883ec20','480fbe410a','8b5908','4869d0');prime=int.from_bytes(g.read(4),'little',signed=True)
    need('positive-current-hash-prime',0<prime<1<<31)
    g.take('0fb6410a','48c1eb1d','83e301','4803da','3c12');g.branch('75',True,1)
    g.take('3c11');g.branch('74',True,1)
    g.take('4869c3');need('same-current-polynomial-prime',int.from_bytes(g.read(4),'little',signed=True)==prime)
    g.take('480301','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,inputKind=17,byrefMaskDwordBit=29,dataBytes=8,prime=prime,
        result='((17 * prime + ((flagsDword >>29)&1)) * prime + dataQword) modulo2^64',
        kindAndByrefAndDataDetermineHash=True,typeRecordPointerAddressHashed=False,
        opaqueCalls=0,entryRspRestored=True,nonvolatileRbxRestored=True,normalReturn=True)


def compare_program(regions,entry,*,image_base,equal=True):
    need('literal-equality-path',type(equal)is bool)
    g=BytesPath(regions,entry)
    g.take('4883ec28','4c8bda','48895c2430');need('selected-comparator-image-base',g.relative('488d15')==image_base)
    g.take('4c8bd1','66660f1f840000000000','410fb6430a','4138420a');g.branch('0f85',False)
    g.take('418b4308','418b4a08','c1e81d','c1e91d','83e001','83e101','3bc8');g.branch('0f85',False)
    g.take('410fbe420a','83c0f1','83f80f');g.branch('0f87',False)
    g.take('4898','8b8c82');table=image_base+int.from_bytes(g.read(4),'little',signed=True);g.take('4803ca','ffe1')
    # Signed kind17 minus15 selects exactly slot2 of this actual table.
    slot=table+8;need('owned-kind17-compare-target-word',all(slot+i in g.bytes for i in range(4)))
    raw=bytes(g.bytes[slot+i]for i in range(4));target=image_base+int.from_bytes(raw,'little',signed=True)
    need('owned-kind17-compare-code',target in g.bytes);g.at=target
    g.take('498b03','493902');g.branch('75',not equal,1)
    if equal:g.take('33db')
    else:g.take('493902','bb01000000','baffffffff','0f42da')
    g.take('8bc3','488b5c2430','4883c428','c3')
    return dict(selectedBytes=g.seen,inputKinds=[17,17],sameRawByrefBitRequired=True,byrefMaskDwordBit=29,
        dataBytes=8,dataEqualRequired=equal,returnedEax=0 if equal else'unsigned left.data < right.data ? -1 : 1',
        dataEqualitySelectsZero=True,typeRecordPointerIdentityCompared=False,tableSlot=slot,tableHex=raw.hex().upper(),
        selectedTarget=target,opaqueCalls=0,entryRspRestored=True,nonvolatileRbxRestored=True,normalReturn=True)


def _calls(body,prefix):
    pattern=bytes.fromhex(prefix+'e8');found=[]
    for at,raw in body['regions']:
        offset=raw.find(pattern)
        while offset>=0:
            site=at+offset+len(pattern)-1;target=site+5+int.from_bytes(raw[offset+len(pattern):offset+len(pattern)+4],'little',signed=True)
            found.append(dict(instructionVa=site,rawHex=raw[offset+len(pattern)-1:offset+len(pattern)+4].hex().upper(),targetVa=target))
            offset=raw.find(pattern,offset+1)
    need('bounded-actual-child-calls:'+prefix,0<len(found)<=4)
    need('one-exact-child-target:'+prefix,len({r['targetVa']for r in found})==1)
    return found


def interner_hash_prefix(regions,entry):
    """Selected initialized-table/count1 entry through actual argument hash E8."""
    g=BytesPath(regions,entry)
    g.take('89542410','53','55','56','57','4154','4155','4156','4157','4883ec58','8bea','4c8bf9',
        '89542420','48894c2428');mutex=g.relative('488d05');g.take('48898424a0000000')
    need('same-owned-mutex-cell',g.relative('488b0d')==mutex);lock=g.relative('ff15');g.take('90')
    table_end=g.relative('488b05');table_begin=g.relative('483b05');g.branch('75',True,1)
    g.take('33ed','4889ac24a0000000');capacity=g.relative('4c8b1d')
    g.take('49ffcb','4c899c24b0000000','8b5c2420','8bfb','4533c0','85db');g.branch('74',False,1)
    g.take('4c8b542428','90','4b8b0cc2');site=g.at;target=g.relative('e8')
    return dict(selectedBytes=g.seen,mutexCell=mutex,lockIatCell=lock,tableEndCell=table_end,tableBeginCell=table_begin,
        tableNonemptyRequired=True,capacityCell=capacity,inputCount1Required=True,argumentOrdinal=0,
        argumentRcx='unchanged saved input buffer[0]',hashCallSite=site,hashTarget=target,
        inputBufferAndCountSavedBeforeOpaqueLock=True,compatibleDisjointNormalLockRequired=True,
        entryRspDeltaAtCall=-152,normalCallHomeAndAlignmentProved=True,entryToCallControlProved=True,
        remainderControlAndNormalReturnProved=False)


def derive(image,pins,**selection_arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_normalizer_selection_paths import derive as selection_source
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base
    selected=selection_source(image,pins,**selection_arguments)
    entry=selected['proof']['normalizer']['actualCalls']['internArguments'];intern=owned(image,entry)
    prefix=interner_hash_prefix(intern['regions'],entry)
    hashing=_calls(intern,'4b8b0cc2');comparisons=_calls(intern,'488b0b')
    need('current-interner-hash-and-two-compare-sites',len(hashing)==1 and len(comparisons)==2)
    need('actual-entry-prefix-hash-call',hashing[0]['instructionVa']==prefix['hashCallSite']and hashing[0]['targetVa']==prefix['hashTarget'])
    hash_body=owned(image,hashing[0]['targetVa']);compare_body=owned(image,comparisons[0]['targetVa'])
    hashed=hash_program(hash_body['regions'],hash_body['pointer'])
    compared=[compare_program(compare_body['regions'],compare_body['pointer'],image_base=base,equal=equal)for equal in(True,False)]
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        cases=selected['cases'],proof=dict(normalizerSelection=selected,actualInternerWindows=intern['windows'],
            hashCallerPrefix=prefix,actualHashCalls=hashing,rawCompareCallCandidates=comparisons,hashWindows=hash_body['windows'],hashProgram=hashed,
            compareWindows=compare_body['windows'],comparePrograms=compared),
        sameKindByrefDataImplyEqualHashAndZeroComparator=True,internerCompareCallControlAndArgumentsProved=False,livePlaceholderDataIdentityProved=False,
        genericInternedIdentityProved=False,concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete selected current interner entry-to-hash prefix and actual hash target, raw owned compare-call candidates, complete selected kind17 hash/equal/unequal paths/frames, owned dispatch word and exact integer key relations.',
            conditional=__doc__,structuralOnly='Native runtime generic argument representation.',
            unresolved=['interner comparison-call control and argument origins','live placeholder/type record data and alias identity','initialized interner/cache result identity',
                'actual nominal provider/formatter/MethodInfo callback selection','collection/wire/parent/EOF']))))
