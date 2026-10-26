"""Authenticate a byte-mask leaf that returns its input or tail-jumps.

This grammar reads the complete reviewed window directly. It does not use a
decoder that can resume inside an unrecognized instruction, assign names to
anonymous fields, or invent a PE function boundary.
"""
from __future__ import annotations

import hashlib

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from .instance_string_field_calls import _require
from .native_image import read_reviewed_contract


def validate_leaf(raw: bytes, *, entry_va: int) -> dict:
    _require(type(raw) is bytes and len(raw)==20,
             'flag-leaf-length','complete 20-byte terminal grammar',len(raw))
    _require(type(entry_va) is int and 0<entry_va<2**64-20,
             'flag-leaf-entry','positive bounded native virtual address',entry_va)
    _require(raw[:2]==b'\xf6\x81','flag-leaf-test',
             'TEST BYTE [RCX+disp32],imm8 (F6 /0)',raw[:7].hex())
    displacement=int.from_bytes(raw[2:6],'little',signed=True);mask=raw[6]
    _require(displacement>=0 and mask!=0,'flag-leaf-mask',
             'nonnegative anonymous byte displacement and nonzero mask',[displacement,mask])
    _require(raw[7:9]==b'\x74\x05','flag-leaf-zero-edge',
             'JE from byte-test flags to exact external tail-jump instruction',raw[7:9].hex())
    _require(raw[9:12]==b'\x48\x8b\xc1','flag-leaf-return-alias',
             'MOV RAX,RCX preserves incoming reference',raw[9:12].hex())
    _require(raw[12:14]==b'\xeb\x05','flag-leaf-return-edge',
             'JMP to exact RET after external tail jump',raw[12:14].hex())
    _require(raw[14]==0xe9,'flag-leaf-tail','E9 signed rel32',raw[14:19].hex())
    _require(raw[19]==0xc3,'flag-leaf-terminal','RET at exact window end',raw[19:].hex())
    tail=entry_va+19+int.from_bytes(raw[15:19],'little',signed=True)
    _require(0<tail<2**64 and not entry_va<=tail<entry_va+20,
             'flag-leaf-external-tail','positive external destination outside proved window',tail)
    spans=((0,7,'TEST BYTE [RCX+disp32],imm8'),(7,9,'JE external-tail-entry'),
           (9,12,'MOV RAX,RCX'),(12,14,'JMP local-return'),
           (14,19,'JMP external signed-rel32 target'),(19,20,'RET'))
    return {'completeReviewedWindowControlProgramProved':True,
        'instructionBoundariesProved':True,
        'instructions':[{'va':entry_va+a,'offset':a,'bytes':raw[a:b].hex().upper(),'text':text}
                        for a,b,text in spans],
        'flagTest':{'anonymousByteOffset':displacement,'mask':mask,
                    'condition':'valid readable byte at incoming RCX plus observed displacement',
                    'fieldMeaningProved':False},
        'nonzeroMaskReturn':{'rax':'unchanged incoming RCX reference','returnVa':entry_va+19,
                            'externalTailSkipped':True,'callsExecuted':0},
        'zeroMaskTail':{'targetVa':tail,'jumpVa':entry_va+14,
                        'argumentRegistersPreserved':['RCX','RDX','R8','R9'],
                        'stackPointerPreserved':True,'returnAddressPreserved':True,
                        'targetAlgorithmProved':False},
        'runtimeExecutionKnown':False,'contextSlotTypeMeaningProved':False,
        'evidenceBoundary':'conditional'}


def prove_window(index, *, entry_va: int, declaration: dict) -> dict:
    name=declaration.get('contract');schema=declaration.get('schema')
    _require(isinstance(name,str) and name.endswith('.json') and '/' not in name and '\\' not in name and ':' not in name,
             'flag-leaf-contract-name','one reviewed contract filename',name)
    _require(isinstance(schema,str) and schema.startswith('endfield.'),
             'flag-leaf-contract-schema','explicit reviewed contract schema',schema)
    contract,digest=read_reviewed_contract(CONTRACTS_DIR/name,schema=schema,label='flagLeaf')
    image=index.image;native=contract['nativeInputs']
    for key,path in (('gameAssembly',image.gameassembly),('metadata',image.metadata_path)):
        actual=_fingerprint(path)['sha256']
        _require(isinstance(native[key]['sha256'],str) and native[key]['sha256'].upper()==actual,
                 'flag-leaf-native-'+key,'supporting contract matches selected installed input',actual)
    rva=entry_va-image.pe.image_base
    matches=[w for w in contract['codeWindows'] if w['startRva']==rva]
    _require(len(matches)==1,'flag-leaf-window','one supporting window at actual call target',len(matches))
    window=matches[0];length=window['endRva']-window['startRva']
    _require(length==20,'flag-leaf-reviewed-width','complete terminal grammar window',length)
    raw=image.pe.bytes_at_va(entry_va,length)
    actual=hashlib.sha256(raw).hexdigest().upper()
    _require(actual==window['sha256'].upper(),'flag-leaf-window-hash',window['sha256'],actual)
    result=validate_leaf(raw,entry_va=entry_va)
    result.update(supportingContract={'name':name,'schema':schema,'sha256':digest},
        reviewedWindow=window,exactPrimaryPeExtentAvailable=entry_va in index.extents,
        neighboringEntryUsedAsBoundary=False,rawHex=raw.hex().upper(),
        targetPrimaryOwnedBytes=(index.extents[result['zeroMaskTail']['targetVa']]-result['zeroMaskTail']['targetVa']
                               if result['zeroMaskTail']['targetVa'] in index.extents else None))
    return result


