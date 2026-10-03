"""Local retained-provider and package-key observations from admitted entries."""
from collections import Counter
from scripts.game_data import wwise_external_package_native as package

SCHEMA = 'endfield.audio-source-io-entry-observations.v1'
BOUNDARY = ('Non-atomic local entry reads under selected retention, storage and package gates. '
            'Path keys are computed from reviewed hash inputs and compared with an independent lookup-input cohort. '
            'No calls are paired; no returned row, package selection, pointer lifetime, managed ownership, file read, decoded output or audibility is established.')


def summarize(rows: list[dict], hooks: list[dict], gates: dict) -> dict:
    """Called only after the surrounding session/row audit; fail closed on children."""
    for name in ('providerRetentionGate','providerStorageGate','externalPackageGate'):
        gate = gates.get(name, {})
        if gate.get('status') != 'validated':
            return {'schema':SCHEMA, 'status':gate.get('status','missing'),
                    'detail':gate.get('detail',name+' unavailable')}
    storage = gates['providerStorageGate']['contract']
    contract = gates['externalPackageGate']['contract']
    spec = gates['externalPackageGate']['observerSpec']
    # The matched primary address point is already authenticated by storage.
    primary = next(row['targetRva'] for row in storage['addressPointBindings']
                   if row['owner']=='ordinaryProviderConstructor' and row['witness']=='addressPrimaryTable')
    by_name = {h['name']:h for h in hooks}
    kinds = ('anonymousProviderRetainedPreparation','anonymousProviderStartPrimary',
             'anonymousExternalPackagePathHash','anonymousExternalPackageKeyLookup')
    result = {kind:{'entryCount':0} for kind in kinds}
    paths, keys, key_tables = Counter(), {}, {}

    def count(entry, field, state):
        entry.setdefault(field,Counter())[state] += 1

    def pointer(entry, facts, field, label):
        if field in facts:
            value = facts[field]
            count(entry,label,'unreadableOrGuardedOut' if value is None else 'nonzero' if value else 'zero')

    for row in rows:
        hook = by_name[row['hook']]
        kind = hook['sourceKind']
        if kind not in result:
            continue
        entry = result[kind]
        entry['entryCount'] += 1
        facts = {f['name']:v if state==1 else None for f,v,state in zip(hook['memory'],row['values'],row['states'])}
        base = row['moduleBase']
        if kind in spec['callers']:
            role = spec['callers'][kind].get(row['returnAddress']-base,'unreviewedCaller')
            count(entry,'callerRoles',role)
        else:
            role = None
        if 'providerAddressPointPointer' in facts:
            value = facts['providerAddressPointPointer']
            count(entry,'addressPoint','unreadable' if value is None else 'matched' if value==base+int(primary,16) else 'different')
        pointer(entry,facts,'retainedDescriptorPointer','retainedDescriptor')
        pointer(entry,facts,'selectedDevicePointer','selectedDevice')
        pointer(entry,facts,'retainedTextPointer','retainedTextPointer')
        pointer(entry,facts,'selectedIoContextPointer','selectedIoContext')
        if 'selectedIoAddressPointPointer' in facts:
            value = facts['selectedIoAddressPointPointer']
            count(entry,'ioAddressPoint','unreadableOrGuardedOut' if value is None else
                  'matchedDefaultPackageIo' if value==base+int(spec['ioAddressPointRva'],16) else 'different')
        if facts.get('retainedWideText') is not None:
            count(entry,'retainedText','terminated')
        if kind == 'anonymousExternalPackagePathHash' and role=='packageDescriptorLookup' and facts.get('externalPackageWideText') is not None:
            text = b''.join(unit.to_bytes(2,'little') for unit in row['textUnits']).decode('utf-16-le')
            if text:
                paths[text] += 1
        if kind == 'anonymousExternalPackageKeyLookup':
            key = row['args'][hook['args']['externalPackageKey']['index']]
            cohort = keys.setdefault(key,{'entryCount':0,'reviewedCallerEntryCount':0,'requiredKindEntryCount':0,'tableCounts':Counter()})
            cohort['entryCount'] += 1
            cohort['reviewedCallerEntryCount'] += role=='packageDescriptorLookup'
            flags = facts['externalPackageFlagsKind']
            cohort['requiredKindEntryCount'] += flags==spec['requiredKind']
            count(entry,'flagsKind','unreadable' if flags is None else str(flags))
            table = facts['externalPackageTablePointer']
            count(entry,'tablePointer','unreadable' if table is None else 'nonzero' if table else 'zero')
            count_value = facts['externalPackageTableCount']
            cohort['tableCounts']['unreadableOrGuardedOut' if count_value is None else str(count_value)] += 1
            if table:
                key_tables.setdefault(key,set()).add(table)
    output = {'schema':SCHEMA,'status':'validated','hooks':{
        kind:{name:dict(value) if isinstance(value,Counter) else value for name,value in entry.items()}
        for kind,entry in result.items()}, 'distinctLookupKeyCount':len(keys),
        'lookupKeysTruncated':len(keys)>32,'lookupKeys':[
            {'key':str(key),**{name:dict(value) if isinstance(value,Counter) else value for name,value in cohort.items()},
             'distinctTablePointerCount':len(key_tables.get(key,()))} for key,cohort in sorted(keys.items())[:32]],
        'distinctHashInputPathCount':len(paths),'pathKeyCandidatesTruncated':len(paths)>32,
        'pathKeyCandidates':[{'path':path,'computedKey':str(package.external_path_key(path,contract)),
            'hashInputEntryCount':count,'sameKeyLookupInputEntryCount':keys.get(package.external_path_key(path,contract),{}).get('entryCount',0)}
            for path,count in sorted(paths.items())[:32]],'evidenceBoundary':BOUNDARY}
    if any(h['sourceKind']=='anonymousProviderPackageCompletion' for h in hooks):
        output['packageCompletionObservations'] = _completion(rows,by_name,gates)
    if any(h['sourceKind']=='anonymousPackageReadTransform' for h in hooks):
        from scripts.webui.audio.semantics.package_read_observations import summarize_read_entries
        output['packageReadObservations']=summarize_read_entries(rows,by_name,gates.get('packageReadGate',{}))
    return output


