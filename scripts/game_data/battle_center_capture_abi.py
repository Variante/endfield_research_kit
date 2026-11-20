"""Narrow shared-reference ABI witness for the two Center blackboard reads.

Only the reviewed getter, canonical reference instantiation and two _ToSkill
call sites are admitted. This is not general permission to pair generic hooks.
No return pointee or runtime generic-context chain is read by the observer.
"""
from __future__ import annotations
import hashlib
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data import skill_blackboard_getter_native as getter
from scripts.game_data import skill_input_blackboard_native as writer

HOOK='battle.Center.GetBlackboard'
CALLER='battle.Center.ToSkill'
OWNER='Beyond.Gameplay.StateMachine`2'
CANONICAL={'classArguments':['System.Int32Enum','object'],'methodArguments':[]}


def _need(condition,message):
    if not condition:raise ValueError('battle_center.getter: '+message)


def selected_sources(selected):
    cached=getattr(selected,'_battle_center_getter_sources',None)
    if cached is not None:return cached
    c,c_digest=read_reviewed_contract(getter.CONTRACT_PATH,schema=getter.SCHEMA,status='reviewed',label='battleCenterGetter')
    w,w_digest=read_reviewed_contract(writer.CONTRACT_PATH,schema=writer.SCHEMA,status='reviewed',label='battleCenterGetter')
    image=selected.image
    _need(c['nativeInputs']==w['nativeInputs'],'writer/getter native inputs differ')
    for name,raw in [('GameAssembly.dll',image.pe.buf),('global-metadata.dat',image.metadata.buf)]:
        _need(hashlib.sha256(raw).hexdigest().upper()==c['nativeInputs'][name].upper(),'selected native input differs: '+name)
    writer._validate(image,w)
    getter._validate(image,c,w)
    _need(hashlib.sha256(getter.CONTRACT_PATH.read_bytes()).hexdigest().upper()==c_digest and
          hashlib.sha256(writer.CONTRACT_PATH.read_bytes()).hexdigest().upper()==w_digest,
          'source declarations changed during validation')
    selected._battle_center_getter_sources=(c,w)
    return c,w


def validate_spec(hook):
    _need(hook.get('name')==HOOK and hook.get('type')==OWNER and hook.get('method')=='get_stateBlackboard'
          and hook.get('static') is False and hook.get('parameters')==[] and hook.get('fields')==[]
          and hook.get('genericEntry')==CANONICAL and hook.get('observationMode')=='paired'
          and hook.get('captureScope')=='paired-ancestor' and hook.get('captureCallerHooks')==[CALLER]
          and hook.get('anonymousEntry') is None and hook.get('captureIndirectCaller') is None,
          'exact paired canonical getter, empty reads and sole scoped _ToSkill caller required')


def prove_center_getter_signature(selected,hook,method):
    validate_spec(hook)
    c,w=selected_sources(selected);image=selected.image
    _need(all(row['result']['methodSpec'][0]==method.index for row in w['contexts']),
          'selected method is not the provided closed getter definition')
    pointer=image.pe.u64_at_va(int(image.registration['types'],16)+method.return_type*8)
    raw=image.pe.bytes_at_va(pointer,16)
    symbol=ContextSymbols(image).type(pointer);owner=symbol.get('parameterOwner',{})
    _need(raw[10]==0x13 and raw[11]&0x7f==0 and owner.get('typeName')==OWNER
          and owner.get('ordinal')==1 and method.parameter_count==0 and not method.flags&16,
          'ordinary second class parameter reference return required')
    _need(hook['returnType']==symbol['name'],'return declaration differs from selected metadata')
    return dict(mode='selectedSharedGenericReference',returnType=symbol['name'],closedReturnType='object',
        nativeTypeRecordHex=raw.hex(),nativeTypeIndex=method.return_type,byref=False,
        sharedNativeEntryRva=hex(w['physicalGetterRva']),contractSchema=getter.SCHEMA,
        evidence='Second class VAR instantiated as canonical object; authenticated getter and exact caller sites; raw RCX/RDX and RAX only. Runtime receiver/context identity remains observed data, not a static inference.')


def validate_center_getter_entry(selected,hook,proof):
    validate_spec(hook)
    _,w=selected_sources(selected)
    _need(proof['pointer']-selected.image.pe.image_base==w['physicalGetterRva'],
          'canonical generic method pointer differs from reviewed physical getter')


def center_getter_caller_returns(selected):
    _,w=selected_sources(selected)
    return [w['sites']['getter1Return'],w['sites']['getter2Return']]


def validate_retained_return(hook, profile):
    """Check retained declarations, not current runtime objects or code execution."""
    c,_=read_reviewed_contract(getter.CONTRACT_PATH,schema=getter.SCHEMA,status='reviewed',label='battleCenterGetter')
    w,_=read_reviewed_contract(writer.CONTRACT_PATH,schema=writer.SCHEMA,status='reviewed',label='battleCenterGetter')
    _need(c['nativeInputs']==w['nativeInputs'],'retained writer/getter native inputs differ')
    for role,name in [('gameAssembly','GameAssembly.dll'),('metadata','global-metadata.dat')]:
        _need((profile.get('files',{}).get(role)or{}).get('sha256','').upper()==c['nativeInputs'][name].upper(),
              'retained native input differs: '+role)
    p=hook.get('returnAbiProof')or{}
    source=c['staticContext']['entries'][0]['type']
    raw=bytes.fromhex(p.get('nativeTypeRecordHex',''))
    _need(profile.get('recipeSchema')=='endfield.mission-trace-capture-recipe.v17'
          and hook.get('name')==HOOK and hook.get('symbol')==OWNER+'.get_stateBlackboard'
          and hook.get('abiId')=='win64.scoped_paired_gp_pointer_2.v1'
          and hook.get('returnType')==hook.get('pairedAbiProof',{}).get('returnType')==p.get('returnType')==source['name']
          and p.get('mode')=='selectedSharedGenericReference' and p.get('closedReturnType')=='object'
          and p.get('contractSchema')==getter.SCHEMA and p.get('byref')is False
          and p.get('returnObserved')is True and p.get('pointeeRead')is False
          and p.get('sharedNativeEntryRva')==hook.get('rva')==hex(w['physicalGetterRva'])
          and raw==bytes.fromhex(source['rawHex'])
          and hook.get('parameters')==[] and hook.get('fields')==[]
          and hook.get('captureScope')=='paired-ancestor'
          and hook.get('captureCallerReturnRvas')==','.join(f'{w["sites"][key]:x}' for key in ('getter1Return','getter2Return')),
          'retained exact scoped shared-reference ABI differs')
    return True
