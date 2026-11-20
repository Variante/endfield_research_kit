"""Physical blackboard getter ordinary-class flow and static type substitution.

The supplied closed MethodInfo, initialized runtime context and compiled getter
declaration are distinct. Only the first is authenticated here. Normal returned
class-resolver outcomes are explicit inputs; source storage has no closed named
field ownership proof in this contract.
"""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.skill_input_blackboard_native import _contexts,SCHEMA as WRITER_SCHEMA
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data.skill_ai_dispatch_native import _strict

SCHEMA='endfield.skill-blackboard-getter-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_blackboard_getter_native.json'
GENERIC='Beyond.Gameplay.StateMachine`2'
BLACKBOARD='Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterBlackboard'


def _rules():
    return dict(ordinaryFailureClassBitMustBeClear=True,specialClassPathsProved=False,sourceReadCount=1,
        typeResolverCallCountBeforeNullTest=2,resolverResultsIndependent=True,nullSourceReturnsNullAfterResolvers=True,
        firstRelationUsesSecondResolvedType=True,firstRelationFalseReturnsNull=True,secondRelationUsesFirstResolvedType=True,
        secondRelationFalseRequestsCastFailure=True,bothRelationsTrueReturnsOriginalSource=True,classEqualityFastPathReturnsTrue=True,
        staticContextTypeParameterOrdinal=1,staticClosedSubstitution=BLACKBOARD,runtimeContextSlotBindingProved=False,
        compiledGetterClosedIdentityProved=False,namedClosedSourceFieldOwnershipProved=False,dynamicInstanceTypeProved=False,
        sameWriterConsumerInstanceProved=False,normalWin64CallsRequired=True,coherentObjectsRequired=True,
        completeRelationHelperSemanticsProved=False,completeCastFailureHelperSemanticsProved=False,
        initializedClassFastPathReturnsInputPointer=True)


class _Program:
    def __init__(self,row):self.row=row;self.at=row['startRva'];self.raw=bytes.fromhex(row['hex']);self.out=bytearray()
    def emit(self,hexcode):self.out.extend(bytes.fromhex(hexcode));self.at=self.row['startRva']+len(self.out)
    def unsigned(self,value,width=1):
        _require(type(value)is int,'getter-integer-operand','ordinary integer',value);self.out.extend(value.to_bytes(width,'little'));self.at=self.row['startRva']+len(self.out)
    def mark(self,at):_require(self.at==at,'getter-program-mark',at,self.at)
    def relative(self,opcode,target,width=4):
        prefix=bytes.fromhex(opcode);self.out.extend(prefix+(target-self.at-len(prefix)-width).to_bytes(width,'little',signed=True));self.at=self.row['startRva']+len(self.out)
    def finish(self):_require(bytes(self.out)==self.raw and self.at==self.row['endRva'],'getter-complete-program',self.raw.hex(),bytes(self.out).hex())


