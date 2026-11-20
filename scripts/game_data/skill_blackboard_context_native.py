"""Authenticate canonical generic declarations and selected local context relations.

This validates static bytes and declarations, never execution of registration,
cache selection, initialization, or identity of any live object.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data.skill_ai_dispatch_native import _strict
from scripts.game_data.skill_blackboard_getter_native import _Program as _GetterProgram

SCHEMA='endfield.skill-blackboard-context-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_blackboard_context_native.json'


class _Program(_GetterProgram):
    def finish(self):
        _require(bytes(self.out)==self.raw and self.at==self.row['endRva'],'context-program-'+self.row['role'],self.raw.hex(),bytes(self.out).hex())


def _relations(c):
    """Decode the small relations used by the result; no whole-CFG inference."""
    w={x['role']:x for x in c['codeWindows']};d=c['operands'];t=c['targets']
    def exact(role, raw):
        _require(bytes.fromhex(w[role]['hex'])==raw,'context-relation-'+role,raw.hex(),w[role]['hex'])
    def rel(role, offset, opcode, target):
        row=w[role];raw=bytes.fromhex(row['hex']);prefix=bytes.fromhex(opcode)
        _require(raw[offset:offset+len(prefix)]==prefix,'context-opcode-'+role,prefix.hex(),raw[offset:].hex())
        at=offset+len(prefix);actual=row['startRva']+at+4+struct.unpack_from('<i',raw,at)[0]
        _require(actual==target,'context-target-'+role,target,actual)
    b=lambda x:bytes([x]);u=lambda x:struct.pack('<I',x)
    # Native type.data begins as a metadata index. These complete tiny helpers
    # replace it with the corresponding selected metadata record pointer.
    for role,header,stride in [('parameterFixup','parameterHeaderOffset','parameterStride'),('definitionFixup','definitionHeaderOffset','definitionStride')]:
        p=_Program(w[role]);p.emit('4863114c8bc183faff');p.relative('75',c['branches']['parameterNonNull' if role=='parameterFixup' else 'definitionNonNull'],1);p.emit('48c70100000000c3')
        p.relative('488b05',d['metadataHeaderCellRva'])
        if role=='parameterFixup':
            _require(d[stride]==16,'context-parameter-stride',16,d[stride]);p.emit('48c1e204486348');p.unsigned(d[header])
        else:p.emit('486bd2');p.unsigned(d[stride]);p.emit('486388');p.unsigned(d[header],4)
        p.relative('48030d',d['metadataBaseCellRva']);p.emit('4803d1498910c3');p.finish()
    # VAR substitution selects the parameter ordinal from genericInst.argv.
    # Attribute differences continue to an opaque copy path; the equality path
    # alone is allowed to return the selected argument pointer directly.
    p=_Program(w['varFastSelect']);p.emit('48895c24');p.unsigned(d['saveRbxStack']);p.emit('574883ec');p.unsigned(d['varFrameBytes']);p.emit('488b01488bf9440fb740');p.unsigned(d['paramOrdinalOffset']);p.emit('488b42');p.unsigned(d['genericInstArgvOffset']);p.emit('4a8b1cc08b53');p.unsigned(d['attributesOffset']);p.emit('3351');p.unsigned(d['attributesOffset']);p.emit('6685d2');p.relative('75',c['branches']['varMismatchTarget'],1);p.emit('8b4b');p.unsigned(d['attributesOffset']);p.emit('334f');p.unsigned(d['attributesOffset']);p.emit('0fbae1');p.unsigned(d['byrefBit']);p.relative('72',c['branches']['varMismatchTarget'],1);p.emit('488bc3488b5c24');p.unsigned(d['varFrameBytes']+8+d['saveRbxStack']);p.emit('4883c4');p.unsigned(d['varFrameBytes']);p.emit('5fc3');p.finish()
    p=_Program(w['referenceTest']);p.emit('8079');p.unsigned(d['nativeTypeKindOffset']);p.unsigned(d['sharedTypeKindClass']);p.relative('0f84',c['branches']['referenceResult']);p.finish()
    p=_Program(w['referenceResult']);p.relative('488b1d',d['objectDefaultCell']);p.emit('4883c3');p.unsigned(d['defaultByvalArgOffset']);p.finish()
    p=_Program(w['normalizerImageBase']);p.relative('4c8d3d',0);p.finish()
    p=_Program(w['enumSwitch']);p.relative('e8',t['enumUnderlyingType']);p.emit('0fbe48');p.unsigned(d['underlyingKindOffset']);p.emit('83c1');p.unsigned((-d['enumUnderlyingTypeKindBase'])&255);p.emit('83f9');p.unsigned(d['enumUnderlyingMaxIndex']);p.relative('77',c['branches']['enumFallback'],1);p.emit('4863c1418b8c87');p.unsigned(c['tables']['enumTargetsRva'],4);p.emit('4903cfffe1');p.finish()
    enum_targets=struct.unpack('<8I',bytes.fromhex(c['tables']['enumTargetsHex']))
    _require(enum_targets[d['sharedTypeKindInt32']-d['enumUnderlyingTypeKindBase']]==w['enumInt32Result']['startRva'],'context-int32-switch-target',w['enumInt32Result']['startRva'],enum_targets)
    p=_Program(w['enumEligibility']);p.relative('488b05',d['enumSharingFlagPointerCell']);p.emit('803800');p.relative('0f84',c['branches']['enumFallback']);p.emit('807b');p.unsigned(d['nativeTypeKindOffset']);p.emit('11');p.relative('75',c['branches']['enumEligibilityReject'],1);p.emit('4885db');p.relative('75',w['enumEligibility']['startRva']+31,1);p.emit('33c0');p.relative('eb',w['enumEligibility']['startRva']+39,1);p.emit('488b0b');p.relative('e8',t['enumTypeDefinitionClass']);p.emit('f680');p.unsigned(d['enumRuntimeFlagOffset'],4);p.unsigned(d['enumRuntimeFlagMask']);p.relative('75',c['branches']['enumNormalize'],1);p.finish()
    p=_Program(w['fixupLoop']);p.emit('40534883ec20');p.relative('4c8b05',d['registrationCellRva']);p.emit('33db413958');p.unsigned(d['typesCountOffset']);p.relative('7e',c['branches']['fixupLoopReturn'],1);p.emit('4889742430');p.relative('488d35',0);p.emit('48897c24388bfb0f1f840000000000');p.mark(c['branches']['fixupLoopHead']);p.emit('498b40');p.unsigned(d['typesPointerOffset']);p.emit('488b0c070fbe41');p.unsigned(d['nativeTypeKindOffset']);p.emit('ffc883f8');p.unsigned(d['fixupMaxKindMinusOne']);p.relative('77',c['branches']['fixupLoopNext'],1);p.emit('48980fb68406');p.unsigned(c['tables']['fixupIndexRva'],4);p.emit('8b9486');p.unsigned(c['tables']['fixupTargetsRva'],4);p.emit('4803d6ffe2');p.relative('e8',w['definitionFixup']['startRva']);p.relative('eb',c['branches']['fixupLoopReload'],1);p.relative('e8',w['parameterFixup']['startRva']);p.mark(c['branches']['fixupLoopReload']);p.relative('4c8b05',d['registrationCellRva']);p.mark(c['branches']['fixupLoopNext']);p.emit('ffc34883c708413b58');p.unsigned(d['typesCountOffset']);p.relative('7c',c['branches']['fixupLoopHead'],1);p.emit('488b7c2438488b742430');p.mark(c['branches']['fixupLoopReturn']);p.emit('4883c4205bc3');p.finish()
    fixup_index=bytes.fromhex(c['tables']['fixupIndexHex']);fixup_targets=struct.unpack('<3I',bytes.fromhex(c['tables']['fixupTargetsHex']))
    _require(fixup_targets[fixup_index[0x13-1]]==c['branches']['fixupLoopReload']-5,'context-var-fixup-dispatch','VAR calls parameter fixup',fixup_targets)
    p=_Program(w['varDispatch']);p.emit('48895c24');p.unsigned(d['saveRbxStack']);p.emit('48897424');p.unsigned(d['saveRsiStack']);p.emit('574883ec');p.unsigned(d['varFrameBytes']);p.emit('0fbe41');p.unsigned(d['nativeTypeKindOffset']);p.emit('488bf983c0');p.unsigned((-d['varKindBase'])&255);p.emit('83f8');p.unsigned(d['varMaxKindIndex']);p.relative('0f87',c['branches']['varDefault']);p.relative('488d0d',0);p.emit('4898448b8c81');p.unsigned(c['tables']['varTargetsRva'],4);p.emit('4c03c941ffe1');p.mark(c['branches']['varKindTarget']);p.emit('488b12488bcf488b5c24');p.unsigned(d['varFrameBytes']+8+d['saveRbxStack']);p.emit('488b7424');p.unsigned(d['varFrameBytes']+8+d['saveRsiStack']);p.emit('4883c4');p.unsigned(d['varFrameBytes']);p.emit('5f');p.relative('e9',t['varSelect']);p.finish()
    _require(struct.unpack('<16I',bytes.fromhex(c['tables']['varTargetsHex']))[0x13-d['varKindBase']]==c['branches']['varKindTarget'],'context-var-dispatch','VAR selects class generic instantiation',c['branches']['varKindTarget'])
    p=_Program(w['kind2Dispatch']);p.emit('418b4df883f903');p.relative('0f84',c['branches']['kind3']);p.emit('83e901');p.relative('0f84',c['branches']['kind1']);p.emit('83e901');p.relative('0f84',w['kind2Index']['startRva']);p.finish()
    p=_Program(w['kind2Index']);p.emit('498b450048630883f9ff');p.relative('75',w['kind2InflateClass']['startRva'],1);p.emit('33c08bc8');p.relative('eb',w['kind2InflateClass']['startRva']+18,1);p.finish()
    p=_Program(w['kind2InflateClass']);p.emit('488bd1');p.relative('488b05',d['registrationCellRva']);p.emit('488b48');p.unsigned(d['typesPointerOffset']);p.emit('488b0cd141b001488bd7');p.relative('e8',t['slotInflation']);p.emit('488bc8b201');p.relative('e8',t['classFromType']);p.relative('e9',c['branches']['slotStore']);p.finish()
    p=_Program(w['enumInt32Result']);p.relative('488b1d',d['enumInt32DefaultCell']);p.relative('eb',c['branches']['enumCommon'],1);p.finish()
    p=_Program(w['enumCommonResult']);p.emit('4883c3');p.unsigned(d['defaultByvalArgOffset']);p.emit('807b');p.unsigned(d['nativeTypeKindOffset']);p.emit('15');p.relative('75',w['enumCommonResult']['endRva']+0x3e,1);p.finish()
    # Defaults are actual name lookup requests, not guessed names beside cells.
    names={r['text']:r for r in c['nameRequests']}
    for role,name,cell in [('objectDefault','Object','objectDefaultCell'),('enumDefault','Int32Enum','enumInt32DefaultCell')]:
        p=_Program(w[role]);p.relative('4c8d05',names[name]['rva']);p.relative('488d15',names['System']['rva'])
        if role=='enumDefault':
            raw=bytes.fromhex(w[role]['hex']);p.emit('488b0d'+raw[17:21].hex())
        p.relative('e8',t['classNameLookup']);p.relative('488905',d[cell]);p.finish()
    exact('rgctxContextSource',bytes.fromhex('488b47604883c0')+b(d['genericClassContextOffset'])+bytes.fromhex('488945')+b(d['contextLocalRbp']&255))
    exact('rgctxContextRestore',bytes.fromhex('488b7d')+b(d['contextLocalRbp']&255))
    exact('slotStoreAdvance',bytes.fromhex('4989074983c5')+b(d['recordStride'])+bytes.fromhex('4983c7')+b(d['slotStride'])+bytes.fromhex('4c897d7748836d7f010f85')+struct.pack('<i',c['branches']['slotLoop']-w['slotStoreAdvance']['endRva']))
    exact('contextArrayStore',bytes.fromhex('488b7d')+b(d['sourceClassLocalRbp'])+bytes.fromhex('488b45')+b(d['contextArrayLocalRbp']&255)+bytes.fromhex('eb03498bc7488987')+u(d['classContextOffset']))
    exact('methodInfoClassStore',bytes.fromhex('488b7d5048895f20'))
    exact('methodInfoOriginalContext',bytes.fromhex('4c897f40'))
    rel('kind2InflateClass',24,'e8',t['slotInflation']);rel('kind2InflateClass',34,'e8',t['classFromType']);rel('kind2InflateClass',39,'e9',c['branches']['slotStore'])
    rel('classInit',9,'e8',t['classInitRequest']);rel('classInit',21,'0f85',c['branches']['classInitError'])
    raw=bytes.fromhex(w['classInit']['hex'])
    _require(raw[6:9]==bytes.fromhex('488bd9')and raw[-8:]==bytes.fromhex('488bc34883c4205bc3')[-8:],'context-class-return','saved input returned on normal local path',raw.hex())
    return dict(localSlotStore=True,recordStride=d['recordStride'],slotStride=d['slotStride'],classContextOffset=d['classContextOffset'],normalClassInitReturnsOriginalPointer=True,metadataIndexFixup=True,varOrdinalSelection=True,referenceNormalizationDefaultNameRequest='System.Object',int32EnumNormalizationDefaultNameRequest='System.Int32Enum',enumNormalizationRequiresRuntimeEnableAndClassFlag=True,defaultLookupRuntimeResultObserved=False,attributeMismatchCopyPathProved=False)


def _canonical(image,c):
    pe=image.pe;base=pe.image_base;reg=image.registration;symbols=ContextSymbols(image)
    code=image.mapper.code_registration_summary(pe,image.code_registration)
    ptr=int(code['genericMethodPointers'],16);table=int(reg['genericMethodTable'],16)
    raw=pe.bytes_at_va(table,reg['genericMethodTableCount']*16);pointers=pe.bytes_at_va(ptr,code['genericMethodPointersCount']*8)
    for role,rows in c['canonical'].items():
        _require(len(rows)==1,'context-canonical-count',1,len(rows));r=rows[0]
        indices={n for n,(p,)in enumerate(struct.iter_unpack('<Q',pointers))if p==base+r['pointerRva']}
        matches=[]
        for n,(spec,method,invoker,adjustor)in enumerate(struct.iter_unpack('<iiii',raw)):
            if method not in indices:continue
            triple=list(struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+spec*12,12)))
            if triple[0]!=r['methodDefinition'][0]:continue
            m=image.metadata.methods[triple[0]]
            matches.append(dict(tableIndex=n,tableRowRva=table-base+n*16,rawHex=raw[n*16:(n+1)*16].hex(),methodSpecIndex=spec,methodSpec=triple,methodDefinition=[triple[0],image.type_name(m.declaring_type),image.metadata.string(m.name_index)],classArguments=symbols.arguments(triple[1]),methodArguments=symbols.arguments(triple[2]),indices=[method,invoker,adjustor],pointerSlotRva=ptr-base+method*8,pointerRva=r['pointerRva']))
        _require(_strict(rows,matches),'context-canonical-'+role,rows,matches)
    return c['canonical']


def _selector(c):
    """Prove exact key comparisons and ordinary hit/result paths.

    Hash/probing and exceptional table helper paths remain separately bounded.
    A collision cannot become equality merely because its hash matches.
    """
    w={x['role']:x for x in c['codeWindows']};s=c['selector'];t=c['targets']
    p=_Program(w['selectorContextInput']);p.emit('4d8be04d8b30488bd94d8b78');p.unsigned(s['contextMethodOffset']);p.emit('f30f7f40a04c8970a04c8978a8');p.finish()
    p=_Program(w['selectorNormalize']);p.emit('498b0c24');p.relative('e8',t['normalizeInstantiation']);p.emit('498b4c24');p.unsigned(s['contextMethodOffset']);p.emit('4889442428');p.relative('e8',t['normalizeInstantiation']);p.finish()
    # First lookup compares original MethodInfo, classInst and methodInst.
    p=_Program(w['selectorOriginalKey']);p.emit('498b4cc308483b11');p.relative('0f85',s['originalProbeNext']);p.emit('4c3b71');p.unsigned(s['contextClassKeyOffset']);p.relative('0f85',s['originalFalse']);p.emit('4c3b79');p.unsigned(s['contextMethodKeyOffset']);p.relative('0f85',s['originalFalse']);p.emit('b00184c0');p.relative('0f84',s['originalProbeNext']);p.emit('4983f9ff');p.relative('0f84',s['originalMiss']);p.emit('4b8d0449');p.relative('e9',s['originalHit']);p.finish()
    # Second lookup keeps the same MethodInfo while comparing normalized insts.
    p=_Program(w['selectorNormalizedKey']);p.emit('498b4cc3084c3b39');p.relative('0f85',s['normalizedProbeNext']);p.emit('483b51');p.unsigned(s['contextClassKeyOffset']);p.relative('0f85',s['normalizedFalse']);p.emit('4c3b71');p.unsigned(s['contextMethodKeyOffset']);p.relative('0f85',s['normalizedFalse']);p.emit('b00184c0');p.relative('0f84',s['normalizedProbeNext']);p.emit('4983f9ff');p.relative('0f84',s['normalizedMiss']);p.emit('4b8d0449');p.relative('e9',s['normalizedHit']);p.finish()
    for role,ret in [('selectorOriginalFalse','originalFalseResume'),('selectorNormalizedFalse','normalizedFalseResume')]:
        p=_Program(w[role]);p.emit('32c0');p.relative('e9',s[ret]);p.finish()
    p=_Program(w['selectorOriginalReturn']);p.emit('488b52');p.unsigned(s['entryValueOffset']);p.emit('4533c0488bcb');p.relative('e8',t['copyPointerRecord']);p.emit('488bc3');p.relative('eb',s['returnEpilogue'],1);p.finish()
    p=_Program(w['selectorNormalizedReturn']);p.emit('4533c0488b52');p.unsigned(s['entryValueOffset']);p.emit('488b8c2490000000');p.relative('e8',t['copyPointerRecord']);p.emit('488b842490000000488b9c24a00000004883c450415f415e415d415c5f5e5dc3');p.finish()
    d=c['pointerRecord'];p=_Program(w['selectorPointerRecord']);p.emit('48895c2408');p.relative('4c8b1d',d['codeRegistrationCell']);p.emit('410fb6d84c8bd1418b43');p.unsigned(d['methodCountOffset']);p.emit('3902');p.relative('73',d['invalid'],1);p.emit('418b43');p.unsigned(d['invokerCountOffset']);p.emit('394204');p.relative('73',d['invalid'],1);p.emit('837a08ff4c630a498b43');p.unsigned(d['methodPointersOffset']);p.emit('4e8b04c8');p.relative('74',d['noAdjustor'],1);p.emit('48634a08498b43');p.unsigned(d['adjustorPointersOffset']);p.emit('4c8b0cc8');p.relative('eb',d['store'],1);p.mark(d['noAdjustor']);p.emit('4d8bc8');p.mark(d['store']);p.emit('498b43');p.unsigned(d['invokerPointersOffset']);p.emit('48634a044d89024d894a0841885a18488b0cc8498bc249894a10488b5c2408c3');p.mark(d['invalid']);p.emit('488b5c240833c04889014889410848894110884118498bc2c3');p.finish()
    return dict(keyFields=['originalMethodInfo','classInstantiationPointer','methodInstantiationPointer'],originalKeyEqualityRequired=True,normalizedLookupPreservesOriginalMethodInfo=True,normalizesClassAndMethodInstantiationsIndependently=True,pointerRecordDecodeProved=True,pointerRecordFields=['genericMethodPointer','adjustorOrGenericMethodPointer','invokerPointer','callerFlag'],fullHashProbeAndExceptionalPathsProved=False)


def _interning(c):
    w={x['role']:x for x in c['codeWindows']};d=c['interning'];t=c['targets']
    p=_Program(w['typeComparerPrefix']);p.emit('4883ec284c8bda48895c2430');p.relative('488d15',0);p.emit('4c8bd166660f1f840000000000410fb6430a4138420a');p.relative('0f85',d['kindMismatch']);p.emit('418b4308418b4a08c1e81dc1e91d83e00183e1013bc8');p.relative('0f85',d['byrefMismatch']);p.emit('410fbe420a83c0f183f80f');p.relative('0f87',w['typeComparerPrimitiveEqual']['startRva']);p.emit('48988b8c82');p.unsigned(d['typeTargetsRva'],4);p.emit('4803caffe1');p.finish()
    targets=struct.unpack('<16I',bytes.fromhex(d['typeTargetsHex']))
    _require(targets[0x11-0xf]==w['typeComparerDefinitionEqual']['startRva']and targets[0x1c-0xf]==w['typeComparerPrimitiveEqual']['startRva'],'context-selected-type-comparison','enum compares definition data; object compares kind/byref only',targets)
    p=_Program(w['typeComparerDefinitionEqual']);p.emit('498b03493902');p.relative('75',d['definitionMismatch'],1);p.emit('33db8bc3488b5c24304883c428c3');p.finish()
    p=_Program(w['typeComparerPrimitiveEqual']);p.emit('33c0488b5c24304883c428c3');p.finish()
    p=_Program(w['internArgumentsEqual']);p.emit('498b4cc5083b19');p.relative('75',d['probeNext'],1);p.emit('33f64d85e4');p.relative('74',d['allEqual'],1);p.emit('488b5c24284c8b71084c2bf30f1f440000');p.mark(d['compareLoop']);p.emit('498b141e488b0b');p.relative('e8',t['typeComparer']);p.emit('85c0');p.relative('75',d['probeNext'],1);p.emit('48ffc64883c308493bf4');p.relative('72',d['compareLoop'],1);p.mark(d['allEqual']);p.emit('4883ffff');p.relative('75',d['foundEntry'],1);p.finish()
    p=_Program(w['internExistingReturn']);p.emit('49c1e2044d03d5493bfa');p.relative('74',d['createEntry'],1);p.emit('488b5f08');p.relative('488b0d',d['lockCell']);p.relative('ff15',d['unlockImportCell']);p.emit('90');p.relative('e9',w['internReturn']['startRva']);p.finish()
    p=_Program(w['internReturn']);p.emit('488bc34883c458415f415e415d415c5f5e5d5bc3');p.finish()
    return dict(existingInstantiationRequiresArgumentCountAndElementTypeEquality=True,selectedObjectComparison='kind-and-byref',selectedEnumComparison='kind-and-byref-and-fixed-up-definition-pointer',existingHitReturnsStoredInstantiationPointer=True,fullInternInsertionAndLockingProved=False)


def _validate(image,c):
    from scripts.game_data import skill_blackboard_getter_native as getter
    from scripts.game_data import skill_input_blackboard_native as writer
    dependencies=[]
    for key,schema in [('getterDependency',getter.SCHEMA),('writerDependency',writer.SCHEMA)]:
        expected='skill_blackboard_getter_native.json'if key=='getterDependency'else'skill_input_blackboard_native.json'
        _require(c[key]==expected,'context-dependency-name',expected,c[key])
        value,digest=read_reviewed_contract(CONTRACTS_DIR/expected,schema=schema,status='reviewed',label='skillBlackboardContext')
        _require(_strict(value['nativeInputs'],c['nativeInputs']),'context-dependency-inputs',c['nativeInputs'],value['nativeInputs']);dependencies.append((CONTRACTS_DIR/expected,value,digest))
    getter_result=getter._validate(image,dependencies[0][1],dependencies[1][1])
    image.check_windows(c['codeWindows'],label='skillBlackboardContext')
    for row in c['codeWindows']:
        raw=bytes.fromhex(row['hex']);_require(len(raw)==row['endRva']-row['startRva']and image.pe.bytes_at_va(image.pe.image_base+row['startRva'],len(raw))==raw,'context-window-'+row['role'],row['hex'],'installed bytes')
    for name,row in c['nativeMetadataSections'].items():
        s=image.metadata.sections[name];_require(row==dict(offset=s.offset,size=s.size),'context-metadata-section-'+name,row,dict(offset=s.offset,size=s.size))
    for name in ('fixupIndex','fixupTargets','varTargets','enumTargets'):
        raw=bytes.fromhex(c['tables'][name+'Hex']);_require(image.pe.bytes_at_va(image.pe.image_base+c['tables'][name+'Rva'],len(raw))==raw,'context-table-'+name,raw.hex(),'installed bytes')
    raw=bytes.fromhex(c['interning']['typeTargetsHex']);_require(image.pe.bytes_at_va(image.pe.image_base+c['interning']['typeTargetsRva'],len(raw))==raw,'context-table-typeTargets',raw.hex(),'installed bytes')
    cx=NativeReferenceContext(image);symbols=ContextSymbols(image)
    for role,r in c['selectedTypes'].items():
        td=image.named_types[r['name']];_require(td.index==r['typeDefinition']and cx.parent(r['name'])==r['parent']and cx.is_value_type(r['name'])==r['isValueType'],'context-selected-'+role,r,'metadata identity')
        _require(_strict(symbols.type(r['argument']['typePointerVa']),r['argument']),'context-selected-argument',r['argument'],symbols.type(r['argument']['typePointerVa']))
        if role=='state':
            actual=[cx.type_name(f.type_index)for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)=='value__']
            _require(actual==[r['underlyingType']],'context-enum-underlying',r['underlyingType'],actual)
    for r in c['nameRequests']:
        raw=image.pe.bytes_at_va(image.pe.image_base+r['instructionRva'],7);target=r['instructionRva']+7+struct.unpack_from('<i',raw,3)[0]
        actual=image.pe.bytes_at_va(image.pe.image_base+target,len(r['text'])+1)
        _require(raw[:3]in(bytes.fromhex('4c8d05'),bytes.fromhex('488d15'))and target==r['rva']and actual==r['text'].encode()+b'\0','context-default-name',r,actual.hex())
    result=dict(canonical=_canonical(image,c),localRelations=_relations(c),pointerSelector=_selector(c),instantiationEquality=_interning(c),staticGetterSubstitution=getter_result['staticSubstitution'],evidenceBoundary=c['evidenceBoundary'],runtimeExecutionProved=False,liveObjectIdentityProved=False,fullInitializationCfgProved=False)
    for path,value,digest in dependencies:_require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'context-dependency-bookend','unchanged',str(path))
    return result


def load_skill_blackboard_context(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema='endfield.skill-blackboard-context-native-audit.v1',status='validation_failed',failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillBlackboardContext');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'context-bookends','unchanged native inputs and contract',after.status)
        audit.update(result,status='validated-static-context-relations',nativeInputs=pins)
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as e:audit.update(status='validation_failed',failures=[dict(check=str(e)[:1600],source=str(path))])
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('gameassembly','metadata','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=load_skill_blackboard_context(gameassembly=a.gameassembly,metadata=a.metadata)
    from scripts.repo_paths import REPO_ROOT
    _require(any(a.output.resolve().is_relative_to(REPO_ROOT/x)for x in ('reports','scratch','tmp')),'context-output-root','ignored',a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if r['status']=='validated-static-context-relations'else 1


if __name__=='__main__':raise SystemExit(main())

