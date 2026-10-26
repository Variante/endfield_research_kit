"""Inventory authenticated IFix rule ownership separately from patch occurrences.

The parent passes its selected Code layout and successfully validated group
audits. An opcode occurring zero times in retained patches is not a reason to
remove it from this inventory. A recipe owner is a scoped conditional proof,
not a claim that every runtime path or callee outcome has been observed.
StackSpace's entry header is kept distinct from its ordinary default route.
"""
from __future__ import annotations

from typing import Any


class RuleInventoryError(ValueError):
    """An inventory declaration disagrees with its authenticated Code layout."""


def _need(ok: bool, detail: str) -> None:
    if not ok: raise RuleInventoryError('ifix-rule-inventory.'+detail)


def _rule_rows(spec: dict[str,Any]) -> list[dict]:
    value=spec.get('rules',[])
    if isinstance(value,list):return value
    _need(isinstance(value,dict),'rules must be a list or mapping')
    # Helper programs may use named text recipes under the same key. They
    # require a validated group audit but own no Code member themselves.
    if all(isinstance(row,str) for row in value.values()):return []
    _need(all(isinstance(row,dict) for row in value.values()),'rules mapping must contain Code declarations or text recipes')
    return [dict(row,opcode=name)for name,row in value.items()]


def build_rule_inventory(contract: dict,layout: dict,audit: dict) -> dict:
    """Run only after the parent authenticates native inputs and all group audits."""
    members=layout['opcodeEnum']['members'];ids={r['name']:r['id']for r in members}
    _need(len(ids)==len(members) and all(type(v) is int for v in ids.values()) and len(set(ids.values()))==len(ids),'Code members must have unique names and integer IDs')
    dispatch=contract['dispatchRules'];defaults=dispatch['defaultOpcodes'];_need(len(defaults)==len(set(defaults)) and set(defaults)<=set(ids),'ordinary default set differs from Code')
    _need(str(audit.get('dispatchRules',{}).get('status','')).startswith('validated'),'validated ordinary dispatcher audit required')
    owners={n:[]for n in ids};operand_owners={n:set()for n in ids}
    for group,spec in contract.items():
        if not isinstance(spec,dict) or 'rules'not in spec:continue
        rows=_rule_rows(spec);proof=audit.get(group,{})
        _need(str(proof.get('status','')).startswith('validated'),group+': validated group audit required')
        for row in rows:
            name=row.get('opcode');_need(name in ids and type(row.get('opcodeId')) is int and row['opcodeId']==ids[name],group+': rule Code identity differs: '+str(name))
            owners[name].append(dict(group=group,selection=row.get('selectedWhen',row.get('selector','group-scoped-conditional-recipe')),evidenceBoundary=spec.get('evidenceBoundary','conditional')))
    # Some complete helper/caller groups report their sole opcode directly.
    for group,proof in audit.items():
        if not isinstance(proof,dict) or 'opcode'not in proof:continue
        name=proof['opcode']
        if name in ids and str(proof.get('status','')).startswith('validated') and not any(r['group']==group for r in owners[name]):
            owners[name].append(dict(group=group,selection='group-scoped-conditional-recipe',evidenceBoundary=proof.get('evidenceBoundary','conditional')))
    for group,proof in audit.items():
        if not isinstance(proof,dict) or 'recipeOpcodeIds'not in proof:continue
        _need(group in contract and str(proof.get('status','')).startswith('validated'),group+': validated recipe audit required')
        declared=proof['recipeOpcodeIds'];_need(isinstance(declared,dict),group+': recipe Code mapping required')
        for name,opcode_id in declared.items():
            _need(name in ids and type(opcode_id)is int and opcode_id==ids[name],group+': recipe Code identity differs')
            if not any(r['group']==group for r in owners[name]):
                owners[name].append(dict(group=group,selection=proof.get('recipeSelections',{}).get(name,'group-scoped-conditional-recipe'),evidenceBoundary=proof.get('evidenceBoundary','conditional')))
    for group,spec in contract.items():
        if not isinstance(spec,dict) or 'producerEvidenceRef'not in spec:continue
        name=spec['producerEvidenceRef'].rsplit('.',1)[-1]
        if name not in ids:
            target=contract
            for part in spec['producerEvidenceRef'].split('.'):
                _need(isinstance(target,dict) and part in target,group+': producer evidence reference missing')
                target=target[part]
            _need(isinstance(target,dict),group+': producer evidence mapping required')
            name=target.get('addressProducer')
            _need(name in ids,group+': producer Code name missing')
        _need(type(spec.get('opcodeIds',{}).get(name)) is int and spec['opcodeIds'][name]==ids[name],group+': producer Code identity differs')
        _need(str(audit.get(group,{}).get('status','')).startswith('validated'),group+': validated producer audit required')
        if not any(r['group']==group for r in owners[name]):owners[name].append(dict(group=group,selection='authenticated-producer-and-helper-link',evidenceBoundary=spec.get('evidenceBoundary','conditional')))
    for group in ('callClaims','branchClaims','tableOperandClaims','frameSlotClaims'):
        for row in contract.get(group,[]):
            name=row['opcode'];_need(name in ids,group+': undeclared Code name');operand_owners[name].add(group)
    for group in ('initobjTypeOperand','constrainedTypeOperand','returnClaim'):
        row=contract.get(group,{})
        if row.get('opcode')in ids:operand_owners[row['opcode']].add(group)
    rows=[]
    for name,opcode_id in sorted(ids.items(),key=lambda p:p[1]):
        rule_owners=sorted(owners[name],key=lambda r:r['group']);default=name in defaults
        rows.append(dict(opcode=name,opcodeId=opcode_id,ordinaryDefault=default,conditionalRuleOwners=rule_owners,
                         operandOwners=sorted(operand_owners[name]),ordinaryRecipeStatus='default-request'if default else 'conditional-rule'if rule_owners else 'pending-rule-review',runtimeExecution='unobserved'))
    pending=[r['opcode']for r in rows if r['ordinaryRecipeStatus']=='pending-rule-review']
    return dict(schema='endfield.ifix-vm-rule-inventory.v1',evidenceBoundary='conditional',executionBoundary='unobserved',
        inventoryBoundary='validated-Code-and-scoped-native-rule-declarations;recipe-ownership-does-not-establish-complete-runtime-semantics',
        occurrenceBoundary='all-Code-members-independent-of-retained-patch-occurrences',
        entryHeaderBoundary='StackSpace-entry-header-is-separate-from-ordinary-default-selection',
        opcodeCount=len(rows),ordinaryDefaultOpcodeCount=len(defaults),conditionalRuleOpcodeCount=sum(r['ordinaryRecipeStatus']=='conditional-rule'for r in rows),
        pendingOrdinaryRecipeOpcodes=pending,operandOnlyOpcodes=[n for n in pending if operand_owners[n]],rules=rows)
