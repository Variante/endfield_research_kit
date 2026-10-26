"""Rebind retained complete source extents to current named native methods.

This owns method/metadata identity and the complete current source-family
windows. Retained selected-program proofs keep their original conditions;
this operation does not reprove their semantics, child grammar or consumer
scope, and never activates a reviewed catalog.
"""
import json


def need(key, condition, detail=None):
    if not condition:
        raise ValueError('catalogSourceAttribution.' + key + ':' + str(detail)[:1000])


def derive(image, pins, *, retained_sources):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_owned_code_sources import source_family
    _publication_gate(image, pins)
    need('bounded-distinct-retained-sources', isinstance(retained_sources, list)
         and 0 < len(retained_sources) <= 1024
         and len({s.get('wrapperName') for s in retained_sources}) == len(retained_sources))
    wrappers = {w.name: w for w in image.memorypack_wrappers.values()}
    md = image.metadata
    base = image.pe.image_base
    rows = []
    for retained in retained_sources:
        name = retained.get('wrapperName')
        method = retained.get('method', [])
        need('same-selected-source-inputs', retained.get('nativeInputs') == pins
             and retained.get('completeSourceProofRetained') is True, name)
        need('literal-retained-named-reader', isinstance(name, str) and name in wrappers
             and len(method) == 4 and method[1:3] == [name, 'Deserialize']
             and type(method[0]) is int and 0 <= method[0] < len(md.methods)
             and type(method[3]) is int and method[3] > 0, name)
        wrapper = wrappers[name]
        definition = md.methods[method[0]]
        need('fresh-actual-reader-definition-and-entry', wrapper.wrapped_type == retained.get('wrappedType')
             and definition.index == method[0] and image.type_name(definition.declaring_type) == name
             and md.string(definition.name_index) == 'Deserialize' and definition.flags & 0x10
             and image.method_pointer_va(definition) == base+method[3], name)
        declared = [(m.name, m.declared_type) for m in wrapper.members]
        stored = retained.get('orderedMembers')
        need('fresh-ordered-member-identities', isinstance(stored, list)
             and stored == [dict(memberIndex=i, fieldName=n, declaredType=t) for i,(n,t) in enumerate(declared)], name)
        family, windows, instructions, partition = source_family(image, pins, entry_rva=method[3])
        expected_windows = retained.get('codeWindows')
        need('same-complete-current-source-family', family == retained.get('family')
             and windows == expected_windows and bool(windows), name)
        image.check_windows(windows, label='catalogSourceAttribution.'+name)
        rows.append(dict(wrapperName=name, wrappedType=wrapper.wrapped_type, method=method,
            codeWindows=windows, sourceFamily=family, ownedCodePartition=partition,
            orderedMembers=stored, nativeMethodAndExtentAttributionProved=True,
            retainedSourceReport=retained.get('retainedSourceReport'),
            retainedSourceProofSha256=retained.get('retainedSourceProofSha256'),
            retainedSourceConditions=retained.get('conditions'),
            sourceProgramSemanticsReproved=False, childGrammarAdmitted=False,
            currentConsumerAdmitted=False, catalogAdmitted=False))
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema='endfield.current-catalog-source-attribution.v1',
        status='validated-current-named-source-attribution', nativeInputs=pins, sources=rows,
        sourceCount=len(rows), retainedProgramProofsReused=True, catalogsActivated=0,
        historicalAttributionHoldsCleared=0, evidenceBoundary=__doc__)))
