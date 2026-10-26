"""Caller-independent EntityPtr list source and exact Module request binder.

Managed40, its opaque runtime tail and the copied selected barrier stay
separate from the independently proved MC3/FF wire value. This owner derives
no Param parent and cannot grant an enclosing Module or runtime selection.
"""
import json
from scripts.game_data.memorypack import entity_list_sources as source

TYPE=source.LIST
ELEMENT=source.TYPE
CAP='story-module-entity-ptr-list'
WIRE='story-module-entity-ptr-list'
SCHEMA='endfield.story-module-entity-ptr-list-components.v2'
LIMIT=4096


def need(check,condition):
    if not condition:raise ValueError('moduleEntityList.'+check)
def norm(value):return json.loads(json.dumps(value))


def _packet(packet,base,label):
    """Every decoded row must exactly cover its authenticated owned byte span."""
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    raw=regions(packet['windows'],packet['regions'],base,label);rows=packet['rows'];by={}
    need(label+'-explicit-entry',type(packet.get('entryRva'))is int
        and any(at<=base+packet['entryRva']<at+len(data)for at,data in raw))
    for row in rows:
        at=int(row['va'],16);data=bytes.fromhex(row['bytes'])
        need(label+'-unique-nonempty-decoded-row',at not in by and bool(data));by[at]=data
    for at,data in raw:
        seen=b'';cursor=at
        while cursor<at+len(data):
            need(label+'-complete-decoded-window',cursor in by);part=by.pop(cursor)
            seen+=part;cursor+=len(part)
        need(label+'-row-bytes-equal-native-window',seen==data)
    need(label+'-no-extra-decoded-rows',not by)
    return raw,rows,base+packet['entryRva']


class _RecordedImage:
    """Narrow byte reader for existing scalar grammars, never a native opener."""
    def __init__(self,base,records):
        import types
        self.base=base;self.data={}
        for record in records:
            for at,h in record['instructions']:
                for i,b in enumerate(bytes.fromhex(h)):
                    need('scalar-overlap-bytes',base+at+i not in self.data or self.data[base+at+i]==b)
                    self.data[base+at+i]=b
        self.pe=types.SimpleNamespace(image_base=base,bytes_at_va=self.read)
    def read(self,at,size):
        try:return bytes(self.data[at+i]for i in range(size))
        except KeyError as error:raise ValueError('moduleEntityList.scalar-unowned-byte')from error
    def check_windows(self,windows,*,label):
        import hashlib
        for w in windows:
            need(label+'-complete-scalar-hash',hashlib.sha256(self.read(self.base+w['startRva'],w['endRva']-w['startRva'])).hexdigest().upper()==w['sha256'])
    def check_instruction_windows(self,rows,*,label):
        for at,h in rows:need(label+'-recorded-instruction',self.read(self.base+at,len(bytes.fromhex(h)))==bytes.fromhex(h))


