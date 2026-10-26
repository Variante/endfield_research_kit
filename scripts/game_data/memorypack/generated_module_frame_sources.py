"""Finite generated caller RBP locals, separate from nominal value sources.

Only the declared Module and Char montage shapes select these stack addresses. Every
source, nominal parameter, copied byte slice, named destination and complete
entry/return frame is still independently proved by its owning checker. These
tables are source-program roles, never element widths or child wire grammars.
"""
from scripts.game_data.memorypack import buff_ec_profiles_native as ec

PROFILE='finite-module-rbp-value-locals.v1'
VECTOR='UnityEngine.Vector3'
LANG='Beyond.LangKey'
ENTITY='Beyond.Gameplay.Core.EntityPtr'
BODY='Beyond.Gameplay.BodyTypeDef'
ALPHA='Beyond.Gameplay.View.Animation.AlphaBlend'
_PLANS={
    'Beyond.Gameplay.GhostWallModuleData':(27,72,-8,24,{
        12:(VECTOR,12,48,32),13:(VECTOR,12,48,32),25:(VECTOR,12,48,32),26:(VECTOR,12,48,32)}),
    'Beyond.Gameplay.RaceData':(11,168,-95,111,{
        2:(VECTOR,12,48,32),3:(ENTITY,40,112,64),9:(VECTOR,12,48,32)}),
    'Beyond.Gameplay.TianshizhuangData':(14,168,-95,111,{
        2:(LANG,16,48,48),4:(LANG,16,48,48),5:(ENTITY,40,112,64),10:(VECTOR,12,48,32),11:(VECTOR,12,48,32)}),
    'Beyond.Gameplay.Core.CharInteractPerform.CharNpcMontageActionData':(25,168,-95,111,{
        0:(BODY,32,96,32),18:(ALPHA,56,32,96)}),
}


def need(check,condition,detail=None):
    if not condition:raise ValueError('generatedModuleFrame.'+check+':'+str(detail)[:700])


def owns(owner):return owner in _PLANS


def _shape(owner,alias_site,entry_site=None):
    need('finite-caller-owner',owner in _PLANS,owner)
    count,frame,origin,_,_=_PLANS[owner]
    result=dict(profile=PROFILE,ownerType=owner,memberCount=count,baseRegister='rbp',entryRspOffset=origin,
        currentRspBytes=frame,rspRelativeBaseOffset=frame+origin,baseAliasInstruction=alias_site)
    if entry_site is not None:result['entryRspAliasInstruction']=entry_site
    return result


def descriptor(owner,header):
    count,frame,origin,displacement,_=_PLANS[owner];address=header.get('headerAddress',{})
    need('exact-independent-header-frame',header.get('mode')=='helper'and header.get('nullFrameBytes')==frame
        and header.get('readerRegister')=='rdi'and header.get('outputRegister')=='rbx'
        and address.get('baseRegister')=='rbp'and address.get('displacement')==displacement
        and address.get('entryRspOffset')==origin+displacement
        and address.get('rspDisplacement')==header.get('headerLocalDisplacement')==frame+origin+displacement
        and address.get('baseAliasInstruction')in header.get('prologue',[]))
    site=address['baseAliasInstruction']
    if origin==-95:
        need('exact-entry-RAX-header-profile',address.get('baseAliasProfile')=='entry-RAX-RBP-95-header.v1'
            and address.get('entryRspAliasInstruction')in header['prologue'])
        return _shape(owner,site,address['entryRspAliasInstruction'])
    need('exact-saved-RBP-MOV-alias',site[1].upper()=='488BEC')
    return _shape(owner,site)


def require_descriptor(alias,header=None):
    need('literal-finite-descriptor',isinstance(alias,dict)and alias.get('profile')==PROFILE and owns(alias.get('ownerType')))
    expected=_shape(alias['ownerType'],alias.get('baseAliasInstruction'),alias.get('entryRspAliasInstruction'))
    need('complete-finite-descriptor',alias==expected)
    if header is not None:need('same-independent-header-descriptor',alias==descriptor(alias['ownerType'],header))
    return alias['rspRelativeBaseOffset']


def validate(alias,events,setters,rows,base):
    origin=require_descriptor(alias);owner=alias['ownerType'];count,_,entry_origin,_,plan=_PLANS[owner]
    need('same-finite-current-members',len(events)==len(setters)==count)
    by={ec.va(r):r for r in rows}
    for key,raw in [('baseAliasInstruction','488BEC'if entry_origin==-8 else'488D68A1')]+(
            [('entryRspAliasInstruction','488BC4')]if entry_origin==-95 else[]):
        site=alias[key];row=by.get(base+site[0]);need('same-complete-source-alias-bytes',row is not None and ec.site(row,base)==site and site[1].upper()==raw)
    for index,(name,width,_,_)in plan.items():
        event,setter=events[index],setters[index];raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
        need('independent-nominal-hidden-source-setter',event.get('memberIndex')==index and event.get('declaredType')==name
            and event.get('kind')==('value12:'+name if name==VECTOR else'managed:'+name)
            and event.get('resultAbi')=='hidden-local'and event.get('actualSourceProved')is True
            and setter.get('storedBytes')==width and len(raw)==16 and raw[10:12]==bytes((17,128)))
    return origin


def source_addresses(alias):
    origin=require_descriptor(alias);plan=_PLANS[alias['ownerType']][-1]
    return {('rcx',home-origin)for _,_,home,_ in plan.values()}|{('rdx',home-origin)for _,_,_,home in plan.values()}


def require_hidden(alias,index,name,width,start):
    require_descriptor(alias);plan=_PLANS[alias['ownerType']][-1]
    need('exact-nominal-hidden-home',index in plan and plan[index][:3]==(name,width,start),(index,name,width,start))
    return True


def copy_spec(alias,index,name,width,offset,register,displacement):
    origin=require_descriptor(alias);plan=_PLANS[alias['ownerType']][-1]
    need('own-current-copied-member',index in plan and plan[index][0]==name)
    _,_,hidden,argument=plan[index]
    slices=((8,0,'xmm0'),(4,8,'rax'))if name==VECTOR else((16,0,'xmm0'),)if name==LANG else(
        ((16,0,'xmm0'),(16,16,'xmm1'))if name==BODY else
        ((16,0,'xmm0'),(16,16,'xmm1'),(16,32,'xmm0'),(8,48,'xmm1'))if name==ALPHA else
        ((16,0,'xmm0'),(16,16,'xmm1'),(8,32,'xmm0')))
    need('exact-owned-local-source-slice',(width,offset,register)in slices and displacement==argument+offset-origin,
        (index,name,width,offset,register,displacement))
    opcode=('f20f1145'if register=='xmm0'else'f20f114d')if width==8 else'8945'if width==4 else'f30f7f45'if name==LANG else'0f2945'if register=='xmm0'else'0f294d'
    return dict(instructionHex=opcode+displacement.to_bytes(1,'little',signed=True).hex(),
        selfCopy=name==LANG and hidden==argument,sourceHome=hidden,argumentHome=argument)
