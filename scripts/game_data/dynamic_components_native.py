"""Authenticate the complete stored fb_main struct graph on a selected build.

The main-vector owner remains authoritative for grid fields and strides.
This owner checks every declared child getter, its actual stored displacement,
and every reverse Prep/Put/zero-Pad byte of each generated struct builder.
The proof concerns stored syntax under the selected normal native paths.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_component_programs import SCALARS, constant_program, expected_writes, instruction_offset, need
from scripts.game_data.dynamic_main_native import validate_native_layout as validate_main
from scripts.game_data.dynamic_scalar_components_native import _validate_carriers
from scripts.game_data.il2cpp.integer_addressing import _address, _prefix, _required, decode_lea_address
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import canonical_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext


CONTRACT = CONTRACTS_DIR / 'dynamic_components_native.json'
SCHEMA = 'endfield.dynamic-components-native-contract.v1'


def _one(raw, start, mapper):
    from scripts.game_data.il2cpp.register_shift_instructions import DECODERS
    from scripts.game_data.il2cpp.integer_effects import decode_locked_memory_exchange
    for decoder in (*DECODERS, decode_lea_address, decode_locked_memory_exchange, decode_memory_move):
        result = decoder(raw, 0, start)
        if result is not None: return result
    return mapper.decode_one_x64(raw, 0, start)


def decode_program(raw, start, mapper):
    """A complete instruction partition; unknown or truncated bytes refuse."""
    rows=[]; cursor=0
    while cursor < len(raw):
        row, end = _one(raw[cursor:], start+cursor, mapper)
        encoded=bytes.fromhex(row.get('bytes',''))
        need('instruction-partition', 0 < end <= len(raw)-cursor and encoded == raw[cursor:cursor+end]
             and not row['text'].startswith(('db','unknown','ff/')), (hex(start+cursor),row['text']))
        row=dict(row,offset=cursor); rows.append(row); cursor+=end
    return rows


def _scalar_memory_offset(raw, width, *, indexed=True):
    decoded=decode_memory_move(raw,0,0)
    if decoded is not None:
        row,end=decoded; op=row['memoryOperation']; address=op['address']
        need('own-inline-read-width', end==len(raw) and op['direction']=='load' and op['memoryBytes']==width
             and not address['ripRelative'] and address['base'] is not None and (not indexed or address['index'] is not None))
        return address['displacement']
    at,rex=_prefix(raw,0)
    if raw[at:at+3]==b'\xf3\x0f\x10':
        at+=3;modrm=raw[at];at+=1
        address,end=_address(raw,at,modrm,rex,0,'dynamic-inline-float')
        need('own-inline-float-width',width==4 and end==len(raw) and address['base'] is not None
             and address['index'] is not None and not address['ripRelative'])
        return address['displacement']
    need('own-inline-bool-comparison', width==1 and raw[:2]==b'\x80\x3c' and raw[-1:]==b'\x00')
    address,end=_address(raw,2,raw[1],0,0,'dynamic-inline-bool')
    need('own-inline-bool-address',end+1==len(raw) and address['base'] is not None and address['index'] is not None)
    return address['displacement']


def _proof_bytes(method, site, image):
    rva=site['rva'];raw=bytes.fromhex(site['bytes'])
    need('owned-nonempty-native-proof', bool(raw) and any(w['startRva']<=rva and rva+len(raw)<=w['endRva'] for w in method['windows']))
    actual=image.pe.bytes_at_va(image.pe.image_base+rva,len(raw))
    need('native-proof-bytes',actual==raw,(method['index'],hex(rva)))
    return actual


def validate_padding(padding, methods, image, context):
    """Reprove minimal Prep arithmetic and its actual counted zero writer."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    selected=padding['methods'];programs=padding['programs'];base=image.pe.image_base
    owner='Google.FlatBuffers.FlatBufferBuilder'
    space=context.field(owner+'::_space')[2];bb=context.field(owner+'::_bb')[2]
    minimum=context.field(owner+'::_minAlign')[2]
    need('small-selected-builder-field-offsets',all(0<n<128 for n in (space,bb,minimum)))
    length=padding['lengthGetter'];idx=length['index']
    image.validate_method_row([idx,'Google.FlatBuffers.ByteBuffer','get_Length',length['rva']],label='dynamicComponents.padding')
    lm=image.metadata.methods[idx]
    need('selected-length-getter-ABI',not image.metadata.parameters_for(lm)
         and canonical_type_name(context.type_name(lm.return_type))=='System.Int32')
    lraw=image.pe.bytes_at_va(base+length['rva'],4)
    need('actual-ByteBuffer-Length-load',lraw[:2]==b'\x8b\x41'and lraw[-1:]==b'\xc3')
    capacity=bb+lraw[2];need('small-capacity-member',capacity<128)
    def check(name,method_name,tokens,call_target=None):
        method=methods[selected[method_name]];site=programs[name]
        raw=_proof_bytes(method,site,image);g=BytesPath([(base+site['rva'],raw)],base+site['rva'])
        g.take(*tokens)
        if call_target is not None:g.call(base+methods[selected[call_target]]['rva'])
        need('complete-padding-source-program:'+name,g.at==base+site['rva']+len(raw))
    def byte(n):return bytes((n,)).hex()
    check('padArguments','Pad',['8bf2','488bf9'])
    check('padSpace','Pad',['8b5f'+byte(space),'2bde','895f'+byte(space)])
    check('padZeroCall','Pad',['488d4f'+byte(bb),'48c744242000000000','448bce','4533c0','8bd3'],'PutByteCount')
    put=methods[selected['PutByteCount']]
    need('actual-counted-byte-writer',(put['type'],put['method'],put['parameters'])==
         ('Google.FlatBuffers.ByteBuffer','PutByte',['System.Int32','System.Byte','System.Int32']))
    check('byteArguments','PutByteCount',['418bf1'])
    check('byteZeroIndex','PutByteCount',['33db'])
    check('byteValue','PutByteCount',['418af8'])
    check('byteLoop','PutByteCount',['8b4c2438','85c9','7e15','488b442430','3bd9','7327','408838','ffc3','48ffc0','3bd9','7cf2'])
    check('prepArguments','Prep',['418be8','8bda','488bf9'])
    check('prepMinimum','Prep',['3b5f'+byte(minimum),'7e03','895f'+byte(minimum)])
    check('prepFormula','Prep',['8b77'+byte(space),'8d43ff','2b77'+byte(capacity),'2bf5','23f0','8d041e','03e8'])
    check('prepPadCall','Prep',['85f6','7e0d','4533c0','8bd6','488bcf'],'Pad')
    # The public vector method performs both the count-word Prep and the
    # element-alignment Prep with the same exact count*width product.
    check('vectorFirst','StartVector',['448bc7','895e64','4533c9','440fafc3','488bce','418d5104'],'Prep')
    site=programs['vectorSecond'];raw=_proof_bytes(methods[selected['StartVector']],site,image)
    g=BytesPath([(base+site['rva'],raw)],base+site['rva'])
    g.take('0faffb','4533c9','8bd5','488bce','448bc7','488b5c2430','488b6c2438','488b742440','4883c420','5f')
    need('vector-second-Prep-tail',g.relative('e9')==base+methods[selected['Prep']]['rva']and g.at==base+site['rva']+len(raw))
    check('finishPrep','Finish',['8b57'+byte(minimum),'448d049d04000000','4533c9','488bcf'],'Prep')
    need('actual-string-NUL-writer',(methods[selected['AddByte']]['type'],methods[selected['AddByte']]['method'],methods[selected['AddByte']]['parameters'])==
         (owner,'AddByte',['System.Byte']))
    check('stringOne','CreateString',['bf01000000'])
    check('stringNul','CreateString',['4533c0','33d2','488bce'],'AddByte')
    check('stringVector','CreateString',['448bcf','48c744242000000000','448bc0','8bd7','488bce','8bd8'],'StartVector')
    need('main-and-child-builder-share-Prep',methods[selected['Prep']]['index']==padding['prepMethodIndex'])
    return dict(minimalAlignmentFormulaProved=True,countedZeroWriterProved=True,
                vectorCountAndElementAlignmentProved=True,stringNulAndAlignmentProved=True,finishRootOffsetAlignmentProved=True)


