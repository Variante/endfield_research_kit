"""Prove the selected default Param<Int64> buffered storage composition.

Evidence and admission boundary:

Conditional default stored Int64 proof uses its own buffered QWORD
read/cursor and owned signed-long setter, not a claimed closed registered
unmanaged helper. Four-field order, typed allocation and pooled path remain
gated. Normal allocator/initialization/barrier, compatible storage and no
interference are required; live provider/refill/evaluation and whole-owner
admission remain unresolved.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
from scripts.game_data.il2cpp.native_image import open_native_image, native_validation_failure
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import scalar_param_native as proof, pooled_source_helper
from scripts.game_data.memorypack.wrapper_members import derive_from_image

SCHEMA = 'endfield.levelscript-long-param-native.v2'
CONTRACT_PATH = CONTRACTS_DIR / 'levelscript_long_param_native.json'


def _source(image: Any, source: dict, offsets: dict) -> None:
    label = 'levelscriptLongParam.source'
    cur, rem, adv, used = (offsets[n] for n in ('currentPtr', 'bufferLength', 'advancedCount', 'consumed'))
    expected = [b'\x48\x89\x5c\x24\x08', b'\x48\x89\x74\x24\x10', b'\x57', b'\x48\x83\xec\x20', b'\x83\x79'+bytes((rem,8)), b'\x48\x8b\xd9', None,
                b'\x48\x8b\x43'+bytes((cur,)), b'\x48\x8b\x30', b'\x8b\x7b'+bytes((rem,)), b'\x83\xc7\xf8', None,
                b'\x48\x83\x43'+bytes((cur,8)), b'\x83\x43'+bytes((adv,8)), b'\x83\x43'+bytes((used,8)), b'\x89\x7b'+bytes((rem,)),
                b'\x48\x8b\x5c\x24\x30', b'\x48\x8b\xc6', b'\x48\x8b\x74\x24\x38', b'\x48\x83\xc4\x20', b'\x5f', b'\xc3']
    image.check_windows([source['window']], label=label)
    proof.program_extent(source['instructions'], source['window'], label)
    proof.program(image, source['instructions'], expected, label)
    for at, opcode in ((6,b'\x0f\x8c'),(11,b'\x0f\x88')):
        raw=bytes.fromhex(source['instructions'][at][1])
        proof.need(label,'guardOpcode',opcode,raw[:2]); proof.need(label,'guardSize',6,len(raw))


def _composition(image: Any, contract: dict, strings: dict) -> dict:
    label='levelscriptLongParam'; p=contract['parameter']; context=NativeReferenceContext(image)
    wrappers=derive_from_image(image); wrapper=wrappers[p['typeDefinition']]; bodies=image.body_index
    proof.need(label,'wrapperName',p['wrapperName'],wrapper.name)
    proof.need(label,'wrappedType','Beyond.Gameplay.Actions.Param`1<long>',wrapper.wrapped_type)
    proof.need(label,'members',p['members'],[{'name':m.name,'declaredType':m.declared_type,'methodIndex':m.method_index} for m in wrapper.members])
    proof.need(label,'fieldTypes',[['constValue','long'],['idRef','int'],['paramSource','int'],['path','string']],[[r['name'],r['declaredType']] for r in p['orderedReads']])
    fields=image.metadata.fields_for(image.metadata.types[p['typeDefinition']])
    holder=next(f for f in fields if image.metadata.string(f.name_index)=='__instance')
    proof.need(label,'holderType',p['wrappedType'],context.type_name(holder.type_index))
    proof.ordinary(image,context.type_pointer(holder.type_index),21,label+'.holderAbi',reference=True)
    proof.need(label,'holderSlot',16,runtime_type_field_offsets(image.metadata,image.pe,image.registration,p['typeDefinition'])['__instance'])
    arguments={'constValue':('long',10,False),'idRef':('int',8,False),'paramSource':('int',8,False),'path':('string',14,True)}
    for name, record in p['methods'].items():
        image.validate_method_row([record['methodIndex'],p['wrapperName'],name,record['pointerRva']],label=label)
        image.check_windows([record['window']],label=label)
        proof.program_extent(record['instructions'],record['window'],label+'.'+name)
        image.check_instruction_windows(record['instructions'],label=label)
        if name=='GetValue': result=(p['wrappedType'],21,True); args=[]
        elif name.startswith('set___'): result=('void',1,False); args=[arguments[name[6:-2]]]
        elif name in ('.ctor','CreateInstance'): result=('void',1,False); args=[]
        else: continue
        proof.owned_method_abi(image,context,record['methodIndex'],p['typeDefinition'],result,args,label+'.'+name)
    body=bodies.body(p['wrapperName'],'Deserialize'); window=p['methods']['Deserialize']['window']
    proof.need(label,'completeDeserialize',[body.pointer-image.pe.image_base,body.pointer+body.size-image.pe.image_base],[window['startRva'],window['endRva']])
    validate_typed_usage_context(image,p['allocationContext'],label=label)
    proof.need(label,'allocationType',p['wrappedType'],p['allocationContext']['typeName'])
    proof.allocation_bridge(image,context,p,label+'.allocation')
    offsets=proof.reader_offsets(image,label)
    _source(image,contract['constantSource'],offsets)
    proof.integer_source(image,contract['int32Source'],offsets,label+'.integer')
    proof.need(label,'pathEncoding','int32-pool-index',strings.get('wireEncoding'))
    proof.parameter_joins(image,p,body,contract['constantSource'],contract['int32Source'],strings,8,label)
    for read in p['orderedReads']:
        proof.call(image,read['readCall'],label); proof.call(image,read['setterCall'],label)
        name=read['name']; slot=p['ownedFieldSlots'][name]; instructions=p['methods']['set___'+name+'__']['instructions']
        if name=='path':
            expected=[b'\x48\x83\xec\x28',b'\x48\x8b\x49\x10',b'\x48\x85\xc9',None,b'\x48\x89\x51'+bytes((slot,)),b'\x48\x83\xc1'+bytes((slot,)),b'\x48\x83\xc4\x28',None,None,b'\xcc']
        else:
            store=(b'\x48' if name=='constValue' else b'')+b'\x89\x50'+bytes((slot,))
            expected=[b'\x48\x83\xec\x28',b'\x48\x8b\x41\x10',b'\x48\x85\xc0',None,None,b'\xcc',store,b'\x48\x83\xc4\x28',b'\xc3']
        proof.program(image,instructions,expected,label+'.setter.'+name)
        branch=bytes.fromhex(instructions[3][1]); destination=8 if name=='path' else 6
        proof.need(label,'setterBranch',0x74 if name=='path' else 0x75,branch[0])
        proof.need(label,'setterBranchSize',2,len(branch))
        proof.need(label,'setterBranchTarget',instructions[destination][0],instructions[3][0]+2+int.from_bytes(branch[1:],'little',signed=True))
        if name=='path':
            proof.need(label,'pathBarrierTail',0xE9,bytes.fromhex(instructions[7][1])[0])
            proof.need(label,'pathNullThrow',0xE8,bytes.fromhex(instructions[8][1])[0])
        else: proof.need(label,'nullThrow',0xE8,bytes.fromhex(instructions[4][1])[0])
    proof.program(image,p['methods']['GetValue']['instructions'],[b'\x48\x8b\x41\x10',b'\xc3'],label+'.getter')
    return {'codecKind':'Param<long>','rawSize':8,'primitiveType':'long','pathEncoding':'int32-pool-index','evidenceBoundary':contract['evidenceBoundary']}


def validate_long_param_native_contract(*, contract_path: Path=CONTRACT_PATH, game_root: Path | None=None,
                                      gameassembly: Path | None=None, metadata: Path | None=None) -> dict:
    try:
        contract=json.loads(contract_path.read_bytes()); proof.need('levelscriptLongParam','schema',SCHEMA,contract.get('schema'))
        proof.need('levelscriptLongParam','status','exact-current-build',contract.get('status'))
        proof.need('levelscriptLongParam','codecKind','Param<long>',contract.get('codecKind'))
        proof.need('levelscriptLongParam','dependencies',[{'role':'pooledStringSource','path':pooled_source_helper.CONTRACT_PATH.name}],contract.get('dependencies'))
        pins=contract['nativeInputs']; proof.need('levelscriptLongParam','pinScope',{'GameAssembly.dll','global-metadata.dat'},set(pins))
        if (gameassembly is None) != (metadata is None):
            raise ValueError('levelscriptLongParam.explicitNativePair: both paths required')
        root=Path(game_root) if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(gameassembly) if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=Path(metadata) if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        if gate.status!='validated': return {'status':gate.status,'detail':gate.detail}
        strings=pooled_source_helper.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
        if strings.get('status')!='validated': return {'status':strings.get('status','unresolved'),'detail':strings.get('detail'),'dependency':'pooledStringSource'}
        result=_composition(open_native_image(gate.gameassembly,gate.metadata),contract,strings)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated': return {'status':after.status,'detail':after.detail}
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,strings['nativeInputs'])
        if failed:return {**failed,'dependency':'pooledStringSource'}
        return {'status':'validated','nativeInputs':pins,**result}
    except (ValueError,KeyError,OSError,IndexError,StopIteration,struct.error,TypeError) as exc:
        return native_validation_failure(exc,label='levelscriptLongParam',source_path=contract_path)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--contract',type=Path,default=CONTRACT_PATH); parser.add_argument('--game-root',type=Path)
    parser.add_argument('--gameassembly',type=Path); parser.add_argument('--metadata',type=Path)
    args=parser.parse_args(); result=validate_long_param_native_contract(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata)
    print(json.dumps(result,indent=2)); return 0 if result['status']=='validated' else 2


if __name__=='__main__': raise SystemExit(main())