def _programs(c):
    windows={w['role']:w for w in c['codeWindows']};d=c['operands'];s=c['sites'];t=c['targets']
    _require(set(windows)=={'getter','slotResolver','initializedClass','relationPrefix','relationTrue','castFailure'}and len(windows)==len(c['codeWindows']),'getter-window-coverage','six complete selected fragments',windows)
    _require(all(type(v)is int for v in d.values())and d['slotIndex']==0,'getter-operand-geometry','ordinary integers and reviewed slot zero',d)
    g=_Program(windows['getter']);g.emit('48895c24');g.unsigned(d['saveRbxStack']);g.emit('48896c24');g.unsigned(d['saveRbpStack']);g.emit('48897424');g.unsigned(d['saveRsiStack']);g.emit('574883ec');g.unsigned(d['stackFrame'])
    g.mark(s['sourceRead']);g.emit('488b59');g.unsigned(d['sourceOffset']);g.emit('488bfa488b4a');g.unsigned(d['methodInfoClassOffset']);g.emit('33d2488b89');g.unsigned(d['classContextOffset'],4)
    g.mark(s['slotCall1']);g.relative('e8',t['slotResolver']);g.emit('488b4f');g.unsigned(d['methodInfoClassOffset']);g.emit('33d2');g.mark(s['firstTypeSave']);g.emit('488be8488b89');g.unsigned(d['classContextOffset'],4)
    g.mark(s['slotCall2']);g.relative('e8',t['slotResolver']);g.mark(s['secondTypeSave']);g.emit('488bf04885db');g.mark(s['sourceNullBranch']);g.relative('74',s['returnZero'],1)
    g.emit('488b3b488bc8488bd7');g.mark(s['relation1Call']);g.relative('e8',t['relation']);g.emit('84c0');g.mark(s['relation1Branch']);g.relative('74',s['flag1'],1)
    g.emit('488b3b488bcd488bd7');g.mark(s['relation2Call']);g.relative('e8',t['relation']);g.emit('84c0');g.mark(s['relation2Branch']);g.relative('74',s['flag2'],1)
    g.mark(s['returnRestore']);g.emit('488b6c24');g.unsigned(d['stackFrame']+8+d['saveRbpStack']);g.mark(s['returnSource']);g.emit('488bc3488b5c24');g.unsigned(d['stackFrame']+8+d['saveRbxStack']);g.emit('488b7424');g.unsigned(d['stackFrame']+8+d['saveRsiStack']);g.emit('4883c4');g.unsigned(d['stackFrame']);g.emit('5fc3')
    g.mark(s['flag1']);g.emit('f687');g.unsigned(d['specialClassFlagOffset'],4);g.unsigned(d['specialClassMask']);g.mark(s['flag1Branch']);g.relative('0f85',t['special1'])
    g.mark(s['returnZero']);g.emit('33db');g.relative('eb',s['returnRestore'],1)
    g.mark(s['flag2']);g.emit('f687');g.unsigned(d['specialClassFlagOffset'],4);g.unsigned(d['specialClassMask']);g.mark(s['flag2Branch']);g.relative('0f84',t['castFailure']);g.relative('e9',t['special2']);g.finish()
    r=_Program(windows['slotResolver']);r.emit('488bc14863ca488b0cc8');r.relative('e9',t['slotResolverClassInit']);r.finish()
    # Only the already-initialized case returns RCX directly. The other target
    # remains an opaque class-initialization request, not a proved type result.
    r=_Program(windows['initializedClass']);r.emit('f681');r.unsigned(d['initializedClassFlagOffset'],4);r.unsigned(d['initializedClassMask']);slow=r.at+2+5;ret=windows['initializedClass']['endRva']-1;r.relative('74',slow,1);r.emit('488bc1');r.relative('eb',ret,1);r.mark(slow);r.relative('e9',t['slowClassInit']);r.mark(ret);r.emit('c3');r.finish()
    r=_Program(windows['relationPrefix']);r.emit('48895c24');r.unsigned(d['relationSaveRbxStack']);r.emit('48895424');r.unsigned(d['relationSaveRdxStack']);r.emit('48894c24');r.unsigned(d['relationSaveRcxStack']);r.emit('55565741544155415641574883ec');r.unsigned(d['relationFrameBytes']);r.emit('4c8be24c8bf9');r.mark(s['relationEquality']);r.emit('483bca');r.mark(s['relationEqualityBranch']);r.relative('0f84',s['relationReturnTrue']);r.finish()
    r=_Program(windows['relationTrue']);r.mark(s['relationReturnTrue']);r.emit('b001488b5c24');r.unsigned(d['relationFrameBytes']+d['relationPushBytes']+d['relationSaveRbxStack']);r.emit('4883c4');r.unsigned(d['relationFrameBytes']);r.emit('415f415e415d415c5f5e5dc3');r.finish()
    r=_Program(windows['castFailure']);r.emit('488bd5488bcb');r.mark(s['castFailureCall']);r.relative('e8',t['castFailureHelper']);r.emit('cc');r.finish()
    _require(t['slotResolver']==windows['slotResolver']['startRva']and t['slotResolverClassInit']==windows['initializedClass']['startRva']
        and t['relation']==windows['relationPrefix']['startRva']and t['castFailure']==windows['castFailure']['startRva'],'getter-call-fragment-joins','actual targets are reviewed fragment entries',t)
    return dict(sourceSlotOffset=d['sourceOffset'],resolverCalls=[s['slotCall1'],s['slotCall2']],relationCalls=[s['relation1Call'],s['relation2Call']],specialClassFlag=dict(offset=d['specialClassFlagOffset'],mask=d['specialClassMask'],readFrom='source.class',readOnlyAfterReachedRelationFailure=True))


