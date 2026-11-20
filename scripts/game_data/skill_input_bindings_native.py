"""Authenticate input enum names, callback entry ABI and local attack held writes."""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import field_defaults,native_enum_members
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data.skill_ai_dispatch_native import _strict

SCHEMA='endfield.skill-input-bindings-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-input-bindings-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_input_bindings_native.json'
LABEL='skillInputBindings'
BINDING='Beyond.Input.InputBindingInfo'
PC='Beyond.Gameplay.Core.PlayerController'


def _declarations(image,contract):
    c=NativeReferenceContext(image);md=image.metadata;methods={}
    for row in contract['methods']:
        index=image.validate_method_row(row['identity'],label=LABEL);m=md.methods[index]
        actual={'id':md.type_full_name(md.types[m.declaring_type])+'.'+md.string(m.name_index),'identity':row['identity'],
            'returnType':c.type_name(m.return_type),'parameters':[{'name':md.string(p.name_index),'type':c.type_name(p.type_index)}for p in md.parameters_for(m)],
            'slot':m.slot,'isStatic':bool(m.flags&16)}
        _require(_strict(actual,row)and row['id']not in methods,'input-method-declaration',row,actual);methods[row['id']]=row
    fields=_validate_fields(image,contract['fields'])
    for row in fields.values():c.field(row['type']+'::'+row['name']);_require(row['static']is False,'input-instance-field',False,row)
    enums={};defaults=field_defaults(md)
    for row in contract['enums']:
        actual=native_enum_members(md,defaults,image.pe,image.registration,row['type'])
        _require(_strict(actual,row['members'])and row['type']not in enums,'input-enum-members',row,actual);enums[row['type']]=actual
    _require(set(enums)=={'Beyond.Input.KeyboardKeyCode','Beyond.Input.InputTimingType'},'input-enum-coverage','selected key and timing enums',list(enums))
    return methods,fields,enums


def _validate(image,contract):
    methods,fields,enums=_declarations(image,contract);windows={r['role']:r for r in contract['codeWindows']}
    expected={'callbackEntry':BINDING+'._RealTriggerCallback','attackStart':PC+'.StartCastNormalAttack','attackEnd':PC+'.EndCastNormalAttack'}
    _require(set(windows)==set(expected)and len(windows)==len(contract['codeWindows']),'input-window-coverage',list(expected),list(windows));image.check_windows(list(windows.values()),label=LABEL)
    for role,method in expected.items():
        w=windows[role];family=image.unwind_index.family(methods[method]['identity'][3])
        _require(w['method']==method and 0<w['endRva']-w['startRva']<=0x1000
            and any(r['runtimeTriple'][0]<=w['startRva'] and w['endRva']<=r['runtimeTriple'][1]for r in family['ranges']),
            'input-window-owner',(role,method),w)
    operands=contract['operands'];_require(set(operands)=={'callbackArgumentSaves','attackStartStore','attackEndStore'},'input-operand-coverage','ABI save and held writes',list(operands))
    for role,row in operands.items():
        raw=bytes.fromhex(row['hex']);w=windows[{'callbackArgumentSaves':'callbackEntry','attackStartStore':'attackStart','attackEndStore':'attackEnd'}[role]]
        _require(w['startRva']<=row['rva'] and row['rva']+len(raw)<=w['endRva']
            and image.pe.bytes_at_va(image.pe.image_base+row['rva'],len(raw))==raw,'input-operand-bytes',row,'different selected bytes')
    _require(bytes.fromhex(operands['callbackArgumentSaves']['hex'])==bytes.fromhex('410fb6e8440fb6f2488bf1'),
             'input-callback-entry-abi','R8B->EBP, DL->R14D, RCX->RSI',operands['callbackArgumentSaves'])
    callback=methods[BINDING+'._RealTriggerCallback']
    _require(callback['returnType']=='bool'and callback['isStatic']is False
        and _strict(callback['parameters'],[{'name':'isRepeat','type':'bool'},{'name':'allowFailureDelay','type':'bool'}]),
        'input-callback-signature','instance Bool(Bool,Bool)',callback)
    field_id=PC+'::<castingNormalAttack>k__BackingField';field=fields[field_id]
    _require(field['valueType']=='bool'and field['ordinaryKind']==2,'input-held-field-type','actual Bool field',field)
    for role,value in [('attackStartStore',1),('attackEndStore',0)]:
        row=operands[role];_require(row['field']==field_id and bytes.fromhex(row['hex'])==bytes.fromhex('c683')+struct.pack('<i',field['offset'])+bytes([value]),
            'input-held-write-program',(field_id,value),row)
    expected_rules={'originalPathOnly':True,'entryAbi':{'method':BINDING+'._RealTriggerCallback','receiverRegister':'RCX',
        'isRepeatRegister':'DL','allowFailureDelayRegister':'R8B','resultRegister':'AL','idField':BINDING+'::<id>k__BackingField',
        'playerActionIdField':BINDING+'::playerActionId','saveSpanPremise':'incoming argument values survive entry to reviewed save span','entryToSaveContinuityProved':False},'attackHeldFlag':{'methodStart':PC+'.StartCastNormalAttack',
        'methodEnd':PC+'.EndCastNormalAttack','field':field_id,'startWrites':True,'endWrites':False,'receiverPremise':'RBX is the selected PlayerController receiver at the reviewed store','entryToStoreReceiverContinuityProved':False},
        'physicalInputProved':False,'activeKeyOverridesProved':False,'heldRepeatSchedulingProved':False,
        'longPressUltimateAcceptanceProved':False,'playerCommandAcceptanceProved':False,'runtimeExecutionProved':False}
    _require(_strict(contract['rules'],expected_rules),'input-rules-boundary',expected_rules,contract['rules'])
    return {'rules':json.loads(json.dumps(expected_rules)),'enums':enums,'methods':list(methods.values()),'fields':list(fields.values())}


def load_skill_input_bindings(contract_path:Path=CONTRACT_PATH,*,gameassembly:Path,metadata:Path):
    path=Path(contract_path);audit={'schema':AUDIT_SCHEMA,'status':'validation_failed','rules':{},'enums':{},'methods':[],'fields':[],'nativeInputs':{},'failures':[]}
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL);audit.update(contract=str(path),contractSha256=digest,evidenceBoundary=contract['evidenceBoundary']);pins=contract['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','input-native-after','unchanged selected pair',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'input-contract-after','unchanged contract bytes','changed')
        audit.update(result,status='validated',detail='',nativeInputs=dict(pins))
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:800],rules={},enums={},methods=[],fields=[],nativeInputs={})
        audit['failures'].append({'validator':LABEL,'check':str(error).split(':',1)[0],'source':str(path),'detail':str(error)[:800]})
    return audit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--gameassembly',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    _require(any(a.output.resolve().is_relative_to(REPO_ROOT/r)for r in('reports','scratch','tmp')),'input-output-root','ignored report root',a.output)
    report=load_skill_input_bindings(gameassembly=a.gameassembly,metadata=a.metadata);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('status','detail','failures')}));return 0 if report['status']=='validated'else 1


if __name__=='__main__':raise SystemExit(main())
