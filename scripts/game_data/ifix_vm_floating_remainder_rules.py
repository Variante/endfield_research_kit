"""Finite floating remainder helper programs, with native FP state conditional.

This authenticates raw-bit special cases, Double split-product/FMA/x87 paths,
Float widening/chunk reduction and numeric-error support callers. It proves
instruction recipes, not a language '%' operator or observed numeric result.
The caller authenticates arithmeticRules for the VM opcode/helper join.
No instruction, VM or native helper is executed here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.ifix_vm_reference_address_rules import _ref,_rva,_hash,_expect


class FloatingRemainderRuleError(ValueError):
    """A floating helper declaration lacks its finite witness."""


def _need(ok: bool,label: str) -> None:
    if not ok:raise FloatingRemainderRuleError('ifix-floating-remainder.'+label)


_HELPER_REFS={'doubleRem':'arithmeticRules.helpers.doubleRem','floatRem':'arithmeticRules.helpers.floatRem'}
_DATA_REFS={'floatSignMask':'bitwiseRules.masks.doubleMask'}
_REQUESTS={'statusMap','recordDouble','recordFloat','modeQuery','callbackRequest','statusRequest','cookieCheck'}
_OWN_HELPERS={'errorDouble','errorFloat','quietFloat'}
_DATA_VALUES={
 'absoluteMask':(16,(0x7fffffffffffffff).to_bytes(8,'little')+bytes(8)),
 'exponentMask':(8,(0x7ff0000000000000).to_bytes(8,'little')),
 'splitMask':(16,(0xfffffffff8000000).to_bytes(8,'little')+bytes(8)),
 'signMask':(16,(0x8000000000000000).to_bytes(8,'little')+bytes(8)),
 'zero':(16,bytes(16)),
 'quietDoubleBit':(16,(1<<51).to_bytes(8,'little')+bytes(8)),
 'defaultDoubleNaN':(16,(0x7ff8000000000000).to_bytes(8,'little')*2),
 'doubleRequestName':(5,b'fmod\0'),'floatRequestName':(6,b'fmodf\0')}
_BOUNDS={'schema':'endfield.ifix-vm-floating-remainder-rules.v1','evidenceBoundary':'conditional','executionBoundary':'unobserved',
 'arithmeticProofRef':'arithmeticRules','opcodeJoinBoundary':'caller-authenticated-arithmeticRules-required;this-group-proves-selected-helper-bodies',
 'operandBoundary':'Double:XMM0-XMM1-raw-low64;Float:XMM0-XMM1-low32-widened-by-CVTSS2SD',
 'floatingBoundary':'normal-native-instruction-completion;MXCSR-x87-rounding-exception-FMA-support-and-actual-values-unobserved',
 'featureBoundary':'selected-unbacked-PE-virtual-tail-Int32-feature-word;runtime-value-and-initialization-unobserved',
 'errorBoundary':'finite-support-callers;external-status-choice-record-cookie-check-results-and-memory-mutation-unobserved',
 'numericalBoundary':'instruction-recipe-only;no-language-percent-or-ideal-real-arithmetic-equivalence',
 'storageBoundary':'valid-native-stack-and-constant-storage-required;helper-mutation-and-aliases-unobserved'}
_DOUBLE_RULES={
 'selectionOrder':'absBits(rhs)>infinityBits:raw-rhs;absBits(lhs)>infinityBits:raw-lhs;lhs-infinity:error-request;rhs-zero:error-request;equal-magnitudes:lhs-sign-only-zero;ordered-magnitude-lhs<=rhs:raw-lhs',
 'fallbackSelection':'zero-exponent-or-exponent-difference>=52: x87;split-path-q-and-rhs-unbiased-exponent-sum>=1023: x87',
 'quotient':'CVTTSD2SI64(DIVSD(abs(lhs),abs(rhs)));CVTSI2SD64 back to q',
 'splitPath':'p=MULSD(q,b);bh=b&splitMask;qh=q&splitMask;bl=SUBSD(b,bh);ql=SUBSD(q,qh);err=ADDSD(MULSD(ql,bl),ADDSD(ADDSD(SUBSD(MULSD(bh,qh),p),MULSD(bh,ql)),MULSD(qh,bl)));y1=SUBSD(a,p);r=ADDSD(SUBSD(SUBSD(SUBSD(a,y1),p),err),y1)',
 'fmaPath':'feature-word-nonzero;q-bits-OR-signMask;VFMADD231SD(a,signed-q,b)',
 'adjustment':'COMISD(r,zero);if CF=1 ADD(abs(rhs));resultBits=(lhsBits&signMask)|(rBits&absoluteMask)',
 'x87':'FLD(rhs);FLD(lhs);FNCLEX;FPREM;FNSTSW-AX;poll-C2-bit10-until-clear;FSTP-low64-result;FSTP-divisor;MOVSD-result-to-XMM0;termination-and-x87-state-unobserved',
 'equalMagnitude':'(lhsBits&signMask)|zeroBits',
 'errorRequests':'lhs-infinity:lhsBits-OR-quietDoubleBit;rhs-zero:defaultDoubleNaN;name=fmod,status22,choice1,stack8/33/type2;support-return-XMM0-unobserved'}
_FLOAT_RULES={
 'selection':'widen-inputs;normal-exponents1..2046-on-both-operands;equal-magnitudes:return widened-lhs-sign-only converted-to-Float;smaller-lhs:convert abs(lhs) with original-lhs-negative sign XOR',
 'chunkCount':'normal-path-positive-exponent-delta;native-signed-magic-trunc(delta/24);delta1..2045;n0..85;groups0..10;remaining0..7',
 'scale':'bScaled=MULSD(abs(rhs),doubleBits(UInt64((1023+24*n)<<52)));downScale=doubleBits(999<<52)=2^-24',
 'chunk':'q32=CVTTSD2SI32(DIVSD(a,bScaled));a=SUBSD(a,MULSD(double(q32),bScaled));bScaled=MULSD(bScaled,downScale);eight-unrolled-chunks-per-group;then-remaining-chunks',
 'finish':'one-final-quotient-subtraction;reload-captured-MXCSR-word-before-COMISS-zero/original-lhs-sign-and-CVTSD2SS;status-and-rounding-after-reload-unobserved',
 'specialOrder':'lhs-exponent>2046:nonzero-lhs-mantissa->quiet-lhs-raw32-tail,zero->invalid;else-rhs-exponent>2046:nonzero-rhs-mantissa->quiet-rhs-raw32-tail,zero->return-original-XMM0;else-lhs-exponent<1-and-rhs-exponent>=1:return-original-XMM0;otherwise:invalid-error-request',
 'quietFloat':'set-raw-bit22-in-ECX;MOVD-XMM0;RET;other-low32-bits-preserved',
 'errorRequest':'name=fmodf,status22,choice1,raw32-default0xffc00000,stack8/33/type2;support-return-XMM0-unobserved'}
_ERROR_RULES={
 'initial':'capture-requested-result-bits-and-choice;request statusMap(status8,local-word-address)',
 'record':'if statusMap-EAX!=0 zero-record-storage;type2 populates caller-operand2-storage/type-marker3-Double-or1-Float;record request includes pointers to local-word/requested-result/caller-operand-storage;Double caller operand-storage values unobserved',
 'selection':'request modeQuery;AL!=0-and-choice!=0 builds local record and requests callbackRequest;callbackRequest-EAX==0 requests statusRequest;otherwise default-path requests statusRequest',
 'return':'callback-path:result-from-local-record-after-opaque-request;default-path:captured-requested-result-after-opaque-requests;Float callback-result converted from Double;cookieCheck request before normal RET',
 'runtimeBoundary':'opaque-request-results-callback-existence-local-mutation-cookie-value-and-abnormal-transfer-unobserved'}


def _claims(spec: dict) -> None:
    _need(all(spec.get(k)==v for k,v in _BOUNDS.items()) and spec.get('helperRefs')==_HELPER_REFS and spec.get('dataRefs')==_DATA_REFS
        and spec.get('doubleRules')==_DOUBLE_RULES and spec.get('floatRules')==_FLOAT_RULES and spec.get('errorRules')==_ERROR_RULES,'unsupported schema/reference/conditional rules')
    _need(set(spec['helpers'])==_OWN_HELPERS and set(spec['requests'])==_REQUESTS and set(spec['data'])==set(_DATA_VALUES)|{'featureSelector','securityCookie'},'owned helper/request/data set differs')


def _token_size(token: Any) -> int:
    if isinstance(token,str):return len(bytes.fromhex(token))
    kind,*args=token
    if kind=='label':return 0
    if kind=='call':return 5
    if kind=='rel':return len(bytes.fromhex(args[0]))+args[2]
    if kind=='rip':return len(bytes.fromhex(args[0]))+4+len(bytes.fromhex(args[2]))
    _need(False,'unknown finite program token');return 0


def _program(name: str,at: int,targets: dict[str,int],data: dict[str,int]) -> tuple[bytes,dict[str,int]]:
    tokens=_PROGRAMS[name];cursor=0;labels={}
    for token in tokens:
        if not isinstance(token,str) and token[0]=='label':
            _need(token[1] not in labels,'duplicate finite label');labels[token[1]]=at+cursor
        cursor+=_token_size(token)
    result=bytearray();points={**targets,**labels}
    for token in tokens:
        if isinstance(token,str):result.extend(bytes.fromhex(token));continue
        kind,*args=token
        if kind=='label':continue
        if kind=='call':prefix=b'\xe8';target=points[args[0]];size=4;suffix=b''
        elif kind=='rel':prefix=bytes.fromhex(args[0]);target=points[args[1]];size=args[2];suffix=b''
        else:prefix=bytes.fromhex(args[0]);target=data[args[1]];size=4;suffix=bytes.fromhex(args[2])
        disp=target-(at+len(result)+len(prefix)+size+len(suffix));result.extend(prefix+disp.to_bytes(size,'little',signed=True)+suffix)
    _need(len(result)==cursor,'finite program length differs');return bytes(result),labels


def _data(image: Any,spec: dict,contract: dict) -> dict[str,int]:
    result={}
    for name,row in spec['data'].items():
        at=_rva(row['rva']);count=row['byteCount'];_need(type(count) is int and count>0,'data width differs: '+name);result[name]=at
        if name=='featureSelector':
            _need(count==4 and row.get('storage')=='unbacked-virtual-tail-runtime-word-unobserved','feature-word boundary differs')
            section=row['section'];matches=[s for s in image.pe.sections if s['name']==section['name'] and s['virtualAddress']<=at and at+count<=s['virtualAddress']+s['virtualSize']]
            _need(len(matches)==1 and matches[0]==section and at>=section['virtualAddress']+section['rawSize'],'feature-word is not selected unbacked virtual tail')
            continue
        raw=image.pe.bytes_at_va(image.pe.image_base+at,count);_hash(raw,row,'data.'+name)
        if name=='securityCookie':_need(count==8 and row.get('storage')=='mutable-runtime-cookie-value-unobserved','runtime-cookie boundary differs')
        else:
            width,expected=_DATA_VALUES[name];_need(count==width,'constant width differs: '+name);_expect(raw,expected,'data.'+name)
    row=_ref(contract,_DATA_REFS['floatSignMask']);at=_rva(row['cellRva']);_need(row['byteCount']==8,'inherited Double sign-mask width differs')
    _hash(image.pe.bytes_at_va(image.pe.image_base+at,8),row,'floatSignMask');_expect(image.pe.bytes_at_va(image.pe.image_base+at,16),(1<<63).to_bytes(8,'little')*2,'floatSignMask.128bits');result['floatSignMask']=at
    return result


def _chunk_certificate() -> dict:
    """A bounded integer lemma for the native exponent-chunk count only."""
    values=[]
    for delta in range(1,2046):
        high=(delta*0x2aaaaaab)>>32;shifted=high>>2;n=shifted+((shifted&0xffffffff)>>31)
        _need(n==delta//24,'positive exponent magic division differs');groups=0 if n<8 else ((n-8)>>3)+1;remaining=n-groups*8
        _need(0<=n<=85 and 0<=groups<=10 and 0<=remaining<=7,'chunk loop bound differs');values.append(n)
    return {'positiveExponentDelta':[1,2045],'chunkCount':[min(values),max(values)],'groups':[0,10],'remaining':[0,7],'evidenceBoundary':'exact-integer-lemma;floating-values-and-instruction-completion-conditional'}


def validate_floating_remainder_rules(image: Any,spec: dict,contract: dict,extents: dict[int,int]) -> dict:
    """Authenticate complete selected helpers; caller owns VM-join validation."""
    _claims(spec);targets={};rows={n:_ref(contract,path) for n,path in _HELPER_REFS.items()};rows.update(spec['helpers']);checked=[]
    for name,row in rows.items():
        at=_rva(row['rva']);count=row['byteCount'];_need(type(count) is int and count>0,'helper width differs: '+name)
        raw=image.pe.bytes_at_va(image.pe.image_base+at,count);_hash(raw,row,'helper.'+name);targets[name]=at
        if name=='quietFloat':_expect(raw,bytes.fromhex('0fbae916660f6ec1c3'),'quietFloat')
        else:_need(extents.get(image.pe.image_base+at)==image.pe.image_base+at+count,'complete helper extent differs: '+name)
        checked.append(dict(helper=name,rva=hex(at),byteCount=count))
    for name,row in spec['requests'].items():
        _need(row.get('effectBoundary')=='selected-entry-window-request-only;callee-result-and-mutation-unobserved' and row['byteCount']==16,'opaque request boundary differs: '+name)
        at=_rva(row['rva']);_hash(image.pe.bytes_at_va(image.pe.image_base+at,16),row,'request.'+name);targets[name]=at
    data=_data(image,spec,contract);labels={}
    for name in _PROGRAMS:
        row=rows[name];at=targets[name];raw=image.pe.bytes_at_va(image.pe.image_base+at,row['byteCount']);expected,native_labels=_program(name,at,targets,data);_expect(raw,expected,name);labels[name]={n:hex(v) for n,v in native_labels.items()}
    return {'status':'validated_conditional_floating_remainder_rules','evidenceBoundary':'conditional','executionBoundary':'unobserved','helpers':checked,
        'labels':labels,'chunkCertificate':_chunk_certificate(),'doubleRules':spec['doubleRules'],'floatRules':spec['floatRules'],'errorRules':spec['errorRules'],
        'unresolved':['actual-inputs-output-values-and-VM-execution','native-MXCSR-x87-state-and-FMA-support','x87-C2-loop-termination-and-exception-transfer',
          'runtime-feature-word-cookie-and-support-helper-results-or-mutation','ideal-remainder-language-percent-equivalence']}


def validate_selected_floating_remainder_rules(contract: dict,*,gameassembly: Path,metadata: Path,spec: dict|None=None) -> dict:
    """Gate the selected pair; offline helper proof has no runtime fallback."""
    if gameassembly is None or metadata is None:return {'status':'missing','evidenceBoundary':'unresolved','detail':'explicit native paths required'}
    inputs=contract['nativeInputs'];_need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),'native hashes required')
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata))
    if gate.status!='validated':return {'status':gate.status,'evidenceBoundary':'unresolved','detail':gate.detail}
    image=NativeImage(gate.gameassembly,gate.metadata,label='ifix.floating-remainder');extents=image.mapper.pdata_function_extents(image.pe)
    return validate_floating_remainder_rules(image,contract['floatingRemainderRules'] if spec is None else spec,contract,extents)

_PROGRAMS = {'doubleRem': ('4881ecb8000000660f7f742450660f7f7c246066490f7ec066490f7ec9',
               ('rip', '4c8b1d', 'absoluteMask', ''),
               '4d23c34d23cb',
               ('rip', '4c8b15', 'exponentMask', ''),
               '4d3bca',
               ('rel', '0f8f', 'd_rhsNaN', 4),
               '4d3bc2',
               ('rel', '0f8f', 'd_return', 4),
               ('rel', '0f84', 'd_infinite', 4),
               '4983f900',
               ('rel', '0f84', 'd_zeroDivisor', 4),
               '4d3bc1',
               ('rel', '0f84', 'd_equal', 4),
               '66490f7ec066490f7ec9660f28e0660f28e966490f6edb660fdbe3660fdbeb660f2fe5',
               ('rel', '0f86', 'd_return', 4),
               '4d23c24d23ca49c1c83449c1c9344d85c0',
               ('rel', '0f84', 'd_x87', 4),
               '4d8bd14d85c9',
               ('rel', '0f84', 'd_x87', 4),
               '4d2bc14983f834',
               ('rel', '0f8d', 'd_x87', 4),
               '4981f8ff070000',
               ('rel', '0f84', 'd_infinite', 4),
               '660f28d4660f28ddf20f5ed3f24c0f2cc2f2490f2ad0',
               ('rip', '833d', 'featureSelector', '00'),
               ('rel', '0f85', 'd_fma', 4),
               '66490f7ed2',
               ('rip', '4c2315', 'exponentMask', ''),
               '49c1ca344981eaff0300004981e9ff0300004d03d14981faff030000',
               ('rel', '0f8d', 'd_x87', 4),
               ('rip', '660f2825', 'splitMask', ''),
               '660f28cd660f28f2660f28faf20f59fd660f54cc660f54d4f20f5ce9f20f5cf2660f28e1f20f59e2f20f5ce7f20f59cef20f58e1f20f59d5f20f58e2f20f59f5f20f58f4660f28c8',
               ('rip', '660fdb0d', 'absoluteMask', ''),
               '660f28d1f20f5ccff20f5cd1f20f5cd7f20f5cd6f20f58d1',
               ('rel', 'eb', 'd_adjust', 1),
               ('label', 'd_fma'),
               ('rip', '660f5615', 'signMask', ''),
               'c4e2e9b9e5660f28d4',
               ('label', 'd_adjust'),
               ('rip', '660f2f15', 'zero', ''),
               ('rel', '73', 'd_sign', 1),
               'f20f58d3',
               ('label', 'd_sign'),
               ('rip', '660f5405', 'signMask', ''),
               ('rip', '660f5415', 'absoluteMask', ''),
               '660f56c2',
               ('rel', 'e9', 'd_return', 4),
               '0f1f00',
               ('label', 'd_x87'),
               'f20f11442430f20f114c2440dd442440dd442430dbe266660f1f840000000000',
               ('label', 'd_x87Loop'),
               'd9f8dfe066250004663d0004',
               ('rel', '74', 'd_x87Loop', 1),
               'dd5c2430dd5c2440f20f10442430',
               ('rel', 'e9', 'd_return', 4),
               '666666666666660f1f840000000000',
               ('label', 'd_equal'),
               '660f28c8',
               ('rip', '660fdb0d', 'signMask', ''),
               ('rip', 'f20f1005', 'zero', ''),
               '660febc1',
               ('rel', 'e9', 'd_return', 4),
               '0f1f00',
               ('label', 'd_infinite'),
               '660f28c8',
               ('rip', '660feb0d', 'quietDoubleBit', ''),
               ('label', 'd_errorArgs'),
               ('rip', '488d0d', 'doubleRequestName', ''),
               'ba1600000066490f7ec841b901000000c744242008000000c744242821000000c744244002000000',
               ('call', 'errorDouble'),
               ('rel', 'eb', 'd_return', 1),
               '6666666666660f1f840000000000',
               ('label', 'd_zeroDivisor'),
               ('rip', '660f280d', 'defaultDoubleNaN', ''),
               ('rel', 'eb', 'd_errorArgs', 1),
               '660f1f440000',
               ('label', 'd_rhsNaN'),
               '660f28c1666666660f1f840000000000',
               ('label', 'd_return'),
               '660f6f7c2460660f6f7424504881c4b8000000c3'),
 'floatRem': ('f30f114424084883ec680f57d20f28e948b8ffffffffffffff7f0f28c8f30f5ad166490f7ed00f57d2f30f5ad5498bc84d8bc848c1e9344c23c881e1ff07000066490f7ed3498bd34d8bd348c1ea344c23d081e2ff07000083f901',
              ('rel', '0f8c', 'f_special', 4),
              '81f9fe070000',
              ('rel', '0f8f', 'f_nanNumerator', 4),
              '8d42ff3dfd070000',
              ('rel', '0f87', 'f_special', 4),
              '4d3bca',
              ('rel', '75', 'f_differentMagnitude', 1),
              '48b800000000000000804c23c066490f6ec0660f5ac04883c468c3',
              ('label', 'f_differentMagnitude'),
              '66490f6ed166490f6eda',
              ('rel', '73', 'f_chunkBegin', 1),
              '0f57c00f2fc1',
              ('rel', '76', 'f_smallerConvert', 1),
              ('rip', '0f5715', 'floatSignMask', ''),
              ('label', 'f_smallerConvert'),
              '0f57c0f20f5ac24883c468c3',
              ('label', 'f_chunkBegin'),
              '0fae5c2478448b4c24783bca',
              ('rel', '0f8e', 'f_finish', 4),
              '2bcab8abaaaa2af7e9448bc233d241c1f802418bc0c1e81f4403c0438d04408d04c5ff0300004863c848b8000000000000703e48c1e13466480f6ee066480f6ec1f20f59d84183f808',
              ('rel', '0f8c', 'f_remaining', 4),
              '418d40f8c1e803ffc08bc88d14c5000000006666660f1f840000000000',
              ('label', 'f_groupLoop'),
              '0f57c90f28c2f20f5ec3f20f2cc0f20f2ac8f20f59cbf20f59dcf20f5cd10f57c90f28c2f20f5ec3f20f2cc0f20f2ac8f20f59cbf20f59dcf20f5cd10f57c90f28c2f20f5ec3f20f2cc0f20f2ac8f20f59cbf20f59dcf20f5cd10f57c90f28c2f20f5ec3f20f2cc0f20f2ac8f20f59cbf20f59dcf20f5cd10f57c90f28c2f20f5ec3f20f2cc0f20f2ac8f20f59cbf20f59dcf20f5cd10f57c90f28c2f20f5ec3f20f2cc0f20f2ac8f20f59cbf20f59dcf20f5cd10f57c90f28c2f20f5ec3f20f2cc0f20f2ac8f20f59cbf20f59dcf20f5cd10f57c90f28c2f20f5ec3f20f2cc0f20f2ac8f20f59cbf20f59dcf20f5cd14883e901',
              ('rel', '0f85', 'f_groupLoop', 4),
              ('label', 'f_remaining'),
              '413bd0',
              ('rel', '7d', 'f_finish', 1),
              '442bc2418bc8',
              ('label', 'f_remainingLoop'),
              '0f28c2f20f5ec3f20f2cc0660f6ec8f30fe6c9f20f59cbf20f59dcf20f5cd14883e901',
              ('rel', '75', 'f_remainingLoop', 1),
              ('label', 'f_finish'),
              '0f28c244894c2478f20f5ec3f20f2cc0660f6ec8f30fe6c9f20f59cbf20f5cd1660f7f5424500fae5424780f57c00f2f442470660f6fc2',
              ('rel', '76', 'f_finishConvert', 1),
              ('rip', '0f5705', 'floatSignMask', ''),
              ('label', 'f_finishConvert'),
              'f20f5ac04883c468c3',
              ('label', 'f_special'),
              '81f9fe070000',
              ('rel', '7e', 'f_denominatorSpecial', 1),
              ('label', 'f_nanNumerator'),
              '48b8ffffffffffff0f004c85c0',
              ('rel', '74', 'f_invalid', 1),
              '0f57c9f30f10c8660f7ec94883c468',
              ('rel', 'e9', 'quietFloat', 4),
              ('label', 'f_denominatorSpecial'),
              '81fafe070000',
              ('rel', '7e', 'f_zeroExponentCheck', 1),
              '48b8ffffffffffff0f004c85d8',
              ('rel', '74', 'f_returnOriginal', 1),
              '0f57c9f30f10cd660f7ec94883c468',
              ('rel', 'e9', 'quietFloat', 4),
              ('label', 'f_zeroExponentCheck'),
              '83f901',
              ('rel', '7d', 'f_invalid', 1),
              '83fa01',
              ('rel', '7d', 'f_returnOriginal', 1),
              ('label', 'f_invalid'),
              'c744244002000000',
              ('rip', '488d0d', 'floatRequestName', ''),
              'f30f116c243841b901000000f30f114c243041b80000c0ffc744242821000000c744242008000000418d5115',
              ('call', 'errorFloat'),
              ('label', 'f_returnOriginal'),
              '4883c468c3'),
 'errorDouble': ('405553564156488d6c24f84881ec080100000f29b424f0000000',
                 ('rip', '488b05', 'securityCookie', ''),
                 '4833c4488945e08bf248c7442438000000004c8bf14c894424308b4d50488d542438418bd9',
                 ('call', 'statusMap'),
                 'f20f10756885c0',
                 ('rel', '74', 'ed_modeQuery', 1),
                 '837d70020f57c00f114424700f1145800f1145900f1145a00f1145b00f1145c00f1145d0',
                 ('rel', '75', 'ed_recordDetails', 1),
                 'f20f1175a0c745b003000000',
                 ('label', 'ed_recordDetails'),
                 '448b4550488d4424304889442428488d542438488d4560448bce488d4c24704889442420',
                 ('call', 'recordDouble'),
                 ('label', 'ed_modeQuery'),
                 ('call', 'modeQuery'),
                 '84c0',
                 ('rel', '74', 'ed_returnDefault', 1),
                 '85db',
                 ('rel', '74', 'ed_returnDefault', 1),
                 'f20f104560488d4c2440f20f104c243033c0f20f11442450f20f114c246089442444f20f11742458895c24404c89742448',
                 ('call', 'callbackRequest'),
                 '85c0',
                 ('rel', '75', 'ed_callbackResult', 1),
                 '8bcb',
                 ('call', 'statusRequest'),
                 ('label', 'ed_callbackResult'),
                 'f20f10442460',
                 ('rel', 'eb', 'ed_epilogue', 1),
                 ('label', 'ed_returnDefault'),
                 '8bcb',
                 ('call', 'statusRequest'),
                 'f20f10442430',
                 ('label', 'ed_epilogue'),
                 '488b4de04833cc',
                 ('call', 'cookieCheck'),
                 '0f28b424f00000004881c408010000415e5e5b5dc3'),
 'errorFloat': ('405553564156488d6c24f84881ec080100000f29b424f0000000',
                ('rip', '488b05', 'securityCookie', ''),
                '4833c4488945e08bf248c7442438000000004c8bf144894424308b4d50488d542438418bd9',
                ('call', 'statusMap'),
                'f30f10756885c0',
                ('rel', '74', 'ef_modeQuery', 1),
                '837d70020f57c00f114424700f1145800f1145900f1145a00f1145b00f1145c00f1145d0',
                ('rel', '75', 'ef_recordDetails', 1),
                'f30f1175a0c745b001000000',
                ('label', 'ef_recordDetails'),
                '448b4550488d4424304889442428488d542438488d4560448bce488d4c24704889442420',
                ('call', 'recordFloat'),
                ('label', 'ef_modeQuery'),
                ('call', 'modeQuery'),
                '84c0',
                ('rel', '74', 'ef_returnDefault', 1),
                '85db',
                ('rel', '74', 'ef_returnDefault', 1),
                'f30f104560488d4c24400f5ac033c0895c2440894424444c897424480f5acef20f11442450f30f104424300f5ac0f20f114c2458f20f11442460',
                ('call', 'callbackRequest'),
                '85c0',
                ('rel', '75', 'ef_callbackResult', 1),
                '8bcb',
                ('call', 'statusRequest'),
                ('label', 'ef_callbackResult'),
                'f20f10442460660f5ac0',
                ('rel', 'eb', 'ef_epilogue', 1),
                ('label', 'ef_returnDefault'),
                '8bcb',
                ('call', 'statusRequest'),
                'f30f10442430',
                ('label', 'ef_epilogue'),
                '488b4de04833cc',
                ('call', 'cookieCheck'),
                '0f28b424f00000004881c408010000415e5e5b5dc3')}
