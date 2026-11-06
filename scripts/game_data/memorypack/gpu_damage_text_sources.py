"""Current DamageText graph: generated readers, concrete adapters and lists."""
import json
from scripts.game_data.memorypack import generated_reader_sources as readers
from scripts.game_data.memorypack.reference_param_profile import derive_pair
from scripts.game_data.memorypack.reference_object_sources import derive_adapter
from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
from scripts.game_data.memorypack.reference_list_induction_sources import derive as list_source
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context

PREFIX='Beyond.UI.GPUI.'
NAMES=('PrefabGroupSerializeData','PrefabSerializeData','AnimationSerializeData','NodeMetadata','NodeSerializeData')


def need(name,value):
    if not value:raise ValueError('gpuDamageText.'+name)


def encoding(name,ctx):
    if name=='string':return 'string'
    if name=='bool':return 'bool'
    if name=='float':return 'f'
    if name=='int'or ctx.is_enum(name):return 'i'
    if name=='uint':return 'I'
    if name=='Beyond.Resource.StringPathHash':return 'q'
    if name=='UnityEngine.Vector2':return '2f'
    if name=='UnityEngine.Vector4':return '4f'
    if name.startswith('System.Collections.Generic.List`1<'):
        child=name[len('System.Collections.Generic.List`1<'):-1]
        need('finite-list-child',child=='string'or child in {PREFIX+n for n in NAMES})
        return 'list:'+('string'if child=='string'else child[len(PREFIX):])
    raise ValueError('gpuDamageText.unsupported-field:'+name)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_string
    _publication_gate(image,pins);ctx=NativeReferenceContext(image)
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()}
    result=readers.derive_many(image,pins,[wrappers[PREFIX+n].name for n in NAMES])
    need('all-five-complete-readers',len(result['owners'])==5 and all(
        o.get('status')=='complete-reader-source-proved'for o in result['owners']))
    records={};sources={};abi=reference_reader_abi(image,pins);base=image.pe.image_base
    for item in result['owners']:
        p=item['proof'];name=p['wrappedType'];w=wrappers[name]
        pair=adapter=None
        if name!=PREFIX+NAMES[0]:
            pair=derive_pair(image,name,w.name);adapter=derive_adapter(image,pins,pair,w)
            need('same-concrete-getter',p['lifecycle']['GetValue']['method']==adapter['getterMethod'])
            need('same-concrete-reader',p['method']==adapter['pairForwarder']['readerMethod'])
        sources[name]=dict(source=p,pair=pair,adapter=adapter,referenceABI=abi,lists={})
        fields=[dict(name=r['fieldName'],encoding=encoding(r['declaredType'],ctx),typeName=r['declaredType'])
                for r in p['orderedSourceReads']]
        records[name[len(PREFIX):]]=dict(typeName=name,memberCount=len(fields),fields=fields)
    for name,own in sources.items():
        for read in own['source']['orderedSourceReads']:
            declared=read['declaredType']
            if not declared.startswith('System.Collections.Generic.List`1<'):continue
            element=declared[len('System.Collections.Generic.List`1<'):-1]
            request=derive_typed_usage_context(image,read['context']['instructionRva'],label='gpuDamageText.list')
            collection=list_source(image,pins,typed_request=request,call_target=base+read['sourceTargetRva'],
                element_type=element,count_limit=10000)
            witness=collection['witnessComponent']
            if element=='string':
                child=derive_string(image,pins)
            else:
                child=sources[element]['adapter']
                need('list-same-reference-reader',witness['referenceSource']['valueContext']['readerMethodDefinition']==
                    abi['referenceReaderMethodDefinition'])
            own['lists'][read['fieldName']]=dict(collection=collection,child=child,
                elementGrammarAdmitted=True,liveFormatterSelectionProved=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(records=records,sources=sources)))


def declaration(graph):
    """Reviewed structure and native anchors, without duplicating run ledgers."""
    windows={}
    def visit(value):
        if isinstance(value,dict):
            if {'startRva','endRva','sha256'}<=set(value):
                key=(value['startRva'],value['endRva']);old=windows.setdefault(key,value['sha256'])
                need('one-window-digest',old==value['sha256'])
            for item in value.values():visit(item)
        elif isinstance(value,list):
            for item in value:visit(item)
    visit(graph)
    return dict(records=graph['records'],readers={name:dict(method=own['source']['method'],
        orderedSourceReads=own['source']['orderedSourceReads'],
        lists={field:dict(elementType=entry['collection']['elementType'],countRange=entry['collection']['countRange'],
            freshListsAdmitted=entry['collection']['freshListsAdmitted'],
            reusedListsRequireInitialCount=entry['collection']['reusedListsRequireInitialCount'])
            for field,entry in own['lists'].items()})for name,own in graph['sources'].items()},
        codeWindows=[dict(startRva=a,endRva=b,sha256=h)for(a,b),h in sorted(windows.items())])
