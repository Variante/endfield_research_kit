"""Exact IntroPart raw24 source, named setter, field and full-frame join."""
import json
from scripts.game_data.memorypack import levelscript_posrot_capture_sources as capture
from scripts.game_data.memorypack import generated_posrot_field_sources as fields
from scripts.game_data.memorypack.generated_called_advance_components import verify_advance

WIRE='story-posrot-raw24'


def need(key,condition):
    if not condition:raise ValueError('generatedPosRotComponents.'+key)


def norm(value):return json.loads(json.dumps(value))


def require_vector_homes(path,scope,*,base):
    """Join both full16 MOVAPS saves/restores to actual frame displacements."""
    delta=0;saves={};loads={};captures={name:[]for name in('xmm6','xmm7')}
    capture_sites={s['loadInstructionVa']:(s['register'],s['bytes'])
        for event in scope['events']if event.get('mode')=='buffered-called-advance-posrot24'
        for s in event['inlineSourceProgram']['capturedSourceSlices']}
    for position,(at,hex_)in enumerate(path['selectedProgram']):
        raw=bytes.fromhex(hex_)
        if raw[:3]==bytes.fromhex('4883ec'):delta-=int.from_bytes(raw[3:],'little');continue
        if raw[:3]==bytes.fromhex('4881ec'):delta-=int.from_bytes(raw[3:],'little');continue
        if raw[:3]==bytes.fromhex('4883c4'):delta+=int.from_bytes(raw[3:],'little');continue
        if raw[:3]==bytes.fromhex('4881c4'):delta+=int.from_bytes(raw[3:],'little');continue
        opcode=raw[1:]if raw[:1]==b'\x41'else raw
        if len(opcode)==1 and 0x50<=opcode[0]<=0x57:delta-=8;continue
        if len(opcode)==1 and 0x58<=opcode[0]<=0x5f:delta+=8;continue
        if base+at in capture_sites:
            name,width=capture_sites[base+at]
            need('capture-after-full-vector-save-before-restore',name in saves and name not in loads
                and width==(16 if name=='xmm6'else 8))
            captures[name].append(position)
        for name,modrm in(('xmm6',0x74),('xmm7',0x7c)):
            if raw[:2]not in(bytes.fromhex('0f29'),bytes.fromhex('0f28')):continue
            if len(raw)==5 and raw[2:4]==bytes((modrm,0x24)):displacement=raw[4]
            elif len(raw)==8 and raw[2:4]==bytes((modrm+0x40,0x24)):displacement=int.from_bytes(raw[4:],'little',signed=True)
            else:continue
            home=delta+displacement
            need('whole16-vector-home-matches-complete-frame',home==path['frame'].get('restoredVectorHomes',{}).get(name)
                and(8+home)%16==0)
            if raw[1]==0x29:
                need('one-original-full16-vector-save',name not in saves and not captures[name]);saves[name]=(home,position)
            else:
                need('same-full16-vector-restored-after-all-captures',name in saves and name not in loads
                    and saves[name][0]==home and len(captures[name])==4);loads[name]=(home,position)
    need('both-full16-registers-restored-at-entry-RSP',delta==0 and set(saves)==set(loads)=={'xmm6','xmm7'}
        and abs(saves['xmm6'][0]-saves['xmm7'][0])>=16)
    return True


