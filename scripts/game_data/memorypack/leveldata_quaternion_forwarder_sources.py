"""Closed Quaternion helper with its own internal ReadUnmanaged request.

The exact helper preserves the incoming hidden output and Reader, supplies an
owned R8 MethodInfo, and calls the independent nominal raw16 source. Its wire
and parent field/frame claims remain separate from this closed call boundary.
"""
import json

from scripts.game_data.memorypack import leveldata_quaternion_value_sources as quaternion

SCHEMA='endfield.story-quaternion-closed-value-source.v1'
MEMBERS={('Beyond.Gameplay.TyphoeaArcheryObstacleData','spawnRotation'),
         ('Beyond.Gameplay.TyphoeaArcheryTargetData','spawnRotation')}


def need(check,condition,detail=None):
    if not condition:raise ValueError('storyQuaternionForwarder.'+check+(':'+str(detail)[:1400]if detail is not None else''))


def owns_member(parent,field,type_name):
    return type_name==quaternion.TYPE and(parent,field)in MEMBERS


def validate_local_copy(row,event,setter,source,locals_,*,register,width,offset):
    """Exact whole16 self-copy into the already-owned hidden RSP48 home."""
    from scripts.game_data.memorypack.buff_ec_profiles_native import raw
    layout=event.get('nominalValueLayout',{});parent,_,field=setter.get('targetField','').rpartition('::')
    carrier=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('exact-own-closed-Quaternion-self-copy',owns_member(parent,field,event.get('declaredType'))
        and event.get('fieldName')==field and event.get('kind')=='value16:'+quaternion.TYPE
        and event.get('sourceContextMode')=='owned-closed-forwarder'and event.get('context')is None
        and event.get('mode')=='typed-hidden-value'and event.get('resultAbi')=='hidden-local'
        and event.get('actualSourceProved')is True and type(event.get('wireBytes'))is int and event['wireBytes']==16
        and layout.get('typeName')==quaternion.TYPE and layout.get('managedBytes')==setter.get('storedBytes')==16
        and layout.get('fields')in([[(axis),'float',16+4*i]for i,axis in enumerate('xyzw')],
            [(axis,'float',16+4*i)for i,axis in enumerate('xyzw')])
        and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]
        and type(layout.get('typeDefinition'))is int and len(carrier)==16 and carrier[10:12]==bytes((17,128))
        and int.from_bytes(carrier[:8],'little')==layout['typeDefinition']
        and type(width)is int and type(offset)is int
        and source[:1]==('member',)and source[2:4]==(0,16)and(register,width,offset)==('xmm0',16,48)
        and raw(row)==bytes.fromhex('f30f7f442430')
        and[locals_.get(offset+i)for i in range(16)]==[(source[1],i)for i in range(16)],
        dict(targetField=setter.get('targetField'),fieldName=event.get('fieldName'),kind=event.get('kind'),
            mode=event.get('mode'),sourceContextMode=event.get('sourceContextMode'),layout=layout,
            parameterTypeRecordHex=setter.get('parameterTypeRecordHex'),source=source,register=register,width=width,
            destination=offset,instruction=row.get('bytes'),sameOwnedHiddenLocal=[locals_.get(offset+i)for i in range(16)]==[(source[1],i)for i in range(16)]))


