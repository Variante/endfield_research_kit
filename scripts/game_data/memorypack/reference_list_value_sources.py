"""Generic reference-list framing; nominal element wire grammars are separate."""
import json

SCHEMA='endfield.reference-list-value-source.v1'


def need(check,condition):
    if not condition:raise ValueError('referenceListValueSources.'+check)


def norm(value):return json.loads(json.dumps(value))


def list_type(element):return 'System.Collections.Generic.List`1<'+element+'>'


def verify_source(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack import reference_list_induction_sources as induction,pooled_string_list_sources as lists
    from scripts.game_data.memorypack import skill_cost_data_list_sources as common,lang_key_list_sources as lang
    need('own-selected-list-source',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins
        and isinstance(actual.get('elementType'),str)and actual.get('closedListType')==list_type(actual['elementType'])
        and type(actual.get('countLimit'))is int and 3<=actual['countLimit']<=4096
        and actual.get('elementGrammarAdmitted')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False)
    p=actual['proof'];native=p['source'];w=native['witnessComponent'];base=p['imageBase']
    need('same-complete-native-framing',type(base)is int and base>=1<<32
        and native.get('status')=='validated-bounded-reference-list-induction'and native.get('nativeInputs')==pins
        and native.get('elementType')==actual['elementType']and w.get('nativeInputs')==pins
        and w.get('elementType')==actual['elementType']and w.get('elementRuntimeBytes')==8 and w.get('headerBytes')==4)
    rebuilt=induction._certificate(w,count_limit=actual['countLimit'])
    need('exact-complete-count-induction',all(native.get(k)==norm(v)for k,v in rebuilt.items()))
    raw=regions(w['windows'],p['sourceRegions'],base,'reference-list-value');offsets=p['readerOffsets']
    symbols={k:base+v for k,v in w['symbols'].items()}
    paths=[lists.list_source(raw,w['entry']['pointer'],offsets,symbols,count=n,new=new,grow=False,count_limit=3)
        for n in range(-1,4)for new in(True,False)]
    need('all-fresh-and-reused-empty-byte-paths',norm(paths)==w['programs'])
    for role,windows,target,expected,canonical in(
        ('clear',w['clearWindows'],symbols['clear'],w['clearProgram'],False),
        ('canonicalClear',w['canonicalClearWindows'],w['clearEntry']['pointer'],w['canonicalClearProgram'],True)):
        own=regions(windows,p[role+'Regions'],base,'reference-list-value-'+role)
        need('own-complete-'+role,norm(common.reference_clear_zero(own,target,canonical=canonical))==expected)
    provider=regions(w['providerWindows'],p['providerRegions'],base,'reference-list-value-provider')
    need('own-complete-provider',norm(lang.wrapper_provider_program(provider,symbols['provider'],{k:base+v for k,v in w['providerSymbols'].items()}))==w['providerProgram'])
    need('own-actual-closed-reference-request',w['closedCarrier'].get('name')==actual['closedListType']
        and tuple(w['typedRequest'].get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[actual['closedListType']]))
    return w,base


def derive_source(image,pins,*,typed_request,call_target,element_type,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import reference_list_induction_sources as induction,scalar_param_native as scalar
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins)
    need('literal-closed-element-and-bound',isinstance(element_type,str)and bool(element_type)
        and type(count_limit)is int and 3<=count_limit<=4096)
    base=image.pe.image_base;native=induction.derive(image,pins,typed_request=typed_request,call_target=call_target,
        element_type=element_type,count_limit=count_limit)
    w=native['witnessComponent'];ctx=NativeReferenceContext(image);offsets=scalar.reader_offsets(image,'referenceListValueSources')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    def capture(target):return [[a-base,raw.hex()]for a,raw in owned(image,target)['regions']]
    result=norm(dict(schema=SCHEMA,nativeInputs=pins,elementType=element_type,closedListType=list_type(element_type),countLimit=count_limit,
        proof=dict(source=native,imageBase=base,readerOffsets=offsets,sourceRegions=capture(w['entry']['pointer']),
            clearRegions=capture(base+w['symbols']['clear']),canonicalClearRegions=capture(w['clearEntry']['pointer']),
            providerRegions=capture(base+w['symbols']['provider'])),
        elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False))
    verify_source(result,pins);_publication_gate(image,pins);return result