def _completion(rows, hooks, gates):
    gate = gates.get('packageResultGate', {})
    schema = 'endfield.audio-package-completion-entry-observations.v2'
    if gate.get('status') != 'validated':
        return {'schema':schema,'status':gate.get('status','missing'),'detail':gate.get('detail','package result gate unavailable')}
    spec = gate['observerSpec']
    counts, statuses, representatives = Counter(), Counter(), {}
    package_gate = gates.get('externalPackageGate', {})
    for row in rows:
        hook = hooks[row['hook']]
        if hook['sourceKind'] != 'anonymousProviderPackageCompletion':
            continue
        counts['entries'] += 1
        fields = {f['name']:v if state==1 else None for f,v,state in zip(hook['memory'],row['values'],row['states'])}
        status = row['args'][hook['args']['completionStatus']['index']] & 0xffffffff
        statuses[str(status)] += 1
        provider = row['args'][hook['args']['providerPointer']['index']]
        request = row['args'][hook['args']['requestPointer']['index']]
        if row['returnAddress']-row['moduleBase'] != int(spec['callerReturnRva'],16):
            counts['unreviewedCaller'] += 1
            continue
        if fields.get('providerAddressPointPointer') != row['moduleBase']+int(spec['primaryAddressPointRva'],16):
            counts['differentOrUnreadableAddressPoint'] += 1
            continue
        if not (provider and request and fields.get('providerRetainedRequestPointer')==request and fields.get('requestProviderPointer')==provider):
            counts['noLocalRequestMatch'] += 1
            continue
        counts['localRequestMatches'] += 1
        result = fields.get('requestResultPointer')
        if not result or result != fields.get('providerResultPointer'):
            counts['noLocalResultMatch'] += 1
            continue
        counts['localResultMatches'] += 1
        if status != 1:
            continue
        counts['successStatusWithLocalResult'] += 1
        text = b''.join(unit.to_bytes(2,'little') for unit in row['textUnits']).decode('utf-16-le') if fields.get('requestWideText') is not None else None
        sample = {'captureId':row['captureId'],'path':text,'status':status,
                'flagsKind':fields.get('requestFlagsKind'),
                'byteLength':str(fields['resultByteLength']) if fields.get('resultByteLength') is not None else None,
                'blockOffset':str(fields['resultBlockOffset']) if fields.get('resultBlockOffset') is not None else None,
                'byteOffset':fields.get('resultByteOffset'),'blockBytes':fields.get('resultBlockBytes'),
                'keyLow':fields.get('resultKeyLow'),
                'packagePointer':hex(fields['resultPackagePointer']) if fields.get('resultPackagePointer') else None,
                'backingObjectPointer':hex(fields['resultPackageBackingObjectPointer']) if fields.get('resultPackageBackingObjectPointer') else None}
        if text and fields.get('requestFlagsKind') == 1 and package_gate.get('status') == 'validated':
            key = package.external_path_key(text, package_gate['contract'])
            sample['computedPathKey'] = str(key)
            low = fields.get('resultKeyLow')
            sample['pathKeyLowComparison'] = 'unreadable' if low is None else 'matched' if low == key & 0xffffffff else 'different'
            counts['externalPathKeyLow' + sample['pathKeyLowComparison'].capitalize()] += 1
            block, offset, observed = (fields.get(name) for name in ('resultBlockBytes','resultBlockOffset','resultByteOffset'))
            sample['byteOffsetComparison'] = ('unreadable' if None in (block, offset, observed) else
                'matched' if (block * offset) & 0xffffffff == observed else 'different')
        # Aggregate the whole admitted window before applying the display budget.
        # A repeated numeric request must not hide a later voice completion.
        identity = tuple(sample.get(name) for name in ('path','flagsKind','byteLength','blockOffset','byteOffset','blockBytes','keyLow','packagePointer','backingObjectPointer'))
        if identity in representatives:
            representatives[identity]['entryCount'] += 1
        else:
            sample['entryCount'] = 1
            representatives[identity] = sample
    samples = sorted(representatives.values(), key=lambda item: (not bool(item['path']), item['captureId']))
    return {'schema':schema,'status':'validated','counts':dict(counts),'statusCounts':dict(statuses),'samples':samples[:12],
            'distinctDescriptorSampleCount':len(samples),'samplesTruncated':len(samples)>12,
            'evidenceBoundary':'Local non-atomic completion-entry request/back-pointer and result equality under authenticated caller/address-point checks. Status one is an incoming completion status. A gated external-path calculation compares only the descriptor key low word and modulo-32-bit block geometry. Descriptor geometry and opaque package/backing pointers do not establish pointer generation, selected row, file identity, media reads, decoding or audibility.'}
