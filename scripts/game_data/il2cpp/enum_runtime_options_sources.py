"""Exact options-pointer publication used by the enum normalization branch.

The selected startup slice stores the address of actual static option bytes
into the same global cell freshly loaded by the normalizer. The normalizer's
first-byte branch is independently byte-proved; its selected static first byte
is reported as data, without treating a pointer cell as a Boolean value.

The bounded slice does not prove startup execution, publication dominance,
exclusive writes, live option-pointer contents or later alias preservation.
It therefore supplies a conditional initialized-options relation, never an
observed runtime configuration or a concrete enum formatter/wire admission.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-runtime-options-sources.v1'
LABEL='enumRuntimeOptionsSources'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def publication_program(regions,entry,*,configuration_cell):
    need('explicit-selected-cell',type(configuration_cell)is int and configuration_cell>0)
    g=BytesPath(regions,entry);source=g.relative('488d05');target=g.relative('488905')
    need('same-normalizer-options-pointer-cell',target==configuration_cell)
    return dict(selectedBytes=g.seen,start=entry,end=g.at,staticOptionsAddress=source,
        configurationPointerCell=target,staticOptionsAddressStoredUnchanged=True,
        optionsByteLoadOffset=0,completeStartupControlProved=False,publicationExecutionObserved=False)


def derive(image,pins,*,normalizer_entry,publication_entry):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_normalizer_selection_paths import normalizer_program
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.levelscript_two_routes_native import _window
    _publication_gate(image,pins);body=owned(image,normalizer_entry)
    normal=normalizer_program(body['regions'],normalizer_entry,image_base=image.pe.image_base)
    raw=image.pe.bytes_at_va(publication_entry,14)
    source=publication_program([(publication_entry,raw)],publication_entry,configuration_cell=normal['configurationCell'])
    data=image.pe.bytes_at_va(source['staticOptionsAddress'],1);need('raw-backed-first-option-byte',len(data)==1)
    window=_window(image,publication_entry,source['end'],'Exact static option-address publication slice; enclosing startup control and execution unproved')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(normalizerWindows=body['windows'],normalizer=normal,publication=source,publicationWindow=window,
            selectedStaticFirstByte=data[0]),selectedStaticByteTakesNonzeroNormalizationBranch=data[0]!=0,
        initializedPointerToStaticOptionsConditional=True,runtimeOptionsPointerOrValueObserved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Bounded source-owned static-address publication to the actual normalizer pointer cell, selected raw-backed first option byte and independent complete selected count1 normalizer path.',
            conditional=__doc__,structuralOnly='Native options pointer and option-byte representation.',
            unresolved=['complete startup/execution/exclusive publication and alias preservation',
                'actual class/interner/provider/MethodInfo callback selection','wire/parent/EOF']))))
