"""Derive the reviewed UTF8 source profile from one explicitly selected image.

All addresses, usage cells and complete unwind-owned windows are read afresh.
The owning source validator must accept the candidate before publication.
"""
from __future__ import annotations
import hashlib
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.string_source_instructions import decode_utf8_decoder_instructions as decode


def derive_contract(image,pins):
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    unwind=image.unwind_index
    def method(owner,name,parameters):
        rows=[m for m in md.methods_for(ctx.index.types[owner]) if md.string(m.name_index)==name
              and [ctx.type_name(p.type_index) for p in md.parameters_for(m)]==parameters]
        if len(rows)!=1:raise ValueError(f'utf8Derive.method:{owner}.{name}: candidates={len(rows)}')
        m=rows[0];return [m.index,owner,name,image.method_pointer_va(m)-base]
    methods={key:method(owner,name,params) for key,owner,name,params in (
        ('readString','MemoryPack.MemoryPackReader','ReadString',[]),('readUtf8','MemoryPack.MemoryPackReader','ReadUtf8',['int']),
        ('getNextSpan','MemoryPack.MemoryPackReader','GetNextSpan',['int']),('getUtf8','System.Text.Encoding','get_UTF8',[]),
        ('spanString','System.Text.Encoding','GetString',['System.ReadOnlySpan`1<byte>']),('pointer','System.Text.Encoding','GetString',['byte*','int']),
        ('constructor','System.Text.UTF8Encoding','.ctor',['bool','bool']),('selectedInitializer','System.Text.UTF8Encoding','SetDefaultFallbacks',[]),
        ('count','System.Text.UTF8Encoding','GetCharCount',['byte*','int','System.Text.DecoderNLS']),
        ('fill','System.Text.UTF8Encoding','GetChars',['byte*','int','char*','int','System.Text.DecoderNLS']),
        ('insufficient','MemoryPack.MemoryPackSerializationException','ThrowInsufficientBufferUnless',['int']))}
    bodies={};groups={}
    def body(role,entry):
        ranges=unwind.family(entry)['ranges'];ranges.sort(key=lambda r:(r['runtimeTriple'][0]!=entry,r['runtimeTriple'][0]))
        windows=[];decoded=[]
        for r in ranges:
            start,end,_=r['runtimeTriple'];raw=image.pe.bytes_at_va(base+start,end-start)
            windows.append({'startRva':start,'endRva':end,'sha256':hashlib.sha256(raw).hexdigest().upper()})
            decoded.append(decode(image.mapper,raw,base+start))
        bodies[role]={'entryRva':entry,'codeWindows':windows};groups[role]=decoded
        return decoded[0]
    def calls(rows):
        return [int(r['va'],16)-base+5+int.from_bytes(bytes.fromhex(r['bytes'])[1:],'little',signed=True)
                for r in rows if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
    def rip(row):
        raw=bytes.fromhex(row['bytes'])
        if len(raw)!=7 or raw[2]&0xc7!=5:raise ValueError('utf8Derive.RIP-usage')
        return int(row['va'],16)-base+7+int.from_bytes(raw[3:],'little',signed=True)
    def usage(row):
        return derive_typed_usage_context(image,int(row['va'],16)-base,label='utf8Derive')
    r=body('readString',methods['readString'][3]);u=body('readUtf8',methods['readUtf8'][3]);g=body('encodingGetter',methods['getUtf8'][3])
    pc=body('pointerString',methods['pointer'][3]);body('constructor',methods['constructor'][3])
    rc,uc,gc,pcc=calls(r),calls(u),calls(g),calls(pc)
    if [len(rc),len(uc),len(gc),len(pcc)]!=[2,6,4,4]:raise ValueError('utf8Derive.selected-call-inventory')
    body('header',rc[1]);body('advance',uc[-1]);sp=body('spanCreation',uc[1]);sg=body('spanGetString',methods['spanString'][3])
    vh=body('virtualDispatch',gc[2]);body('count',methods['count'][3]);body('fill',methods['fill'][3])
    ci=next(i for i,row in enumerate(vh) if bytes.fromhex(row['bytes'])==b'\x41\xff\xd0');last=vh[ci+1]
    bodies['virtualDispatch']['prefixEndRva']=int(last['va'],16)-base+len(bytes.fromhex(last['bytes']))
    cc=calls([row for group in groups['pointerString'][1:] for row in group])
    if len(cc)!=14:raise ValueError('utf8Derive.exception-call-inventory')
    contexts={'span':usage(next(row for row in u if bytes.fromhex(row['bytes'])[:3]==b'\x4c\x8b\x0d')),
              'encodingType':usage(g[2]),'allocationType':usage(g[15]),
              'emptyString':usage(next(row for row in pc if bytes.fromhex(row['bytes'])[:3]==b'\x48\x8b\x05'))}
    offsets=runtime_type_field_offsets(md,image.pe,image.registration,ctx.index.types['MemoryPack.MemoryPackReader'].index)
    from scripts.game_data.il2cpp.string_source_bindings import validate_encoding_bindings
    fields=validate_encoding_bindings(image,{k:contexts[k] for k in ('span','encodingType','allocationType')})
    opaque={'metadataInit':rc[0],'nullThrow':gc[1],'allocate':gc[0],'barrier':gc[3],
            'classInit':calls(sp)[0],'prepareClass':pcc[0],'allocateString':pcc[1],
            'allocateException':cc[2],'rangeConstructor':cc[4],'nullConstructor':cc[11],'throwException':cc[6],
            'advanceFallback':calls(groups['header'][1])[1]}
    loads=[row for row in pc if bytes.fromhex(row['bytes'])[:3]==b'\x4c\x8b\x90']
    if len(loads)!=2:raise ValueError('utf8Derive.virtual-call-inventory')
    layout={key:int.from_bytes(bytes.fromhex(row['bytes'])[3:],'little') for key,row in zip(('countFunction','fillFunction'),loads)}
    layout['firstChar']=ctx.field('System.String::_firstChar')[2]
    result={'schema':'endfield.memorypack-utf8-source-helper-native.v2','status':'exact-current-build','nativeInputs':pins,
            'wireEncoding':'nullable-int32-byte-length-valid-utf8','sourceHelpers':[methods['readString'][3]],
            'methods':methods,'bodies':bodies,'opaqueCalls':opaque,'readerFieldOffsets':{n:offsets[n]-16 for n in ('currentPtr','bufferLength','advancedCount','consumed','totalLength')},
            'encodingFields':fields,'contexts':contexts,'pointerLayout':layout,'emptyLiteral':{'usageCellRva':rip(r[5]),'value':''},
            'evidenceBoundary':{
                'exact':'Pinned native identities, complete unwind-owned byte ranges, selected local edges and original signed-length/cursor programs.',
                'direct':'Typed byte-span context and registered entry, UTF8 allocation/cache and constructor-equivalent flags, standard Encoding.GetString API calls and internal method declarations, count/allocation/fill/String return transfers.',
                'conditional':'Buffered normal paths, stable valid disjoint storage, zeroed compatible allocation, matched initialized runtime type/context/cache and ordinary ABI-preserving callees. The virtual generic path excludes every checked optimized target.',
                'decoderScope':'Original bounded null, empty and valid UTF8 spans only, decoded by the standard UTF8 contract. Native Unicode algorithm reconstruction, invalid-byte replacement/error parity and live execution are not claimed.',
                'callerRequirement':'Each field must independently prove this actual source helper and its source-to-destination span; no whole-corpus admission follows.',
                'unresolved':['live cache/receiver/provider selection','allocator/initializer/barrier effects','runtime loading or IFix changes','evaluated field meaning']}}
    from scripts.game_data.memorypack.utf8_source_helper import _validate_native
    _validate_native(image,result)
    return result