def _static_context(image,c,writer):
    _contexts(image,writer)  # Includes explicit RDX MethodInfo -> physical call join.
    _require(writer['physicalGetterRva']==next(w['startRva']for w in c['codeWindows']if w['role']=='getter'),'getter-writer-target','same physical getter',writer['physicalGetterRva'])
    actual=ContextSymbols(image).context(image.named_types[GENERIC].index,slots=[c['operands']['slotIndex']])
    _require(_strict(actual,c['staticContext']),'getter-static-context',c['staticContext'],actual)
    entries=actual['entries'];_require(len(entries)==1 and entries[0]['kind']==2,'getter-class-slot','class RGCTX definition',entries)
    parameter=entries[0]['type']['parameterOwner'];_require(parameter['typeName']==GENERIC and parameter['ordinal']==1,'getter-slot-parameter-owner','second type parameter of same StateMachine',parameter)
    _require(all(row['result']['classArguments'][parameter['ordinal']]==BLACKBOARD for row in writer['contexts']),'getter-static-substitution',BLACKBOARD,writer['contexts'])
    return dict(relativeSlot=c['operands']['slotIndex'],parameterOrdinal=parameter['ordinal'],substitutedType=BLACKBOARD,runtimeInitializedSlotProved=False)


def _validate(image,c,writer):
    image.check_windows(c['codeWindows'],label='skillBlackboardGetter');g=next(w for w in c['codeWindows']if w['role']=='getter');family=image.unwind_index.family(g['startRva'])
    _require(any(r['runtimeTriple'][0]<=g['startRva']<g['endRva']<=r['runtimeTriple'][1]for r in family['ranges']),'getter-primary-owner','selected physical entry range',g)
    for w in c['codeWindows']:
        raw=bytes.fromhex(w['hex']);_require(len(raw)==w['endRva']-w['startRva']and image.pe.bytes_at_va(image.pe.image_base+w['startRva'],len(raw))==raw,'getter-window-bytes',w['role'],w)
    context=_static_context(image,c,writer);facts=_programs(c);_require(_strict(c['rules'],_rules()),'getter-rules-boundary',_rules(),c['rules'])
    return dict(rules=_rules(),ordinaryFlow=facts,staticSubstitution=context,evidenceBoundary=c['evidenceBoundary'])


def load_skill_blackboard_getter(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema='endfield.skill-blackboard-getter-native-audit.v1',status='validation_failed',rules={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillBlackboardGetter');pins=c['nativeInputs'];_require(c['writerDependency']=='skill_input_blackboard_native.json','getter-dependency-name','selected writer declaration',c['writerDependency'])
        dependency=CONTRACTS_DIR/c['writerDependency'];writer,writer_digest=read_reviewed_contract(dependency,schema=WRITER_SCHEMA,status='reviewed',label='skillBlackboardGetter')
        _require(_strict(writer['nativeInputs'],pins),'getter-dependency-inputs','same native inputs',writer['nativeInputs'])
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        result=_validate(open_native_image(gate.gameassembly,gate.metadata),c,writer);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest and hashlib.sha256(dependency.read_bytes()).hexdigest().upper()==writer_digest,'getter-bookends','native and both declarations unchanged',after.status)
        audit.update(result,status='validated-conditional-getter',nativeInputs=pins)
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as e:audit.update(status='validation_failed',rules={},failures=[dict(check=str(e)[:1200],source=str(path))])
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('gameassembly','metadata','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=load_skill_blackboard_getter(gameassembly=a.gameassembly,metadata=a.metadata)
    from scripts.repo_paths import REPO_ROOT
    _require(any(a.output.resolve().is_relative_to(REPO_ROOT/x)for x in ('reports','scratch','tmp')),'getter-output-root','ignored',a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if r['status']=='validated-conditional-getter'else 1


if __name__=='__main__':raise SystemExit(main())
