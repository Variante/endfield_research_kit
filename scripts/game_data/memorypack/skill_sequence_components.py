"""Compose current Sequence wire and its independently proved reference lifecycle.

The capability describes finite stored action arrays. Concrete action routes,
runtime callback selection and enclosing parents remain independent. Pure
composition grants no native admission; derive owns both fresh source lanes.
"""
import json

LABEL='skillSequenceComponents'

def compose(lifecycle,sequence,inputs):
    """Join independently derived existing-wrapper wire and concrete lifecycle."""
    if (lifecycle.get('schema')!='endfield.sequence-reference-lifecycle-source.v1'
            or lifecycle.get('status')!='validated-conditional-reference-lifecycle'
            or lifecycle.get('nativeInputs')!=inputs
            or lifecycle.get('typeName')!='Beyond.Gameplay.Core.SequenceActionData'
            or lifecycle.get('wholeGrammarAdmitted')is not False
            or any(lifecycle.get(key)is not True for key in('ownConcreteGetterSemanticsProved',
                'ownConcreteFactorySemanticsProved','canonicalAdapterPrecreatesWrapperRequired',
                'existingWrapperSourceRequired','ordinaryOriginalReadValueSourceAdmitted'))
            or sequence.get('wrapperName')!=lifecycle['wrapperName']
            or sequence.get('wrappedType')!=lifecycle['typeName']
            or type(sequence.get('memberCount'))is not int or sequence['memberCount']!=3
            or sequence.get('readerMethod')!=lifecycle['adapter']['pairForwarder']['readerMethod']
            or sequence.get('wrapperNullAdmitted')is not True
            or sequence.get('positiveArraySourceAdmitted')is not True
            or sequence.get('elementGrammarAdmitted')is not False
            or sequence.get('wholeSkillDataAdmitted')is not False
            or sequence.get('collectionCounts')!=list(range(-1,18))
            or any(type(n)is not int for n in sequence['collectionCounts'])
            or type(lifecycle.get('referenceReaderMethodDefinition'))is not int
            or type(lifecycle.get('referenceReaderTargetRva'))is not int):
        raise ValueError(LABEL+'.source:unproved-sequence-reference-composition')
    return dict(typeName=lifecycle['typeName'],wrapperName=lifecycle['wrapperName'],
        nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        canonicalPrecreatedWrapperRequired=True,
        collectionCounts=sequence['collectionCounts'],
        **{key:lifecycle[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')})


def derive_on_wire(image,pins,lifecycle,wire,*,count_limit=10000):
    """Extend the exact fresh-array loop by byte-identical count induction."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_sequence_array_sources import source_program
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    if type(count_limit)is not int or not 17<=count_limit<=10000:
        raise ValueError(LABEL+'.source:invalid-count-induction-bound')
    _publication_gate(image,pins);cap=compose(lifecycle,wire,pins)
    body=owned(image,image.pe.image_base+wire['readerMethod'][3])
    witness3=source_program(body['regions'],body['pointer'],wire['readerOffsets'],wire['fieldOffsets'],count=3)
    witnesses=[dict(wire['programs'][str(n)],newList=True)for n in(0,1,2)]+[dict(witness3,newList=True)]
    certificate=prove_induction(witnesses,initial='33f6',increment='ffc6',comparison='3bf5',
        counter='esi',saved_count='ebp',max_count=count_limit)
    certificate['allocationKind']='fresh reference array; existing array output is not admitted'
    for proof in certificate['pathProofs']:
        proof['freshArray']=proof.pop('newList')
    cap.update(collectionCounts=[-1,0],positiveCountsAdmitted=True,countLimit=count_limit,
        freshArrayCountInductionProved=True)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-sequence-components.v1',nativeInputs=pins,
        status='validated-conditional-sequence-components',capabilities={'SequenceActionData':cap},
        proof=dict(wire=wire,lifecycle=lifecycle,countWitness3=witness3,countInduction=certificate),
        wholeSkillDataAdmitted=False)))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import skill_shared_sequence_sources,skill_sequence_array_sources,skill_sequence_reference_sources
    _publication_gate(image,pins)
    lists=skill_shared_sequence_sources.derive_selector_lists(image,pins)
    wire=skill_sequence_array_sources.derive(image,pins,lists['components']['target-validator-list'])
    lifecycle=skill_sequence_reference_sources.derive(image,pins)
    return derive_on_wire(image,pins,lifecycle,wire)