def _verify_child(child,pins,base,dispatch_target):
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
    from scripts.game_data.memorypack import entity_ptr_leaf,entity_ptr_adapter,entity_ptr_conversion
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param
    need('own-replayable-independent-value-schema',child.get('schema')=='endfield.entity-ptr-independent-value-source.v2'
        and child.get('nativeInputs')==pins and child.get('parentDerived')is False and'outer'not in child
        and child.get('parentFieldAdmitted')is False and child.get('wholeOwnerAdmitted')is False)
    replay=child['replay'];packets=replay['sources'];roles={'leaf','adapter','dispatch','peek','readNull','conversion','slot','forwarder',
        'getter','set_logicId','set_slotId','set_useSlotId','registration0','registrationThunk0'}
    need('complete-finite-own-child-source-set',set(packets)==roles)
    data={role:_packet(p,base,'EntityPtr-'+role)for role,p in packets.items()}
    leaf=child['leaf'];offsets=replay['readerOffsets'];rows=data['leaf'][1];entry=data['leaf'][2]
    need('whole-leaf-window-identity',leaf.get('nativeInputs')==pins and leaf['sourceWindows']==packets['leaf']['windows'])
    calls=[control_transfer(r)['target']for r in rows if control_transfer(r)['kind']=='call']
    symbols=dict(zip(('uint64','uint32','boolean','barrier'),calls[:4]))
    symbols['allocation']=next(control_transfer(r)['target']for i,r in enumerate(rows[:-1])
        if control_transfer(r)['kind']=='call'and rows[i+1]['text']=='test rax, rax')
    need('whole-MC3-leaf-byte-programs',norm([entity_ptr_leaf.path(rows,entry,offsets,symbols,allocated=a)for a in(False,True)])==leaf['sourcePaths'])
    scalar_records=list(leaf['sources'].values());recorded=_RecordedImage(base,scalar_records)
    for name,width in(('uint64',8),('uint32',4)):
        record=leaf['sources'][name]
        need('same-own-leaf-scalar-target-'+name,base+record['pointerRva']==symbols[name])
        scalar.integer_source(recorded,record,offsets,'EntityPtr-'+name,width=width)
    need('same-own-leaf-bool-target',base+leaf['sources']['boolean']['pointerRva']==symbols['boolean'])
    scalar.boolean_source(recorded,leaf['sources']['boolean'],offsets,'EntityPtr-bool')
    get=data['getter'][1]
    need('own-hidden40-getter-full-byte-copy',[bytes.fromhex(r['bytes']).hex()for r in get]==
        ['0f104210','488bc1','0f104a20','0f1101','f20f104230','0f114910','f20f114120','c3']and get==leaf['getter'])
    for setter,(name,width,slot,opcode)in zip(leaf['setters'],(('logicId',8,24,'488951'),('slotId',4,32,'8951'),('useSlotId',1,16,'8851'))):
        r=data['set_'+name][1]
        need('own-complete-named-leaf-setter-'+name,setter['member']==name and setter['storedOffset']==slot and setter['storedBytes']==width
            and r==setter['program']and [bytes.fromhex(x['bytes']).hex()for x in r]==[opcode+bytes((slot,)).hex(),'c3'])
    need('exact-three-named-wire-setters',len(leaf['setters'])==3)
    own=child['adapter'];s=own['symbols']
    need('own-canonical-and-actual-dispatch-entry',s['adapter']==data['adapter'][2]
        and dispatch_target==data['dispatch'][2]and s['notNull']==data['conversion'][2]
        and s['peek']==data['peek'][2]and s['readNull']==data['readNull'][2])
    adapter_paths=[entity_ptr_adapter.adapter(data[role][1],data[role][2],s,dispatch=kind,null=null,skip_factory=skip)
        for role,kind in(('adapter',False),('dispatch',True))for null,skip in((True,False),(False,False),(False,True))]
    need('own-canonical-and-slot-match-default40-and-positive-replay',norm(adapter_paths)==own['paths'])
    peek=own['peekSource'];consume=own['nullConsumeSource'];ri=_RecordedImage(base,[peek,consume])
    for role,record in(('peek',peek),('readNull',consume)):
        primary=packets[role]['windows'][0]
        need('same-own-'+role+'-primary-span',record['window']==primary
            and record['instructions']==[[int(r['va'],16)-base,bytes.fromhex(r['bytes']).hex().upper()]for r in data[role][1]
                if base+primary['startRva']<=int(r['va'],16)<base+primary['endRva']])
    remaining,current=offsets['bufferLength'],offsets['currentPtr']
    scalar.program_extent(peek['instructions'],peek['window'],'EntityPtr-peek')
    scalar.program(ri,peek['instructions'],[b'\x40\x53',b'\x48\x83\xec\x20',b'\x83\x79'+bytes((remaining,1)),b'\x48\x8b\xd9',None,
        b'\x48\x8b\x43'+bytes((current,)),b'\x80\x38\xff',b'\x0f\x94\xc0',b'\x48\x83\xc4\x20',b'\x5b',b'\xc3'],'EntityPtr-peek')
    guard_at,h=peek['instructions'][4];guard=bytes.fromhex(h);target=guard_at+6+int.from_bytes(guard[2:],'little',signed=True)
    need('peek-full-zero-consumption-and-cold-guard',len(guard)==6 and guard[:2]==b'\x0f\x8c'
        and not peek['window']['startRva']<=target<peek['window']['endRva'])
    primitive_param.object_header_source(ri,consume,offsets)
    conversion=child['conversion'];need('same-owned-conversion-source',conversion['windows']==packets['conversion']['windows']
        and conversion['instructions']==data['conversion'][1]
        and norm(entity_ptr_conversion.check(data['conversion'][1],conversion['symbols']))==conversion['proof'])
    need('exact-own-slot-and-forwarder-callback',norm(deserialize_slot(data['slot'][0],data['slot'][2],
        prepare=conversion['symbols']['classPrepare'],callback=data['forwarder'][2]))==child['slotTransfer'])
    fr=data['forwarder'][1];fc=[control_transfer(r)['target']for r in fr if control_transfer(r)['kind']=='call']
    need('own-generated-wrapper-forwarder',len(child['forwarders'])==1 and child['forwarders'][0]['originalType']==ELEMENT
        and norm(prove_zero_wrapper_forwarder(fr,dict(zip(('metadataInit','classInit'),fc[:2])),entry,label='entityParam.forward'))==child['forwarders'][0]['proof'])
    flow,=child['registrations'];composition,=child['compositions'];interface,=composition['interfaces'];registration,=composition['registrations']
    need('exact-own-value-registration-and-concrete-formatter-interface',flow['originalType']==registration['originalType']==interface['originalType']==ELEMENT
        and flow['wrapperType']==registration['wrapperType']==interface['wrapperType']==leaf['wrapperName']
        and composition['methods'][0][0]==interface['getValueMethodIndex']and base+composition['methods'][0][3]==data['getter'][2]
        and composition['methods'][1][0]==interface['formatterDeserializeMethodIndex']and base+composition['methods'][1][3]==data['forwarder'][2]
        and any(r['pointer']==s['adapter']and len(r['classInstantiation']['arguments'])==2
            and bytes.fromhex(r['classInstantiation']['arguments'][0]['raw_type_record_hex'])==bytes.fromhex(flow['key']['typeRawHex'])
            and bytes.fromhex(r['classInstantiation']['arguments'][1]['raw_type_record_hex'])[10:12]==bytes((28,0))
            for r in child['adapterRegistration']))
    need('same-own-selected-registration-windows',packets['registration0']['windows']==[flow['window']]
        and packets['registrationThunk0']['windows']==[flow['constructorThunk']['window']])
    _verify_registration(flow,data['registration0'],data['registrationThunk0'],base,registration)


