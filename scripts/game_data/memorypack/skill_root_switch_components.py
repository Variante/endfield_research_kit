"""SwitchToBuffConfig caller and exact conditional external child identities.

Own MC5/FF/new source, Original/wrapper factory, getter, canonical reference
adapter and ordinary Reader identity are independently selected. The actual
buff list request joins the complete BuffInput/AssignPair source. TargetSettings
and SequenceActionData remain external: their exact nominal Reader definition
and actual E8 must match separately admitted lifecycle/wire capabilities before
the enclosing composition can enable this program. This component never admits
either external child from a name or bare grammar flag. Matching coherent
runtime callbacks, normal allocation/helper/disabled collector effects and
disjoint buffered storage remain conditions. Root/EOF and runtime meaning stay
unresolved independently of the complete selected native return.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need,reference_record_abi
from scripts.game_data.memorypack.skill_root_attribute_components import reference_cap

TYPE='Beyond.Gameplay.Core.SwitchToBuffConfig'
CAPABILITY='skill-root-switch-to-buff-config'
BUFFS='skill-root-buff-input-list'
EXTERNALS={'Beyond.Gameplay.Core.TargetSettings':'target-profile','Beyond.Gameplay.Core.SequenceActionData':'SequenceActionData'}
ORDER=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
    ('asSkillCast','bool',None),('buffs','reference-list',BUFFS),('buffSource','target-profile','target-profile'),
    ('condition','sequence-profile','SequenceActionData'),('targets','target-profile','target-profile'))]


def external_identity(join,reference):
    typename=join['typeName'];need('Switch-finite-external-type',True,typename in EXTERNALS)
    need('Switch-literal-external-identity',True,all(type(reference.get(k))is int and reference[k]>0
        for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')))
    usage=join['typedRequest']
    need('Switch-actual-external-request',('MemoryPack.MemoryPackReader','ReadValue',[],[typename]),
        tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments')))
    need('Switch-actual-external-method',usage['methodSpec'][0],reference['referenceReaderMethodDefinition'])
    need('Switch-actual-external-target',join['sourceTargetRva'],reference['referenceReaderTargetRva'])
    return dict(typeName=typename,**{k:reference[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})


def derive(image,pins,*,buffs=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_additional_records import derive as record_source
    from scripts.game_data.memorypack.skill_root_buff_input_components import derive_list
    _publication_gate(image,pins);parent=record_source(image,pins,types=[TYPE])['records'][TYPE]
    reference=reference_record_abi(image,pins,parent)
    joins={j['fieldName']:j for j in parent['requiredChildJoins']}
    need('Switch-complete-named-child-order',['buffs','buffSource','condition','targets'],list(joins))
    join=joins['buffs']
    buffs=derive_list(image,pins,typed_request=join['typedRequest'],call_target=image.pe.image_base+join['sourceTargetRva'])if buffs is None else buffs
    need('Switch-same-buff-list-pins',pins,buffs['nativeInputs']);bc=buffs['capabilities'][BUFFS]
    need('Switch-nominal-buff-list',join['typeName'],bc['closedListType'])
    need('Switch-exact-buff-list-method-and-target',(join['typedRequest']['methodSpec'][0],join['sourceTargetRva']),
        (bc['packableReaderMethodDefinition'],bc['packableReaderTargetRva']))
    identities={};bindings=[]
    for field in('buffSource','condition','targets'):
        identity=external_identity(joins[field],reference);capability=EXTERNALS[identity['typeName']]
        if capability in identities:need('Switch-shared-external-identity',identities[capability],identity)
        identities[capability]=identity;bindings.append(dict(fieldName=field,capability=capability,**identity))
    caps=dict(buffs['capabilities']);caps[CAPABILITY]=reference_cap(parent,reference,ORDER)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-switch-components.v1',nativeInputs=pins,
        status='validated-conditional-external-components',capabilities=caps,
        requiredExternalCapabilities=['SequenceActionData','byte-payload','target-profile'],requiredExternalCapabilityIdentities=identities,
        proof=dict(parent=parent,parentReference=reference,buffs=buffs,externalBindings=bindings,
            externalChildGrammarAdmittedByThisComponent=False),
        evidenceBoundary=dict(exact='SwitchToBuffConfig own complete MC5/FF/new/factory/getter/reference adapter and actual typed BuffInput list plus exact nominal external TargetSettings/Sequence reader joins.',
            conditional=__doc__,structuralOnly='Stored switch configuration.',unresolved=['separately admitted external child source/lifecycle/wire capabilities','runtime meaning','root/EOF']))))
