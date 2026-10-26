"""Compose the finite positive Polyline grammar, including recursive Node.

Recursion uses a type-grammar induction: FF terminates, each positive Node
consumes its header/raw16 bounds before recursive children, and every edge
uses the independently proved same nominal reference adapter. No cyclic JSON
capability or width-derived element grammar is used.
"""
import json
from scripts.game_data.memorypack import leveldata_polyline_graph_sources as source

CAP='story-polyline-shape'
WIRE='polyline-graph-record'
LIST_WIRE='polyline-graph-list'


def need(check,condition,detail=None):source.need(check,condition,detail)
def key(name):return 'story-polyline-graph:'+name
def norm(value):return json.loads(json.dumps(value))


def bind_reference(pins,join,child,capability):
    from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
    cap=child.get('capabilities',{}).get(capability,{})
    need('finite-own-recursive-edge',join['typeName']in(source.TREE,source.NODE)
        and capability==key(join['typeName'])and cap.get('recursiveTypeGrammarAssumption')is True)
    joined=bind_read_value(pins,join,child,capability)
    return dict(joined,canonicalAdapterTargetRva=cap['canonicalAdapterTargetRva'],
        canonicalAdapterMethodDefinition=cap['canonicalAdapterMethodDefinition'],
        actualCallbackEqualsProvedChildRequired=True)


def bind_collection(pins,join,child,capability):
    cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
    need('exact-own-positive-list',child.get('nativeInputs')==pins and capability==key(join['typeName'])
        and cap.get('typeName')==join['typeName']and cap.get('wholeGrammarAdmitted')is True
        and cap.get('countLimit')==source.LIMIT and cap.get('actualCallbackEqualsProvedChildRequired')is True
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[join['typeName']])
        and cap.get('sourceMethodSpec')==usage.get('methodSpec')
        and cap.get('packableReaderMethodDefinition')==usage['methodSpec'][0]
        and cap.get('packableReaderTargetRva')==join['sourceTargetRva'])
    result=dict(fieldName=join['fieldName'],typeName=join['typeName'],capability=capability,
        readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
        countLimit=source.LIMIT,positiveCountsAdmitted=True,actualCallbackEqualsProvedChildRequired=True)
    if cap.get('elementCapability')is not None:
        result.update(elementCallbackTargetRva=cap['elementCallbackTargetRva'],
            elementCallbackMethodDefinition=cap['elementCallbackMethodDefinition'])
    return result