def validate_return_bridge(primary: bytes, *, entry_va: int, cold: bytes, cold_va: int) -> dict:
    """Prove normal alias return and the complete owned cold call program.

    The preparation, carrier and final cold helpers remain opaque. In
    particular, the DWORD comparison reads storage after preparation, and
    the cold argument rereads that storage; no initial value is preserved.
    """
    _require(len(primary)==36 and len(cold)==22,'flag-bridge-length',
             'complete primary and one complete cold fragment',[len(primary),len(cold)])
    _require(type(entry_va) is int and type(cold_va) is int and entry_va>0 and cold_va>0
             and (entry_va+36<=cold_va or cold_va+22<=entry_va),
             'flag-bridge-extents','distinct positive nonoverlapping fragment addresses',[entry_va,cold_va])
    _require(primary[:5]==b'\x40\x53\x48\x83\xec','flag-bridge-frame','PUSH RBX; SUB RSP,imm8',primary[:6].hex())
    frame=int.from_bytes(primary[5:6],'little',signed=True)
    _require(32<=frame<128 and frame%16==0,'flag-bridge-shadow','aligned Win64 shadow frame',frame)
    _require(primary[6:9]==b'\x48\x8b\xd9','flag-bridge-input','RBX preserves incoming RCX before helper',primary[6:9].hex())
    def call(raw,at):
        _require(len(raw)==5 and raw[0]==0xe8,'flag-bridge-call','direct E8 signed-rel32',raw.hex())
        target=at+5+int.from_bytes(raw[1:],'little',signed=True)
        _require(0<target<2**64 and not entry_va<=target<entry_va+36 and not cold_va<=target<cold_va+22,
                 'flag-bridge-external-call','external helper target',target)
        return target
    prepare=call(primary[9:14],entry_va+9)
    _require(primary[14:16]==b'\x83\xbb' and primary[20]==0,'flag-bridge-read',
             'CMP DWORD [RBX+disp32],0 after preparation',primary[14:21].hex())
    offset=int.from_bytes(primary[16:20],'little',signed=True)
    _require(offset>=0,'flag-bridge-field','nonnegative anonymous DWORD displacement',offset)
    _require(primary[21:23]==b'\x0f\x85'
             and entry_va+27+int.from_bytes(primary[23:27],'little',signed=True)==cold_va,
             'flag-bridge-cold-edge','JNE to exact complete owned cold fragment',primary[21:27].hex())
    _require(primary[27:]==b'\x48\x8b\xc3\x48\x83\xc4'+bytes([frame])+b'\x5b\xc3',
             'flag-bridge-return','RAX=input RBX; matched frame restore; POP RBX; RET',primary[27:].hex())
    _require(cold[:2]==b'\x8b\x8b' and int.from_bytes(cold[2:6],'little',signed=True)==offset,
             'flag-bridge-cold-read','fresh DWORD at same anonymous field into ECX',cold[:6].hex())
    carrier=call(cold[6:11],cold_va+6)
    _require(cold[11:16]==b'\x48\x8b\xc8\x33\xd2','flag-bridge-cold-arguments',
             'carrier RAX to RCX; zero RDX',cold[11:16].hex())
    failure=call(cold[16:21],cold_va+16)
    _require(cold[21]==0xcc,'flag-bridge-cold-terminal','INT3 after final helper',cold[21:].hex())
    return {'completePrimaryAndOwnedColdProgramsProved':True,
        'preparationHelper':{'callVa':entry_va+9,'targetVa':prepare,'rcx':'unchanged incoming RCX reference',
                             'behaviorProved':False},
        'postPreparationDword':{'offset':offset,'readVa':entry_va+14,'bits':32,'fieldMeaningProved':False},
        'normalReturn':{'condition':'post-preparation DWORD comparison is zero and preparation returns normally',
                        'rax':'same incoming RCX reference saved in RBX','returnVa':entry_va+35},
        'coldProgram':{'condition':'post-preparation DWORD comparison is nonzero',
            'carrierHelper':{'callVa':cold_va+6,'targetVa':carrier,
                'rcx':'zero-extended fresh DWORD read at the same anonymous offset','behaviorProved':False},
            'finalHelper':{'callVa':cold_va+16,'targetVa':failure,
                'rcx':'RAX returned by opaque carrier helper','rdx':0,'behaviorProved':False},
            'int3Va':cold_va+21,'returnValueProved':False,'comparedDwordValuePreserved':False},
        'initialFieldValuePreservedByPreparationProved':False,'helperAlgorithmsProved':False,
        'contextSlotTypeMeaningProved':False,'runtimeExecutionKnown':False,'evidenceBoundary':'conditional'}


def prove_return_bridge(index, *, entry_va: int) -> dict:
    _require(entry_va in index.extents,'flag-bridge-primary-owner','exact primary PE entry',entry_va)
    fragments=index.chained_fragments.get(entry_va,[])
    _require(len(fragments)==1,'flag-bridge-cold-owner','one complete owned chained fragment',fragments)
    cold_va,cold_size=fragments[0];size=index.extents[entry_va]-entry_va
    primary=index.image.pe.bytes_at_va(entry_va,size);cold=index.image.pe.bytes_at_va(cold_va,cold_size)
    result=validate_return_bridge(primary,entry_va=entry_va,cold=cold,cold_va=cold_va)
    base=index.image.pe.image_base
    result['codeWindows']=[{'startRva':address-base,'endRva':address+len(raw)-base,
                            'sha256':hashlib.sha256(raw).hexdigest().upper()}
                           for address,raw in ((entry_va,primary),(cold_va,cold))]
    result['omittedChainedFragments']=False
    return result