def compile_member(owner,scope,read,pins):
    index=read['memberIndex']
    need('same-complete-exact-parent',owner.get('wrappedType')==scope.get('wrappedType')==capture.PARENT
        and type(index)is int and 0<=index<len(scope.get('events',[]))
        and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
        and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read
        and owner.get('completeSelectedCallerAdmitted')is True and scope.get('sourceScopeAdmitted')is True
        and read.get('context')is None and'sourceTargetRva'not in read and'resultAbi'not in read)
    setter=owner['setters'][index];layout=fields.validate_event(read,setter)
    value=scope.get('valueTypeSources',{}).get(str(index),{});macro=read['inlineSourceProgram'];advance=read['inlineAdvanceSource']
    need('own-independent-nominal-and-inline-source',value.get('typeName')==capture.TYPE and value.get('layout')==layout
        and value.get('actualSourceProved')is True and value.get('wireBytes')==24
        and value.get('resultAbi')=='inline-bits-to-owned-field'and value.get('advanceSource')==advance)
    base=macro['guardInstructionVa']-read['instruction'][0];selected=scope.get('selectedProgram',[])
    need('literal-owned-guard-and-registers',type(base)is int and base>0 and bool(selected)
        and(scope['headerProof']['readerRegister'],scope['headerProof']['outputRegister'])==('rbx','rdi')
        and bytes.fromhex(read['instruction'][1])==bytes((131,123,macro['readerOffsets']['bufferLength'],24)))
    fields.require_setter(setter,base=base)
    holder=setter.get('directHolder',{});life=owner.get('lifecycle',{})
    need('same-own-direct-holder-lifecycle',norm(holder.get('field'))==norm(life.get('baseHolder'))
        and holder.get('inheritedFieldAliasUsed')is False and setter.get('getter')is None
        and setter.get('targetField')==capture.PARENT+'::'+read['fieldName']
        and setter.get('directGetValue',{}).get('program')is not None)
    regions=[(base+a,bytes.fromhex(h))for a,h in selected]
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    from scripts.game_data.memorypack.generated_vector_member_sources import nonnull
    # Untaken null/buffer edges belong to the complete parent windows. The
    # selected trace cannot supply cold bodies and does not claim them here.
    g=_owned_setter_trace(regions,macro['guardInstructionVa'],scope['codeWindows'],base)
    g.take('837b'+bytes((macro['readerOffsets']['bufferLength'],)).hex()+'18')
    wrapper=g.at;g.take('488b37');g.branch('0f8c',False)
    pointer=g.at;g.take('488b43'+bytes((macro['readerOffsets']['currentPtr'],)).hex(),'ba18000000','488bcb')
    low=g.at;g.take('0f1030');high=g.at;g.take('f20f107810');call=g.at;g.call(macro['advanceTargetVa'])
    need('full-literal-capture-replay',norm(g.seen)==norm(macro.get('selectedBytes'))
        and g.at==macro.get('nextInstructionVa')and pointer==macro.get('sourcePointerInstructionVa')
        and wrapper==macro.get('wrapperLoad',{}).get('instructionVa')and call==macro.get('advanceCallInstructionVa')
        and[low,high]==[s['loadInstructionVa']for s in macro['capturedSourceSlices']])
    verify_advance(advance,macro,pins,base)
    g.take('4885f6');nonnull(g);g.take('488b4610','4885c0');nonnull(g)
    low_store=g.at;g.take(_displacement('0f11b0',setter['fieldOffset']))
    if setter['fieldOffset']==120:g.take('488bcb')
    high_store=g.at;g.take(_displacement('f20f11b8',setter['fieldOffset']+16))
    rich=scope.get('richProgram',{});flows=[x for x in rich.get('sources',[])if x.get('memberIndex')==index]
    stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index];flow=value.get('sourceProgram',{})
    need('complete-once-only-direct-field-byteflow',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==selected and len(flows)==1
        and flows[0].get('instruction')==read['instruction']and flows[0].get('mode')==read['mode']
        and flows[0].get('program')==macro and flows[0].get('actualAdvanceSource')==advance
        and[(x.get('sourceOffset'),x.get('storedBytes'))for x in stores]==[(0,16),(16,8)]
        and all(x['instruction']in selected for x in stores)and all(flow.get(k)==v for k,v in macro.items())
        and flow.get('sourceBytes')==macro['selectedBytes']and flow.get('storedBytes')==24
        and flow.get('fullValueBitsStoredUnchanged')is True and flow.get('fieldStoreProgram')==stores
        and setter==scope['richSetters'][index])
    selected_stores=[(a,h)for a,h in g.seen if a in(low_store,high_store)]
    need('same-whole-macro-named-store-sites',norm([[a-base,h.upper()]for a,h in selected_stores])==[s['instruction']for s in stores])
    paths=owner.get('programs',[])
    need('all-four-complete-parent-frames',len(paths)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in paths}==
        {(False,False),(True,False),(False,True),(True,True)}and all(p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    for p in paths:
        homes=p['frame'].get('restoredVectorHomes',{})
        if p['wrapperNull']:
            # The FF entry returns before either capture and before vector
            # saves. Decode-free exclusion is restricted to this actual short
            # scalar/header path; no vector instruction is admitted by it.
            need('FF-never-writes-vector-registers',not homes and bool(p.get('selectedProgram')))
            for at,hex_ in p['selectedProgram']:
                raw=bytes.fromhex(hex_);opcode=raw[1:]if 0x40<=raw[0]<=0x4f else raw
                need('FF-only-scalar-instructions-and-conditional-branches',raw[0]not in(0x66,0xf2,0xf3,0xc4,0xc5,0x62)
                    and not 0xd8<=raw[0]<=0xdf and(opcode[0]!=15 or len(opcode)>1 and 0x80<=opcode[1]<=0x8f))
        else:
            need('both-full-vector-homes-on-positive-parent-path',all(type(homes.get(name))is int for name in('xmm6','xmm7'))
                and abs(homes['xmm6']-homes['xmm7'])>=16)
            require_vector_homes(p,scope,base=base)
    return WIRE
