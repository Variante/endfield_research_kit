"""BuffFindSettings MC3 with selected pooled string list and Query children.

The exact named parent list/Query MethodSpecs and actual source targets join
their independently proved list callback and Query16/array programs. Query's
actual warm provider owns the full successful backend/compatible-cast return;
the returned matching canonical callback is an explicit selection condition.
Original/wrapper construction, holder getter, canonical reference adapter and
ordinary ReadValue are separately authenticated. Matching nonnull exported
StringPool, initialized coherent typed contexts, normal helpers/allocations,
disabled collectors and disjoint buffered/frame storage remain conditions.
Stored buff-find configuration gives no runtime meaning or root/EOF admission.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need,reference_record_abi
from scripts.game_data.memorypack.skill_root_attribute_components import reference_cap

CAPABILITY='skill-root-buff-find-settings'
STRINGS='skill-root-pooled-string-list'
QUERY='skill-root-gameplay-tag-query'
ORDER=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
    ('buffIdList','pooled-string-list',STRINGS),('checkType','enum32',None),('tagQuery','record',QUERY))]


def bind_children(pins,parent,strings,query):
    for role,child in(('strings',strings),('query',query)):need('same-BuffFind-child-pins:'+role,pins,child['nativeInputs'])
    sc=strings['capabilities'][STRINGS];qc=query['capabilities'][QUERY]
    need('BuffFind-literal-child-reader-identities',True,all(type(c.get(k))is int and c[k]>0 for c,keys in(
        (sc,('packableReaderMethodDefinition','packableReaderTargetRva')),
        (qc,('valueReaderMethodDefinition','valueDispatcherTargetRva')))for k in keys))
    need('BuffFind-closed-string-list','System.Collections.Generic.List`1<string>',sc['closedListType'])
    need('BuffFind-list-formal-and-actual',(parent['contexts']['buffIdList']['methodSpec'][0],parent['symbolRvas']['list']),
        (sc['packableReaderMethodDefinition'],sc['packableReaderTargetRva']))
    need('BuffFind-nominal-Query','Beyond.Gameplay.Core.GameplayTagQuery',qc['typeName'])
    need('BuffFind-Query-formal-and-actual',(parent['contexts']['tagQuery']['methodSpec'][0],parent['symbolRvas']['dispatch']),
        (qc['valueReaderMethodDefinition'],qc['valueDispatcherTargetRva']))
    need('BuffFind-positive-Query',True,qc.get('wholeGrammarAdmitted')is True)
    return dict(strings=STRINGS,query=QUERY,actualListSourceTargetRva=sc['packableReaderTargetRva'],
        actualQueryDispatcherTargetRva=qc['valueDispatcherTargetRva'])


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer,pooled_global_buff_id_sources
    from scripts.game_data.memorypack.skill_root_buff_find_sources import derive as parent_source
    from scripts.game_data.memorypack.skill_pooled_string_list_sources import derive as string_source
    from scripts.game_data.memorypack.skill_root_tag_query_components import derive as query_source
    from scripts.game_data.memorypack.skill_root_value_dispatch import provider_inline_cast_program
    parent=parent_source(image,pins);base=image.pe.image_base
    strings=string_source(image,pins,typed_request=parent['contexts']['buffIdList'],call_target=base+parent['symbolRvas']['list'])
    query=query_source(image,pins,typed_request=parent['contexts']['tagQuery'],dispatcher_target=base+parent['symbolRvas']['dispatch'])
    bindings=bind_children(pins,parent,strings,query);reference=reference_record_abi(image,pins,parent)
    provider=pointer.owned(image,base+parent['symbolRvas']['provider'])
    def call(offset):
        row,=[r for r in provider['rows']if int(r['va'],16)==provider['pointer']+offset]
        raw=bytes.fromhex(row['bytes']);need('BuffFind-owned-provider-E8',(5,232),(len(raw),raw[0]))
        return control_transfer(row)['target']
    s={n:call(off)for n,off in dict(typeHandle=52,backend=79,indexed=96,assignable=116).items()}
    program=provider_inline_cast_program(provider['regions'],provider['pointer'],s)
    need('BuffFind-same-provider-static-class',parent['programs'][0]['providerClassCell'],program['providerClassCell'])
    need('BuffFind-named-TypeFromHandle',base+parent['registeredPair']['registration']['helperMethods']['typeFromHandle'][3],s['typeHandle'])
    transfer=query['proof']['transfer']
    need('BuffFind-same-type-class-as-canonical',program['typeClassCell'],transfer['paths']['adapter'][0]['typeClassCell'])
    need('BuffFind-same-provider-class-as-canonical',program['providerClassCell'],transfer['paths']['nonnull'][0]['providerClassCell'])
    need('BuffFind-same-owned-context-indexer',s['indexed']-base,transfer['symbolRvas']['indexed'])
    backend=pointer.owned(image,s['backend']);tails=[control_transfer(r)['target']for r in backend['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
    need('BuffFind-one-backend-tail',1,len(tails));bridge=pooled_global_buff_id_sources.backend_bridge(backend['regions'],backend['pointer'],tails[0])
    caps=dict(strings['capabilities'])
    for name,cap in query['capabilities'].items():
        if name in caps:need('BuffFind-shared-child-cap:'+name,caps[name],cap)
        caps[name]=cap
    caps[CAPABILITY]=reference_cap(parent,reference,ORDER)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-buff-find-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities=caps,requiredExternalCapabilities=['byte-payload'],
        proof=dict(parent=parent,parentReference=reference,strings=strings,query=query,bindings=bindings,
            providerProgram=program,providerWindows=provider['windows'],providerSymbolRvas={k:v-base for k,v in s.items()},
            backendProgram=bridge,backendWindows=backend['windows']),
        evidenceBoundary=dict(exact='BuffFindSettings own MC3/FF/new source and typed factories/getter/reference adapter, actual pooled-string-list request and Query16 callback/source/array joins, complete warm provider successful cast source.',
            conditional=__doc__,structuralOnly='Stored buff-find configuration.',unresolved=['runtime provider choice','enclosing root/physical EOF']))))
