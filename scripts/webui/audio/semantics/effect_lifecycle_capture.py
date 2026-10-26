"""Review paired bank, subscription and template lifetimes without inventing origins."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path

from scripts.repo_paths import REPO_ROOT
from scripts.webui.audio.semantics.playback_observer_profile import compile_reads
from scripts.webui.audio.semantics.effect_lifecycle_observer_profile import prepare


def argument(row, index):
    return row['args'][index] if index < 4 else row[{4:'returnValue',5:'moduleBase',6:'extraArgument',7:'sixthArgument',8:'seventhArgument',9:'eighthArgument',10:'ninthArgument',11:'tenthArgument'}[index]]


def snapshot(row, fields, program=None):
    """Check widths, guards, direct addresses, copied spans and array tails."""
    if row['phase'] == 3:
        if any(row.get(k) for k in ('values','states','addresses','spanHex','spanBytes','spanRequested')):
            raise ValueError('unwind contains result reads')
        return {}
    if any(len(row[k]) != len(fields) for k in ('values','states','addresses')):
        raise ValueError('lifecycle field shape differs')
    if program is None:
        program = [list(map(int, r.split(','))) for r in compile_reads(fields).split(';') if r]
    facts = {}; span = bytes.fromhex(row['spanHex']); declared_span = False
    for index, (field, words) in enumerate(zip(fields, program)):
        value = row['values'][index]; state = row['states'][index]; address = row['addresses'][index]
        if type(value) is not int or not 0 <= value < 2**64 or state not in (0,1,2) or type(address) is not int or not 0 <= address < 0x800000000000:
            raise ValueError('lifecycle scalar/state/address invalid')
        mode, ref, wanted = words[5:]
        enabled = (row['states'][ref] == 1 and (row['values'][ref] != 0 if mode == 1 else row['values'][ref] == wanted)) if mode in (1,2) else argument(row,ref) != 0 if mode == 3 else True
        if enabled != (state != 0) or state == 0 and (value or address):
            raise ValueError('lifecycle guard differs')
        kind = field['kind']; bits = {'u8':8,'u16':16,'u32':32,'argumentU32':32}.get(kind,64)
        if value >= 2**bits:
            raise ValueError('lifecycle scalar width differs')
        if kind in ('argument','argumentU32'):
            if state == 2 or address or state == 1 and value != (argument(row,field['argIndex']) & (2**bits - 1)):
                raise ValueError('lifecycle argument read differs')
        elif state == 1 and not field.get('pointerOffsets') and kind != 'pointerFromField':
            if address != argument(row,field['argIndex']) + field['offset']:
                raise ValueError('lifecycle direct read address differs')
        if kind == 'pointerFromField' and state == 1:
            if address != facts[field['baseField']] + field['offset']:
                raise ValueError('lifecycle field pointer address differs')
        if kind == 'lastPointer' and state == 1:
            count = facts[field['countField']]
            pointer_name = {'slotObjectCount':'slotObjects','targetCount':'targetArray','contextHandleCount':'contextHandleArray','sourceHandleCount':'sourceHandleArray'}.get(field['countField'])
            if not 1 <= count <= field['maxCount']:
                raise ValueError('lifecycle array count bound differs')
            if pointer_name and address != facts[pointer_name] + field['offset'] + (count - 1) * field.get('stride',8):
                raise ValueError('lifecycle array tail address differs')
        if kind == 'bytes':
            declared_span = True
            if state == 0 and (span or row['spanRequested'] or row['spanAddress']):
                raise ValueError('guarded lifecycle span contains bytes')
            if state == 2 and span:
                raise ValueError('failed lifecycle span contains bytes')
            if state == 1:
                requested = facts[field['countField']] * field['stride']
                if row['spanRequested'] != requested or len(span) != min(requested,field['maxBytes']) or row['spanBytes'] != len(span) or value != len(span) or row['spanAddress'] != address:
                    raise ValueError('lifecycle span length/address differs')
                pointer_name={'targetBytes':'targetArray','handleBytes':'subscriptionHandles','bankBodyBytes':'bodyAddress'}.get(field['name'])
                if field.get('pointerOffsets') and pointer_name and facts.get(pointer_name)!=address:
                    raise ValueError('lifecycle span pointer chain differs')
        facts[field['name']] = value if state == 1 else None
    if not declared_span and (span or row['spanBytes'] or row['spanRequested'] or row['spanAddress']):
        raise ValueError('undeclared lifecycle span')
    for index, field in enumerate(fields):
        if field['name']=='carrierParameterVtable' and row['states'][index]==1:
            if row['addresses'][index]!=facts.get('selectedCarrierParameter',facts.get('carrierParameter')):
                raise ValueError('lifecycle selected parameter vtable address differs')
        if field['name']=='subscriberVtable' and row['states'][index]==1 and field.get('pointerOffsets'):
            if row['addresses'][index]!=facts.get('subscriber'):
                raise ValueError('lifecycle descriptor subscriber address differs')
        if field['name'].startswith('parameterWord') and row['states'][index] == 1 and field.get('pointerOffsets'):
            pointer = facts.get('templateParameter',facts.get('storedParameter'))
            if not pointer or row['addresses'][index] != pointer + field['offset']:
                raise ValueError('lifecycle parameter projection address differs')
    return facts


def check_scope(row, hook, observer, check_parents=True):
    predicates={}
    for test in hook.get('scopeTests','').split(';'):
        if not test:continue
        index,value,relative=map(int,test.split(','))
        predicates.setdefault(index,[]).append(value+(row['moduleBase'] if relative else 0))
    for index,values in predicates.items():
        if row['states'][index]!=1 or row['values'][index] not in values:
            raise ValueError('lifecycle captured entry violates declared scope')
    mask=hook.get('scopeParentMask',0)
    if mask and check_parents:
        parent=row['parentCaptureId'];seen=set();matched=False
        hook_indices={h['name']:i for i,h in enumerate(observer.expected['nativeHooks'])}
        while parent:
            if parent in seen:raise ValueError('lifecycle scope ancestry cycles')
            seen.add(parent);ancestor=observer.calls.get((row['windowId'],parent))
            if ancestor is None:break
            entry=ancestor['entry']
            if entry['threadId']!=row['threadId'] or entry['timestampNs']>row['timestampNs'] or 'return' in ancestor:break
            matched|=bool(mask & (1<<hook_indices[entry['hook']]))
            parent=entry['parentCaptureId']
        if not matched:raise ValueError('lifecycle selected parent scope missing')


class Lifecycle:
    def __init__(self, expected, parameter_transform=None, parameter_initialize=None):
        self.expected = expected; self.calls = {}; self.completed = []; self.children = {}; self.counts = Counter()
        self.parameter_transform=parameter_transform
        self.parameter_initialize=parameter_initialize
        self.parameter_loads=[]
        self.carrier_retentions={}
        self.templates = {}; self.parameters = {}; self.carriers = {}; self.effects = {}; self.generation = Counter()
        self.bank_references = []; self.bank_releases = []; self.bank_owners = {}; self.subscriptions = []; self.destructions = []; self.outputs = []; self.updates = []; self.callbacks = []; self.unresolved = Counter(); self.carrier_origins = {}

    def ancestors(self, call):
        parent = call['entry']['parentCaptureId']; seen = set()
        while parent:
            key = (call['entry']['windowId'],parent)
            if key in seen or key not in self.calls:
                break
            seen.add(key); ancestor = self.calls[key]
            if ancestor['entry']['threadId'] != call['entry']['threadId']:
                break
            if ancestor['entry']['timestampNs'] > call['entry']['timestampNs'] or 'return' in ancestor and 'return' in call and ancestor['return']['timestampNs'] < call['return']['timestampNs']:
                break
            yield ancestor; parent = ancestor['entry']['parentCaptureId']

    def descendants(self, call, kind):
        key=(call['entry']['windowId'],call['entry']['captureId']); stack=list(self.children.get(key,())); seen=set()
        while stack:
            child=stack.pop(); identity=(child['entry']['windowId'],child['entry']['captureId'])
            if identity in seen or len(seen)>=65536:raise ValueError('lifecycle descendant graph exceeds bound or cycles')
            seen.add(identity);stack.extend(self.children.get(identity,()))
            if child['kind']==kind and child['closed'] and any(a is call for a in self.ancestors(child)):yield child

    def birth(self, lane, pointer, call, values):
        self.generation[(lane,pointer)] += 1
        return dict(pointer=pointer,generation=self.generation[(lane,pointer)],captureId=call['entry']['captureId'],windowId=call['entry']['windowId'],**values)

    def enter(self, row, facts, kind):
        key = (row['windowId'],row['captureId'])
        if key in self.calls:
            raise ValueError('duplicate lifecycle invocation')
        if len(self.calls) >= 250000:
            raise ValueError('lifecycle invocation bound exceeded')
        call = dict(entry=row,initial=facts,kind=kind,closed=False)
        # Save the observed generation at entry; a later reused pointer cannot
        # become the origin of an earlier call.
        call['parameterOrigin'] = self.parameters.get((row['windowId'],row['args'][0]))
        call['templateOrigin'] = self.templates.get((row['windowId'],row['args'][0]))
        call['carrierOrigin'] = self.carriers.get((row['windowId'],row['args'][0]))
        call['effectOrigin'] = self.effects.get((row['windowId'],row['args'][0]))
        if kind=='effectParameterInstantiateWithAllocator':call['requestedTemplateOrigin']=self.templates.get((row['windowId'],row['args'][1]))
        if kind in ('gameSyncTargetInsert','gameSyncRemoveTarget'):
            target=facts.get('subscriber')
            call['targetCarrierOrigin']=self.carriers.get((row['windowId'],target-self.expected['effectLifecycle']['layout']['subscriptionNestedOffset'])) if target else None
        if kind=='gameSyncSubscriberCallback':
            call['carrierOrigin']=self.carriers.get((row['windowId'],row['args'][0]-self.expected['effectLifecycle']['layout']['subscriptionNestedOffset']))
            call['callbackParameterOrigin']=self.parameters.get((row['windowId'],facts.get('carrierParameter')))
        if kind=='roomEffectInitialize':call['initializeParameterOrigin']=self.parameters.get((row['windowId'],row['args'][3]))
        if kind=='effectTemplateDestructor' and self.templates.get((row['windowId'],row['args'][0])) is call['templateOrigin']:
            # Destruction need not have entered through final release. Retire
            # at entry so nested work cannot borrow a destroying template.
            self.templates.pop((row['windowId'],row['args'][0]),None)
        self.calls[key] = call
        self.children.setdefault((row['windowId'],row['parentCaptureId']),[]).append(call)

    def finish(self, row, facts, window):
        key = (row['windowId'],row['captureId']); call = self.calls.get(key)
        if not call or 'return' in call:
            raise ValueError('orphan or duplicate lifecycle return')
        before = call['entry']; kind = call['kind']; i = call['initial']; f = facts
        if any(before[k] != row[k] for k in ('args','threadId','hook','parentCaptureId','moduleBase','moduleBytes','invocationStartNs')) or row['timestampNs'] < before['timestampNs']:
            raise ValueError('lifecycle pair identity differs')
        call.update(returned=f,returnRow=row)
        call['return'] = row
        call['closed'] = (row['phase'] == 2 and before.get('observationWindowOpen') is True
                          and row.get('observationWindowOpen') is True and window[0] <= before['invocationStartNs'] <= before['timestampNs'] <= row['timestampNs'] <= window[1])
        self.completed.append(call); self.counts[kind] += 1
        if not call['closed']:
            self.unresolved['notClosedNormally'] += 1; return
        result = row['returnValue']; pointer = row['args'][0]; config = self.expected['effectLifecycle']
        if kind == 'effectTemplateConstructor' and result == pointer and f.get('templateVtable') == row['moduleBase'] + int(config['templateVtableRva'],16):
            self.templates[(row['windowId'],pointer)] = self.birth('template',pointer,call,dict(objectId=f.get('objectId')))
        elif kind=='roomParameterFactory':
            if result and f.get('createdParameter')==result and f.get('parameterVtable')==row['moduleBase']+int(config['parameterVtableRva'],16):
                self.parameters[(row['windowId'],result)]=self.birth('parameter',result,call,dict(sourceParameter=None,sourceTemplate=None,sourceFactoryCaptureId=row['captureId'],allocationGenerationClaim=True,initializationClaim=False))
        elif kind=='effectTemplateLoad':
            points=[row['moduleBase']+int(v,16) for v in config.get('templateVtableRvas',[config['templateVtableRva']])]
            parameter=f.get('templateParameter');body=bytes.fromhex(before['spanHex']);children=list(self.descendants(call,'effectParameterRegistryCreate'))
            created=next((child for child in children if child['return']['returnValue']==1 and child['initial'].get('classId')==int(config['parameterClassId'],16) and child['returned'].get('createdParameter')==parameter),None)
            factory_origin=self.parameters.get((row['windowId'],parameter))
            factories=list(self.descendants(created,'roomParameterFactory')) if created is not None else []
            factory=next((child for child in factories if factory_origin is not None and child['entry']['captureId']==factory_origin['captureId'] and child['return']['returnValue']==parameter),None)
            words=[f.get('parameterWord'+str(j)) for j in range(config['parameterProjection']['byteExtent']//4)]
            parameter_bytes=struct.pack('<'+str(len(words))+'I',*words) if all(type(v) is int for v in words) else b''
            valid=(result==1 and parameter and created is not None and factory is not None and i.get('templateVtable')==f.get('templateVtable') in points and f.get('templateClass')==int(config['parameterClassId'],16) and len(body)>=12 and struct.unpack_from('<II',body)==(f.get('objectId'),f.get('templateClass')) and len(parameter_bytes)==200 and struct.unpack_from('<Q',parameter_bytes)[0]==row['moduleBase']+int(config['parameterVtableRva'],16))
            if valid:
                owner=self.templates.get((row['windowId'],pointer))
                if owner is not call['templateOrigin']:owner=None
                if owner:owner.update(objectId=f['objectId'],effectiveVtable=f['templateVtable'])
                origin=dict(factory_origin,sourceTemplate=owner,sourceLoadCaptureId=row['captureId'],allocationOrigin=factory_origin,initializationClaim=True)
                self.parameters[(row['windowId'],parameter)]=origin
                banks=[a for a in self.ancestors(call) if a['kind'] in ('bankSharedFxRead','bankCustomFxRead')]
                length=struct.unpack_from('<I',body,8)[0];source_verified=False
                if self.parameter_initialize is not None and length<=len(body)-12:
                    derived=self.parameter_initialize(body[12:12+length])
                    source_verified=(len(derived)==len(parameter_bytes) and all(derived[a:b]==parameter_bytes[a:b] for a,b in config['parameterProjection']['knownRanges']) and all(derived[at]==parameter_bytes[at]==1 for at in config['parameterProjection']['transientBytes']))
                self.parameter_loads.append(dict(captureId=row['captureId'],windowId=row['windowId'],templatePointer=pointer,templateOrigin=owner,objectId=f['objectId'],parameterClass=f['templateClass'],parameterOrigin=origin,factoryCaptureId=factory['entry']['captureId'],registryCaptureId=created['entry']['captureId'],sourceAddress=i.get('bodyAddress'),sourcePrefixHex=body.hex(),declaredSerializedBytes=length,originalSerializedSettingsVerified=source_verified,sourceBankCaptureId=banks[0]['entry']['captureId'] if banks else None,status='factoryParameterRetainedByLoadedTemplate',physicalPackageOccurrenceClaim=False))
            else:self.unresolved['loadedTemplateFactoryParameterOrSourceMissing']+=1
        elif kind == 'roomParameterClone':
            initial_words=[i.get('parameterWord'+str(j)) for j in range(config['parameterProjection']['byteExtent']//4)]
            final_words=[f.get('parameterWord'+str(j)) for j in range(config['parameterProjection']['byteExtent']//4)]
            exact=False
            if all(type(v) is int for v in initial_words+final_words):
                raw=struct.pack('<'+str(len(initial_words))+'I',*initial_words); expected=bytearray(raw)
                for offset in config['parameterProjection']['transientBytes']:expected[offset]=1
                exact=(struct.pack('<'+str(len(final_words))+'I',*final_words)==bytes(expected)
                       and struct.unpack_from('<Q',raw)[0]==row['moduleBase']+int(config['parameterVtableRva'],16))
            if result and result != pointer and exact:
                self.parameters[(row['windowId'],result)] = self.birth('parameter',result,call,dict(sourceParameter=pointer,sourceParameterOrigin=call['parameterOrigin'],sourceTemplate=None))
        elif kind == 'effectParameterInstantiateWithAllocator':
            clone = f.get('carrierParameter'); template = f.get('carrierTemplate'); origin = self.parameters.get((row['windowId'],clone))
            if i.get('templateParameter') and self.carriers.get((row['windowId'],pointer)) is call['carrierOrigin']:
                self.carriers.pop((row['windowId'],pointer),None)
            if clone and clone==result and template==row['args'][1] and i.get('templateClass')==f.get('templateClass') and i.get('templateParameter')==f.get('templateParameter'):
                self.carrier_retentions[(row['windowId'],row['captureId'])]=dict(captureId=row['captureId'],windowId=row['windowId'],pointer=pointer,templatePointer=template,templateClass=f.get('templateClass'),parameterPointer=clone,allocationGenerationClaim=False,status='observedEffectCarrierRetention')
            children = list(self.descendants(call,'roomParameterClone'))
            if clone and clone == result and origin and any(c['entry']['captureId']==origin['captureId'] and c['return']['returnValue'] == clone and c['entry']['args'][0]==i.get('templateParameter') for c in children) and template == row['args'][1] and i.get('templateClass')==f.get('templateClass')==int(config['parameterClassId'],16) and i.get('templateParameter')==f.get('templateParameter'):
                owner=self.templates.get((row['windowId'],template));origin['sourceTemplate']=owner if owner is call['requestedTemplateOrigin'] else None
                self.carriers[(row['windowId'],pointer)] = self.birth('carrier',pointer,call,dict(parameterOrigin=origin,templatePointer=template,templateObjectId=i.get('objectId')))
                self.carrier_origins[(row['windowId'],row['captureId'])]=self.carriers[(row['windowId'],pointer)]
            else:
                self.unresolved['carrierCloneOrTemplateOriginMissing'] += 1
        elif kind in ('bankSharedFxRead','bankCustomFxRead'):
            initial_count=i.get('slotObjectCount'); count=f.get('slotObjectCount'); template=f.get('lastSlotObject')
            bodies=list(self.descendants(call,'bankReaderData')); body=next((b for b in bodies if b['entry']['args'][0] == pointer+8),None)
            body_bytes=bytes.fromhex(body['return']['spanHex']) if body else b''
            same_key=all(i.get(k) is not None and i[k]==f.get(k) for k in ('bankId','bankKeyWord','bankMemoryIdentity')) and i['bankKeyWord']&0xffffffff==i['bankId']
            valid=(result==1 and type(initial_count) is int and count==initial_count+1 and type(f.get('slotObjectCapacity')) is int and count<=f['slotObjectCapacity'] and template and same_key and i.get('hircType')==(16 if kind=='bankSharedFxRead' else 17) and body is not None and body['entry']['args'][1]==i.get('hircBodyLength') and len(body_bytes)>=4 and struct.unpack_from('<I',body_bytes)[0]==f.get('readObjectId'))
            if valid:
                owner=self.templates.get((row['windowId'],template))
                loads=[load for load in self.parameter_loads if load['windowId']==row['windowId'] and load['templatePointer']==template and load['objectId']==f['readObjectId'] and self.parameters.get((row['windowId'],load['parameterOrigin']['pointer'])) is load['parameterOrigin'] and (owner is not None and load['templateOrigin'] is owner or load['sourceBankCaptureId']==row['captureId'] and load['sourceAddress']==body['return']['returnValue'])]
                self.bank_references.append(dict(captureId=row['captureId'],windowId=row['windowId'],slot=row['args'][2],bankId=f['bankId'],bankKeyWord=f['bankKeyWord'],bankMemoryIdentity=f['bankMemoryIdentity'],objectId=f['readObjectId'],templatePointer=template,templateOrigin=owner,retainedParameterLoads=loads,bodyPrefixHex=body_bytes.hex(),bodyLength=body['entry']['args'][1],status='directBankSlotReference',constructionGenerationClaim=owner is not None,physicalPackageOccurrenceClaim=False))
                self.bank_owners.setdefault((row['windowId'],row['args'][2]),[]).append(dict(self.bank_references[-1],arrayOrdinal=count,returnSequence=row['sequence']))
            else:self.unresolved['bankAppendBodyOrStableKeyMissing']+=1
        elif kind=='bankSlotPrepareRelease':
            acquired=self.bank_owners.pop((row['windowId'],pointer),[])
            valid=(f.get('slotObjects')==f.get('slotObjectCount')==f.get('slotObjectCapacity')==0
                   and type(i.get('slotObjectCount')) is int and all(i.get(k) is not None for k in ('bankId','bankMemoryIdentity')))
            selected=[ref for ref in acquired if ref['bankId']==i['bankId'] and ref['bankKeyWord']==i.get('bankKeyWord') and ref['bankMemoryIdentity']==i['bankMemoryIdentity'] and ref['arrayOrdinal']<=i['slotObjectCount'] and ref['returnSequence']<before['sequence']] if valid else []
            finals=list(self.descendants(call,'indexableFinalRelease'))
            if selected:
                self.bank_releases.append(dict(captureId=row['captureId'],windowId=row['windowId'],slot=pointer,bankId=i['bankId'],bankKeyWord=i.get('bankKeyWord'),bankMemoryIdentity=i['bankMemoryIdentity'],status='observedBankArrayReleased',knownReferences=selected,finalReleaseCaptureIds=[child['entry']['captureId'] for child in finals if any(ref['templatePointer']==child['entry']['args'][0] and (ref['templateOrigin'] is None or ref['templateOrigin'] is child['templateOrigin']) for ref in selected)],completeBankOwnerInventoryClaim=False,membershipPersistenceClaim='conditional on selected array append/release routes and no intervening unobserved mutation'))
            else:self.unresolved['bankReleaseAcquisitionOrArrayClearMissing']+=1
        elif kind in ('gameSyncTargetInsert','gameSyncRemoveTarget'):
            target=i.get('subscriber'); initial=i.get('targetCount'); final=f.get('targetCount')
            before_targets=[struct.unpack_from('<Q',bytes.fromhex(before['spanHex']),j)[0] for j in range(0,len(bytes.fromhex(before['spanHex']))//16*16,16)]
            after_targets=[struct.unpack_from('<Q',bytes.fromhex(row['spanHex']),j)[0] for j in range(0,len(bytes.fromhex(row['spanHex']))//16*16,16)]
            added=kind=='gameSyncTargetInsert' and result==1 and type(initial) is int and final==initial+1 and target and f.get('lastTarget')==target
            removed=kind=='gameSyncRemoveTarget' and result==1 and type(initial) is int and final==initial-1 and initial<=16 and target in before_targets and target not in after_targets
            if added or removed:
                ancestors=list(self.ancestors(call)); carrier=self.carriers.get((row['windowId'],target-config['layout']['subscriptionNestedOffset'])) if target else None
                if carrier is not call['targetCarrierOrigin'] or carrier and (i.get('selectedCarrierParameter')!=carrier['parameterOrigin']['pointer'] or self.parameters.get((row['windowId'],carrier['parameterOrigin']['pointer'])) is not carrier['parameterOrigin']):carrier=None
                parent=next((a for a in ancestors if a['kind']=='effectParameterInstantiateWithAllocator' and target==a['entry']['args'][0]+config['layout']['subscriptionNestedOffset']),None)
                carrier_calls=[dict(windowId=parent['entry']['windowId'],captureId=parent['entry']['captureId'],pointer=parent['entry']['args'][0],parameterPointer=i.get('selectedCarrierParameter'))] if parent else []
                if parent:carrier=None # Its new retention has not completed yet.
                self.subscriptions.append(dict(captureId=row['captureId'],windowId=row['windowId'],subscriber=target,targetArrayHeader=pointer,status='actualTargetAdded' if added else 'actualTargetRemoved',carrierOrigin=carrier,parameterOrigin=carrier.get('parameterOrigin') if carrier else None,carrierCalls=carrier_calls))
            else:self.unresolved['targetMembershipChangeNotProved']+=1
        elif kind=='stateTargetRegister':
            request=before['args'][0]
            context=i.get('stateContext')
            lane='context' if context else 'source' if i.get('stateGameObjectId')==0 and i.get('stateSource') else None
            stable=all(i.get(k) is not None and i[k]==f.get(k) for k in ('stateContext','stateGameObjectId','stateSource'))
            if lane and stable and result==1 and type(i.get(lane+'HandleCount')) is int and f.get(lane+'HandleCount')==i[lane+'HandleCount']+1 and f.get(lane+'LastHandle')==request:
                # This shared function also runs from ordinary scoped RTPC
                # application. Its historical hook label cannot establish a
                # State namespace; preserve the packed key and raw type.
                self.subscriptions.append(dict(captureId=row['captureId'],windowId=row['windowId'],gameSyncKey=request,gameSyncId=request&0xffffffff,gameSyncType=(request>>32)&255,status='actualScopeHandleAdded',selectedOwner=i['stateContext'] if lane=='context' else i['stateSource'],selectedOwnerLane=lane,scopeKeyAddress=before['args'][1],namedStateSubscriptionClaim=False))
            else:self.unresolved['scopeSelectedOwnerOrHandleWriteMissing']+=1
        elif kind=='stateTargetInsert':
            if result==1 and f.get('created')==1 and f.get('registration'):
                self.subscriptions.append(dict(captureId=row['captureId'],windowId=row['windowId'],status='untypedRegistrationCreated',registration=f['registration'],descriptorTarget=i.get('descriptorTarget'),descriptorType=i.get('descriptorType'),parameterOwnershipClaim=False,namedStateSubscriptionClaim=False))
            else:self.unresolved['untypedRegistrationCreationNotSelected']+=1
        elif kind=='gameSyncSubscriberCallback':
            carrier=self.carriers.get((row['windowId'],pointer-config['layout']['subscriptionNestedOffset']))
            if carrier is not call['carrierOrigin'] or carrier and (call['callbackParameterOrigin'] is not carrier['parameterOrigin'] or self.parameters.get((row['windowId'],carrier['parameterOrigin']['pointer'])) is not carrier['parameterOrigin']):carrier=None
            parameter=carrier['parameterOrigin']['pointer'] if carrier else None
            if carrier and i.get('subscriberVtable')==f.get('subscriberVtable')==row['moduleBase']+int(config['subscriberVtableRva'],16) and i.get('carrierParameter')==f.get('carrierParameter')==parameter and i.get('carrierTemplate')==f.get('carrierTemplate')==carrier['templatePointer']:
                selected_updates={update['captureId'] for update in self.updates if update['windowId']==row['windowId'] and update['status']=='selectedParameterWriteObserved' and update['parameterOrigin'] is carrier['parameterOrigin']}
                setters=[child['entry']['captureId'] for child in self.descendants(call,'roomParameterUpdate') if child['entry']['args'][0]==parameter and child['entry']['captureId'] in selected_updates]
                self.callbacks.append(dict(captureId=row['captureId'],windowId=row['windowId'],status='ownedGameSyncCallback',gameSyncId=i.get('gameSyncId'),gameSyncKey=before['args'][1],gameSyncType=(before['args'][1]>>32)&255,fourthValue=i.get('fourthValue'),fifthValue=i.get('fifthValue'),carrierOrigin=carrier,parameterUpdateCaptureIds=setters,actualParameterWriteClaim=bool(setters)))
            else:self.unresolved['callbackCarrierOrParameterOriginMissing']+=1
        elif kind=='roomEffectInitialize':
            parameter=f.get('storedParameter'); origin=self.parameters.get((row['windowId'],parameter))
            if result==1 and parameter==before['args'][3] and origin and origin is call['initializeParameterOrigin']:
                self.effects[(row['windowId'],pointer)]=self.birth('effect',pointer,call,dict(parameterOrigin=origin))
            else:self.unresolved['effectParameterOriginMissing']+=1
        elif kind=='roomVerbExecute':
            effect=self.effects.get((row['windowId'],pointer))
            if effect and effect is call['effectOrigin'] and i.get('storedParameter')==f.get('storedParameter')==effect['parameterOrigin']['pointer'] and self.parameters.get((row['windowId'],effect['parameterOrigin']['pointer'])) is effect['parameterOrigin']:
                self.outputs.append(dict(captureId=row['captureId'],windowId=row['windowId'],status='ownedParametersReachRoomExecute',effectOrigin=effect,wholeEventToDeviceClaim=False))
            else:self.unresolved['executeEffectOrParameterOriginMissing']+=1
        elif kind=='roomParameterUpdate':
            count=config['parameterProjection']['byteExtent']//4;initial=[i.get('parameterWord'+str(j)) for j in range(count)];final=[f.get('parameterWord'+str(j)) for j in range(count)]
            if all(type(v) is int for v in initial+final):
                raw=struct.pack('<'+str(count)+'I',*initial);returned=struct.pack('<'+str(count)+'I',*final)
                if struct.unpack_from('<Q',raw)[0]==struct.unpack_from('<Q',returned)[0]==row['moduleBase']+int(config['parameterVtableRva'],16):
                    parameter_id=i['parameterIdRaw']&65535;parameter_id=parameter_id-65536 if parameter_id&32768 else parameter_id
                    dispatch=next((d for d in config.get('parameterUpdateRows',[]) if d['parameterId']==parameter_id),None);changed=[j for j,(x,y) in enumerate(zip(raw,returned)) if x!=y]
                    expected_bytes=None;input_value=None
                    if dispatch:
                        input_value=i.get('inputByte' if dispatch['sourceBytes']==1 else 'inputWord')
                        if type(input_value) is int:
                            transform=dispatch['transform']
                            if transform in ('copyBits','boolean'):
                                expected_bytes=bytearray(raw);value=int(input_value!=0) if transform=='boolean' else input_value
                                at=dispatch['storedOffset'];width=dispatch['storedBytes'];expected_bytes[at:at+width]=value.to_bytes(width,'little')
                                for dirty in dispatch['dirtyOffsets']:expected_bytes[dirty]=1
                            elif transform=='dbToLinear' and self.parameter_transform is not None:
                                derived=self.parameter_transform(raw,parameter_id,input_value.to_bytes(dispatch['sourceBytes'],'little'))
                                if len(derived)!=len(raw):raise ValueError('original parameter transform extent differs')
                                expected_bytes=raw[:8]+derived[8:]
                            elif transform!='dbToLinear':raise ValueError('unsupported selected parameter transform')
                    exact=expected_bytes is not None and returned==bytes(expected_bytes)
                    status='selectedParameterWriteObserved' if result==1 and i.get('inputPointer') and dispatch and exact else 'unsupportedIdNoMutation' if result==1 and i.get('inputPointer') and not dispatch and not changed else 'nullInputRejected' if result==31 and not i.get('inputPointer') and not changed else 'parameterUpdateNotSelected'
                    current_origin=self.parameters.get((row['windowId'],pointer));origin=call['parameterOrigin'] if current_origin is call['parameterOrigin'] else None
                    self.updates.append(dict(captureId=row['captureId'],windowId=row['windowId'],parameter=pointer,parameterOrigin=origin,parameterId=parameter_id,declaredInputSize=i.get('declaredInputSize'),inputValue=input_value,exactPayloadAndDirtyWrites=exact,changedBytes=changed,status=status,readinessClaim=False))
        elif kind=='indexableFinalRelease':
            origin=call['templateOrigin']; destructors=list(self.descendants(call,'effectTemplateDestructor')); destroys=list(self.descendants(call,'indexableDestroy'))
            if i.get('objectReferences')==0 and result==0 and i.get('templateVtable') in [row['moduleBase']+int(v,16) for v in config.get('templateVtableRvas',[config['templateVtableRva']])] and any(c['entry']['args'][0]==pointer for c in destructors) and any(c['entry']['args'][0]==pointer for c in destroys):
                terms=list(self.descendants(call,'roomParameterTerminate')); parameter=i.get('templateParameter')
                self.destructions.append(dict(captureId=row['captureId'],windowId=row['windowId'],templatePointer=pointer,templateOrigin=origin,objectId=i.get('objectId'),registryLane=i.get('registryLane'),parameterTerminated=not parameter or any(c['entry']['args'][0]==parameter and c['return']['returnValue']==1 for c in terms),status='finalTemplateDestroyObserved',registryRemovalObserved=False,registryRemovalClaim='conditional on a nonzero ID and matching typed registry entry; list mutation not captured',storageFreeClaim='selected original free route completed'))
                if self.templates.get((row['windowId'],pointer)) is origin:self.templates.pop((row['windowId'],pointer),None)
            elif result==1:self.unresolved['referenceRetainedNoFinalDestruction']+=1
        elif kind=='roomParameterTerminate':
            if self.parameters.get((row['windowId'],pointer)) is call['parameterOrigin']:self.parameters.pop((row['windowId'],pointer),None)
        elif kind=='effectParameterCarrierRelease':
            if self.carriers.get((row['windowId'],pointer)) is call['carrierOrigin']:self.carriers.pop((row['windowId'],pointer),None)
        elif kind=='roomEffectTerminate':
            if self.effects.get((row['windowId'],pointer)) is call['effectOrigin']:self.effects.pop((row['windowId'],pointer),None)
        elif kind=='effectTemplateDestructor':
            if self.templates.get((row['windowId'],pointer)) is call['templateOrigin']:self.templates.pop((row['windowId'],pointer),None)

    def publish(self, diagnostics):
        for subscription in self.subscriptions:
            for candidate in subscription.pop('carrierCalls',[]):
                retention=self.carrier_retentions.get((candidate['windowId'],candidate['captureId']))
                if retention and retention['pointer']==candidate['pointer'] and retention['parameterPointer']==candidate['parameterPointer']:subscription['carrierRetention']=retention
                carrier=self.carrier_origins.get((candidate['windowId'],candidate['captureId']))
                if carrier and carrier['pointer']==candidate['pointer'] and carrier['parameterOrigin']['pointer']==candidate['parameterPointer']:
                    subscription.update(carrierOrigin=carrier,parameterOrigin=carrier['parameterOrigin']);break
        return dict(schema='endfield.audio-effect-lifecycle-review.v7',status='withheld' if diagnostics else 'reviewed',diagnostics=diagnostics,counts=dict(self.counts),unresolved=dict(self.unresolved),parameterLoads=[] if diagnostics else self.parameter_loads,bankReferences=[] if diagnostics else self.bank_references,bankReferenceReleases=[] if diagnostics else self.bank_releases,subscriptions=[] if diagnostics else self.subscriptions,parameterUpdates=[] if diagnostics else self.updates,callbacks=[] if diagnostics else self.callbacks,destructions=[] if diagnostics else self.destructions,roomExecution=[] if diagnostics else self.outputs,wholeEventToDeviceClaim=False,evidenceBoundary='Closed unsampled paired lifecycles within declared entry predicates and observed-parent scopes. Actual bank-array append, callback target membership, packed-key scope-handle append, untyped registration output and selected zero-reference destruction are distinct claims. Historical state hook labels do not establish a State namespace. Observed constructors/clone results provide generations; missing births stay unresolved. Source prefixes plus bank ID provide candidates, not a unique physical package occurrence. Snapshot equality does not prove atomicity, cross-thread causal ordering or exclusive ownership.')


def review_rows(records, expected, windows, summary, parameter_transform=None, parameter_initialize=None):
    observer=Lifecycle(expected,parameter_transform,parameter_initialize); hooks={h['name']:h for h in expected['nativeHooks']}; diagnostics=[]; count=0; previous=0; extent=None
    programs={(name,phase):[list(map(int,r.split(','))) for r in compile_reads(h['memory'] if phase==1 else h['resultMemory']).split(';') if r] for name,h in hooks.items() for phase in (1,2)}
    skipped=summary.get('playbackSampling',{}).get('skipped',[])
    sampling=summary.get('playbackSampling',{});unreadable=sampling.get('scopeUnreadable',[])
    checks=dict(complete=summary.get('complete') is True,hooksQuiescent=summary.get('hooksQuiescent') is True,sourceOwnerWriteComplete=summary.get('sourceOwnerWriteComplete') is True,noDrops=summary.get('dropped')==0,noUnresolvedResults=summary.get('unresolvedResults')==0,allSelectedLifecycleCalls=sampling.get('allSelectedEffectLifecycleCalls') is True,declaredSelection=sampling.get('effectLifecycleSelection')=='declaredPredicatesAndObservedParents',noUnreadableScope=len(unreadable)>=len(hooks) and all(type(v) is int and v==0 for v in unreadable[:len(hooks)]),noSampling=len(skipped)>=len(hooks) and all(v==0 for v in skipped[:len(hooks)]))
    # A known lossy recording cannot establish generations or ancestry. Still
    # validate every saved row and its pair identity, without retaining a full
    # graph or attempting semantic joins. The bound applies to pending calls,
    # rather than rejecting an arbitrarily long stream of completed calls.
    admissible=all(checks.values()); pending={}; failures=Counter()
    for number,row in enumerate(records,1):
        count=number
        try:
            if number>5000000:raise ValueError('lifecycle row bound exceeded')
            hook=hooks[row['hook']]; phase=row['phase']; window=windows[row['windowId']]
            if row['schema']!='endfieldCapture.audioPlaybackObservation.v1' or phase not in (1,2,3) or row['sequence']<=previous or len(row['args'])!=4 or any(type(v) is not int or not 0<=v<2**64 for v in row['args']) or type(row['captureId']) is not int or row['captureId']<=0:
                raise ValueError('lifecycle row schema/phase/sequence differs')
            previous=row['sequence']
            if row.get('observationWindowId')!=row['windowId'] or type(row.get('observationWindowOpen')) is not bool:
                raise ValueError('lifecycle window identity differs')
            current=(row['moduleBase'],row['moduleBytes'])
            if not current[0] or current[0]%4096 or not 0<current[1]<2**32 or current[0]+current[1]>=0x800000000000 or extent is not None and current!=extent:
                raise ValueError('lifecycle module extent differs')
            extent=current
            if phase==2 and (row['flags']&5!=5 or row['flags']&2 or row['resultCode']!=0):raise ValueError('lifecycle normal result is not resolved')
            if phase==3 and row['resultCode']!=0xffffffff:raise ValueError('lifecycle unwind result differs')
            fields=hook['memory'] if phase==1 else hook['resultMemory'];facts=snapshot(row,fields,programs[(row['hook'],1 if phase==1 else 2)])
            if phase==1:check_scope(row,hook,observer,admissible)
            if admissible:
                if phase==1:observer.enter(row,facts,hook['sourceKind'])
                else:observer.finish(row,facts,window)
            else:
                key=(row['windowId'],row['captureId'])
                if phase==1:
                    if key in pending:raise ValueError('duplicate lifecycle invocation')
                    if len(pending)>=250000:raise ValueError('lifecycle pending invocation bound exceeded')
                    pending[key]=row
                else:
                    before=pending.pop(key,None)
                    if before is None:raise ValueError('orphan or duplicate lifecycle return')
                    if any(before[k]!=row[k] for k in ('args','threadId','hook','parentCaptureId','moduleBase','moduleBytes','invocationStartNs')) or row['timestampNs']<before['timestampNs']:
                        raise ValueError('lifecycle pair identity differs')
                    observer.counts[hook['sourceKind']]+=1
        except (ValueError,KeyError,TypeError,IndexError,struct.error) as error:
            failures[str(error)[:240]]+=1
            if len(diagnostics)<32:diagnostics.append(dict(row=number,detail=str(error)[:240]))
    incomplete=sum('return' not in c for c in observer.calls.values()) if admissible else len(pending)
    checks.update(rowCount=summary.get('sourceOwnerRows')==count,closedWindows=bool(windows),allPairsClosed=incomplete==0)
    diagnostics.extend(dict(check=k,detail='lifecycle completeness gate failed') for k,v in checks.items() if not v)
    result=observer.publish(diagnostics);result.update(rows=count,incompletePairs=incomplete,coverage=checks,rowFailureCounts=dict(failures),semanticJoinsAttempted=admissible)
    return result


def review(session, expected, parameter_transform=None, parameter_initialize=None):
    session=Path(session).resolve(); inputs=[]
    def read(path):
        raw=path.read_bytes();inputs.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()));return raw
    identity=json.loads(read(session/'session.json')); runtime=read(session/'private/EndfieldCapture.dll')
    if len(runtime)!=identity['runtimeBytes'] or hashlib.sha256(runtime).hexdigest()!=identity['runtimeSha256'].lower():
        raise ValueError('lifecycle staged runtime differs from session identity')
    manifest=json.loads(read(session/'private/source-owner-build-manifest.json')); activation=json.loads(read(session/'private/audio-activation.json'));summary=json.loads(read(session/'audio/summary.json'))
    for key in ('schema','files','hooks','nativeHooks','effectLifecycle','automaticWindow','nativeSelectionScope'):
        if manifest.get(key)!=expected.get(key):raise ValueError('saved lifecycle recipe differs: '+key)
    if activation['schema']!=expected['effectLifecycle']['activationSchema']:raise ValueError('lifecycle activation schema differs')
    activated={h['name']:h for h in activation['hooks']}
    if len(activated)!=len(expected['hooks'])+len(expected['nativeHooks']):raise ValueError('lifecycle activated hook roster differs')
    for hook in expected['nativeHooks']:
        if hook['name'] not in activated or any(activated[hook['name']].get(k)!=hook.get(k) for k in ('rva','abiId','readProgram','resultProgram','scopeTests','scopeParentMask')):raise ValueError('lifecycle activation site/ABI/read program/scope differs')
    windows={}
    for line in read(session/'audio/windows.jsonl').splitlines():
        row=json.loads(line)
        if row['action']=='stop':
            if row['requestId'] in windows or row['endNs']<row['startNs']:raise ValueError('lifecycle duplicate/invalid closed window')
            windows[row['requestId']]=(row['startNs'],row['endNs'])
    path=session/'audio/source_owner.jsonl';digest=hashlib.sha256();size=0
    def records():
        nonlocal size
        with path.open('rb') as stream:
            for line in stream:
                if len(line)>65536:raise ValueError('lifecycle raw row bound exceeded')
                digest.update(line);size+=len(line);yield json.loads(line)
    result=review_rows(records(),expected,windows,summary,parameter_transform,parameter_initialize);inputs.append(dict(path=str(path),bytes=size,sha256=digest.hexdigest()))
    result.update(session=str(session),inputs=inputs);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--game-root',type=Path,required=True);parser.add_argument('--session',type=Path,required=True);parser.add_argument('--original-ak',type=Path,help='Explicit identical private DLL for exact original nonlinear setter comparisons; no engine Init');parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/audio/effect_lifecycle_capture_current.json');args=parser.parse_args()
    if REPO_ROOT/'reports' not in args.output.resolve().parents:raise ValueError('Lifecycle reports must stay under reports/')
    expected=prepare(args.game_root,REPO_ROOT/'reports/audio/effect_lifecycle_capture_manifest.json');transform=initialize=None
    if args.original_ak is not None:
        from scripts.game_data.wwise_room_parameters_host import OriginalRoomParameters
        host=OriginalRoomParameters(gameassembly=args.game_root/'GameAssembly.dll',metadata=args.game_root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',ak_sound_engine=args.game_root/'Endfield_Data/Plugins/x86_64/AkSoundEngine.dll',original_ak=args.original_ak)
        transform=lambda raw,identifier,payload:bytes.fromhex(host.run(stored_parameter_hex=raw.hex(),updates=[(identifier,payload)])['updatedParameterHex'])
        initialize=lambda payload:bytes.fromhex(host.run(serialized_parameter_hex=payload.hex())['initialParameterHex'])
    result=review(args.session,expected,transform,initialize);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(result['status'],result['rows'],'rows;',len(result['diagnostics']),'diagnostics ->',args.output)


if __name__=='__main__':main()
