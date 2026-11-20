"""Validate bounded postconstruction refresh dispatch and Tick allow-copy relations."""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.skill_request_cache_native import _validate_declarations,COMBO,REQUEST
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data.skill_ai_dispatch_native import _strict

CONTRACT_PATH=CONTRACTS_DIR/'skill_request_refresh_tail_native.json'
SCHEMA='endfield.skill-request-refresh-tail-native-contract.v2'
LABEL='skillRequestRefreshTail'


def _rules():
    return {'scope':'successful-postconstruction-only','virtualSlot':11,'deltaArgumentsFloat32Hex':['00000000']*3,
        'dynamicTargetMustEqualNamedTick':True,'tickOriginalPathRequired':True,'normalReturnsRequired':True,
        'refreshReturnsTrueAfterDispatch':True,'allowResultSource':'_AllowNextSkill.AL',
        'allowStoreMechanism':'AL to R9B to replacement local to whole request copyback',
        'genericBranchReachedRequired':True,'carrierContinuityRequired':True,'dispatcherComparisonCfgProved':False,
        'fullTickExpiryReproved':False,'liveIFixSelectionProved':False,'fullReceiverContinuityProved':False}


def _validate(image,c):
    methods,fields=_validate_declarations(image,c)
    tick=methods[COMBO+'.Tick'];allow=methods[COMBO+'._AllowNextSkill'];refresh=methods[COMBO+'.RefreshNextSkillRequest']
    _require(tick['slot']==11 and tick['returnType']=='void' and _strict(tick['parameters'],[
        {'name':'allScaledTime','type':'float'},{'name':'timeManagerDeltaTime','type':'float'},{'name':'unscaledDeltaTime','type':'float'}]),'tail-tick-signature','slot11 void(Single,Single,Single)',tick)
    windows={x['role']:x for x in c['codeWindows']}
    _require(set(windows)=={'refreshTail','dispatch','tickTransfer'}and len(windows)==len(c['codeWindows']),'tail-window-coverage','three',windows)
    image.check_windows(c['codeWindows'],label=LABEL)
    for role,method in [('refreshTail',refresh),('tickTransfer',tick)]:
        w=windows[role];family=image.unwind_index.family(method['identity'][3])
        _require(any(x['runtimeTriple'][0]<=w['startRva']<w['endRva']<=x['runtimeTriple'][1]for x in family['ranges']),'tail-method-ownership',role,w)
    a={}
    for role,row in c['anchors'].items():
        raw=bytes.fromhex(row['hex']);at=row['rva']
        _require(any(w['startRva']<=at and at+len(raw)<=w['endRva']for w in windows.values())and image.pe.bytes_at_va(image.pe.image_base+at,len(raw))==raw,'tail-anchor-bytes',role,row);a[role]=raw
    d=c['operandDeclarations'];layout=c['layout']
    base=fields[COMBO+'::m_nextSkillRequest']['offset'];offset=fields[REQUEST+'::allowToCastNextSkill']['offset']
    payload=base+layout['outerValueOffset'];allow_unboxed=offset-layout['objectHeaderBytes']
    _require(d['allowLocal']==d['replacementLocal']+allow_unboxed
        and d['requestBuffer16']==d['requestBuffer']+16
        and d['requestPayload16']==payload+16 and d['requestPayload32']==payload+32
        and d['outerValueLocal']==d['outerNullableLocal']+layout['outerValueOffset']+8
        and d['outerLocal32']==d['outerNullableLocal']+32,
        'tail-typed-copy-offset','typed payload and declared stack copy geometry',d)
    def enc(name,size=1):
        value=d[name];_require(type(value)is int,'tail-operand-type','int',name)
        return value.to_bytes(size,'little',signed=value<0).hex()
    expected={'tailArguments':'0f57d2b9'+tick['slot'].to_bytes(4,'little').hex()+'0f57dbf30f115424'+enc('outgoingThirdStack')+'488bd3e8',
        'tailReturn':'b001eb'+enc('tailSuccessJump')+'32c0',
        'dispatchSlot':'488b07488d4b'+enc('vtableBaseUnits')+'4803c9488b14c84c8b44c8'+enc('methodInfoByteOffset'),
        'dispatchForward':'f30f109c24'+enc('incomingThirdStack',4)+'0f28d60f28cf4c894424'+enc('outgoingThirdStack')+'488bcfffd2eb'+enc('genericReturnJump'),
        'tickSetup':'0f1047'+payload.to_bytes(1,'little').hex()+'4533c0488bcf0f104f'+enc('requestPayload16')+'0f114424'+enc('requestBuffer')+'488b5c24'+enc('requestBuffer')+'0f1047'+enc('requestPayload32')+'488bd3',
        'tickAL':'440fb6c8','tickAllowLocal':'f3410f5cc044884d'+enc('allowLocal'),
        'tickCopyIn':'0f114d'+enc('copyInOffset'),
        'tickOuterLoad':'0f288d'+enc('outerValueLocal',4)+'c685'+enc('outerNullableLocal',4)+'010f2885'+enc('outerNullableLocal',4)+'0f1147'+base.to_bytes(1,'little').hex()+'0f2885'+enc('outerLocal32',4)+'0f114f'+(base+16).to_bytes(1,'little').hex()}
    _require(set(a)==set(expected)|{'tickCall','special0','special1','special2'},'tail-anchor-coverage',list(expected),list(a))
    for role,want in expected.items():
        actual=a[role][:-4]if role=='tailArguments'else a[role]
        _require(actual==bytes.fromhex(want),'tail-operand-program',role,actual.hex())
    links=c['links'];call=c['anchors']['tailArguments']['rva']+len(a['tailArguments'])-5
    _require(call+5+struct.unpack('<i',a['tailArguments'][-4:])[0]==links['dispatcherRva']==windows['dispatch']['startRva'],'tail-dispatch-target',links,call)
    raw=a['tickCall'];at=c['anchors']['tickCall']['rva']
    _require(raw[0]==0xe8 and at+5+struct.unpack('<i',raw[1:5])[0]==allow['identity'][3]
        and raw[5:7]==bytes.fromhex('833d')and raw[-4:]==bytes.fromhex('0f1145'+enc('zeroVectorLocal'))and at==links['tickAllowCallRva']
        and at+5==links['tickAllowReturnRva']and at+len(raw)==c['anchors']['tickAL']['rva'],'tail-allow-return-join',allow,raw.hex())
    anchors=c['anchors']
    _require(anchors['tailArguments']['rva']+len(a['tailArguments'])==anchors['tailReturn']['rva'],
        'tail-return-adjacency','call returns into success AL',anchors['tailReturn'])
    order=['tickSetup','tickCall','tickAL','tickAllowLocal','tickCopyIn','tickOuterLoad']
    _require(all(anchors[left]['rva']+len(a[left])<=anchors[right]['rva']for left,right in zip(order,order[1:])),
        'tail-transfer-order','call -> AL capture -> local -> copy -> store',order)
    special=[]
    for role in ('special0','special1','special2'):
        at=c['anchors'][role]['rva'];raw=a[role]
        _require(raw[:3]==bytes.fromhex('488d05'),'tail-special-target-lea','RAX target address',raw.hex());special.append(at+7+struct.unpack('<i',raw[3:])[0])
    _require(special==links['specialTargets']and tick['identity'][3]not in special,'tail-special-comparison-operands','Tick unequal declared special operands; branch reach remains premise',special)
    _require(_strict(c['rules'],_rules()),'tail-rules-boundary',_rules(),c['rules'])
    return {'rules':_rules(),'callSites':{'tickAllow':{'method':allow['identity'],'callRva':links['tickAllowCallRva'],'returnRva':links['tickAllowReturnRva']},'refreshDispatcher':{'physicalTargetRva':links['dispatcherRva'],'virtualSlot':11}},'boundary':c['evidenceBoundary']}


def load_skill_request_refresh_tail(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit={'status':'validation_failed','rules':{},'callSites':{},'failures':[]}
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL);pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        image=open_native_image(gate.gameassembly,gate.metadata);result=_validate(image,c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        _require(after.status=='validated','tail-native-after','validated',after.status)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'tail-contract-after','unchanged',str(path))
        audit.update(result,status='validated-conditional-fragments',nativeInputs=dict(pins))
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',rules={},callSites={},failures=[{'check':str(error)[:1000],'source':str(path)}])
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('gameassembly','metadata','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=load_skill_request_refresh_tail(gameassembly=a.gameassembly,metadata=a.metadata)
    from scripts.repo_paths import REPO_ROOT
    _require(any(a.output.resolve().is_relative_to(REPO_ROOT/x)for x in ('reports','scratch','tmp')),'tail-output-root','ignored',a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if r['status']=='validated-conditional-fragments'else 1


if __name__=='__main__':raise SystemExit(main())