def compose(native,pins,requests):
    """Pure composition of sources derived inside one selected-image call."""
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.reference_list_value_sources import verify_source
    need('whole-finite-source-obligations',native.get('nativeInputs')==pins
        and set(native.get('records',{}))==set(source.PLANS)
        and set(native.get('collections',{}))=={source.LIST(t)for t in('int',source.VECTOR,source.NODE,source.LIST(source.VECTOR))}
        and native.get('wireGrammarAdmitted')is False)
    _,base=verify_source(native['collections'][source.LIST(source.NODE)]['source'],pins)
    caps={};listcaps={};programs={}
    for name,row in native['records'].items():
        full=row['source'];ref=row['referenceSource'];adapter=row['adapter'];pair=row['pair']
        need('exact-own-full-record-and-adapter',full.get('nativeInputs')==adapter.get('nativeInputs')==pins
            and full.get('wrappedType')==adapter.get('typeName')==name
            and full.get('completeSelectedCallerAdmitted')is True and full.get('childGrammarAdmitted')is False
            and full.get('wholeOwnerAdmitted')is False
            and[(r['fieldName'],r['declaredType'])for r in full['orderedSourceReads']]==list(source.PLANS[name])
            and adapter.get('pair')==pair
            and adapter.get('getterMethod')==full['lifecycle']['GetValue']['method']
            and full['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True
            and pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex']==full['lifecycle']['concreteFormatter']['method'][0],name)
        need('own-reference-source-FF-and-ordinary-identity',ref.get('typeName')==name and ref.get('nativeInputs')==pins
            and ref.get('wrapperName')==full.get('wrapperName')and norm(ref.get('pair'))==norm(pair)
            and ref.get('canonicalRegistration',{}).get('pointer')==base+ref.get('callbackBinding',{}).get('canonicalTargetRva')
            and ref['canonicalRegistration'].get('methodDefinitionIndices')==[
                adapter['canonicalRoutes']['canonicalEntries']['Deserialize']['definition']]
            and ref['callbackBinding']['canonicalTargetRva']==adapter['callbackBinding']['canonicalTargetRva']
            and ref['callbackBinding'].get('actualCallbackEqualsCanonicalRequired')is True
            and ref.get('nullAdmitted')is True and ref.get('positiveAdmitted')is False
            and ref.get('nullMarker')==255 and ref.get('consumedBytes')==1
            and type(ref.get('referenceReaderMethodDefinition'))is int and type(ref.get('referenceReaderTargetRva'))is int,name)
        caps[key(name)]=dict(typeName=name,memberCount=len(source.PLANS[name]),wholeGrammarAdmitted=True,
            ordinaryOriginalReadValueAdmitted=True,recursiveTypeGrammarAssumption=True,
            referenceReaderMethodDefinition=ref['referenceReaderMethodDefinition'],referenceReaderTargetRva=ref['referenceReaderTargetRva'],
            originalTypeDefinition=ref['typeDefinition'],
            canonicalAdapterTargetRva=adapter['callbackBinding']['canonicalTargetRva'],
            canonicalAdapterMethodDefinition=adapter['canonicalRoutes']['canonicalEntries']['Deserialize']['definition'],
            formatterDeserializeMethodDefinition=pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'],
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
    for name,row in native['collections'].items():
        own=row['source'];element=name[len('System.Collections.Generic.List`1<'):-1];usage=row['typedRequest']
        callback_fields={}
        if element=='int':
            c=own['capability'];need('own-full-int32-list',own.get('nativeInputs')==pins and c.get('typeName')==name
                and c.get('elementWireBytes')==4 and c.get('countLimit')==source.LIMIT and c.get('wholeGrammarAdmitted')is True)
        elif element==source.VECTOR:
            c=own['capability'];need('own-full-Vector2-list',own.get('nativeInputs')==pins and c.get('closedListType')==name
                and c.get('managedElementBytes')==c.get('elementWireBytes')==8 and c.get('countLimit')==source.LIMIT
                and c.get('wholeGrammarAdmitted')is True and own.get('loopInduction')is not None)
            registration=own['registrations']['list'];context=own['context']
            need('own-Vector2-list-canonical-slot5-and-complete-source',registration==context['registration']
                and registration.get('methodDefinitionIndices')==[own['methodAbis']['list']['methodDefinition']]
                and own['methodAbis']['list'].get('instance')is True and own['methodAbis']['list'].get('parameters')==2
                and all(p['selectedBytes'][0][0]==registration['pointer']for p in own['listPrograms']))
            callback_fields=dict(canonicalFormatterTargetRva=registration['pointer']-base,
                canonicalFormatterMethodDefinition=own['methodAbis']['list']['methodDefinition'],
                closedCarrier=context['closedCarrier'])
        else:
            witness,actual_base=verify_source(own,pins)
            need('same-selected-list-native-base',actual_base==base)
            need('own-positive-reference-list-nominal',witness['elementType']==element
                and witness['closedCarrier']['name']==name and witness['typedRequest']==usage
                and witness['callTargetRva']==row['sourceTargetRva'])
            carrier,=witness['closedCarrier']['classArguments']
            if element==source.NODE:
                raw=bytes.fromhex(carrier['rawHex'])
                need('own-Node-callback-nominal',carrier['name']==source.NODE and raw[10:12]==bytes((18,0))
                    and int.from_bytes(raw[:8],'little')==caps[key(source.NODE)]['originalTypeDefinition'])
                callback_fields=dict(elementCallbackTargetRva=caps[key(source.NODE)]['canonicalAdapterTargetRva'],
                    elementCallbackMethodDefinition=caps[key(source.NODE)]['canonicalAdapterMethodDefinition'],elementCarrier=carrier)
            else:
                vector=native['collections'][source.LIST(source.VECTOR)]['source']
                need('own-nested-Vector2-list-callback',element==source.LIST(source.VECTOR)
                    and carrier['name']==element and bytes.fromhex(carrier['rawHex'])[10:12]==bytes((21,0))
                    and vector['context']['closedListType']==element
                    and vector['registrations']['list']==vector['context']['registration']
                    and carrier==vector['context']['closedCarrier']
                    and vector['registrations']['list']['methodDefinitionIndices']==[vector['methodAbis']['list']['methodDefinition']]
                    and all(p['selectedBytes'][0][0]==vector['registrations']['list']['pointer']for p in vector['listPrograms']))
                callback_fields=dict(elementCallbackTargetRva=vector['registrations']['list']['pointer']-base,
                    elementCallbackMethodDefinition=vector['methodAbis']['list']['methodDefinition'],elementCarrier=carrier)
        listcaps[key(name)]=dict(typeName=name,elementType=element,countLimit=source.LIMIT,countRange=[-1,source.LIMIT],
            nullable=True,positiveCountsAdmitted=True,wholeGrammarAdmitted=True,
            elementWireBytes=4 if element=='int'else 8 if element==source.VECTOR else None,
            elementCapability=key(element)if element in(source.NODE,source.LIST(source.VECTOR))else None,
            sourceMethodSpec=usage['methodSpec'],packableReaderMethodDefinition=usage['methodSpec'][0],
            packableReaderTargetRva=row['sourceTargetRva'],actualCallbackEqualsProvedChildRequired=True,
            liveFormatterSelectionObserved=False,**callback_fields)
    for name,row in native['records'].items():
        full=row['source'];references={};ref_children={};collections={};list_children={}
        for read in full['orderedSourceReads']:
            typ=read['declaredType'];index=read['memberIndex']
            if typ in(source.NODE,source.TREE):
                references[typ]=(key(typ),WIRE,key(typ));ref_children[typ]=dict(nativeInputs=pins,capabilities={key(typ):caps[key(typ)]})
            elif typ.startswith('System.Collections.Generic.List`1<'):
                collections[typ]=(key(typ),LIST_WIRE,key(typ));list_children[index]=dict(nativeInputs=pins,capabilities={key(typ):listcaps[key(typ)]})
        program,pending=compile_member_program(full,pins,wrapper_name=full['wrapperName'],type_name=name,value4={},
            references=references,reference_children=ref_children,reference_binder=bind_reference,
            collections=collections,collection_children=list_children,collection_binder=bind_collection,
            typed_requests=requests[name])
        need('whole-own-record-compiled',not pending,dict(typeName=name,pending=pending))
        need('same-positive-recursion-progress',name!=source.NODE or program['reads'][0]['kind']=='story-aabb-raw16')
        programs[name]=program
    cap=dict(schema=source.SCHEMA,typeName=source.TYPE,memberCount=12,program=programs[source.TYPE],programs=programs,
        records=caps,collections=listcaps,nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,
        wholeGrammarAdmitted=True,finiteFloatProfile=True,actualCallbackEqualsProvedChildRequired=True,
        positiveBvhNodesAdmitted=True,positiveConvexPolygonsAdmitted=True,positiveTreeAdmitted=True,
        recursiveTypeGrammarDischarged=True,
        recursiveTypeGrammar=dict(types=[source.NODE],nullMarker=255,positiveHeaderBytes=1,
            positiveNodeBoundsWireBytes=16,depthLimit=64,nodeBudget=16384),
        referenceReaderMethodDefinition=caps[key(source.TYPE)]['referenceReaderMethodDefinition'],
        referenceReaderTargetRva=caps[key(source.TYPE)]['referenceReaderTargetRva'],liveFormatterSelectionObserved=False)
    return norm(dict(schema=source.SCHEMA,nativeInputs=pins,capability=cap,proof=dict(sources=native,typedRequests=requests),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    native=source.derive_sources(image,pins);requests={}
    for name,row in native['records'].items():
        requests[name]={r['memberIndex']:derive_typed_usage_context(image,r['context']['instructionRva'],label='polylinePositiveGraph.actual-edge')
            for r in row['source']['orderedSourceReads']if r.get('context')is not None and r['kind'].startswith('reference:')}
    result=compose(native,pins,requests);_publication_gate(image,pins);return result
