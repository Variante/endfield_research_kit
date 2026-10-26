"""Fresh complete CharInteract root transfer, independent of child wire.

The reviewed dedicated root program proves its existing matching wrapper and
Original, factory/default ABI, every typed child call and whole named store.
It is not a generic generated-record source and is never relabeled as one.
"""
import json

TYPE='Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformRuntimeCfg'
SCHEMA='endfield.char-interact-current-root-source.v1'


def need(check,condition):
    if not condition:raise ValueError('charCurrentRootSource.'+check)


def norm(value):return json.loads(json.dumps(value))


def verify(source,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.char_perform_root_sources import root_existing
    need('own-selected-root-source',source.get('schema')==SCHEMA and source.get('nativeInputs')==pins
        and source.get('typeName')==TYPE and source.get('completeExistingRootSourceAdmitted')is True
        and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    p=source['proof'];fact=p['declaration'];profile=fact['profile'];actual=p['source'];rows=source['requests'];base=p['imageBase']
    need('own-current-reviewed-root',fact.get('schema')=='endfield.char-interact-perform-sparse-native.v4'
        and fact.get('status')=='conditional-current-build-wire'and fact.get('nativeInputs')==pins
        and profile.get('original')==TYPE and source.get('wrapperName')==profile.get('wrapper'))
    need('all-and-only-current-ordered-fields',len(rows)==28 and actual.get('fields')==profile['fieldPlan']
        and[(r.get('memberIndex'),r.get('fieldName'),r.get('typeName'))for r in rows]==
            [(i,f['name'],f['type'])for i,f in enumerate(profile['fieldPlan'])])
    call,=[c for c in profile['calls']if c['model']=='root'];program,=[r for r in profile['programs']if r['role']=='rootReader']
    raw=regions(program['windows'],p['sourceRegions'],base,'char-root28')
    expected=root_existing(raw,base+program['entryRva'],profile['fieldPlan'],offsets=call['kwargs']['offsets'],source_targets={})
    root,=[r['proof']for r in actual['proofs']if r['model']=='root']
    need('whole-own-root-program-and-frame',norm(expected)==root and root.get('entryRspRestored')is True
        and root.get('memberCount')==28)
    selected_bytes={a+i:b for a,h in root['selectedBytes']for i,b in enumerate(bytes.fromhex(h))}
    for field,row in zip(root['fields'],rows,strict=True):
        need('same-own-field-call-and-store',row.get('actualFieldTransfer')==field and row.get('mode')==field['mode']
            and row.get('fieldOffset')==field['fieldOffset']and row.get('sourceTargetRva')==field['sourceTarget']-base)
        at,encoded=row['instruction'];encoded=bytes.fromhex(encoded)
        need('same-actual-owned-root-E8',at==field['sourceCall']-base and len(encoded)==5 and encoded[0]==232
            and at+5+int.from_bytes(encoded[1:],'little',signed=True)==row['sourceTargetRva']
            and bytes(selected_bytes.get(base+at+i,0)for i in range(5))==encoded)
        usage=row.get('typedRequest');cells=field['contextCells']
        if cells:
            need('one-actual-root-context',len(cells)==1 and isinstance(usage,dict)
                and usage.get('instructionRva')==cells[0]['instruction']-base)
            expected=('Beyond.SerializeFieldDictionary`2','DeserializeV2',row['typeName'].split('<',1)[1][:-1].split(',',1),[])if row['mode']=='out8'else(
                'MemoryPack.MemoryPackReader','ReadPackable'if row['typeName'].startswith('System.Collections.Generic.List`1<')else
                    'ReadUnmanaged'if row['mode']=='enum'else'ReadValue',[],[row['typeName']])
            need('exact-nominal-root-context',tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments'))==expected)
        else:need('only-untyped-primitive-root-call',usage is None and row['mode']in('bool','float'))
        if row['mode']=='out8':
            need('own-static-initial-null-out-local',row.get('initiallyNullOutputProved')is True
                and field.get('temporarySlot')in(103,127))
    return base


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data import char_interact_perform_sparse_native as sparse
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    _publication_gate(image,pins);before=sparse.CONTRACT_PATH.read_bytes();fact=json.loads(before)
    need('same-selected-native-inputs',fact.get('nativeInputs')==pins)
    actual=sparse.derive(image,fact);profile=fact['profile'];base=image.pe.image_base
    root,=[r['proof']for r in actual['proofs']if r['model']=='root'];requests=[]
    for index,(field,transfer)in enumerate(zip(profile['fieldPlan'],root['fields'],strict=True)):
        cells=transfer['contextCells'];need('zero-or-one-actual-parent-context',len(cells)<=1)
        usage=derive_typed_usage_context(image,cells[0]['instruction']-base,label='charCurrentRoot.actual')if cells else None
        at=transfer['sourceCall'];raw=image.pe.bytes_at_va(at,5)
        requests.append(dict(memberIndex=index,fieldName=field['name'],typeName=field['type'],mode=field['mode'],
            fieldOffset=field['offset'],typedRequest=usage,sourceTargetRva=transfer['sourceTarget']-base,
            instruction=[at-base,raw.hex()],actualFieldTransfer=transfer,
            initiallyNullOutputProved=field['mode']=='out8'))
    program,=[r for r in profile['programs']if r['role']=='rootReader']
    result=norm(dict(schema=SCHEMA,nativeInputs=pins,typeName=TYPE,wrapperName=profile['wrapper'],requests=requests,
        completeExistingRootSourceAdmitted=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(declaration=fact,source=actual,imageBase=base,sourceRegions=[[w['startRva'],image.window_bytes(w).hex()]for w in program['windows']]),
        evidenceBoundary=__doc__))
    verify(result,pins);need('reviewed-root-contract-bookend',sparse.CONTRACT_PATH.read_bytes()==before)
    _publication_gate(image,pins);return result