def _verify_registration(flow,packet,thunk_packet,base,composition):
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_registration import _stack_slot
    _,rows,entry=packet;_,thunk_rows,thunk_entry=thunk_packet
    need('own-selected-eager-value-registration-span',flow['window']['startRva']==entry-base and len(rows)==18)
    for i,key,prefix in((0,'allocation','488b0d'),(5,'constructor','488b15'),(8,'key','488b05')):
        usage=flow[key];raw=bytes.fromhex(rows[i]['bytes']);at=int(rows[i]['va'],16)-base
        need('own-registration-typed-'+key,at==usage['instructionRva']and raw.hex().upper()==usage['instructionHex']
            and len(raw)==7 and raw[:3]==bytes.fromhex(prefix)
            and at+7+int.from_bytes(raw[3:],'little',signed=True)==usage['usageCellRva'])
    constructor=flow['constructor'];key=flow['key'];allocation=flow['allocation']
    need('own-value-nominal-registration-carriers',constructor['tag']==6 and constructor['typeName']=='Beyond.MemoryPack.GenericMemoryPackFormatter`2'
        and constructor['methodName']=='.ctor'and constructor['classArguments']==[ELEMENT,flow['wrapperType']]and constructor['methodArguments']==[]
        and constructor['methodSpec']==composition['constructorMethodSpec']and key['tag']==2 and key['typeName']==ELEMENT
        and bytes.fromhex(key['typeRawHex'])[10:12]==bytes((17,128))and key['typeIndex']==composition['keyTypeIndex']
        and allocation['tag']==1 and allocation['typeIndex']==composition['adapterTypeIndex']
        and allocation['typeName']=='Beyond.MemoryPack.GenericMemoryPackFormatter`2<'+ELEMENT+','+flow['wrapperType']+'>')
    obj,obj_at=_stack_slot(rows[2],'EntityPtr-registration');original,original_at=_stack_slot(rows[9],'EntityPtr-registration');resolved,resolved_at=_stack_slot(rows[13],'EntityPtr-registration')
    need('registration-disjoint-carriers',len({obj_at,original_at,resolved_at})==3)
    for at,expected in {3:f'mov rcx, {obj}',6:f'mov rcx, {obj}',10:'xor edx, edx',11:f'mov rcx, {original}',14:'xor r8d, r8d',15:f'mov rdx, {resolved}',16:f'mov rcx, {obj}'}.items():
        need('registration-object-key-flow',rows[at]['text']==expected)
    for at,name in((1,'allocation'),(4,'objectCheck'),(7,'constructor'),(12,'typeFromHandle'),(17,'registerWrap')):
        need('registration-actual-'+name,control_transfer(rows[at])==dict(kind='call',target=base+flow['actualCalls'][name]))
    thunk=flow['constructorThunk']
    need('complete-own-closed-constructor-thunk',len(thunk_rows)==2 and thunk_entry==base+flow['actualCalls']['constructor']
        and all(thunk['context'][k]==constructor[k]for k in('tag','methodSpecIndex','methodSpec','typeName','methodName','classArguments','methodArguments'))
        and thunk_entry-base==thunk['context']['instructionRva']
        and bytes.fromhex(thunk_rows[0]['bytes']).hex().upper()==thunk['context']['instructionHex']
        and control_transfer(thunk_rows[1])==dict(kind='jump',target=base+thunk['sharedTargetRva']))