def prove_getter(field, method, image, *, carriers, readers):
    proof=field['getterProof']; kind=proof['kind']; width=SCALARS.get(field['type'],('',0))[1]
    raw=_proof_bytes(method,proof['offsetInstruction'],image)
    if kind=='inline':
        need('inline-scalar-nominal-type',field['type'] in SCALARS)
        actual=_scalar_memory_offset(raw,width)
    else:
        base=_proof_bytes(method,proof['positionLoad'],image)
        decoded=decode_memory_move(base,0,0)
        # MOVSXD position loads occur in the direct indexed getter profile.
        if decoded is None and base[:2]in(b'\x48\x63',b'\x4c\x63'):
            at,rex=_prefix(base,0);modrm=base[at+1]
            address,end=_address(base,at+2,modrm,rex,0,'dynamic-position-load')
            need('signed-position-load',end==len(base) and address['displacement']==0 and address['index'] is None)
        else:
            need('parent-inline-position-load', decoded is not None and decoded[1]==len(base))
            op=decoded[0]['memoryOperation'];address=op['address']
            need('parent-inline-position-address',op['direction']=='load' and op['memoryBytes']==4
                 and not address['ripRelative'] and address['base'] is not None
                 and address['index'] is None and address['displacement']==0)
            source_register=op['backingRegister']
        actual=0 if proof['offsetKind']=='position-base' and raw==base else instruction_offset(raw,proof['offsetKind'])
        call=_proof_bytes(method,proof['readCall'],image)
        need('own-direct-read-call',len(call)==5 and call[0]==0xe8)
        target=proof['readCall']['rva']+5+int.from_bytes(call[1:],'little',signed=True)
        need('ordered-own-getter-transfer',proof['positionLoad']['rva']<=proof['offsetInstruction']['rva']<proof['readCall']['rva']
             and proof['readCall']['rva']-proof['positionLoad']['rva']<=1024)
        if decoded is not None:
            from scripts.game_data.il2cpp.integer_addressing import _reg
            at,rex=_prefix(raw,0);opcode=raw[at];modrm=raw[at+1]
            if proof['offsetKind']=='position-lea':
                address,_=_address(raw,at+2,modrm,rex,0,'dynamic-position-transfer')
                need('same-parent-position-register',address['base']==source_register)
                output_register=_reg(((modrm>>3)&7)|((rex&4)<<1),64)
            elif proof['offsetKind']=='position-add':
                output_register=_reg((modrm&7)|((rex&1)<<3),64)
                need('same-parent-add-register',output_register==source_register)
            elif proof['offsetKind']=='zero-position':
                need('same-parent-zero-position-register',_reg((modrm&7)|((rex&1)<<3),64)==source_register)
                output_register=_reg(((modrm>>3)&7)|((rex&4)<<1),64)
            else:output_register=source_register
            if kind=='nested':
                needed='rdx'if target==carriers['initialize']['rva']else'r8'
                need('actual-child-carrier-position-argument',output_register==needed)
        if kind=='nested':
            need('own-typed-child-carrier',field['type']not in SCALARS and target in {r['rva']for r in carriers.values()})
        else:
            need('own-primitive-read',field['type']in SCALARS and target in
                 {readers[field['type']]['rva'],*readers[field['type']].get('additionalTargets',[])})
    need('independently-read-named-field-offset',actual==field['offset'],(method['type'],method['method'],field['offset'],actual))