def verify(actual,pins):
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    need('current-own-closed-Quaternion-source',actual.get('schema')==SCHEMA and actual.get('status')=='validated'
        and actual.get('nativeInputs')==pins and actual.get('typeName')==quaternion.TYPE
        and actual.get('readMethod')=='ReadUnmanaged'and actual.get('wireBytes')==actual.get('managedBytes')==16
        and type(actual.get('wireBytes'))is int and type(actual.get('managedBytes'))is int
        and actual.get('resultAbi')=='hidden-local'and actual.get('contextRegister')is None
        and actual.get('contextMode')=='owned-closed-forwarder'and actual.get('actualSourceProved')is True
        and actual.get('referenceLaneOffsets')==actual.get('paddingByteRanges')==[]
        and actual.get('pointerAliasClaimed')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False)
    p=actual['proof'];forward=p['forwarderProgram'];selected=forward.get('selectedBytes',[])
    need('literal-owned-helper-entry',bool(selected)and type(actual.get('targetRva'))is int)
    base=selected[0][0]-actual['targetRva']
    helper=regions(p['actualWindows'],p['actualSourceRegions'],base,'Quaternion-forwarder')
    need('own-helper-family',p.get('actualFamily',{}).get('selectedPrimaryRva')==actual['targetRva'])
    need('complete-closed-helper-byte-program',json.loads(json.dumps(forwarder_program(helper,base+actual['targetRva'])))==forward)
    nested=p['nestedSource'];context=p['internalContext'];q=nested['proof'];request=q['typedRequest']
    need('separate-own-typed-source',nested.get('nativeInputs')==pins
        and nested.get('typeDefinition')==actual.get('typeDefinition')
        and nested.get('readerMethodDefinition')==actual.get('readerMethodDefinition')
        and q.get('actualFamily',{}).get('selectedPrimaryRva')==nested.get('targetRva')
        and forward['nestedTargetVa']==base+nested.get('targetRva',-1)
        and p.get('typedRequest')==request and p.get('actualProgram')==q.get('actualProgram'))
    quaternion.bind(context,forward['nestedTargetVa'],nested,base=base)
    raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('exact-internal-owned-Quaternion-request',len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==actual['typeDefinition']
        and context.get('instructionRva')==forward['contextInstructionVa']-base
        and context.get('cellVa')==forward['contextCellVa']
        and tuple(request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[quaternion.TYPE])
        and all(request.get(k)==context.get(k)for k in('instructionRva','instructionHex','methodSpec','methodSpecIndex')))
    context_bytes=[b[forward['contextInstructionVa']-a:forward['contextInstructionVa']-a+7]
        for a,b in helper if a<=forward['contextInstructionVa']and forward['contextInstructionVa']+7<=a+len(b)]
    need('literal-seven-byte-R8-context-load',len(context_bytes)==1 and context_bytes[0][:3]==bytes.fromhex('4c8b05')
        and context_bytes[0].hex().upper()==context.get('instructionHex'))
    raw_source=regions(q['actualWindows'],q['actualSourceRegions'],base,'Quaternion-raw16')
    need('same-complete-raw16-byte-program',json.loads(json.dumps(quaternion.program(raw_source,
        forward['nestedTargetVa'],q['readerOffsets'])))==q['actualProgram'])
    need('same-independent-four-Single-layout',q.get('nominalLayout')==[[axis,'float',16+4*i]for i,axis in enumerate('xyzw')]
        and q.get('boxedBytes')==32 and q.get('nativeBytes')==16)
    return base


def derive(image,pins,*,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import generated_action_sources as actions,pointer_param
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    _publication_gate(image,pins);base=image.pe.image_base
    need('actual-owned-helper-target',type(source_target)is int and source_target>base)
    body=pointer_param.owned(image,source_target);program=forwarder_program(body['regions'],source_target)
    contexts,skipped=actions._contexts(image,body['rows'])
    need('one-internal-current-context',len(contexts)==1);context,=contexts
    need('context-owned-at-actual-R8-load',context.get('instructionRva')==program['contextInstructionVa']-base)
    nested=quaternion.derive(image,pins,context=context,source_target=program['nestedTargetVa'])
    raw_body=pointer_param.owned(image,program['nestedTargetVa'])
    need('same-owned-nested-windows',raw_body['windows']==nested['proof']['actualWindows'])
    nested['proof']['actualSourceRegions']=[[at-base,raw.hex().upper()]for at,raw in raw_body['regions']]
    result=dict(schema=SCHEMA,status='validated',nativeInputs=dict(pins),typeName=quaternion.TYPE,
        typeDefinition=nested['typeDefinition'],readMethod='ReadUnmanaged',readerMethodDefinition=nested['readerMethodDefinition'],
        targetRva=source_target-base,wireBytes=16,managedBytes=16,resultAbi='hidden-local',hiddenOutputRegister='rcx',
        readerRegister='rdx',contextRegister=None,contextMode='owned-closed-forwarder',actualSourceProved=True,
        referenceLaneOffsets=[],paddingByteRanges=[],pointerAliasClaimed=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(forwarderProgram=program,internalContext=context,nestedSource=nested,typedRequest=nested['proof']['typedRequest'],
            actualProgram=nested['proof']['actualProgram'],actualWindows=body['windows'],
            actualFamily=image.unwind_index.family(source_target-base),
            actualSourceRegions=[[at-base,raw.hex().upper()]for at,raw in body['regions']],skippedRuntimeCells=skipped),
        evidenceBoundary=dict(exact='Own full closed helper and internal typed R8 request join the independent complete raw16 Quaternion source.',
            conditional=__doc__,unresolved=['enclosing field/local/all-frame joins','refill/error paths','whole owner and physical EOF']))
    result=json.loads(json.dumps(result));verify(result,pins);_publication_gate(image,pins);return result
