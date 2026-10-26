"""Selected native proof and bounded decoding of stored UTF-8 string spans.

This reader accepts null, empty and valid UTF-8 payloads only. Native invalid
byte replacement, execution, source loading and evaluated keys are outside
its evidence boundary. Callers separately prove their field's source call.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, native_validation_failure
from scripts.game_data.il2cpp import string_source_programs as programs
from scripts.game_data.il2cpp.string_source_bindings import validate_encoding_bindings, validate_span_entry, validate_pointer_decoder_bindings
from scripts.game_data.il2cpp.string_source_instructions import decode_utf8_decoder_instructions
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
from scripts.game_data.il2cpp.type_data_initialization_control import _complete
from scripts.game_data.il2cpp.formatter_composition import _vtable
from scripts.game_data.memorypack.core import CONTRACTS_DIR

LABEL = "memorypackUtf8SourceHelper"
CONTRACT_PATH = CONTRACTS_DIR / "memorypack_utf8_source_helper_native.json"


def _contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value, _ = read_reviewed_contract(path,
        schema="endfield.memorypack-utf8-source-helper-native.v2",
        status="exact-current-build", label=LABEL)
    if (set(value) != {'schema','status','nativeInputs','wireEncoding','sourceHelpers','methods','bodies',
                       'opaqueCalls','readerFieldOffsets','encodingFields','contexts','pointerLayout','emptyLiteral','evidenceBoundary'}
            or value.get("wireEncoding") != "nullable-int32-byte-length-valid-utf8"
            or not value.get("sourceHelpers") or not value.get("bodies") or not value.get("methods")
            or value.get("emptyLiteral", {}).get("value") != ""):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def _need(check, expected, actual):
    if expected != actual:
        raise ValueError(f'{LABEL}.native:{check}: expected={str(expected)[:350]} actual={str(actual)[:350]}')


def _validate_native(image, contract):
    """Prove stored framing and standard Encoding API joins, not its Unicode implementation."""
    base=image.pe.image_base; methods=contract['methods']; bodies=contract['bodies'];selected=NativeReferenceContext(image)
    expected={'readString':('MemoryPack.MemoryPackReader','ReadString'), 'readUtf8':('MemoryPack.MemoryPackReader','ReadUtf8'),
              'getNextSpan':('MemoryPack.MemoryPackReader','GetNextSpan'), 'getUtf8':('System.Text.Encoding','get_UTF8'),
              'spanString':('System.Text.Encoding','GetString'), 'pointer':('System.Text.Encoding','GetString'),
              'constructor':('System.Text.UTF8Encoding','.ctor'), 'selectedInitializer':('System.Text.UTF8Encoding','SetDefaultFallbacks'),
              'count':('System.Text.UTF8Encoding','GetCharCount'), 'fill':('System.Text.UTF8Encoding','GetChars'),
              'insufficient':('MemoryPack.MemoryPackSerializationException','ThrowInsufficientBufferUnless')}
    _need('method-roles',set(expected),set(methods))
    for role,row in methods.items():
        _need(role+'.method',list(expected[role]),row[1:3]);image.validate_method_row(row,label=LABEL)
    for role,parameters in {'readString':[],'readUtf8':['int'],'getNextSpan':['int'],'getUtf8':[],
                            'spanString':['System.ReadOnlySpan`1<byte>'],'constructor':['bool','bool'],
                            'selectedInitializer':[],'insufficient':['int']}.items():
        method=image.metadata.methods[methods[role][0]];declared=list(image.metadata.parameters_for(method))
        _need(role+'.parameters',parameters,[selected.type_name(p.type_index) for p in declared])
        _need(role+'.static',role in ('getUtf8','insufficient'),bool(method.flags&0x10))
        for type_index in ([] if role=='getNextSpan' else [method.return_type])+[p.type_index for p in declared]:
            _need(role+'.ordinary-abi',0,image.pe.bytes_at_va(selected.type_pointer(type_index),16)[11]&0x7f)
    initializer=image.metadata.methods[methods['selectedInitializer'][0]]
    _need('initializer-slot',5,initializer.slot);_need('initializer-virtual',True,bool(initializer.flags&0x40))
    _vtable(image,initializer.declaring_type,initializer.slot,initializer.index,LABEL)
    roles={'readString','readUtf8','header','advance','spanCreation','spanGetString','encodingGetter','constructor','pointerString','virtualDispatch','count','fill'}
    _need('body-roles',roles,set(bodies))
    rva,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda r,n:image.pe.bytes_at_va(base+r,n),table_rva=rva,image_size=size)
    groups={}
    for role,body in bodies.items():
        windows=body['codeWindows'];family=unwind.family(body['entryRva'])
        _need(role+'.primary',body['entryRva'],windows[0]['startRva'])
        _need(role+'.owned-ranges',sorted((r['startRva'],r['endRva']) for r in windows),sorted(tuple(r['runtimeTriple'][:2]) for r in family['ranges']))
        image.check_windows(windows,label=LABEL+'.'+role)
        groups[role]=[decode_utf8_decoder_instructions(image.mapper,image.window_bytes(w),base+w['startRva']) for w in windows]
    for role,key in (('readString','readString'),('readUtf8','readUtf8'),('spanGetString','spanString'),('encodingGetter','getUtf8'),
                     ('constructor','constructor'),('pointerString','pointer'),('count','count'),('fill','fill')):
        _need(role+'.entry',methods[key][3],bodies[role]['entryRva'])
    _need('source-helpers',[bodies['readString']['entryRva']],contract['sourceHelpers'])
    td=selected.index.types['MemoryPack.MemoryPackReader']
    _need('reader-value-type',True,selected.is_value_type('MemoryPack.MemoryPackReader'))
    offsets=runtime_type_field_offsets(image.metadata,image.pe,image.registration,td.index)
    fields={name:offsets[name]-16 for name in contract['readerFieldOffsets']}
    _need('reader-fields',contract['readerFieldOffsets'],fields)
    contexts=contract['contexts']; encoding=validate_encoding_bindings(image,{k:contexts[k] for k in ('span','encodingType','allocationType')})
    _need('encoding-fields',contract['encodingFields'],encoding)
    validate_span_entry(image,contexts['span'],base+bodies['spanCreation']['entryRva'])
    symbols={k:base+v for k,v in contract['opaqueCalls'].items()}
    for key in ('readUtf8','getNextSpan','getUtf8','insufficient'):symbols[key]=base+methods[key][3]
    for key,role in (('header','header'),('advance','advance'),('createSpan','spanCreation'),('getString','spanGetString'),('initializeEncoding','virtualDispatch')):
        symbols[key]=base+bodies[role]['entryRva']
    symbols['pointerGetString']=base+methods['pointer'][3];symbols['selectedMethod']=base+methods['selectedInitializer'][3]
    def one(role):
        _need(role+'.single-range',1,len(groups[role]));return groups[role][0]
    def split(role):
        normal=[];cold=[]
        for rows in groups[role]:
            if not normal or int(rows[0]['va'],16)==int(normal[-1]['va'],16)+len(bytes.fromhex(normal[-1]['bytes'])):normal.extend(rows)
            else:cold.extend(rows)
        return normal,cold
    literal=contract['emptyLiteral'];cell=base+literal['usageCellRva'];word=image.pe.u64_at_va(cell)
    section=image.metadata.sections['stringLiteral'];data_section=image.metadata.sections['stringLiteralData'];index=(word>>1)&0xfffffff
    if word>0xffffffff or not word&1 or word>>29!=5 or index>=section.size//8:raise ValueError(f'{LABEL}.native:empty-literal-usage')
    length,start=struct.unpack_from('<ii',image.metadata.buf,section.offset+index*8)
    if length!=0 or not 0<=start<=data_section.size:raise ValueError(f'{LABEL}.native:empty-literal-value')
    proofs={'header':programs.prove_collection_header(*split('header'),fields,symbols),
            'readString':programs.prove_string_reader(one('readString'),symbols,cell),
            'readUtf8':programs.prove_utf8_reader(one('readUtf8'),fields,symbols,base+contexts['span']['usageCellRva']),
            'span':programs.prove_span_creation(one('spanCreation'),symbols),
            'spanString':programs.prove_span_get_string(one('spanGetString'),symbols),
            'advance':programs.prove_reader_advance(*split('advance'),fields,symbols),
            'constructor':programs.prove_utf8_constructor(one('constructor'),encoding,symbols),
            'cache':programs.prove_utf8_cache(one('encodingGetter'),encoding,symbols,base+contexts['encodingType']['usageCellRva'],base+contexts['allocationType']['usageCellRva']),
            'pointer':programs.prove_pointer_get_string(*split('pointerString'),contract['pointerLayout'],symbols,base+contexts['emptyString']['usageCellRva'])}
    body=bodies['virtualDispatch'];end=body['prefixEndRva'];window=body['codeWindows'][0]
    if not body['entryRva']<end<=window['endRva']:raise ValueError(f'{LABEL}.native:virtual-prefix-range')
    prefix=decode_utf8_decoder_instructions(image.mapper,image.pe.bytes_at_va(base+body['entryRva'],end-body['entryRva']),base+body['entryRva'])
    proofs['virtualPrefix']=programs.prove_virtual_slot_prefix(prefix,symbols)
    validate_pointer_decoder_bindings(image,{k:methods[k] for k in ('pointer','count','fill')},contract['pointerLayout'],proofs['virtualPrefix']['vtableOffset'],contexts['emptyString'])
    for role in ('count','fill'):
        _complete([r for group in groups[role] for r in group],base+bodies[role]['entryRva'])
    return proofs


def validate_current_native_contract(*, gameassembly: Path, metadata: Path, contract_path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = _contract(contract_path); pins = contract["nativeInputs"]
    gate = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": pins}
    unity = Path(gate.gameassembly).parent / "UnityPlayer.dll"

    def unity_matches() -> bool:
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins["UnityPlayer.dll"]

    if not unity_matches():
        return {"status": "mismatched" if unity.is_file() else "missing",
                "detail": "UnityPlayer.dll missing or mismatched", "nativeInputs": pins}
    try:
        _validate_native(open_native_image(gate.gameassembly, gate.metadata),contract)
    except (ValueError,KeyError,IndexError,TypeError,struct.error) as error:
        return native_validation_failure(error,label=LABEL,source_path=contract_path)
    after = check_installed_native_inputs(pins["GameAssembly.dll"], pins["global-metadata.dat"],
        gameassembly=gameassembly, metadata=metadata)
    if after.status != "validated" or not unity_matches():
        return {"status": after.status if after.status != "validated" else "mismatched" if unity.is_file() else "missing",
                "detail": "native inputs changed during validation", "nativeInputs": pins}
    return {"status": "validated", "nativeInputs": pins,
        "sourceHelpers": contract["sourceHelpers"], "wireEncoding": contract["wireEncoding"],
        "evidenceBoundary": contract["evidenceBoundary"]}


def decode_source_string(data: bytes, *, source: str, digest: str, start: int, end: int,
                         source_helper_rva: int, native_validation: dict[str, Any]) -> dict[str, Any]:
    """Decode one original field span whose independently proved call uses this helper."""
    contract = _contract()
    if (native_validation.get("status") != "validated"
            or native_validation.get("nativeInputs") != contract["nativeInputs"]
            or native_validation.get("sourceHelpers") != contract["sourceHelpers"]
            or native_validation.get("wireEncoding") != contract["wireEncoding"]
            or source_helper_rva not in contract["sourceHelpers"]
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    if end - start < 4:
        raise ValueError(f"{LABEL}.decode:short-length")
    count = struct.unpack_from("<i", data, start)[0]
    if count < -1 or end != start + 4 + max(count, 0):
        raise ValueError(f"{LABEL}.decode:length-or-eof")
    try:
        value = None if count == -1 else data[start + 4:end].decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"{LABEL}.decode:invalid-utf8") from error
    return {"schema": "endfield.memorypack-source-string-receipt.v1",
        "source": source, "logicalSha256": digest.upper(), "start": start, "end": end,
        "rawHex": data[start:end].hex().upper(), "byteLength": count, "value": value,
        "sourceHelperRva": source_helper_rva, "nativeStatus": "validated",
        "wholeStoredSpanExact": True, "storedStringValueExact": True,
        "runtimeMeaningExact": False}