def _verify_helpers(native,pins,base,symbols):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack import float_list_sources,numeric_list_sources,null_list_param,modelview_packable_sources
    from scripts.game_data.il2cpp.string_source_programs import prove_collection_header
    parent=native['parent'];empty=parent['emptyList'];helper=empty['helperProofs'];replay=native['replay']
    need('exact-selected-collection-helper-set',set(replay['sources'])=={'clear','registeredClear','header','frontend'})
    data={role:_packet(p,base,'EntityList-'+role)for role,p in replay['sources'].items()}
    need('same-own-null-empty-and-positive-helper-identities',all(base+v==symbols[k]for k,v in empty['helperRvas'].items()))
    own_list=regions(native['sourceWindows']['list'],native['sourceRegions']['list'],base,'EntityList-empty')
    need('both-complete-empty-paths-replayed',norm([null_list_param.empty_entity_program(own_list,native['actualContext']['registration']['pointer'],symbols,new=n)for n in(False,True)])==empty['programs'])
    constructor=regions(native['sourceWindows']['constructor'],native['sourceRegions']['constructor'],base,'EntityList-constructor')
    need('both-own-capacity-constructor-programs',norm([float_list_sources.capacity_program(constructor,symbols['constructor'],symbols,positive=p)for p in(False,True)])==native['constructorPrograms']
        and helper['constructorWindows']==native['sourceWindows']['constructor'])
    need('own-empty-constructor-program',norm(null_list_param.empty_list_constructor(constructor,symbols['constructor'],context=symbols['context'],barrier=symbols['barrier']))==helper['constructorProgram'])
    clear=data['clear'];need('same-actual-Clear-source',clear[2]==symbols['clear']and replay['sources']['clear']['windows']==helper['clearWindows'])
    clear_programs=[null_list_param.empty_list_clear(clear[0],clear[2],array_clear=base+helper['arrayClearCallRva'],nonempty=n)for n in(False,True)]
    registered=data['registeredClear'];need('own-registered-closed-Clear-entry',registered[2]==helper['registeredClearEntry']['pointer']
        and b''.join(b for _,b in registered[0]).hex().upper()==helper['registeredClearProgramBytes'])
    registered_programs=[null_list_param.registered_list_clear(registered[0],registered[2],array_clear=base+helper['arrayClearCallRva'],nonempty=n)for n in(False,True)]
    need('both-selected-and-registered-Clear-effects',norm(clear_programs)==helper['clearPrograms']and norm(registered_programs)==helper['registeredClearPrograms']
        and helper['clearSelectedEffectsEquivalent']is True
        and all({k:a[k]for k in('previousSizePositive','sizeOffset','versionOffset','itemsOffset','returnedSize')}==
            {k:b[k]for k in('previousSizePositive','sizeOffset','versionOffset','itemsOffset','returnedSize')}for a,b in zip(clear_programs,registered_programs)))
    provider=regions(native['sourceWindows']['provider'],native['sourceRegions']['provider'],base,'EntityList-provider')
    ps={k:base+v for k,v in replay['providerSymbolRvas'].items()}
    need('actual-provider-full-selected-path',norm(float_list_sources.provider_program(provider,symbols['provider'],ps))==native['providerProgram'])
    backend=regions(native['sourceWindows']['backend'],native['sourceRegions']['backend'],base,'EntityList-backend')
    need('actual-provider-backend-forwarder',norm(numeric_list_sources.uint_backend_forward_program(backend,ps['backend'],base+replay['backendTargetRva']))==native['backendForward'])
    context=native['providerContext'];slots={r['relativeSlot']:r for r in context['entries']}
    need('own-provider-MVAR-key-and-result',set(slots)=={0,1}and slots[0]['kind']==1 and slots[1]['kind']==2
        and native['providerEntry']['methodDefinitionIndices']==[context['definition']]
        and slots[1]['type']['definition']['name']=='MemoryPack.MemoryPackFormatter`1'
        and slots[1]['type']['classArguments']==[slots[0]['type']]
        and slots[0]['type']['parameterOwner']['methodIndex']==context['definition']
        and type(slots[0]['type']['parameterOwner']['ordinal'])is int and slots[0]['type']['parameterOwner']['ordinal']==0
        and bytes.fromhex(slots[0]['type']['rawHex'])[10:12]==bytes((30,0)))
    expected_cells=[(native['providerProgram']['providerClassCell'],'System.Type'),
        (native['providerProgram']['rootClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
        (native['backendForward']['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')]
    need('exact-three-provider-owned-class-cells',len(native['classUsages'])==3)
    allbytes={at+i:b for at,raw in provider+backend for i,b in enumerate(raw)}
    for usage,(cell,name)in zip(native['classUsages'],expected_cells):
        raw=bytes.fromhex(usage['instructionHex']);at=base+usage['instructionRva']
        need('same-actual-provider-class-usage',type(usage['tag'])is int and usage['tag']==1 and usage['typeName']==name
            and len(raw)==7 and raw[:3]==bytes.fromhex('488b0d')and bytes(allbytes[at+i]for i in range(7))==raw
            and at+7+int.from_bytes(raw[3:],'little',signed=True)==cell==base+usage['usageCellRva'])
    header=data['header'];need('own-current-collection-header-entry',header[2]==symbols['header'])
    windows=replay['sources']['header']['windows'];primary=[];cold=[]
    for window in windows:
        group=[r for r in header[1]if base+window['startRva']<=int(r['va'],16)<base+window['endRva']]
        if not primary or int(group[0]['va'],16)==int(primary[-1]['va'],16)+len(bytes.fromhex(primary[-1]['bytes'])):primary+=group
        else:cold+=group
    hs={k:base+v for k,v in replay['headerSymbolRvas'].items()};fields=replay['headerReaderOffsets']
    need('same-own-header-and-child-reader-layout',all(fields[k]==native['child']['replay']['readerOffsets'][k]for k in native['child']['replay']['readerOffsets'])
        and norm(prove_collection_header(primary,cold,fields,hs))==parent['collectionHeader']['header'])
    reference=native['actualContext']['referenceSource'];rs={k:base+v for k,v in replay['referenceSymbolRvas'].items()}
    need('actual-reference-frontend-zero-outlocal-and-callback',data['frontend'][2]==base+native['actualContext']['callTargetRva']
        and norm(modelview_packable_sources.read_packable(data['frontend'][0],data['frontend'][2],rs))==reference['source']
        and norm(modelview_packable_sources.backend_forwarder(backend,ps['backend'],base+replay['backendTargetRva']))==reference['backendForwarder']
        and reference.get('closedReferenceCallerRequired')is True and reference.get('liveProviderSelectionProved')is False
        and reference.get('wholeOwnerAdmitted')is False)
    need('same-typed-list-and-owned-capacity-contexts',native['typedBase']==empty['typedBase']==native['actualContext']['typedContext']
        and native['capacityContext']==native['actualContext']['capacityContext']
        and helper['constructorContext']==native['actualContext']['listContext'])
    add=native['canonicalAddRegistration'];slots={r['relativeSlot']:r for r in empty['context']['entries']}
    need('own-exact-Add-declaration-and-element-context',native['addParameterOwner']['typeIndex']==native['capacityContext']['listClassDefinition']
        and type(native['addParameterOwner']['ordinal'])is int and native['addParameterOwner']['ordinal']==0
        and add['methodDefinitionIndices']==[slots[6]['methodSpec'][0]]
        and add['classInstantiation']['arguments']==native['actualContext']['registration']['classInstantiation']['arguments'])


def compose(native,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('own-independent-positive-source',native.get('schema')=='endfield.entity-ptr-list-source.v3'
        and native.get('nativeInputs')==pins and native.get('codecKind')=='List<EntityPtr>'
        and native.get('typeName')==TYPE and native.get('elementType')==ELEMENT
        and native.get('parentDerived')is False and native.get('parentFieldAdmitted')is False
        and native.get('wholeOwnerAdmitted')is False and type(native.get('maxCount'))is int and native['maxCount']==LIMIT
        and all(native.get(k)is True for k in('nullAdmitted','emptyAdmitted','positiveAdmitted'))
        and native.get('managedElementBytes')==40 and native.get('wireCountBytes')==4
        and native.get('elementGrammar')==dict(nullMarker=255,memberCount=3,fields=['uint64','uint32','bool-byte']))
    context=native['actualContext'];parent=native['parent'];child=native['child'];registration=context['registration']
    need('no-Param-parent-or-capability-reused',parent.get('context')==context
        and parent.get('parentFieldAdmitted')is False and parent.get('wholeOwnerAdmitted')is False
        and child.get('schema')=='endfield.entity-ptr-independent-value-source.v2'
        and child.get('nativeInputs')==pins and child.get('parentDerived')is False and'outer'not in child
        and child.get('parentFieldAdmitted')is False and child.get('wholeOwnerAdmitted')is False
        and [r['originalType']for r in child['registrations']]==[ELEMENT]
        and [r['originalType']for r in child['forwarders']]==[ELEMENT])
    carrier=context['closedCarrier'];element,=carrier['classArguments'];raw=bytes.fromhex(element['rawHex'])
    need('own-exact-closed-value-carrier',context.get('nativeInputs')==pins and context.get('closedListType')==TYPE
        and context.get('elementType')==ELEMENT and context.get('elementValueType')is True
        and carrier.get('name')==TYPE and element.get('name')==ELEMENT
        and len(raw)==16 and raw[10:12]==bytes((17,128))
        and parent['listRegistration']==registration
        and [a['raw_type_record_hex'].upper()for a in registration['classInstantiation']['arguments']]==[element['rawHex'].upper()])
    selected=native['listPrograms'];entry=selected[0]['selectedBytes'][0][0]
    base=entry-native['sourceWindows']['list'][0]['startRva'];symbols={k:base+v for k,v in native['symbolRvas'].items()}
    need('actual-list-entry-owns-complete-source',entry==registration['pointer']and type(base)is int and base>=1<<32)
    own=regions(native['sourceWindows']['list'],native['sourceRegions']['list'],base,'Module-Entity-list')
    paths=[source.list_program(own,entry,symbols,count=count,new=new)for new in(False,True)for count in range(4)]
    need('all-eight-owned-list-paths-replayed',norm(paths)==selected)
    induction=prove_induction(paths,initial='33db',increment='ffc3',comparison='413bdc',counter='ebx',
        saved_count='R12D loaded once from the collection header output; preserved nonvolatile through callbacks.',max_count=LIMIT)
    need('own-positive-count-induction',norm(induction)==native['countInduction'])
    from scripts.game_data.memorypack.null_list_param import null_list_program
    need('own-null-count-path-replayed',norm(null_list_program(own,entry,symbols['header'],symbols['barrier']))==parent['nullListProgram'])
    add=regions(native['sourceWindows']['actualAdd'],native['sourceRegions']['actualAdd'],base,'Module-Entity-Add')
    need('actual-full40-Add-and-selected-barrier-replayed',norm(source.add_program(add,symbols['add'],symbols['barrier']))==native['actualAdd']
        and native['actualAdd'].get('arrayStride')==native['actualAdd'].get('storedBytes')==40
        and native['actualAdd'].get('barrierElementOffset')==24
        and native.get('actualCanonicalAddPointerEquivalenceClaimed')is False)
    _verify_child(child,pins,base,symbols['dispatch'])
    _verify_helpers(native,pins,base,symbols)
    actual_paths=[p for p in child['adapter']['paths']if p.get('profile')=='actual-slot-match']
    need('same-exact-Entity-value-dispatch-source',len(actual_paths)==3
        and all(p.get('selectedInstructions')and p['selectedInstructions'][0]==symbols['dispatch']for p in actual_paths)
        and len(child['leaf']['sourcePaths'])==2
        and all(p.get('memberCount')==3 and p.get('wireBytes')==14
            and p.get('storedMembers')==[['logicId',8,24],['slotId',4,32],['useSlotId',1,16]]for p in child['leaf']['sourcePaths'])
        and any(row['pointer']==child['adapter']['symbols']['adapter']for row in child['adapterRegistration']))
    usage=context['typedRequest']
    need('same-own-ReadPackable-request',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[TYPE])
        and context['callTargetRva']>0)
    cap=dict(typeName=TYPE,elementType=ELEMENT,elementValueType=True,managedElementBytes=40,
        headerBytes=4,countLimit=LIMIT,countRange=[-1,LIMIT],nullable=True,positiveCountsAdmitted=True,
        elementGrammarAdmitted=True,wholeGrammarAdmitted=True,wireMemberCount=3,positiveElementWireBytes=14,
        nullElementWireBytes=1,nullHeaderDefaultValueBytes=40,knownPaddingByteRanges=[[1,8],[20,24]],
        opaqueRuntimeStorageRanges=[[24,40]],selectedBarrierValueOffsets=[24],runtimeReferenceLayoutAdmitted=False,
        completeRuntimePaddingMapAdmitted=False,runtimeEntityResolutionProved=False,
        freshListsAdmitted=True,reusedListsRequireCapacityAtLeastCount=True,actualCallbackEqualsProvedChildRequired=True,
        canonicalValueAdapterTargetRva=child['adapter']['symbols']['adapter']-base,
        actualSlotDispatchTargetRva=symbols['dispatch']-base,closedCarrier=carrier,
        packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=context['callTargetRva'],
        sourceMethodSpec=usage['methodSpec'],liveFormatterSelectionObserved=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    return norm(dict(schema=SCHEMA,nativeInputs=pins,capability=CAP,capabilities={CAP:cap},proof=dict(source=native),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False))


def validate_component(component,pins):
    need('own-component-envelope',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    checked=compose(component['proof']['source'],pins);need('complete-source-and-capability-replayed',checked==component)
    return checked['capabilities'][CAP]


def derive(image,pins,*,typed_request,call_target):
    native=source.derive_collection(image,pins,typed_request=typed_request,call_target=call_target,count_limit=LIMIT)
    return compose(native,pins)


def bind_request(pins,join,component,capability):
    cap=validate_component(component,pins);usage=join['typedRequest']
    need('exact-independent-child-and-own-Module-request',capability==CAP and join.get('typeName')==TYPE
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[TYPE])
        and usage.get('methodSpec')==cap['sourceMethodSpec']
        and (usage['methodSpec'][0],join.get('sourceTargetRva'))==(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva']))
    return dict(fieldName=join['fieldName'],typeName=TYPE,capability=CAP,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
        countLimit=LIMIT,managedElementBytes=40,wireMemberCount=3,positiveElementWireBytes=14,
        actualCallbackEqualsProvedChildRequired=True,runtimeEntityResolutionProved=False)