def validate_native_layout(gameassembly: Path, metadata: Path):
    declaration,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,label='dynamicComponents',status='validated')
    pins=declaration['nativeInputs']
    gate=check_installed_native_inputs(pins['gameAssemblySha256'],pins['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    need('selected-native-inputs',gate.status=='validated',gate.detail)
    unity=Path(gameassembly).parent/'UnityPlayer.dll'
    need('selected-Unity-input',unity.is_file()and sha256_file_upper(unity)==pins['unityPlayerSha256'])
    main,_,main_pins=validate_main(gameassembly,metadata)
    need('same-main-selected-build',pins==main_pins)
    image=open_native_image(gameassembly,metadata);ctx=NativeReferenceContext(image);md=image.metadata
    methods={}
    for row in declaration['methods']:
        idx=row['index'];need('distinct-methods',idx not in methods)
        image.validate_method_row([idx,row['type'],row['method'],row['rva']],label='dynamicComponents')
        native=md.methods[idx];params=md.parameters_for(native)
        need('selected-method-signature',([canonical_type_name(ctx.type_name(p.type_index))for p in params],
             [md.string(p.name_index)for p in params],canonical_type_name(ctx.type_name(native.return_type)))==
             (row['parameters'],row['parameterNames'],row['returnType']),(row['type'],row['method']))
        family=image.unwind_index.family(row['rva'])['ranges']
        need('complete-owned-method-windows',[(w['startRva'],w['endRva'])for w in row['windows']]==[tuple(r['runtimeTriple'][:2])for r in family])
        for window in row['windows']:
            data=image.window_bytes(window)
            need('native-window-hash',hashlib.sha256(data).hexdigest().upper()==window['sha256'],(idx,window['startRva']))
        methods[idx]=row
    carrier_contract,_=read_reviewed_contract(CONTRACTS_DIR/'dynamic_scalar_components_native.json',schema='endfield.dynamic-scalar-components-native-contract.v3',label='dynamicComponents.carriers',status='validated')
    need('same-carrier-native-build',carrier_contract['nativeInputs']==pins)
    carriers=_validate_carriers(carrier_contract['layout'],image)
    readers=declaration['primitiveReaders']
    for kind,reader in readers.items():
        need('primitive-reader-type',kind in SCALARS)
        for window in reader['windows']:
            need('primitive-reader-window',hashlib.sha256(image.window_bytes(window)).hexdigest().upper()==window['sha256'])
        proof=reader['readInstruction'];raw=bytes.fromhex(proof['bytes'])
        need('primitive-read-owned-window',any(w['startRva']<=proof['rva']and proof['rva']+len(raw)<=w['endRva']for w in reader['windows']))
        need('primitive-reader-actual-read',image.pe.bytes_at_va(image.pe.image_base+proof['rva'],len(raw))==raw)
        need('primitive-reader-width',_scalar_memory_offset(raw,SCALARS[kind][1],indexed=False)==reader.get('displacement',0))
        if 'bridgeCall'in reader:
            bridge=reader['bridgeCall'];call=bytes.fromhex(bridge['bytes'])
            need('primitive-bridge-owned',any(w['startRva']<=bridge['rva']and bridge['rva']+len(call)<=w['endRva']for w in reader['windows']))
            need('primitive-bridge-actual-bytes',image.pe.bytes_at_va(image.pe.image_base+bridge['rva'],len(call))==call)
            need('primitive-bridge-to-own-raw-reader',len(call)==5 and call[0]==0xe8
                 and bridge['rva']+5+int.from_bytes(call[1:],'little',signed=True)==bridge['targetRva'])
        if 'positionTail'in reader:
            from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
            bridge=reader['positionTail'];raw=bytes.fromhex(bridge['bytes'])
            need('signed-position-tail-owned',any(w['startRva']<=bridge['rva']and bridge['rva']+len(raw)<=w['endRva']for w in reader['windows']))
            need('signed-position-tail-bytes',image.pe.bytes_at_va(image.pe.image_base+bridge['rva'],len(raw))==raw)
            g=BytesPath([(image.pe.image_base+bridge['rva'],raw)],image.pe.image_base+bridge['rva'])
            g.take('8bd3','488bcf','488b5c2430','4883c420','5f')
            need('signed-position-preserves-arguments-and-word',g.relative('e9')==image.pe.image_base+readers['System.UInt64']['rva']
                 and g.at==image.pe.image_base+bridge['rva']+len(raw))
            need('same-unsigned-span-read',reader['unsignedSlice']==readers['System.UInt64']['bridgeCall']
                 and readers['System.UInt64']['bridgeCall']['targetRva']==reader['rva'])
    padding_proof=validate_padding(declaration['padding'],methods,image,ctx)
    records={r['type']:r for r in declaration['records']}
    need('distinct-records',len(records)==len(declaration['records']))
    visited=set();pending=set()
    def require_child(name):
        need('finite-nominal-child-graph',name in records and name not in pending,name)
        if name in visited:return
        pending.add(name);record=records[name]
        need('positive-struct-width-alignment',type(record['width'])is int and record['width']>0
             and type(record['alignment'])is int and record['alignment']>0
             and record['alignment']&(record['alignment']-1)==0 and record['width']%record['alignment']==0,name)
        need('distinct-named-fields',bool(record['fields'])and len(record['fields'])==len({f['name']for f in record['fields']}),name)
        for field in record['fields']:
            if field['type']not in SCALARS:require_child(field['type'])
        pending.remove(name);visited.add(name)
    for record in records.values():require_child(record['type'])
    targets={}
    for name,idx in declaration['builderMethods'].items():
        method=methods[idx]
        need('builder-library-owner',method['type']=='Google.FlatBuffers.FlatBufferBuilder')
        role=(name,None)if name in ('prep','pad')else('put',name)
        targets[image.pe.image_base+method['rva']]=role
    for record in records.values():
        actual=[m for m in md.methods_for(image.named_types[record['type']])if md.string(m.name_index).startswith('get_')and md.string(m.name_index)!='get_ByteBuffer']
        need('every-declared-child-getter',[m.index for m in actual]==[f['getterMethodIndex']for f in record['fields']],record['type'])
        for field in record['fields']:
            m=methods[field['getterMethodIndex']]
            need('own-named-child-getter',(m['type'],m['method'],m['parameters'],m['returnType'])==(record['type'],'get_'+field['name'],[],field['type']))
            prove_getter(field,m,image,carriers=carriers,readers=readers)
        builder=methods[record['builderMethodIndex']]
        def flatten(r,prefix=''):
            for f in r['fields']:
                if f['type']in SCALARS:yield prefix+f['name'],f['type']
                else:yield from flatten(records[f['type']],prefix+f['name']+'_')
        flat=list(flatten(record))
        need('complete-own-builder-parameters',builder['type']==record['type']and builder['method']=='Create'+record['type'].rsplit('.',1)[-1]
             and builder['parameters']==['Google.FlatBuffers.FlatBufferBuilder',*[k for n,k in flat]]
             and [n.casefold()for n in builder['parameterNames'][1:]]==[n.casefold()for n,k in flat],record['type'])
        program=record['builderProgram'];raw=_proof_bytes(builder,program,image)
        rows=decode_program(raw,image.pe.image_base+program['rva'],image.mapper)
        constant_program(rows,targets,width=record['width'],alignment=record['alignment'],expected_writes=expected_writes(record,records))
    bound={r['gridFieldIndex']:r for r in records.values()if 'gridFieldIndex'in r}
    need('all-inline-grid-children',set(bound)=={v['fieldIndex']for v in main['vectors']if v['elementKind']=='struct'})
    for vector in main['vectors']:
        if vector['elementKind']!='struct':continue
        row=bound[vector['fieldIndex']]
        need('actual-parent-child-width-alignment', (row['type'],row['width'],row['alignment'])==
             (vector['elementType'],vector['elementWidth'],vector['elementAlignment']),vector['name'])
    return dict(records=records,main=main,nativeInputs=pins,padding=padding_proof,methods=methods,image=image)
