"""Selected original cast predicates; helper results remain conditional inputs."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.skill_timing_runtime_native import _require, _validate_fields

SCHEMA='endfield.skill-cast-gate-native-contract.v2'
AUDIT_SCHEMA='endfield.skill-cast-gate-native-audit.v2'
CONTRACT_PATH=CONTRACTS_DIR/'skill_cast_gate_native.json'
LABEL='skillCastGate'
ORDERS={
 'core':['mapNonnull','containsKey','getItem','optionalInterrupt','skillNonnull','targetCheck'],
 'target':['readiness','optionalDistance','optionalAngle'],
 'readiness':['ownerValidFirst','ownerPointerNonnull','ownerResolveSecond','ownerResolvedNonnull','typeCheck','localCooldownPredicate','CheckCost','CheckTag','CheckState']}
# Finite register/opcode grammar. Field/layout/literal operands are reviewed contract declarations.
TEMPLATES={'saveCoreInputs': '488bf1410fb6e9498bd8488bfa',
 'interruptForward': '4533c0488bd0488bce',
 'preserveFoundSkill': '488bf8',
 'saveViewInputs': '4c8bd9',
 'viewForward': '48c74424{operand1:s1}{operand2:u4}498bcbc64424{operand3:s1}{operand2:u1}44884c24{operand4:s1}458ac84c8b42{operand5:s1}488b12',
 'coreForward': '4533c0440fb6cd4c894424{operand4:s1}488bd3440fb64424{operand6:s1}488bcf',
 'distanceForward': '4533c941b0{operand7:u1}488bd3488bcd',
 'angleForward': '4533c0488bd3488bcd',
 'readinessReceiver': '488bcd',
 'ownerFirst': '488d4b{operand8:s1}488b90{operand9:s4}488b52{operand10:s1}',
 'ownerSecond': '488d4b{operand8:s1}488b90{operand11:s4}488b52{operand12:s1}',
 'ownerLoad': '488b43{operand8:s1}',
 'ownerResolve': '488b7b{operand8:s1}',
 'typeForward': 'b9{operand13:u4}488bd7',
 'localForward': '488bcb',
 'costForward': '33d2488bcb',
 'tagForward': '33d2488bcb',
 'stateForward': '33d2488bcb',
 'targetTrue': 'b0{operand7:u1}',
 'targetFalse': '32c0',
 'readinessTrue': 'b0{operand7:u1}',
 'readinessFalse': '32c0',
 'coreFalse': '32c0',
 'canonicalizeTarget': '84c00f95c0',
 'saveTargetFlags': '488be9410fb6f9410fb6f0488bda'}
PROGRAM_BINDINGS={'operand1': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand2': {'kind': 'zero'},
 'operand3': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand4': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand5': {'kind': 'viewField', 'field': 'viewTarget'},
 'operand6': {'kind': 'stackSlot', 'base': 'rsp'},
 'operand7': {'kind': 'one'},
 'operand8': {'kind': 'field', 'field': 'owner'},
 'operand9': {'kind': 'contextOffset', 'role': 'ownerFirst'},
 'operand10': {'kind': 'contextOffset', 'role': 'ownerFirst'},
 'operand11': {'kind': 'contextOffset', 'role': 'ownerSecond'},
 'operand12': {'kind': 'contextOffset', 'role': 'ownerSecond'},
 'operand13': {'kind': 'opaqueLiteral', 'role': 'typeForward'}}
NOMINAL={
 'view':('Beyond.Gameplay.Core.AbilitySystem','CanCastSkill',['inputView','skipAngle','skipDistance']),
 'core':('Beyond.Gameplay.Core.AbilitySystem','CanCastSkill',['skillId','inputTarget','skipAngle','skipDistance','skipInterruptCheck']),
 'target':('Beyond.Gameplay.Core.Skill','CanCastToTarget',['inputTarget','skipDistance','skipAngle']),
 'distance':('Beyond.Gameplay.Core.Skill','CheckCastDistance',['inputTarget','ignoreOutOfRangeStrategy']),
 'angle':('Beyond.Gameplay.Core.Skill','CheckCastAngle',['targetHandle']),
 'interrupt':('Beyond.Gameplay.Core.AbilitySystem','CheckCanInterruptCurSkill',['newSkill']),
 'cost':('Beyond.Gameplay.Core.Skill','CheckCost',[]),
 'tag':('Beyond.Gameplay.Core.Skill','CheckTag',[]),
 'state':('Beyond.Gameplay.Core.Skill','CheckState',[]),
}

def _program_operands(contract,fields,bindings):
    declared=contract['operandBindings']
    _require(set(declared)==set(bindings),'program-operand-coverage',list(bindings),list(declared))
    result={}
    for name,expected in bindings.items():
        row=declared[name]
        _require({k:v for k,v in row.items()if k!='value'}==expected,'program-operand-binding-'+name,expected,row)
        value=row['value']
        _require(type(value)is int,'program-operand-integer',name,value)
        if expected['kind']=='field':actual=fields[expected['field']]['offset']
        elif expected['kind']=='inputField':actual=fields[expected['base']]['offset']+fields[expected['field']]['offset']-contract['inputDataHeaderBytes']
        elif expected['kind']=='viewField':actual=fields[expected['field']]['offset']-contract['inputViewHeaderBytes']
        elif expected['kind']=='zero':actual=0
        elif expected['kind']=='one':actual=1
        else:
            _require(expected['kind']in('stackSlot','contextOffset','opaqueLiteral','conditionalEntityOffset'),
                'program-operand-kind','bounded reviewed declaration',expected)
            actual=value
        _require(value==actual,'program-operand-field-'+name,actual,value);result[name]=value
    return result


def _render_program(shape,operands):
    import re
    def encode(match):
        value=operands[match[1]];signed=match[2]=='s';width=int(match[3])
        try:return value.to_bytes(width,'little',signed=signed).hex()
        except OverflowError as error:raise ValueError('program-operand-range:'+match[1])from error
    return re.sub(r'\{([A-Za-z0-9_]+):([su])([1248])\}',encode,shape)



def _rule_scope(contract):
    rules=contract['rules']
    _require(rules['orderedPredicates']==ORDERS,'cast-order',ORDERS,rules['orderedPredicates'])
    for key,value in {'originalPathOnly':True,'normalHelperReturnRequired':True,
        'completePlayerInputAcceptanceProved':False,'collectionEffectsProved':False,
        'readinessManagedIdentityProved':False,'distanceGeometryProved':False,'angleGeometryProved':False,
        'missingMapKeyNormalReturn':False,'foundNullSkill':'exception',
        'readinessOwnerSecondNull':'exception','typeCheckFalseRejects':True,
        'viewSkipInterruptCheck':False,'distanceIgnoreOutOfRangeStrategy':True}.items():
        _require(rules[key]==value and type(rules[key])is type(value),'cast-boundary-'+key,value,rules[key])
    _require(rules['targetParameterOrder']==['inputTarget','skipDistance','skipAngle'],
             'cast-target-flags','distance before angle',rules['targetParameterOrder'])
    _require(len(contract['facts'])==4 and {r['id']for r in contract['facts']}=={'viewForwarding','castCore','castTarget','readiness'}
        and all(r['evidence']=='conditional' and r['boundary'] and r['rules']==rules for r in contract['facts']),
        'cast-facts','four conditional rule-bound facts',contract['facts'])
    return rules


def _relative(raw,rva):
    if len(raw)==5 and raw[0]in(0xe8,0xe9):return rva+5+struct.unpack_from('<i',raw,1)[0]
    if len(raw)==2 and raw[0]in(0x74,0x75,0xeb):return rva+2+int.from_bytes(raw[1:],'little',signed=True)
    if len(raw)==6 and raw[:2]in(b'\x0f\x84',b'\x0f\x85'):return rva+6+struct.unpack_from('<i',raw,2)[0]
    raise ValueError('cast-relative-encoding')


def _validate(image,contract):
    rules=_rule_scope(contract);context=NativeReferenceContext(image);methods={}
    for row in contract['methods']:
        role=row['id'];index=image.validate_method_row(row['identity'],label=LABEL)
        method=image.metadata.methods[index]
        actual=dict(returnType=context.type_name(method.return_type),parameters=[dict(name=image.metadata.string(p.name_index),type=context.type_name(p.type_index))for p in image.metadata.parameters_for(method)])
        _require(actual=={k:row[k]for k in actual}and not method.flags&0x10,'cast-signature',row,actual)
        expected=NOMINAL[role]
        _require((row['identity'][1],row['identity'][2],[p['name']for p in row['parameters']])==expected,
                 'cast-nominal',expected,row)
        _require(role not in methods,'cast-method-distinct','distinct',role);methods[role]=row
    _require(set(methods)==set(NOMINAL),'cast-method-coverage',list(NOMINAL),list(methods))
    windows=contract['codeWindows'];image.check_windows(windows,label=LABEL)
    owners={w['owner']:w for w in windows}
    _require(len(owners)==len(windows),'cast-window-unique','unique',windows)
    for role in ('core','view','target','readiness','missing'):
        _require(role in owners,'cast-window-required',role,list(owners))
    for role in ('core','view','target'):
        _require(owners[role]['startRva']==methods[role]['identity'][3],'cast-entry',methods[role]['identity'][3],owners[role])
    fields=_validate_fields(image,contract['fields'])
    def checked(row):
        w=owners[row['owner']];raw=bytes.fromhex(row['hex']);rva=row['rva']
        _require(raw and w['startRva']<=rva<rva+len(raw)<=w['endRva'],'cast-byte-owner',w,row)
        actual=image.pe.bytes_at_va(image.pe.image_base+rva,len(raw))
        _require(actual==raw,'cast-byte-mismatch',raw.hex(),actual.hex());return raw
    spans={r['role']:r for r in contract['spans']}
    _require(set(spans)==set(TEMPLATES),'cast-span-coverage',list(TEMPLATES),list(spans))
    operands=_program_operands(contract,fields,PROGRAM_BINDINGS)
    _require(set(contract['reviewedPrograms'])==set(TEMPLATES),'cast-reviewed-program-coverage',list(TEMPLATES),list(contract['reviewedPrograms']))
    for role,shape in TEMPLATES.items():
        template=_render_program(shape,operands)
        _require(contract['reviewedPrograms'][role]==template and checked(spans[role]).hex()==template,'cast-instruction-'+role,template,spans[role]['hex'])
    expected_edges={
      'mapNull':('coreException','0f84'),'mapMissing':('missingStart','0f84'),
      'mapSecondNull':('coreException','74'),'skipInterrupt':('skillTest','75'),
      'interruptFalse':('coreFalse','74'),'skillNull':('coreException','74'),
      'missingReturn':('coreFalse','e9'),'readinessFalse':('targetFalse','74'),
      'needsDistance':('distanceStart','74'),'needsAngle':('angleStart','74'),
      'distanceTrue':('angleSkipTest','75'),'distanceFalse':('targetFalse','eb'),
      'angleTrue':('targetTrue','75'),'firstInvalid':('firstInvalidZero','0f84'),
      'firstPointerNull':('readyFalse','0f84'),'secondInvalid':('resolvedOwnerTest','74'),
      'resolvedNull':('readyException','74'),'typeFalse':('readyFalse','74'),
      'localFalse':('readyFalse','74'),'costFalse':('readyFalse','74'),
      'tagFalse':('readyFalse','74'),'stateFalse':('readyFalse','74'),
      'firstInvalidJoin':('firstPointerTest','e9')}
    _require(len(contract['edges'])==len(expected_edges)and
        {r['source']:(r['target'],r['opcode'])for r in contract['edges']}==expected_edges,
        'cast-edge-coverage',expected_edges,contract['edges'])
    expected_calls={'viewCall':('method','core','viewForward'),
      'targetCall':('method','target','coreForward'),
      'interruptCall':('method','interrupt','interruptForward'),
      'readinessCall':('window','readiness','readinessReceiver'),
      'distanceCall':('method','distance','distanceForward'),'angleCall':('method','angle','angleForward'),
      'ownerFirstCall':('window','ownerValid','ownerFirst'),'ownerSecondCall':('window','ownerValid','ownerSecond'),
      'typeCall':('window','typeCheck','typeForward'),'localCall':('window','local','localForward'),
      'costCall':('method','cost','costForward'),'tagCall':('method','tag','tagForward'),
      'stateCall':('method','state','stateForward')}
    _require(len(contract['calls'])==len(expected_calls)and
      {r['node']:('method'if'method'in r else'window',r.get('method',r.get('window')),r.get('setup'))for r in contract['calls']}==expected_calls,
      'cast-call-coverage',expected_calls,contract['calls'])
    nodes={r['id']:r for r in contract['nodes']}
    _require(len(nodes)==len(contract['nodes']),'cast-node-unique','unique',nodes)
    for node in nodes.values():checked(node)
    for edge in contract['edges']:
        source=nodes[edge['source']];target=nodes[edge['target']];raw=checked(source)
        _require(raw[:len(bytes.fromhex(edge['opcode']))].hex()==edge['opcode']
                 and _relative(raw,source['rva'])==target['rva'],'cast-control-edge',edge,raw.hex())
    for call in contract['calls']:
        node=nodes[call['node']];raw=checked(node)
        if 'method'in call:
            target=methods[call['method']]['identity'][3]
        else:target=owners[call['window']]['startRva']
        _require(raw[0]==0xe8 and _relative(raw,node['rva'])==target,'cast-call-binding',call,raw.hex())
        if 'setup'in call:
            setup=spans[call['setup']]
            _require(setup['owner']==node['owner']and setup['rva']+len(checked(setup))==node['rva'],
                     'cast-call-contiguous-carrier',call,setup)
    def follows(left,right,middle=b''):
        a=nodes.get(left,spans.get(left));b=nodes.get(right,spans.get(right))
        _require(a['owner']==b['owner']and a['rva']+len(checked(a))+len(middle)==b['rva']
          and image.pe.bytes_at_va(image.pe.image_base+a['rva']+len(checked(a)),len(middle))==middle,
          'cast-normal-flow-'+left+'-'+right,'contiguous reviewed transfer',middle.hex())
    for call,branch in [('readinessCall','readinessFalse'),('distanceCall','distanceTrue'),
      ('angleCall','angleTrue'),('ownerFirstCall','firstInvalid'),('ownerSecondCall','secondInvalid'),
      ('typeCall','typeFalse'),('localCall','localFalse'),('costCall','costFalse'),
      ('tagCall','tagFalse'),('stateCall','stateFalse'),('interruptCall','interruptFalse')]:
        follows(call,branch,b'\x84\xc0')
    for branch,setup in [('typeFalse','localForward'),('localFalse','costForward'),
      ('costFalse','tagForward'),('tagFalse','stateForward'),('stateFalse','readinessTrue'),
      ('readinessFalse','needsDistance')]:
        follows(branch,setup,b'\x40\x84\xf6'if branch=='readinessFalse'else b'')
    follows('needsDistance','needsAngle',b'\x40\x84\xff')
    follows('needsAngle','targetTrue');follows('distanceTrue','distanceFalse')
    follows('targetCall','canonicalizeTarget')
    # Field view is conditional on the ordinary boxed-header adjustment, never a global ABI claim.
    _require(fields['activeMap']['offset']==int.from_bytes(checked(nodes['mapLoad'])[3:7],'little')
             and fields['owner']['offset']==checked(spans['ownerLoad'])[3],
             'cast-field-operands','selected metadata offsets',fields)
    _require(type(contract['inputViewHeaderBytes'])is int and contract['inputViewHeaderBytes']>0 and fields['viewSkillId']['offset']==contract['inputViewHeaderBytes']
        and fields['viewTarget']['offset']-contract['inputViewHeaderBytes']==struct.calcsize('Q') and fields['viewTarget']['ordinaryKind']==17,
        'cast-view-field-carriers','selected boxed header and one Win64 carrier; target is a value type',fields)
    for row in contract['typedContexts']:
        actual=derive_typed_usage_context(image,row['rva'],label=LABEL)
        _require(actual==row['result']and actual['typeName']=='System.Collections.Generic.Dictionary`2'
            and actual['classArguments']==['string','Beyond.Gameplay.Core.Skill']
            and actual['methodName']==row['method'],'cast-map-typed-context',row,actual)
        node=nodes[row['call']];raw=bytes.fromhex(row['hex']);checked(dict(owner='core',rva=row['rva'],hex=row['hex']))
        _require(row['method']in('ContainsKey','get_Item')and raw[:7].hex().upper()==actual['instructionHex'].upper()
            and raw[7:-5].hex()in('','488bd7')and row['rva']+len(raw)-5==node['rva']
            and raw[-5:]==checked(node),'cast-map-context-consumer','R8 context retained until actual call',row)
    _require({r['method']for r in contract['typedContexts']}=={'ContainsKey','get_Item'},'cast-map-context-coverage','two selected requests',contract['typedContexts'])
    return dict(rules)


def load_skill_cast_gate(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',nativeInputs={},rows=[],rules={},failures=[],contract=str(path))
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label=LABEL)
        audit.update(contractSha256=digest,evidenceBoundary=contract['evidenceBoundary'])
        pins=contract['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        rules=_validate(open_native_image(gate.gameassembly,gate.metadata),contract)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated','cast-native-after','validated',after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'cast-contract-after','unchanged','changed')
        audit.update(status='validated',detail='',nativeInputs=dict(pins),rows=contract['facts'],rules=rules)
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error)as error:
        audit.update(status='validation_failed',detail=str(error)[:1200],nativeInputs={},rows=[],rules={})
        audit['failures'].append(dict(validator=LABEL,source=str(path),check=str(error).split(':',1)[0],detail=str(error)[:1200]))
    return audit


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv);audit=load_skill_cast_gate(gameassembly=args.gameassembly,metadata=args.metadata)
    if args.output:
        from scripts.repo_paths import REPO_ROOT
        if not any(args.output.resolve().is_relative_to(REPO_ROOT/root)for root in('reports','scratch','tmp')):parser.error('output must be reports/scratch/tmp')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:audit[k]for k in('status','detail','failures')},indent=2));return int(audit['status']!='validated')
if __name__=='__main__':raise SystemExit(main())

