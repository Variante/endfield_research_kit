"""Local package read facts; never pair descriptor and transfer lifetimes."""
from collections import Counter
from scripts.game_data.wwise_package import decrypt_vfs_bytes
from scripts.webui.audio.semantics.observation_sampling import StratifiedSamples

SCHEMA='endfield.audio-package-read-entry-observations.v2'
BOUNDARY=('Non-atomic entry snapshots. The batch shows only its first record. Platform completion arguments belong to that entry; '
          'the pre-transform entry checks its local cookie descriptor and reviewed zero-error caller. Entries are not paired. '
          'Descriptor cohorts group matching local geometry, not allocation lifetimes. Range unions describe transform lengths only. '
          'Coverage dimensions count all checked observed entries before display limits; they do not measure corpus prevalence. '
          'One guarded buffer word is not full payload coverage or decoded PCM; file naming, allocation generation and audibility remain unresolved.')


def merge_ranges(ranges):
    """Union half-open integer ranges; never infer bytes between intervals."""
    merged=[]
    for start,end in sorted(ranges):
        if merged and start<=merged[-1][1]:
            merged[-1][1]=max(end,merged[-1][1])
        else:
            merged.append([start,end])
    return merged


def checked_transform_fields(row,hook,spec):
    """Return only independently checked, local transform-entry fields."""
    fields={f['name']:v if state==1 else None for f,v,state in zip(hook['memory'],row['values'],row['states'])}
    if row['returnAddress']-row['moduleBase']!=int(spec['transformCallerReturnRva'],16):
        return None,'transformUnreviewedCaller'
    descriptor=row['args'][hook['args']['descriptorPointer']['index']]
    if not descriptor or fields.get('cookieDescriptorPointer')!=descriptor:
        return None,'transformNoLocalDescriptorMatch'
    if fields.get('cookiePrimaryIoAddressPointPointer')!=row['moduleBase']+int(spec['primaryIoAddressPointRva'],16):
        return None,'transformDifferentOrUnreadableIo'
    return fields,'transformLocalDescriptorMatches'


def summarize_read_entries(rows, hooks, gate):
    if gate.get('status')!='validated':
        return {'schema':SCHEMA,'status':gate.get('status','missing'),'detail':gate.get('detail','package read gate unavailable')}
    counts, errors, transfers, cohorts=Counter(),Counter(),Counter(),{}
    sampler=StratifiedSamples(16)
    encryption_flags, alignments, relative_offsets=Counter(),Counter(),Counter()
    spec=gate['observerSpec']
    transform_gate=gate.get('packageTransformGate',{})
    for row in rows:
        hook=hooks[row['hook']];kind=hook['sourceKind']
        if kind not in ('anonymousDefaultIoReadBatch','anonymousDefaultIoReadCompletion','anonymousPackageReadTransform'):
            continue
        counts[kind]+=1
        fields={f['name']:v if state==1 else None for f,v,state in zip(hook['memory'],row['values'],row['states'])}
        arg=lambda name:row['args'][hook['args'][name]['index']]
        if kind=='anonymousDefaultIoReadBatch':
            match=fields.get('ioAddressPointPointer')==row['moduleBase']+int(spec['ioAddressPointRva'],16)
            counts['batchDefaultIoMatches' if match else 'batchDifferentOrUnreadableIo']+=1
            counts['positiveBatchCounts' if 0<(arg('batchCount')&0xffffffff)<0x80000000 else 'nonpositiveBatchCounts']+=1
        elif kind=='anonymousDefaultIoReadCompletion':
            error=arg('platformError')&0xffffffff;actual=arg('transferredBytes')&0xffffffff
            errors[str(error)]+=1
            requested=fields.get('transferRequestedBytes')
            comparison='unreadableRequest' if requested is None else 'exactRequestedBytes' if actual==requested else 'shorterThanRequested' if actual<requested else 'largerThanRequested'
            transfers[comparison]+=1
            counts['zeroErrorCompletions']+=error==0
        else:
            fields,comparison=checked_transform_fields(row,hook,spec)
            counts[comparison]+=1
            if fields is None:continue
            sample={'captureId':row['captureId']}
            handle=fields.get('descriptorFileHandle')
            sample['descriptorFileHandle']=hex(handle) if handle is not None else None
            for name in ('descriptorByteLength','descriptorBlockOffset','descriptorByteOffset','descriptorKeyLow','descriptorBlockBytes',
                         'transferFilePosition','transferRequestedBytes','transferTransformBytes'):
                value=fields.get(name)
                sample[name]=str(value) if value is not None and name in ('descriptorByteLength','descriptorBlockOffset','transferFilePosition') else value
            flag=fields.get('descriptorEncryptionFlagWord')
            sample['descriptorEncryptionFlag']=None if flag is None else flag&255
            encryption_flags['unreadable' if flag is None else str(flag&255)]+=1
            position,offset=(fields.get(name) for name in ('transferFilePosition','descriptorByteOffset'))
            relative=None if None in (position,offset) else position-offset
            alignments['unreadable' if relative is None else str(relative%4)]+=1
            relative_offsets['unreadable' if relative is None else 'zero' if relative==0 else 'positive' if relative>0 else 'negative']+=1
            word=fields.get('bufferFirstWord')
            bounded=all(fields.get(name) is not None and fields[name]>=4 for name in ('transferRequestedBytes','transferTransformBytes'))
            sample['preTransformBufferWord']=f'{word:08x}' if word is not None and bounded else None
            if transform_gate.get('status')=='validated':
                callback=next(g['entryRva'] for g in transform_gate['contract']['nativeGroups'] if g['key']=='transferCompletionDispatcher')
                counts['reviewedTransferCallbacks' if fields.get('transferCallbackPointer')==row['moduleBase']+int(callback,16) else 'differentOrUnreadableTransferCallbacks']+=1
                position,offset,key=(fields.get(name) for name in ('transferFilePosition','descriptorByteOffset','descriptorKeyLow'))
                if sample['preTransformBufferWord'] is not None and sample['descriptorEncryptionFlag']==1 and None not in (position,offset,key):
                    relative=(position-offset)&0xffffffff
                    if relative%4==0:
                        predicted=bytearray(word.to_bytes(4,'little'))
                        decrypt_vfs_bytes(predicted,0,4,key,data_offset=relative)
                        sample['predictedClearWord']=f'{int.from_bytes(predicted,"little"):08x}'
            geometry=('descriptorKeyLow','descriptorByteLength','descriptorBlockOffset','descriptorByteOffset','descriptorBlockBytes','descriptorPackagePointer','descriptorFileHandle')
            cohort_key=tuple(fields.get(name) for name in geometry)
            identity={key:value for key,value in sample.items() if key!='captureId'}
            sampler.add(cohort_key,identity,sample,label={name:sample[name] for name in
                ('descriptorKeyLow','descriptorByteLength','descriptorByteOffset')})
            cohort=cohorts.setdefault(cohort_key,{'descriptorKeyLow':sample['descriptorKeyLow'],
                'descriptorByteLength':sample['descriptorByteLength'],'descriptorByteOffset':sample['descriptorByteOffset'],
                'entryCount':0,'invalidRangeCount':0,'ranges':[],'wordOffsets':set()})
            cohort['entryCount']+=1
            position,length,offset,total=(fields.get(name) for name in ('transferFilePosition','transferTransformBytes','descriptorByteOffset','descriptorByteLength'))
            if None in (position,length,offset,total) or position<offset or length<=0 or position-offset+length>total:
                cohort['invalidRangeCount']+=1
            else:
                relative=position-offset
                cohort['ranges'].append((relative,relative+length))
                if sample['preTransformBufferWord'] is not None:cohort['wordOffsets'].add(relative)
    descriptor_cohorts=[]
    range_coverage=Counter()
    for cohort_key in sorted(cohorts,key=lambda key:tuple((value is not None,value or 0) for value in key)):
        cohort=cohorts[cohort_key]
        ranges=merge_ranges(cohort.pop('ranges'))
        total=cohort['descriptorByteLength']
        cohort.update(transformRangeBytes=str(sum(end-start for start,end in ranges)),
            transformRanges=[[str(start),str(end)] for start,end in ranges[:16]],
            rangesTruncated=len(ranges)>16,
            transformRangesSpanDescriptor=total is not None and ranges==[[0,int(total)]],
            distinctSampledWordCount=len(cohort.pop('wordOffsets')))
        state='invalid' if cohort['invalidRangeCount'] else 'complete' if cohort['transformRangesSpanDescriptor'] else 'partial'
        cohort['rangeCoverage']=state
        range_coverage[state]+=1
        descriptor_cohorts.append(cohort)
    samples,selection=sampler.finish()
    # Balance descriptor display across range states as well as sample display
    # across local geometry. Full state counts never depend on these budgets.
    range_groups=[[cohort for cohort in descriptor_cohorts if cohort['rangeCoverage']==state]
                  for state in ('complete','partial','invalid')]
    displayed_cohorts=[]
    for index in range(16):
        for group in range_groups:
            if index<len(group) and len(displayed_cohorts)<16:displayed_cohorts.append(group[index])
    hook_kinds=('anonymousDefaultIoReadBatch','anonymousDefaultIoReadCompletion','anonymousPackageReadTransform')
    return {'schema':SCHEMA,'status':'validated','counts':dict(counts),'platformErrorCounts':dict(errors),
            'hookCounts':{kind:counts[kind] for kind in hook_kinds},
            'transferComparisons':dict(transfers),'samples':samples,
            'distinctSampleCount':selection['distinctSampleCount'],'samplesTruncated':selection['samplesTruncated'],
            'sampleSelection':selection,
            'observedCoverage':{'checkedTransformEntryCount':sum(encryption_flags.values()),
                'encryptionFlagCounts':dict(sorted(encryption_flags.items())),
                'relativeOffsetModulo4Counts':dict(sorted(alignments.items())),
                'relativeOffsetCounts':dict(sorted(relative_offsets.items())),
                'descriptorRangeCohortCounts':{state:range_coverage[state] for state in ('complete','partial','invalid')},
                'evidenceBoundary':'All checked entries and local descriptor cohorts in this recording, before display limits. Observed coverage is not corpus prevalence, retained full payload bytes, allocation identity or lifetime.'},
            'descriptorCohorts':displayed_cohorts,'distinctDescriptorCohortCount':len(descriptor_cohorts),
            'descriptorCohortsTruncated':len(descriptor_cohorts)>16,
            'descriptorCohortSelection':{'strategy':'deterministicRangeCoverageRoundRobin','sampleLimit':16,
                'representedCohortCount':len(displayed_cohorts),'omittedCohortCount':len(descriptor_cohorts)-len(displayed_cohorts)},
            'alignedTransformGate':{'status':transform_gate.get('status','missing'),
                'detail':transform_gate.get('detail','aligned transform dependency unavailable'),
                'evidenceBoundary':transform_gate.get('evidenceBoundary')},'evidenceBoundary':BOUNDARY}
